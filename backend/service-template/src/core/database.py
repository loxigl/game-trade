from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as async_sessionmaker

from typing import Generator, AsyncGenerator

from .config import settings

# Создаем движок SQLAlchemy для синхронных операций
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,

)

# Создаем движок SQLAlchemy для асинхронных операций
async_engine = create_async_engine(
    settings.DATABASE_ASYNC_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,

)

# Создаем фабрику сессий для синхронной работы
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем фабрику сессий для асинхронной работы
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


# Для синхронных эндпоинтов
def get_db() -> Generator[Session, None, None]:
    """
    Функция-генератор для получения сессии базы данных.
    Используется как зависимость в маршрутах FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Для асинхронных эндпоинтов
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная функция-генератор для получения сессии базы данных.
    Используется как зависимость в асинхронных маршрутах FastAPI.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 