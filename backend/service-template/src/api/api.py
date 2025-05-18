from fastapi import APIRouter

from .endpoints import example

# Создаем главный API роутер
api_router = APIRouter()

# Подключаем все роутеры модулей
api_router.include_router(example.router, prefix="/example", tags=["example"])

# Здесь можно добавить и другие роутеры, например:
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
# и т.д. 