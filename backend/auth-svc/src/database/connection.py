from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
from ..config.settings import settings

# Создаем базовый класс для моделей SQLAlchemy
Base = declarative_base()

# Настраиваем движок SQLAlchemy с пулом соединений
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=settings.DEBUG
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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