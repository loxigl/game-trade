from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .core.config import settings
from .api.api import api_router
from .core import messaging

# Логирование
import logging

# Инициализация логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Фабричная функция для создания приложения FastAPI"""
    
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url=f"{settings.API_PREFIX}/docs",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )
    
    # Настройка CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Обработчики ошибок
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Обрабатывает ошибки валидации запросов"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=422,
            content={"detail": "Ошибка валидации", "errors": errors}
        )
    
    # Регистрация роутеров API
    application.include_router(api_router, prefix=settings.API_PREFIX)
    
    @application.get("/health")
    async def health_check():
        """Эндпоинт для проверки работоспособности сервиса"""
        return {"status": "healthy"}
    
    # События запуска и остановки приложения
    @application.on_event("startup")
    async def startup_event():
        """Действия при запуске приложения"""
        logger.info(f"Запуск приложения {settings.APP_NAME} v{settings.APP_VERSION}")
        
        # Инициализация соединения с RabbitMQ
        if settings.RABBITMQ_URL:
            rabbitmq_success = await messaging.initialize_rabbitmq()
            if rabbitmq_success:
                logger.info("RabbitMQ успешно инициализирован")
            else:
                logger.warning("Не удалось инициализировать RabbitMQ")
    
    @application.on_event("shutdown")
    async def shutdown_event():
        """Действия при остановке приложения"""
        logger.info(f"Остановка приложения {settings.APP_NAME}")
        
        # Закрытие соединения с RabbitMQ
        if settings.RABBITMQ_URL:
            await messaging.close_rabbitmq()
    
    return application


app = create_application()


if __name__ == "__main__":
    """Точка входа для локального запуска приложения"""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 