# GameTrade - P2P-маркетплейс для безопасного обмена игровыми ценностями

GameTrade - это платформа для безопасной и легальной торговли внутриигровыми предметами, валютами и аккаунтами. Сервис обеспечивает безопасность сделок с помощью системы гарантированных сделок и строгой верификации участников.

## Структура проекта

Проект использует монорепозиторную структуру:

```
├── backend/
│   ├── auth-svc/         # Сервис аутентификации и авторизации
│   ├── marketplace-svc/  # Сервис маркетплейса (объявления, поиск, фильтрация)
│   ├── payment-svc/      # Сервис платежей и финансовых операций
│   └── chat-svc/         # Сервис обмена сообщениями
├── frontend/             # Next.js приложение (клиентская часть)
├── shared/               # Общие библиотеки и утилиты
└── docker-compose.yml    # Конфигурация для локальной разработки
```

## Технологический стек

- **Фронтенд**: Next.js, TypeScript, Tailwind CSS
- **Бэкенд**: Python, FastAPI, SQLAlchemy, Pydantic
- **База данных**: PostgreSQL
- **Кеширование**: Redis
- **Очереди сообщений**: RabbitMQ
- **Контейнеризация**: Docker, Kubernetes
- **CI/CD**: GitHub Actions
- **Мониторинг**: Prometheus, Grafana

## Начало работы

### Предварительные требования

- Python 3.10 или выше
- Node.js (>= 18.0.0)
- npm (>= 9.0.0)
- Docker и docker-compose
- Git

### Установка и запуск

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/yourusername/gametrade.git
   cd gametrade
   ```

2. Установите зависимости:
   ```
   # Для фронтенда
   npm install
   
   # Для бэкенда (в каждом сервисе)
   cd backend/auth-svc
   python -m venv venv
   source venv/bin/activate  # или venv\Scripts\activate на Windows
   pip install -r requirements.txt
   ```

3. Запустите локальную среду разработки:
   ```
   docker-compose up
   ```

4. Запустите фронтенд отдельно:
   ```
   npm run start:frontend
   ```

5. Откройте браузер и перейдите по адресу: http://localhost:3000

## Разработка

### Полезные команды

- `npm run start:all` - Запуск всех сервисов через docker-compose
- `npm run start:frontend` - Запуск Next.js приложения в режиме разработки
- `npm run lint` - Проверка кода с помощью ESLint
- `npm run test` - Запуск тестов
- `npm run format` - Форматирование кода с помощью Prettier

## Лицензия

[MIT](LICENSE) 