"""
Скрипт для заполнения базы данных начальными данными.
"""
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import random

from ..models.categorization import (
    Game, ItemCategory, CategoryAttribute, ItemTemplate, Item, AttributeType, 
    ItemAttributeValue, TemplateAttribute
)
from ..models.core import User, Profile, Wallet, Listing, Transaction, ListingStatus, ImageType, Image, ImageStatus
from .connection import get_db, Base, get_async_db, async_engine as engine

async def seed_users(db: AsyncSession) -> dict:
    """Заполняет базу данных тестовыми пользователями"""
    print("Заполнение пользователей...")

    # Проверяем, есть ли уже пользователи в базе
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar()

    if count > 0:
        print(f"В базе уже есть {count} пользователей, пропускаем...")
        # Получаем существующих пользователей
        result = await db.execute(select(User))
        users = result.scalars().all()
        return {user.username: user for user in users}

    users_data = [
        {
            "email": "seller@example.com",
            "username": "seller1"
        },
        {
            "email": "buyer@example.com",
            "username": "buyer1"
        }
    ]

    created_users = {}
    for user_data in users_data:
        user = User(**user_data)
        db.add(user)
        await db.flush()

        # Создаем профиль для пользователя
        profile = Profile(user_id=user.id)
        db.add(profile)

        # Создаем кошелек
        wallet = Wallet(user_id=user.id, balance=1000.0, is_default=True)
        db.add(wallet)

        created_users[user.username] = user
        print(f"Создан пользователь: {user.username}")

    await db.commit()
    return created_users

async def seed_games(db: AsyncSession) -> dict:
    """Заполняет базу данных играми"""
    print("Заполнение игр...")
    
    # Проверяем, есть ли уже игры в базе
    result = await db.execute(select(func.count()).select_from(Game))
    count = result.scalar()
    
    if count > 0:
        print(f"В базе уже есть {count} игр, пропускаем...")
        # Получаем существующие игры для дальнейшего использования
        result = await db.execute(select(Game))
        games = result.scalars().all()
        return {game.name: game for game in games}
    
    games_data = [
        {
            "name": "Counter-Strike 2",
            "description": "Современный тактический шутер от первого лица с богатой экосистемой торговли скинами",
            "logo_url": "https://example.com/cs2-logo.png",
            "is_active": True
        },
        {
            "name": "Dota 2",
            "description": "MOBA игра с обширной системой косметических предметов",
            "logo_url": "https://example.com/dota2-logo.png",
            "is_active": True
        },
        {
            "name": "Team Fortress 2",
            "description": "Классический командный шутер с системой головных уборов и оружия",
            "logo_url": "https://example.com/tf2-logo.png",
            "is_active": True
        },
        {
            "name": "Rust",
            "description": "Выживание в суровом открытом мире с возможностью торговли предметами",
            "logo_url": "https://example.com/rust-logo.png",
            "is_active": True
        },
        {
            "name": "World of Warcraft",
            "description": "Легендарная MMORPG с глубокой системой предметов и экономикой",
            "logo_url": "https://example.com/wow-logo.png",
            "is_active": True
        },
        {
            "name": "Minecraft",
            "description": "Популярная песочница с возможностью создания и торговли предметами",
            "logo_url": "https://example.com/minecraft-logo.png",
            "is_active": True
        },
        {
            "name": "Fortnite",
            "description": "Популярная игра в жанре battle royale с системой скинов и предметов",
            "logo_url": "https://example.com/fortnite-logo.png",
            "is_active": True
        },
        {
            "name": "Apex Legends",
            "description": "Командный шутер в жанре battle royale с системой скинов и предметов",
            "logo_url": "https://example.com/apex-logo.png",
            "is_active": True
        }
    ]
    
    created_games = {}
    for game_data in games_data:
        game = Game(**game_data)
        db.add(game)
        await db.flush()
        created_games[game.name] = game
        print(f"Создана игра: {game.name}")
    
    await db.commit()
    return created_games

async def seed_categories(db: AsyncSession, games: dict) -> dict:
    """Заполняет базу данных иерархией категорий предметов для игр"""
    print("Заполнение категорий предметов...")
    
    # Проверяем, есть ли уже категории в базе
    result = await db.execute(select(func.count()).select_from(ItemCategory))
    count = result.scalar()
    
    if count > 0:
        print(f"В базе уже есть {count} категорий, пропускаем...")
        # Получаем существующие категории для дальнейшего использования
        result = await db.execute(select(ItemCategory))
        categories = result.scalars().all()
        return {f"{category.game_id}_{category.name}_{category.parent_id or 0}": category for category in categories}
    
    # Структура категорий: словарь, где ключ - имя игры, значение - список корневых категорий
    # Каждая категория может иметь подкатегории в поле 'subcategories'
    categories_hierarchy = {
        "Counter-Strike 2": [
            {
                "name": "Предметы",
                "description": "Виртуальные предметы для игры",
                "icon_url": "https://example.com/cs2/items-icon.png",
                "subcategories": [
                    {
                        "name": "Оружие",
                        "description": "Различные виды оружия",
                        "icon_url": "https://example.com/cs2/weapons-icon.png",
                        "subcategories": [
                            {
            "name": "Ножи",
            "description": "Редкое холодное оружие ближнего боя",
                                "icon_url": "https://example.com/cs2/knife-icon.png"
                            },
                            {
            "name": "Пистолеты",
            "description": "Вторичное оружие",
                                "icon_url": "https://example.com/cs2/pistols-icon.png"
        },
        {
            "name": "Винтовки",
            "description": "Основное оружие",
                                "icon_url": "https://example.com/cs2/rifles-icon.png"
                            }
                        ]
                    },
                    {
                        "name": "Экипировка",
                        "description": "Предметы экипировки",
                        "icon_url": "https://example.com/cs2/equipment-icon.png",
                        "subcategories": [
                            {
                                "name": "Перчатки",
                                "description": "Косметические предметы для рук",
                                "icon_url": "https://example.com/cs2/gloves-icon.png"
                            }
                        ]
                    },
                    {
                        "name": "Украшения",
                        "description": "Декоративные элементы",
                        "icon_url": "https://example.com/cs2/decorations-icon.png",
                        "subcategories": [
                            {
                                "name": "Наклейки",
                                "description": "Декоративные элементы для украшения оружия",
                                "icon_url": "https://example.com/cs2/stickers-icon.png"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Аккаунты",
                "description": "Аккаунты игры с различными характеристиками",
                "icon_url": "https://example.com/cs2/accounts-icon.png",
                "subcategories": [
                    {
                        "name": "Премиум аккаунты",
                        "description": "Аккаунты с премиум статусом",
                        "icon_url": "https://example.com/cs2/premium-icon.png"
                    },
                    {
                        "name": "Рейтинговые аккаунты",
                        "description": "Аккаунты с высоким рейтингом",
                        "icon_url": "https://example.com/cs2/ranked-icon.png"
                    }
                ]
            },
            {
                "name": "Валюта",
                "description": "Внутриигровая валюта",
                "icon_url": "https://example.com/cs2/currency-icon.png"
            }
        ],
        
        "Dota 2": [
            {
                "name": "Предметы",
                "description": "Виртуальные предметы для игры",
                "icon_url": "https://example.com/dota2/items-icon.png",
                "subcategories": [
                    {
                        "name": "Экипировка героев",
                        "description": "Предметы для персонажей",
                        "icon_url": "https://example.com/dota2/hero-items-icon.png",
                        "subcategories": [
                            {
            "name": "Сеты",
            "description": "Полные комплекты предметов для героев",
            "icon_url": "https://example.com/dota2/sets-icon.png"
                            }
                        ]
                    },
                    {
                        "name": "Компаньоны",
                        "description": "Сопровождающие существа",
                        "icon_url": "https://example.com/dota2/companions-icon.png",
                        "subcategories": [
                            {
            "name": "Курьеры",
            "description": "Существа, доставляющие предметы на поле боя",
            "icon_url": "https://example.com/dota2/couriers-icon.png"
        },
        {
            "name": "Варды",
            "description": "Косметические предметы для вардов",
            "icon_url": "https://example.com/dota2/wards-icon.png"
                            }
                        ]
                    },
                    {
                        "name": "Спецэффекты",
                        "description": "Визуальные эффекты",
                        "icon_url": "https://example.com/dota2/effects-icon.png",
                        "subcategories": [
                            {
                                "name": "Эффекты",
                                "description": "Визуальные эффекты для героев и оружия",
                                "icon_url": "https://example.com/dota2/effects-icon.png"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Аккаунты",
                "description": "Аккаунты игры с различными характеристиками",
                "icon_url": "https://example.com/dota2/accounts-icon.png",
                "subcategories": [
                    {
                        "name": "MMR аккаунты",
                        "description": "Аккаунты с высоким рейтингом MMR",
                        "icon_url": "https://example.com/dota2/mmr-icon.png"
                    }
                ]
            }
        ],
        
        "World of Warcraft": [
            {
                "name": "Предметы",
                "description": "Внутриигровые предметы",
                "icon_url": "https://example.com/wow/items-icon.png",
                "subcategories": [
                    {
                        "name": "Экипировка",
                        "description": "Броня и оружие",
                        "icon_url": "https://example.com/wow/gear-icon.png",
                        "subcategories": [
                            {
            "name": "Оружие",
                                "description": "Мечи, посохи и другое оружие",
                                "icon_url": "https://example.com/wow/weapons-icon.png"
                            },
                            {
                                "name": "Броня",
                                "description": "Нагрудники, шлемы и другие части брони",
                                "icon_url": "https://example.com/wow/armor-icon.png"
                            }
                        ]
                    },
                    {
                        "name": "Маунты",
                        "description": "Ездовые животные и транспорт",
                        "icon_url": "https://example.com/wow/mounts-icon.png"
                    },
                    {
                        "name": "Питомцы",
                        "description": "Боевые и декоративные питомцы",
                        "icon_url": "https://example.com/wow/pets-icon.png"
                    }
                ]
            },
            {
                "name": "Аккаунты",
                "description": "Аккаунты WoW с различными характеристиками",
                "icon_url": "https://example.com/wow/accounts-icon.png",
                "subcategories": [
                    {
                        "name": "PvE аккаунты",
                        "description": "Аккаунты с высоким PvE прогрессом",
                        "icon_url": "https://example.com/wow/pve-icon.png"
                    },
                    {
                        "name": "PvP аккаунты",
                        "description": "Аккаунты с высоким PvP рейтингом",
                        "icon_url": "https://example.com/wow/pvp-icon.png"
                    }
                ]
            },
            {
                "name": "Валюта",
                "description": "Внутриигровая валюта",
                "icon_url": "https://example.com/wow/currency-icon.png",
                "subcategories": [
                    {
                        "name": "Золото",
                        "description": "Основная внутриигровая валюта",
                        "icon_url": "https://example.com/wow/gold-icon.png"
                    }
                ]
            }
        ]
    }
    
    created_categories = {}
    
    # Рекурсивная функция для создания категорий и подкатегорий
    async def create_category(game_id, category_data, parent_id=None):
        category = ItemCategory(
            game_id=game_id,
            name=category_data["name"],
            description=category_data["description"],
            icon_url=category_data["icon_url"],
            parent_id=parent_id
        )
        db.add(category)
        await db.flush()
        
        key = f"{game_id}_{category.name}_{parent_id or 0}"
        created_categories[key] = category
        print(f"Создана категория: {category.name} для игры с ID {game_id}" + 
              (f", родительская категория: {parent_id}" if parent_id else ""))
        
        # Рекурсивно создаем подкатегории, если они есть
        if "subcategories" in category_data:
            for subcategory_data in category_data["subcategories"]:
                await create_category(game_id, subcategory_data, category.id)
    
    # Создаем категории для каждой игры
    for game_name, categories_data in categories_hierarchy.items():
        game = games.get(game_name)
        if not game:
            print(f"Игра {game_name} не найдена, пропускаем категории...")
            continue
        
        for category_data in categories_data:
            await create_category(game.id, category_data)
    
    await db.commit()
    return created_categories

async def seed_attributes(db: AsyncSession, categories: dict) -> dict:
    """Заполняет базу данных атрибутами для категорий"""
    print("Заполнение атрибутов для категорий...")
    
    # Проверяем, есть ли уже атрибуты в базе
    result = await db.execute(select(func.count()).select_from(CategoryAttribute))
    count = result.scalar()
    
    if count > 0:
        print(f"В базе уже есть {count} атрибутов, пропускаем...")
        result = await db.execute(select(CategoryAttribute))
        attributes = result.scalars().all()
        return {f"{attr.category_id}_{attr.name}": attr for attr in attributes}
    
    # Общие атрибуты для всех категорий типа "Предметы"
    common_item_attributes = [
        {
            "name": "Редкость",
            "description": "Уровень редкости предмета",
            "attribute_type": AttributeType.ENUM,
            "is_required": True,
            "is_filterable": True,
            "default_value": "Обычный",
            "options": json.dumps(["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный", "Древний"])
        },
        {
            "name": "Качество",
            "description": "Качество предмета",
            "attribute_type": AttributeType.ENUM,
            "is_required": True,
            "is_filterable": True,
            "default_value": "Стандартное",
            "options": json.dumps(["Стандартное", "Уникальное", "Винтажное", "Подлинное", "Коллекционное"])
        }
    ]
    
    # Атрибуты для категорий "Аккаунты"
    account_attributes = [
        {
            "name": "Уровень",
            "description": "Уровень аккаунта",
            "attribute_type": AttributeType.NUMBER,
            "is_required": True,
            "is_filterable": True,
            "default_value": "1",
            "options": None
        },
        {
            "name": "Дата создания",
            "description": "Дата создания аккаунта",
            "attribute_type": AttributeType.STRING,
            "is_required": False,
            "is_filterable": True,
            "default_value": None,
            "options": None
        },
        {
            "name": "Email в комплекте",
            "description": "Включает ли продажа доступ к email аккаунту",
            "attribute_type": AttributeType.BOOLEAN,
            "is_required": True,
            "is_filterable": True,
            "default_value": "false",
            "options": None
        }
    ]
    
    # Атрибуты для категорий "Валюта"
    currency_attributes = [
        {
            "name": "Метод передачи",
            "description": "Способ передачи валюты",
            "attribute_type": AttributeType.ENUM,
            "is_required": True,
            "is_filterable": True,
            "default_value": "Прямая передача",
            "options": json.dumps(["Прямая передача", "Через аукцион", "Через обмен предметами"])
        },
        {
            "name": "Скорость доставки",
            "description": "Скорость получения валюты",
            "attribute_type": AttributeType.ENUM,
            "is_required": True,
            "is_filterable": True,
            "default_value": "Стандартная",
            "options": json.dumps(["Экспресс (до 2 часов)", "Стандартная (до 24 часов)", "Экономная (1-3 дня)"])
        }
    ]
    
    # Специфичные атрибуты для конкретных категорий
    category_specific_attributes = {
        # CS2 - Ножи
        "Ножи": [
        {
            "name": "Паттерн",
            "description": "Уникальный паттерн раскраски",
            "attribute_type": AttributeType.STRING,
            "is_required": False,
            "is_filterable": True,
            "default_value": None,
            "options": None
        },
        {
            "name": "Состояние",
                "description": "Внешний износ скина",
            "attribute_type": AttributeType.ENUM,
            "is_required": True,
            "is_filterable": True,
            "default_value": "Прямо с завода",
            "options": json.dumps([
                "Прямо с завода", 
                "Немного поношенное", 
                "После полевых испытаний", 
                "Поношенное", 
                "Закаленное в боях"
            ])
        },
        {
            "name": "StatTrak™",
            "description": "Счетчик убийств",
            "attribute_type": AttributeType.BOOLEAN,
            "is_required": True,
            "is_filterable": True,
            "default_value": "false",
            "options": None
        }
        ],
        # CS2 - Перчатки
        "Перчатки": [
            {
                "name": "Состояние",
                "description": "Внешний износ скина",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Прямо с завода",
                "options": json.dumps([
                    "Прямо с завода", 
                    "Немного поношенное", 
                    "После полевых испытаний", 
                    "Поношенное", 
                    "Закаленное в боях"
                ])
            }
        ],
        # CS2 - Пистолеты и винтовки
        "Пистолеты": [
            {
                "name": "Состояние",
                "description": "Внешний износ скина",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Прямо с завода",
                "options": json.dumps([
                    "Прямо с завода", 
                    "Немного поношенное", 
                    "После полевых испытаний", 
                    "Поношенное", 
                    "Закаленное в боях"
                ])
            },
            {
                "name": "StatTrak™",
                "description": "Счетчик убийств",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            },
            {
                "name": "Сувенир",
                "description": "Сувенирное оружие с турнира",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            }
        ],
        "Винтовки": [
            {
                "name": "Состояние",
                "description": "Внешний износ скина",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Прямо с завода",
                "options": json.dumps([
                    "Прямо с завода", 
                    "Немного поношенное", 
                    "После полевых испытаний", 
                    "Поношенное", 
                    "Закаленное в боях"
                ])
            },
            {
                "name": "StatTrak™",
                "description": "Счетчик убийств",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            },
            {
                "name": "Сувенир",
                "description": "Сувенирное оружие с турнира",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            }
        ],
        # Dota 2 - Курьеры
        "Курьеры": [
            {
                "name": "Стиль",
                "description": "Количество разблокированных стилей",
                "attribute_type": AttributeType.NUMBER,
                "is_required": False,
                "is_filterable": True,
                "default_value": "1",
                "options": None
            },
            {
                "name": "Эффект",
                "description": "Необычный эффект",
                "attribute_type": AttributeType.STRING,
                "is_required": False,
                "is_filterable": True,
                "default_value": None,
                "options": None
            },
            {
                "name": "Самоцветы",
                "description": "Количество слотов для самоцветов",
                "attribute_type": AttributeType.NUMBER,
                "is_required": False,
                "is_filterable": True,
                "default_value": "0",
                "options": None
            }
        ],
        # WoW - Шаблоны предметов
        "PvE аккаунты": [
            {
                "name": "Tier прогресса",
                "description": "Уровень пройденного PvE контента",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Tier 1",
                "options": json.dumps(["Tier 1", "Tier 2", "Tier 3", "Mythic Tier"])
            },
            {
                "name": "Уровень предметов",
                "description": "Средний уровень предметов персонажа",
                "attribute_type": AttributeType.NUMBER,
                "is_required": True,
                "is_filterable": True,
                "default_value": "200",
                "options": None
            }
        ],
        "PvP аккаунты": [
            {
                "name": "Рейтинг арены",
                "description": "Максимальный рейтинг на арене",
                "attribute_type": AttributeType.NUMBER,
                "is_required": True,
                "is_filterable": True,
                "default_value": "1500",
                "options": None
            },
            {
                "name": "Титулы PvP",
                "description": "Количество полученных PvP титулов",
                "attribute_type": AttributeType.NUMBER,
                "is_required": False,
                "is_filterable": True,
                "default_value": "0",
            "options": None
        }
    ]
    }
    
    created_attributes = {}
    
    # Для каждой категории добавляем атрибуты в зависимости от её типа
    for key, category in categories.items():
        # Определяем базовые атрибуты в зависимости от названия категории
        if category.name == "Предметы" or category.name in ["Оружие", "Экипировка", "Ножи", "Перчатки", "Пистолеты", "Винтовки", "Курьеры"]:
            # Добавляем общие атрибуты для предметов
            attributes_to_add = common_item_attributes.copy()
        elif "аккаунт" in category.name.lower() or category.name in ["Аккаунты", "PvE аккаунты", "PvP аккаунты", "MMR аккаунты", "Премиум аккаунты", "Рейтинговые аккаунты"]:
            # Добавляем атрибуты для аккаунтов
            attributes_to_add = account_attributes.copy()
        elif category.name == "Валюта" or category.name in ["Золото"]:
            # Добавляем атрибуты для валюты
            attributes_to_add = currency_attributes.copy()
        else:
            # Для прочих категорий добавляем только базовые атрибуты
            attributes_to_add = common_item_attributes.copy()[:1]  # Только "Редкость"
        
        # Добавляем специфичные атрибуты для конкретных категорий
        if category.name in category_specific_attributes:
            attributes_to_add.extend(category_specific_attributes[category.name])
        
        # Создаем атрибуты в базе данных
        for attr_data in attributes_to_add:
                attribute = CategoryAttribute(category_id=category.id, **attr_data)
                db.add(attribute)
                await db.flush()
                created_attributes[f"{category.id}_{attribute.name}"] = attribute
        print(f"Создан атрибут категории: {attribute.name} для категории {category.name}")
    
    await db.commit()
    return created_attributes

async def seed_templates(db: AsyncSession, categories: dict) -> dict:
    """Заполняет базу данных шаблонами предметов"""
    print("Заполнение шаблонов предметов...")
    
    # Проверяем, есть ли уже шаблоны в базе
    result = await db.execute(select(func.count()).select_from(ItemTemplate))
    count = result.scalar()
    
    if count > 0:
        print(f"В базе уже есть {count} шаблонов предметов, пропускаем...")
        result = await db.execute(select(ItemTemplate))
        templates = result.scalars().all()
        return {template.name: template for template in templates}

    # Сначала проверяем, какие категории являются конечными (не имеют подкатегорий)
    result = await db.execute(select(ItemCategory))
    all_categories = result.scalars().all()
    
    # Создаем словарь категорий с ключом по ID
    categories_by_id = {category.id: category for category in all_categories}
    
    # Определяем, у каких категорий есть подкатегории (не конечные)
    non_leaf_categories = set()
    for category in all_categories:
        if category.parent_id is not None:
            non_leaf_categories.add(category.parent_id)
    
    # Конечные категории - те, которые не имеют подкатегорий
    leaf_categories = [category for category in all_categories if category.id not in non_leaf_categories]
    print(f"Найдено {len(leaf_categories)} конечных категорий для шаблонов")
    
    # Шаблоны для разных категорий
    templates_data = {
        # CS2 - Ножи
        "Ножи": [
        {
            "name": "Керамбит | Градиент",
                "description": "Изогнутый нож с градиентной раскраской"
        },
        {
            "name": "Штык-нож M9 | Убийство",
                "description": "Штык-нож с черно-красной раскраской"
        },
        {
            "name": "Нож-бабочка | Кровавая паутина",
                "description": "Складной нож с паутинным узором"
        },
        {
            "name": "Фальшион | Мраморный градиент",
                "description": "Изогнутый нож с мраморным градиентом"
            }
        ],
        # CS2 - Перчатки
        "Перчатки": [
            {
                "name": "Спортивные перчатки | Пандора",
                "description": "Перчатки с фиолетово-черным дизайном"
            },
            {
                "name": "Перчатки-водителя | Имперский плед",
                "description": "Кожаные перчатки с клетчатым узором"
            },
            {
                "name": "Мотоциклетные перчатки | Затмение",
                "description": "Защитные перчатки с черно-красной отделкой"
            }
        ],
        # CS2 - Пистолеты
        "Пистолеты": [
            {
                "name": "Desert Eagle | Пламя",
                "description": "Мощный пистолет с огненным узором"
            },
            {
                "name": "USP-S | Убийца",
                "description": "Бесшумный пистолет с темным узором"
            },
            {
                "name": "Glock-18 | Градиент",
                "description": "Стандартный пистолет с голубым градиентом"
            }
        ],
        # CS2 - Винтовки
        "Винтовки": [
            {
                "name": "AK-47 | Вулкан",
                "description": "Штурмовая винтовка с бело-красно-оранжевым оформлением"
            },
            {
                "name": "M4A4 | Император",
                "description": "Штурмовая винтовка с царским узором"
            },
            {
                "name": "AWP | Драконий огонь",
                "description": "Снайперская винтовка с огненно-драконьим дизайном"
            }
        ],
        # CS2 - Наклейки
        "Наклейки": [
            {
                "name": "Сияние | Голографическая",
                "description": "Наклейка с голографическим эффектом"
            },
            {
                "name": "NAVI | Стокгольм 2021",
                "description": "Командная наклейка с турнира в Стокгольме"
            },
            {
                "name": "Глаз дракона",
                "description": "Блестящая наклейка с драконьим глазом"
            }
        ],
        # Dota 2 - Сеты
        "Сеты": [
            {
                "name": "Набор 'Огненный страж' для Ember Spirit",
                "description": "Полный комплект предметов с огненной тематикой"
            },
            {
                "name": "Набор 'Ледяное проклятие' для Crystal Maiden",
                "description": "Редкий набор предметов с ледяной тематикой"
            },
            {
                "name": "Набор 'Темный артефакт' для Phantom Assassin",
                "description": "Мистический набор с темной энергией"
            }
        ],
        # Dota 2 - Курьеры
        "Курьеры": [
            {
                "name": "Маленький дракончик",
                "description": "Милый летающий курьер в виде дракона"
            },
            {
                "name": "Механический жук",
                "description": "Необычный курьер в стиле стимпанк"
            },
            {
                "name": "Радужный единорог",
                "description": "Мифический курьер, оставляющий радужный след"
            }
        ],
        # Dota 2 - Варды
        "Варды": [
            {
                "name": "Око бездны",
                "description": "Мистическое око, наблюдающее за врагами"
            },
            {
                "name": "Страж природы",
                "description": "Вард в виде древесного духа"
            },
            {
                "name": "Механический наблюдатель",
                "description": "Вард в стиле стимпанк с вращающимися шестеренками"
            }
        ],
        # Dota 2 - Эффекты
        "Эффекты": [
            {
                "name": "Эфирное пламя",
                "description": "Огненный эффект для курьеров"
            },
            {
                "name": "Водоворот душ",
                "description": "Мистический эффект для предметов"
            },
            {
                "name": "Небесное сияние",
                "description": "Яркий эффект с небесной тематикой"
            }
        ],
        # CS2 - Премиум аккаунты
        "Премиум аккаунты": [
            {
                "name": "Премиум аккаунт CS2 с Prime",
                "description": "Аккаунт с активированным статусом Prime и всеми дополнительными привилегиями"
            },
            {
                "name": "Аккаунт CS2 с медалями",
                "description": "Аккаунт с коллекцией редких сервисных медалей"
            }
        ],
        # WoW - Оружие
        "Оружие": [
            {
                "name": "Громовая ярость, благословенный клинок искателя ветра",
                "description": "Легендарный меч, выкованный для искателя ветра"
            },
            {
                "name": "Коготь Азинота",
                "description": "Древний артефакт невероятной силы"
            }
        ],
        # WoW - Броня
        "Броня": [
            {
                "name": "Доспех Тьмы",
                "description": "Комплект легендарной брони, собранный из редчайших материалов"
            },
            {
                "name": "Наплечники Предвестника Рока",
                "description": "Наплечники, наводящие ужас одним своим видом"
            }
        ],
        # WoW - Маунты
        "Маунты": [
            {
                "name": "Пепельный дракон",
                "description": "Редкий летающий маунт-дракон с эффектом пепла"
            },
            {
                "name": "Боевой медведь тундры",
                "description": "Боевой маунт северных земель с отличной броней"
            }
        ],
        # WoW - PvP аккаунты
        "PvP аккаунты": [
            {
                "name": "Гладиатор 10 сезона",
                "description": "Аккаунт с высшим рейтингом арены и полным комплектом брони Гладиатора"
            }
        ],
        # WoW - Золото
        "Золото": [
            {
                "name": "Золото WoW [1000]",
                "description": "1000 золотых монет в игре World of Warcraft"
            },
            {
                "name": "Золото WoW [5000]",
                "description": "5000 золотых монет в игре World of Warcraft"
            },
            {
                "name": "Золото WoW [10000]",
                "description": "10000 золотых монет в игре World of Warcraft"
            }
        ]
    }

    created_templates = {}

    # Для каждой конечной категории создаем шаблоны
    for category in leaf_categories:
        category_name = category.name
        
        # Найдем шаблоны для данной категории
        if category_name in templates_data:
            templates_for_category = templates_data[category_name]
            
            # Создаем шаблоны
            for template_data in templates_for_category:
            template = ItemTemplate(category_id=category.id, **template_data)
            db.add(template)
            await db.flush()
            created_templates[template.name] = template
            print(f"Создан шаблон предмета: {template.name} для категории {category_name}")
        else:
            print(f"Для категории {category_name} не найдено шаблонов в списке, пропускаем...")

    await db.commit()
    return created_templates

async def seed_template_attributes(db: AsyncSession, templates: dict) -> dict:
    """Заполняет базу данных атрибутами для шаблонов предметов"""
    print("Заполнение атрибутов для шаблонов предметов...")
    
    # Проверяем, есть ли уже атрибуты шаблонов в базе
    result = await db.execute(select(func.count()).select_from(TemplateAttribute))
    count = result.scalar()
    
    if count > 0:
        print(f"В базе уже есть {count} атрибутов шаблонов, пропускаем...")
        result = await db.execute(select(TemplateAttribute))
        attributes = result.scalars().all()
        return {f"{attr.template_id}_{attr.name}": attr for attr in attributes}
    
    # Словари специфичных атрибутов для различных шаблонов
    template_specific_attributes = {
        # CS2 - Шаблоны ножей
        "Керамбит | Градиент": [
            {
                "name": "Процент градиента",
                "description": "Процентное соотношение градиента (влияет на цветовую насыщенность)",
                "attribute_type": AttributeType.NUMBER,
                "is_required": True,
                "is_filterable": True,
                "default_value": "95",
                "options": None
            },
            {
                "name": "Фаза",
                "description": "Фаза градиента, определяющая цветовую схему",
                "attribute_type": AttributeType.NUMBER,
                "is_required": True,
                "is_filterable": True,
                "default_value": "1",
                "options": None
            }
        ],
        "Штык-нож M9 | Убийство": [
            {
                "name": "Количество паутинок",
                "description": "Количество видимых паутинок на лезвии (влияет на стоимость)",
                "attribute_type": AttributeType.NUMBER,
                "is_required": True,
                "is_filterable": True,
                "default_value": "3",
                "options": None
            }
        ],
        "Нож-бабочка | Кровавая паутина": [
            {
                "name": "Симметрия",
                "description": "Симметричность узора на обеих сторонах лезвия",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Высокая",
                "options": json.dumps(["Низкая", "Средняя", "Высокая", "Идеальная"])
            },
            {
                "name": "Центральная паутина",
                "description": "Наличие паутины в центре лезвия",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "true",
                "options": None
            }
        ],
        
        # CS2 - Шаблоны перчаток
        "Спортивные перчатки | Пандора": [
            {
                "name": "Чистота фиолетового",
                "description": "Уровень насыщенности фиолетового цвета",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Средняя",
                "options": json.dumps(["Низкая", "Средняя", "Высокая", "Максимальная"])
            }
        ],
        "Перчатки-водителя | Имперский плед": [
            {
                "name": "Четкость клетки",
                "description": "Четкость клетчатого узора на перчатках",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Стандартная",
                "options": json.dumps(["Размытая", "Стандартная", "Четкая", "Безупречная"])
            }
        ],
        
        # Dota 2 - Шаблоны курьеров
        "Маленький дракончик": [
            {
                "name": "Цвет дракона",
                "description": "Основной цвет дракона",
                "attribute_type": AttributeType.ENUM,
                "is_required": True,
                "is_filterable": True,
                "default_value": "Красный",
                "options": json.dumps(["Красный", "Синий", "Зеленый", "Золотой", "Платиновый"])
            },
            {
                "name": "Дыхание огнем",
                "description": "Наличие эффекта дыхания огнем",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            }
        ],
        
        # WoW - Шаблоны предметов
        "Громовая ярость, благословенный клинок искателя ветра": [
            {
                "name": "Зачарование",
                "description": "Тип зачарования на оружии",
                "attribute_type": AttributeType.ENUM,
                "is_required": False,
                "is_filterable": True,
                "default_value": "Нет",
                "options": json.dumps(["Нет", "Крестоносец", "Палач", "Огненное оружие", "Ледяное оружие"])
            },
            {
                "name": "Глефа",
                "description": "Модель содержит редкую глефу",
                "attribute_type": AttributeType.BOOLEAN,
                "is_required": True,
                "is_filterable": True,
                "default_value": "false",
                "options": None
            }
        ]
    }
    
    # Общие атрибуты для всех шаблонов
    common_template_attributes = [
        {
            "name": "Торгуемость",
            "description": "Можно ли обменивать предмет",
            "attribute_type": AttributeType.BOOLEAN,
            "is_required": True,
            "is_filterable": True,
            "default_value": "true",
            "options": None
        },
        {
            "name": "Крайний срок обмена",
            "description": "Дата, до которой действует ограничение на обмен",
            "attribute_type": AttributeType.STRING,
            "is_required": False,
            "is_filterable": True,
            "default_value": None,
            "options": None
        }
    ]
    
    created_attributes = {}
    
    # Для каждого шаблона добавляем базовые атрибуты
    for template_name, template in templates.items():
        # Добавляем общие атрибуты для всех шаблонов
        for attr_data in common_template_attributes:
            attribute = TemplateAttribute(template_id=template.id, **attr_data)
            db.add(attribute)
            await db.flush()
            created_attributes[f"{template.id}_{attribute.name}"] = attribute
            print(f"Создан общий атрибут шаблона: {attribute.name} для шаблона {template_name}")
        
        # Добавляем специфичные атрибуты для конкретных шаблонов, если они есть
        if template_name in template_specific_attributes:
            for attr_data in template_specific_attributes[template_name]:
                attribute = TemplateAttribute(template_id=template.id, **attr_data)
                db.add(attribute)
                await db.flush()
                created_attributes[f"{template.id}_{attribute.name}"] = attribute
                print(f"Создан специфичный атрибут шаблона: {attribute.name} для шаблона {template_name}")
    
    await db.commit()
    return created_attributes

async def _create_item_attribute_value(db: AsyncSession, item_id: int, attr=None, template_attr=None, value=None) -> None:
    """Вспомогательная функция для создания значения атрибута предмета"""
    attr_value = ItemAttributeValue(
        item_id=item_id,
        attribute_id=attr.id if attr else None,
        template_attribute_id=template_attr.id if template_attr else None
    )

    # Определяем тип атрибута
    attribute = attr or template_attr
    if not attribute:
        print("Ошибка: не указан ни атрибут категории, ни атрибут шаблона")
        return

    # Устанавливаем значение в соответствующее поле в зависимости от типа атрибута
    if attribute.attribute_type == AttributeType.BOOLEAN:
        if isinstance(value, str):
            attr_value.value_boolean = (value.lower() == "true")
        else:
            attr_value.value_boolean = bool(value)
    elif attribute.attribute_type == AttributeType.NUMBER:
        try:
            attr_value.value_number = float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            attr_value.value_number = 0.0
    else:  # STRING или ENUM
        attr_value.value_string = str(value) if value is not None else ""

    db.add(attr_value)

async def seed_items(db: AsyncSession, templates: dict, users: dict) -> dict:
    """Заполняет базу данных конкретными предметами на основе шаблонов"""
    print("Заполнение предметов...")

    # Проверяем, есть ли уже предметы в базе
    result = await db.execute(select(func.count()).select_from(Item))
    count = result.scalar()

    if count > 0:
        print(f"В базе уже есть {count} предметов, пропускаем...")
        result = await db.execute(select(Item))
        items = result.scalars().all()
        return {f"{item.template_id}_{item.owner_id}": item for item in items}

    # Получаем пользователя-продавца
    seller = users.get("seller1")
    if not seller:
        print("Пользователь-продавец не найден, пропускаем создание предметов...")
        return {}

    # Значения атрибутов по типу предмета (используем имя шаблона для определения)
    # Разделяем атрибуты категории и атрибуты шаблона
    attribute_values = {
        # CS2 - Ножи
        "Керамбит | Градиент": {
            "category": {
            "Редкость": "Легендарный",
            "Качество": "Коллекционное",
            "Паттерн": "Fade 95%",
            "Состояние": "Прямо с завода",
            "StatTrak™": "true"
            },
            "template": {
                "Торгуемость": "true",
                "Крайний срок обмена": "2023-12-31",
                "Процент градиента": "95",
                "Фаза": "4"
            }
        },
        "Штык-нож M9 | Убийство": {
            "category": {
            "Редкость": "Мифический",
            "Качество": "Уникальное",
            "Паттерн": "Crimson Web",
            "Состояние": "Немного поношенное",
            "StatTrak™": "true"
            },
            "template": {
                "Торгуемость": "true",
                "Количество паутинок": "5"
            }
        },
        "Нож-бабочка | Кровавая паутина": {
            "category": {
            "Редкость": "Древний",
            "Качество": "Коллекционное",
            "Паттерн": "Crimson Web 0.07",
            "Состояние": "Прямо с завода",
            "StatTrak™": "true"
        },
            "template": {
                "Торгуемость": "true",
                "Симметрия": "Идеальная",
                "Центральная паутина": "true"
            }
        },
        # CS2 - Перчатки
        "Спортивные перчатки | Пандора": {
            "category": {
            "Редкость": "Редкий",
            "Качество": "Стандартное",
            "Состояние": "Немного поношенное"
        },
            "template": {
                "Торгуемость": "true",
                "Чистота фиолетового": "Высокая"
            }
        },
        "Перчатки-водителя | Имперский плед": {
            "category": {
            "Редкость": "Необычный",
                "Качество": "Стандартное",
                "Состояние": "Прямо с завода"
            },
            "template": {
                "Торгуемость": "true",
                "Четкость клетки": "Четкая"
            }
        },
        # CS2 - Пистолеты
        "Desert Eagle | Пламя": {
            "category": {
                "Редкость": "Мифический",
            "Качество": "Уникальное",
                "Состояние": "Прямо с завода",
                "StatTrak™": "true",
                "Сувенир": "false"
            },
            "template": {
                "Торгуемость": "true"
            }
        },
        # CS2 - Винтовки
        "AK-47 | Вулкан": {
            "category": {
                "Редкость": "Легендарный",
                "Качество": "Коллекционное",
                "Состояние": "Прямо с завода",
            "StatTrak™": "true",
                "Сувенир": "false"
            },
            "template": {
                "Торгуемость": "true"
            }
        },
        # Dota 2 - Курьеры
        "Маленький дракончик": {
            "category": {
                "Редкость": "Мифический",
                "Качество": "Уникальное",
                "Стиль": "2",
                "Эффект": "Эфирное пламя",
                "Самоцветы": "3"
            },
            "template": {
                "Торгуемость": "true",
                "Цвет дракона": "Золотой",
                "Дыхание огнем": "true"
            }
        },
        # WoW - Оружие
        "Громовая ярость, благословенный клинок искателя ветра": {
            "category": {
                "Редкость": "Легендарный"
            },
            "template": {
                "Торгуемость": "false",
                "Зачарование": "Крестоносец",
                "Глефа": "true"
            }
        },
        # WoW - Золото
        "Золото WoW [1000]": {
            "category": {
                "Метод передачи": "Прямая передача",
                "Скорость доставки": "Экспресс (до 2 часов)"
            },
            "template": {
                "Торгуемость": "true"
            }
        },
        # CS2 - Премиум аккаунты
        "Премиум аккаунт CS2 с Prime": {
            "category": {
                "Уровень": "40",
                "Дата создания": "2018-05-15",
                "Email в комплекте": "true"
            },
            "template": {
                "Торгуемость": "false"
            }
        },
        # WoW - PvP аккаунты
        "Гладиатор 10 сезона": {
            "category": {
                "Уровень": "60",
                "Email в комплекте": "true",
                "Рейтинг арены": "2800",
                "Титулы PvP": "5"
            },
            "template": {
                "Торгуемость": "false"
            }
        }
    }

    # Словарь для хранения созданных предметов
    created_items = {}

    # Создаем по одному предмету для каждого шаблона
    for template_name, template in templates.items():
        # Проверяем, есть ли значения атрибутов для данного шаблона
        if template_name not in attribute_values:
            print(f"Для шаблона {template_name} нет значений атрибутов, создаем с базовыми значениями...")
            item_values = {
                "category": {"Редкость": "Обычный"},
                "template": {"Торгуемость": "true"}
            }
        else:
            item_values = attribute_values[template_name]

        # Создаем предмет
        item = Item(
            template_id=template.id,
            owner_id=seller.id,
            created_at=datetime.now(),
        )
        db.add(item)
        await db.flush()
        created_items[f"{template.id}_{seller.id}"] = item
        print(f"Создан предмет по шаблону: {template_name}")

        # Получаем категорию для этого шаблона
        category_result = await db.execute(
            select(ItemCategory).where(ItemCategory.id == template.category_id)
        )
        category = category_result.scalar_one_or_none()
        if not category:
            print(f"Категория для шаблона {template_name} не найдена, пропускаем атрибуты...")
            continue

        # Создаем значения атрибутов категории
        if "category" in item_values:
            # Получаем атрибуты категории
            category_attrs_result = await db.execute(
                select(CategoryAttribute).where(CategoryAttribute.category_id == category.id)
            )
            category_attrs = category_attrs_result.scalars().all()
            
            # Словарь для быстрого поиска атрибутов по имени
            category_attrs_dict = {attr.name: attr for attr in category_attrs}
            
            # Создаем значения для атрибутов категории
            for attr_name, attr_value in item_values["category"].items():
                if attr_name in category_attrs_dict:
                    await _create_item_attribute_value(
                        db, 
                        item.id, 
                        attr=category_attrs_dict[attr_name], 
                        template_attr=None, 
                        value=attr_value
                    )
                else:
                    print(f"Атрибут категории {attr_name} не найден для {template_name}")

        # Создаем значения атрибутов шаблона
        if "template" in item_values:
            # Получаем атрибуты шаблона
            template_attrs_result = await db.execute(
                select(TemplateAttribute).where(TemplateAttribute.template_id == template.id)
            )
            template_attrs = template_attrs_result.scalars().all()
            
            # Словарь для быстрого поиска атрибутов шаблона по имени
            template_attrs_dict = {attr.name: attr for attr in template_attrs}
            
            # Создаем значения для атрибутов шаблона
            for attr_name, attr_value in item_values["template"].items():
                if attr_name in template_attrs_dict:
                    await _create_item_attribute_value(
                        db, 
                        item.id, 
                        attr=None, 
                        template_attr=template_attrs_dict[attr_name], 
                        value=attr_value
                    )
                else:
                    print(f"Атрибут шаблона {attr_name} не найден для {template_name}")

    await db.commit()
    return created_items

async def seed_listings(db: AsyncSession, items: dict, users: dict) -> None:
    """Заполняет базу данных объявлениями о продаже"""
    print("Заполнение объявлений...")

    # Проверяем, есть ли уже объявления в базе
    result = await db.execute(select(func.count()).select_from(Listing))
    count = result.scalar()

    if count > 0:
        print(f"В базе уже есть {count} объявлений, пропускаем...")
        return

    # Получаем пользователя-продавца
    seller = users.get("seller1")
    if not seller:
        print("Пользователь-продавец не найден, пропускаем создание объявлений...")
        return

    # Цены для разных предметов по шаблонам
    prices = {
        # CS2 - Ножи
        "Керамбит | Градиент": 299.99,
        "Штык-нож M9 | Убийство": 249.99,
        "Нож-бабочка | Кровавая паутина": 399.99,
        "Фальшион | Мраморный градиент": 199.99,

        # CS2 - Перчатки
        "Спортивные перчатки | Пандора": 189.99,
        "Перчатки-водителя | Имперский плед": 149.99,
        "Мотоциклетные перчатки | Затмение": 169.99,

        # CS2 - Пистолеты
        "Desert Eagle | Пламя": 79.99,
        "USP-S | Убийца": 59.99,
        "Glock-18 | Градиент": 39.99,

        # CS2 - Винтовки
        "AK-47 | Вулкан": 129.99,
        "M4A4 | Император": 99.99,
        "AWP | Драконий огонь": 179.99,

        # CS2 - Наклейки
        "Сияние | Голографическая": 24.99,
        "NAVI | Стокгольм 2021": 19.99,
        "Глаз дракона": 29.99,

        # Dota 2 - Сеты
        "Набор 'Огненный страж' для Ember Spirit": 29.99,
        "Набор 'Ледяное проклятие' для Crystal Maiden": 24.99,
        "Набор 'Темный артефакт' для Phantom Assassin": 34.99,

        # Dota 2 - Курьеры
        "Маленький дракончик": 14.99,
        "Механический жук": 9.99,
        "Радужный единорог": 19.99,

        # Dota 2 - Варды
        "Око бездны": 5.99,
        "Страж природы": 4.99,
        "Механический наблюдатель": 6.99,

        # Dota 2 - Эффекты
        "Эфирное пламя": 99.99,
        "Водоворот душ": 79.99,
        "Небесное сияние": 89.99,

        # TF2 - Головные уборы
        "Необычная федора": 24.99,
        "Шлем викинга": 19.99,
        "Цилиндр джентльмена": 29.99,

        # TF2 - Оружие и наборы
        "Золотая сковорода": 399.99,
        "Огненный топор": 49.99,
        "Австралиум миниган": 299.99,
        "Набор шпиона-джентльмена": 59.99,
        "Набор безумного учёного для Медика": 49.99,
        "Комплект воина для Солдата": 39.99,

        # Rust - Предметы
        "Тактический бронежилет": 19.99,
        "Радиационный костюм": 29.99,
        "Кожаная куртка с нашивками": 24.99,
        "Электрическая дрель": 14.99,
        "Декорированный топор": 9.99,
        "Кирка с черепом": 12.99,
        "Настенные часы": 4.99,
        "Граффити 'Волк'": 2.99,
        "Постер 'Выживание'": 3.99
    }

    # Статусы для объявлений с небольшой вариацией
    statuses = [
        ListingStatus.ACTIVE,
        ListingStatus.ACTIVE,
        ListingStatus.ACTIVE,
        ListingStatus.PENDING,
        ListingStatus.ACTIVE
    ]

    # Валюты для объявлений
    currencies = ["USD", "USD", "EUR", "USD", "RUB"]

    # Счетчик для выбора статуса и валюты
    counter = 0

    for item_key, item in items.items():
        # Получаем шаблон предмета для получения названия и описания
        template_result = await db.execute(select(ItemTemplate).where(ItemTemplate.id == item.template_id))
        template = template_result.scalar_one_or_none()
        if not template:
            print(f"Шаблон для предмета {item_key} не найден, пропускаем...")
            continue

        # Получаем категорию для дополнительной информации в описании
        category_result = await db.execute(select(ItemCategory).where(ItemCategory.id == template.category_id))
        category = category_result.scalar_one_or_none()

        # Получаем игру для дополнительной информации в описании
        game = None
        if category:
            game_result = await db.execute(select(Game).where(Game.id == category.game_id))
            game = game_result.scalar_one_or_none()

        # Составляем расширенное описание
        extended_description = template.description
        if category and game:
            extended_description = f"{template.description}. Категория: {category.name}, Игра: {game.name}"

            # Добавляем информацию о значениях атрибутов в описание
            category_attrs_result = await db.execute(
                select(ItemAttributeValue, CategoryAttribute)
                .join(CategoryAttribute, CategoryAttribute.id == ItemAttributeValue.attribute_id)
                .filter(ItemAttributeValue.item_id == item.id)
                .filter(ItemAttributeValue.attribute_id != None)
            )
            category_attr_values = category_attrs_result.all()
            
            template_attrs_result = await db.execute(
                select(ItemAttributeValue, TemplateAttribute)
                .join(TemplateAttribute, TemplateAttribute.id == ItemAttributeValue.template_attribute_id)
                .filter(ItemAttributeValue.item_id == item.id)
                .filter(ItemAttributeValue.template_attribute_id != None)
            )
            template_attr_values = template_attrs_result.all()
            
            if category_attr_values or template_attr_values:
                extended_description += "\n\nХарактеристики:"
                
                for attr_value, attr in category_attr_values:
                    value = None
                    if attr.attribute_type == AttributeType.BOOLEAN:
                        value = "Да" if attr_value.value_boolean else "Нет"
                    elif attr.attribute_type == AttributeType.NUMBER:
                        value = str(attr_value.value_number)
                    else:
                        value = attr_value.value_string
                    
                    extended_description += f"\n- {attr.name}: {value}"
                
                for attr_value, attr in template_attr_values:
                    value = None
                    if attr.attribute_type == AttributeType.BOOLEAN:
                        value = "Да" if attr_value.value_boolean else "Нет"
                    elif attr.attribute_type == AttributeType.NUMBER:
                        value = str(attr_value.value_number)
                    else:
                        value = attr_value.value_string
                    
                    extended_description += f"\n- {attr.name}: {value} (атрибут шаблона)"

        # Выбираем статус и валюту
        status = statuses[counter % len(statuses)]
        currency = currencies[counter % len(currencies)]
        counter += 1

        # Создаем объявление
        listing = Listing(
            seller_id=seller.id,
            item_template_id=template.id,
            item_id=item.id,
            title=template.name,
            description=extended_description,
            price=prices.get(template.name, 100.0),  # Цена из словаря или по умолчанию
            currency=currency,
            status=status
        )
        db.add(listing)
        await db.flush()
        print(f"Создано объявление: {template.name} ({game.name if game else 'Неизвестная игра'}) с ценой {listing.price} {listing.currency}, статус: {status.name}")
    
    await db.commit()

async def seed_images(db: AsyncSession, users: dict) -> None:
    """Заполняет базу данных изображениями для различных сущностей"""
    print("Заполнение изображений...")

    # Проверяем, есть ли уже изображения в базе
    result = await db.execute(select(func.count()).select_from(Image))
    count = result.scalar()

    if count > 0:
        print(f"В базе уже есть {count} изображений, пропускаем...")
        return

    # Получаем пользователя-владельца изображений
    owner = users.get("seller1")
    if not owner:
        print("Пользователь-владелец не найден, пропускаем создание изображений...")
        return

    # Получаем листинги для добавления изображений
    result = await db.execute(select(Listing))
    listings = result.scalars().all()
    if not listings:
        print("Листинги не найдены, пропускаем создание изображений...")
        return

    # Создаем изображения для листингов по категориям
    image_templates = {
        # CS2 - Ножи
        "Керамбит | Градиент": "cs2_knife_karambit",
        "Штык-нож M9 | Убийство": "cs2_knife_m9",
        "Нож-бабочка | Кровавая паутина": "cs2_knife_butterfly",
        "Фальшион | Мраморный градиент": "cs2_knife_falchion",

        # CS2 - Перчатки
        "Спортивные перчатки | Пандора": "cs2_gloves_sport",
        "Перчатки-водителя | Имперский плед": "cs2_gloves_driver",
        "Мотоциклетные перчатки | Затмение": "cs2_gloves_moto",

        # CS2 - Пистолеты
        "Desert Eagle | Пламя": "cs2_pistol_deagle",
        "USP-S | Убийца": "cs2_pistol_usp",
        "Glock-18 | Градиент": "cs2_pistol_glock",

        # CS2 - Винтовки
        "AK-47 | Вулкан": "cs2_rifle_ak47",
        "M4A4 | Император": "cs2_rifle_m4a4",
        "AWP | Драконий огонь": "cs2_rifle_awp",

        # CS2 - Наклейки
        "Сияние | Голографическая": "cs2_sticker_holo",
        "NAVI | Стокгольм 2021": "cs2_sticker_navi",
        "Глаз дракона": "cs2_sticker_dragon",

        # Dota 2 - Сеты
        "Набор 'Огненный страж' для Ember Spirit": "dota_set_ember",
        "Набор 'Ледяное проклятие' для Crystal Maiden": "dota_set_cm",
        "Набор 'Темный артефакт' для Phantom Assassin": "dota_set_pa",

        # Dota 2 - Курьеры
        "Маленький дракончик": "dota_courier_dragon",
        "Механический жук": "dota_courier_beetle",
        "Радужный единорог": "dota_courier_unicorn",

        # Dota 2 - Варды
        "Око бездны": "dota_ward_eye",
        "Страж природы": "dota_ward_nature",
        "Механический наблюдатель": "dota_ward_mech",

        # Dota 2 - Эффекты
        "Эфирное пламя": "dota_effect_flame",
        "Водоворот душ": "dota_effect_vortex",
        "Небесное сияние": "dota_effect_celestial",

        # TF2 - Головные уборы
        "Необычная федора": "tf2_hat_fedora",
        "Шлем викинга": "tf2_hat_viking",
        "Цилиндр джентльмена": "tf2_hat_tophat",

        # TF2 - Оружие и наборы
        "Золотая сковорода": "tf2_weapon_pan",
        "Огненный топор": "tf2_weapon_axe",
        "Австралиум миниган": "tf2_weapon_minigun",
        "Набор шпиона-джентльмена": "tf2_set_spy",
        "Набор безумного учёного для Медика": "tf2_set_medic",
        "Комплект воина для Солдата": "tf2_set_soldier",

        # Rust - Предметы
        "Тактический бронежилет": "rust_clothing_vest",
        "Радиационный костюм": "rust_clothing_hazmat",
        "Кожаная куртка с нашивками": "rust_clothing_jacket",
        "Электрическая дрель": "rust_tool_drill",
        "Декорированный топор": "rust_tool_axe",
        "Кирка с черепом": "rust_tool_pickaxe",
        "Настенные часы": "rust_decor_clock",
        "Граффити 'Волк'": "rust_decor_graffiti",
        "Постер 'Выживание'": "rust_decor_poster"
    }

    # Общее количество изображений для каждого листинга
    images_per_listing = 3

    # Счетчик созданных изображений
    created_images_count = 0

    for listing in listings:
        # Получаем шаблон предмета для определения типа изображения
        template_result = await db.execute(select(ItemTemplate).where(ItemTemplate.id == listing.item_template_id))
        template = template_result.scalar_one_or_none()
        if not template:
            print(f"Шаблон для листинга {listing.id} не найден, пропускаем...")
            continue

        # Получаем базовое имя файла из словаря или используем default
        base_filename = image_templates.get(template.name, f"default_item_{listing.id}")

        # Создаем несколько изображений для каждого листинга
        for i in range(images_per_listing):
            is_main = (i == 0)  # Первое изображение - главное
            image_name = f"{base_filename}_{i+1}"

            listing_image = Image(
                owner_id=owner.id,
                entity_id=listing.id,
                type=ImageType.LISTING,
                filename=f"{image_name}.jpg",
                original_filename=f"{template.name.replace('|', '_')}_{i+1}.jpg",
                file_path=f"/uploads/{image_name}.jpg",
                content_type="image/jpeg",
                is_main=is_main,
                status=ImageStatus.ACTIVE,
                order_index=i
            )
            db.add(listing_image)
            created_images_count += 1

            if is_main:
                print(f"Создано главное изображение для листинга: {template.name}")

        # Также создаем изображения для самого предмета
        item_result = await db.execute(select(Item).where(Item.id == listing.item_id))
        item = item_result.scalar_one_or_none()
        if item:
            item_image = Image(
                owner_id=owner.id,
                entity_id=item.id,
                type=ImageType.ITEM,
                filename=f"item_{item.id}.jpg",
                original_filename=f"{template.name.replace('|', '_')}_item.jpg",
                file_path=f"/uploads/item_{item.id}.jpg",
                content_type="image/jpeg",
                is_main=True,
                status=ImageStatus.ACTIVE,
                order_index=0
            )
            db.add(item_image)
            created_images_count += 1
            print(f"Создано изображение для предмета: {template.name}")

    # Получаем игры для добавления изображений
    result = await db.execute(select(Game))
    games = result.scalars().all()

    for game in games:
        game_image = Image(
            owner_id=owner.id,
            entity_id=game.id,
            type=ImageType.GAME,
            filename=f"{game.name.lower().replace(' ', '_').replace(':', '')}_logo.jpg",
            original_filename=f"{game.name}_logo_original.jpg",
            file_path=f"/uploads/{game.name.lower().replace(' ', '_').replace(':', '')}_logo.jpg",
            content_type="image/jpeg",
            is_main=True,
            status=ImageStatus.ACTIVE,
            order_index=0
        )
        db.add(game_image)
        created_images_count += 1
        print(f"Создано изображение для игры: {game.name}")

    # Получаем категории для добавления изображений
    result = await db.execute(select(ItemCategory))
    categories = result.scalars().all()

    for category in categories:
        category_image = Image(
            owner_id=owner.id,
            entity_id=category.id,
            type=ImageType.CATEGORY,
            filename=f"category_{category.id}.jpg",
            original_filename=f"category_{category.name}_original.jpg",
            file_path=f"/uploads/category_{category.id}.jpg",
            content_type="image/jpeg",
            is_main=True,
            status=ImageStatus.ACTIVE,
            order_index=0
        )
        db.add(category_image)
        created_images_count += 1
        print(f"Создано изображение для категории: {category.name}")

    # Получаем шаблоны предметов для добавления изображений
    result = await db.execute(select(ItemTemplate))
    templates = result.scalars().all()

    for template in templates:
        template_image = Image(
            owner_id=owner.id,
            entity_id=template.id,
            type=ImageType.ITEM_TEMPLATE,
            filename=f"template_{template.id}.jpg",
            original_filename=f"template_{template.name.replace('|', '_')}_original.jpg",
            file_path=f"/uploads/template_{template.id}.jpg",
            content_type="image/jpeg",
            is_main=True,
            status=ImageStatus.ACTIVE,
            order_index=0
        )
        db.add(template_image)
        created_images_count += 1
        print(f"Создано изображение для шаблона: {template.name}")

    await db.commit()
    print(f"Изображения успешно созданы: {created_images_count} изображений")

async def seed_all():
    """Запускает весь процесс заполнения базы данных"""
    print("Начало заполнения базы данных...")
    
    async with engine.begin() as conn:
        # Создаем таблицы, если они еще не созданы
        # В реальном приложении это должно делаться через миграции
        await conn.run_sync(Base.metadata.create_all)
    
    async for db in get_async_db():
        try:
            # Заполняем данные
            users = await seed_users(db)
            games = await seed_games(db)
            categories = await seed_categories(db, games)
            attributes = await seed_attributes(db, categories)
            templates = await seed_templates(db, categories)
            template_attributes = await seed_template_attributes(db, templates)
            items = await seed_items(db, templates, users)
            await seed_listings(db, items, users)
            await seed_images(db, users)
            
            print("Заполнение базы данных успешно завершено!")
        except Exception as e:
            await db.rollback()
            print(f"Ошибка при заполнении базы данных: {e}")
            raise
        finally:
            await db.close()

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(seed_all()) 
