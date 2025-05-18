from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database.connection import get_db, engine
from .routes.auth import router as auth_router
from .routes.register import router as register_router
from .routes.account import router as account_router
from .routes.roles import router as roles_router
from .routes.permissions import router as permissions_router
from sqlalchemy import text

app = FastAPI(
    title="GameTrade Authentication Service",
    description="API для аутентификации и авторизации пользователей в системе GameTrade. "
                "Предоставляет функционал регистрации, входа, управления профилем, "
                "а также управления ролями и разрешениями пользователей.",
    version="0.1.0",
    root_path="/api/auth",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Операции аутентификации и управления токенами"
        },
        {
            "name": "register",
            "description": "Регистрация и подтверждение аккаунтов"
        },
        {
            "name": "account",
            "description": "Управление профилем и настройками пользователя"
        },
        {
            "name": "roles",
            "description": "Управление ролями пользователей"
        },
        {
            "name": "permissions",
            "description": "Управление и проверка разрешений"
        }
    ]
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на реальные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем маршруты аутентификации
app.include_router(auth_router)
app.include_router(register_router)
app.include_router(account_router)
app.include_router(roles_router)
app.include_router(permissions_router)

@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Authentication Service API",
        "version": "0.1.0",
        "docs": "/api/docs"
    }

@app.get("/health", tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Проверка состояния сервиса аутентификации.
    Проверяет доступность базы данных и общее состояние приложения.
    """
    health_data = {
        "status": "healthy",
        "service": "auth",
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        # Проверяем соединение с базой данных
        db.execute(text("SELECT 1"))
        health_data["database"] = "connected"
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["database"] = "disconnected"
        health_data["error"] = str(e)
        return health_data, status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 