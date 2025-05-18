"""
Схемы для работы с ролями пользователей
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class RoleAssign(BaseModel):
    """Схема для назначения роли пользователю"""
    user_id: int = Field(..., description="ID пользователя")
    role: str = Field(..., description="Название роли для назначения")

class RoleRevoke(BaseModel):
    """Схема для отзыва роли у пользователя"""
    user_id: int = Field(..., description="ID пользователя")
    role: str = Field(..., description="Название роли для отзыва")

class UserWithRoles(BaseModel):
    """Схема для отображения пользователя с его ролями"""
    id: int
    username: str
    email: str
    roles: List[str]
    is_active: bool

    class Config:
        from_attributes = True

class RoleInfo(BaseModel):
    """Схема для отображения информации о роли"""
    name: str
    description: str
    permissions: List[str]

class RoleWithUsers(BaseModel):
    """Схема для отображения роли со списком пользователей"""
    role: str
    users: List[UserWithRoles]
    total: int

class PermissionInfo(BaseModel):
    """Схема для отображения информации о разрешении"""
    name: str
    description: str 