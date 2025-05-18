"""
Маршруты для аутентификации и выдачи токенов
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Dict, Any
from jose import jwt
from ..database.connection import get_db
from ..models.user import User
from ..schemas.user import Token, UserLogin, TokenValidateRequest, TokenValidateResponse
from ..services.password import verify_password
from ..services.jwt import create_access_token, create_refresh_token, refresh_tokens, blacklist_token, decode_token
from ..services.rate_limiter import rate_limit
from ..config.settings import settings
from datetime import datetime, timedelta

# Создаем роутер для аутентификации
router = APIRouter(
    tags=["auth"],
    responses={401: {"description": "Не авторизован"}},
)

@router.post("/login", response_model=Token)
async def login_for_access_token(
    user_data: UserLogin,
    db: Session = Depends(get_db),
    rate_limiter: None = Depends(rate_limit(5, 60))  # Не более 5 попыток в минуту
) -> Dict[str, str]:
    """
    Аутентификация пользователя и выдача JWT токенов
    
    Args:
        user_data: Данные пользователя
        db: Сессия базы данных
        rate_limiter: Ограничитель частоты запросов
        
    Returns:
        Словарь с токенами доступа и обновления
        
    Raises:
        HTTPException: Если аутентификация не удалась
    """
    user = db.query(User).filter(User.email == user_data.email).first()

    
    # Проверка существования пользователя и правильности пароля
    if not user or not verify_password(user_data.password, user.hashed_password):
        # Увеличиваем счетчик неудачных попыток входа, если пользователь существует
        if user:
            user.failed_login_attempts += 1
            
            # Блокируем аккаунт, если превышено число попыток
            if user.failed_login_attempts >= 5:  # Значение для примера, лучше вынести в настройки
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                
            db.commit()
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка активности аккаунта
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )
    
    # Проверка блокировки аккаунта
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Аккаунт заблокирован до {user.account_locked_until}",
        )
    
    # Сбрасываем счетчик неудачных попыток входа
    user.failed_login_attempts = 0
    user.last_password_change = user.last_password_change or datetime.utcnow()
    db.commit()
    
    # Создаем данные для JWT токена
    token_data = {
        "sub": str(user.id),
        "username": user.username
    }
    
    # Создаем токены
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Возвращаем токены
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    token: Dict[str, str],
    rate_limiter: None = Depends(rate_limit(10, 60))  # Не более 10 обновлений в минуту
) -> Dict[str, str]:
    """
    Обновление токенов доступа с использованием refresh токена
    
    Args:
        token: Словарь с refresh токеном {"refresh_token": "..."}
        rate_limiter: Ограничитель частоты запросов
        
    Returns:
        Словарь с новыми токенами
        
    Raises:
        HTTPException: Если refresh токен недействителен
    """
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отсутствует refresh токен",
        )
    
    try:
        # Получаем новые токены
        new_tokens = refresh_tokens(refresh_token)
        
        # Добавляем тип токена
        new_tokens["token_type"] = "bearer"
        
        return new_tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Недействительный refresh токен: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: Dict[str, str]
) -> None:
    """
    Выход из системы путем добавления токенов в черный список
    
    Args:
        token: Словарь с токенами {"access_token": "...", "refresh_token": "..."}
        
    Returns:
        None
    """
    # Выходим из системы только если предоставлены токены
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    
    # Добавляем токены в черный список, если они предоставлены
    if access_token:
        try:
            # Получаем информацию о токене
            payload = jwt.decode(
                access_token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Добавляем токен в черный список
            blacklist_token(
                payload.get("jti", ""), 
                datetime.fromtimestamp(payload.get("exp", 0))
            )
        except:
            # Игнорируем ошибки при добавлении в черный список
            pass
    
    if refresh_token:
        try:
            # Получаем информацию о токене
            payload = jwt.decode(
                refresh_token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Добавляем токен в черный список
            blacklist_token(
                payload.get("jti", ""), 
                datetime.fromtimestamp(payload.get("exp", 0))
            )
        except:
            # Игнорируем ошибки при добавлении в черный список
            pass 

@router.post("/validate", response_model=TokenValidateResponse)
async def validate_token(
    token_data: TokenValidateRequest,
) -> TokenValidateResponse:
    """
    Валидация JWT токена
    
    Проверяет действительность токена и возвращает информацию о пользователе
    
    Args:
        token_data: Данные токена для проверки
        
    Returns:
        Информация о валидности токена и пользователя
    """
    try:
        # Декодируем токен
        payload = decode_token(token_data.token)
        
        # Возвращаем информацию о валидности токена и пользователя
        return TokenValidateResponse(
            is_valid=True,
            user_id=int(payload.get("sub", 0)),
            username=payload.get("username")
        )
    except Exception as e:
        # Возвращаем информацию о невалидности токена
        return TokenValidateResponse(
            is_valid=False,
            user_id=None,
            username=None
        ) 
