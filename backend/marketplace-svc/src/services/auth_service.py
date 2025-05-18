"""Сервис для взаимодействия с auth-svc"""

import httpx
import json
from typing import Optional, Dict, Any
import logging
from fastapi import HTTPException, status
from pydantic import BaseModel
from functools import lru_cache
import os
import time
from datetime import datetime, timedelta

from ..config.settings import get_settings

settings = get_settings()

# Получение URL для сервиса аутентификации из переменных окружения или конфигурации
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-svc:8000/api/auth')

# Настройка логирования
logger = logging.getLogger(__name__)


# Модель для информации о пользователе
class UserInfo(BaseModel):
    """Данные пользователя, полученные из токена"""
    user_id: int
    username: str


# Простой кэш для хранения результатов валидации токенов
_token_cache = {}
_cache_ttl = 60  # время жизни кэша в секундах


class AuthService:
    """Сервис для проверки аутентификации через auth-svc"""

    @staticmethod
    async def validate_token(token: str) -> Optional[UserInfo]:
        """Проверяет валидность JWT токена через auth-svc

        Args:
            token: JWT токен для проверки

        Returns:
            UserInfo: Информация о пользователе, если токен валиден
            None: Если токен не валиден

        Raises:
            HTTPException: В случае ошибки соединения с auth-svc
        """
        # Проверяем кэш
        cache_key = token[:32]  # Используем часть токена как ключ для безопасности
        current_time = time.time()

        if cache_key in _token_cache:
            cache_entry = _token_cache[cache_key]
            # Проверяем время жизни кэша
            if current_time - cache_entry['timestamp'] < _cache_ttl:
                logger.debug(f"Using cached token validation result")
                return cache_entry['result']
            else:
                # Удаляем устаревший кэш
                del _token_cache[cache_key]

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Sending token to auth-svc: {token[:10]}...")
                # Отправляем запрос на проверку токена
                response = await client.post(
                    f"{AUTH_SERVICE_URL}/validate",
                    json={"token": token},
                    timeout=5.0  # Таймаут для запроса
                )
                logger.info(f"Received response from auth-svc: {response.status_code}")

                # Проверяем успешность запроса
                if response.status_code != 200:
                    logger.error(f"Ошибка валидации токена: {response.status_code} - {response.text}")
                    return None

                # Разбираем ответ
                data = response.json()

                # Проверяем валидность токена
                if not data.get('is_valid', False):
                    return None

                # Создаем объект с информацией о пользователе
                result = UserInfo(
                    user_id=data.get('user_id'),
                    username=data.get('username')
                )

                # Сохраняем результат в кэш
                _token_cache[cache_key] = {
                    'result': result,
                    'timestamp': current_time
                }

                return result

        except (httpx.RequestError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка соединения с auth-svc: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Сервис аутентификации недоступен"
            )
