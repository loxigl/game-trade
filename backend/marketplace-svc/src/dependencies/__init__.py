"""
Модуль зависимостей для FastAPI
"""

from .auth import get_current_user, get_current_active_user
from .db import get_db 