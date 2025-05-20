#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных auth-svc тестовыми пользователями
"""

import os
import sys
import json
import asyncio
import random
from datetime import datetime, timedelta
import uuid

# Добавляем корневую директорию проекта в путь импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты из моделей auth-svc
try:
    from src.database.connection import SessionLocal, engine, Base
    from src.models.user import User, UserStatus, UserRole
    from src.models.profile import Profile, ProfileStatus
    from src.security.password import get_password_hash
except ImportError:
    print("❌ Ошибка импорта моделей auth-svc. Убедитесь, что скрипт запускается в контейнере auth-svc.")
    sys.exit(1)

# Путь для сохранения данных (используется другими сервисами)
DATA_DIR = "/app/scripts/data"
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

# Создание таблиц в БД
def create_tables():
    """
    Создает все таблицы в БД, если они еще не существуют
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")

# Подготовка директории для экспорта данных
def prepare_export_dir():
    """
    Создает директорию для экспорта данных
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"✅ Директория {DATA_DIR} создана/существует")

# Создание тестовых пользователей
def create_users():
    """
    Создает тестовых пользователей в базе данных
    
    Returns:
        list: Список созданных пользователей и их данных для экспорта
    """
    # Получаем сессию БД
    db = SessionLocal()
    
    # Создаем тестовых пользователей
    exported_users = []
    created_users = []
    
    try:
        # Проверяем, есть ли уже пользователи
        existing_user_count = db.query(User).count()
        if existing_user_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_user_count} пользователей. Пропускаем создание.")
            
            # Экспортируем существующих пользователей
            users = db.query(User).all()
            for user in users:
                profile = db.query(Profile).filter(Profile.user_id == user.id).first()
                
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_verified": user.is_verified,
                    "is_admin": user.role == UserRole.ADMIN,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "profile": {
                        "id": profile.id if profile else None,
                        "avatar_url": profile.avatar_url if profile else None,
                        "bio": profile.bio if profile else None
                    }
                }
                exported_users.append(user_data)
            
            return exported_users
        
        # Создаем новых пользователей
        for i, user_data in enumerate(USER_DATA):
            # Создаем пользователя
            hashed_password = get_password_hash(user_data["password"])
            
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=hashed_password,
                is_active=True,
                is_verified=random.choice([True, False]) if i > 0 else True,  # Админ всегда верифицирован
                role=UserRole.ADMIN if user_data["is_admin"] else UserRole.USER,
                status=UserStatus.ACTIVE,
                created_at=datetime.now() - timedelta(days=random.randint(1, 365))
            )
            db.add(user)
            db.flush()  # Чтобы получить ID пользователя
            
            # Создаем профиль пользователя
            profile = Profile(
                user_id=user.id,
                bio=user_data["bio"],
                avatar_url=user_data["avatar"],
                status=ProfileStatus.ACTIVE,
                reputation_score=random.uniform(3.0, 5.0) if i > 0 else 5.0,  # У админа максимальный рейтинг
                total_sales=random.randint(0, 100) if i > 0 else 0
            )
            db.add(profile)
            
            # Подготавливаем данные для экспорта
            export_data = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_verified": user.is_verified,
                "is_admin": user.role == UserRole.ADMIN,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "profile": {
                    "id": profile.id,
                    "avatar_url": profile.avatar_url,
                    "bio": profile.bio
                }
            }
            
            created_users.append(user)
            exported_users.append(export_data)
        
        db.commit()
        print(f"✅ Создано {len(created_users)} пользователей")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании пользователей: {e}")
    finally:
        db.close()
    
    return exported_users

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
async def seed_database():
    """
    Заполняет базу данных auth-svc тестовыми данными
    """
    print("🔄 Начало заполнения базы данных auth-svc тестовыми данными...")
    
    prepare_export_dir()
    create_tables()
    users = create_users()
    export_user_data(users)
    
    print("✅ База данных auth-svc успешно заполнена тестовыми данными!")

# Запуск скрипта
if __name__ == "__main__":
    asyncio.run(seed_database()) 