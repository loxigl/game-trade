from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from ..core.config import settings
from ..schemas.auth import TokenData, UserResponse

# Схема OAuth2 для получения токена доступа
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена доступа.
    
    Аргументы:
        data (dict): Данные, которые нужно закодировать в токене.
        expires_delta (Optional[timedelta]): Время жизни токена.
        
    Возвращает:
        str: Закодированный JWT токен.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    Получение текущего пользователя из JWT токена.
    
    Аргументы:
        token (str): JWT токен доступа.
        
    Возвращает:
        UserResponse: Данные текущего пользователя.
        
    Raises:
        HTTPException: Если токен недействительный или не содержит необходимые данные.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Декодирование токена
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Извлечение данных пользователя из токена
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        
        if username is None or user_id is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # В реальном приложении здесь нужно запросить пользователя из базы данных
    # и проверить, существует ли он и активен ли
    
    # Для примера, просто возвращаем данные из токена
    # В реальном приложении замените это на запрос к базе данных
    user = UserResponse(
        id=token_data.user_id,
        username=token_data.username,
        email=f"{token_data.username}@example.com",  # Здесь должен быть реальный email из БД
        is_active=True,
        is_verified=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    if user is None:
        raise credentials_exception
    
    return user

# Дополнительные зависимости можно добавить здесь, например:

async def get_current_active_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Проверяет, что текущий пользователь активен.
    
    Аргументы:
        current_user (UserResponse): Текущий пользователь.
        
    Возвращает:
        UserResponse: Данные текущего пользователя.
        
    Raises:
        HTTPException: Если пользователь неактивен.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неактивный пользователь"
        )
    return current_user

async def get_current_admin_user(current_user: UserResponse = Depends(get_current_active_user)) -> UserResponse:
    """
    Проверяет, что текущий пользователь является администратором.
    
    Аргументы:
        current_user (UserResponse): Текущий пользователь.
        
    Возвращает:
        UserResponse: Данные текущего пользователя.
        
    Raises:
        HTTPException: Если пользователь не является администратором.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    return current_user 