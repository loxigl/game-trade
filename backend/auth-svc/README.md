# GameTrade Auth Service (auth-svc)

## Описание

**auth-svc** — это микросервис аутентификации и авторизации пользователей для платформы GameTrade. Сервис реализован на FastAPI, использует PostgreSQL для хранения данных и Redis для управления сессиями и черным списком токенов. Поддерживает JWT, управление ролями, защиту аккаунтов и интеграцию с другими сервисами через RabbitMQ.

---

## Архитектура
- **FastAPI** — REST API
- **PostgreSQL** — хранение пользователей
- **Redis** — сессии, черный список токенов
- **RabbitMQ** — события пользователей
- **Alembic** — миграции БД
- **Модули**: routes, services, models, schemas, config

Подробнее см. [Документацию](./documentation.md).

---

## Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
cd backend/auth-svc
pip install -r requirements.txt
```

### 2. Переменные окружения
Создайте `.env` (см. пример ниже) или настройте переменные окружения:
```
DATABASE_URL=postgresql://gametrade:gametrade@localhost:5432/gametrade
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your_jwt_secret
RABBITMQ_URL=amqp://gametrade:gametrade@localhost:5672/
FRONTEND_URL=http://localhost:3000
```

### 3. Миграции базы данных
```bash
alembic upgrade head
```
или через Docker Compose:
```bash
docker-compose run --rm auth-svc alembic upgrade head
```

### 4. Запуск сервиса
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
или через Docker Compose:
```bash
docker-compose up auth-svc
```

---

## Основные переменные окружения
- `DATABASE_URL` — строка подключения к PostgreSQL
- `REDIS_URL` — строка подключения к Redis
- `JWT_SECRET` — секрет для подписи JWT
- `RABBITMQ_URL` — строка подключения к RabbitMQ
- `FRONTEND_URL` — URL фронтенда для email-ссылок

---

## Миграции
- Создание миграции:  
  `alembic revision --autogenerate -m "описание"`
- Применение миграций:  
  `alembic upgrade head`
- Откат:  
  `alembic downgrade -1`

Подробнее: [migrations/README](./migrations/README)

---

## Основные API эндпоинты
- `POST   /login` — вход, выдача JWT
- `POST   /refresh` — обновление токенов
- `POST   /logout` — выход, отзыв токенов
- `POST   /validate` — валидация токена
- `POST   /register` — регистрация пользователя
- `GET    /account/me` — профиль текущего пользователя
- `PATCH  /account/me` — обновление профиля
- `POST   /account/change-password` — смена пароля
- `GET    /roles` — список ролей (требует прав)
- `POST   /roles/assign` — назначение роли (админ)
- `GET    /permissions` — список разрешений (админ)
- `GET    /health` — проверка состояния сервиса

Полная OpenAPI-спецификация доступна по `/docs` при запуске сервиса.

---

## Тестирование
- Запуск всех тестов:
  ```bash
  ./scripts/run_tests.sh
  ```
- Покрытие кода и HTML-отчет:
  ```bash
  ./scripts/run_tests.sh -c -r
  ```
- Используются Pytest, coverage, mock.

---

## Интеграция
- **RabbitMQ** — публикация событий о пользователях
- **REST API** — для других сервисов (валидация токенов, получение профиля)
- **Docker/Kubernetes** — готовые манифесты для деплоя

---

## Безопасность
- JWT с ограниченным сроком действия
- Хеширование паролей (bcrypt)
- Rate limiting (Redis)
- Блокировка аккаунта при множественных ошибках
- Валидация сложности паролей
- Черный список токенов

---

## Контакты и поддержка
- Вопросы и баги: создавайте issue в репозитории
- Документация: [documentation.md](./documentation.md)
