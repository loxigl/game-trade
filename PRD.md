Полное PRD - Биржа внутриигровых ценностей
Версия: 1.2
Дата: 12 мая 2025 г.
Статус: Готов к реализации
1. Введение
1.1 Обзор продукта
Платформа "GameTrade" представляет собой P2P-маркетплейс для безопасного обмена внутриигровыми ценностями (предметами, аккаунтами) между игроками. Ключевой особенностью платформы является система Escrow, которая гарантирует безопасность сделок и предотвращает мошенничество.
1.2 Глоссарий
ТерминОписаниеEscrowМеханизм заморозки средств до подтверждения передачи предметаListingОбъявление о продаже конкретного предмета/аккаунтаMarketplace‑serviceБизнес‑логика публикации лотов и сделокItemTemplateСтатический справочник предметов конкретной игрыDisputeСпор между продавцом и покупателемWalletВнутренний кошелек пользователя с балансом в определенной валюте
1.3 Цели проекта

Предоставить безопасную P2P-площадку для торговли внутриигровыми ценностями
Минимизировать мошенничество через Escrow, антифрод и модерацию
Обеспечить высокую производительность (P95 latency < 200 мс при 1000 RPS)
Гарантировать доступность (SLA 99.9%)

2. Обзор системы
2.1 Высокоуровневая архитектура
┌ Browser (React‑SPA) ┐
│   Next.js 14 SSR   │
└───────▲────────────┘
        │HTTPS JSON/REST + WebSocket
┌───────┴───────────┐  AMQP   ┌────────────────┐
│  API‑Gateway (NGINX) │◀────▶│ notification‑svc │
├───────────────────┤         └────────────────┘
│  auth‑svc        │  gRPC   ┌────────────────┐
│  marketplace‑svc │◀──────▶│ payment‑svc     │
│  fraud‑svc       │         └────────────────┘
│  chat-svc        │
│  admin‑svc       │
└───────────────────┘
        │
     PostgreSQL + Redis + Elasticsearch
Каждая сервис‑группа развёрнута в отдельном Kubernetes‑Deployment с авто‑хоризонтальным масштабированием (HPA) на основе CPU / RPS.
2.2 Технологический стек

Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2
Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
Данные: PostgreSQL 15, Redis 7, Elasticsearch
Сообщения: RabbitMQ
Деплой: Kubernetes, Docker, GitHub Actions, Terraform
Мониторинг: Prometheus + Grafana, OpenSearch + Fluent Bit

3. Функциональные требования
3.1 User Stories & Acceptance Criteria
#КакЯ хочуЧтобыAcceptance Test (ID)US‑01ГостьНайти предмет по названиюБыстро купить егоsearch‑01 — <300 мс, релевантность > 0.8US‑04ПродавецОпубликовать лотПолучить деньги на кошелёкlisting‑create‑01 — статус=ACTIVE, комиссия рассчитанаUS‑08ПокупательОплатить лотСредства ушли в Escrowtxn‑init‑01 — статус=HELD, wallet‑balance‑buyer −=amountUS‑12Модер.Заблокировать подозрительный лотПредотвратить фродmoder‑ban‑01 — статус=BANNED, уведомление продавцу
3.2 Сценарии ошибок

LISTING_NOT_FOUND — 404
INSUFFICIENT_FUNDS — 409
ESCROW_TIMEOUT — автоматическое открытие спора (Dispute)
AUTHORIZATION_FAILED — 401
VALIDATION_ERROR — 422
RATE_LIMIT_EXCEEDED — 429

4. Функциональные требования
4.1 Аутентификация и авторизация

JWT-аутентификация с access token (15 мин) и refresh token (30 дней)
Роли: гость, пользователь, продавец, модератор, администратор
OAuth интеграция со Steam и Discord

Пример JWT-токена:
json{
  "sub": "af7c441e-2e9c-48f0-8b27-3d39a8f2c9d5",
  "role": "user",
  "email": "user@example.com",
  "iat": 1715507098,
  "exp": 1715508098
}
4.2 Динамическая категоризация товаров и услуг
Система должна поддерживать различные типы внутриигровых ценностей, которые существенно различаются между играми:

Предметы (оружие, броня, расходники, косметические предметы)
Валюта (золото, кристаллы, внутриигровые монеты)
Услуги (прокачка уровня, прохождение рейдов, обучение)
Аккаунты (полноценные аккаунты с прогрессом)

4.2.1 Динамические атрибуты для предметов
Для поддержки различных типов предметов и их уникальных атрибутов в зависимости от игры, система использует динамическую схему атрибутов:
json// Пример структуры метаданных для предметов WoW
{
  "item_type": "equipment",
  "sub_type": "weapon",
  "weapon_type": "sword",
  "level": 70,
  "item_level": 415,
  "stats": {
    "strength": 120,
    "stamina": 85,
    "critical_strike": 45,
    "haste": 30
  },
  "required_level": 60,
  "binding": "bind_on_equip",
  "unique": true,
  "visual_effect": "fiery_glow"
}

// Пример структуры для внутриигровой валюты
{
  "item_type": "currency",
  "currency_type": "gold",
  "amount": 10000,
  "server": "Silvermoon",
  "faction": "Alliance",
  "delivery_method": "auction_house"
}

// Пример структуры для услуг
{
  "item_type": "service",
  "service_type": "leveling",
  "from_level": 1,
  "to_level": 60,
  "character_class": "Warrior",
  "estimated_time": "3 days",
  "includes_gear": true
}
4.2.2 Система категорий
Для эффективной работы с множеством игр и типов товаров, система использует иерархическую структуру категорий:
┌─ Игра
│  └─ Тип товара
│     └─ Подтип
│        └─ Специфические фильтры
Пример иерархии для World of Warcraft:
World of Warcraft
├── Валюта
│   ├── Золото
│   │   ├── Фильтры: сервер, фракция, метод доставки
│   └── Другие валюты
├── Предметы
│   ├── Оружие
│   │   ├── Одноручное
│   │   │   ├── Фильтры: уровень предмета, характеристики, требуемый уровень
│   │   ├── Двуручное
│   │   └── Дальний бой
│   ├── Броня
│   │   ├── Тканевая
│   │   ├── Кожаная
│   │   ├── Кольчужная
│   │   └── Латная
│   └── Расходники
├── Услуги
│   ├── Прокачка персонажа
│   │   ├── Фильтры: начальный уровень, конечный уровень, класс, срок
│   ├── Рейды и подземелья
│   └── Профессии
└── Аккаунты
    └── Фильтры: уровень, классы, достижения, редкие предметы
Пример иерархии для Counter-Strike 2:
Counter-Strike 2
├── Скины
│   ├── Оружие
│   │   ├── Ножи
│   │   │   ├── Фильтры: редкость, износ, StatTrak
│   │   ├── Пистолеты
│   │   ├── Винтовки
│   │   └── Пистолеты-пулеметы
│   └── Перчатки
├── Наклейки
├── Кейсы
└── Аккаунты
    └── Фильтры: ранг, статистика, количество скинов
4.2.3 Модель данных для категоризации
sql-- Игры
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Категории товаров
CREATE TABLE item_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id),
    parent_id UUID REFERENCES item_categories(id),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    level INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT unique_category_slug_per_game UNIQUE (game_id, slug)
);

-- Атрибуты категорий
CREATE TABLE category_attributes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES item_categories(id),
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    attribute_type TEXT NOT NULL, -- string, number, boolean, enum
    is_required BOOLEAN DEFAULT FALSE,
    is_filterable BOOLEAN DEFAULT FALSE,
    is_searchable BOOLEAN DEFAULT FALSE,
    default_value JSONB,
    validation_rules JSONB,
    enum_values JSONB,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT unique_attribute_per_category UNIQUE (category_id, name)
);

-- Расширение ItemTemplate
CREATE TABLE item_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id),
    category_id UUID NOT NULL REFERENCES item_categories(id),
    name TEXT NOT NULL,
    description TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Индексы для поиска
CREATE INDEX idx_item_templates_category ON item_templates(category_id);
CREATE INDEX idx_item_templates_game ON item_templates(game_id);
CREATE INDEX idx_item_templates_attrs ON item_templates USING GIN(attributes);
4.2.4 Функциональный пример: Создание листинга с динамическими атрибутами
Запрос:
httpPOST /api/v1/listings HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "game_id": "f8e7d6c5-b4a3-4d21-9e87-1f0e2cd3b4a5",
  "category_id": "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
  "title": "Эпический меч Ледяного ветра +10",
  "price": "49.99",
  "currency": "USD",
  "quantity": 1,
  "attributes": {
    "item_level": 415,
    "required_level": 60,
    "weapon_type": "sword",
    "damage": 2450,
    "stats": {
      "strength": 120,
      "stamina": 85,
      "critical_strike": 45,
      "haste": 30
    },
    "enchantment": "frost_damage",
    "socket_count": 2,
    "binding": "bind_on_equip"
  },
  "delivery_method": "in_game_mail",
  "delivery_time": "within_1_hour",
  "expires_at": "2025-05-31T00:00:00Z",
  "description": "Редкий меч дракона с бонусом к урону +10"
}
Ответ:
httpHTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "a27ba44e-0c47-48b5-8643-2e39a8e23fbc",
  "status": "ACTIVE",
  "fee": "5.00",
  "seller_id": "95c31220-b3be-4152-aea6-4d1d9c8c22ac",
  "game": {
    "id": "f8e7d6c5-b4a3-4d21-9e87-1f0e2cd3b4a5",
    "name": "World of Warcraft",
    "icon_url": "/games/wow.png"
  },
  "category": {
    "id": "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
    "name": "Оружие > Одноручное > Мечи"
  },
  "title": "Эпический меч Ледяного ветра +10",
  "attributes": {
    "item_level": 415,
    "required_level": 60,
    "weapon_type": "sword",
    "damage": 2450,
    "stats": {
      "strength": 120,
      "stamina": 85,
      "critical_strike": 45,
      "haste": 30
    },
    "enchantment": "frost_damage",
    "socket_count": 2,
    "binding": "bind_on_equip"
  },
  "price": "49.99",
  "currency": "USD",
  "delivery_method": "in_game_mail",
  "delivery_time": "within_1_hour",
  "created_at": "2025-05-12T14:38:29Z",
  "expires_at": "2025-05-31T00:00:00Z",
  "images": []
}
4.2.5 Функциональный пример: Поиск с динамическими фильтрами
Запрос:
httpGET /api/v1/listings?game=world-of-warcraft&category=weapons/one-handed/swords&min_item_level=400&max_item_level=450&stats.strength.min=100&sort=price_asc&limit=20 HTTP/1.1
Ответ:
httpHTTP/1.1 200 OK
Content-Type: application/json

{
  "items": [
    {
      "id": "a27ba44e-0c47-48b5-8643-2e39a8e23fbc",
      "title": "Эпический меч Ледяного ветра +10",
      "price": "49.99",
      "currency": "USD",
      "attributes": {
        "item_level": 415,
        "required_level": 60,
        "stats": {
          "strength": 120,
          "stamina": 85
        }
      },
      "images": ["/listings/a27ba44e/1.jpg"],
      "seller": {
        "id": "95c31220-b3be-4152-aea6-4d1d9c8c22ac",
        "display_name": "DragonSlayer",
        "rating": 4.8
      },
      "created_at": "2025-05-12T14:38:29Z"
    },
    // ... другие предметы
  ],
  "filters": {
    "item_level": {
      "min": 410,
      "max": 450,
      "distribution": [
        {"value": 410, "count": 2},
        {"value": 415, "count": 5},
        {"value": 420, "count": 3},
        {"value": 440, "count": 1},
        {"value": 450, "count": 1}
      ]
    },
    "weapon_type": [
      {"value": "sword", "count": 8},
      {"value": "axe", "count": 4}
    ],
    "stats.strength": {
      "min": 100,
      "max": 145,
      "distribution": [
        {"range": "100-110", "count": 3},
        {"range": "111-120", "count": 5},
        {"range": "121-130", "count": 2},
        {"range": "131-145", "count": 2}
      ]
    }
    // ... другие фильтры
  },
  "pagination": {
    "total": 42,
    "limit": 20,
    "offset": 0,
    "next_offset": 20
  }
}
4.2.6 Пример: Управление динамическими атрибутами в админ-панели
Данные категории:
json{
  "id": "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
  "game_id": "f8e7d6c5-b4a3-4d21-9e87-1f0e2cd3b4a5",
  "parent_id": "e9d8c7b6-a5f4-4e3d-2c1b-0a9b8c7d6e5f",
  "name": "Мечи",
  "slug": "swords",
  "level": 3,
  "attributes": [
    {
      "id": "b1a2d3c4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "item_level",
      "display_name": "Уровень предмета",
      "attribute_type": "number",
      "is_required": true,
      "is_filterable": true,
      "is_searchable": false,
      "validation_rules": {
        "min": 1,
        "max": 1000
      },
      "sort_order": 1
    },
    {
      "id": "c1b2a3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "required_level",
      "display_name": "Требуемый уровень",
      "attribute_type": "number",
      "is_required": true,
      "is_filterable": true,
      "is_searchable": false,
      "validation_rules": {
        "min": 1,
        "max": 70
      },
      "sort_order": 2
    },
    {
      "id": "d1c2b3a4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "damage",
      "display_name": "Урон",
      "attribute_type": "number",
      "is_required": true,
      "is_filterable": true,
      "is_searchable": false,
      "sort_order": 3
    },
    {
      "id": "e1d2c3b4-a5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "stats",
      "display_name": "Характеристики",
      "attribute_type": "object",
      "is_required": true,
      "is_filterable": true,
      "is_searchable": false,
      "sub_attributes": [
        {
          "name": "strength",
          "display_name": "Сила",
          "attribute_type": "number",
          "is_required": false,
          "is_filterable": true
        },
        {
          "name": "stamina",
          "display_name": "Выносливость",
          "attribute_type": "number",
          "is_required": false,
          "is_filterable": true
        },
        {
          "name": "critical_strike",
          "display_name": "Критический удар",
          "attribute_type": "number",
          "is_required": false,
          "is_filterable": true
        },
        {
          "name": "haste",
          "display_name": "Скорость",
          "attribute_type": "number",
          "is_required": false,
          "is_filterable": true
        }
      ],
      "sort_order": 4
    },
    {
      "id": "f1e2d3c4-b5a6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "binding",
      "display_name": "Привязка",
      "attribute_type": "enum",
      "is_required": true,
      "is_filterable": true,
      "is_searchable": false,
      "enum_values": [
        {"value": "bind_on_pickup", "label": "Привязывается при получении"},
        {"value": "bind_on_equip", "label": "Привязывается при надевании"},
        {"value": "bind_on_use", "label": "Привязывается при использовании"},
        {"value": "no_binding", "label": "Не привязывается"}
      ],
      "sort_order": 5
    }
  ]
}
4.3 Процесс сделки

Инициация сделки покупателем
Escrow-механизм с холдированием средств
Подтверждение доставки предметов
Автоматические выплаты продавцам

Пример последовательности сделки:

Покупатель инициирует транзакцию: POST /api/v1/transactions
Сервис замораживает средства: POST /api/v1/payments/hold
Продавец передает предмет покупателю (off-platform)
Покупатель подтверждает получение: POST /api/v1/transactions/{id}/complete
Система освобождает средства продавцу: POST /api/v1/payments/capture

4.4 Кошелек и платежи

Внутренний кошелек пользователя для каждой поддерживаемой валюты
Интеграция со Stripe для пополнения и вывода средств
Мультивалютная поддержка (USD, EUR, GBP) с автоконверсией
История транзакций и выписки

Пример структуры кошелька:
json{
  "id": "6721f4db-e2d4-4e23-bfd3-ba1d98152b0c",
  "user_id": "af7c441e-2e9c-48f0-8b27-3d39a8f2c9d5",
  "currency": "USD",
  "balance": "152.47",
  "transactions": [
    {
      "id": "f5d8e39a-c347-4321-b544-1f2b75c26ef9",
      "type": "DEPOSIT",
      "amount": "100.00",
      "status": "COMPLETED",
      "created_at": "2025-05-10T12:23:45Z"
    },
    {
      "id": "a2e4f918-b62d-4c17-9e88-7d2a3b4c5d6e",
      "type": "PURCHASE",
      "amount": "-19.99",
      "status": "COMPLETED",
      "created_at": "2025-05-11T09:15:22Z",
      "reference_id": "c8c40a32-6e0a-4d32-9c50-e48dd89e77ac"
    }
  ]
}
4.5 Система споров

Открытие спора при проблеме с доставкой предмета
Загрузка доказательств (скриншоты, видео)
Интерфейс модератора для разрешения споров
Автоматический возврат средств при тайм-ауте

Пример создания спора:
httpPOST /api/v1/disputes HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "transaction_id": "c8c40a32-6e0a-4d32-9c50-e48dd89e77ac",
  "reason": "ITEM_NOT_RECEIVED",
  "description": "Продавец не передал предмет в течение 24 часов",
  "evidence_urls": [
    "https://marketplace-media.s3.amazonaws.com/evidence/screenshot1.jpg"
  ]
}
4.6 Уведомления

Реализация через WebSocket для мгновенных уведомлений
Push-уведомления в браузере
Email-уведомления для важных событий
SMS-уведомления (опционально)

Пример структуры уведомления:
json{
  "id": "a0f4e9d8-b7c6-4a3b-85e2-1d0c9b8a7f6e",
  "user_id": "af7c441e-2e9c-48f0-8b27-3d39a8f2c9d5",
  "type": "TRANSACTION_COMPLETED",
  "title": "Сделка завершена",
  "body": "Сделка #c8c40a32 успешно завершена. Не забудьте оставить отзыв!",
  "created_at": "2025-05-12T15:42:18Z",
  "read": false,
  "action_url": "/transactions/c8c40a32-6e0a-4d32-9c50-e48dd89e77ac/review"
}
4.7 Система репутации

Рейтинг продавцов и покупателей (1-5 звезд)
Текстовые отзывы о сделках
Статистика успешных сделок
Верификация пользователей

Пример отзыва:
json{
  "id": "1d2e3f4a-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
  "transaction_id": "c8c40a32-6e0a-4d32-9c50-e48dd89e77ac",
  "author_id": "af7c441e-2e9c-48f0-8b27-3d39a8f2c9d5",
  "recipient_id": "95c31220-b3be-4152-aea6-4d1d9c8c22ac",
  "rating": 5,
  "comment": "Отличный продавец, быстро передал предмет. Рекомендую!",
  "created_at": "2025-05-12T16:30:45Z"
}
4.8 Система чата между покупателем и продавцом
Платформа предоставляет встроенную систему обмена сообщениями для безопасной и удобной коммуникации между покупателями и продавцами.
4.8.1 Функциональные возможности чата

Обмен текстовыми сообщениями в реальном времени
Отправка изображений (скриншотов для подтверждения передачи предметов)
Хранение истории сообщений для каждой сделки
Уведомления о новых сообщениях
Модерация чатов для разрешения споров

4.8.2 Техническая реализация

WebSocket-соединение для доставки сообщений в реальном времени
Сохранение истории сообщений в базу данных
Отдельный микросервис chat-svc для обработки сообщений
Интеграция с системой уведомлений
End-to-end шифрование для конфиденциальности

4.8.3 Правила и ограничения

Чат становится доступен после создания транзакции и до истечения 30 дней после завершения сделки
Ограничение на размер сообщений: 1000 символов
Ограничение на размер изображений: до 5 МБ
Модераторы имеют доступ к истории чата в случае открытия спора
Автоматическая фильтрация нецензурной лексики

4.8.4 Интерфейс чата

Встроенный интерфейс на странице транзакции
Отдельный раздел в личном кабинете со всеми активными чатами
Индикаторы статуса (прочитано/не прочитано)
Индикаторы присутствия собеседника онлайн

Пример структуры сообщения:
json{
  "id": "d2f8e9c7-b6a5-4d23-81fe-7a9c4b5d3e2f",
  "transaction_id": "c8c40a32-6e0a-4d32-9c50-e48dd89e77ac",
  "sender_id": "af7c441e-2e9c-48f0-8b27-3d39a8f2c9d5",
  "recipient_id": "95c31220-b3be-4152-aea6-4d1d9c8c22ac",
  "content": "Привет! Я готов передать предмет. В какое время тебе удобно?",
  "type": "text", // text, image
  "image_url": null,
  "created_at": "2025-05-12T15:23:47Z",
  "read_at": null,
  "is_system": false // true для системных сообщений
}
4.8.5 API-эндпоинты для чата
МетодURLОписаниеGET/v1/chatsПолучить список активных чатов пользователяGET/v1/chats/{transaction_id}Получить историю сообщений по транзакцииPOST/v1/chats/{transaction_id}/messagesОтправить новое сообщениеPATCH/v1/chats/{transaction_id}/messages/{message_id}/readОтметить сообщение прочитаннымPOST/v1/chats/{transaction_id}/messages/imageЗагрузить изображениеDELETE/v1/chats/{transaction_id}/messages/{message_id}Удалить сообщение (только свои)
4.8.6 WebSocket API
javascript// Пример подключения к WebSocket чата
const socket = new WebSocket('wss://api.gametrade.com/v1/chats/ws');

// Авторизация
socket.onopen = () => {
  socket.send(JSON.stringify({
    type: 'auth',
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
  }));
};

// Подписка на определенную транзакцию
socket.send(JSON.stringify({
  type: 'subscribe',
  transaction_id: 'c8c40a32-6e0a-4d32-9c50-e48dd89e77ac'
}));

// Обработка входящих сообщений
socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Новое сообщение:', message);
};

// Отправка сообщения
socket.send(JSON.stringify({
  type: 'message',
  transaction_id: 'c8c40a32-6e0a-4d32-9c50-e48dd89e77ac',
  content: 'Привет! Когда будешь готов передать предмет?'
}));
4.8.7 Пример сценария использования

Покупатель создает транзакцию для покупки предмета
Система автоматически создает чат между покупателем и продавцом
Продавец получает уведомление о новой транзакции и входит в чат
Стороны договариваются о времени и способе передачи предмета
Продавец отправляет скриншот/подтверждение передачи через чат
Покупатель подтверждает получение, завершая транзакцию
Чат остается доступным еще 30 дней для возможных вопросов

4.8.8 Интеграция с системой споров
В случае открытия спора:

Вся история переписки автоматически прикрепляется к спору
Модератор получает доступ к чату для анализа ситуации
Модератор может отправлять системные сообщения обеим сторонам
Системные уведомления о статусе спора автоматически отправляются в чат

4.9 Аналитическая панель для администраторов

Дашборд с ключевыми метриками бизнеса
Детальная статистика по продажам, пользователям и спорам
Графики активности и конверсий
Экспорт отчетов в CSV/Excel

Ключевые метрики дашборда:

Общий объем продаж (GMV) за период
Количество активных пользователей (DAU/MAU)
Средний чек и комиссия платформы
Conversion rate воронки покупки
Процент успешно закрытых споров
TOP-10 популярных предметов и игр

Пример структуры дашборда:
┌─────────────────────────┐ ┌─────────────────────────┐
│ Ключевые метрики        │ │ Продажи по играм        │
│ GMV: $125,432           │ │ [Круговая диаграмма]    │
│ Транзакции: 834         │ │                         │
│ Ср. чек: $150.4         │ │                         │
│ Комиссия: $12,543       │ │                         │
└─────────────────────────┘ └─────────────────────────┘
┌─────────────────────────┐ ┌─────────────────────────┐
│ Активность пользователей│ │ Статистика споров       │
│ [График по дням]        │ │ Открыто: 24             │
│                         │ │ Решено: 22              │
│                         │ │ Среднее время: 1.2 дня  │
│                         │ │ В пользу покупателя: 60%│
└─────────────────────────┘ └─────────────────────────┘
┌───────────────────────────────────────────────────────┐
│ Последние транзакции                                  │
│ ID         | Сумма   | Игра        | Статус | Время   │
│ a27ba44e.. | $19.99  | Dragon Quest| COMPLETED| 14:38 │
│ f8e91c5d.. | $45.50  | CS 2        | ESCROW  | 13:22  │
│ ...                                                    │
└───────────────────────────────────────────────────────┘
Экраны админ-панели:

Главный дашборд (обзор метрик)
Управление пользователями
Мониторинг транзакций
Модерация листингов
Разрешение споров
Настройки комиссий и лимитов
Отчеты и аналитика

5. API и интеграции
5.1 REST API
Все сервисы публикуют OpenAPI 3.1 спецификацию, генерируемую из код-аннотаций.
5.2 auth-service
МетодURLAuthОписаниеPOST/v1/auth/registernoneРегистрация нового пользователяPOST/v1/auth/loginnoneВход в системуPOST/v1/auth/refreshrefresh_tokenОбновление токена доступаGET/v1/auth/meuserПолучение профиля пользователяPATCH/v1/auth/profileuserОбновление профиля
5.3 marketplace-service
МетодURLAuthОписаниеPOST/v1/listingssellerСоздать лотGET/v1/listings/{id}anyПолучить лотPATCH/v1/listings/{id}sellerИзменить цену/статусDELETE/v1/listings/{id}sellerСнять с продажиGET/v1/listingsanyПоиск лотов с фильтрамиPOST/v1/transactionsbuyerСоздать транзакциюGET/v1/transactions/{id}buyer/sellerПолучить детали транзакцииPOST/v1/transactions/{id}/completebuyerПодтвердить получение предметаPOST/v1/disputesbuyer/sellerОткрыть спор
5.4 Чат-сервис
EndpointОписаниеGET /v1/chatsПолучить список активных чатов пользователяGET /v1/chats/{transaction_id}Получить историю сообщений по транзакцииPOST /v1/chats/{transaction_id}/messagesОтправить новое сообщениеPATCH /v1/chats/{transaction_id}/messages/{message_id}/readОтметить сообщение прочитаннымPOST /v1/chats/{transaction_id}/messages/imageЗагрузить изображениеDELETE /v1/chats/{transaction_id}/messages/{message_id}Удалить сообщениеGET /v1/chats/wsWebSocket-соединение для чата
WebSocket Protocol:
{
  "type": "[auth|subscribe|message|typing|read]",
  "transaction_id": "uuid", // Для всех типов кроме auth
  "token": "jwt-token", // Только для auth
  "content": "text", // Только для message
  "message_id": "uuid" // Для read
}
5.5 notification-service
Отправляет события через Web‑Push и Email (SES) на базе шаблонов Handlebars.
EndpointОписаниеPOST /v1/notificationsСоздать уведомлениеGET /v1/notifications/user/{user_id}Получить уведомления пользователяPATCH /v1/notifications/{id}/readОтметить как прочитанноеPOST /v1/notifications/subscribeПодписаться на WebSocket уведомления
5.6 payment-service
EndpointОписаниеPOST /v1/payments/holdЗаморозить средства (Stripe PI)POST /v1/payments/captureПеревести средства продавцуPOST /v1/payments/refundЧАСТИЧНЫЙ/ПОЛНЫЙ возвратGET /v1/wallet/{user_id}/balanceПолучить баланс кошелькаPOST /v1/wallet/depositПополнить кошелекPOST /v1/wallet/withdrawВывести средства
Webhook /v1/webhooks/stripe — подпись проверяется по HMAC‑SHA256.
6. Модель данных
6.1 Core Entities
users
sqlCREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
profiles
sqlCREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    CONSTRAINT unique_user_profile UNIQUE (user_id)
);
wallets
sqlCREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency CHAR(3) NOT NULL,
    balance NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT positive_balance CHECK (balance >= 0.00),
    CONSTRAINT unique_user_currency UNIQUE (user_id, currency)
);
listings
sqlCREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_template_id UUID NOT NULL REFERENCES item_templates(id),
    seller_id UUID NOT NULL REFERENCES users(id),
    price NUMERIC(14,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    status listing_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    description TEXT
);
transactions
sqlCREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id),
    buyer_id UUID NOT NULL REFERENCES users(id),
    amount NUMERIC(14,2) NOT NULL,
    fee NUMERIC(14,2) NOT NULL,
    status txn_status NOT NULL DEFAULT 'PENDING',
    escrow_payment_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);
6.2 Enums и константы
sqlCREATE TYPE user_role AS ENUM ('user', 'moderator', 'admin');
CREATE TYPE listing_status AS ENUM ('PENDING', 'ACTIVE', 'SOLD', 'EXPIRED', 'BANNED');
CREATE TYPE txn_status AS ENUM ('PENDING', 'ESCROW_HELD', 'COMPLETED', 'REFUNDED', 'DISPUTED');
CREATE TYPE dispute_status AS ENUM ('OPEN', 'RESOLVED_BUYER', 'RESOLVED_SELLER', 'RESOLVED_SPLIT');
6.3 Entity Relationship Diagram (ERD)
USER(id) --1:N--> LISTING(seller_id)
USER(id) --1:N--> TRANSACTION(buyer_id)
USER(id) --1:1--> PROFILE(user_id)
USER(id) --1:N--> WALLET(user_id)
USER(id) --1:N--> RATING(author_id)

ITEMTEMPLATE(id) --1:N--> LISTING(item_template_id)

LISTING(id) --1:1--> TRANSACTION(listing_id)
LISTING(id) --1:N--> LISTING_IMAGE(listing_id)

TRANSACTION(id) --1:1--> ESCROW_PAYMENT(transaction_id)
TRANSACTION(id) --1:1--> DISPUTE(transaction_id)
TRANSACTION(id) --1:N--> RATING(transaction_id)

WALLET(id) --1:N--> WALLET_TX(wallet_id)

DISPUTE(id) --1:N--> DISPUTE_MSG(dispute_id)
6.4 Динамическая схема данных для категоризации
Для поддержки различных игр с их уникальными типами товаров и атрибутами предметов необходима гибкая схема данных:
sql-- Игры
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Категории товаров (иерархическая структура)
CREATE TABLE item_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id),
    parent_id UUID REFERENCES item_categories(id),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    level INTEGER NOT NULL, -- уровень вложенности
    sort_order INTEGER NOT NULL DEFAULT 0,
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT unique_category_slug_per_game UNIQUE (game_id, slug)
);

-- Атрибуты категорий
CREATE TABLE category_attributes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES item_categories(id),
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    attribute_type TEXT NOT NULL, -- string, number, boolean, enum, object
    is_required BOOLEAN DEFAULT FALSE,
    is_filterable BOOLEAN DEFAULT FALSE,
    is_searchable BOOLEAN DEFAULT FALSE,
    default_value JSONB,
    validation_rules JSONB,
    enum_values JSONB,
    sub_attributes JSONB, -- для вложенных объектов
    sort_order INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT unique_attribute_per_category UNIQUE (category_id, name)
);

-- Шаблоны предметов с динамическими атрибутами
CREATE TABLE item_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id),
    category_id UUID NOT NULL REFERENCES item_categories(id),
    name TEXT NOT NULL,
    description TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Расширенная таблица лотов для поддержки категорий и атрибутов
CREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID NOT NULL REFERENCES users(id),
    game_id UUID NOT NULL REFERENCES games(id),
    category_id UUID NOT NULL REFERENCES item_categories(id),
    item_template_id UUID REFERENCES item_templates(id), -- опционально
    title TEXT NOT NULL,
    description TEXT,
    price NUMERIC(14,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    delivery_method TEXT NOT NULL,
    delivery_time TEXT NOT NULL,
    status listing_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Изображения лотов
CREATE TABLE listing_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- Индексы для эффективного поиска
CREATE INDEX idx_listings_game ON listings(game_id);
CREATE INDEX idx_listings_category ON listings(category_id);
CREATE INDEX idx_listings_seller ON listings(seller_id);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_listings_price ON listings(price);
CREATE INDEX idx_item_templates_game ON item_templates(game_id);
CREATE INDEX idx_item_templates_category ON item_templates(category_id);
CREATE INDEX idx_item_categories_game ON item_categories(game_id);
CREATE INDEX idx_item_categories_parent ON item_categories(parent_id);

-- Полнотекстовый поиск
CREATE INDEX idx_listings_title_trgm ON listings USING GIN (title gin_trgm_ops);
CREATE INDEX idx_listings_description_trgm ON listings USING GIN (description gin_trgm_ops);

-- Индексы для JSON атрибутов (для фильтрации)
CREATE INDEX idx_listings_attrs ON listings USING GIN(attributes);
CREATE INDEX idx_item_templates_attrs ON item_templates USING GIN(attributes);
6.5 Модель данных для чата
sql-- Таблица чатов (по транзакциям)
CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id),
    buyer_id UUID NOT NULL REFERENCES users(id),
    seller_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMPTZ, -- 30 дней после закрытия транзакции
    CONSTRAINT unique_transaction_chat UNIQUE (transaction_id)
);

-- Таблица сообщений
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES chats(id),
    sender_id UUID NOT NULL REFERENCES users(id),
    recipient_id UUID NOT NULL REFERENCES users(id),
    content TEXT,
    message_type message_type NOT NULL DEFAULT 'text',
    image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at TIMESTAMPTZ,
    is_system BOOLEAN NOT NULL DEFAULT false,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

-- Тип сообщения
CREATE TYPE message_type AS ENUM ('text', 'image', 'system');

-- Индексы
CREATE INDEX idx_chat_transaction ON chats(transaction_id);
CREATE INDEX idx_chat_buyer ON chats(buyer_id);
CREATE INDEX idx_chat_seller ON chats(seller_id);
CREATE INDEX idx_chat_message_chat ON chat_messages(chat_id);
CREATE INDEX idx_chat_message_sender ON chat_messages(sender_id);
CREATE INDEX idx_chat_message_recipient ON chat_messages(recipient_id);
CREATE INDEX idx_chat_message_created ON chat_messages(created_at);
CREATE INDEX idx_chat_message_unread ON chat_messages(recipient_id, read_at) 
    WHERE read_at IS NULL;
7. Асинхронные события (RabbitMQ → topic marketplace.events)
EventProducerСхема payloaditem_listedmarketplace‑svc{ listing_id, seller_id, price }transaction_createdmarketplace‑svc{ txn_id, buyer_id, amount }payment_capturedpayment‑svc{ txn_id, amount, fee }transaction_completedmarketplace‑svc{ txn_id, rating_url }dispute_openedfraud‑svc{ dispute_id, reason }message_sentchat-svc{ message_id, chat_id, sender_id, recipient_id }
Пример схемы Avro для события transaction_created
json{
  "type": "record",
  "name": "TransactionCreated",
  "namespace": "com.gamemarket.events.v1",
  "fields": [
    { "name": "txn_id", "type": "string" },
    { "name": "buyer_id", "type": "string" },
    { "name": "seller_id", "type": "string" },
    { "name": "listing_id", "type": "string" },
    { "name": "amount", "type": "string" },
    { "name": "currency", "type": "string" },
    { "name": "created_at", "type": "string" },
    { "name": "item_name", "type": ["null", "string"], "default": null }
  ]
}
8. Frontend
8.1 Ключевые страницы

Главная страница (последние лоты, популярные игры)
Каталог предметов с фильтрами
Страница лота с деталями и кнопкой покупки
Личный кабинет (профиль, кошелек, история)
Страница продавца (форма создания лота)
Страница покупки (подтверждение, оплата, чат с продавцом)
Страница спора (доказательства, переписка)
Админ-панель с дашбордами и управлением

8.2 Макеты UI
┌─ Главная страница ─────────────────────────────────────┐
│                                                         │
│  ┌──────────┐ ┌───────────────────────────────────┐    │
│  │ Логотип  │ │ Поиск                        [🔍] │    │
│  └──────────┘ └───────────────────────────────────┘    │
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Игра 1  │ │ Игра 2  │ │ Игра 3  │ │ Игра 4  │ ...   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                         │
│  Популярные предметы                                    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐             │
│  │ [Изобр.]  │ │ [Изобр.]  │ │ [Изобр.]  │             │
│  │ Предмет 1 │ │ Предмет 2 │ │ Предмет 3 │ ...         │
│  │ $19.99    │ │ $24.50    │ │ $12.75    │             │
│  └───────────┘ └───────────┘ └───────────┘             │
│                                                         │
│  Последние добавленные                                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐             │
│  │ [Изобр.]  │ │ [Изобр.]  │ │ [Изобр.]  │             │
│  │ Предмет 4 │ │ Предмет 5 │ │ Предмет 6 │ ...         │
│  │ $35.00    │ │ $8.99     │ │ $42.25    │             │
│  └───────────┘ └───────────┘ └───────────┘             │
└─────────────────────────────────────────────────────────┘
9. Технические требования
9.1 Производительность

P95 latency < 200 ms для API запросов
Обработка 1000 RPS на пиковых нагрузках
Время загрузки страницы < 1.5 сек (FCP)
SLA 99.9% (43.8 минут даунтайма в месяц)

9.2 Масштабируемость

Горизонтальное масштабирование через Kubernetes HPA
Шардирование базы данных по мере роста
Кеширование часто запрашиваемых данных в Redis
Асинхронная обработка тяжелых операций через очереди

9.3 Безопасность

OWASP Top-10 проверки (автоматические и ручные)
Хранение паролей с использованием bcrypt/Argon2
Rate limiting для API запросов
HTTPS для всех соединений
Rotations секретов каждые 90 дней
WAF для защиты от DDoS и других атак

10. Инфраструктура
10.1 Развертывание

Kubernetes (EKS) с автомасштабированием
Multi-AZ для обеспечения высокой доступности
CI/CD через GitHub Actions + ArgoCD
Blue/Green deployments для zero-downtime обновлений

10.2 Мониторинг

Prometheus + Grafana для системных метрик
OpenTelemetry + Jaeger для трассировки запросов
OpenSearch + Fluent Bit для логов
PagerDuty интеграция для алертинга
Custom дашборды для бизнес-метрик

11. План разработки
11.1 Фазы проекта
ФазаДлительностьЦельВыходной артефактДизайн2 неделиПроработка архитектуры и интерфейсовУтвержденные макеты и схемыAlpha6 недельБазовая функциональностьMVP с auth+listings+transactionsBeta4 неделиПолный функционал# 