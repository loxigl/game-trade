#!/usr/bin/env python3
"""
Скрипт для эмуляции реальных запросов к API auth-svc для создания пользователей
через эндпоинты регистрации вместо прямого доступа к БД
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
# AUTH_SERVICE_URL = "http://localhost/api/auth"  # URL к API auth-svc
AUTH_SERVICE_URL = "http://auth-svc:8000"  # URL к API auth-svc внутри Docker-сети
DATA_DIR = "scripts/seed/data"
DATA_FILE = os.path.join(DATA_DIR, "auth_seed_data.json")

# Тестовые данные для создания пользователей
USER_DATA = [
    {
        "email": "admin@gametrade.com",
        "username": "admin",
        "password": "admin123",
        "is_admin": True,
        "bio": "Администратор платформы GameTrade",
        "avatar": "https://randomuser.me/api/portraits/men/0.jpg"
    },
    {
        "email": "alice@example.com",
        "username": "alice",
        "password": "password123",
        "is_admin": False,
        "bio": "Опытный продавец цифровых товаров для игр",
        "avatar": "https://randomuser.me/api/portraits/women/1.jpg"
    },
    {
        "email": "bob@example.com",
        "username": "bob",
        "password": "password123",
        "is_admin": False,
        "bio": "Коллекционер редких внутриигровых предметов",
        "avatar": "https://randomuser.me/api/portraits/men/2.jpg"
    },
    {
        "email": "charlie@example.com",
        "username": "charlie",
        "password": "password123",
        "is_admin": False,
        "bio": "Профессиональный геймер и продавец аккаунтов",
        "avatar": "https://randomuser.me/api/portraits/men/3.jpg"
    },
    {
        "email": "diana@example.com", 
        "username": "diana",
        "password": "password123",
        "is_admin": False,
        "bio": "Стример и продавец внутриигровой валюты",
        "avatar": "https://randomuser.me/api/portraits/women/4.jpg"
    },
    {
        "email": "evan@example.com",
        "username": "evan",
        "password": "password123",
        "is_admin": False,
        "bio": "Новичок в мире торговли игровыми предметами",
        "avatar": "https://randomuser.me/api/portraits/men/5.jpg"
    },
    {
        "email": "fiona@example.com",
        "username": "fiona",
        "password": "password123",
        "is_admin": False,
        "bio": "Специалист по редким предметам World of Warcraft",
        "avatar": "https://randomuser.me/api/portraits/women/6.jpg"
    },
    {
        "email": "george@example.com",
        "username": "george",
        "password": "password123",
        "is_admin": False,
        "bio": "Продаю скины для CS:GO и Dota 2",
        "avatar": "https://randomuser.me/api/portraits/men/7.jpg"
    },
    {
        "email": "hannah@example.com",
        "username": "hannah",
        "password": "password123",
        "is_admin": False,
        "bio": "Художник, создаю и продаю моды для игр",
        "avatar": "https://randomuser.me/api/portraits/women/8.jpg"
    },
    {
        "email": "ivan@example.com",
        "username": "ivan",
        "password": "password123",
        "is_admin": False,
        "bio": "Покупаю и продаю аккаунты с редкими предметами",
        "avatar": "https://randomuser.me/api/portraits/men/9.jpg"
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
    Проверяет, доступен ли сервис auth-svc
    """
    try:
        response = requests.get(f"{AUTH_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Сервис auth-svc доступен")
            return True
        else:
            print(f"❌ Сервис auth-svc недоступен, код ответа: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Ошибка при проверке доступности сервиса auth-svc: {e}")
        return False

# Регистрация пользователей через API
def register_users():
    """
    Регистрирует пользователей через эндпоинт регистрации
    
    Returns:
        list: Список зарегистрированных пользователей и их токенов
    """
    registered_users = []
    admin_token = None
    
    # Проверим, есть ли уже зарегистрированные пользователи
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if data and "users" in data and len(data["users"]) > 0:
                print(f"⚠️ Уже есть {len(data['users'])} зарегистрированных пользователей. Используем их.")
                return data["users"]
    except FileNotFoundError:
        pass  # Файл не существует, продолжаем регистрацию
    
    for user_data in USER_DATA:
        # Создаем данные для запроса регистрации
        register_data = {
            "email": user_data["email"],
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        # Отправляем запрос на регистрацию
        try:
            print(f"🔄 Регистрация пользователя: {user_data['username']}")
            response = requests.post(
                f"{AUTH_SERVICE_URL}/register", 
                json=register_data,
                timeout=10
            )
            
            if response.status_code == 201:
                user_id = response.json().get("user_id")
                
                # Логинимся для получения токена
                login_data = {
                    "username": user_data["email"],  # Обычно вход по email
                    "password": user_data["password"]
                }
                
                login_response = requests.post(
                    f"{AUTH_SERVICE_URL}/login", 
                    json=login_data,
                    timeout=10
                )
                
                if login_response.status_code == 200:
                    access_token = login_response.json().get("access_token")
                    
                    # Сохраняем токен администратора для дальнейшего использования
                    if user_data["is_admin"] and admin_token is None:
                        admin_token = access_token
                    
                    # Получаем профиль пользователя
                    headers = {"Authorization": f"Bearer {access_token}"}
                    profile_response = requests.get(
                        f"{AUTH_SERVICE_URL}/me", 
                        headers=headers,
                        timeout=10
                    )
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        
                        # Обновляем профиль пользователя
                        update_data = {
                            "bio": user_data["bio"],
                            "avatar_url": user_data["avatar"]
                        }
                        
                        update_response = requests.patch(
                            f"{AUTH_SERVICE_URL}/account/profile", 
                            json=update_data,
                            headers=headers,
                            timeout=10
                        )
                        
                        if update_response.status_code == 200:
                            # Если это админ, присваиваем роль администратора
                            if user_data["is_admin"] and admin_token:
                                # Получаем список ролей
                                roles_response = requests.get(
                                    f"{AUTH_SERVICE_URL}/roles",
                                    headers={"Authorization": f"Bearer {admin_token}"},
                                    timeout=10
                                )
                                
                                if roles_response.status_code == 200:
                                    roles = roles_response.json()
                                    admin_role_id = None
                                    
                                    # Ищем роль администратора
                                    for role in roles:
                                        if role.get("name").lower() == "admin":
                                            admin_role_id = role.get("id")
                                            break
                                    
                                    # Если нашли роль админа, присваиваем пользователю
                                    if admin_role_id:
                                        role_assign_response = requests.post(
                                            f"{AUTH_SERVICE_URL}/users/{user_id}/roles/{admin_role_id}",
                                            headers={"Authorization": f"Bearer {admin_token}"},
                                            timeout=10
                                        )
                                        
                                        if role_assign_response.status_code not in [200, 201]:
                                            print(f"⚠️ Не удалось присвоить роль администратора пользователю {user_data['username']}")
                            
                            # Подготавливаем данные пользователя для экспорта
                            export_data = {
                                "id": profile_data.get("id"),
                                "email": user_data["email"],
                                "username": user_data["username"],
                                "is_verified": True,
                                "is_admin": user_data["is_admin"],
                                "created_at": datetime.now().isoformat(),
                                "profile": {
                                    "id": profile_data.get("profile", {}).get("id"),
                                    "avatar_url": user_data["avatar"],
                                    "bio": user_data["bio"]
                                },
                                "token": access_token
                            }
                            
                            registered_users.append(export_data)
                            print(f"✅ Пользователь {user_data['username']} успешно зарегистрирован и настроен")
                        else:
                            print(f"⚠️ Не удалось обновить профиль пользователя {user_data['username']}")
                    else:
                        print(f"⚠️ Не удалось получить профиль пользователя {user_data['username']}")
                else:
                    print(f"⚠️ Не удалось войти в систему пользователем {user_data['username']}")
            else:
                print(f"⚠️ Не удалось зарегистрировать пользователя {user_data['username']}, код ответа: {response.status_code}")
                if response.text:
                    try:
                        error_data = response.json()
                        print(f"   Ошибка: {error_data}")
                    except:
                        print(f"   Ответ: {response.text}")
        except requests.RequestException as e:
            print(f"❌ Ошибка при регистрации пользователя {user_data['username']}: {e}")
    
    print(f"✅ Зарегистрировано {len(registered_users)} пользователей")
    return registered_users

# Экспорт данных пользователей для других сервисов
def export_user_data(users):
    """
    Экспортирует данные пользователей в JSON-файл
    
    Args:
        users: Список данных пользователей для экспорта
    """
    try:
        # Сохраняем данные в JSON-файл
        with open(DATA_FILE, 'w') as f:
            json.dump({"users": users}, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные пользователей экспортированы в {DATA_FILE}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте данных пользователей: {e}")

# Основная функция 
async def run_auth_emulator():
    """
    Эмулирует запросы к API auth-svc
    """
    print("🔄 Начало эмуляции запросов к API auth-svc...")
    
    prepare_export_dir()
    
    if not check_service():
        print("❌ Невозможно продолжить, сервис auth-svc недоступен")
        return False
    
    users = register_users()
    export_user_data(users)
    
    print("✅ Эмуляция запросов к API auth-svc успешно завершена!")
    return True

# Запуск скрипта
if __name__ == "__main__":
    success = asyncio.run(run_auth_emulator())
    sys.exit(0 if success else 1) 