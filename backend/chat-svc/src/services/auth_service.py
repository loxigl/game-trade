"""
Сервис для аутентификации через auth-svc
"""

import httpx
import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# URL сервиса аутентификации
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-svc:8000")

# Схема для получения JWT токена
security = HTTPBearer()


class User:
    """Класс пользователя"""
    def __init__(self, id: int, username: str, roles: List[str]):
        self.id = id
        self.username = username
        self.roles = roles

    def has_role(self, role: str) -> bool:
        """Проверка наличия роли у пользователя"""
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """Проверка наличия любой из указанных ролей"""
        return any(role in self.roles for role in roles)


class AuthService:
    """Сервис для аутентификации"""

    def __init__(self):
        self.auth_url = AUTH_SERVICE_URL

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Валидация токена через auth-svc
        
        Args:
            token: JWT токен
            
        Returns:
            Данные пользователя или None
        """
        try:
            logger.info(f"validate_token: {token}")
            async with httpx.AsyncClient() as client:
                
                response = await client.post(
                    f"{self.auth_url}/validate",
                    json={"token": token},
                    timeout=10.0
                )
                logger.info(f"response: {response}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("is_valid"):
                        return data
                    
                return None
                
        except Exception as e:
            logger.error(f"Ошибка валидации токена: {str(e)}")
            return None

    async def get_user_info(self, user_id: int, token: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе
        
        Args:
            user_id: ID пользователя
            token: JWT токен для авторизации
            
        Returns:
            Данные пользователя или None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_url}/account/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                    
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе: {str(e)}")
            return None

    async def get_user_roles(self, token: str) -> List[str]:
        """
        Получение ролей пользователя
        
        Args:
            token: JWT токен
            
        Returns:
            Список ролей пользователя
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_url}/account/roles",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                    
                return []
                
        except Exception as e:
            logger.error(f"Ошибка получения ролей пользователя: {str(e)}")
            return []


# Singleton экземпляр
auth_service = AuthService()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Получение текущего аутентифицированного пользователя
    
    Args:
        credentials: HTTP Bearer токен
        
    Returns:
        Объект пользователя
        
    Raises:
        HTTPException: Если токен недействителен
    """
    token = credentials.credentials
    
    # Валидируем токен
    user_data = await auth_service.validate_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )
    
    # Получаем роли пользователя
    roles = await auth_service.get_user_roles(token)
    
    return User(
        id=user_data["user_id"],
        username=user_data["username"],
        roles=roles
    )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """
    Получение пользователя (опционально)
    
    Args:
        credentials: HTTP Bearer токен (опционально)
        
    Returns:
        Объект пользователя или None
    """
    if not credentials:
        return None
        
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(role: str):
    """
    Декоратор для проверки роли пользователя
    
    Args:
        role: Требуемая роль
        
    Returns:
        Функция зависимости
    """
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {role}"
            )
        return current_user
    
    return check_role


def require_any_role(roles: List[str]):
    """
    Декоратор для проверки любой из указанных ролей
    
    Args:
        roles: Список ролей (достаточно одной)
        
    Returns:
        Функция зависимости
    """
    async def check_roles(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется одна из ролей: {', '.join(roles)}"
            )
        return current_user
    
    return check_roles


# Предопределенные зависимости для ролей
require_admin = require_role("admin")
require_moderator = require_any_role(["admin", "moderator"])
require_seller = require_any_role(["admin", "moderator", "seller"]) 