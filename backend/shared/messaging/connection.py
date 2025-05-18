"""
Модуль для установления и управления соединениями с RabbitMQ.
"""
import aio_pika
import asyncio
import logging
from typing import Optional, Dict, Any
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class RabbitMQConnection:
    """
    Класс для управления соединением с RabbitMQ.
    
    Обеспечивает асинхронное соединение с RabbitMQ, управление каналами
    и восстановление соединения в случае ошибок.
    """
    def __init__(self, connection_url: str):
        """
        Инициализирует соединение с RabbitMQ.
        
        Args:
            connection_url: URL для подключения к RabbitMQ (например, 'amqp://guest:guest@localhost:5672/')
        """
        self.connection_url = connection_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self._lock = asyncio.Lock()
        
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True
    )
    async def connect(self) -> None:
        """
        Устанавливает соединение с RabbitMQ с механизмом повторных попыток.
        
        Raises:
            Exception: Если не удалось установить соединение после нескольких попыток.
        """
        async with self._lock:
            if self.connection and not self.connection.is_closed:
                return
            
            logger.info(f"Подключение к RabbitMQ: {self.connection_url}")
            self.connection = await aio_pika.connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            logger.info("Соединение с RabbitMQ установлено успешно")
    
    async def get_channel(self) -> aio_pika.Channel:
        """
        Возвращает активный канал, при необходимости создавая новое соединение.
        
        Returns:
            aio_pika.Channel: Активный канал RabbitMQ.
        """
        if not self.connection or self.connection.is_closed:
            await self.connect()
        
        if not self.channel or self.channel.is_closed:
            self.channel = await self.connection.channel()
            
        return self.channel
    
    async def close(self) -> None:
        """
        Закрывает соединение с RabbitMQ.
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Соединение с RabbitMQ закрыто")
    
    async def __aenter__(self) -> 'RabbitMQ':
        """
        Контекстный менеджер для использования в async with.
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Закрывает соединение при выходе из контекстного менеджера.
        """
        await self.close()


def connection_required(func):
    """
    Декоратор, который гарантирует наличие соединения перед выполнением функции.
    
    Args:
        func: Асинхронная функция, требующая соединения с RabbitMQ.
        
    Returns:
        Обертка вокруг оригинальной функции.
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'connection') or not self.connection or self.connection.is_closed:
            await self.connect()
        return await func(self, *args, **kwargs)
    return wrapper 