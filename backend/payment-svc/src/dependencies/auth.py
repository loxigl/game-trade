"""
Модуль для аутентификации и авторизации пользователей через auth-svc
"""

import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from ..services.auth_service import AuthService, UserInfo
from fastapi.security import OAuth2PasswordBearer
from ..database.connection import get_db
import httpx
import logging
import os
import json
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# URL сервиса аутентификации
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-svc:8000")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{AUTH_SERVICE_URL}/token")

class User(BaseModel):
    """Базовая модель пользователя"""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool = False
    is_seller: bool = False
    
    class Config:
        orm_mode = True


async def get_current_user(request: Request) -> UserInfo:
    """Получение текущего пользователя по токену"""
    user = await AuthService.get_current_user(request)
    if not user:
        logger.error("Не удалось аутентифицировать пользователя")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_token(request: Request) -> str:
    """Получение токена из заголовка Authorization"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.split(" ")[1]

async def get_current_active_user(request: Request) -> User:
    """Проверка, что пользователь активен и преобразование UserInfo в User"""
    user_info = await get_current_user(request)
    user_data = await AuthService.get_user_data(user_info.token)
    # Преобразование UserInfo в User
    user = User(**user_data.model_dump())
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Проверка, что текущий пользователь имеет права администратора"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    return current_user

async def get_current_seller_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Проверка, что текущий пользователь является продавцом"""
    if not current_user.is_seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь не является продавцом"
        )
    return current_user 