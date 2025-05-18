# GameTrade Shared Libraries

В этой директории находятся общие библиотеки, используемые всеми микросервисами проекта GameTrade.

## Модуль для работы с RabbitMQ: `messaging`

Модуль `messaging` предоставляет унифицированный интерфейс для межсервисного взаимодействия через RabbitMQ.

### Установка

```bash
cd backend/shared
pip install -r requirements.txt
```

### Использование

#### Установка соединения

```python
from shared.messaging.connection import RabbitMQConnection

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Не забудьте закрыть соединение, когда оно больше не требуется
await connection.close()
```

#### Отправка сообщений (Producer)

```python
from shared.messaging.producer import MessageProducer
from shared.messaging.connection import RabbitMQConnection

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Создаем продюсера
producer = MessageProducer(connection)

# Отправляем сообщение напрямую в очередь
message_id = await producer.publish_to_queue(
    queue_name="example_queue",
    message_data={"key": "value", "message": "Hello World"}
)

# Отправляем сообщение через обменник
message_id = await producer.publish_message(
    exchange_name="events",
    routing_key="user.registered",
    message_data={"user_id": 123, "username": "gametrader1"}
)

# Закрываем соединение
await connection.close()
```

#### Получение сообщений (Consumer)

```python
from shared.messaging.consumer import MessageConsumer
from shared.messaging.connection import RabbitMQConnection
from typing import Dict, Any

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Создаем консьюмера
consumer = MessageConsumer(connection)

# Определяем обработчик сообщений
async def message_handler(message: Dict[str, Any], headers: Dict[str, Any]) -> bool:
    print(f"Получено сообщение: {message}")
    print(f"Заголовки: {headers}")
    # Возвращаем True, если сообщение успешно обработано
    return True

# Подписываемся на очередь
consumer_tag = await consumer.subscribe(
    queue_name="example_queue",
    handler=message_handler,
    max_retries=3  # Количество повторных попыток при ошибке
)

# ...

# Отменяем подписку, когда она больше не нужна
await consumer.cancel_subscription("example_queue", consumer_tag)

# Закрываем соединение
await connection.close()
```

### Высокоуровневые шаблоны обмена сообщениями

#### Publish/Subscribe (События)

```python
from shared.messaging.connection import RabbitMQConnection
from shared.messaging.patterns import PubSub, EventTypes

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Создаем клиента для работы с событиями
pubsub = PubSub(connection, "my_service")

# Подписываемся на события пользователя
await pubsub.subscribe_to_event("user.*", user_event_handler)

# Публикуем событие регистрации пользователя
await pubsub.publish_event(
    EventTypes.USER_REGISTERED, 
    {"user_id": 123, "username": "gametrader1"}
)

# ...

# Отменяем подписку
await pubsub.unsubscribe_from_event("user.*")

# Закрываем соединение
await connection.close()
```

#### Remote Procedure Call (RPC)

```python
from shared.messaging.connection import RabbitMQConnection
from shared.messaging.patterns import RPC

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Создаем RPC сервер
rpc_server = RPC(connection, "auth_service")

# Регистрируем метод для удаленного вызова
await rpc_server.register_method("authenticate", authenticate_user)

# Создаем RPC клиент
rpc_client = RPC(connection, "marketplace_service")

# Вызываем удаленный метод
result = await rpc_client.call_method(
    "auth_service", 
    "authenticate", 
    {"username": "admin", "password": "admin123"}
)

# Закрываем соединение
await connection.close()
```

#### Work Queue (Очереди задач)

```python
from shared.messaging.connection import RabbitMQConnection
from shared.messaging.patterns import WorkQueue

# Создаем соединение
connection = RabbitMQConnection("amqp://gametrade:gametrade@localhost:5672/")
await connection.connect()

# Создаем очередь задач
work_queue = WorkQueue(connection)

# Запускаем обработку задач
consumer_tag = await work_queue.process_tasks(
    queue_name="tasks",
    handler=task_handler,
    prefetch_count=2  # Получаем по 2 задачи одновременно
)

# Добавляем задачу в очередь
await work_queue.add_task(
    queue_name="tasks",
    task_data={"task_id": 1, "description": "Важная задача"}
)

# ...

# Останавливаем обработку
await work_queue.stop_processing("tasks", consumer_tag)

# Закрываем соединение
await connection.close()
```

### Типы событий

В модуле `patterns` определены стандартные типы событий, которые используются в системе:

```python
from shared.messaging.patterns import EventTypes

# Пользовательские события
EventTypes.USER_REGISTERED
EventTypes.USER_ACTIVATED
EventTypes.USER_DEACTIVATED
EventTypes.USER_UPDATED

# События для игровых ценностей
EventTypes.ITEM_LISTED
EventTypes.ITEM_UPDATED
EventTypes.ITEM_REMOVED

# События для торговых операций
EventTypes.TRADE_CREATED
EventTypes.TRADE_ACCEPTED
EventTypes.TRADE_REJECTED
EventTypes.TRADE_COMPLETED
EventTypes.TRADE_CANCELED

# События для платежей
EventTypes.PAYMENT_INITIATED
EventTypes.PAYMENT_COMPLETED
EventTypes.PAYMENT_FAILED

# События для сообщений чата
EventTypes.MESSAGE_SENT
EventTypes.MESSAGE_READ
EventTypes.MESSAGE_DELETED

# Системные события
EventTypes.SYSTEM_ERROR
EventTypes.SYSTEM_ALERT
EventTypes.SYSTEM_INFO
``` 