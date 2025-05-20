"""Сервис для взаимодействия с auth-svc"""

import httpx
import json
from typing import Optional, Dict, Any
import logging
from fastapi import HTTPException, status, Request
from pydantic import BaseModel
import os
from sqlalchemy.orm import Session
from ..models.core import User
import time
from datetime import datetime, timedelta

from ..config.settings import get_settings

settings = get_settings()

# Получение URL для сервиса аутентификации из переменных окружения или конфигурации
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-svc:8000')

# Настройка логирования
logger = logging.getLogger(__name__)


# Модель для информации о пользователе
class UserInfo(BaseModel):
    """Данные пользователя, полученные из токена"""
    user_id: int
    username: str
    token: str


class UserResponse(BaseModel):
    """Данные пользователя, полученные из auth-svc"""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    roles: list[str]
    is_verified: bool

# Простой кэш для хранения результатов валидации токенов
_token_cache = {}
_cache_ttl = 60  # время жизни кэша в секундах


class AuthService:
    """Сервис для проверки аутентификации через auth-svc"""

    @staticmethod
    async def validate_token(token: str) -> Optional[UserInfo]:
        """Проверяет валидность JWT токена через auth-svc"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"Sending token to auth-svc: {token[:10]}...")
                # Отправляем запрос на проверку токена
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/api/auth/validate",
                    json={"token": token},
                )
                
                logger.info(f"Received response from auth-svc: {response.status_code}")
                logger.debug(f"Response content: {response.text[:100]}")

                # Проверяем успешность запроса
                if response.status_code != 200:
                    logger.error(f"Ошибка валидации токена: {response.status_code} - {response.text}")
                    return None

                # Разбираем ответ
                data = response.json()

                # Проверяем валидность токена
                if not data.get('is_valid', False):
                    logger.error(f"Токен не валиден: {data}")
                    return None

                # Создаем объект с информацией о пользователе
                user_id = data.get('user_id')
                username = data.get('username')
                
                if not user_id or not username:
                    logger.error(f"Недостаточно данных пользователя: {data}")
                    return None
                    
                result = UserInfo(
                    user_id=user_id,
                    username=username,
                    token=token
                )
                
                logger.info(f"Пользователь успешно получен: {username} (ID: {user_id})")
                return result

        except Exception as e:
            logger.error(f"Ошибка при валидации токена: {str(e)}", exc_info=True)
            return None

    @staticmethod
    async def get_current_user(request: Request) -> Optional[UserInfo]:
        """Получение текущего пользователя из заголовка Authorization"""
        # Получаем токен из заголовка
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Заголовок Authorization отсутствует")
            return None
            
        # Проверяем формат и наличие Bearer
        if not auth_header.startswith("Bearer "):
            logger.warning("Неверный формат заголовка Authorization")
            return None
            
        token = auth_header.replace("Bearer ", "")
        return await AuthService.validate_token(token)
    
    @staticmethod
    async def get_user_data(token: str) -> Optional[UserResponse]:
        """Получение данных пользователя из auth-svc"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{AUTH_SERVICE_URL}/api/auth/account/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code != 200:
                    logger.error(f"Ошибка получения данных пользователя: {response.status_code} - {response.text}")
                    return None
                return UserResponse(**response.json())
        except Exception as e:
            logger.error(f"Ошибка при получении данных пользователя: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def create_user(token: str, db: Session) -> Optional[User]:
        """Создание пользователя в локальной БД на основе данных из auth-svc"""
        try:
            # Сначала получаем данные пользователя из auth-svc
            user_data = await AuthService.get_user_data(token)
            if not user_data:
                logger.error("Не удалось получить данные пользователя из auth-svc")
                return None

            # Проверяем, существует ли пользователь в локальной БД
            existing_user = db.query(User).filter(User.id == user_data.id).first()
            if existing_user:
                logger.info(f"Пользователь {user_data.username} уже существует в локальной БД")
                return existing_user

            # Создаем пользователя в локальной БД
            user = User(
                id=user_data.id,
                username=user_data.username,
                email=user_data.email,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Пользователь {user.username} успешно создан в локальной БД")
            return user
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя в локальной БД: {str(e)}", exc_info=True)
            db.rollback()
            return None

