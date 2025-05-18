from pydantic_settings import BaseSettings
from typing import Any, Dict, List, Optional
import os


class Settings(BaseSettings):
    # Базовые настройки приложения
    APP_NAME: str = "FastAPI Service"
    APP_DESCRIPTION: str = "FastAPI Microservice Template"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("ENVIRONMENT", "development") == "development"
    
    # API настройки
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/v1"
    
    # CORS настройки
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/service"
    )
    DATABASE_ASYNC_URL: str = os.getenv(
        "DATABASE_ASYNC_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/service"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # Настройки Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Настройки RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    
    # Настройки JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 часа
    
    # Настройки логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Настройки для межсервисного взаимодействия
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://auth-svc:8000")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Создаем экземпляр настроек, который будет использоваться во всем приложении
settings = Settings() 