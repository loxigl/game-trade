"""
Сервис для работы с RabbitMQ
"""

import json
import aio_pika
import asyncio
from typing import Any, Dict, Optional, Callable
from functools import lru_cache
import logging
import os

logger = logging.getLogger(__name__)

class RabbitMQService:
    """
    Сервис для работы с RabbitMQ
    Позволяет публиковать сообщения и создавать потребителей
    """

    def __init__(self):
        """Инициализация сервиса"""
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://gametrade:gametrade@rabbitmq:5672/")
        self.connection = None
        self.channel = None
        self._connect_lock = asyncio.Lock()
        self._connection_attempts = 0
        self._max_connection_attempts = 5  # Максимальное количество попыток соединения

    async def connect(self) -> None:
        """
        Установка соединения с RabbitMQ
        """
        if self.connection is not None and not self.connection.is_closed:
            return

        async with self._connect_lock:
            if self.connection is not None and not self.connection.is_closed:
                return

            try:
                self._connection_attempts += 1
                logger.info(f"Connecting to RabbitMQ: {self.rabbitmq_url}")
                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    timeout=10
                )
                self.channel = await self.connection.channel()
                self._connection_attempts = 0
                logger.info("Connected to RabbitMQ")
            except Exception as e:
                logger.error(f"Error connecting to RabbitMQ: {str(e)}")
                if self._connection_attempts >= self._max_connection_attempts:
                    logger.error("Max connection attempts reached")
                    self._connection_attempts = 0
                    raise
                await asyncio.sleep(2)  # Задержка перед повторной попыткой
                await self.connect()

    async def close(self) -> None:
        """
        Закрытие соединения с RabbitMQ
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

    async def publish(self, exchange_name: str, routing_key: str, message: Dict[str, Any]) -> None:
        """
        Публикация сообщения в RabbitMQ

        Args:
            exchange_name: Имя обменника
            routing_key: Ключ маршрутизации
            message: Сообщение для публикации (будет преобразовано в JSON)
        """
        await self.connect()

        # Создаем обменник, если его нет
        exchange = await self.channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        # Преобразуем сообщение в JSON
        message_body = json.dumps(message).encode('utf-8')

        # Создаем и публикуем сообщение
        await exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )

        logger.info(f"Message published to {exchange_name} with routing key {routing_key}")

    async def create_consumer(
        self,
        exchange_name: str,
        queue_name: str,
        routing_key: str,
        callback: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Создание потребителя сообщений

        Args:
            exchange_name: Имя обменника
            queue_name: Имя очереди
            routing_key: Ключ маршрутизации
            callback: Функция обратного вызова для обработки полученных сообщений
        """
        await self.connect()

        # Создаем обменник
        exchange = await self.channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        # Создаем очередь
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True,
            auto_delete=False
        )

        # Привязываем очередь к обменнику
        await queue.bind(exchange, routing_key)

        async def process_message(message: aio_pika.IncomingMessage) -> None:
            """Обработка входящего сообщения"""
            async with message.process():
                try:
                    message_body = message.body.decode('utf-8')
                    message_data = json.loads(message_body)
                    await callback(message_data)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    # Возможно, стоит перенаправить в очередь "мертвых писем"

        # Запускаем потребителя
        await queue.consume(process_message)
        logger.info(f"Consumer created for queue {queue_name} with routing key {routing_key}")

@lru_cache
def get_rabbitmq_service() -> RabbitMQService:
    """
    Получение экземпляра сервиса RabbitMQ

    Returns:
        Экземпляр RabbitMQService
    """
    return RabbitMQService() 