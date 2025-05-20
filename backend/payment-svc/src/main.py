from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import os
from sqlalchemy import text

# Импорт внутренних модулей
from .database.connection import engine, Base, get_db
from .services.rabbitmq_service import get_rabbitmq_service, RabbitMQService
from .services.message_handler import setup_rabbitmq_consumers
from .services.event_rabbit_bridge import setup_event_rabbit_bridge
from .services.transaction_timeout_service import setup_transaction_timeout_service
from .services.idempotency_cleanup_service import setup_idempotency_cleanup_service
from .services.user_consumer_service import UserConsumerService
from .config.settings import get_settings
from .routers import (
    transaction_router, transaction_history_router, 
    statistics_router, sales_router, wallets_router, 
    currency_router
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Функция для обработки startup/shutdown событий
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Выполняется при запуске
    logger.info("Starting up payment service...")
    
    # Создаем таблицы в БД (в продакшене используйте миграции Alembic)
    Base.metadata.create_all(bind=engine)
    
    # Инициализируем сервисы
    await setup_event_rabbit_bridge()
    await setup_rabbitmq_consumers()
    await setup_transaction_timeout_service()
    await setup_idempotency_cleanup_service()
    
    # Настраиваем потребителей событий пользователя
    try:
        await UserConsumerService.setup_consumers()
        logger.info("User consumers set up successfully")
    except Exception as e:
        logger.error(f"Failed to set up user consumers: {str(e)}")
    
    logger.info("Payment service started successfully")
    
    yield  # Здесь FastAPI обрабатывает запросы
    
    # Выполняется при выключении
    logger.info("Shutting down payment service...")
    
    # Закрываем соединения
    rabbitmq_service = get_rabbitmq_service()
    await rabbitmq_service.close()
    
    logger.info("Payment service shut down successfully")

# Инициализация приложения FastAPI
app = FastAPI(
    title="Payment Service API",
    description="""
    API платежной системы для управления кошельками, транзакциями и валютами.
    
    ## Основные возможности
    
    * Управление кошельками и балансами
    * Операции с транзакциями
    * Конвертация валют
    * Управление продажами
    * Статистика и отчеты
    * История транзакций
    
    ## Аутентификация
    
    Все запросы к API должны содержать заголовок `Authorization` с JWT токеном:
    ```
    Authorization: Bearer <token>
    ```
    
    ## Ограничения
    
    * Максимальный размер страницы: 100 записей
    * Минимальный размер страницы: 1 запись
    * Максимальная длина описания транзакции: 1000 символов
    * Минимальная сумма транзакции: 0.01
    * Поддерживаемые валюты: USD, EUR, RUB
    """,
    version="1.0.0",
    
    openapi_tags=[
        {
            "name": "wallets",
            "description": "Операции с кошельками и балансами",
        },
        {
            "name": "transactions",
            "description": "Управление транзакциями",
        },
        {
            "name": "transaction_history",
            "description": "История транзакций и экспорт данных",
        },
        {
            "name": "currency",
            "description": "Операции с валютами и курсами обмена",
        },
        {
            "name": "statistics",
            "description": "Статистика и отчеты по транзакциям",
        },
        {
            "name": "sales",
            "description": "Управление продажами маркетплейса",
        },
    ],
    lifespan=lifespan,
    root_path="/api/payments"
)

# Настройка CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "https://yourfrontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутизаторов
app.include_router(transaction_history_router)
app.include_router(transaction_router)
app.include_router(statistics_router)
app.include_router(sales_router)
app.include_router(wallets_router)
app.include_router(currency_router)

@app.get("/")
async def root():
    return {"message": "Payment Service API"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Эндпоинт для проверки здоровья сервиса"""
    try:
        # Проверяем соединение с базой данных
        db.execute(text("SELECT 1"))
        
        # Проверяем соединение с Redis, если настроено
        redis_status = "Not configured"
        
        return {
            "status": "healthy",
            "db_connection": "Connected",
            "redis_connection": redis_status,
            "version": "1.0.0",
            "env": os.environ.get("ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True) 