# Kubernetes Deployment для GameTrade

Эта директория содержит Kubernetes манифесты для развертывания микросервисного приложения GameTrade в различных окружениях.

## Структура директории

```
kubernetes/
├── base/                       # Базовые манифесты для всех окружений
│   ├── namespace.yaml          # Определение пространства имен
│   ├── postgres-auth.yaml         # БД сервиса auth
│   ├── postgres-marketplace.yaml  # БД сервиса marketplace
│   ├── postgres-payment.yaml      # БД сервиса payment
│   ├── postgres-chat.yaml         # БД сервиса chat
│   ├── redis.yaml              # Конфигурация кэш-сервера
│   ├── rabbitmq.yaml           # Конфигурация сервера очередей сообщений
│   ├── nginx.yaml              # Конфигурация API Gateway
│   ├── auth-svc.yaml           # Сервис авторизации
│   ├── marketplace-svc.yaml    # Сервис маркетплейса
│   ├── payment-svc.yaml        # Сервис платежей
│   ├── chat-svc.yaml           # Сервис чата
│   ├── service-template.yaml   # Шаблон для других сервисов
│   ├── autoscaler-template.yaml # Шаблон для автомасштабирования
│   └── kustomization.yaml      # Kustomize конфигурация для базового уровня
│
├── overlays/                   # Наложения для разных окружений
│   ├── dev/                    # Окружение разработки
│   │   ├── kustomization.yaml  # Kustomize конфигурация для dev
│   │   ├── patches/            # Патчи для dev-окружения
│   │   ├── postgres-dev.yaml   # Настройки PostgreSQL для всех сервисов в dev
│   │   └── redis-dev.yaml      # Специфические настройки Redis для dev
│   │
│   └── prod/                   # Производственное окружение
│       ├── kustomization.yaml  # Kustomize конфигурация для prod
│       ├── patches/            # Патчи для prod-окружения
│       ├── postgres-prod.yaml  # Настройки PostgreSQL для всех сервисов в prod
│       ├── redis-prod.yaml     # Специфические настройки Redis для prod
│       ├── nginx-prod.yaml     # Специфические настройки NGINX для prod
│       └── auth-svc-prod.yaml  # Специфические настройки сервиса auth для prod
│
└── README.md                   # Это файл
```

## Используемые технологии

- **Kubernetes**: Оркестрация контейнеров
- **Kustomize**: Настройка конфигураций для разных окружений
- **StatefulSets**: Для развертывания PostgreSQL и RabbitMQ
- **Deployments**: Для развертывания stateless сервисов
- **Services**: Для маршрутизации трафика
- **ConfigMaps**: Для управления конфигурацией
- **PersistentVolumeClaims**: Для хранения данных

## Компоненты приложения

- **PostgreSQL**: Основная база данных
- **Redis**: Кэширование и управление сессиями
- **RabbitMQ**: Очереди сообщений и асинхронная обработка
- **NGINX**: API Gateway для управления трафиком и маршрутизации
- **auth-svc**: Сервис авторизации и управления пользователями
- **marketplace-svc**: Сервис маркетплейса игровых ценностей
- **payment-svc**: Сервис платежей
- **chat-svc**: Сервис чата и коммуникаций

## Развертывание

### Развертывание в окружении разработки

```bash
# Применение конфигурации для dev-окружения
kubectl apply -k overlays/dev
```

### Развертывание в производственном окружении

```bash
# Применение конфигурации для prod-окружения
kubectl apply -k overlays/prod
```

## Управление ресурсами

Конфигурации для различных окружений используют разные параметры ресурсов:

- **Dev**: Минимальные ресурсы для локальной разработки и тестирования
- **Prod**: Масштабируемая конфигурация для реальной нагрузки

## Масштабирование

В производственном окружении настроено горизонтальное автомасштабирование (HPA) для следующих сервисов:
- auth-svc
- marketplace-svc
- payment-svc
- chat-svc
- nginx (API Gateway)

## Мониторинг

Для мониторинга NGINX используется Prometheus exporter, доступный через порт 9113.

## Безопасность

- Все секреты должны храниться в Kubernetes Secrets (не включены в эти манифесты для безопасности)
- В реальной продакшн-среде необходимо заменить плейсхолдеры для паролей и токенов
- Настроены соответствующие RBAC-правила и NetworkPolicies

## Примечания по эксплуатации

- Перед обновлением в продакшн-среде рекомендуется протестировать изменения в dev-окружении
- Для резервного копирования PostgreSQL используйте отдельные CronJob (не включен в эти манифесты)
- Журналы приложений и метрики должны быть интегрированы с внешними системами мониторинга 