"""
Сервис для управления ролями и разрешениями
"""
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Any

# Определение ролей в системе
class Role(str, Enum):
    """
    Роли пользователей в системе
    """
    GUEST = "guest"
    USER = "user"
    SELLER = "seller"
    MODERATOR = "moderator"
    ADMIN = "admin"

# Определение типов разрешений
class Permission(str, Enum):
    """
    Типы разрешений в системе
    """
    # Общие разрешения
    READ_PUBLIC = "read:public"
    
    # Разрешения для пользователей
    MANAGE_OWN_PROFILE = "manage:own-profile"
    MANAGE_OWN_ITEMS = "manage:own-items"
    
    # Разрешения для продавцов
    CREATE_LISTINGS = "create:listings"
    EDIT_LISTINGS = "edit:listings"
    MANAGE_ORDERS = "manage:orders"
    
    # Разрешения для модераторов
    MODERATE_CONTENT = "moderate:content"
    REVIEW_REPORTS = "review:reports"
    EDIT_PUBLIC_CONTENT = "edit:public-content"
    
    # Разрешения администраторов
    MANAGE_USERS = "manage:users"
    MANAGE_ROLES = "manage:roles"
    MANAGE_SYSTEM = "manage:system"

# Иерархия ролей с соответствующими разрешениями
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Role.GUEST: [
        Permission.READ_PUBLIC
    ],
    Role.USER: [
        Permission.READ_PUBLIC,
        Permission.MANAGE_OWN_PROFILE,
        Permission.MANAGE_OWN_ITEMS
    ],
    Role.SELLER: [
        Permission.READ_PUBLIC,
        Permission.MANAGE_OWN_PROFILE,
        Permission.MANAGE_OWN_ITEMS,
        Permission.CREATE_LISTINGS,
        Permission.EDIT_LISTINGS,
        Permission.MANAGE_ORDERS
    ],
    Role.MODERATOR: [
        Permission.READ_PUBLIC,
        Permission.MANAGE_OWN_PROFILE,
        Permission.MANAGE_OWN_ITEMS,
        Permission.MODERATE_CONTENT,
        Permission.REVIEW_REPORTS,
        Permission.EDIT_PUBLIC_CONTENT
    ],
    Role.ADMIN: [
        Permission.READ_PUBLIC,
        Permission.MANAGE_OWN_PROFILE,
        Permission.MANAGE_OWN_ITEMS,
        Permission.CREATE_LISTINGS,
        Permission.EDIT_LISTINGS,
        Permission.MANAGE_ORDERS,
        Permission.MODERATE_CONTENT,
        Permission.REVIEW_REPORTS,
        Permission.EDIT_PUBLIC_CONTENT,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_SYSTEM
    ]
}

# Иерархия ролей (от низших к высшим)
ROLE_HIERARCHY = [
    Role.GUEST,
    Role.USER,
    Role.SELLER,
    Role.MODERATOR,
    Role.ADMIN
]

def get_permissions_for_role(role: str) -> List[str]:
    """
    Получает список разрешений для указанной роли
    
    Args:
        role: Название роли
        
    Returns:
        Список разрешений для роли
    """
    return ROLE_PERMISSIONS.get(role, [])

def get_permissions_for_roles(roles: List[str]) -> Set[str]:
    """
    Получает объединенный набор разрешений для списка ролей
    
    Args:
        roles: Список ролей
        
    Returns:
        Набор разрешений для всех указанных ролей
    """
    permissions: Set[str] = set()
    
    for role in roles:
        role_permissions = get_permissions_for_role(role)
        permissions.update(role_permissions)
    
    return permissions

def is_higher_role(higher_role: str, lower_role: str) -> bool:
    """
    Проверяет, является ли первая роль выше второй в иерархии
    
    Args:
        higher_role: Предположительно высшая роль
        lower_role: Предположительно низшая роль
        
    Returns:
        True, если первая роль выше, иначе False
    """
    try:
        higher_index = ROLE_HIERARCHY.index(higher_role)
        lower_index = ROLE_HIERARCHY.index(lower_role)
        return higher_index > lower_index
    except ValueError:
        return False

def get_highest_role(roles: List[str]) -> Optional[str]:
    """
    Определяет самую высокую роль из списка
    
    Args:
        roles: Список ролей
        
    Returns:
        Самая высокая роль или None, если список пуст
    """
    if not roles:
        return None
    
    highest = Role.GUEST
    highest_index = 0
    
    for role in roles:
        try:
            role_index = ROLE_HIERARCHY.index(role)
            if role_index > highest_index:
                highest = role
                highest_index = role_index
        except ValueError:
            continue
    
    return highest

def has_permission(roles: List[str], required_permission: str) -> bool:
    """
    Проверяет, имеется ли у списка ролей указанное разрешение
    
    Args:
        roles: Список ролей
        required_permission: Требуемое разрешение
        
    Returns:
        True, если разрешение имеется, иначе False
    """
    permissions = get_permissions_for_roles(roles)
    return required_permission in permissions

def has_required_role(roles: List[str], required_role: str) -> bool:
    """
    Проверяет, имеется ли у пользователя указанная роль или выше
    
    Args:
        roles: Список ролей пользователя
        required_role: Требуемая роль
        
    Returns:
        True, если у пользователя есть требуемая роль или выше, иначе False
    """
    highest = get_highest_role(roles)
    
    if not highest:
        return False
    
    try:
        highest_index = ROLE_HIERARCHY.index(highest)
        required_index = ROLE_HIERARCHY.index(required_role)
        return highest_index >= required_index
    except ValueError:
        return False 