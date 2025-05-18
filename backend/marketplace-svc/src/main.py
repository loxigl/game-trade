from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database.connection import get_db, engine, Base
import os
import httpx
import time
import logging
import asyncio
from typing import Dict, List

# Импорт роутеров
from .routers import listings, categories, games, search, images, templates
from .dependencies.db import get_db
from .config.settings import get_settings
from .services.image_processor import ImageProcessor

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация сервисов
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-svc:8000")

app = FastAPI(
    title="GameTrade Marketplace Service",
    description="API для управления объявлениями маркетплейса и поиска товаров",
    version="0.1.0",
    root_path="/api/marketplace"
)

# Получение настроек
settings = get_settings()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Создаем директорию для загрузки, если она не существует
os.makedirs("uploads", exist_ok=True)

# Монтируем статические файлы для прямого доступа (в продакшене лучше использовать nginx)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Регистрация роутеров
app.include_router(listings)
app.include_router(categories)
app.include_router(games)
app.include_router(search)
app.include_router(images)
app.include_router(templates)

# Создание экземпляра обработчика изображений
image_processor = ImageProcessor()

@app.on_event("startup")
async def startup_event():
    """
    Запуск обработчика изображений при старте приложения
    """
    try:
        # Запускаем обработчик изображений в фоновом режиме
        asyncio.create_task(image_processor.start_consumer())
    except Exception as e:
        print(f"Ошибка при запуске обработчика изображений: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Marketplace Service API"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Комплексная проверка состояния сервиса marketplace.
    Проверяет подключение к базе данных и доступность зависимых сервисов.
    """
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "service": "marketplace",
        "timestamp": str(time.time()),
        "checks": {}
    }
    
    # Проверка подключения к базе данных
    try:
        db.execute(text("SELECT 1"))
        health_data["checks"]["database"] = {
            "status": "connected",
            "latency_ms": round((time.time() - start_time) * 1000)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_data["status"] = "unhealthy"
        health_data["checks"]["database"] = {
            "status": "disconnected", 
            "error": str(e)
        }
    
    # Проверка доступности сервиса авторизации
    auth_start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            auth_response = await client.get(f"{AUTH_SERVICE_URL}/health")
            auth_latency = round((time.time() - auth_start_time) * 1000)
            
            if auth_response.status_code == 200:
                health_data["checks"]["auth_service"] = {
                    "status": "available",
                    "latency_ms": auth_latency
                }
            else:
                health_data["status"] = "degraded"
                health_data["checks"]["auth_service"] = {
                    "status": "error",
                    "code": auth_response.status_code,
                    "latency_ms": auth_latency
                }
    except Exception as e:
        logger.error(f"Auth service health check failed: {str(e)}")
        health_data["status"] = "degraded"
        health_data["checks"]["auth_service"] = {
            "status": "unavailable",
            "error": str(e)
        }
    
    # Возвращаем соответствующий HTTP-статус в зависимости от состояния
    if health_data["status"] == "unhealthy":
        return health_data, status.HTTP_503_SERVICE_UNAVAILABLE
    elif health_data["status"] == "degraded":
        return health_data, status.HTTP_207_MULTI_STATUS
    
    return health_data

@app.get("/db-test")
async def db_test(db: Session = Depends(get_db)):
    """Тестовый эндпоинт для проверки подключения к базе данных"""
    try:
        # Выполняем простой запрос
        db.execute("SELECT 1")
        return {"message": "Database connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)