"""
Модуль для интеграции с RabbitMQ в сервисе.

Этот модуль предоставляет функции для инициализации и работы с RabbitMQ
в контексте FastAPI приложения.
"""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable, TypeVar

from shared.messaging.connection import RabbitMQConnection
from shared.messaging.producer import MessageProducer
from shared.messaging.consumer import MessageConsumer, MessageHandler
from shared.messaging.patterns import RPC, PubSub, WorkQueue, EventTypes

from .config import settings

logger = logging.getLogger(__name__)

# Создаем соединение с RabbitMQ на уровне модуля
rabbitmq_connection = RabbitMQConnection(settings.RABBITMQ_URL)

# Создаем экземпляры высокоуровневых клиентов
producer = None
consumer = None
rpc = None
pubsub = None
work_queue = None

async def initialize_rabbitmq():
    """
    Инициализирует соединение с RabbitMQ и создает клиентов для работы с ним.
    
    Вызывается при запуске приложения.
    """
    global producer, consumer, rpc, pubsub, work_queue
    
    try:
        logger.info(f"Инициализация соединения с RabbitMQ: {settings.RABBITMQ_URL}")
        await rabbitmq_connection.connect()
        
        # Создаем клиентов для работы с RabbitMQ
        producer = MessageProducer(rabbitmq_connection)
        consumer = MessageConsumer(rabbitmq_connection)
        rpc = RPC(rabbitmq_connection, settings.APP_NAME.lower().replace(' ', '_'))
        pubsub = PubSub(rabbitmq_connection, settings.APP_NAME.lower().replace(' ', '_'))
        work_queue = WorkQueue(rabbitmq_connection)
        
        logger.info("Соединение с RabbitMQ успешно установлено")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации RabbitMQ: {str(e)}")
        return False

async def close_rabbitmq():
    """
    Закрывает соединение с RabbitMQ.
    
    Вызывается при остановке приложения.
    """
    try:
        # Отменяем все подписки
        if consumer:
            await consumer.cancel_all_subscriptions()
        
        # Закрываем соединение
        await rabbitmq_connection.close()
        logger.info("Соединение с RabbitMQ закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с RabbitMQ: {str(e)}")

async def publish_event(event_type: str, data: Dict[str, Any]) -> Optional[str]:
    """
    Публикует событие в RabbitMQ.
    
    Args:
        event_type: Тип события (см. EventTypes).
        data: Данные события.
        
    Returns:
        Optional[str]: ID сообщения или None в случае ошибки.
    """
    if not pubsub:
        logger.error("PubSub клиент не инициализирован")
        return None
    
    try:
        return await pubsub.publish_event(event_type, data)
    except Exception as e:
        logger.error(f"Ошибка при публикации события {event_type}: {str(e)}")
        return None

async def register_event_handler(
    event_type: str, 
    handler: MessageHandler
) -> bool:
    """
    Регистрирует обработчик событий.
    
    Args:
        event_type: Тип события или шаблон (например, "user.*").
        handler: Функция-обработчик события.
        
    Returns:
        bool: True в случае успеха, False в случае ошибки.
    """
    if not pubsub:
        logger.error("PubSub клиент не инициализирован")
        return False
    
    try:
        await pubsub.subscribe_to_event(event_type, handler)
        logger.info(f"Обработчик для события '{event_type}' зарегистрирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчика события {event_type}: {str(e)}")
        return False

async def register_rpc_method(
    method_name: str, 
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]
) -> bool:
    """
    Регистрирует метод RPC.
    
    Args:
        method_name: Имя метода.
        handler: Функция-обработчик метода.
        
    Returns:
        bool: True в случае успеха, False в случае ошибки.
    """
    if not rpc:
        logger.error("RPC клиент не инициализирован")
        return False
    
    try:
        await rpc.register_method(method_name, handler)
        logger.info(f"RPC метод '{method_name}' зарегистрирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при регистрации RPC метода {method_name}: {str(e)}")
        return False

async def call_remote_method(
    service_name: str, 
    method_name: str, 
    params: Dict[str, Any], 
    timeout: float = 30.0
) -> Optional[Any]:
    """
    Вызывает удаленный метод.
    
    Args:
        service_name: Имя удаленного сервиса.
        method_name: Имя удаленного метода.
        params: Параметры для метода.
        timeout: Таймаут ожидания ответа в секундах.
        
    Returns:
        Optional[Any]: Результат вызова или None в случае ошибки.
    """
    if not rpc:
        logger.error("RPC клиент не инициализирован")
        return None
    
    try:
        return await rpc.call_method(service_name, method_name, params, timeout)
    except Exception as e:
        logger.error(f"Ошибка при вызове метода {service_name}.{method_name}: {str(e)}")
        return None

async def add_task(
    queue_name: str, 
    task_data: Dict[str, Any],
    priority: Optional[int] = None
) -> Optional[str]:
    """
    Добавляет задачу в очередь.
    
    Args:
        queue_name: Имя очереди задач.
        task_data: Данные задачи.
        priority: Приоритет задачи (0-9).
        
    Returns:
        Optional[str]: ID задачи или None в случае ошибки.
    """
    if not work_queue:
        logger.error("Work Queue клиент не инициализирован")
        return None
    
    try:
        return await work_queue.add_task(queue_name, task_data, priority)
    except Exception as e:
        logger.error(f"Ошибка при добавлении задачи в очередь {queue_name}: {str(e)}")
        return None

async def register_task_processor(
    queue_name: str, 
    handler: MessageHandler,
    prefetch_count: int = 1
) -> bool:
    """
    Регистрирует обработчик задач.
    
    Args:
        queue_name: Имя очереди задач.
        handler: Функция-обработчик задач.
        prefetch_count: Количество задач, получаемых одновременно.
        
    Returns:
        bool: True в случае успеха, False в случае ошибки.
    """
    if not work_queue:
        logger.error("Work Queue клиент не инициализирован")
        return False
    
    try:
        await work_queue.process_tasks(queue_name, handler, prefetch_count=prefetch_count)
        logger.info(f"Обработчик для очереди задач '{queue_name}' зарегистрирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчика задач для очереди {queue_name}: {str(e)}")
        return False 