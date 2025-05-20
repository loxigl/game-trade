"""
Настройки приложения
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # PostgreSQL
    POSTGRES_USER: str = "gametrade"
    POSTGRES_PASSWORD: str = "gametrade"
    POSTGRES_DB: str = "payment_db"
    POSTGRES_HOST: str = "postgres-payment"
    POSTGRES_PORT: str = "5432"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://gametrade:gametrade@rabbitmq:5672/"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # Общие настройки
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "GameTrade Payment Service"
    DEBUG: bool = True
    
    # Настройки безопасности
    SECRET_KEY: str = "gametrade_payment_secret_key"
    JWT_SECRET_KEY: str = "gametrade_payment_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки Escrow
    DEFAULT_ESCROW_PERIOD_DAYS: int = 3
    FEE_PERCENTAGE: float = 5.0  # 5% комиссия с транзакций

    # Настройки для межсервисного взаимодействия
    AUTH_SERVICE_URL: str = "http://auth-svc:8000"
    MARKETPLACE_SERVICE_URL: str = "http://marketplace-svc:8001"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Получить настройки приложения с кэшированием
    
    Returns:
        Настройки приложения
    """
    return Settings() 