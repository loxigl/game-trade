"""
Зависимости для доступа к базе данных
"""

from typing import Generator
from sqlalchemy.orm import Session
from ..database.connection import get_db 