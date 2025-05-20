#!/bin/bash

# Скрипт для запуска всех seed скриптов в Docker
# Выполняет seed скрипты последовательно:
# 1. auth-svc - создание пользователей
# 2. marketplace-svc - создание объявлений для пользователей
# 3. payment-svc - создание транзакций, кошельков и продаж

set -e  # Выход при любой ошибке

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SHARED_DATA_DIR="${SCRIPT_DIR}/data"
AUTH_DATA="${SHARED_DATA_DIR}/auth_seed_data.json"
MARKETPLACE_DATA="${SHARED_DATA_DIR}/marketplace_seed_data.json"

# Создаем директорию для обмена данными между скриптами
mkdir -p "${SHARED_DATA_DIR}"

echo "🔍 Проверка работы Docker и docker-compose..."
if ! command -v docker &> /dev/null || ! command -v docker compose &> /dev/null; then
    echo "❌ Docker или docker-compose не установлены!"
    exit 1
fi

echo "🧪 Проверка доступности сервисов..."
docker-compose ps auth-svc marketplace-svc payment-svc --format json | grep -q "running" || {
    echo "❌ Сервисы не запущены! Запустите их с помощью docker-compose up -d"
    exit 1
}

# Проверка существования пути к скриптам в контейнерах
echo "🔄 Подготовка скриптов в контейнерах..."

# Копируем скрипты в контейнеры
echo "📋 Копируем скрипты внутрь контейнеров..."
docker cp "${SCRIPT_DIR}/auth_seed.py" $(docker-compose ps -q auth-svc):/app/scripts/
docker cp "${SCRIPT_DIR}/marketplace_seed.py" $(docker-compose ps -q marketplace-svc):/app/scripts/
docker cp "${SCRIPT_DIR}/payment_seed.py" $(docker-compose ps -q payment-svc):/app/scripts/

# Запуск seed скрипта для auth-svc
echo "🔐 Запуск seed скрипта для auth-svc..."
docker-compose exec -T auth-svc python /app/scripts/auth_seed.py

# Проверяем, что файл данных auth создан
if [ ! -f "${AUTH_DATA}" ]; then
    echo "❌ Данные авторизации не сгенерированы!"
    exit 1
fi

# Копируем данные auth в контейнер marketplace-svc
echo "📨 Копируем данные авторизации в контейнер marketplace-svc..."
docker cp "${AUTH_DATA}" $(docker-compose ps -q marketplace-svc):/app/scripts/data/auth_seed_data.json

# Запуск seed скрипта для marketplace-svc
echo "🏪 Запуск seed скрипта для marketplace-svc..."
docker-compose exec -T marketplace-svc python /app/scripts/marketplace_seed.py

# Проверяем, что файл данных marketplace создан
if [ ! -f "${MARKETPLACE_DATA}" ]; then
    echo "❌ Данные маркетплейса не сгенерированы!"
    exit 1
fi

# Копируем данные auth и marketplace в контейнер payment-svc
echo "📨 Копируем данные в контейнер payment-svc..."
docker cp "${AUTH_DATA}" $(docker-compose ps -q payment-svc):/app/scripts/data/auth_seed_data.json
docker cp "${MARKETPLACE_DATA}" $(docker-compose ps -q payment-svc):/app/scripts/data/marketplace_seed_data.json

# Запуск seed скрипта для payment-svc
echo "💵 Запуск seed скрипта для payment-svc..."
docker-compose exec -T payment-svc python /app/scripts/payment_seed.py

echo "✅ Все seed скрипты выполнены успешно!"
echo "👨‍💻 Данные пользователей, объявлений и транзакций созданы!" 