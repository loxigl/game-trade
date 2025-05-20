#!/usr/bin/env python3
"""
Скрипт для эмуляции реальных запросов к API marketplace-svc для создания объявлений
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
# MARKETPLACE_SERVICE_URL = "http://localhost/api/marketplace"  # URL к API marketplace-svc
MARKETPLACE_SERVICE_URL = "http://marketplace-svc:8000"  # URL к API marketplace-svc внутри Docker-сети
DATA_DIR = "scripts/seed/data"
AUTH_DATA_FILE = os.path.join(DATA_DIR, "auth_seed_data.json")
DATA_FILE = os.path.join(DATA_DIR, "marketplace_seed_data.json")

# Категории игр и товаров
GAME_CATEGORIES = [
    "RPG", "MMORPG", "FPS", "Strategy", "Simulation", "Sports", 
    "Adventure", "Action", "Racing", "Puzzle", "Platformer", "Fighting"
]

ITEM_TYPES = [
    "Game Account", "In-Game Currency", "Items & Skins", "Game Key", 
    "Power Leveling", "Boosting", "Coaching"
]

GAMES = [
    {
        "name": "World of Warcraft",
        "item_names": ["Epic Mount", "Legendary Weapon", "Rare Pet", "Gold", "Epic Account", "Raid Boost", "PvP Boost"]
    },
    {
        "name": "Counter-Strike 2",
        "item_names": ["Knife Skin", "Glove Skin", "AWP Skin", "AK-47 Skin", "Rank Boost", "Tournament Account", "FACEIT Level 10"]
    },
    {
        "name": "Dota 2",
        "item_names": ["Arcana Set", "Immortal Item", "Courier", "MMR Boost", "Battle Pass Levels", "Tournament Account", "Coaching Session"]
    },
    {
        "name": "League of Legends",
        "item_names": ["Champion Skin", "Rare Account", "Ranked Boost", "Coaching Session", "Riot Points", "Tournament Rewards", "Seasonal Boost"]
    },
    {
        "name": "Fortnite",
        "item_names": ["Rare Skin", "Battle Pass", "V-Bucks", "Account With Exclusives", "Tournament Ready Account", "Competitive Coaching", "Arena Points Boost"]
    },
    {
        "name": "Minecraft",
        "item_names": ["Modded Account", "Rare Username", "Server Access", "Resource Pack", "Marketplace Content", "Custom Build", "Coaching Session"]
    },
    {
        "name": "Apex Legends",
        "item_names": ["Heirloom Account", "Legend Tokens", "Apex Coins", "Ranked Boost", "Badges Boost", "Tournament Account", "Coaching Session"]
    },
    {
        "name": "Genshin Impact",
        "item_names": ["5-Star Character Account", "Primogems", "Artifacts", "Weapons", "Adventure Rank Boost", "Abyss Completion", "Story Quest Help"]
    },
    {
        "name": "Roblox",
        "item_names": ["Rare Limited Item", "Robux", "Premium Account", "Rare Username", "Game Development", "Coaching", "Custom Avatar"]
    },
    {
        "name": "Valorant",
        "item_names": ["Skin Collection", "Ranked Account", "Radianite Points", "Rank Boost", "Tournament Account", "Coaching Session", "Agent Unlock"]
    }
]

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
    Проверяет, доступен ли сервис marketplace-svc
    """
    try:
        response = requests.get(f"{MARKETPLACE_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Сервис marketplace-svc доступен")
            return True
        else:
            print(f"❌ Сервис marketplace-svc недоступен, код ответа: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Ошибка при проверке доступности сервиса marketplace-svc: {e}")
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

# Проверка существующих объявлений
def check_existing_listings():
    """
    Проверяет, есть ли уже созданные объявления в файле
    
    Returns:
        list: Список существующих объявлений или пустой список
    """
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if "listings" in data and len(data["listings"]) > 0:
                print(f"⚠️ Уже есть {len(data['listings'])} созданных объявлений. Используем их.")
                return data["listings"]
            else:
                return []
    except FileNotFoundError:
        return []  # Файл не существует, продолжаем создание объявлений
    except json.JSONDecodeError:
        return []  # Ошибка при чтении JSON, продолжаем создание объявлений

# Создание объявлений через API
def create_listings(users):
    """
    Создает объявления через API для каждого пользователя
    
    Args:
        users: Список пользователей
    
    Returns:
        list: Список созданных объявлений
    """
    # Проверяем существующие объявления
    existing_listings = check_existing_listings()
    if existing_listings:
        return existing_listings
    
    all_listings = []
    
    # Каждый пользователь создает несколько объявлений
    for user in users:
        # Пропускаем администратора
        if user.get("is_admin", False):
            continue
        
        # Получаем токен пользователя
        token = user.get("token")
        if not token:
            print(f"⚠️ Пользователь {user.get('username')} не имеет токена, пропускаем")
            continue
            
        # Создаем от 1 до 5 объявлений для каждого пользователя
        num_listings = random.randint(1, 5)
        print(f"🔄 Создание {num_listings} объявлений для пользователя {user.get('username')}")
        
        for _ in range(num_listings):
            # Выбираем случайную игру
            game = random.choice(GAMES)
            game_name = game["name"]
            
            # Выбираем случайный тип товара и название
            item_type = random.choice(ITEM_TYPES)
            item_name = random.choice(game["item_names"])
            
            # Генерируем цену
            price = random.randint(5, 1000)
            
            # Генерируем случайные данные для объявления
            title = f"{item_name} - {game_name}"
            description = f"""Продается {item_name} для игры {game_name}.
            
Товар данного типа: {item_type}
            
Это уникальное предложение от продавца {user.get('username')}. 
Безопасная сделка гарантирована платформой GameTrade!

Характеристики:
- Высокое качество
- Мгновенная доставка
- 100% безопасность
            
Контакты для связи внутри платформы после покупки.
            """
            
            # Категория объявления (категория игры)
            category = random.choice(GAME_CATEGORIES)
            
            # Фото для объявления (случайные изображения)
            photos = [
                f"https://picsum.photos/id/{random.randint(1, 200)}/300/200",
                f"https://picsum.photos/id/{random.randint(201, 400)}/300/200"
            ]
            
            # Данные для создания объявления
            listing_data = {
                "title": title,
                "description": description,
                "price": price,
                "category": category,
                "game": game_name,
                "item_type": item_type,
                "photos": photos,
                "quantity": random.randint(1, 10),
                "condition": random.choice(["New", "Used", "Digital"])
            }
            
            # Отправляем запрос на создание объявления
            try:
                headers = {"Authorization": f"Bearer {token}"}
                
                response = requests.post(
                    f"{MARKETPLACE_SERVICE_URL}/listings",
                    json=listing_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    listing_data = response.json()
                    listing_id = listing_data.get("id")
                    
                    # Если объявление дороже 500, делаем его премиум (для некоторых)
                    if price > 500 and random.random() < 0.3:
                        promote_data = {"featured": True}
                        promote_response = requests.patch(
                            f"{MARKETPLACE_SERVICE_URL}/listings/{listing_id}/promote",
                            json=promote_data,
                            headers=headers,
                            timeout=10
                        )
                        
                        if promote_response.status_code == 200:
                            listing_data["featured"] = True
                            print(f"   ⭐ Объявление '{title}' помечено как премиум")
                    
                    # Добавляем данные пользователя к объявлению для экспорта
                    listing_data["seller"] = {
                        "id": user.get("id"),
                        "username": user.get("username"),
                        "email": user.get("email")
                    }
                    
                    all_listings.append(listing_data)
                    print(f"   ✅ Объявление '{title}' успешно создано")
                else:
                    print(f"   ❌ Не удалось создать объявление '{title}', код ответа: {response.status_code}")
                    if response.text:
                        try:
                            error_data = response.json()
                            print(f"      Ошибка: {error_data}")
                        except:
                            print(f"      Ответ: {response.text}")
            except requests.RequestException as e:
                print(f"   ❌ Ошибка при создании объявления '{title}': {e}")
    
    print(f"✅ Создано {len(all_listings)} объявлений")
    return all_listings

# Экспорт данных объявлений
def export_listing_data(listings):
    """
    Экспортирует данные объявлений в JSON-файл
    
    Args:
        listings: Список данных объявлений для экспорта
    """
    try:
        # Сохраняем данные в JSON-файл
        with open(DATA_FILE, 'w') as f:
            json.dump({"listings": listings}, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные объявлений экспортированы в {DATA_FILE}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте данных объявлений: {e}")

# Основная функция
async def run_marketplace_emulator():
    """
    Эмулирует запросы к API marketplace-svc
    """
    print("🔄 Начало эмуляции запросов к API marketplace-svc...")
    
    prepare_export_dir()
    
    if not check_service():
        print("❌ Невозможно продолжить, сервис marketplace-svc недоступен")
        return False
    
    users = load_user_data()
    if not users:
        print("❌ Нет данных пользователей для создания объявлений")
        return False
    
    listings = create_listings(users)
    export_listing_data(listings)
    
    print("✅ Эмуляция запросов к API marketplace-svc успешно завершена!")
    return True

# Запуск скрипта
if __name__ == "__main__":
    success = asyncio.run(run_marketplace_emulator())
    sys.exit(0 if success else 1) 