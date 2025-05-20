#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных marketplace-svc тестовыми объявлениями
на основе пользователей из auth-svc
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

# Импорты из моделей marketplace-svc
try:
    from src.database.connection import SessionLocal, engine, Base
    from src.models.listing import Listing, ListingStatus, ListingVisibility
    from src.models.category import Category
    from src.models.game import Game
    from src.models.tag import Tag, listing_tags
    from src.models.image import Image, ImageStatus
except ImportError:
    print("❌ Ошибка импорта моделей marketplace-svc. Убедитесь, что скрипт запускается в контейнере marketplace-svc.")
    sys.exit(1)

# Пути для данных
DATA_DIR = "/app/scripts/data"
AUTH_DATA_FILE = os.path.join(DATA_DIR, "auth_seed_data.json")
MARKETPLACE_DATA_FILE = os.path.join(DATA_DIR, "marketplace_seed_data.json")

# Данные для объявлений
GAMES = [
    {"name": "World of Warcraft", "slug": "world-of-warcraft", "description": "Популярная MMORPG от Blizzard Entertainment"},
    {"name": "Dota 2", "slug": "dota-2", "description": "MOBA от Valve"},
    {"name": "Counter-Strike 2", "slug": "counter-strike-2", "description": "Тактический шутер от Valve"},
    {"name": "Minecraft", "slug": "minecraft", "description": "Песочница с открытым миром от Mojang Studios"},
    {"name": "Fortnite", "slug": "fortnite", "description": "Battle Royale от Epic Games"},
    {"name": "Elder Scrolls Online", "slug": "elder-scrolls-online", "description": "MMORPG от ZeniMax Online Studios"},
    {"name": "League of Legends", "slug": "league-of-legends", "description": "MOBA от Riot Games"},
    {"name": "Apex Legends", "slug": "apex-legends", "description": "Battle Royale от Respawn Entertainment"},
    {"name": "Overwatch 2", "slug": "overwatch-2", "description": "Командный шутер от Blizzard"},
    {"name": "Destiny 2", "slug": "destiny-2", "description": "MMO-шутер от Bungie"}
]

CATEGORIES = [
    {"name": "Аккаунты", "slug": "accounts", "description": "Продажа аккаунтов, в том числе с редкими предметами"},
    {"name": "Внутриигровые предметы", "slug": "ingame-items", "description": "Предметы, оружие, броня и другие вещи из игр"},
    {"name": "Валюта", "slug": "currency", "description": "Игровая валюта и ресурсы"},
    {"name": "Скины", "slug": "skins", "description": "Косметические предметы для персонажей и оружия"},
    {"name": "Услуги", "slug": "services", "description": "Прокачка персонажей, сопровождение и обучение"},
    {"name": "Ключи и коды", "slug": "keys", "description": "Ключи активации игр и дополнений"}
]

TAGS = [
    {"name": "Редкий", "slug": "rare", "description": "Редкие предметы и аккаунты"},
    {"name": "Распродажа", "slug": "sale", "description": "Товары со скидкой"},
    {"name": "Срочно", "slug": "urgent", "description": "Срочные продажи"},
    {"name": "Новый", "slug": "new", "description": "Новые предметы или аккаунты"},
    {"name": "Премиум", "slug": "premium", "description": "Премиум товары высокого уровня"},
    {"name": "Подписка", "slug": "subscription", "description": "Товары с активной подпиской"},
    {"name": "Коллекционер", "slug": "collector", "description": "Товары для коллекционеров"},
    {"name": "Лимитированное", "slug": "limited", "description": "Лимитированные или сезонные предметы"}
]

# Тексты для объявлений
TITLES_TEMPLATES = [
    "{game} аккаунт с редкими предметами",
    "Продам скины для {game}",
    "{game} валюта - выгодный курс",
    "Премиум аккаунт {game} с максимальным уровнем",
    "Редкие предметы {game} - большая коллекция",
    "Аккаунт {game} с подпиской на год",
    "Комплект скинов {game} - все редкости",
    "Услуги прокачки в {game} - быстро и надежно",
    "{game} ключи активации всех DLC",
    "Эксклюзивный контент для {game}"
]

DESCRIPTIONS_TEMPLATES = [
    "Продам аккаунт {game} с множеством редких предметов. Аккаунт создан более 3 лет назад. Никаких банов, чистая история.",
    "Большая коллекция скинов для {game}. Есть много редких и коллекционных предметов, которых больше не получить.",
    "Игровая валюта {game} с выгодным курсом. Быстро, безопасно, с гарантией. Возможны объемные заказы.",
    "Продаю премиум аккаунт {game} с максимальным уровнем и всеми разблокированными возможностями. Множество наград и достижений.",
    "Большой набор редких предметов {game}. Собирал коллекцию несколько лет, сейчас продаю из-за отсутствия времени на игру.",
    "Аккаунт {game} с оплаченной подпиской на год вперед. Много внутриигрового контента и бонусов.",
    "Полный комплект скинов {game} разной редкости. Есть эксклюзивные и лимитированные предметы с прошлых ивентов.",
    "Предлагаю услуги прокачки персонажей в {game}. Быстро и надежно, с гарантией безопасности вашего аккаунта.",
    "Ключи активации для {game} и всех выпущенных DLC. Официальные ключи, активация в любом регионе.",
    "Эксклюзивный контент для {game}, полученный с ограниченных мероприятий и промо-акций."
]

# Функция загрузки данных пользователей из auth-svc
def load_auth_data():
    """
    Загружает данные пользователей из auth-svc
    
    Returns:
        list: Список пользователей из auth-svc
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(AUTH_DATA_FILE):
            print(f"❌ Файл данных пользователей {AUTH_DATA_FILE} не найден!")
            return []
        
        # Загружаем данные из JSON-файла
        with open(AUTH_DATA_FILE, 'r') as f:
            data = json.load(f)
            
        if not data or "users" not in data:
            print("❌ Файл данных пользователей не содержит информации о пользователях!")
            return []
            
        users = data["users"]
        print(f"✅ Загружено {len(users)} пользователей из auth-svc")
        return users
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных пользователей: {e}")
        return []

# Подготовка директории для экспорта данных
def prepare_export_dir():
    """
    Создает директорию для экспорта данных
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"✅ Директория {DATA_DIR} создана/существует")

# Создание таблиц в БД
def create_tables():
    """
    Создает все таблицы в БД, если они еще не существуют
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")

# Создание игр
def create_games(db):
    """
    Создает игры в базе данных
    
    Args:
        db: Сессия SQLAlchemy
        
    Returns:
        list: Список созданных игр
    """
    games = []
    
    try:
        # Проверяем, есть ли уже игры
        existing_games_count = db.query(Game).count()
        if existing_games_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_games_count} игр. Пропускаем создание.")
            return db.query(Game).all()
        
        # Создаем игры
        for game_data in GAMES:
            game = Game(
                name=game_data["name"],
                slug=game_data["slug"],
                description=game_data["description"],
                is_active=True,
                image_url=f"https://loremflickr.com/320/240/{game_data['slug']}?random={random.randint(1, 1000)}"
            )
            db.add(game)
            games.append(game)
        
        db.commit()
        print(f"✅ Создано {len(games)} игр")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании игр: {e}")
        
    return games

# Создание категорий
def create_categories(db):
    """
    Создает категории в базе данных
    
    Args:
        db: Сессия SQLAlchemy
        
    Returns:
        list: Список созданных категорий
    """
    categories = []
    
    try:
        # Проверяем, есть ли уже категории
        existing_categories_count = db.query(Category).count()
        if existing_categories_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_categories_count} категорий. Пропускаем создание.")
            return db.query(Category).all()
        
        # Создаем категории
        for category_data in CATEGORIES:
            category = Category(
                name=category_data["name"],
                slug=category_data["slug"],
                description=category_data["description"],
                is_active=True,
                icon_url=f"https://loremflickr.com/64/64/{category_data['slug']}?random={random.randint(1, 1000)}"
            )
            db.add(category)
            categories.append(category)
        
        db.commit()
        print(f"✅ Создано {len(categories)} категорий")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании категорий: {e}")
        
    return categories

# Создание тегов
def create_tags(db):
    """
    Создает теги в базе данных
    
    Args:
        db: Сессия SQLAlchemy
        
    Returns:
        list: Список созданных тегов
    """
    tags = []
    
    try:
        # Проверяем, есть ли уже теги
        existing_tags_count = db.query(Tag).count()
        if existing_tags_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_tags_count} тегов. Пропускаем создание.")
            return db.query(Tag).all()
        
        # Создаем теги
        for tag_data in TAGS:
            tag = Tag(
                name=tag_data["name"],
                slug=tag_data["slug"],
                description=tag_data["description"]
            )
            db.add(tag)
            tags.append(tag)
        
        db.commit()
        print(f"✅ Создано {len(tags)} тегов")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании тегов: {e}")
        
    return tags

# Создание объявлений
def create_listings(db, users, games, categories, tags):
    """
    Создает объявления в базе данных
    
    Args:
        db: Сессия SQLAlchemy
        users: Список пользователей из auth-svc
        games: Список игр
        categories: Список категорий
        tags: Список тегов
        
    Returns:
        list: Список созданных объявлений
    """
    listings = []
    
    try:
        # Проверяем, есть ли уже объявления
        existing_listings_count = db.query(Listing).count()
        if existing_listings_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_listings_count} объявлений. Пропускаем создание.")
            
            # Возвращаем существующие объявления
            all_listings = db.query(Listing).all()
            
            # Экспортируемые данные
            export_listings = []
            for listing in all_listings:
                export_data = {
                    "id": listing.id,
                    "title": listing.title,
                    "slug": listing.slug,
                    "price": float(listing.price),
                    "currency": listing.currency,
                    "seller_id": listing.seller_id,
                    "status": listing.status.value,
                    "created_at": listing.created_at.isoformat() if listing.created_at else None,
                    "game_id": listing.game_id,
                    "category_id": listing.category_id
                }
                export_listings.append(export_data)
            
            return export_listings
        
        # Создаем объявления для каждого пользователя
        for user in users:
            if not user["is_admin"]:  # Исключаем админов из создания объявлений
                # Создаем от 1 до 5 объявлений для каждого пользователя
                num_listings = random.randint(1, 5)
                
                for i in range(num_listings):
                    # Выбираем случайную игру, категорию и 1-3 тега
                    game = random.choice(games)
                    category = random.choice(categories)
                    selected_tags = random.sample(tags, random.randint(1, 3))
                    
                    # Генерируем название и описание
                    title_template = random.choice(TITLES_TEMPLATES)
                    description_template = random.choice(DESCRIPTIONS_TEMPLATES)
                    
                    title = title_template.format(game=game.name)
                    description = description_template.format(game=game.name)
                    
                    # Генерируем случайную цену
                    price = round(random.uniform(10.0, 1000.0), 2)
                    
                    # Определяем статус объявления (большинство активных)
                    statuses = [ListingStatus.ACTIVE] * 7 + [ListingStatus.PENDING, ListingStatus.SOLD, ListingStatus.PAUSED]
                    status = random.choice(statuses)
                    
                    # Создаем объявление
                    listing = Listing(
                        title=title,
                        description=description,
                        price=price,
                        currency="USD",  # Можно добавить разные валюты при необходимости
                        seller_id=user["id"],
                        status=status,
                        visibility=ListingVisibility.PUBLIC,
                        created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                        is_featured=random.choice([True, False, False, False]),  # 25% шанс быть рекомендованным
                        views_count=random.randint(0, 1000),
                        game_id=game.id,
                        category_id=category.id
                    )
                    
                    db.add(listing)
                    db.flush()  # Чтобы получить ID объявления
                    
                    # Добавляем теги к объявлению
                    for tag in selected_tags:
                        db.execute(listing_tags.insert().values(listing_id=listing.id, tag_id=tag.id))
                    
                    # Добавляем изображения к объявлению (от 1 до 5)
                    num_images = random.randint(1, 5)
                    for j in range(num_images):
                        image = Image(
                            listing_id=listing.id,
                            url=f"https://loremflickr.com/800/600/{game.slug}?random={random.randint(1, 1000)}",
                            status=ImageStatus.ACTIVE,
                            is_main=(j == 0),  # Первое изображение делаем главным
                            position=j
                        )
                        db.add(image)
                    
                    # Подготавливаем данные для экспорта
                    export_data = {
                        "id": listing.id,
                        "title": listing.title,
                        "slug": listing.slug,
                        "price": float(listing.price),
                        "currency": listing.currency,
                        "seller_id": listing.seller_id,
                        "status": listing.status.value,
                        "created_at": listing.created_at.isoformat() if listing.created_at else None,
                        "game_id": listing.game_id,
                        "category_id": listing.category_id
                    }
                    listings.append(export_data)
        
        db.commit()
        print(f"✅ Создано {len(listings)} объявлений")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании объявлений: {e}")
        
    return listings

# Экспорт данных объявлений для других сервисов
def export_listings_data(listings):
    """
    Экспортирует данные объявлений в JSON-файл
    
    Args:
        listings: Список данных объявлений для экспорта
    """
    try:
        # Сохраняем данные в JSON-файл
        with open(MARKETPLACE_DATA_FILE, 'w') as f:
            json.dump({"listings": listings}, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные объявлений экспортированы в {MARKETPLACE_DATA_FILE}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте данных объявлений: {e}")

# Основная функция 
async def seed_database():
    """
    Заполняет базу данных marketplace-svc тестовыми данными
    """
    print("🔄 Начало заполнения базы данных marketplace-svc тестовыми данными...")
    
    # Подготавливаем директорию для экспорта данных
    prepare_export_dir()
    
    # Создаем таблицы
    create_tables()
    
    # Загружаем данные пользователей из auth-svc
    users = load_auth_data()
    
    if not users:
        print("⚠️ Нет данных пользователей из auth-svc. Невозможно создать объявления без пользователей.")
        return
    
    # Получаем сессию БД
    db = SessionLocal()
    
    try:
        # Создаем базовые данные
        games = create_games(db)
        categories = create_categories(db)
        tags = create_tags(db)
        
        # Создаем объявления на основе пользователей
        listings = create_listings(db, users, games, categories, tags)
        
        # Экспортируем данные объявлений
        export_listings_data(listings)
        
        print("✅ База данных marketplace-svc успешно заполнена тестовыми данными!")
    except Exception as e:
        print(f"❌ Ошибка при заполнении базы данных: {e}")
    finally:
        db.close()

# Запуск скрипта
if __name__ == "__main__":
    asyncio.run(seed_database()) 