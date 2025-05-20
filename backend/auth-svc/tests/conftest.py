import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.database.connection import Base, get_db
from src.main import app
from src.models.user import User
from src.services.password import hash_password
from src.services.jwt import create_access_token, create_refresh_token

# Создаем тестовую базу данных в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """
    Фикстура для создания тестовой БД в памяти и таблиц для каждого теста
    """
    # Создаем движок SQLAlchemy для SQLite в памяти
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # Удаляем все таблицы
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    """
    Фикстура для создания тестового клиента FastAPI
    с переопределением зависимости БД
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Переопределяем зависимость для БД
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Очищаем переопределения зависимостей
    app.dependency_overrides = {}

@pytest.fixture
def test_user(test_db):
    """
    Фикстура для создания тестового пользователя
    """
    # Создаем тестового пользователя
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_verified=True,
        roles=["user"]
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_admin(test_db):
    """
    Фикстура для создания тестового администратора
    """
    # Создаем тестового администратора
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        is_active=True,
        is_verified=True,
        is_admin=True,
        roles=["user", "admin"]
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin

@pytest.fixture
def test_moderator(test_db):
    """
    Фикстура для создания тестового модератора
    """
    # Создаем тестового модератора
    moderator = User(
        username="moderator",
        email="moderator@example.com",
        hashed_password=hash_password("moderator123"),
        is_active=True,
        is_verified=True,
        roles=["user", "moderator"]
    )
    test_db.add(moderator)
    test_db.commit()
    test_db.refresh(moderator)
    return moderator

@pytest.fixture
def user_token(test_user):
    """
    Фикстура для создания токена обычного пользователя
    """
    # Создаем токен для тестового пользователя
    token_data = {
        "sub": str(test_user.id),
        "username": test_user.username
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {"access_token": access_token, "refresh_token": refresh_token}

@pytest.fixture
def admin_token(test_admin):
    """
    Фикстура для создания токена администратора
    """
    # Создаем токен для тестового администратора
    token_data = {
        "sub": str(test_admin.id),
        "username": test_admin.username
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {"access_token": access_token, "refresh_token": refresh_token}

@pytest.fixture
def moderator_token(test_moderator):
    """
    Фикстура для создания токена модератора
    """
    # Создаем токен для тестового модератора
    token_data = {
        "sub": str(test_moderator.id),
        "username": test_moderator.username
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {"access_token": access_token, "refresh_token": refresh_token}

# Используем фикстуры pytest-asyncio для асинхронных тестов
@pytest.fixture
def event_loop():
    """
    Фикстура для создания цикла событий для асинхронных тестов
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 