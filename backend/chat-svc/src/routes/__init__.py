"""
Модуль с маршрутами для chat-svc
"""

from .chats import router as chats_router
from .websockets import router as websockets_router

__all__ = [
    "chats_router",
    "websockets_router"

] 