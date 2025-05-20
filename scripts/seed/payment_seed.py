#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных payment-svc тестовыми транзакциями,
кошельками и продажами на основе пользователей из auth-svc и 
объявлений из marketplace-svc
"""

import os
import sys
import json
import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Добавляем корневую директорию проекта в путь импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты из моделей payment-svc
try:
    from src.database.connection import SessionLocal, engine, Base
    from src.models.core import User, Profile
    from src.models.wallet import Wallet, WalletTransaction, WalletStatus, WalletTransactionStatus, WalletTransactionType
    from src.models.transaction import Transaction, TransactionStatus, TransactionType
    from src.models.transaction_history import TransactionHistory, TransactionHistoryType
except ImportError:
    print("❌ Ошибка импорта моделей payment-svc. Убедитесь, что скрипт запускается в контейнере payment-svc.")
    sys.exit(1)

# Пути для данных
DATA_DIR = "/app/scripts/data"
AUTH_DATA_FILE = os.path.join(DATA_DIR, "auth_seed_data.json")
MARKETPLACE_DATA_FILE = os.path.join(DATA_DIR, "marketplace_seed_data.json")

# Создание таблиц в БД
def create_tables():
    """
    Создает все таблицы в БД, если они еще не существуют
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")

# Загрузка данных пользователей из auth-svc
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

# Загрузка данных объявлений из marketplace-svc
def load_marketplace_data():
    """
    Загружает данные объявлений из marketplace-svc
    
    Returns:
        list: Список объявлений из marketplace-svc
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(MARKETPLACE_DATA_FILE):
            print(f"❌ Файл данных объявлений {MARKETPLACE_DATA_FILE} не найден!")
            return []
        
        # Загружаем данные из JSON-файла
        with open(MARKETPLACE_DATA_FILE, 'r') as f:
            data = json.load(f)
            
        if not data or "listings" not in data:
            print("❌ Файл данных объявлений не содержит информации о объявлениях!")
            return []
            
        listings = data["listings"]
        print(f"✅ Загружено {len(listings)} объявлений из marketplace-svc")
        return listings
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных объявлений: {e}")
        return []

# Создание пользователей в БД payment-svc
def create_users(db, users_data):
    """
    Создает пользователей в базе данных payment-svc на основе данных из auth-svc
    
    Args:
        db: Сессия SQLAlchemy
        users_data: Список пользователей из auth-svc
        
    Returns:
        list: Список созданных пользователей
    """
    users = []
    
    try:
        # Проверяем, есть ли уже пользователи
        existing_users_count = db.query(User).count()
        if existing_users_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_users_count} пользователей. Пропускаем создание.")
            return db.query(User).all()
        
        # Создаем пользователей
        for user_data in users_data:
            user = User(
                id=user_data["id"],  # Используем тот же ID, что и в auth-svc
                email=user_data["email"],
                username=user_data["username"],
                is_active=True,
                is_verified=user_data.get("is_verified", False),
                is_admin=user_data.get("is_admin", False),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.now()
            )
            db.add(user)
            
            # Создаем профиль пользователя (если есть данные)
            if "profile" in user_data and user_data["profile"]:
                profile_data = user_data["profile"]
                profile = Profile(
                    user_id=user.id,
                    bio=profile_data.get("bio", ""),
                    avatar_url=profile_data.get("avatar_url", "")
                )
                db.add(profile)
            
            users.append(user)
        
        db.commit()
        print(f"✅ Создано {len(users)} пользователей")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании пользователей: {e}")
    
    return users

# Создание кошельков
def create_wallets(db, users):
    """
    Создает кошельки для пользователей
    
    Args:
        db: Сессия SQLAlchemy
        users: Список пользователей
        
    Returns:
        list: Список созданных кошельков
    """
    wallets = []
    
    try:
        # Проверяем, есть ли уже кошельки
        existing_wallets_count = db.query(Wallet).count()
        if existing_wallets_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_wallets_count} кошельков. Пропускаем создание.")
            return db.query(Wallet).all()
        
        # Создаем кошельки для каждого пользователя
        for user in users:
            # Создаем основной кошелек с балансом
            balance = Decimal(random.uniform(100.0, 5000.0)).quantize(Decimal('0.01'))
            
            wallet = Wallet(
                user_id=user.id,
                balance=balance,
                status=WalletStatus.ACTIVE,
                currency="USD",
                created_at=datetime.now() - timedelta(days=random.randint(30, 180)),
                updated_at=datetime.now()
            )
            db.add(wallet)
            db.flush()  # Чтобы получить ID кошелька
            
            # Создаем начальную транзакцию пополнения кошелька
            deposit_transaction = WalletTransaction(
                wallet_id=wallet.id,
                amount=balance,
                type=WalletTransactionType.DEPOSIT,
                status=WalletTransactionStatus.COMPLETED,
                description="Начальное пополнение счета",
                created_at=wallet.created_at,
                updated_at=wallet.created_at,
                transaction_id=str(uuid.uuid4())
            )
            db.add(deposit_transaction)
            
            wallets.append(wallet)
        
        db.commit()
        print(f"✅ Создано {len(wallets)} кошельков")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании кошельков: {e}")
    
    return wallets

# Создание транзакций на основе объявлений
def create_transactions(db, listings_data, wallets):
    """
    Создает транзакции на основе объявлений
    
    Args:
        db: Сессия SQLAlchemy
        listings_data: Список объявлений из marketplace-svc
        wallets: Список кошельков
        
    Returns:
        list: Список созданных транзакций
    """
    transactions = []
    
    try:
        # Проверяем, есть ли уже транзакции
        existing_transactions_count = db.query(Transaction).count()
        if existing_transactions_count > 0:
            print(f"⚠️ В базе данных уже есть {existing_transactions_count} транзакций. Пропускаем создание.")
            return db.query(Transaction).all()
        
        # Создаем транзакции для 60% случайно выбранных объявлений
        selected_listings = random.sample(listings_data, min(len(listings_data), int(len(listings_data) * 0.6)))
        
        wallet_dict = {wallet.user_id: wallet for wallet in wallets}
        
        for listing_data in selected_listings:
            # Проверяем, что статус не ACTIVE (т.е. объявление можно купить)
            if listing_data["status"] == "SOLD" or random.choice([True, False, False]):  # 33% шанс создать транзакцию
                seller_id = listing_data["seller_id"]
                
                # Выбираем случайного покупателя (не продавца)
                buyer_ids = [wallet.user_id for wallet in wallets if wallet.user_id != seller_id]
                if not buyer_ids:
                    continue  # Пропускаем, если нет подходящих покупателей
                
                buyer_id = random.choice(buyer_ids)
                
                # Получаем кошельки продавца и покупателя
                seller_wallet = wallet_dict.get(seller_id)
                buyer_wallet = wallet_dict.get(buyer_id)
                
                if not seller_wallet or not buyer_wallet:
                    continue  # Пропускаем, если нет кошельков
                
                # Создаем транзакцию
                price = Decimal(listing_data["price"]).quantize(Decimal('0.01'))
                created_at = datetime.now() - timedelta(days=random.randint(0, 30))
                
                # Определяем статус транзакции (в основном завершенные)
                statuses = [
                    TransactionStatus.COMPLETED,
                    TransactionStatus.COMPLETED,
                    TransactionStatus.COMPLETED,
                    TransactionStatus.COMPLETED,
                    TransactionStatus.PENDING,
                    TransactionStatus.FAILED,
                    TransactionStatus.CANCELED
                ]
                status = random.choice(statuses)
                
                # Проверяем достаточно ли средств у покупателя
                if status == TransactionStatus.COMPLETED and buyer_wallet.balance < price:
                    # Если недостаточно средств, добавляем средства на счет
                    additional_amount = price + Decimal(random.uniform(100.0, 500.0)).quantize(Decimal('0.01'))
                    buyer_wallet.balance += additional_amount
                    
                    # Создаем транзакцию пополнения
                    deposit_transaction = WalletTransaction(
                        wallet_id=buyer_wallet.id,
                        amount=additional_amount,
                        type=WalletTransactionType.DEPOSIT,
                        status=WalletTransactionStatus.COMPLETED,
                        description="Пополнение счета",
                        created_at=created_at - timedelta(minutes=random.randint(10, 60)),
                        updated_at=created_at - timedelta(minutes=random.randint(1, 10)),
                        transaction_id=str(uuid.uuid4())
                    )
                    db.add(deposit_transaction)
                
                transaction = Transaction(
                    listing_id=listing_data["id"],
                    listing_title=listing_data["title"],
                    buyer_id=buyer_id,
                    seller_id=seller_id,
                    amount=price,
                    currency=listing_data["currency"],
                    status=status,
                    type=TransactionType.MARKETPLACE,
                    created_at=created_at,
                    updated_at=created_at + timedelta(minutes=random.randint(10, 120)) if status != TransactionStatus.PENDING else None
                )
                db.add(transaction)
                db.flush()  # Чтобы получить ID транзакции
                
                # Создаем историю транзакции (для статусов, отличных от PENDING)
                if status != TransactionStatus.PENDING:
                    history = TransactionHistory(
                        transaction_id=transaction.id,
                        status=status,
                        type=TransactionHistoryType.STATUS_CHANGED,
                        comment=f"Статус изменен на {status.value}",
                        created_at=transaction.updated_at or transaction.created_at
                    )
                    db.add(history)
                
                # Обновляем балансы для завершенных транзакций
                if status == TransactionStatus.COMPLETED:
                    # Снимаем деньги с кошелька покупателя
                    buyer_wallet.balance -= price
                    buyer_wallet.updated_at = transaction.updated_at or datetime.now()
                    
                    # Создаем транзакцию снятия денег
                    withdrawal_transaction = WalletTransaction(
                        wallet_id=buyer_wallet.id,
                        amount=price,
                        type=WalletTransactionType.WITHDRAWAL,
                        status=WalletTransactionStatus.COMPLETED,
                        description=f"Оплата за {listing_data['title']}",
                        created_at=transaction.created_at,
                        updated_at=transaction.updated_at or transaction.created_at,
                        transaction_id=str(uuid.uuid4()),
                        related_transaction_id=transaction.id
                    )
                    db.add(withdrawal_transaction)
                    
                    # Зачисляем деньги на кошелек продавца
                    seller_wallet.balance += price
                    seller_wallet.updated_at = transaction.updated_at or datetime.now()
                    
                    # Создаем транзакцию зачисления денег
                    deposit_transaction = WalletTransaction(
                        wallet_id=seller_wallet.id,
                        amount=price,
                        type=WalletTransactionType.DEPOSIT,
                        status=WalletTransactionStatus.COMPLETED,
                        description=f"Получение оплаты за {listing_data['title']}",
                        created_at=transaction.updated_at or transaction.created_at,
                        updated_at=transaction.updated_at or transaction.created_at,
                        transaction_id=str(uuid.uuid4()),
                        related_transaction_id=transaction.id
                    )
                    db.add(deposit_transaction)
                
                transactions.append(transaction)
        
        db.commit()
        print(f"✅ Создано {len(transactions)} транзакций")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании транзакций: {e}")
    
    return transactions

# Основная функция
async def seed_database():
    """
    Заполняет базу данных payment-svc тестовыми данными
    """
    print("🔄 Начало заполнения базы данных payment-svc тестовыми данными...")
    
    # Создаем директорию для данных
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Создаем таблицы
    create_tables()
    
    # Загружаем данные пользователей из auth-svc
    users_data = load_auth_data()
    
    if not users_data:
        print("⚠️ Нет данных пользователей из auth-svc. Невозможно создать транзакции без пользователей.")
        return
    
    # Загружаем данные объявлений из marketplace-svc
    listings_data = load_marketplace_data()
    
    if not listings_data:
        print("⚠️ Нет данных объявлений из marketplace-svc. Невозможно создать транзакции без объявлений.")
        return
    
    # Получаем сессию БД
    db = SessionLocal()
    
    try:
        # Создаем пользователей
        users = create_users(db, users_data)
        
        # Создаем кошельки для пользователей
        wallets = create_wallets(db, users)
        
        # Создаем транзакции на основе объявлений
        transactions = create_transactions(db, listings_data, wallets)
        
        print("✅ База данных payment-svc успешно заполнена тестовыми данными!")
    except Exception as e:
        print(f"❌ Ошибка при заполнении базы данных: {e}")
    finally:
        db.close()

# Запуск скрипта
if __name__ == "__main__":
    asyncio.run(seed_database()) 