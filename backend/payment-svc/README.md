# GameTrade Payment Service (payment-svc)

## Описание

**payment-svc** — микросервис для управления платежами, кошельками, транзакциями, эскроу и выводом средств на платформе GameTrade. Сервис реализован на FastAPI, использует PostgreSQL для хранения данных, RabbitMQ для событий и Redis для кеширования и идемпотентности. Поддерживает мультивалютность, комиссии, безопасные сделки через эскроу и интеграцию с другими сервисами платформы.

---

## Архитектура
- **FastAPI** — REST API
- **PostgreSQL** — хранение кошельков, транзакций, истории
- **RabbitMQ** — события для интеграции с marketplace, auth, chat
- **Redis** — кеширование, идемпотентность, rate limiting
- **Alembic** — миграции БД
- **Модули**: routers, services, models, schemas, config

Подробнее см. [Документацию](./docs/api.md) и [Архитектуру](./documentation.md).

---

## Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
cd backend/payment-svc
pip install -r requirements.txt
```

### 2. Запуск локально
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

### 3. Запуск через Docker
```bash
docker build -t payment-svc .
docker run --env-file .env -p 8002:8002 payment-svc
```

### 4. Проверка работоспособности
- [http://localhost:8002/health](http://localhost:8002/health) — healthcheck
- [http://localhost:8002/docs](http://localhost:8002/docs) — Swagger UI

---

## Переменные окружения
- `DATABASE_URL` — строка подключения к PostgreSQL
- `RABBITMQ_URL` — строка подключения к RabbitMQ
- `REDIS_HOST`, `REDIS_PORT` — параметры Redis
- `JWT_SECRET` — секрет для проверки JWT токенов
- `SERVICE_PORT` — порт запуска сервиса (по умолчанию 8002)
- `LOG_LEVEL` — уровень логирования
- `AUTH_SERVICE_URL` — URL сервиса аутентификации
- `MARKETPLACE_SERVICE_URL` — URL сервиса маркетплейса

Все переменные можно задать в `.env` файле.

---

## Миграции базы данных

### Применение миграций
```bash
alembic upgrade head
```

### Создание новой миграции
```bash
alembic revision --autogenerate -m "описание изменений"
```

---

## Основные API эндпоинты

### Кошельки
- `POST /wallets` — создать кошелек
- `GET /wallets` — список кошельков
- `GET /wallets/{id}` — информация о кошельке
- `POST /wallets/{id}/deposit` — пополнение
- `POST /wallets/{id}/withdraw` — вывод средств
- `POST /wallets/{id}/convert` — конвертация валюты

### Транзакции
- `POST /transactions` — создать транзакцию
- `GET /transactions` — список транзакций
- `GET /transactions/{id}` — информация о транзакции
- `POST /transactions/{id}/escrow` — перевод в эскроу
- `POST /transactions/{id}/complete` — завершить
- `POST /transactions/{id}/refund` — возврат
- `POST /transactions/{id}/dispute` — открыть спор
- `POST /transactions/{id}/resolve` — разрешить спор
- `POST /transactions/{id}/cancel` — отменить

### История и отчеты
- `GET /transaction_history` — история транзакций
- `GET /transaction_history/{id}` — история по транзакции
- `GET /transaction_history/{id}/export` — экспорт истории (CSV/JSON)

### Валюта и комиссии
- `GET /currency/rates` — курсы валют
- `POST /currency/convert/preview` — расчет конвертации
- `POST /currency/convert/execute` — выполнить конвертацию
- `GET /currency/fees` — комиссии

### Статистика
- `GET /statistics/seller` — статистика продавца
- `GET /statistics/transactions/summary` — сводка по транзакциям
- `GET /statistics/popular-games` — популярные игры

### Продажи
- `POST /sales/{sale_id}/initiate-payment` — инициировать оплату
- `POST /sales/{sale_id}/confirm` — подтвердить оплату
- `POST /sales/{sale_id}/reject` — отклонить оплату
- `POST /sales/{sale_id}/complete-delivery` — завершить доставку
- `POST /sales/{sale_id}/release-funds` — вывести средства

Полная спецификация — [docs/api.md](./docs/api.md)

---

## Интеграция с другими сервисами
- **auth-svc** — проверка JWT, создание пользователей
- **marketplace-svc** — получение информации о товарах, продажах
- **RabbitMQ** — события о транзакциях, кошельках, продажах
- **Redis** — кеширование, идемпотентность

---

## Безопасность и best practices
- JWT-аутентификация для всех операций
- Идемпотентность через заголовок `X-Idempotency-Key`
- Логирование и аудит всех операций
- Проверка прав доступа (admin, seller, buyer)
- Защита от дублирования и race conditions
- Эскроу для безопасных сделок

---

## Контакты и поддержка
- Вопросы и баги: через Issues в репозитории
- Техническая поддержка: [email@example.com]
- Подробнее: см. [Документацию](./documentation.md) 