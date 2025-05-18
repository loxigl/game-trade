"""
Маршруты для регистрации пользователей и управления аккаунтом
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
from ..database.connection import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserResponse
from ..services.password import hash_password, validate_password_strength
from ..services.rate_limiter import rate_limit
from ..config.settings import settings

# Создаем роутер для регистрации
router = APIRouter(
    tags=["register"],
    responses={400: {"description": "Некорректный запрос"}},
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    rate_limiter: None = Depends(rate_limit(3, 3600))  # Не более 3 регистраций в час с одного IP
) -> Dict[str, Any]:
    """
    Регистрация нового пользователя
    
    Args:
        user_data: Данные для создания пользователя
        background_tasks: Фоновые задачи FastAPI
        db: Сессия базы данных
        rate_limiter: Ограничитель частоты запросов
        
    Returns:
        Данные созданного пользователя
        
    Raises:
        HTTPException: Если валидация не прошла или пользователь уже существует
    """
    # Проверка сложности пароля
    is_valid, error_message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Хеширование пароля
    hashed_password = hash_password(user_data.password)
    
    # Генерация токена подтверждения
    verification_token = str(uuid4())
    verification_expires = datetime.utcnow() + timedelta(hours=24)
    
    # Создание нового пользователя
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        roles=["user"],  # Базовая роль
        password_reset_token=verification_token,
        password_reset_expires=verification_expires  # Используем это поле для срока действия токена верификации
    )
    
    try:
        # Добавление пользователя в базу данных
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Можно добавить отправку email с подтверждением в фоновую задачу
        # background_tasks.add_task(send_verification_email, new_user.email, verification_token)
        
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким именем или email уже существует"
        )

@router.get("/verify-email/{token}", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Подтверждение email пользователя
    
    Args:
        token: Токен подтверждения
        db: Сессия базы данных
        
    Returns:
        Сообщение об успешном подтверждении
        
    Raises:
        HTTPException: Если токен недействителен или истек срок его действия
    """
    # Поиск пользователя по токену
    user = db.query(User).filter(User.password_reset_token == token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Токен подтверждения недействителен"
        )
    
    # Проверка срока действия токена
    if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Срок действия токена подтверждения истек"
        )
    
    # Подтверждение аккаунта
    user.is_verified = True
    user.password_reset_token = None
    user.password_reset_expires = None
    
    db.commit()
    
    return {"message": "Email успешно подтвержден"}

@router.post("/reset-password-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    email: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    rate_limiter: None = Depends(rate_limit(3, 3600))  # Не более 3 запросов сброса пароля в час
) -> Dict[str, str]:
    """
    Запрос на сброс пароля
    
    Args:
        email: Словарь с email пользователя {"email": "user@example.com"}
        background_tasks: Фоновые задачи FastAPI
        db: Сессия базы данных
        rate_limiter: Ограничитель частоты запросов
        
    Returns:
        Сообщение об отправке инструкций
    """
    user_email = email.get("email")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не указан"
        )
    
    # Поиск пользователя по email
    user = db.query(User).filter(User.email == user_email).first()
    
    # Даже если пользователь не найден, мы не сообщаем об этом для безопасности
    if user:
        # Генерация токена сброса пароля
        reset_token = str(uuid4())
        reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        # Обновление данных пользователя
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        
        db.commit()
        
        # Можно добавить отправку email с токеном сброса пароля в фоновую задачу
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
    
    return {"message": "Если учетная запись с указанным email существует, инструкции по сбросу пароля были отправлены"}

@router.post("/reset-password/{token}", status_code=status.HTTP_200_OK)
async def reset_password(
    token: str,
    new_password: Dict[str, str],
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Сброс пароля по токену
    
    Args:
        token: Токен сброса пароля
        new_password: Словарь с новым паролем {"password": "new_password"}
        db: Сессия базы данных
        
    Returns:
        Сообщение об успешном сбросе пароля
        
    Raises:
        HTTPException: Если токен недействителен, истек срок его действия или пароль не соответствует требованиям
    """
    # Извлечение нового пароля
    password = new_password.get("password")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль не указан"
        )
    
    # Проверка сложности пароля
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Поиск пользователя по токену
    user = db.query(User).filter(User.password_reset_token == token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Токен сброса пароля недействителен"
        )
    
    # Проверка срока действия токена
    if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Срок действия токена сброса пароля истек"
        )
    
    # Обновление пароля
    user.hashed_password = hash_password(password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.last_password_change = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Пароль успешно изменен"} 