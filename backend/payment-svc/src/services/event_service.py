"""
Сервис управления событиями для транзакций и кошельков
"""
import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Callable, Awaitable, Optional, Set, Type
import asyncio
import json

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Типы событий для системы уведомлений"""
    # События транзакций
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_REFUNDED = "transaction.refunded"
    TRANSACTION_DISPUTED = "transaction.disputed"
    TRANSACTION_CANCELED = "transaction.canceled"
    TRANSACTION_FAILED = "transaction.failed"
    
    # События кошельков
    WALLET_CREATED = "wallet.created"
    WALLET_UPDATED = "wallet.updated"
    WALLET_BALANCE_CHANGED = "wallet.balance_changed"
    WALLET_BLOCKED = "wallet.blocked"
    WALLET_UNBLOCKED = "wallet.unblocked"
    WALLET_CLOSED = "wallet.closed"
    
    # События Escrow
    ESCROW_FUNDS_HELD = "escrow.funds_held"
    ESCROW_FUNDS_RELEASED = "escrow.funds_released"
    ESCROW_FUNDS_REFUNDED = "escrow.funds_refunded"
    
    # События для уведомлений
    NOTIFICATION_SENT = "notification.sent"

class EventPayload(BaseModel):
    """Базовая модель данных события"""
    event_type: EventType
    timestamp: datetime = datetime.utcnow()
    data: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Тип для обработчика событий
EventHandler = Callable[[EventPayload], Awaitable[None]]

class EventService:
    """
    Сервис для обработки событий в системе
    
    Реализует паттерн Publisher-Subscriber для асинхронного обмена сообщениями
    между различными компонентами системы
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._all_events_subscribers: List[EventHandler] = []
        self._event_history: List[EventPayload] = []
        self._max_history_size = 1000  # Максимальный размер истории событий
        self._initialized = True
        
        logger.info("EventService инициализирован")
    
    async def publish(self, event: EventPayload) -> None:
        """
        Публикация события в системе
        
        Args:
            event: Данные события
        """
        logger.debug(f"Публикация события: {event.event_type}")
        
        # Сохраняем событие в истории
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        # Вызываем обработчики для конкретного типа события
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Ошибка при обработке события {event.event_type}: {str(e)}")
        
        # Вызываем обработчики для всех событий
        for handler in self._all_events_subscribers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Ошибка при обработке события {event.event_type} в глобальном обработчике: {str(e)}")
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Подписка на события определенного типа
        
        Args:
            event_type: Тип события
            handler: Обработчик события
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.debug(f"Добавлена подписка на событие {event_type}")
    
    def subscribe_to_all(self, handler: EventHandler) -> None:
        """
        Подписка на все события
        
        Args:
            handler: Обработчик события
        """
        self._all_events_subscribers.append(handler)
        logger.debug(f"Добавлена подписка на все события")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Отмена подписки на события определенного типа
        
        Args:
            event_type: Тип события
            handler: Обработчик события
        """
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Удалена подписка на событие {event_type}")
    
    def unsubscribe_from_all(self, handler: EventHandler) -> None:
        """
        Отмена подписки на все события
        
        Args:
            handler: Обработчик события
        """
        if handler in self._all_events_subscribers:
            self._all_events_subscribers.remove(handler)
            logger.debug(f"Удалена подписка на все события")
    
    def get_event_history(self, event_type: Optional[EventType] = None) -> List[EventPayload]:
        """
        Получение истории событий
        
        Args:
            event_type: Тип события для фильтрации (если None, возвращается вся история)
            
        Returns:
            Список событий
        """
        if event_type is None:
            return self._event_history
        
        return [event for event in self._event_history if event.event_type == event_type]

# Синглтон для сервиса событий
def get_event_service() -> EventService:
    """
    Получение экземпляра сервиса событий
    
    Returns:
        Экземпляр сервиса событий
    """
    return EventService() 