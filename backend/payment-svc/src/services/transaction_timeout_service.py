"""
Сервис для обработки истекших транзакций
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..database.connection import get_db
from ..models.transaction import Transaction, TransactionStatus
from .transaction_state_service import get_transaction_state_service
from .event_service import EventType, EventPayload, get_event_service

logger = logging.getLogger(__name__)

class TransactionTimeoutService:
    """
    Сервис для обработки истекших транзакций
    
    Периодически проверяет транзакции на истечение срока и выполняет
    соответствующие действия (отмена, возврат средств и т.д.)
    """
    
    def __init__(self):
        """Инициализация сервиса обработки истекших транзакций"""
        self._initialized = False
        self._running = False
        self.check_interval = 60 * 5  # 5 минут (в секундах)
        self.event_service = get_event_service()
    
    async def initialize(self) -> None:
        """Инициализация сервиса"""
        if self._initialized:
            return
        
        # Запускаем фоновую задачу
        asyncio.create_task(self._background_check_loop())
        
        logger.info("Сервис обработки истекших транзакций инициализирован")
        self._initialized = True
    
    async def _background_check_loop(self) -> None:
        """Фоновая задача для периодической проверки истекших транзакций"""
        self._running = True
        
        logger.info(f"Запуск фоновой задачи проверки истекших транзакций (интервал: {self.check_interval} сек)")
        
        while self._running:
            try:
                await self._process_expired_transactions()
            except Exception as e:
                logger.error(f"Ошибка при проверке истекших транзакций: {str(e)}")
            
            # Ждем до следующей проверки
            await asyncio.sleep(self.check_interval)
    
    async def _process_expired_transactions(self) -> None:
        """Обработка истекших транзакций"""
        # Получаем сессию БД
        db = next(get_db())
        
        try:
            # Получаем текущее время
            now = datetime.utcnow()
            
            # Получаем транзакции, у которых истек срок
            # Ищем транзакции в состоянии PENDING или ESCROW_HELD с истекшим сроком действия
            expired_transactions = db.query(Transaction).filter(
                Transaction.expiration_date <= now,
                Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.ESCROW_HELD])
            ).all()
            
            if not expired_transactions:
                logger.debug("Истекших транзакций не найдено")
                return
            
            logger.info(f"Найдено {len(expired_transactions)} истекших транзакций")
            
            # Обрабатываем каждую истекшую транзакцию
            for transaction in expired_transactions:
                await self._handle_expired_transaction(transaction.id, db)
        
        except Exception as e:
            logger.error(f"Ошибка при обработке истекших транзакций: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def _handle_expired_transaction(self, transaction_id: int, db: Session) -> None:
        """
        Обработка конкретной истекшей транзакции
        
        Args:
            transaction_id: ID транзакции
            db: Сессия базы данных
        """
        try:
            # Получаем транзакцию
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            
            if not transaction:
                logger.error(f"Транзакция с ID {transaction_id} не найдена")
                return
            
            logger.info(f"Обработка истекшей транзакции ID {transaction_id}, статус: {transaction.status}")
            
            # Получаем сервис управления состояниями
            transaction_state_service = get_transaction_state_service(db)
            
            # В зависимости от текущего состояния выполняем соответствующее действие
            if transaction.status == TransactionStatus.PENDING:
                # Если транзакция в ожидании оплаты, просто отменяем её
                transaction = await transaction_state_service.cancel_transaction(
                    transaction_id, 
                    {"reason": "Истек срок транзакции"}
                )
                logger.info(f"Транзакция {transaction_id} отменена из-за истечения срока")
                
            elif transaction.status == TransactionStatus.ESCROW_HELD:
                # Если средства уже в Escrow, возвращаем их покупателю
                transaction = await transaction_state_service.refund_transaction(
                    transaction_id, 
                    {"reason": "Истек срок транзакции в Escrow"}
                )
                logger.info(f"Средства по транзакции {transaction_id} возвращены из-за истечения срока")
            
            # Публикуем событие об обработке истекшей транзакции
            await self.event_service.publish(EventPayload(
                event_type=EventType.TRANSACTION_UPDATED,
                data={
                    "transaction_id": transaction.id,
                    "status": transaction.status,
                    "reason": "expired",
                    "previous_status": transaction.status,
                    "expiration_date": transaction.expiration_date.isoformat() if transaction.expiration_date else None
                }
            ))
            
        except Exception as e:
            logger.error(f"Ошибка при обработке истекшей транзакции {transaction_id}: {str(e)}")
            db.rollback()
            raise
    
    async def stop(self) -> None:
        """Остановка сервиса"""
        self._running = False
        logger.info("Сервис обработки истекших транзакций остановлен")

# Синглтон для сервиса обработки истекших транзакций
_transaction_timeout_service_instance = None

async def get_transaction_timeout_service() -> TransactionTimeoutService:
    """
    Получение экземпляра сервиса обработки истекших транзакций
    
    Returns:
        Экземпляр TransactionTimeoutService
    """
    global _transaction_timeout_service_instance
    
    if _transaction_timeout_service_instance is None:
        _transaction_timeout_service_instance = TransactionTimeoutService()
        await _transaction_timeout_service_instance.initialize()
    
    return _transaction_timeout_service_instance

async def setup_transaction_timeout_service() -> None:
    """
    Настройка сервиса обработки истекших транзакций
    """
    await get_transaction_timeout_service() 