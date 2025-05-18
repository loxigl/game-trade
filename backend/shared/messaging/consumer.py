"""
Модуль для получения и обработки сообщений из очередей RabbitMQ.
"""
import json
import logging
import asyncio
import aio_pika
from aio_pika import IncomingMessage
from typing import Dict, Any, Callable, Coroutine, Optional, List, Tuple
from functools import partial

from .connection import RabbitMQConnection, connection_required

logger = logging.getLogger(__name__)

# Тип для обработчика сообщений
MessageHandler = Callable[[Dict[str, Any], Dict[str, Any]], Coroutine[Any, Any, bool]]

class MessageConsumer:
    """
    Класс для получения и обработки сообщений из очередей RabbitMQ.
    
    Предоставляет методы для подписки на очереди и обработки входящих сообщений 
    с возможностью повторной обработки сообщений в случае ошибок.
    """
    
    def __init__(self, connection: RabbitMQConnection):
        """
        Инициализирует потребителя сообщений.
        
        Args:
            connection: Соединение с RabbitMQ.
        """
        self.connection = connection
        self.active_consumers: List[Tuple[str, str]] = []  # (queue_name, consumer_tag)
        
    @connection_required
    async def setup_dlq(self, queue_name: str) -> Tuple[aio_pika.Queue, aio_pika.Queue]:
        """
        Настраивает очередь и соответствующую dead-letter очередь.
        
        Args:
            queue_name: Имя основной очереди.
            
        Returns:
            Tuple[aio_pika.Queue, aio_pika.Queue]: Основная очередь и DLQ.
        """
        channel = await self.connection.get_channel()
        
        # Настраиваем dead-letter обменник
        dlx_name = f"{queue_name}.dlx"
        dlx = await channel.declare_exchange(
            name=dlx_name,
            type=aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # Настраиваем dead-letter очередь
        dlq_name = f"{queue_name}.dlq"
        dlq = await channel.declare_queue(
            name=dlq_name,
            durable=True
        )
        
        # Связываем DLQ с DLX
        await dlq.bind(dlx, routing_key=queue_name)
        
        # Настраиваем основную очередь с DLX
        queue = await channel.declare_queue(
            name=queue_name,
            durable=True,
            arguments={
                'x-dead-letter-exchange': dlx_name,
                'x-dead-letter-routing-key': queue_name,
                'x-message-ttl': 1000 * 60 * 60 * 24,  # 24 часа
            }
        )
        
        return queue, dlq
    
    async def process_message(
        self, 
        message: IncomingMessage, 
        handler: MessageHandler,
        max_retries: int = 3
    ) -> None:
        """
        Обрабатывает сообщение с возможностью повторных попыток.
        
        Args:
            message: Входящее сообщение RabbitMQ.
            handler: Функция обработчик сообщения.
            max_retries: Максимальное количество попыток обработки.
        """
        async with message.process():
            try:
                # Декодируем сообщение
                message_data = json.loads(message.body.decode())
                headers = message.headers or {}
                
                # Проверяем, есть ли информация о попытках
                retry_count = headers.get('x-retry-count', 0)
                
                logger.info(f"Обработка сообщения {message.message_id}, попытка {retry_count+1}/{max_retries+1}")
                
                # Вызываем обработчик
                success = await handler(message_data, headers)
                
                if not success:
                    if retry_count < max_retries:
                        # Переотправляем сообщение с увеличенным счетчиком попыток
                        headers['x-retry-count'] = retry_count + 1
                        
                        # Отправляем в ту же очередь через некоторое время
                        await asyncio.sleep(min(10 * (2 ** retry_count), 300))  # Экспоненциальное увеличение задержки
                        
                        # Переотправка сообщения
                        await message.nack(requeue=True)
                        logger.warning(f"Сообщение {message.message_id} не обработано. Переотправка, попытка {retry_count+2}")
                    else:
                        # Превышено количество попыток, отправляем в DLQ
                        logger.error(f"Сообщение {message.message_id} не обработано после {max_retries+1} попыток. Отправка в DLQ.")
                        await message.reject()
                else:
                    logger.info(f"Сообщение {message.message_id} успешно обработано")
                    
            except Exception as e:
                # В случае исключения во время обработки
                logger.exception(f"Ошибка при обработке сообщения {message.message_id}: {str(e)}")
                
                # Проверяем, можно ли повторить
                retry_count = message.headers.get('x-retry-count', 0) if message.headers else 0
                
                if retry_count < max_retries:
                    await message.nack(requeue=True)
                    logger.warning(f"Сообщение {message.message_id} вернулось в очередь для повторной обработки")
                else:
                    await message.reject()
                    logger.error(f"Сообщение {message.message_id} отклонено после {max_retries+1} попыток")
    
    @connection_required
    async def subscribe(
        self, 
        queue_name: str, 
        handler: MessageHandler, 
        max_retries: int = 3,
        prefetch_count: int = 10,
        setup_dlq: bool = True
    ) -> str:
        """
        Подписывается на очередь и начинает обработку сообщений.
        
        Args:
            queue_name: Имя очереди.
            handler: Функция обработчик сообщения.
            max_retries: Максимальное количество попыток обработки.
            prefetch_count: Количество сообщений, получаемых одновременно.
            setup_dlq: Флаг создания dead-letter очереди.
            
        Returns:
            str: Тег потребителя.
        """
        channel = await self.connection.get_channel()
        
        # Устанавливаем prefetch_count
        await channel.set_qos(prefetch_count=prefetch_count)
        
        # Настраиваем очередь и DLQ если требуется
        if setup_dlq:
            queue, _ = await self.setup_dlq(queue_name)
        else:
            queue = await channel.declare_queue(name=queue_name, durable=True)
        
        # Создаем обработчик с учетом повторных попыток
        message_processor = partial(self.process_message, handler=handler, max_retries=max_retries)
        
        # Подписываемся на очередь
        consumer_tag = await queue.consume(message_processor)
        
        self.active_consumers.append((queue_name, consumer_tag))
        logger.info(f"Подписка на очередь {queue_name} установлена с тегом {consumer_tag}")
        
        return consumer_tag
        
    @connection_required
    async def subscribe_to_topic(
        self, 
        exchange_name: str,
        routing_key: str,
        handler: MessageHandler,
        queue_name: Optional[str] = None,
        max_retries: int = 3,
        prefetch_count: int = 10,
        setup_dlq: bool = True
    ) -> str:
        """
        Подписывается на обменник по заданному ключу маршрутизации.
        
        Args:
            exchange_name: Имя обменника.
            routing_key: Ключ маршрутизации (поддерживает шаблоны).
            handler: Функция обработчик сообщения.
            queue_name: Имя очереди (если None, создается уникальная очередь).
            max_retries: Максимальное количество попыток обработки.
            prefetch_count: Количество сообщений, получаемых одновременно.
            setup_dlq: Флаг создания dead-letter очереди.
            
        Returns:
            str: Тег потребителя.
        """
        channel = await self.connection.get_channel()
        
        # Устанавливаем prefetch_count
        await channel.set_qos(prefetch_count=prefetch_count)
        
        # Создаем обменник
        exchange = await channel.declare_exchange(
            name=exchange_name,
            type=aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Если имя очереди не указано, создаем временную очередь
        if queue_name is None:
            # Для топика с шаблоном создаем уникальное имя очереди
            queue_name = f"{exchange_name}.{routing_key.replace('*', 'star').replace('#', 'hash')}"
        
        # Настраиваем очередь и DLQ если требуется
        if setup_dlq:
            queue, _ = await self.setup_dlq(queue_name)
        else:
            queue = await channel.declare_queue(name=queue_name, durable=True)
        
        # Привязываем очередь к обменнику с заданным ключом маршрутизации
        await queue.bind(exchange, routing_key=routing_key)
        
        # Создаем обработчик с учетом повторных попыток
        message_processor = partial(self.process_message, handler=handler, max_retries=max_retries)
        
        # Подписываемся на очередь
        consumer_tag = await queue.consume(message_processor)
        
        self.active_consumers.append((queue_name, consumer_tag))
        logger.info(f"Подписка на обменник {exchange_name} с ключом {routing_key} установлена, очередь {queue_name}, тег {consumer_tag}")
        
        return consumer_tag
    
    @connection_required
    async def cancel_subscription(self, queue_name: str, consumer_tag: str) -> None:
        """
        Отменяет подписку на очередь.
        
        Args:
            queue_name: Имя очереди.
            consumer_tag: Тег потребителя.
        """
        channel = await self.connection.get_channel()
        await channel.basic_cancel(consumer_tag)
        
        if (queue_name, consumer_tag) in self.active_consumers:
            self.active_consumers.remove((queue_name, consumer_tag))
            
        logger.info(f"Подписка на очередь {queue_name} с тегом {consumer_tag} отменена")
    
    async def cancel_all_subscriptions(self) -> None:
        """
        Отменяет все активные подписки.
        """
        for queue_name, consumer_tag in self.active_consumers.copy():
            await self.cancel_subscription(queue_name, consumer_tag)
            
        logger.info("Все подписки отменены") 