"""
Маршруты для управления аккаунтом пользователя
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
from ..database.connection import get_db
from ..models.user import User
from ..schemas.user import UserResponse, UserUpdate
from ..services.auth_middleware import get_current_user
from ..services.password import hash_password, validate_password_strength
from ..services.client_auth import get_client_permissions, get_ui_permissions

# Создаем роутер для аккаунта
router = APIRouter(
    prefix="/account",
    tags=["account"],
    responses={401: {"description": "Не авторизован"}},
)

@router.get("/me", response_model=UserResponse)
async def get_current_account(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Получение данных текущего пользователя

    Args:
        current_user: Текущий авторизованный пользователь

    Returns:
        Данные пользователя
    """
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_account(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Обновление данных текущего пользователя

    Args:
        user_data: Данные для обновления
        current_user: Текущий авторизованный пользователь
        db: Сессия базы данных

    Returns:
        Обновленные данные пользователя

    Raises:
        HTTPException: Если валидация не прошла или произошла ошибка обновления
    """
    # Обновляем только предоставленные данные
    if user_data.username is not None:
        current_user.username = user_data.username

    if user_data.email is not None:
        current_user.email = user_data.email
        # При изменении email можно сбросить статус верификации
        current_user.is_verified = False

    if user_data.password is not None:
        # Проверка сложности пароля
        is_valid, error_message = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # Хеширование и обновление пароля
        current_user.hashed_password = hash_password(user_data.password)
        current_user.last_password_change = datetime.utcnow()

    # Сохранение изменений
    db.commit()
    db.refresh(current_user)

    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> None:
    """
    Удаление аккаунта текущего пользователя

    Args:
        current_user: Текущий авторизованный пользователь
        db: Сессия базы данных
    """
    # Удаление пользователя (можно заменить на деактивацию)
    db.delete(current_user)
    db.commit()

@router.get("/roles", response_model=List[str])
async def get_user_roles(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """
    Получение списка ролей текущего пользователя

    Args:
        current_user: Текущий авторизованный пользователь

    Returns:
        Список ролей пользователя
    """
    return current_user.roles

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    passwords: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Изменение пароля текущего пользователя

    Args:
        passwords: Словарь с текущим и новым паролями
                  {"current_password": "old", "new_password": "new"}
        current_user: Текущий авторизованный пользователь
        db: Сессия базы данных

    Returns:
        Сообщение об успешном изменении пароля

    Raises:
        HTTPException: Если текущий пароль неверен или новый пароль не
                      соответствует требованиям
    """
    # Проверка наличия необходимых полей
    current_password = passwords.get("current_password")
    new_password = passwords.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать текущий и новый пароли"
        )

    # Проверка текущего пароля
    from ..services.password import verify_password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный текущий пароль"
        )

    # Проверка сложности нового пароля
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Обновление пароля
    current_user.hashed_password = hash_password(new_password)
    current_user.last_password_change = datetime.utcnow()

    db.commit()

    return {"message": "Пароль успешно изменен"}

@router.get("/permissions")
async def get_current_user_permissions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получение информации о разрешениях текущего пользователя

    Args:
        current_user: Текущий пользователь

    Returns:
        Информация о разрешениях пользователя
    """
    client_permissions = get_client_permissions(current_user.roles)
    return client_permissions

@router.get("/ui-permissions")
async def get_current_user_ui_permissions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, bool]:
    """
    Получение информации о разрешениях для элементов UI

    Args:
        current_user: Текущий пользователь

    Returns:
        Словарь с флагами разрешений для UI
    """
    return get_ui_permissions(current_user.roles)
