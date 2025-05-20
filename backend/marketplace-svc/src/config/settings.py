"""
Настройки для сервиса marketplace
"""

from functools import lru_cache
from pydantic import  validator, PostgresDsn, AnyHttpUrl
from pydantic_settings import BaseSettings
from typing import Optional, List, Union
import os

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "marketplace-service"
    API_PREFIX: str = "/api/marketplace"
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    
    # Тестовый режим
    TEST_MODE: bool = False  # Включает тестовые функции, такие как автоматическая генерация transaction_id
    
    # Настройки базы данных
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    REDIS_PREFIX: str = "marketplace:"
    
    # Auth service
    AUTH_SERVICE_URL: AnyHttpUrl
    
    # JWT (используется для валидации токенов)
    JWT_SECRET: str
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # RabbitMQ настройки
    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str = "marketplace"
    RABBITMQ_IMAGES_QUEUE: str = "marketplace_images"
    RABBITMQ_IMAGES_ROUTING_KEY: str = "images"
    RABBITMQ_SALES_QUEUE: str = "marketplace_sales"
    RABBITMQ_SALES_ROUTING_KEY: str = "sales.created"
    
    class Config:
        """Конфигурация настроек"""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Получение настроек приложения с кэшированием
    
    Returns:
        Settings: Настройки приложения
    """
    return Settings() 