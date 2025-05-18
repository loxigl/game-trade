"""
Сервис для работы с JWT токенами аутентификации
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from uuid import uuid4
from ..config.settings import settings
from redis import Redis

# Инициализация Redis для работы с черным списком токенов
redis_client = Redis.from_url(settings.REDIS_URL)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT access token
    
    Args:
        data: Данные для включения в полезную нагрузку токена
        expires_delta: Срок действия токена (если None, используется значение по умолчанию)
        
    Returns:
        Строка с JWT токеном
    """
    to_encode = data.copy()
    
    # Если срок действия не указан, используем значение из настроек
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    # Добавляем стандартные поля JWT
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),  # Уникальный идентификатор токена для возможности отзыва
        "type": "access"
    })
    
    # Кодируем токен
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Создает JWT refresh token с длительным сроком действия
    
    Args:
        data: Данные для включения в полезную нагрузку токена
        
    Returns:
        Строка с JWT refresh токеном
    """
    to_encode = data.copy()
    
    # Refresh токен действует 30 дней
    expire = datetime.utcnow() + timedelta(days=30)
    
    # Добавляем стандартные поля JWT
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),
        "type": "refresh"
    })
    
    # Кодируем токен
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Проверяет JWT токен на валидность
    
    Args:
        token: JWT токен для проверки
        token_type: Тип токена ("access" или "refresh")
        
    Returns:
        Декодированные данные из токена
        
    Raises:
        JWTError: Если токен недействителен или истек срок его действия
    """
    try:
        # Декодируем токен
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Проверяем, соответствует ли тип токена
        if payload.get("type") != token_type:
            raise JWTError(f"Token type mismatch: expected {token_type}")
        
        # Проверяем, не в черном ли списке токен
        token_jti = payload.get("jti")
        if token_jti and is_token_blacklisted(token_jti):
            raise JWTError("Token has been blacklisted")
        
        return payload
    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}")

def is_token_blacklisted(token_jti: str) -> bool:
    """
    Проверяет, находится ли токен в черном списке
    
    Args:
        token_jti: JTI (уникальный идентификатор) токена
        
    Returns:
        True если токен в черном списке, иначе False
    """
    return bool(redis_client.exists(f"blacklist:{token_jti}"))

def blacklist_token(token_jti: str, expires_at: datetime) -> None:
    """
    Добавляет токен в черный список
    
    Args:
        token_jti: JTI (уникальный идентификатор) токена
        expires_at: Дата и время истечения срока действия токена
    """
    # Вычисляем TTL для Redis (сколько секунд до истечения)
    ttl = int((expires_at - datetime.utcnow()).total_seconds())
    if ttl > 0:
        redis_client.setex(f"blacklist:{token_jti}", ttl, 1)

def refresh_tokens(refresh_token: str) -> Dict[str, str]:
    """
    Обновляет пару токенов (access и refresh) с использованием refresh токена
    
    Args:
        refresh_token: Действующий refresh токен
        
    Returns:
        Словарь с новыми токенами {'access_token': '...', 'refresh_token': '...'}
        
    Raises:
        JWTError: Если refresh токен недействителен
    """
    # Проверяем refresh токен
    payload = verify_token(refresh_token, token_type="refresh")
    
    # Извлекаем данные пользователя
    user_id = payload.get("sub")
    username = payload.get("username")
    
    if not user_id:
        raise JWTError("Invalid refresh token: user ID missing")
    
    # Добавляем старый refresh токен в черный список
    blacklist_token(payload.get("jti", ""), 
                   datetime.fromtimestamp(payload.get("exp", 0)))
    
    # Создаем новые токены
    token_data = {"sub": user_id}
    if username:
        token_data["username"] = username
    
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }

def decode_token(token: str) -> Dict[str, Any]:
    """
    Декодирование и проверка JWT токена
    
    Args:
        token: JWT токен для декодирования и проверки
        
    Returns:
        Декодированные данные из токена
        
    Raises:
        JWTError: Если токен недействителен или истек срок его действия
    """
    try:
        # Декодируем токен
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Проверяем, не истек ли срок действия токена
        if 'exp' in payload and datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
            raise JWTError("Token has expired")
            
        # Проверяем, не находится ли токен в черном списке
        token_jti = payload.get('jti', '')
        if is_token_blacklisted(token_jti):
            raise JWTError("Token has been revoked")
        
        return payload
    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}") 