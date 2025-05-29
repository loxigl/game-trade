"""
Обработчики сообщений RabbitMQ для marketplace-svc
"""

import logging
from typing import Dict, Any, Callable, Awaitable
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.connection import get_db
from .rabbitmq_service import get_rabbitmq_service, RabbitMQService
from ..models.core import User, Transaction, TransactionStatus, Sale
from .sale_service import SaleService
from .chat_client import ChatClient, get_chat_client
from ..config.settings import get_settings
from fastapi import Depends
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

settings = get_settings()
# Тип для обработчика сообщений
MessageHandler = Callable[[Dict[str, Any], Session], Awaitable[None]]


async def handle_user_created(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события создания пользователя
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение о создании пользователя: {message}")
    
    try:
        user_data = message.get("user", {})
        if not user_data or not user_data.get("id"):
            logger.error("Некорректный формат сообщения о создании пользователя")
            return
            
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(User.id == user_data["id"]).first()
        
        if existing_user:
            logger.info(f"Пользователь с ID={user_data['id']} уже существует в marketplace-svc. Обновляем данные.")
            # Обновляем существующего пользователя
            existing_user.email = user_data.get("email", existing_user.email)
            existing_user.username = user_data.get("username", existing_user.username)
            existing_user.is_active = user_data.get("is_active", existing_user.is_active)
            existing_user.is_verified = user_data.get("is_verified", existing_user.is_verified)
            existing_user.is_admin = user_data.get("is_admin", existing_user.is_admin)
            existing_user.roles = user_data.get("roles", existing_user.roles)
            existing_user.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Пользователь с ID={user_data['id']} обновлен в marketplace-svc")
        else:
            # Создаем нового пользователя
            new_user = User(
                id=user_data["id"],
                email=user_data.get("email", ""),
                username=user_data.get("username", ""),
                is_active=user_data.get("is_active", True),
                is_verified=user_data.get("is_verified", False),
                is_admin=user_data.get("is_admin", False),
                roles=user_data.get("roles", ["user"])
            )
            db.add(new_user)
            db.commit()
            logger.info(f"Новый пользователь создан в marketplace-svc с ID={user_data['id']}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке создания пользователя: {str(e)}")
        db.rollback()


async def handle_user_updated(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события обновления пользователя
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение об обновлении пользователя: {message}")
    
    try:
        user_data = message.get("user", {})
        if not user_data or not user_data.get("id"):
            logger.error("Некорректный формат сообщения об обновлении пользователя")
            return
            
        # Находим пользователя
        user = db.query(User).filter(User.id == user_data["id"]).first()
        
        if user:
            # Обновляем существующего пользователя
            user.email = user_data.get("email", user.email)
            user.username = user_data.get("username", user.username)
            user.is_active = user_data.get("is_active", user.is_active)
            user.is_verified = user_data.get("is_verified", user.is_verified)
            user.is_admin = user_data.get("is_admin", user.is_admin)
            user.roles = user_data.get("roles", user.roles)
            user.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Пользователь обновлен в marketplace-svc: ID={user_data['id']}")
        else:
            # Если пользователя нет, создаем нового
            logger.info(f"Пользователь с ID={user_data['id']} не найден в marketplace-svc. Создаем нового.")
            new_user = User(
                id=user_data["id"],
                email=user_data.get("email", ""),
                username=user_data.get("username", ""),
                is_active=user_data.get("is_active", True),
                is_verified=user_data.get("is_verified", False),
                is_admin=user_data.get("is_admin", False),
                roles=user_data.get("roles", ["user"])
            )
            db.add(new_user)
            db.commit()
            logger.info(f"Создан пользователь в marketplace-svc: ID={user_data['id']}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления пользователя: {str(e)}")
        db.rollback()


async def handle_user_deleted(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события удаления пользователя
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено сообщение об удалении пользователя: {message}")
    
    try:
        user_id = message.get("user_id")
        if not user_id:
            logger.error("Некорректный формат сообщения об удалении пользователя")
            return
            
        # Находим пользователя
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            # Помечаем пользователя как неактивного
            user.is_active = False
            user.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Пользователь в marketplace-svc с ID={user_id} помечен как неактивный")
        else:
            logger.warning(f"Пользователь с ID={user_id} не найден в marketplace-svc")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления пользователя: {str(e)}")
        db.rollback()


async def handle_transaction_event(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события транзакции из payment-svc
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено событие транзакции от payment-svc: {message}")
    
    try:
        # Получаем данные из сообщения
        transaction_id = message.get("transaction_id")
        
        # Если transaction_id отсутствует в корне, ищем в data
        if not transaction_id and "data" in message and isinstance(message["data"], dict):
            transaction_id = message["data"].get("transaction_id")
            
        if not transaction_id:
            logger.error("Отсутствует transaction_id в сообщении о транзакции")
            return
            
        # Извлекаем все доступные данные из сообщения
        event_type = message.get("event_type", "")
        listing_id = message.get("listing_id")
        buyer_id = message.get("buyer_id")
        seller_id = message.get("seller_id")
        amount = message.get("amount")
        currency = message.get("currency")
        fee_amount = message.get("fee_amount")
        status_value = message.get("status")
        created_at_str = message.get("created_at")
        updated_at_str = message.get("updated_at")
        completed_at_str = message.get("completed_at")
        
        # Смотрим в data для любых отсутствующих полей
        if "data" in message and isinstance(message["data"], dict):
            data = message["data"]
            if not listing_id and "listing_id" in data:
                listing_id = data.get("listing_id")
            if not buyer_id and "buyer_id" in data:
                buyer_id = data.get("buyer_id")
            if not seller_id and "seller_id" in data:
                seller_id = data.get("seller_id")
            if not amount and "amount" in data:
                amount = data.get("amount")
            if not currency and "currency" in data:
                currency = data.get("currency")
            if not fee_amount and "fee_amount" in data:
                fee_amount = data.get("fee_amount")
            if not status_value and "status" in data:
                status_value = data.get("status")
            elif not status_value and "to_state" in data:
                status_value = data.get("to_state")  # Обрабатываем случай с to_state
            if not created_at_str and "created_at" in data:
                created_at_str = data.get("created_at")
            if not updated_at_str and "updated_at" in data:
                updated_at_str = data.get("updated_at")
            if not completed_at_str and "completed_at" in data:
                completed_at_str = data.get("completed_at")
        
        # Преобразуем даты в объекты datetime
        created_at = None
        updated_at = None
        completed_at = None
        
        try:
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str)
            if updated_at_str:
                updated_at = datetime.fromisoformat(updated_at_str)
            if completed_at_str:
                completed_at = datetime.fromisoformat(completed_at_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка преобразования дат: {str(e)}")
            
        # Проверяем существование транзакции в нашей БД
        existing_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        
        # Определяем статус транзакции
        status = None
        
        # Преобразуем строковое значение в enum TransactionStatus
        mapping = {
            "PENDING": TransactionStatus.PENDING,
            "ESCROW_HELD": TransactionStatus.PAID,
            "PAID": TransactionStatus.PAID,
            "COMPLETED": TransactionStatus.COMPLETED,
            "REFUNDED": TransactionStatus.REFUNDED,
            "DISPUTED": TransactionStatus.DISPUTED,
            "CANCELLED": TransactionStatus.CANCELLED,
            "CANCELED": TransactionStatus.CANCELLED
        }
        
        # Пытаемся использовать маппинг статусов
        if status_value and isinstance(status_value, str):
            # Особая обработка для случая, когда приходит статус вида "TransactionStatus.XXX"
            if status_value.startswith("TransactionStatus."):
                try:
                    # Извлекаем часть после точки (например, COMPLETED из TransactionStatus.COMPLETED)
                    status_part = status_value.split(".", 1)[1].strip()
                    logger.info(f"Извлечен статус из TransactionStatus: {status_part}")
                    
                    # Пытаемся сопоставить с известными статусами
                    if status_part in mapping:
                        status = mapping[status_part]
                    else:
                        try:
                            # Пытаемся напрямую создать enum
                            status = TransactionStatus[status_part]
                        except (KeyError, ValueError):
                            logger.warning(f"Неизвестный статус транзакции: {status_part}")
                            status = TransactionStatus.PENDING  # Значение по умолчанию
                except Exception as e:
                    logger.error(f"Ошибка при разборе статуса транзакции '{status_value}': {str(e)}")
                    status = TransactionStatus.PENDING  # Значение по умолчанию
            else:
                # Стандартная обработка для обычных строковых статусов
                status_upper = status_value.upper()
                if status_upper in mapping:
                    status = mapping[status_upper]
                else:
                    # Пытаемся напрямую преобразовать
                    try:
                        status = TransactionStatus(status_value)
                    except ValueError:
                        logger.warning(f"Неизвестный статус транзакции: {status_value}")
                        status = TransactionStatus.PENDING  # Значение по умолчанию
        
        # Также можем определить статус по типу события
        if not status and event_type:
            event_to_status = {
                "transaction_created": TransactionStatus.PENDING,
                "escrow_funds_held": TransactionStatus.PAID,
                "escrow_funds_released": TransactionStatus.COMPLETED,  # Добавлен новый маппинг
                "transaction_completed": TransactionStatus.COMPLETED,
                "transaction_refunded": TransactionStatus.REFUNDED,
                "transaction_disputed": TransactionStatus.DISPUTED,
                "transaction_canceled": TransactionStatus.CANCELLED
            }
            
            for event_part, mapped_status in event_to_status.items():
                if event_part in event_type.lower():
                    status = mapped_status
                    logger.info(f"Статус определен по типу события '{event_type}': {status}")
                    break
        
        # Если до сих пор не определен статус
        if not status:
            logger.error(f"Не удалось определить статус для транзакции {transaction_id}")
            status = TransactionStatus.PENDING  # Значение по умолчанию
                
        # Если транзакция уже существует, обновляем её
        if existing_transaction:
            logger.info(f"Обновляем существующую транзакцию ID={transaction_id}")
            
            # Обновляем только если статус изменился или другие важные поля
            update_needed = False
            
            if status and existing_transaction.status != status:
                existing_transaction.status = status
                update_needed = True
                
            # Обновляем другие поля, если они переданы и отличаются
            if listing_id and existing_transaction.listing_id != listing_id:
                existing_transaction.listing_id = listing_id
                update_needed = True
                
            if buyer_id and existing_transaction.buyer_id != buyer_id:
                existing_transaction.buyer_id = buyer_id
                update_needed = True
                
            if seller_id and existing_transaction.seller_id != seller_id:
                existing_transaction.seller_id = seller_id
                update_needed = True
                
            if amount is not None and existing_transaction.amount != amount:
                existing_transaction.amount = float(amount)
                update_needed = True
                
            if currency and existing_transaction.currency != currency:
                existing_transaction.currency = currency
                update_needed = True
                
            if fee_amount is not None and existing_transaction.fee_amount != fee_amount:
                existing_transaction.fee_amount = float(fee_amount)
                update_needed = True
                
            # Обновляем даты, если они переданы и более новые
            if status == TransactionStatus.COMPLETED and completed_at:
                existing_transaction.completed_at = completed_at
                update_needed = True
                
            if updated_at:
                existing_transaction.updated_at = updated_at
                update_needed = True
            else:
                # Если updated_at не передан, но были изменения, обновляем текущим временем
                if update_needed:
                    existing_transaction.updated_at = datetime.utcnow()
            
            if update_needed:
                db.commit()
                logger.info(f"Транзакция ID={transaction_id} обновлена до статуса {status}")
                
                # Обновляем связанную продажу, если статус изменился
                sale = db.query(Sale).filter(Sale.transaction_id == transaction_id).first()
                if sale:
                    sale_service = SaleService(db)
                    logger.info(f"Обновляем статус продажи ID={sale.id}, статус до обновления {sale.status}")
                    # Обновляем статус продажи в зависимости от статуса транзакции
                    try:
                        if status == TransactionStatus.PAID:
                            await sale_service.update_sale_status(sale.id, 0, "payment_processing", "Средства переведены в эскроу")
                        elif status == TransactionStatus.COMPLETED:
                            await sale_service.update_sale_status(sale.id, 0, "completed", "Транзакция завершена")
                        elif status == TransactionStatus.REFUNDED:
                            await sale_service.update_sale_status(sale.id, 0, "refunded", "Средства возвращены")
                        elif status == TransactionStatus.DISPUTED:
                            await sale_service.update_sale_status(sale.id, 0, "disputed", "Открыт спор")
                        elif status == TransactionStatus.CANCELLED:
                            await sale_service.update_sale_status(sale.id, 0, "canceled", "Транзакция отменена")
                        logger.info(f"Обновлен статус продажи ID={sale.id} до статуса {sale.status}")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении статуса продажи ID={sale.id}: {str(e)}")
        else:
            # Создаем новую запись транзакции
            logger.info(f"Создаем новую транзакцию ID={transaction_id}")
            
            # Валидируем обязательные поля для создания транзакции
            if not all([listing_id, buyer_id, seller_id]):
                logger.warning(f"Недостаточно данных для создания транзакции ID={transaction_id}")
                # Пытаемся найти недостающие данные через связанную продажу
                sale = None
                if listing_id:
                    sale = db.query(Sale).filter(
                        Sale.listing_id == listing_id,
                        Sale.status.in_(["pending", "payment_processing"])
                    ).order_by(Sale.created_at.desc()).first()
                
                if sale:
                    if not buyer_id:
                        buyer_id = sale.buyer_id
                        logger.info(f"Получен buyer_id={buyer_id} из sale ID={sale.id}")
                    if not seller_id:
                        seller_id = sale.seller_id
                        logger.info(f"Получен seller_id={seller_id} из sale ID={sale.id}")
                    if not listing_id:
                        listing_id = sale.listing_id
                        logger.info(f"Получен listing_id={listing_id} из sale ID={sale.id}")
            
            # Проверяем еще раз обязательные поля
            if not all([listing_id, buyer_id, seller_id]):
                logger.error(f"Невозможно создать транзакцию ID={transaction_id} - отсутствуют обязательные поля")
                return
                
            # Создаем транзакцию с доступными данными
            try:
                new_transaction = Transaction(
                    id=transaction_id,
                    listing_id=listing_id,
                    buyer_id=buyer_id,
                    seller_id=seller_id,
                    amount=float(amount) if amount is not None else 0.0,
                    currency=currency or "USD",
                    fee_amount=float(fee_amount) if fee_amount is not None else 0.0,
                    status=status,
                    created_at=created_at or datetime.utcnow(),
                    updated_at=updated_at,
                    completed_at=completed_at
                )
                
                db.add(new_transaction)
                db.commit()
                db.refresh(new_transaction)
                logger.info(f"Создана новая транзакция в marketplace-svc ID={transaction_id}")
                
                # Проверяем, есть ли продажа с этим transaction_id
                sale = db.query(Sale).filter(Sale.transaction_id == transaction_id).first()
                
                if not sale:
                    logger.info(f"Не найдена продажа с transaction_id={transaction_id}, проверяем по параметрам")
                    
                    # Ищем продажу по комбинации параметров
                    filters = [
                        Sale.status.in_(["pending", "payment_processing"])
                    ]
                    
                    if listing_id:
                        filters.append(Sale.listing_id == listing_id)
                    if buyer_id:
                        filters.append(Sale.buyer_id == buyer_id)
                    if seller_id:
                        filters.append(Sale.seller_id == seller_id)
                    
                    sale = db.query(Sale).filter(*filters).order_by(Sale.created_at.desc()).first()
                    
                    if not sale and listing_id:
                        # Если все еще не нашли продажу, попробуем по одному listing_id
                        logger.info(f"Не найдена продажа по комбинации параметров, ищем только по listing_id={listing_id}")
                        sale = db.query(Sale).filter(
                            Sale.listing_id == listing_id,
                            Sale.status.in_(["pending", "payment_processing"])
                        ).order_by(Sale.created_at.desc()).first()
                    
                if sale and not sale.transaction_id:
                    try:
                        # Связываем продажу с транзакцией
                        sale.transaction_id = transaction_id
                        
                        # Обновляем статус продажи в зависимости от статуса транзакции
                        try:
                            if status == TransactionStatus.PAID:
                                sale.status = "payment_processing"
                                await sale_service.update_sale_status(sale.id, 0, "payment_processing", "Средства переведены в эскроу")
                            elif status == TransactionStatus.COMPLETED:
                                sale.status = "completed"
                                sale.completed_at = datetime.utcnow()
                                await sale_service.update_sale_status(sale.id, 0, "completed", "Транзакция завершена")
                            elif status == TransactionStatus.REFUNDED:
                                sale.status = "refunded"
                                await sale_service.update_sale_status(sale.id, 0, "refunded", "Средства возвращены")
                            elif status == TransactionStatus.DISPUTED:
                                sale.status = "disputed"
                                await sale_service.update_sale_status(sale.id, 0, "disputed", "Открыт спор")
                            elif status == TransactionStatus.CANCELLED:
                                sale.status = "canceled"
                                await sale_service.update_sale_status(sale.id, 0, "canceled", "Транзакция отменена")
                        except Exception as e:
                            logger.error(f"Ошибка при обновлении статуса продажи ID={sale.id}: {str(e)}")
                        
                        # Добавляем дополнительную информацию о транзакции
                        if not sale.extra_data:
                            sale.extra_data = {}
                        
                        sale.extra_data["transaction_update"] = {
                            "updated_at": datetime.utcnow().isoformat(),
                            "event_type": event_type,
                            "status": status.value if hasattr(status, 'value') else str(status),
                            "message": f"Транзакция {transaction_id} связана с продажей и имеет статус {status}"
                        }
                        
                        # Обновляем информацию о транзакции в чате, только если уже есть chat_id
                        if sale.chat_id:
                            try:
                                chat_client = get_chat_client()
                                system_token = settings.SYSTEM_TOKEN
                                
                                # Обновляем информацию о транзакции в существующем чате
                                await chat_client.update_chat(
                                    chat_id=sale.chat_id,
                                    transaction_id=transaction_id,
                                    listing_id=listing_id,
                                    user_token=system_token
                                )
                                logger.info(f"Обновлена информация о транзакции ID={transaction_id} в чате ID={sale.chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при обновлении информации о транзакции в чате: {str(e)}")
                        
                        db.commit()
                        logger.info(f"Обновлена продажа ID={sale.id} с transaction_id={transaction_id} и статусом {sale.status}")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении продажи: {str(e)}")
                        db.rollback()
                        
                        # Если возникла ошибка внешнего ключа, логируем детальную информацию для отладки
                        if "violates foreign key constraint" in str(e):
                            logger.error(f"Ошибка внешнего ключа. Проверка транзакции ID={transaction_id}, sale ID={sale.id}")
                            # Перепроверяем существование транзакции
                            tx_check = db.query(Transaction).filter(Transaction.id == transaction_id).first()
                            logger.error(f"Проверка транзакции: {tx_check is not None}")
                
            except Exception as e:
                logger.error(f"Ошибка при создании транзакции: {str(e)}")
                db.rollback()
                
    except Exception as e:
        logger.error(f"Ошибка при обработке события транзакции: {str(e)}")
        db.rollback()


async def handle_transaction_completed(message: Dict[str, Any], db: Session) -> None:
    """
    Обработчик события завершения транзакции из payment-svc
    
    Args:
        message: Данные сообщения
        db: Сессия базы данных
    """
    logger.info(f"Получено событие завершения транзакции от payment-svc: {message}")
    
    try:
        # Получаем transaction_id из сообщения
        transaction_id = message.get("transaction_id")
        
        # Если transaction_id отсутствует в корне, ищем в data
        if not transaction_id and "data" in message and isinstance(message["data"], dict):
            transaction_id = message["data"].get("transaction_id")
            
        if not transaction_id:
            logger.error("Отсутствует transaction_id в сообщении о завершении транзакции")
            return
        
        # Проверяем существование транзакции в БД
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        
        if not transaction:
            logger.error(f"Транзакция с ID={transaction_id} не найдена в marketplace-svc")
            return
        
        # Обновляем статус транзакции на COMPLETED
        transaction.status = TransactionStatus.COMPLETED
        transaction.updated_at = datetime.utcnow()
        
        # Устанавливаем дату завершения, если её нет
        if not transaction.completed_at:
            transaction.completed_at = datetime.utcnow()
        
        # Ищем связанную продажу
        sale = db.query(Sale).filter(Sale.transaction_id == transaction_id).first()
        
        if sale:
            # Создаем экземпляр сервиса продаж
            sale_service = SaleService(db)
            
            logger.info(f"Обновляем статус продажи ID={sale.id} на completed")
            
            try:
                # Обновляем статус продажи на completed
                await sale_service.update_sale_status(
                    sale_id=sale.id,
                    user_id=sale.buyer_id,
                    new_status="completed"
                )
                
                # Обновляем информацию о транзакции в чате, если есть chat_id
                if sale.chat_id:
                    try:
                        chat_client = get_chat_client()
                        system_token = settings.SYSTEM_TOKEN
                        
                        await chat_client.update_chat(
                            chat_id=sale.chat_id,
                            transaction_id=transaction_id,
                            listing_id=sale.listing_id,
                            user_token=system_token
                        )
                        
                        # Отправляем системное сообщение в чат о завершении транзакции
                        await chat_client.send_system_message(
                            chat_id=sale.chat_id,
                            content="✅ Транзакция успешно завершена. Средства переведены продавцу.",
                            user_token=system_token
                        )
                        
                        logger.info(f"Отправлено системное сообщение в чат ID={sale.chat_id} о завершении транзакции")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении информации о транзакции в чате: {str(e)}")
                
                logger.info(f"Статус продажи ID={sale.id} обновлен на completed")
            except Exception as e:
                logger.error(f"Ошибка при обновлении статуса продажи ID={sale.id}: {str(e)}")
        else:
            logger.warning(f"Не найдена продажа для транзакции ID={transaction_id}")
        
        # Сохраняем изменения в БД
        db.commit()
        logger.info(f"Транзакция ID={transaction_id} успешно обновлена на статус COMPLETED")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке события завершения транзакции: {str(e)}")
        db.rollback()


async def setup_rabbitmq_consumers() -> None:
    """
    Настройка потребителей сообщений RabbitMQ
    """
    # Получаем экземпляр сервиса RabbitMQ
    rabbitmq = get_rabbitmq_service()
    
    # Словарь с обработчиками сообщений для разных событий
    handlers = {
        ("user_events", "user.created"): handle_user_created,
        ("user_events", "user.updated"): handle_user_updated,
        ("user_events", "user.deleted"): handle_user_deleted,
        
        # События транзакций из payment-svc
        ("payment", "transaction.created"): handle_transaction_event,
        ("payment", "transaction.updated"): handle_transaction_event,
        ("payment", "transaction.completed"): handle_transaction_completed,  # Используем новый обработчик
        ("payment", "transaction.refunded"): handle_transaction_event,
        ("payment", "transaction.disputed"): handle_transaction_event,
        ("payment", "transaction.canceled"): handle_transaction_event,
        ("payment", "transaction.failed"): handle_transaction_event,
        
        # События Escrow из payment-svc
        ("payment", "escrow.funds_held"): handle_transaction_event,
        ("payment", "escrow.funds_released"): handle_transaction_completed,  # Используем новый обработчик
        ("payment", "escrow.funds_refunded"): handle_transaction_event,
        
        # События кошельков (если требуются)
        # ("payment", "wallet.created"): handle_wallet_event,
        # ("payment", "wallet.balance_changed"): handle_wallet_event,
    }
    
    # Получаем сессию базы данных
    db = next(get_db())
    
    # Регистрируем обработчики для разных типов сообщений
    for (exchange_name, routing_key), handler in handlers.items():
        queue_name = f"marketplace_svc_{exchange_name}_{routing_key.replace('.', '_')}"
        
        # Оборачиваем обработчик для передачи сессии базы данных
        async def wrapped_handler(message_data, _handler=handler):
            await _handler(message_data, db)
        
        # Регистрируем потребителя
        await rabbitmq.create_consumer(exchange_name, queue_name, routing_key, wrapped_handler)
        
        logger.info(f"Зарегистрирован обработчик для {exchange_name} -> {routing_key} -> {queue_name}") 