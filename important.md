Краткое руководство по ключевым компонентам проекта GameTrade
1. Архитектура

Микросервисы: Система разделена на 5 сервисов (auth-svc, marketplace-svc, payment-svc, notification-svc, admin-svc)
API Gateway: NGINX обрабатывает все входящие запросы, маршрутизирует и выполняет JWT-аутентификацию
Асинхронная коммуникация: RabbitMQ для событийно-ориентированного взаимодействия между сервисами

2. Динамическая категоризация (ключевая особенность)
Модель данных
games → item_categories → category_attributes → item_templates → listings
Работа с динамическими атрибутами

Используйте JSONB в PostgreSQL для хранения атрибутов (attributes поле в listings)
Создавайте индексы GIN для полей JSONB: CREATE INDEX idx_listings_attrs ON listings USING GIN(attributes);
При поиске используйте операторы PostgreSQL для JSONB: WHERE attributes->'item_level' > '400'

Пример API-запроса для создания лота
httpPOST /api/v1/listings
Content-Type: application/json
{
  "game_id": "uuid-игры",
  "category_id": "uuid-категории",
  "title": "Название предмета",
  "price": "19.99",
  "currency": "USD",
  "attributes": { 
    "item_level": 415,
    "required_level": 60,
    "stats": { "strength": 120 }
  }
}
3. Процесс сделки (Escrow)

Инициация: Покупатель создает транзакцию (POST /api/v1/transactions)
Холдирование: Средства замораживаются на счете покупателя (payment-svc)
Передача предмета: Продавец передает предмет покупателю (вне платформы)
Подтверждение: Покупатель подтверждает получение (POST /api/v1/transactions/{id}/complete)
Завершение: Средства переводятся продавцу, минус комиссия

Важные статусы транзакций
PENDING → ESCROW_HELD → COMPLETED
           ↓
           → DISPUTED → RESOLVED_BUYER/RESOLVED_SELLER
           ↓
           → REFUNDED
4. Поисковые возможности

Основные параметры поиска: game, category, query, price_min, price_max
Динамические фильтры: stats.strength.min=100
Полный URL-пример: /api/v1/listings?game=world-of-warcraft&category=weapons/one-handed&stats.strength.min=100&sort=price_asc

5. Безопасность

JWT: Токены с 15-минутным сроком действия + refresh tokens
Хранение паролей: Argon2 или bcrypt
HTTPS: Для всех соединений
Rate Limiting: По IP и user_id
CORS: Проверка источников запросов

6. База данных

PostgreSQL с шардированием по играм при росте системы
Важные индексы:
sqlCREATE INDEX idx_listings_game ON listings(game_id);
CREATE INDEX idx_listings_category ON listings(category_id);
CREATE INDEX idx_listings_status ON listings(status);

Транзакционное управление: Используйте Unit of Work шаблон

7. Клиентская часть

Структура страниц:

/ - главная страница с категориями и популярными предметами
/listings - поиск и фильтрация лотов
/listings/[id] - детальная страница лота
/account/wallet - управление кошельком
/account/listings - управление лотами продавца
/account/transactions - история сделок
/admin/dashboard - админ-панель с аналитикой


Состояние: Используйте React Query для данных с сервера и Zustand для глобального состояния

8. Процесс разработки

Начинайте с базовых сущностей: игры, категории, атрибуты
Реализуйте core-сервисы: аутентификация, листинги, поиск
Добавьте систему Escrow и платежи
Разработайте систему споров и модерации
Имплементируйте аналитику и админ-панель

9. Команды для быстрого старта

Запуск локально: docker-compose up
Миграции БД: alembic upgrade head
Генерация OpenAPI: python -m marketplace.main --generate-openapi
Запуск тестов: pytest

10. Важные файлы

Конфигурация: marketplace/config.py - все настройки сервиса
Модели данных: marketplace/domain/*.py - ключевые бизнес-сущности
API-эндпоинты: marketplace/api/routers/*.py - HTTP-интерфейсы
Бизнес-логика: marketplace/services/*.py - основная логика приложения

Используйте это руководство как быстрый справочник по ключевым аспектам системы. Для более детальной информации обращайтесь к полному PRD.