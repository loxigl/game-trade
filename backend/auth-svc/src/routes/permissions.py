"""
Маршруты для управления разрешениями
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from ..models.user import User
from ..schemas.role import PermissionInfo
from ..services.authorization import require_admin
from ..services.roles import Permission, ROLE_PERMISSIONS, has_permission

# Создаем роутер для управления разрешениями
router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
    responses={401: {"description": "Не авторизован"}, 403: {"description": "Запрещено"}},
)

@router.get("/", response_model=List[str])
async def get_all_permissions(
    _: User = Depends(require_admin)
) -> List[str]:
    """
    Получение списка всех доступных разрешений
    
    Args:
        _: Текущий пользователь с правами админа
        
    Returns:
        Список разрешений
    """
    return [permission for permission in Permission]

@router.get("/info", response_model=List[PermissionInfo])
async def get_permissions_info(
    _: User = Depends(require_admin)
) -> List[PermissionInfo]:
    """
    Получение подробной информации о разрешениях
    
    Args:
        _: Текущий пользователь с правами админа
        
    Returns:
        Список информации о разрешениях
    """
    permission_descriptions = {
        Permission.READ_PUBLIC: "Чтение публичного контента",
        Permission.MANAGE_OWN_PROFILE: "Управление собственным профилем",
        Permission.MANAGE_OWN_ITEMS: "Управление собственными товарами",
        Permission.CREATE_LISTINGS: "Создание торговых объявлений",
        Permission.EDIT_LISTINGS: "Редактирование торговых объявлений",
        Permission.MANAGE_ORDERS: "Управление заказами",
        Permission.MODERATE_CONTENT: "Модерация контента пользователей",
        Permission.REVIEW_REPORTS: "Просмотр и обработка жалоб",
        Permission.EDIT_PUBLIC_CONTENT: "Редактирование публичного контента",
        Permission.MANAGE_USERS: "Управление пользователями",
        Permission.MANAGE_ROLES: "Управление ролями пользователей",
        Permission.MANAGE_SYSTEM: "Управление настройками системы"
    }
    
    return [
        PermissionInfo(
            name=permission,
            description=permission_descriptions.get(permission, "")
        )
        for permission in Permission
    ]

@router.get("/role/{role}", response_model=List[str])
async def get_permissions_by_role(
    role: str,
    _: User = Depends(require_admin)
) -> List[str]:
    """
    Получение списка разрешений для указанной роли
    
    Args:
        role: Название роли
        _: Текущий пользователь с правами админа
        
    Returns:
        Список разрешений для роли
        
    Raises:
        HTTPException: Если роль не существует
    """
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Роль '{role}' не существует"
        )
    
    return ROLE_PERMISSIONS[role]

@router.get("/check", response_model=Dict[str, bool])
async def check_user_permission(
    current_user: User = Depends(require_admin)
) -> Dict[str, bool]:
    """
    Проверка наличия разрешений у текущего пользователя
    
    Args:
        current_user: Текущий пользователь с правами админа
        
    Returns:
        Словарь с разрешениями и флагами наличия
    """
    return {
        permission: has_permission(current_user.roles, permission)
        for permission in Permission
    } 