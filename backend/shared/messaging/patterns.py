"""
Модуль с шаблонами сообщений и общими сценариями использования RabbitMQ.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Coroutine, TypeVar, Generic, Union

from .connection import RabbitMQConnection
from .producer import MessageProducer
from .consumer import MessageConsumer, MessageHandler

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Типы событий в системе
class EventTypes:
    """Типы событий в системе"""
    
    # Пользовательские события
    USER_REGISTERED = "user.registered"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_UPDATED = "user.updated"
    
    # События для игровых ценностей
    ITEM_LISTED = "item.listed"
    ITEM_UPDATED = "item.updated"
    ITEM_REMOVED = "item.removed"
    
    # События для торговых операций
    TRADE_CREATED = "trade.created"
    TRADE_ACCEPTED = "trade.accepted"
    TRADE_REJECTED = "trade.rejected"
    TRADE_COMPLETED = "trade.completed"
    TRADE_CANCELED = "trade.canceled"
    
    # События для платежей
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    
    # События для сообщений чата
    MESSAGE_SENT = "message.sent"
    MESSAGE_READ = "message.read"
    MESSAGE_DELETED = "message.deleted"
    
    # Системные события
    SYSTEM_ERROR = "system.error"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_INFO = "system.info"


class RPC:
    """
    Класс для реализации шаблона RPC (Remote Procedure Call) через RabbitMQ.
    
    Предоставляет возможность вызывать методы на удаленных сервисах и получать результаты.
    """
    
    def __init__(self, connection: RabbitMQConnection, service_name: str):
        """
        Инициализирует RPC клиент/сервер.
        
        Args:
            connection: Соединение с RabbitMQ.
            service_name: Имя сервиса (для уникальной идентификации очередей).
        """
        self.connection = connection
        self.service_name = service_name
        self.producer = MessageProducer(connection)
        self.consumer = MessageConsumer(connection)
        self.response_queues = {}
        self.futures = {}
        
    async def register_method(self, method_name: str, handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, Any]]) -> str:
        """
        Регистрирует метод для удаленного вызова.
        
        Args:
            method_name: Имя метода.
            handler: Обработчик метода.
            
        Returns:
            str: Тег потребителя.
        """
        rpc_queue_name = f"rpc.{self.service_name}.{method_name}"
        
        async def rpc_handler(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
            try:
                reply_to = headers.get('reply_to')
                correlation_id = headers.get('correlation_id')
                
                if not reply_to or not correlation_id:
                    logger.error(f"RPC сообщение не содержит reply_to или correlation_id: {headers}")
                    return False
                
                # Вызываем обработчик метода
                result = await handler(message)
                
                # Отправляем результат обратно
                await self.producer.publish_to_queue(
                    queue_name=reply_to,
                    message_data={"result": result},
                    headers={"correlation_id": correlation_id}
                )
                return True
            except Exception as e:
                logger.exception(f"Ошибка при обработке RPC запроса: {str(e)}")
                # Отправляем ошибку обратно
                if 'reply_to' in headers and 'correlation_id' in headers:
                    await self.producer.publish_to_queue(
                        queue_name=headers['reply_to'],
                        message_data={"error": str(e)},
                        headers={"correlation_id": headers['correlation_id']}
                    )
                return False
        
        # Подписываемся на очередь RPC запросов
        return await self.consumer.subscribe(
            queue_name=rpc_queue_name,
            handler=rpc_handler,
            max_retries=0  # Для RPC не нужны повторы, результат уже может быть неактуальным
        )
    
    async def call_method(
        self, 
        service_name: str, 
        method_name: str, 
        params: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Any:
        """
        Вызывает удаленный метод и ожидает результат.
        
        Args:
            service_name: Имя целевого сервиса.
            method_name: Имя вызываемого метода.
            params: Параметры для метода.
            timeout: Таймаут ожидания в секундах.
            
        Returns:
            Any: Результат вызова метода.
            
        Raises:
            TimeoutError: Если ответ не получен в течение таймаута.
            Exception: Если удаленный метод вернул ошибку.
        """
        # Формируем имя очереди для RPC запросов
        rpc_queue_name = f"rpc.{service_name}.{method_name}"
        
        # Создаем временную очередь для ответа, если её еще нет
        if self.service_name not in self.response_queues:
            response_queue_name = f"rpc.response.{self.service_name}"
            channel = await self.connection.get_channel()
            response_queue = await channel.declare_queue(name=response_queue_name, durable=True)
            
            # Функция обработки ответов
            async def handle_response(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
                correlation_id = headers.get('correlation_id')
                if correlation_id and correlation_id in self.futures:
                    future = self.futures[correlation_id]
                    if not future.done():
                        if "error" in message:
                            future.set_exception(Exception(message["error"]))
                        else:
                            future.set_result(message.get("result"))
                    return True
                return False
            
            # Подписываемся на очередь ответов
            await self.consumer.subscribe(
                queue_name=response_queue_name,
                handler=handle_response,
                max_retries=0
            )
            
            self.response_queues[self.service_name] = response_queue_name
        
        response_queue_name = self.response_queues[self.service_name]
        
        # Создаем future для ожидания ответа
        future = asyncio.get_event_loop().create_future()
        correlation_id = await self.producer.publish_message(
            exchange_name="",  # Используем default exchange
            routing_key=rpc_queue_name,
            message_data=params,
            headers={
                "reply_to": response_queue_name,
                "correlation_id": str(id(future))
            }
        )
        
        # Сохраняем future для обработки ответа
        self.futures[str(id(future))] = future
        
        try:
            # Ожидаем результат с таймаутом
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            # Очищаем future из словаря
            self.futures.pop(str(id(future)), None)


class PubSub:
    """
    Класс для реализации шаблона Publish/Subscribe через RabbitMQ.
    
    Предоставляет возможность публиковать события и подписываться на них.
    """
    
    def __init__(self, connection: RabbitMQConnection, service_name: str):
        """
        Инициализирует Pub/Sub клиент.
        
        Args:
            connection: Соединение с RabbitMQ.
            service_name: Имя сервиса (для уникальной идентификации подписчиков).
        """
        self.connection = connection
        self.service_name = service_name
        self.producer = MessageProducer(connection)
        self.consumer = MessageConsumer(connection)
        self.subscriptions = {}
        
    async def publish_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        exchange_name: str = "events"
    ) -> str:
        """
        Публикует событие.
        
        Args:
            event_type: Тип события (используется как routing_key).
            event_data: Данные события.
            exchange_name: Имя обменника (по умолчанию "events").
            
        Returns:
            str: ID опубликованного сообщения.
        """
        return await self.producer.publish_message(
            exchange_name=exchange_name,
            routing_key=event_type,
            message_data=event_data,
            headers={"event_type": event_type}
        )
    
    async def subscribe_to_event(
        self, 
        event_type: str, 
        handler: MessageHandler,
        exchange_name: str = "events",
        max_retries: int = 3
    ) -> str:
        """
        Подписывается на событие.
        
        Args:
            event_type: Тип события (поддерживает шаблоны, например "user.*").
            handler: Обработчик события.
            exchange_name: Имя обменника (по умолчанию "events").
            max_retries: Максимальное количество попыток обработки.
            
        Returns:
            str: Тег подписки.
        """
        # Создаем уникальное имя очереди для подписчика
        queue_name = f"{exchange_name}.{self.service_name}.{event_type.replace('*', 'star').replace('#', 'hash')}"
        
        # Подписываемся на топик
        consumer_tag = await self.consumer.subscribe_to_topic(
            exchange_name=exchange_name,
            routing_key=event_type,
            handler=handler,
            queue_name=queue_name,
            max_retries=max_retries
        )
        
        # Сохраняем информацию о подписке
        self.subscriptions[event_type] = (queue_name, consumer_tag)
        
        return consumer_tag
    
    async def unsubscribe_from_event(self, event_type: str) -> None:
        """
        Отменяет подписку на событие.
        
        Args:
            event_type: Тип события.
        """
        if event_type in self.subscriptions:
            queue_name, consumer_tag = self.subscriptions[event_type]
            await self.consumer.cancel_subscription(queue_name, consumer_tag)
            del self.subscriptions[event_type]


class WorkQueue:
    """
    Класс для реализации шаблона Work Queue через RabbitMQ.
    
    Предоставляет возможность распределять задачи между несколькими обработчиками.
    """
    
    def __init__(self, connection: RabbitMQConnection):
        """
        Инициализирует Work Queue.
        
        Args:
            connection: Соединение с RabbitMQ.
        """
        self.connection = connection
        self.producer = MessageProducer(connection)
        self.consumer = MessageConsumer(connection)
        
    async def add_task(
        self, 
        queue_name: str, 
        task_data: Dict[str, Any],
        priority: Optional[int] = None
    ) -> str:
        """
        Добавляет задачу в очередь.
        
        Args:
            queue_name: Имя очереди.
            task_data: Данные задачи.
            priority: Приоритет задачи (0-9, где 9 - наивысший).
            
        Returns:
            str: ID задачи.
        """
        return await self.producer.publish_to_queue(
            queue_name=queue_name,
            message_data=task_data,
            headers={"task_type": queue_name},
            priority=priority
        )
    
    async def process_tasks(
        self, 
        queue_name: str, 
        handler: MessageHandler,
        max_retries: int = 3,
        prefetch_count: int = 1
    ) -> str:
        """
        Начинает обработку задач из очереди.
        
        Args:
            queue_name: Имя очереди.
            handler: Обработчик задач.
            max_retries: Максимальное количество попыток обработки.
            prefetch_count: Количество задач, которые обработчик может получить заранее.
            
        Returns:
            str: Тег потребителя.
        """
        return await self.consumer.subscribe(
            queue_name=queue_name,
            handler=handler,
            max_retries=max_retries,
            prefetch_count=prefetch_count
        )
        
    async def stop_processing(self, queue_name: str, consumer_tag: str) -> None:
        """
        Останавливает обработку задач.
        
        Args:
            queue_name: Имя очереди.
            consumer_tag: Тег потребителя.
        """
        await self.consumer.cancel_subscription(queue_name, consumer_tag) 