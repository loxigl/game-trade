#!/usr/bin/env python3
"""
Скрипт для эмуляции реальных запросов к API payment-svc для создания кошельков, транзакций и продаж
через эндпоинты API вместо прямого доступа к БД
"""

import os
import sys
import json
import asyncio
import random
import requests
from datetime import datetime, timedelta
import uuid

# Константы
# PAYMENT_SERVICE_URL = "http://localhost/api/payment"  # URL к API payment-svc
PAYMENT_SERVICE_URL = "http://payment-svc:8000"  # URL к API payment-svc внутри Docker-сети
DATA_DIR = "scripts/seed/data"
AUTH_DATA_FILE = os.path.join(DATA_DIR, "auth_seed_data.json")
MARKETPLACE_DATA_FILE = os.path.join(DATA_DIR, "marketplace_seed_data.json")
DATA_FILE = os.path.join(DATA_DIR, "payment_seed_data.json")

# Подготовка директории для экспорта данных
def prepare_export_dir():
    """
    Создает директорию для экспорта данных
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"✅ Директория {DATA_DIR} создана/существует")

# Проверка, что сервис запущен
def check_service():
    """
    Проверяет, доступен ли сервис payment-svc
    """
    try:
        response = requests.get(f"{PAYMENT_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Сервис payment-svc доступен")
            return True
        else:
            print(f"❌ Сервис payment-svc недоступен, код ответа: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Ошибка при проверке доступности сервиса payment-svc: {e}")
        return False

# Загрузка данных пользователей из файла
def load_user_data():
    """
    Загружает данные пользователей из файла
    
    Returns:
        list: Список данных пользователей
    """
    try:
        with open(AUTH_DATA_FILE, 'r') as f:
            data = json.load(f)
            if "users" in data and len(data["users"]) > 0:
                print(f"✅ Загружено {len(data['users'])} пользователей из {AUTH_DATA_FILE}")
                return data["users"]
            else:
                print("❌ Нет данных пользователей в файле")
                return []
    except FileNotFoundError:
        print(f"❌ Файл с данными пользователей не найден: {AUTH_DATA_FILE}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Ошибка при чтении JSON из файла: {AUTH_DATA_FILE}")
        return []

# Загрузка данных объявлений из файла
def load_listing_data():
    """
    Загружает данные объявлений из файла
    
    Returns:
        list: Список данных объявлений
    """
    try:
        with open(MARKETPLACE_DATA_FILE, 'r') as f:
            data = json.load(f)
            if "listings" in data and len(data["listings"]) > 0:
                print(f"✅ Загружено {len(data['listings'])} объявлений из {MARKETPLACE_DATA_FILE}")
                return data["listings"]
            else:
                print("❌ Нет данных объявлений в файле")
                return []
    except FileNotFoundError:
        print(f"❌ Файл с данными объявлений не найден: {MARKETPLACE_DATA_FILE}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Ошибка при чтении JSON из файла: {MARKETPLACE_DATA_FILE}")
        return []

# Проверка существующих данных
def check_existing_data():
    """
    Проверяет, есть ли уже созданные данные в файле
    
    Returns:
        dict: Словарь с существующими данными или пустой словарь
    """
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if data:
                print(f"⚠️ Уже есть созданные данные платежного сервиса. Используем их.")
                return data
            else:
                return {}
    except FileNotFoundError:
        return {}  # Файл не существует, продолжаем создание данных
    except json.JSONDecodeError:
        return {}  # Ошибка при чтении JSON, продолжаем создание данных

# Создание кошельков для пользователей
def create_wallets(users):
    """
    Создает кошельки для пользователей через API
    
    Args:
        users: Список пользователей
    
    Returns:
        list: Список созданных кошельков
    """
    wallets = []
    
    for user in users:
        # Получаем токен пользователя
        token = user.get("token")
        if not token:
            print(f"⚠️ Пользователь {user.get('username')} не имеет токена, пропускаем создание кошелька")
            continue
        
        # Создаем кошелек через API
        print(f"🔄 Создание кошелька для пользователя {user.get('username')}")
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Проверяем, есть ли уже кошелек
            check_response = requests.get(
                f"{PAYMENT_SERVICE_URL}/wallets/my",
                headers=headers,
                timeout=10
            )
            
            wallet = None
            
            # Если кошелек существует, используем его
            if check_response.status_code == 200:
                wallet = check_response.json()
                print(f"   ✅ Кошелек для пользователя {user.get('username')} уже существует")
            # Если нет, создаем новый
            else:
                # Создаем кошелек
                wallet_response = requests.post(
                    f"{PAYMENT_SERVICE_URL}/wallets",
                    headers=headers,
                    timeout=10
                )
                
                if wallet_response.status_code in [200, 201]:
                    wallet = wallet_response.json()
                    print(f"   ✅ Кошелек для пользователя {user.get('username')} успешно создан")
                else:
                    print(f"   ❌ Не удалось создать кошелек для пользователя {user.get('username')}, код ответа: {wallet_response.status_code}")
                    if wallet_response.text:
                        try:
                            error_data = wallet_response.json()
                            print(f"      Ошибка: {error_data}")
                        except:
                            print(f"      Ответ: {wallet_response.text}")
                    continue  # Пропускаем этого пользователя
            
            # Пополняем кошелек (начальные средства)
            if wallet:
                wallet_id = wallet.get("id")
                initial_balance = random.randint(1000, 5000)
                
                # Только администраторы могут пополнять кошельки через API
                # Получаем токен администратора
                admin_user = next((u for u in users if u.get("is_admin", False)), None)
                if not admin_user:
                    print("   ⚠️ Администратор не найден, невозможно пополнить кошелек")
                    # Добавляем кошелек с балансом 0
                    wallet["user_id"] = user.get("id")
                    wallet["username"] = user.get("username")
                    wallets.append(wallet)
                    continue
                
                admin_token = admin_user.get("token")
                if not admin_token:
                    print("   ⚠️ Токен администратора не найден, невозможно пополнить кошелек")
                    # Добавляем кошелек с балансом 0
                    wallet["user_id"] = user.get("id")
                    wallet["username"] = user.get("username")
                    wallets.append(wallet)
                    continue
                
                # Пополняем кошелек через API с токеном администратора
                deposit_data = {
                    "amount": initial_balance,
                    "description": "Initial balance"
                }
                
                deposit_response = requests.post(
                    f"{PAYMENT_SERVICE_URL}/wallets/{wallet_id}/deposit",
                    json=deposit_data,
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10
                )
                
                if deposit_response.status_code in [200, 201]:
                    # Обновляем данные кошелька после пополнения
                    updated_wallet = deposit_response.json()
                    updated_wallet["user_id"] = user.get("id")
                    updated_wallet["username"] = user.get("username")
                    wallets.append(updated_wallet)
                    print(f"   💰 Кошелек пользователя {user.get('username')} пополнен на {initial_balance}")
                else:
                    print(f"   ⚠️ Не удалось пополнить кошелек пользователя {user.get('username')}, код ответа: {deposit_response.status_code}")
                    # Добавляем кошелек с балансом 0
                    wallet["user_id"] = user.get("id")
                    wallet["username"] = user.get("username")
                    wallets.append(wallet)
        except requests.RequestException as e:
            print(f"   ❌ Ошибка при создании кошелька для пользователя {user.get('username')}: {e}")
    
    print(f"✅ Создано и настроено {len(wallets)} кошельков")
    return wallets

# Создание продаж для объявлений
def create_sales(users, listings, wallets):
    """
    Создает продажи для объявлений через API
    
    Args:
        users: Список пользователей
        listings: Список объявлений
        wallets: Список кошельков
    
    Returns:
        list: Список созданных продаж
    """
    sales = []
    
    # Если нет пользователей или объявлений, выходим
    if not users or not listings:
        print("⚠️ Недостаточно данных для создания продаж")
        return sales
    
    # Получаем список пользователей, у которых есть токены
    valid_users = [user for user in users if user.get("token")]
    
    # Выбираем случайные объявления для продажи (не более 30% от всех объявлений)
    num_sales = min(int(len(listings) * 0.3), len(listings))
    if num_sales == 0:
        print("⚠️ Нет объявлений для создания продаж")
        return sales
    
    sale_listings = random.sample(listings, num_sales)
    
    print(f"🔄 Создание {num_sales} продаж из случайных объявлений")
    
    for listing in sale_listings:
        # Получаем данные продавца
        seller_id = listing.get("seller", {}).get("id")
        if not seller_id:
            print(f"   ⚠️ Объявление {listing.get('id')} не имеет данных о продавце, пропускаем")
            continue
        
        # Исключаем продавца из списка покупателей
        potential_buyers = [user for user in valid_users if user.get("id") != seller_id]
        if not potential_buyers:
            print(f"   ⚠️ Нет подходящих покупателей для объявления {listing.get('id')}, пропускаем")
            continue
        
        # Выбираем случайного покупателя
        buyer = random.choice(potential_buyers)
        buyer_token = buyer.get("token")
        
        # Получаем кошелек покупателя
        buyer_wallet = next((w for w in wallets if w.get("user_id") == buyer.get("id")), None)
        if not buyer_wallet:
            print(f"   ⚠️ У покупателя {buyer.get('username')} нет кошелька, пропускаем")
            continue
        
        # Проверяем, достаточно ли средств
        listing_price = listing.get("price", 0)
        buyer_balance = buyer_wallet.get("balance", 0)
        
        if buyer_balance < listing_price:
            print(f"   ⚠️ У покупателя {buyer.get('username')} недостаточно средств для покупки объявления {listing.get('id')}, пропускаем")
            continue
        
        # Создаем продажу через API
        try:
            # Данные для создания продажи
            sale_data = {
                "listing_id": listing.get("id"),
                "quantity": 1
            }
            
            # Отправляем запрос на создание продажи
            headers = {"Authorization": f"Bearer {buyer_token}"}
            
            sale_response = requests.post(
                f"{PAYMENT_SERVICE_URL}/sales",
                json=sale_data,
                headers=headers,
                timeout=10
            )
            
            if sale_response.status_code in [200, 201]:
                sale = sale_response.json()
                
                # Подтверждаем оплату продажи
                payment_response = requests.post(
                    f"{PAYMENT_SERVICE_URL}/sales/{sale.get('id')}/pay",
                    headers=headers,
                    timeout=10
                )
                
                if payment_response.status_code in [200, 201]:
                    # Добавляем дополнительные данные для экспорта
                    paid_sale = payment_response.json()
                    paid_sale["buyer"] = {
                        "id": buyer.get("id"),
                        "username": buyer.get("username")
                    }
                    paid_sale["seller"] = {
                        "id": seller_id,
                        "username": listing.get("seller", {}).get("username")
                    }
                    paid_sale["listing"] = {
                        "id": listing.get("id"),
                        "title": listing.get("title")
                    }
                    
                    sales.append(paid_sale)
                    print(f"   ✅ Создана и оплачена продажа для объявления '{listing.get('title')}', покупатель: {buyer.get('username')}")
                else:
                    print(f"   ❌ Не удалось оплатить продажу для объявления {listing.get('id')}, код ответа: {payment_response.status_code}")
                    if payment_response.text:
                        try:
                            error_data = payment_response.json()
                            print(f"      Ошибка: {error_data}")
                        except:
                            print(f"      Ответ: {payment_response.text}")
            else:
                print(f"   ❌ Не удалось создать продажу для объявления {listing.get('id')}, код ответа: {sale_response.status_code}")
                if sale_response.text:
                    try:
                        error_data = sale_response.json()
                        print(f"      Ошибка: {error_data}")
                    except:
                        print(f"      Ответ: {sale_response.text}")
        except requests.RequestException as e:
            print(f"   ❌ Ошибка при создании продажи для объявления {listing.get('id')}: {e}")
    
    print(f"✅ Создано {len(sales)} продаж")
    return sales

# Экспорт данных
def export_payment_data(wallets, sales):
    """
    Экспортирует данные кошельков и продаж в JSON-файл
    
    Args:
        wallets: Список кошельков
        sales: Список продаж
    """
    try:
        data = {
            "wallets": wallets,
            "sales": sales
        }
        
        # Сохраняем данные в JSON-файл
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные платежного сервиса экспортированы в {DATA_FILE}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте данных платежного сервиса: {e}")

# Основная функция
async def run_payment_emulator():
    """
    Эмулирует запросы к API payment-svc
    """
    print("🔄 Начало эмуляции запросов к API payment-svc...")
    
    prepare_export_dir()
    
    if not check_service():
        print("❌ Невозможно продолжить, сервис payment-svc недоступен")
        return False
    
    # Проверяем существующие данные
    existing_data = check_existing_data()
    if existing_data and "wallets" in existing_data and "sales" in existing_data:
        print("✅ Используем существующие данные платежного сервиса")
        return True
    
    # Загружаем данные пользователей и объявлений
    users = load_user_data()
    if not users:
        print("❌ Нет данных пользователей для создания кошельков и продаж")
        return False
    
    listings = load_listing_data()
    if not listings:
        print("⚠️ Нет данных объявлений для создания продаж. Продолжаем только с кошельками.")
    
    # Создаем кошельки
    wallets = create_wallets(users)
    
    # Создаем продажи, если есть объявления
    sales = []
    if listings:
        sales = create_sales(users, listings, wallets)
    
    # Экспортируем данные
    export_payment_data(wallets, sales)
    
    print("✅ Эмуляция запросов к API payment-svc успешно завершена!")
    return True

# Запуск скрипта
if __name__ == "__main__":
    success = asyncio.run(run_payment_emulator())
    sys.exit(0 if success else 1) 