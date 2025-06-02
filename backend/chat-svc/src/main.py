from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import asyncio

from .database.connection import create_tables
from .routes import chats_router, websockets_router
from .services.rabbitmq_service import get_rabbitmq_service
from .services.message_handler import setup_rabbitmq_consumers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GameTrade Chat Service",
    description="API для обмена сообщениями между пользователями",
    version="0.1.0",
    root_path="/api/chat"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на реальные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(chats_router)
app.include_router(websockets_router, prefix="/ws")

@app.on_event("startup")
async def startup_event():
    """
    Выполняется при запуске приложения
    Инициализирует соединение с RabbitMQ и настраивает потребителей сообщений
    """
    try:
        # Создание таблиц в базе данных
        create_tables()
        logger.info("Database tables created successfully")
        
        # Инициализация соединения с RabbitMQ
        rabbitmq_service = get_rabbitmq_service()
        await rabbitmq_service.connect()
        logger.info("Successfully connected to RabbitMQ")
        
        # Настройка потребителей сообщений
        await setup_rabbitmq_consumers()
        logger.info("RabbitMQ consumers are set up")
    except Exception as e:
        logger.error(f"Failed to initialize service: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Выполняется при остановке приложения
    Закрывает соединение с RabbitMQ
    """
    try:
        rabbitmq_service = get_rabbitmq_service()
        await rabbitmq_service.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Chat Service API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chat"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True) 