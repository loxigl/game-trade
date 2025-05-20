"""
Сервис для работы с транзакциями и механизмом Escrow
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import logging
from uuid import UUID

from .transaction_history_service import TransactionHistoryService
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.wallet import Wallet, WalletTransaction, Currency, WalletStatus
from ..schemas.transaction import TransactionCreate, TransactionUpdate
from .rabbitmq_service import get_rabbitmq_service

logger = logging.getLogger(__name__)

class TransactionService:
    """Сервис для работы с транзакциями и механизмом Escrow"""

    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных
        """
        self.db = db
        self._escrow_wallet_id = None  # ID кошелька Escrow (будет получен при первом запросе)
    
    async def _get_escrow_wallet(self) -> Wallet:
        """
        Получить или создать системный Escrow кошелек
        
        Returns:
            Кошелек Escrow
        """
        # Проверяем кэш
        if self._escrow_wallet_id:
            escrow_wallet = self.db.query(Wallet).filter(Wallet.id == self._escrow_wallet_id).first()
            if escrow_wallet:
                return escrow_wallet
        
        # Ищем системный Escrow кошелек
        escrow_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == 0, 
            Wallet.is_default == True
        ).first()
        
        # Если не существует, создаем новый
        if not escrow_wallet:
            # Начальные балансы для всех поддерживаемых валют
            initial_balances = {currency.value: 0.0 for currency in Currency}
            
            escrow_wallet = Wallet(
                user_id=0,  # Системный пользователь
                balances=initial_balances,  # Мультивалютные балансы
                status=WalletStatus.ACTIVE,
                is_default=True,
                is_system_escrow=True,
                notes="Системный Escrow кошелек"
            )
            self.db.add(escrow_wallet)
            self.db.commit()
            self.db.refresh(escrow_wallet)
            logger.info(f"Создан системный Escrow кошелек с ID {escrow_wallet.id}")
        
        # Сохраняем ID в кэш
        self._escrow_wallet_id = escrow_wallet.id
        return escrow_wallet
    
    async def create_transaction(self, transaction_data: TransactionCreate) -> Transaction:
        """
        Создать новую транзакцию
        
        Args:
            transaction_data: Данные для создания транзакции
            
        Returns:
            Созданная транзакция
        """
        # Создаем транзакцию
        transaction = Transaction(
            buyer_id=transaction_data.buyer_id,
            seller_id=transaction_data.seller_id,
            listing_id=transaction_data.listing_id,
            item_id=transaction_data.item_id,
            amount=transaction_data.amount,
            currency=transaction_data.currency,
            fee_amount=transaction_data.fee_amount,
            fee_percentage=transaction_data.fee_percentage,
            type=transaction_data.type,
            status=TransactionStatus.PENDING,
            description=transaction_data.description,
            notes=transaction_data.notes,
            extra_data=transaction_data.extra_data,
            completion_deadline=datetime.utcnow() + timedelta(days=transaction_data.days_to_complete or 3)
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Публикуем событие о создании транзакции
        await self._publish_transaction_event(transaction, "transaction_created")
        
        return transaction
    
    async def process_escrow_payment(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Обработать платеж и перевести средства в Escrow
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные для обработки (опционально)
            
        Returns:
            Обновленная транзакция
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Нельзя обработать платеж для транзакции в статусе {transaction.status}")
        
        # Получаем кошельки покупателя и Escrow
        buyer_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.buyer_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not buyer_wallet:
            raise ValueError(f"Активный кошелек покупателя не найден")
        
        # Проверяем наличие валюты в кошельке и достаточность средств
        buyer_balance = buyer_wallet.balances.get(transaction.currency, 0)
        if buyer_balance < transaction.amount:
            raise ValueError("Недостаточно средств на кошельке покупателя")
        
        escrow_wallet = await self._get_escrow_wallet()
        
        # Выполняем транзакцию: списываем с кошелька покупателя
        buyer_wallet.balances[transaction.currency] = buyer_balance - transaction.amount
        # Маркируем балансы как измененные для SQLAlchemy
        buyer_wallet.balances = dict(buyer_wallet.balances)
        
        # Создаем запись в истории кошелька покупателя
        buyer_wallet_transaction = WalletTransaction(
            wallet_id=buyer_wallet.id,
            amount=-transaction.amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=buyer_balance,
            balance_after=buyer_wallet.balances[transaction.currency],
            type="debit",
            description=f"Списание средств для Escrow платежа (ID: {transaction.id})"
        )
        self.db.add(buyer_wallet_transaction)
        
        # Зачисляем на счет Escrow
        escrow_balance = escrow_wallet.balances.get(transaction.currency, 0)
        escrow_wallet.balances[transaction.currency] = escrow_balance + transaction.amount
        # Маркируем балансы как измененные для SQLAlchemy
        escrow_wallet.balances = dict(escrow_wallet.balances)
        
        # Создаем запись в истории кошелька Escrow
        escrow_wallet_transaction = WalletTransaction(
            wallet_id=escrow_wallet.id,
            amount=transaction.amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=escrow_balance,
            balance_after=escrow_wallet.balances[transaction.currency],
            type="credit",
            description=f"Зачисление средств в Escrow (ID: {transaction.id})"
        )
        self.db.add(escrow_wallet_transaction)
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.ESCROW_HELD
        transaction.escrow_held_at = datetime.now(timezone.utc)
        
        # Добавляем информацию о кошельке в extra_data
        if not transaction.extra_data:
            transaction.extra_data = {}
        
        transaction.extra_data["escrow"] = {
            "wallet_id": escrow_wallet.id,
            "held_at": transaction.escrow_held_at.isoformat()
        }
        
        # Если в запросе есть sale_id, сохраняем его для связи с marketplace-svc
        if data and isinstance(data, dict) and "sale_id" in data:
            transaction.extra_data["sale_id"] = data["sale_id"]
            logger.info(f"Связываем транзакцию {transaction.id} с продажей {data['sale_id']}")
            
        # Сохраняем транзакцию
        self.db.commit()
        
        # Публикуем событие об успешном переводе в Escrow
        await self._publish_transaction_event(transaction, "escrow_funded")
        
        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "escrow_held_at": transaction.escrow_held_at.isoformat() if transaction.escrow_held_at else None,
            "wallet_id": escrow_wallet.id
        }
    
    async def complete_transaction(self, transaction_id: int) -> Transaction:
        """
        Завершить транзакцию и перевести средства продавцу
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Обновленная транзакция
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        if transaction.status != TransactionStatus.ESCROW_HELD:
            raise ValueError(f"Нельзя завершить транзакцию в статусе {transaction.status}")
        
        # Получаем кошельки продавца и Escrow
        seller_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.seller_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not seller_wallet:
            raise ValueError(f"Активный кошелек продавца не найден")
            
        # Инициализируем баланс для этой валюты, если нужно
        if transaction.currency not in seller_wallet.balances:
            seller_wallet.balances[transaction.currency] = 0.0
        
        escrow_wallet = await self._get_escrow_wallet()
        
        # Проверяем наличие валюты в кошельке эскроу
        if transaction.currency not in escrow_wallet.balances:
            raise ValueError(f"В кошельке Escrow нет баланса в валюте {transaction.currency}")
            
        # Проверяем достаточность средств в Escrow
        if escrow_wallet.balances[transaction.currency] < transaction.amount:
            raise ValueError(f"Недостаточно средств в Escrow для завершения транзакции")
        
        # Расчет итоговой суммы (сумма транзакции за вычетом комиссии)
        final_amount = transaction.amount - transaction.fee_amount
        
        # Текущие балансы для записи в историю
        escrow_before = escrow_wallet.balances[transaction.currency]
        seller_before = seller_wallet.balances[transaction.currency]
        
        # Выполняем транзакцию: списываем с Escrow
        escrow_wallet.balances[transaction.currency] -= transaction.amount
        # Маркируем балансы как измененные для SQLAlchemy
        escrow_wallet.balances = dict(escrow_wallet.balances)
        
        # Создаем запись в истории кошелька Escrow
        escrow_wallet_transaction = WalletTransaction(
            wallet_id=escrow_wallet.id,
            amount=-transaction.amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=escrow_before,
            balance_after=escrow_wallet.balances[transaction.currency],
            type="debit",
            description=f"Списание средств из Escrow для выплаты продавцу (ID: {transaction.id})"
        )
        self.db.add(escrow_wallet_transaction)
        
        # Зачисляем на счет продавца (за вычетом комиссии)
        seller_wallet.balances[transaction.currency] += final_amount
        # Маркируем балансы как измененные для SQLAlchemy
        seller_wallet.balances = dict(seller_wallet.balances)
        
        # Создаем запись в истории кошелька продавца
        seller_wallet_transaction = WalletTransaction(
            wallet_id=seller_wallet.id,
            amount=final_amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=seller_before,
            balance_after=seller_wallet.balances[transaction.currency],
            type="credit",
            description=f"Получение средств за продажу (ID: {transaction.id})"
        )
        self.db.add(seller_wallet_transaction)
        
        # Если есть комиссия, создаем запись о ней (перевод на системный кошелек комиссий)
        if transaction.fee_amount > 0:
            # Получаем системный кошелек комиссий (TODO: создать метод для получения системного кошелька комиссий)
            # В рамках этой реализации, просто оставляем комиссию в Escrow кошельке
            pass
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(transaction)
        
        # Публикуем событие о завершении транзакции
        await self._publish_transaction_event(transaction, "transaction_completed")
        
        return transaction
    
    async def refund_transaction(self, transaction_id: int, reason: str = None) -> Transaction:
        """
        Отменить транзакцию и вернуть средства покупателю
        
        Args:
            transaction_id: ID транзакции
            reason: Причина возврата
            
        Returns:
            Обновленная транзакция
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        if transaction.status != TransactionStatus.ESCROW_HELD:
            raise ValueError(f"Нельзя выполнить возврат для транзакции в статусе {transaction.status}")
        
        # Получаем кошельки покупателя и Escrow
        buyer_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.buyer_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not buyer_wallet:
            raise ValueError(f"Активный кошелек покупателя не найден")
            
        # Инициализируем баланс для этой валюты, если нужно
        if transaction.currency not in buyer_wallet.balances:
            buyer_wallet.balances[transaction.currency] = 0.0
        
        escrow_wallet = await self._get_escrow_wallet()
        
        # Проверяем наличие валюты в кошельке эскроу
        if transaction.currency not in escrow_wallet.balances:
            raise ValueError(f"В кошельке Escrow нет баланса в валюте {transaction.currency}")
            
        # Проверяем достаточность средств в Escrow
        if escrow_wallet.balances[transaction.currency] < transaction.amount:
            raise ValueError(f"Недостаточно средств в Escrow для возврата")
            
        # Текущие балансы для записи в историю
        escrow_before = escrow_wallet.balances[transaction.currency]
        buyer_before = buyer_wallet.balances[transaction.currency]
        
        # Выполняем транзакцию: списываем с Escrow
        escrow_wallet.balances[transaction.currency] -= transaction.amount
        # Маркируем балансы как измененные для SQLAlchemy
        escrow_wallet.balances = dict(escrow_wallet.balances)
        
        # Создаем запись в истории кошелька Escrow
        escrow_wallet_transaction = WalletTransaction(
            wallet_id=escrow_wallet.id,
            amount=-transaction.amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=escrow_before,
            balance_after=escrow_wallet.balances[transaction.currency],
            type="debit",
            description=f"Списание средств из Escrow для возврата покупателю (ID: {transaction.id})"
        )
        self.db.add(escrow_wallet_transaction)
        
        # Зачисляем на счет покупателя
        buyer_wallet.balances[transaction.currency] += transaction.amount
        # Маркируем балансы как измененные для SQLAlchemy
        buyer_wallet.balances = dict(buyer_wallet.balances)
        
        # Создаем запись в истории кошелька покупателя
        buyer_wallet_transaction = WalletTransaction(
            wallet_id=buyer_wallet.id,
            amount=transaction.amount,
            currency=transaction.currency,
            transaction_id=transaction.id,
            balance_before=buyer_before,
            balance_after=buyer_wallet.balances[transaction.currency],
            type="credit",
            description=f"Возврат средств (ID: {transaction.id})"
        )
        self.db.add(buyer_wallet_transaction)
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.REFUNDED
        transaction.refunded_at = datetime.utcnow()
        transaction.refund_reason = reason
        
        self.db.commit()
        self.db.refresh(transaction)
        
        # Публикуем событие о возврате средств
        await self._publish_transaction_event(transaction, "transaction_refunded")
        
        return transaction
    
    async def dispute_transaction(self, transaction_id: int, reason: str) -> Transaction:
        """
        Открыть спор по транзакции
        
        Args:
            transaction_id: ID транзакции
            reason: Причина спора
            
        Returns:
            Обновленная транзакция
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        if transaction.status != TransactionStatus.ESCROW_HELD:
            raise ValueError(f"Нельзя открыть спор для транзакции в статусе {transaction.status}")
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.DISPUTED
        transaction.disputed_at = datetime.utcnow()
        transaction.dispute_reason = reason
        
        self.db.commit()
        self.db.refresh(transaction)
        
        # Публикуем событие об открытии спора
        await self._publish_transaction_event(transaction, "transaction_disputed")
        
        return transaction
    
    async def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """
        Получить транзакцию по ID
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Транзакция или None, если не найдена
        """
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    async def get_user_transactions(self, user_id: int, status: Optional[TransactionStatus] = None,skip: int = 0, limit: int = 10,role: Optional[str] = None) -> List[Transaction]:
        """
        Получить транзакции пользователя
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу транзакций (опционально)
            skip: Количество транзакций для пропуска
            limit: Количество транзакций для получения
            role: Роль пользователя (опционально)
        Returns:
            Список транзакций
        """
        query = self.db.query(Transaction).filter(
            or_(
                Transaction.buyer_id == user_id,
                Transaction.seller_id == user_id
            )
        )
        if role == "buyer":
            query = query.filter(Transaction.buyer_id == user_id)
        elif role == "seller":
            query = query.filter(Transaction.seller_id == user_id)
        if status:
            query = query.filter(Transaction.status == status)
        
        return query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
     
    async def count_user_transactions(self, user_id: int, status: Optional[TransactionStatus] = None,role: Optional[str] = None) -> int:
        """Подсчет количества транзакций пользователя"""
        query = self.db.query(func.count(Transaction.id)).filter(
            or_(
                Transaction.buyer_id == user_id,
                Transaction.seller_id == user_id
            )
        )
        if role == "buyer":
            query = query.filter(Transaction.buyer_id == user_id)
        elif role == "seller":
            query = query.filter(Transaction.seller_id == user_id)
        if status:
            query = query.filter(Transaction.status == status)
        
        return query.scalar()
    
    async def _publish_transaction_event(self, transaction: Transaction, event_type: str) -> None:
        """
        Опубликовать событие о транзакции в RabbitMQ
        
        Args:
            transaction: Транзакция
            event_type: Тип события
        """
        try:
            rabbitmq_service = get_rabbitmq_service()
            
            # Формируем подробное сообщение со всеми полями
            message = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "transaction_id": transaction.id,
                "transaction_uid": str(transaction.transaction_uid) if transaction.transaction_uid else None,
                "buyer_id": transaction.buyer_id,
                "seller_id": transaction.seller_id,
                "listing_id": transaction.listing_id,
                "item_id": transaction.item_id,
                "amount": float(transaction.amount) if transaction.amount is not None else 0.0,
                "currency": transaction.currency or "USD",
                "fee_amount": float(transaction.fee_amount) if transaction.fee_amount is not None else 0.0,
                "fee_percentage": float(transaction.fee_percentage) if transaction.fee_percentage is not None else 0.0,
                "status": transaction.status.value if transaction.status else None,
                "type": transaction.type.value if transaction.type else None,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
                "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
                "escrow_held_at": transaction.escrow_held_at.isoformat() if transaction.escrow_held_at else None,
                "disputed_at": transaction.disputed_at.isoformat() if transaction.disputed_at else None,
                "refunded_at": transaction.refunded_at.isoformat() if transaction.refunded_at else None,
                "canceled_at": transaction.canceled_at.isoformat() if transaction.canceled_at else None,
                "description": transaction.description,
                "notes": transaction.notes,
                "extra_data": transaction.extra_data,
                "parent_transaction_id": transaction.parent_transaction_id,
                "wallet_id": transaction.wallet_id
            }
            
            # ВАЖНО: Всегда добавляем sale_id в корень сообщения, если он есть в extra_data
            if transaction.extra_data and isinstance(transaction.extra_data, dict):
                # Проверяем наличие sale_id в разных местах extra_data
                if "sale_id" in transaction.extra_data:
                    message["sale_id"] = transaction.extra_data["sale_id"]
                    logger.info(f"Добавлен sale_id={transaction.extra_data['sale_id']} в корень сообщения для события {event_type}")
                
                # Проверяем также во вложенных структурах
                if "escrow" in transaction.extra_data and isinstance(transaction.extra_data["escrow"], dict) and "sale_id" in transaction.extra_data["escrow"]:
                    message["sale_id"] = transaction.extra_data["escrow"]["sale_id"]
                    logger.info(f"Добавлен sale_id={transaction.extra_data['escrow']['sale_id']} из escrow в корень сообщения для события {event_type}")
                
                # Если есть доп. данные связанные с продажей
                for field in ["sale_data", "sale_info", "marketplace_data"]:
                    if field in transaction.extra_data:
                        message[field] = transaction.extra_data[field]
            
            # Публикуем события в RabbitMQ
            exchange_name = "payment"
            
            # Маппинг типов событий на ключи маршрутизации
            event_to_routing_key = {
                "created": "transaction.created",
                "updated": "transaction.updated",
                "completed": "transaction.completed",
                "refunded": "transaction.refunded",
                "disputed": "transaction.disputed",
                "canceled": "transaction.canceled",
                "failed": "transaction.failed",
                "escrow_funded": "escrow.funds_held",
                "escrow_released": "escrow.funds_released",
                "escrow_refunded": "escrow.funds_refunded"
            }
            
            # Получаем ключ маршрутизации для текущего события
            routing_key = event_to_routing_key.get(event_type)
            
            if not routing_key:
                # Если не нашли соответствие, используем общий формат
                routing_key = f"transaction.{event_type}"
                
            # Публикуем сообщение
            await rabbitmq_service.publish(exchange_name, routing_key, message)
            logger.info(f"Опубликовано событие {routing_key} для транзакции {transaction.id}")
            
            # Дополнительная публикация для специфических событий
            if event_type == "completed":
                # Отправляем событие завершения транзакции в marketplace
                await rabbitmq_service.publish(exchange_name, "sales.transaction_completed", message)
                logger.info(f"Отправлено дополнительное уведомление sales.transaction_completed для транзакции {transaction.id}")
                
        except Exception as e:
            logger.error(f"Ошибка при публикации события транзакции {transaction.id}: {str(e)}")
            # Не прерываем обработку при ошибке публикации события
            
    async def update_transaction(self, transaction_id: int, transaction_data: TransactionUpdate) -> Transaction:
        """
        Обновить транзакцию
        
        Args:
            transaction_id: ID транзакции
            transaction_data: Данные для обновления
            
        Returns:
            Обновленная транзакция
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Обновляем поля
        for key, value in transaction_data.dict(exclude_unset=True).items():
            setattr(transaction, key, value)
        
        transaction.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(transaction)
        
        # Публикуем событие об обновлении транзакции
        await self._publish_transaction_event(transaction, "transaction_updated")
        
        return transaction

    def get_history_service(db: Session) -> TransactionHistoryService:
        """
        Получить экземпляр сервиса истории транзакций
        """
        return TransactionHistoryService(db)


def get_transaction_service(db: Session) -> TransactionService:
    """
    Получить экземпляр сервиса транзакций
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Экземпляр TransactionService
    """
    return TransactionService(db) 