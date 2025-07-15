# GameTrade — P2P-маркетплейс для геймеров

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-5-red)](https://redis.io/)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12-orange)](https://www.rabbitmq.com/)

> **GameTrade** — это современная платформа для безопасного обмена внутриигровыми ценностями, аккаунтами и услугами между игроками. Проект построен на микросервисной архитектуре, поддерживает мультивалютные платежи, эскроу, чаты, продвинутую админку и масштабируемую инфраструктуру.

---

## Архитектура платформы

```
[ Next.js (Frontend) ]
         |
         v
[ API Gateway (опционально) ]
   |      |      |      |
   v      v      v      v
[auth] [market] [pay] [chat]  <---> [shared]
   |      |      |      |
   v      v      v      v
[ PostgreSQL | Redis | RabbitMQ ]
```
- **Frontend:** Next.js (React)
- **Backend:** auth-svc, marketplace-svc, payment-svc, chat-svc (FastAPI)
- **Инфраструктура:** PostgreSQL, Redis, RabbitMQ, Docker, Kubernetes

---

## Возможности платформы
- P2P-маркетплейс с фильтрами, категориями, играми
- Безопасные сделки через эскроу и мультивалютные кошельки
- Встроенные чаты (личные, групповые, по сделкам)
- Админ-панель для управления пользователями, ролями, контентом
- Интеграция с платежными системами, поддержка комиссий
- Уведомления, статистика, отчёты, поддержка API

---

## Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-org/game-trade.git
cd game-trade
```

### 2. Запуск всех сервисов через Docker Compose
```bash
docker-compose up --build
```

### 3. Локальный запуск сервисов
- Backend: см. `backend/*/README.md`
- Frontend: см. `frontend/README.md`

### 4. Открыть в браузере
- Frontend: [http://localhost:3000](http://localhost:3000)
- Документация API: [http://localhost:8000/docs](http://localhost:8000/docs) (auth-svc и др.)

---

## Сервисы и документация
- **Frontend:** [`frontend/`](./frontend/README.md)
- **Auth Service:** [`backend/auth-svc/`](./backend/auth-svc/README.md)
- **Marketplace Service:** [`backend/marketplace-svc/`](./backend/marketplace-svc/README.md)
- **Payment Service:** [`backend/payment-svc/`](./backend/payment-svc/README.md)
- **Chat Service:** [`backend/chat-svc/`](./backend/chat-svc/README.md)
- **Общие библиотеки:** [`backend/shared/`](./backend/shared/README.md)
- **Kubernetes/DevOps:** [`kubernetes/`](./kubernetes/README.md)

---

## Технологии

| Категория   | Технологии                                      | Назначение                                 |
|-------------|--------------------------------------------------|--------------------------------------------|
| Frontend    | Next.js, React, TypeScript, Ant Design, TailwindCSS | UI, SSR, SPA, стилизация, компоненты       |
| Backend     | FastAPI, Python, SQLAlchemy, Pydantic           | REST API, бизнес-логика, ORM, валидация    |
| Database    | PostgreSQL                                      | Хранение данных пользователей, сделок      |
| Кеш/Очереди | Redis, RabbitMQ                                 | Кеш, очереди событий, rate limiting        |
| DevOps      | Docker, Docker Compose, Kubernetes, Nginx        | Контейнеризация, оркестрация, прокси       |
| Мониторинг  | Prometheus, Grafana                             | Метрики, мониторинг, алерты                |
| Тесты       | Pytest, httpx, Jest, Testing Library             | Юнит- и интеграционные тесты               |

---

## Как внести вклад
1. Форкни репозиторий и создай новую ветку
2. Сделай изменения и добавь тесты
3. Оформи Pull Request с описанием изменений
4. Следуй code style и best practices (см. README сервисов)

---

## Контакты и поддержка
- Вопросы и баги: через Issues в репозитории
- Подробнее о каждом сервисе — см. соответствующие README 