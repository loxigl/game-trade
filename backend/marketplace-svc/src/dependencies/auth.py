"""
Зависимости для аутентификации и авторизации
"""

import os
from typing import Optional, Annotated, Dict, Any
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import httpx
import logging
import time
from functools import lru_cache

from ..database.connection import get_db
from ..models.core import User
from ..services.auth_service import AuthService

# Конфигурация аутентификации
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-svc:8000")
TOKEN_SCHEME = OAuth2PasswordBearer(tokenUrl=f"{AUTH_SERVICE_URL}/token")

# Настройка логирования
logger = logging.getLogger(__name__)

# Кеш для пользовательских данных, чтобы уменьшить количество запросов к auth-svc
@lru_cache(maxsize=1000)
def cache_user_data(user_id: int, token_hash: str) -> Dict[str, Any]:
    """
    Кеширует данные пользователя по ID и хешу токена

    Args:
        user_id: ID пользователя
        token_hash: Хеш токена для инвалидации кеша при изменении токена

    Returns:
        Dict[str, Any]: Кешированные данные пользователя
    """
    # Этот метод в реальности ничего не делает, но используется как ключ для lru_cache
    pass

async def get_current_user(
    token: str = Depends(TOKEN_SCHEME),
    db: Session = Depends(get_db)
) -> User:
    """
    Получает текущего пользователя по токену JWT

    Args:
        token: JWT токен
        db: Сессия базы данных

    Returns:
        User: Объект пользователя

    Raises:
        HTTPException: Если токен недействителен или пользователь не найден
    """
    try:
        # Измерение времени запроса для мониторинга производительности
        start_time = time.time()

        # Используем сервис AuthService для валидации токена
        user_info = await AuthService.validate_token(token)
        
        # Логирование результата запроса
        request_time = time.time() - start_time
        logger.debug(f"Auth service response time: {request_time:.4f}s")
        
        if not user_info:
            logger.warning("Token validation failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительные учетные данные",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Ищем пользователя в локальной БД marketplace-svc
        db_user = db.query(User).filter(User.id == user_info.user_id).first()
        user_data = await AuthService.get_user_data(token)
        # Если пользователя нет в локальной БД, создаем его
        if not db_user:
            logger.info(f"Creating new user in marketplace-svc database: {user_info.user_id}")
            db_user = User(
                id=user_info.user_id,
                username=user_info.username,
                email=user_data.email
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        
        return db_user

    except Exception as e:
        logger.error(f"Error during token validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительные учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Проверяет, что текущий пользователь активен

    Args:
        current_user: Текущий аутентифицированный пользователь

    Returns:
        User: Объект активного пользователя

    Raises:
        HTTPException: Если пользователь неактивен
    """
    # if not current_user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Активная запись не найдена",
    #     )
    return current_user

def has_role(required_role: str):
    """
    Зависимость для проверки роли пользователя

    Args:
        required_role: Требуемая роль

    Returns:
        Callable: Зависимость для FastAPI
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = getattr(current_user, "roles", [])
        if required_role not in user_roles and "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Роль {required_role} требуется для доступа"
            )
        return current_user
    return role_checker

def has_permission(required_permission: str):
    """
    Зависимость для проверки разрешения пользователя

    Args:
        required_permission: Требуемое разрешение

    Returns:
        Callable: Зависимость для FastAPI
    """
    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = getattr(current_user, "permissions", [])
        if required_permission not in user_permissions and "admin" not in getattr(current_user, "roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Разрешение {required_permission} требуется для доступа"
            )
        return current_user
    return permission_checker
