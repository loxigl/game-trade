"""
Обработчики сообщений RabbitMQ
"""

import logging
from typing import Dict, Any, Callable, Awaitable
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
from sqlalchemy import text
import psycopg2
import os
import re

from ..database.connection import get_db
from .transaction_service import get_transaction_service
from .rabbitmq_service import get_rabbitmq_service, RabbitMQService
from ..models.transaction import TransactionStatus, TransactionType, Transaction
from ..models.core import Sale, SaleStatus
from ..schemas.transaction import TransactionCreate
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Тип для обработчика сообщений
MessageHandler = Callable[[Dict[str, Any], Session], Awaitable[None]]


async def handle_listing_created(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события создания объявления
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение о создании объявления: {message}")
    # Здесь можно добавить логику обработки события создания объявления


async def handle_listing_updated(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события обновления объявления
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение об обновлении объявления: {message}")
    # Здесь можно добавить логику обработки события обновления объявления


async def handle_purchase_request(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события запроса на покупку
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение о запросе на покупку: {message}")
    
    try:
        # Извлекаем данные из сообщения
        listing_id = message.get("listing_id")
        buyer_id = message.get("buyer_id")
        seller_id = message.get("seller_id")
        item_id = message.get("item_id")
        amount = message.get("amount")
        currency = message.get("currency", "USD")
        
        if not all([listing_id, buyer_id, seller_id, item_id, amount]):
            logger.error("Отсутствуют обязательные поля в сообщении о запросе на покупку")
            return
        
        # Создаем транзакцию
        transaction_service = get_transaction_service(db)
        
        # Расчет комиссии (можно вынести в отдельный сервис)
        fee_percentage = 5.0  # 5% комиссия
        fee_amount = float(amount) * (fee_percentage / 100)
        
        # Создаем данные для транзакции
        transaction_data = TransactionCreate(
            buyer_id=buyer_id,
            seller_id=seller_id,
            listing_id=listing_id,
            item_id=item_id,
            amount=float(amount),
            currency=currency,
            fee_amount=fee_amount,
            fee_percentage=fee_percentage,
            type="purchase",
            description=f"Покупка по объявлению ID: {listing_id}",
            days_to_complete=3  # Стандартный период для Escrow
        )
        
        # Создаем транзакцию
        transaction = await transaction_service.create_transaction(transaction_data)
        logger.info(f"Создана транзакция ID: {transaction.id} для покупки по объявлению ID: {listing_id}")
        
        # Отправляем ответное сообщение в marketplace-svc
        rabbitmq = get_rabbitmq_service()
        response_message = {
            "event_type": "purchase_request_processed",
            "transaction_id": transaction.id,
            "listing_id": listing_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "status": transaction.status.value,
            "next_action": "escrow_payment"
        }
        
        await rabbitmq.publish("payment", "transaction.created", response_message)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на покупку: {str(e)}")


async def handle_sale_created(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события создания продажи
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение о создании продажи: {message}")
    
    try:
        # Создаем запись о продаже напрямую через ORM, используя правильное значение enum
        sale = Sale(
            id=message["sale_id"],
            listing_id=message["listing_id"],
            buyer_id=message["buyer_id"],
            seller_id=message["seller_id"],
            price=float(message["price"]),
            currency=message["currency"],
            status=SaleStatus.PENDING.value,  # Используем enum напрямую
            extra_data={
                "wallet_id": message.get("wallet_id"),
                "created_at_marketplace": message.get("created_at")
            }
        )
        
        # Добавляем в сессию и коммитим
        db.add(sale)
        db.commit()
        db.refresh(sale)
        
        logger.info(f"Создана запись о продаже ID: {sale.id}, статус: {sale.status}")
        
        # Отправляем подтверждение в marketplace-svc
        rabbitmq = get_rabbitmq_service()
        response_message = {
            "event_type": "sale_registered",
            "sale_id": sale.id,
            "status": "pending",  # В сообщении используем нижний регистр, т.к. это согласуется с API
            "next_action": "wait_for_escrow"
        }
        
        await rabbitmq.publish("marketplace", "sales.registered", response_message)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке создания продажи: {str(e)}")
        if 'db' in locals() and db:
            db.rollback()  # Откатываем изменения в случае ошибки
        raise  # Пробрасываем ошибку дальше


async def handle_sale_completed(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события завершения продажи
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение о завершении продажи: {message}")
    
    try:
        transaction_service = get_transaction_service(db)
        
        # Получаем транзакцию по sale_id
        transaction = await transaction_service.get_transaction_by_sale_id(message["sale_id"])
        if not transaction:
            logger.error(f"Транзакция для продажи {message['sale_id']} не найдена")
            return
        
        # Обновляем статус транзакции
        updated_transaction = await transaction_service.update_transaction_status(
            transaction_id=transaction.id,
            new_status=TransactionStatus.COMPLETED,
            reason="Продажа завершена успешно"
        )
        
        logger.info(f"Транзакция {transaction.id} обновлена в статус COMPLETED")
        
        # Отправляем подтверждение в marketplace-svc
        rabbitmq = get_rabbitmq_service()
        response_message = {
            "event_type": "transaction_completed",
            "transaction_id": transaction.id,
            "sale_id": message["sale_id"],
            "status": TransactionStatus.COMPLETED.value,
            "completed_at": updated_transaction.completed_at.isoformat() if updated_transaction.completed_at else None
        }
        
        await rabbitmq.publish("marketplace", "sales.transaction_completed", response_message)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке завершения продажи: {str(e)}")


async def handle_escrow_funds_held(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события перевода средств в Escrow
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено событие о переводе средств в Escrow: {message}")
    
    try:
        # Получаем ID транзакции
        transaction_id = message.get("transaction_id")
        if not transaction_id:
            logger.error("Отсутствует ID транзакции в сообщении о переводе в Escrow")
            return
        
        # Получаем транзакцию
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            logger.error(f"Транзакция {transaction_id} не найдена")
            return
        
        # Получаем продажу, связанную с транзакцией
        sale_id = None
        if transaction.extra_data and "sale_id" in transaction.extra_data:
            sale_id = transaction.extra_data["sale_id"]
            
        # Если нет продажи, ищем по listing_id
        if not sale_id:
            sale = db.query(Sale).filter(
                Sale.listing_id == transaction.listing_id,
                Sale.transaction_id.is_(None)  # Ещё не привязана к транзакции
            ).order_by(Sale.created_at.desc()).first()
            
            if sale:
                sale_id = sale.id
                # Связываем продажу с транзакцией
                sale.transaction_id = transaction_id
                sale.status = SaleStatus.PAYMENT_PROCESSING.value
                transaction.extra_data = transaction.extra_data or {}
                transaction.extra_data["sale_id"] = sale.id
                db.commit()
                logger.info(f"Продажа {sale.id} связана с транзакцией {transaction_id} и переведена в статус PAYMENT_PROCESSING")
        
        # Отправляем уведомление в marketplace-svc
        if sale_id:
            rabbitmq = get_rabbitmq_service()
            sale_data = {
                "transaction_id": transaction_id,
                "sale_id": sale_id,
                "listing_id": transaction.listing_id,
                "buyer_id": transaction.buyer_id,
                "seller_id": transaction.seller_id,
                "status": "escrow_held"
            }
            
            await rabbitmq.publish("marketplace", "escrow.funds_held", sale_data)
            logger.info(f"Уведомление о переводе в Escrow для продажи {sale_id} отправлено в marketplace-svc")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке события перевода в Escrow: {str(e)}")


async def setup_rabbitmq_consumers() -> None:
    """
    Настройка потребителей сообщений RabbitMQ
    """
    # Получаем экземпляр сервиса RabbitMQ
    rabbitmq = get_rabbitmq_service()
    
    # Словарь с обработчиками сообщений для разных событий
    # Ключ: (exchange_name, routing_key)
    handlers = {
        ("marketplace", "listing.created"): handle_listing_created,
        ("marketplace", "listing.updated"): handle_listing_updated,
        ("marketplace", "purchase.request"): handle_purchase_request,
        ("marketplace", "sales.created"): handle_sale_created,
        ("marketplace", "sales.completed"): handle_sale_completed,
        ("payment", "escrow.funds_held"): handle_escrow_funds_held,
    }
    
    # Обертка для передачи сессии БД в обработчики
    async def message_processor(handler: MessageHandler, message: Dict[str, Any]) -> None:
        """
        Обертка для обработчика сообщений, которая предоставляет сессию БД
        
        Args:
            handler: Функция-обработчик
            message: Сообщение для обработки
        """
        # Получаем новую сессию БД
        db = next(get_db())
        try:
            # Вызываем обработчик с сессией
            await handler(message, db)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")
            db.rollback()  # Откатываем изменения в случае ошибки
        finally:
            db.close()  # Закрываем сессию
    
    # Регистрируем обработчики для разных типов сообщений
    for (exchange_name, routing_key), handler in handlers.items():
        queue_name = f"payment_svc_{exchange_name}_{routing_key.replace('.', '_')}"
        
        # Создаем обертку для конкретного обработчика
        processor = lambda msg, h=handler: message_processor(h, msg)
        
        # Регистрируем потребителя
        await rabbitmq.create_consumer(exchange_name, queue_name, routing_key, processor)
        
        logger.info(f"Зарегистрирован обработчик для {exchange_name} -> {routing_key} -> {queue_name}") 