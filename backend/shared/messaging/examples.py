"""
Модуль с примерами использования RabbitMQ.

Данный модуль содержит примеры использования различных шаблонов и сценариев работы с RabbitMQ.
Эти примеры могут быть использованы как справочный материал при разработке.
"""
import asyncio
import logging
from typing import Dict, Any

from .connection import RabbitMQConnection
from .producer import MessageProducer
from .consumer import MessageConsumer
from .patterns import RPC, PubSub, WorkQueue, EventTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#
# Пример 1: Простая публикация и обработка сообщений
#
async def simple_messaging_example():
    """Пример простой публикации и обработки сообщений"""
    
    # Подключение к RabbitMQ
    connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
    await connection.connect()
    
    # Создаем продюсера и консьюмера
    producer = MessageProducer(connection)
    consumer = MessageConsumer(connection)
    
    # Определяем обработчик сообщений
    async def message_handler(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
        logger.info(f"Получено сообщение: {message}")
        logger.info(f"Заголовки: {headers}")
        return True
    
    # Подписываемся на очередь
    consumer_tag = await consumer.subscribe(
        queue_name="example_queue",
        handler=message_handler
    )
    
    # Отправляем несколько сообщений
    for i in range(3):
        message_id = await producer.publish_to_queue(
            queue_name="example_queue",
            message_data={"index": i, "message": f"Тестовое сообщение {i}"}
        )
        logger.info(f"Отправлено сообщение {message_id}")
    
    # Ждем некоторое время для обработки сообщений
    await asyncio.sleep(2)
    
    # Отменяем подписку и закрываем соединение
    await consumer.cancel_subscription("example_queue", consumer_tag)
    await connection.close()

#
# Пример 2: Использование шаблона Publish/Subscribe с событиями
#
async def pub_sub_example():
    """Пример использования шаблона Publish/Subscribe"""
    
    # Подключение к RabbitMQ
    connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
    await connection.connect()
    
    # Создаем клиента для работы с событиями
    pubsub = PubSub(connection, "example_service")
    
    # Обработчик для событий пользователя
    async def user_event_handler(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
        event_type = headers.get("event_type", "unknown")
        logger.info(f"Получено событие пользователя: {event_type}")
        logger.info(f"Данные события: {message}")
        return True
    
    # Обработчик для событий торговли
    async def trade_event_handler(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
        event_type = headers.get("event_type", "unknown")
        logger.info(f"Получено событие торговли: {event_type}")
        logger.info(f"Данные события: {message}")
        return True
    
    # Подписываемся на события
    await pubsub.subscribe_to_event("user.*", user_event_handler)
    await pubsub.subscribe_to_event("trade.*", trade_event_handler)
    
    # Публикуем несколько событий
    await pubsub.publish_event(
        EventTypes.USER_REGISTERED, 
        {"user_id": 123, "username": "gametrader1"}
    )
    
    await pubsub.publish_event(
        EventTypes.TRADE_CREATED, 
        {"trade_id": 456, "seller_id": 123, "buyer_id": 789}
    )
    
    # Ждем некоторое время для обработки событий
    await asyncio.sleep(2)
    
    # Отменяем подписки
    await pubsub.unsubscribe_from_event("user.*")
    await pubsub.unsubscribe_from_event("trade.*")
    
    # Закрываем соединение
    await connection.close()

#
# Пример 3: Использование шаблона RPC для удаленного вызова методов
#
async def rpc_example():
    """Пример использования шаблона RPC"""
    
    # Подключение к RabbitMQ
    connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
    await connection.connect()
    
    # Создаем RPC сервер
    rpc_server = RPC(connection, "auth_service")
    
    # Определяем метод для удаленного вызова
    async def authenticate_user(params: Dict[str, Any]) -> Dict[str, Any]:
        username = params.get("username")
        password = params.get("password")
        
        # В реальном сервисе здесь была бы аутентификация
        if username == "admin" and password == "admin123":
            return {"success": True, "user_id": 1, "role": "admin"}
        else:
            return {"success": False, "error": "Неверные учетные данные"}
    
    # Регистрируем метод
    await rpc_server.register_method("authenticate", authenticate_user)
    
    # Создаем RPC клиент
    rpc_client = RPC(connection, "marketplace_service")
    
    # Вызываем удаленный метод
    try:
        # Правильные учетные данные
        result = await rpc_client.call_method(
            "auth_service", 
            "authenticate", 
            {"username": "admin", "password": "admin123"}
        )
        logger.info(f"Результат аутентификации: {result}")
        
        # Неправильные учетные данные
        result = await rpc_client.call_method(
            "auth_service", 
            "authenticate", 
            {"username": "user", "password": "wrongpass"}
        )
        logger.info(f"Результат аутентификации: {result}")
    except Exception as e:
        logger.error(f"Ошибка при вызове RPC: {str(e)}")
    
    # Закрываем соединение
    await connection.close()

#
# Пример 4: Использование шаблона Work Queue для распределения задач
#
async def work_queue_example():
    """Пример использования шаблона Work Queue"""
    
    # Подключение к RabbitMQ
    connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
    await connection.connect()
    
    # Создаем очередь задач
    work_queue = WorkQueue(connection)
    
    # Определяем обработчик задач
    async def task_handler(task: Dict[str, Any], headers: Dict[str, Any]) -> bool:
        task_id = task.get("task_id", "unknown")
        logger.info(f"Обработка задачи {task_id}")
        
        # Имитируем выполнение задачи
        await asyncio.sleep(1)
        
        logger.info(f"Задача {task_id} выполнена")
        return True
    
    # Запускаем обработку задач
    consumer_tag = await work_queue.process_tasks(
        queue_name="tasks",
        handler=task_handler,
        prefetch_count=2  # Получаем по 2 задачи одновременно
    )
    
    # Добавляем задачи в очередь
    for i in range(5):
        await work_queue.add_task(
            queue_name="tasks",
            task_data={"task_id": i, "description": f"Задача {i}"}
        )
        logger.info(f"Задача {i} добавлена в очередь")
    
    # Ждем выполнения всех задач
    await asyncio.sleep(5)
    
    # Останавливаем обработку
    await work_queue.stop_processing("tasks", consumer_tag)
    
    # Закрываем соединение
    await connection.close()

# Основная функция для запуска примеров
async def run_examples():
    """Запускает все примеры по очереди"""
    
    logger.info("Запуск примера простой публикации и обработки сообщений")
    await simple_messaging_example()
    
    logger.info("\nЗапуск примера Publish/Subscribe")
    await pub_sub_example()
    
    logger.info("\nЗапуск примера RPC")
    await rpc_example()
    
    logger.info("\nЗапуск примера Work Queue")
    await work_queue_example()

# Этот код выполняется при запуске файла как скрипта
if __name__ == "__main__":
    asyncio.run(run_examples()) 