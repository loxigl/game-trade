"""
Маршруты для управления ролями пользователей
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from ..database.connection import get_db
from ..models.user import User
from ..schemas.role import RoleAssign, RoleRevoke, UserWithRoles, RoleInfo
from ..services.authorization import require_admin, require_manage_roles
from ..services.roles import Role, ROLE_HIERARCHY, is_higher_role, get_permissions_for_role

# Создаем роутер для управления ролями
router = APIRouter(
    prefix="/roles",
    tags=["roles"],
    responses={401: {"description": "Не авторизован"}, 403: {"description": "Запрещено"}},
)

@router.get("/", response_model=List[str])
async def get_available_roles(
    _: User = Depends(require_admin)
) -> List[str]:
    """
    Получение списка доступных ролей
    
    Args:
        _: Текущий пользователь с правами админа
        
    Returns:
        Список доступных ролей
    """
    return [role for role in ROLE_HIERARCHY if role != Role.GUEST]

@router.get("/info", response_model=List[RoleInfo])
async def get_roles_info(
    _: User = Depends(require_admin)
) -> List[RoleInfo]:
    """
    Получение подробной информации о ролях
    
    Args:
        _: Текущий пользователь с правами админа
        
    Returns:
        Список информации о ролях
    """
    role_descriptions = {
        Role.USER: "Базовая роль для всех пользователей системы",
        Role.SELLER: "Роль для продавцов с возможностью создания и управления товарами",
        Role.MODERATOR: "Роль для модерации контента и пользователей",
        Role.ADMIN: "Административная роль с полным доступом к системе"
    }
    
    return [
        RoleInfo(
            name=role,
            description=role_descriptions.get(role, ""),
            permissions=get_permissions_for_role(role)
        )
        for role in ROLE_HIERARCHY if role != Role.GUEST
    ]

@router.post("/assign", status_code=status.HTTP_200_OK)
async def assign_role(
    role_data: RoleAssign,
    current_user: User = Depends(require_manage_roles),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Назначение роли пользователю
    
    Args:
        role_data: Данные для назначения роли
        current_user: Текущий пользователь с правами управления ролями
        db: Сессия базы данных
        
    Returns:
        Сообщение об успешном назначении роли
        
    Raises:
        HTTPException: Если пользователь не найден, роль не существует или недостаточно прав
    """
    # Проверяем существование роли
    if role_data.role not in [r for r in ROLE_HIERARCHY if r != Role.GUEST]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Роль {role_data.role} не существует"
        )
    
    # Получаем пользователя
    user = db.query(User).filter(User.id == role_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверяем, что текущий пользователь имеет достаточно прав для назначения роли
    # (т.е. имеет роль выше, чем назначает)
    highest_current_role = max(current_user.roles, key=lambda r: ROLE_HIERARCHY.index(r) if r in ROLE_HIERARCHY else -1)
    
    if not is_higher_role(highest_current_role, role_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для назначения этой роли"
        )
    
    # Добавляем роль пользователю, если она у него еще не назначена
    if role_data.role not in user.roles:
        user.roles.append(role_data.role)
        db.commit()
    
    return {"message": f"Роль {role_data.role} успешно назначена пользователю с ID {role_data.user_id}"}

@router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke_role(
    role_data: RoleRevoke,
    current_user: User = Depends(require_manage_roles),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Отзыв роли у пользователя
    
    Args:
        role_data: Данные для отзыва роли
        current_user: Текущий пользователь с правами управления ролями
        db: Сессия базы данных
        
    Returns:
        Сообщение об успешном отзыве роли
        
    Raises:
        HTTPException: Если пользователь не найден, роль не существует или недостаточно прав
    """
    # Получаем пользователя
    user = db.query(User).filter(User.id == role_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверяем, что текущий пользователь имеет достаточно прав для отзыва роли
    highest_current_role = max(current_user.roles, key=lambda r: ROLE_HIERARCHY.index(r) if r in ROLE_HIERARCHY else -1)
    
    if not is_higher_role(highest_current_role, role_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для отзыва этой роли"
        )
    
    # Удаляем роль у пользователя, если она у него есть
    if role_data.role in user.roles:
        user.roles.remove(role_data.role)
        
        # Проверяем, есть ли у пользователя хотя бы одна роль
        if not user.roles:
            # Если нет, добавляем базовую роль user
            user.roles.append(Role.USER)
        
        db.commit()
    
    return {"message": f"Роль {role_data.role} успешно отозвана у пользователя с ID {role_data.user_id}"}

@router.get("/users/{role}", response_model=List[UserWithRoles])
async def get_users_by_role(
    role: str,
    _: User = Depends(require_manage_roles),
    db: Session = Depends(get_db)
) -> List[UserWithRoles]:
    """
    Получение списка пользователей с указанной ролью
    
    Args:
        role: Название роли
        _: Текущий пользователь с правами управления ролями
        db: Сессия базы данных
        
    Returns:
        Список пользователей с данной ролью
        
    Raises:
        HTTPException: Если роль не существует
    """
    # Проверяем существование роли
    if role not in [r for r in ROLE_HIERARCHY]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Роль {role} не существует"
        )
    
    # Получаем всех пользователей
    users = db.query(User).all()
    
    # Фильтруем пользователей по наличию указанной роли
    users_with_role = [
        UserWithRoles(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=user.roles,
            is_active=user.is_active
        )
        for user in users if role in user.roles
    ]
    
    return users_with_role 