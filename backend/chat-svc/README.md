# GameTrade Chat Service (chat-svc)

## Описание

**chat-svc** — микросервис для обмена сообщениями между пользователями платформы GameTrade. Поддерживает групповые и приватные чаты, интеграцию с marketplace, уведомления, модерацию, WebSocket для real-time общения и взаимодействует с другими сервисами через RabbitMQ.

---

## Архитектура
- **FastAPI** — REST и WebSocket API
- **PostgreSQL** — хранение чатов и сообщений
- **RabbitMQ** — события пользователей и marketplace
- **Redis** — кеширование и rate limiting (опционально)
- **Alembic** — миграции БД
- **Модули**: routes, services, models, schemas, config

---

## Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
cd backend/chat-svc
pip install -r requirements.txt
```

### 2. Переменные окружения
Создайте `.env` или настройте переменные окружения:
```
DATABASE_URL=postgresql://gametrade:gametrade@localhost:5432/chat_db
RABBITMQ_URL=amqp://gametrade:gametrade@localhost:5672/
AUTH_SERVICE_URL=http://localhost:8000
```

### 3. Миграции базы данных
```bash
alembic upgrade head
```
или через Docker Compose:
```bash
docker-compose run --rm chat-svc alembic upgrade head
```

### 4. Запуск сервиса
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload
```
или через Docker Compose:
```bash
docker-compose up chat-svc
```

---

## Основные переменные окружения
- `DATABASE_URL` — строка подключения к PostgreSQL
- `RABBITMQ_URL` — строка подключения к RabbitMQ
- `AUTH_SERVICE_URL` — URL сервиса аутентификации (auth-svc)

---

## Миграции
- Создание миграции:  
  `alembic revision --autogenerate -m "описание"`
- Применение миграций:  
  `alembic upgrade head`
- Откат:  
  `alembic downgrade -1`

---

## Основные API эндпоинты

### REST API
- `POST   /chats` — создать чат
- `GET    /chats` — получить список чатов пользователя
- `GET    /chats/{chat_id}` — получить чат по ID
- `PATCH  /chats/{chat_id}` — обновить чат
- `POST   /chats/{chat_id}/messages` — отправить сообщение
- `GET    /chats/{chat_id}/messages` — получить сообщения чата
- `PATCH  /chats/{chat_id}/messages/{message_id}` — редактировать сообщение
- `DELETE /chats/{chat_id}/messages/{message_id}` — удалить сообщение
- `POST   /chats/{chat_id}/read` — отметить сообщения как прочитанные
- `POST   /chats/{chat_id}/moderator` — назначить модератора (админ/модератор)
- `POST   /chats/{chat_id}/resolve` — разрешить спор (админ/модератор)
- `GET    /health` — проверка состояния сервиса

### WebSocket API
- `/ws?token=...` — универсальный WebSocket для событий и сообщений
- `/ws/chat/{chat_id}?token=...` — WebSocket для конкретного чата
- Поддерживаемые типы сообщений: `join_chat`, `leave_chat`, `typing`, `ping`, `new_message`, `user_joined`, `user_left`, `typing`, `error`, `pong`

---



## Интеграция
- **auth-svc** — валидация JWT токенов и получение профиля пользователя
- **RabbitMQ** — события о пользователях, marketplace, уведомления
- **WebSocket** — real-time обмен сообщениями и событиями
- **Docker/Kubernetes** — готовые манифесты для деплоя

---

## Безопасность
- JWT-аутентификация через auth-svc
- Проверка ролей и прав доступа
- Rate limiting (опционально через Redis)
- Валидация данных и ограничение размера сообщений
- Логирование событий и ошибок

---

## Контакты и поддержка
- Вопросы и баги: создавайте issue в репозитории
