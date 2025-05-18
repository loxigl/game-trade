from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Базовые настройки приложения
    APP_NAME: str = "GameTrade Authentication Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("ENVIRONMENT", "development") == "development"
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://gametrade:gametrade@localhost:5432/gametrade")
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # Настройки Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Настройки JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 часа
    
    # Настройки для хеширования паролей
    PWD_CONTEXT_SCHEMES: list[str] = ["bcrypt"]
    PWD_CONTEXT_DEPRECATED: str = "auto"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Создаем экземпляр настроек, который будет использоваться во всем приложении
settings = Settings() 