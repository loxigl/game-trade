"""
Модуль роутеров API для маркетплейса
"""

from .listings import router as listings_router
from .categories import router as categories_router
from .games import router as games_router
from .search import router as search_router
from .images import router as images_router
from .templates import router as templates_router

# Экспортируем роутеры для удобства импорта
listings = listings_router
categories = categories_router
games = games_router
search = search_router
images = images_router
templates = templates_router 