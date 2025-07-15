# GameTrade Frontend

## Описание

**GameTrade Frontend** — это клиентское приложение для платформы GameTrade, реализующее маркетплейс, чаты, управление кошельками, сделки, профиль пользователя и административные функции. Построено на Next.js (React), поддерживает SSR, современный UI/UX, темную тему и интеграцию с микросервисами backend.

---

## Основные технологии
- **Next.js** — SSR/SPA, маршрутизация, API-роуты
- **React 19** — компонентный подход
- **TypeScript** — типизация
- **Ant Design** — UI-компоненты
- **TailwindCSS** — утилитарная стилизация
- **Chart.js** — графики и статистика
- **Axios** — HTTP-клиент
- **Jest/Testing Library** — тестирование (если внедрено)

---

## Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
cd frontend
npm install
```

### 2. Запуск в режиме разработки
```bash
npm run dev
```

### 3. Сборка и запуск production-версии
```bash
npm run build
npm start
```

### 4. Запуск через Docker
```bash
docker build -t gametrade/frontend:latest .
docker run -p 3000:3000 gametrade/frontend:latest
```

---

## Переменные окружения
- `NEXT_PUBLIC_API_URL` — базовый URL API (gateway или backend)
- `NEXT_PUBLIC_AUTH_URL` — адрес сервиса аутентификации
- `NEXT_PUBLIC_MARKETPLACE_URL` — адрес marketplace-сервиса
- `NEXT_PUBLIC_PAYMENT_URL` — адрес payment-сервиса
- `NEXT_PUBLIC_CHAT_URL` — адрес chat-сервиса

Пример `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_AUTH_URL=http://localhost:8000/api/auth
NEXT_PUBLIC_MARKETPLACE_URL=http://localhost:8001/api/marketplace
NEXT_PUBLIC_PAYMENT_URL=http://localhost:8002/api/payments
NEXT_PUBLIC_CHAT_URL=http://localhost:8003/api/chat
```

---

## Структура проекта
- `src/app/` — страницы, layout, маршруты Next.js
- `src/app/components/` — переиспользуемые компоненты UI
- `src/app/hooks/` — кастомные хуки (работа с API, авторизация, кошельки и т.д.)
- `src/app/types/` — типы и интерфейсы TypeScript
- `public/` — статические файлы, иконки, изображения
- `styles/` или `globals.css` — глобальные стили
- `next.config.js` — конфигурация Next.js
- `Dockerfile` — сборка контейнера

---

## Основные команды
- `npm run dev` — запуск dev-сервера (localhost:3000)
- `npm run build` — сборка production-версии
- `npm start` — запуск production-сервера
- `npm run lint` — проверка кода линтером
- `npm run docker:build` — сборка Docker-образа
- `npm run docker:run` — запуск контейнера

---

## Сборка и деплой
- Для production используйте `npm run build` и `npm start` или Docker.
- Все переменные окружения должны быть определены на этапе сборки.
- Для SSR/SSG требуется корректная настройка API-адресов.
- Для деплоя на Vercel, Netlify, Render и др. — настройте переменные окружения в панели управления.

---

## Интеграция с backend-сервисами
- Все запросы к API идут через переменные окружения (`NEXT_PUBLIC_*_URL`).
- Для авторизации используется JWT (хранится в cookie/localStorage).
- Поддерживается интеграция с auth-svc, marketplace-svc, payment-svc, chat-svc.
- Для WebSocket-чатов используется адрес из `NEXT_PUBLIC_CHAT_URL`.

---

## Тестирование и линтинг
- Линтинг: `npm run lint` (ESLint, правила для TypeScript и Next.js)
- Тесты: (если внедрено) `npm run test`
- Рекомендуется использовать Prettier для автоформатирования

---

## Советы по разработке и best practices
- Используйте хуки для работы с API и состоянием
- Следуйте компонентному подходу и принципу single responsibility
- Используйте типы из `src/app/types/` для строгой типизации
- Для темной темы используйте классы `.dark` и переключатель темы
- Для новых страниц используйте маршрутизацию Next.js (app router)
- Для работы с формами используйте Ant Design Form или React Hook Form
- Проверяйте доступность (a11y) компонентов

---

## Контакты и поддержка
- Вопросы и баги: через Issues в репозитории

