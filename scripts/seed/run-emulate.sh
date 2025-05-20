#!/bin/bash

# Скрипт для запуска всех эмуляторов API в Docker
# Выполняет эмуляцию запросов к API последовательно:
# 1. auth_emulator.py - Эмуляция запросов к API auth-svc для создания пользователей
# 2. marketplace_emulator.py - Эмуляция запросов к API marketplace-svc для создания объявлений
# 3. payment_emulator.py - Эмуляция запросов к API payment-svc для создания транзакций, кошельков и продаж

set -e  # Выход при любой ошибке

# Задержка в секундах между запусками скриптов
SCRIPT_DELAY=5

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SHARED_DATA_DIR="${SCRIPT_DIR}/data"
mkdir -p "${SHARED_DATA_DIR}"

echo "🔍 Проверка работы Docker и docker-compose..."
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker или docker-compose не установлены!"
    exit 1
fi

echo "🧪 Проверка доступности сервисов..."
docker-compose ps auth-svc marketplace-svc payment-svc --format json | grep -q "running" || {
    echo "❌ Сервисы не запущены! Запустите их с помощью docker-compose up -d"
    exit 1
}

# Копируем скрипты в контейнеры
echo "📋 Копируем скрипты внутрь контейнеров..."
docker cp "${SCRIPT_DIR}/auth_emulator.py" $(docker-compose ps -q auth-svc):/app/scripts/
docker cp "${SCRIPT_DIR}/marketplace_emulator.py" $(docker-compose ps -q marketplace-svc):/app/scripts/
docker cp "${SCRIPT_DIR}/payment_emulator.py" $(docker-compose ps -q payment-svc):/app/scripts/

# Создаем директории для файлов с данными в контейнерах
echo "📁 Создаем директории для файлов с данными в контейнерах..."
docker-compose exec -T auth-svc mkdir -p /app/scripts/seed/data
docker-compose exec -T marketplace-svc mkdir -p /app/scripts/seed/data
docker-compose exec -T payment-svc mkdir -p /app/scripts/seed/data

# Убедимся, что все необходимые пакеты установлены в контейнерах
echo "📦 Установка необходимых пакетов в контейнерах..."
docker-compose exec -T auth-svc pip install requests
docker-compose exec -T marketplace-svc pip install requests
docker-compose exec -T payment-svc pip install requests

# Запуск эмулятора для auth-svc
echo "🔐 Запуск эмулятора API для auth-svc..."
docker-compose exec -T auth-svc python /app/scripts/auth_emulator.py

# Копируем данные из контейнера в общую директорию
echo "📋 Копируем данные из контейнера auth-svc..."
docker cp $(docker-compose ps -q auth-svc):/app/scripts/seed/data/auth_seed_data.json "${SHARED_DATA_DIR}/"

# Проверяем, что файл данных auth создан
AUTH_DATA="${SHARED_DATA_DIR}/auth_seed_data.json"
if [ ! -f "${AUTH_DATA}" ]; then
    echo "❌ Данные авторизации не сгенерированы!"
    exit 1
fi

# Ждем перед следующим запуском
echo "⏱️ Ожидаем ${SCRIPT_DELAY} секунд перед следующим скриптом..."
sleep ${SCRIPT_DELAY}

# Копируем данные auth в контейнер marketplace-svc
echo "📨 Копируем данные авторизации в контейнер marketplace-svc..."
docker cp "${AUTH_DATA}" $(docker-compose ps -q marketplace-svc):/app/scripts/seed/data/auth_seed_data.json

# Запуск эмулятора для marketplace-svc
echo "🏪 Запуск эмулятора API для marketplace-svc..."
docker-compose exec -T marketplace-svc python /app/scripts/marketplace_emulator.py

# Копируем данные из контейнера в общую директорию
echo "📋 Копируем данные из контейнера marketplace-svc..."
docker cp $(docker-compose ps -q marketplace-svc):/app/scripts/seed/data/marketplace_seed_data.json "${SHARED_DATA_DIR}/"

# Проверяем, что файл данных marketplace создан
MARKETPLACE_DATA="${SHARED_DATA_DIR}/marketplace_seed_data.json"
if [ ! -f "${MARKETPLACE_DATA}" ]; then
    echo "❌ Данные маркетплейса не сгенерированы!"
    exit 1
fi

# Ждем перед следующим запуском
echo "⏱️ Ожидаем ${SCRIPT_DELAY} секунд перед следующим скриптом..."
sleep ${SCRIPT_DELAY}

# Копируем данные auth и marketplace в контейнер payment-svc
echo "📨 Копируем данные в контейнер payment-svc..."
docker cp "${AUTH_DATA}" $(docker-compose ps -q payment-svc):/app/scripts/seed/data/auth_seed_data.json
docker cp "${MARKETPLACE_DATA}" $(docker-compose ps -q payment-svc):/app/scripts/seed/data/marketplace_seed_data.json

# Запуск эмулятора для payment-svc
echo "💵 Запуск эмулятора API для payment-svc..."
docker-compose exec -T payment-svc python /app/scripts/payment_emulator.py

# Копируем данные из контейнера в общую директорию
echo "📋 Копируем данные из контейнера payment-svc..."
docker cp $(docker-compose ps -q payment-svc):/app/scripts/seed/data/payment_seed_data.json "${SHARED_DATA_DIR}/" || true

echo "✅ Все эмуляторы API выполнены успешно!"
echo "👨‍💻 Данные пользователей, объявлений и транзакций созданы через API!"

echo "📊 Статистика созданных данных:"
echo "--------------------------------"
if [ -f "${AUTH_DATA}" ]; then
    echo "Пользователи: $(jq '.users | length' ${AUTH_DATA} 2>/dev/null || echo "Ошибка чтения")"
fi
if [ -f "${MARKETPLACE_DATA}" ]; then
    echo "Объявления: $(jq '.listings | length' ${MARKETPLACE_DATA} 2>/dev/null || echo "Ошибка чтения")"
fi
if [ -f "${SHARED_DATA_DIR}/payment_seed_data.json" ]; then
    echo "Кошельки: $(jq '.wallets | length' ${SHARED_DATA_DIR}/payment_seed_data.json 2>/dev/null || echo "Ошибка чтения")"
    echo "Продажи: $(jq '.sales | length' ${SHARED_DATA_DIR}/payment_seed_data.json 2>/dev/null || echo "Ошибка чтения")"
fi
echo "--------------------------------"
echo "🎉 Все готово для тестирования!" 