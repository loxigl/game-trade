from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy.orm import Session
from typing import Generator

# Получение переменных окружения
POSTGRES_USER = os.getenv("POSTGRES_USER", "gametrade")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "gametrade")
POSTGRES_DB = os.getenv("POSTGRES_DB", "payment_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-payment")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Формирование строки подключения к PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Создание движка SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Функция-зависимость для внедрения сессии БД в эндпоинты FastAPI.
    Создаёт новую сессию для каждого запроса и закрывает её после выполнения запроса.
    
    Yields:
        Session: Сессия SQLAlchemy для работы с базой данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 