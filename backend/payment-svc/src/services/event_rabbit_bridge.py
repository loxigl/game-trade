"""
Мост между системой событий и RabbitMQ
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional

from .event_service import EventService, EventType, EventPayload, get_event_service
from .rabbitmq_service import RabbitMQService, get_rabbitmq_service

logger = logging.getLogger(__name__)

class EventRabbitBridge:
    """
    Мост для передачи событий из системы событий в RabbitMQ
    
    Этот класс подписывается на события в EventService и публикует их в RabbitMQ
    для уведомления других сервисов.
    """
    
    def __init__(self):
        """Инициализация моста между событиями и RabbitMQ"""
        self.event_service = get_event_service()
        self.rabbitmq_service = get_rabbitmq_service()
        self._initialized = False
        
        # Маппинг типов событий на обменники и ключи маршрутизации
        self.routing_map = {
            # События транзакций
            EventType.TRANSACTION_CREATED: ("payment", "transaction.created"),
            EventType.TRANSACTION_UPDATED: ("payment", "transaction.updated"),
            EventType.TRANSACTION_COMPLETED: ("payment", "transaction.completed"),
            EventType.TRANSACTION_REFUNDED: ("payment", "transaction.refunded"),
            EventType.TRANSACTION_DISPUTED: ("payment", "transaction.disputed"),
            EventType.TRANSACTION_CANCELED: ("payment", "transaction.canceled"),
            EventType.TRANSACTION_FAILED: ("payment", "transaction.failed"),
            
            # События Escrow
            EventType.ESCROW_FUNDS_HELD: ("payment", "escrow.funds_held"),
            EventType.ESCROW_FUNDS_RELEASED: ("payment", "escrow.funds_released"),
            EventType.ESCROW_FUNDS_REFUNDED: ("payment", "escrow.funds_refunded"),
            
            # События кошельков
            EventType.WALLET_CREATED: ("payment", "wallet.created"),
            EventType.WALLET_UPDATED: ("payment", "wallet.updated"),
            EventType.WALLET_BALANCE_CHANGED: ("payment", "wallet.balance_changed"),
            EventType.WALLET_BLOCKED: ("payment", "wallet.blocked"),
            EventType.WALLET_UNBLOCKED: ("payment", "wallet.unblocked"),
            EventType.WALLET_CLOSED: ("payment", "wallet.closed"),
        }
    
    async def initialize(self) -> None:
        """Инициализация моста и настройка обработчиков событий"""
        if self._initialized:
            return
        
        # Подписываемся на все события
        self.event_service.subscribe_to_all(self.handle_event)
        logger.info("Установлена подписка на все события в системе")
        
        self._initialized = True
    
    async def handle_event(self, event: EventPayload) -> None:
        """
        Обработчик событий из системы событий
        
        Args:
            event: Данные события
        """
        try:
            # Проверяем, нужно ли отправлять это событие в RabbitMQ
            if event.event_type not in self.routing_map:
                logger.debug(f"Событие {event.event_type} не настроено для публикации в RabbitMQ")
                return
            
            # Получаем настройки маршрутизации
            exchange_name, routing_key = self.routing_map[event.event_type]
            
            # Формируем сообщение
            message = {
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
            
            # Добавляем в корень сообщения важные данные для идентификации продажи
            transaction_events = [
                EventType.TRANSACTION_CREATED,
                EventType.TRANSACTION_UPDATED,
                EventType.TRANSACTION_COMPLETED,
                EventType.TRANSACTION_REFUNDED,
                EventType.TRANSACTION_DISPUTED,
                EventType.TRANSACTION_CANCELED,
                EventType.TRANSACTION_FAILED,
                EventType.ESCROW_FUNDS_HELD,
                EventType.ESCROW_FUNDS_RELEASED,
                EventType.ESCROW_FUNDS_REFUNDED
            ]
            
            if event.event_type in transaction_events:
                # Копируем важные поля из data в корень сообщения для лучшей доступности в marketplace-svc
                important_fields = ["transaction_id", "buyer_id", "seller_id", "listing_id", "item_id", "amount", "currency"]
                for field in important_fields:
                    if field in event.data:
                        message[field] = event.data[field]
                        
                # Обеспечиваем наличие transaction_id в корне сообщения
                if "transaction_id" in event.data:
                    logger.info(f"Добавлен transaction_id={event.data['transaction_id']} в корень сообщения для события {event.event_type.value}")
            
            # Отправляем в RabbitMQ
            await self.rabbitmq_service.publish(exchange_name, routing_key, message)
            logger.info(f"Событие {event.event_type.value} опубликовано в RabbitMQ с ключом {routing_key}")
            
        except Exception as e:
            logger.error(f"Ошибка при публикации события в RabbitMQ: {str(e)}")

    async def _event_to_rabbit(self, event: EventPayload) -> None:
        """
        Обработчик конвертации события в сообщение RabbitMQ
        
        Args:
            event: Данные события
        """
        # Получаем ключ маршрутизации из типа события
        routing_key = event.event_type.value
        
        # Подготавливаем сообщение
        message = {
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }
        
        # Добавляем transaction_id в корень сообщения для всех событий, связанных с транзакциями
        transaction_events = [
            EventType.TRANSACTION_CREATED,
            EventType.TRANSACTION_UPDATED,
            EventType.TRANSACTION_COMPLETED,
            EventType.TRANSACTION_REFUNDED,
            EventType.TRANSACTION_DISPUTED,
            EventType.TRANSACTION_CANCELED,
            EventType.TRANSACTION_FAILED,
            EventType.ESCROW_FUNDS_HELD,
            EventType.ESCROW_FUNDS_RELEASED,
            EventType.ESCROW_FUNDS_REFUNDED
        ]
        
        if event.event_type in transaction_events:
            if "transaction_id" in event.data:
                message["transaction_id"] = event.data["transaction_id"]
                logger.info(f"Добавлен transaction_id={event.data['transaction_id']} в корень сообщения для события {event.event_type.value}")
        
        # Публикуем сообщение
        await self.rabbitmq_service.publish(self.exchange_name, routing_key, message)
        
        logger.info(f"Событие {event.event_type.value} опубликовано в RabbitMQ с ключом {routing_key}")

# Синглтон для моста между событиями и RabbitMQ
_event_rabbit_bridge_instance = None

async def get_event_rabbit_bridge() -> EventRabbitBridge:
    """
    Получение экземпляра моста между событиями и RabbitMQ
    
    Returns:
        Экземпляр EventRabbitBridge
    """
    global _event_rabbit_bridge_instance
    
    if _event_rabbit_bridge_instance is None:
        _event_rabbit_bridge_instance = EventRabbitBridge()
        await _event_rabbit_bridge_instance.initialize()
    
    return _event_rabbit_bridge_instance

async def setup_event_rabbit_bridge() -> None:
    """
    Настройка моста между событиями и RabbitMQ
    """
    await get_event_rabbit_bridge() 