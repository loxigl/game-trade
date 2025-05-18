"""
Middleware и утилиты для авторизации на основе ролей
"""
from fastapi import Depends, HTTPException, status
from typing import List, Callable, Optional
from .auth_middleware import get_current_user
from .roles import has_required_role, has_permission, Role, Permission
from ..models.user import User

def require_role(required_role: str):
    """
    Создает зависимость, требующую наличия у пользователя указанной роли или выше
    
    Args:
        required_role: Требуемая роль
        
    Returns:
        Функция-зависимость для FastAPI
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Проверяет, имеет ли пользователь требуемую роль
        
        Args:
            current_user: Текущий пользователь
            
        Returns:
            Пользователь, если он имеет требуемую роль
            
        Raises:
            HTTPException: Если у пользователя нет требуемой роли
        """
        if not has_required_role(current_user.roles, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Для выполнения этой операции требуется роль {required_role} или выше"
            )
        return current_user
    
    return role_checker

def require_permission(required_permission: str):
    """
    Создает зависимость, требующую наличия у пользователя указанного разрешения
    
    Args:
        required_permission: Требуемое разрешение
        
    Returns:
        Функция-зависимость для FastAPI
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Проверяет, имеет ли пользователь требуемое разрешение
        
        Args:
            current_user: Текущий пользователь
            
        Returns:
            Пользователь, если он имеет требуемое разрешение
            
        Raises:
            HTTPException: Если у пользователя нет требуемого разрешения
        """
        if not has_permission(current_user.roles, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав для выполнения этой операции"
            )
        return current_user
    
    return permission_checker

# Предопределенные зависимости для распространенных ролей
require_admin = require_role(Role.ADMIN)
require_moderator = require_role(Role.MODERATOR)
require_seller = require_role(Role.SELLER)
require_user = require_role(Role.USER)

# Предопределенные зависимости для распространенных разрешений
require_manage_users = require_permission(Permission.MANAGE_USERS)
require_manage_roles = require_permission(Permission.MANAGE_ROLES)
require_manage_content = require_permission(Permission.MODERATE_CONTENT) 