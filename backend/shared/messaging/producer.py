"""
Модуль для отправки сообщений в очереди RabbitMQ.
"""
import json
import uuid
import logging
import aio_pika
from aio_pika import Message, DeliveryMode
from typing import Dict, Any, Optional
from datetime import datetime

from .connection import RabbitMQConnection, connection_required

logger = logging.getLogger(__name__)

class MessageProducer:
    """
    Класс для отправки сообщений в очереди RabbitMQ.
    
    Предоставляет методы для публикации сообщений в различные очереди
    и обменники (exchanges) RabbitMQ.
    """
    
    def __init__(self, connection: RabbitMQConnection):
        """
        Инициализирует продюсера сообщений.
        
        Args:
            connection: Соединение с RabbitMQ.
        """
        self.connection = connection
        
    @connection_required
    async def publish_message(
        self,
        exchange_name: str,
        routing_key: str,
        message_data: Dict[str, Any],
        message_id: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        persistent: bool = True,
        priority: Optional[int] = None
    ) -> str:
        """
        Публикует сообщение в обменник RabbitMQ.
        
        Args:
            exchange_name: Имя обменника.
            routing_key: Ключ маршрутизации.
            message_data: Данные сообщения в виде словаря.
            message_id: ID сообщения (если None, генерируется автоматически).
            headers: Дополнительные заголовки для сообщения.
            persistent: Флаг сохранения сообщения (True для гарантии доставки).
            priority: Приоритет сообщения (0-9, где 9 - наивысший).
            
        Returns:
            str: ID отправленного сообщения.
        """
        # Получаем канал
        channel = await self.connection.get_channel()
        
        # Создаем обменник, если его нет
        exchange = await channel.declare_exchange(
            name=exchange_name,
            type=aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Генерируем ID сообщения, если не указан
        if not message_id:
            message_id = str(uuid.uuid4())
            
        # Подготавливаем заголовки по умолчанию
        default_headers = {
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": routing_key.split(".")[-1] if "." in routing_key else routing_key
        }
        
        # Объединяем с пользовательскими заголовками
        if headers:
            default_headers.update(headers)
            
        # Создаем сообщение
        message = Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            message_id=message_id,
            headers=default_headers,
            delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT,
            priority=priority
        )
        
        # Публикуем сообщение
        await exchange.publish(message, routing_key=routing_key)
        
        logger.info(f"Сообщение {message_id} опубликовано в {exchange_name} с ключом {routing_key}")
        return message_id
        
    @connection_required
    async def publish_to_queue(
        self,
        queue_name: str,
        message_data: Dict[str, Any],
        message_id: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        persistent: bool = True,
        priority: Optional[int] = None
    ) -> str:
        """
        Публикует сообщение напрямую в очередь RabbitMQ.
        
        Args:
            queue_name: Имя очереди.
            message_data: Данные сообщения в виде словаря.
            message_id: ID сообщения (если None, генерируется автоматически).
            headers: Дополнительные заголовки для сообщения.
            persistent: Флаг сохранения сообщения (True для гарантии доставки).
            priority: Приоритет сообщения (0-9, где 9 - наивысший).
            
        Returns:
            str: ID отправленного сообщения.
        """
        # Получаем канал
        channel = await self.connection.get_channel()
        
        # Создаем очередь, если её нет
        queue = await channel.declare_queue(
            name=queue_name,
            durable=True
        )
        
        # Генерируем ID сообщения, если не указан
        if not message_id:
            message_id = str(uuid.uuid4())
            
        # Подготавливаем заголовки по умолчанию
        default_headers = {
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": queue_name
        }
        
        # Объединяем с пользовательскими заголовками
        if headers:
            default_headers.update(headers)
            
        # Создаем сообщение
        message = Message(
            body=json.dumps(message_data).encode(),
            content_type="application/json",
            message_id=message_id,
            headers=default_headers,
            delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT,
            priority=priority
        )
        
        # Публикуем сообщение напрямую в очередь
        await channel.default_exchange.publish(message, routing_key=queue_name)
        
        logger.info(f"Сообщение {message_id} опубликовано в очередь {queue_name}")
        return message_id 