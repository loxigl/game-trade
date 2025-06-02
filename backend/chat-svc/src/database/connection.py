"""
Конфигурация подключения к базе данных
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..models.base import Base

# URL подключения к базе данных
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://gametrade:gametrade@postgres-chat:5432/chat_db"
)

# Создание движка для PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Получение сессии базы данных
    
    Yields:
        Session: Сессия SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Создание таблиц в базе данных
    """
    Base.metadata.create_all(bind=engine) 