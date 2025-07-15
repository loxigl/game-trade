# GameTrade Marketplace Service (marketplace-svc)

## Описание

**marketplace-svc** — микросервис для управления торговой площадкой GameTrade. Отвечает за объявления, категории, сделки, взаимодействие с пользователями, интеграцию с платежами и чатами. Реализован на FastAPI, использует PostgreSQL, RabbitMQ и поддерживает масштабируемую архитектуру.

---

## Архитектура
- **FastAPI** — REST API
- **PostgreSQL** — хранение объявлений, категорий, сделок
- **RabbitMQ** — события для интеграции с chat-svc, payment-svc и др.
- **Alembic** — миграции БД
- **Модули**: routers, services, models, schemas, config

---

## Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
cd backend/marketplace-svc
pip install -r requirements.txt
```

### 2. Переменные окружения
Создайте `.env` или настройте переменные окружения:
```
DATABASE_URL=postgresql://gametrade:gametrade@localhost:5432/marketplace_db
RABBITMQ_URL=amqp://gametrade:gametrade@localhost:5672/
AUTH_SERVICE_URL=http://localhost:8000
PAYMENT_SERVICE_URL=http://localhost:8002
```

### 3. Миграции базы данных
```bash
alembic upgrade head
```
или через Docker Compose:
```bash
docker-compose run --rm marketplace-svc alembic upgrade head
```

### 4. Запуск сервиса
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```
или через Docker Compose:
```bash
docker-compose up marketplace-svc
```

---

## Основные переменные окружения
- `DATABASE_URL` — строка подключения к PostgreSQL
- `RABBITMQ_URL` — строка подключения к RabbitMQ
- `AUTH_SERVICE_URL` — URL сервиса аутентификации
- `PAYMENT_SERVICE_URL` — URL сервиса платежей

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
- `GET    /categories` — список категорий
- `POST   /categories` — создать категорию (админ)
- `GET    /games` — список игр
- `POST   /games` — создать игру (админ)
- `GET    /listings` — поиск и фильтрация объявлений
- `POST   /listings` — создать объявление
- `GET    /listings/{id}` — получить объявление по ID
- `PATCH  /listings/{id}` — обновить объявление
- `DELETE /listings/{id}` — удалить объявление
- `GET    /orders` — список заказов пользователя
- `POST   /orders` — создать заказ
- `GET    /orders/{id}` — получить заказ по ID
- `PATCH  /orders/{id}` — обновить заказ
- `GET    /health` — проверка состояния сервиса

Полная OpenAPI-спецификация доступна по `/docs` при запуске сервиса.

---



---

## Интеграция
- **auth-svc** — аутентификация и получение профиля пользователя
- **payment-svc** — создание и отслеживание платежей
- **chat-svc** — создание чатов по сделкам
- **RabbitMQ** — события marketplace, уведомления
- **Docker/Kubernetes** — готовые манифесты для деплоя

---

## Безопасность
- JWT-аутентификация через auth-svc
- Проверка ролей и прав доступа
- Валидация данных и ограничение доступа к чужим объявлениям/заказам
- Логирование событий и ошибок

---

## Контакты и поддержка
- Вопросы и баги: создавайте issue в репозитории 