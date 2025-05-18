"""
Middleware для JWT аутентификации
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
from .jwt import verify_token
from ..database.connection import get_db
from ..models.user import User

# Создаем схему OAuth2 для получения токенов из запросов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    Возвращает текущего аутентифицированного пользователя на основе JWT токена
    
    Args:
        token: JWT токен из запроса
        db: Сессия базы данных
        
    Returns:
        Объект пользователя
        
    Raises:
        HTTPException: Если токен недействителен или пользователь не найден
    """
    try:
        # Проверяем токен
        payload = verify_token(token)
        
        # Получаем ID пользователя из токена
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Недействительный токен аутентификации",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Проверяем тип токена (должен быть access)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Требуется токен доступа",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Недействительный токен аутентификации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Получаем пользователя из базы данных
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден"
        )
    
    # Проверяем активность аккаунта
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Аккаунт деактивирован"
        )
    
    # Проверяем блокировку аккаунта
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=403,
            detail=f"Аккаунт заблокирован до {user.account_locked_until}"
        )
    
    return user

async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Пытается получить текущего пользователя, но не вызывает исключение,
    если токен отсутствует или недействителен
    
    Args:
        request: HTTP запрос
        db: Сессия базы данных
        
    Returns:
        Объект пользователя или None
    """
    # Извлекаем токен из заголовка Authorization
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    
    try:
        # Получаем токен из строки "Bearer {token}"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        # Проверяем токен
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Получаем пользователя из базы данных
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        
        return user
    except (JWTError, ValueError):
        return None

async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверяет, является ли текущий пользователь активным администратором
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        Объект пользователя, если он администратор
        
    Raises:
        HTTPException: Если пользователь не имеет прав администратора
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для выполнения операции"
        )
    return current_user

def has_role(required_role: str):
    """
    Создает зависимость для проверки наличия определенной роли у пользователя
    
    Args:
        required_role: Требуемая роль
        
    Returns:
        Функция-зависимость для FastAPI
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Проверяет наличие требуемой роли у пользователя
        
        Args:
            current_user: Текущий пользователь
            
        Returns:
            Объект пользователя, если у него есть требуемая роль
            
        Raises:
            HTTPException: Если у пользователя нет требуемой роли
        """
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Для выполнения операции требуется роль: {required_role}"
            )
        return current_user
    
    return role_checker 