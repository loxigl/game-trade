"""
Модуль для аутентификации клиентов
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from jose import JWTError
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from .jwt import create_access_token, create_refresh_token, verify_token, blacklist_token
from .password import verify_password, hash_password as get_password_hash
from .roles import Role, get_permissions_for_roles, get_highest_role
from ..database.connection import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserResponse
from ..schemas.token import TokenResponse

# Функции для использования в других модулях
def get_client_permissions(roles: list) -> Dict[str, Any]:
    """
    Получает информацию о разрешениях пользователя по его ролям
    
    Args:
        roles: Список ролей пользователя
        
    Returns:
        Словарь с информацией о разрешениях
    """
    if not roles:
        return {
            "roles": [],
            "permissions": [],
            "is_admin": False,
            "is_moderator": False,
            "is_seller": False,
            "highest_role": None
        }
    
    # Получаем разрешения на основе ролей
    permissions = list(get_permissions_for_roles(roles))
    
    # Определяем высшую роль
    highest_role = get_highest_role(roles)
    
    # Проверяем специальные роли
    is_admin = Role.ADMIN in roles
    is_moderator = Role.MODERATOR in roles or is_admin
    is_seller = Role.SELLER in roles or is_admin
    
    return {
        "roles": roles,
        "permissions": permissions,
        "is_admin": is_admin,
        "is_moderator": is_moderator,
        "is_seller": is_seller,
        "highest_role": highest_role
    }

def get_ui_permissions(roles: list) -> Dict[str, bool]:
    """
    Получает информацию о разрешениях для UI на основе ролей пользователя
    
    Args:
        roles: Список ролей пользователя
        
    Returns:
        Словарь с информацией о разрешениях UI в формате {ключ: булево значение}
    """
    if not roles:
        return {}
    
    # Получаем общую информацию о разрешениях
    perms = get_client_permissions(roles)
    
    # Создаем словарь разрешений UI
    return {
        # Общие разрешения
        "canViewProfile": True,
        "canEditProfile": True,
        
        # Разрешения для продавцов
        "canCreateListings": perms["is_seller"],
        "canManageOwnListings": perms["is_seller"],
        "canViewOrders": perms["is_seller"] or perms["is_admin"],
        "canManageOrders": perms["is_seller"] or perms["is_admin"],
        
        # Разрешения для модераторов
        "canModerateListing": perms["is_moderator"],
        "canModerateReviews": perms["is_moderator"],
        "canModerateUsers": perms["is_moderator"],
        
        # Разрешения для админов
        "canManageUsers": perms["is_admin"],
        "canManageRoles": perms["is_admin"],
        "canViewStatistics": perms["is_admin"],
        "canEditSystem": perms["is_admin"],
        
        # Другие ключевые разрешения для UI
        "canAccessAdminPanel": perms["is_admin"] or perms["is_moderator"]
    }

class ClientAuth:
    """
    Класс для аутентификации клиентов
    """
    
    @staticmethod
    def register_user(user_data: UserCreate, db: Session) -> User:
        """
        Регистрирует нового пользователя
        
        Args:
            user_data: Данные нового пользователя
            db: Сессия базы данных
            
        Returns:
            Созданный пользователь
            
        Raises:
            HTTPException: Если email уже зарегистрирован
        """
        # Проверяем, существует ли пользователь с таким email
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже зарегистрирован"
            )
        
        # Хешируем пароль
        hashed_password = get_password_hash(user_data.password)
        
        # Создаем нового пользователя
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            roles=[Role.USER],  # По умолчанию обычный пользователь
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Сохраняем в базу данных
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
        """
        Аутентифицирует пользователя по email и паролю
        
        Args:
            email: Email пользователя
            password: Пароль пользователя
            db: Сессия базы данных
            
        Returns:
            Объект пользователя или None, если аутентификация не удалась
        """
        # Находим пользователя по email
        user = db.query(User).filter(User.email == email).first()
        
        # Проверяем существование пользователя и валидность пароля
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        # Проверяем активность аккаунта
        if not user.is_active:
            return None
        
        # Проверяем блокировку аккаунта
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            return None
        
        return user
    
    @staticmethod
    def create_login_tokens(user: User) -> TokenResponse:
        """
        Создает токены доступа и обновления для пользователя
        
        Args:
            user: Объект пользователя
            
        Returns:
            Токены доступа и обновления
        """
        # Данные для токена
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        }
        
        # Создаем токены
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    @staticmethod
    def refresh_user_tokens(refresh_token: str, db: Session) -> TokenResponse:
        """
        Обновляет токены пользователя с использованием refresh токена
        
        Args:
            refresh_token: Токен обновления
            db: Сессия базы данных
            
        Returns:
            Новые токены доступа и обновления
            
        Raises:
            HTTPException: Если токен обновления недействителен
        """
        try:
            # Проверяем refresh токен
            payload = verify_token(refresh_token, token_type="refresh")
            
            # Извлекаем ID пользователя
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Недействительный токен обновления"
                )
            
            # Находим пользователя
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Пользователь не найден или деактивирован"
                )
            
            # Добавляем старый refresh токен в черный список
            token_jti = payload.get("jti")
            if token_jti:
                exp = datetime.fromtimestamp(payload.get("exp", 0))
                blacklist_token(token_jti, exp)
            
            # Создаем новые токены
            return ClientAuth.create_login_tokens(user)
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен обновления",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    @staticmethod
    def logout_user(token_jti: str, expires_at: datetime) -> Dict[str, Any]:
        """
        Выход пользователя из системы (добавление токена в черный список)
        
        Args:
            token_jti: Уникальный идентификатор токена
            expires_at: Время истечения токена
            
        Returns:
            Сообщение об успешном выходе
        """
        # Добавляем текущий токен в черный список
        blacklist_token(token_jti, expires_at)
        
        return {"message": "Успешный выход из системы"}
    
    @staticmethod
    def get_user_permissions(user: User) -> Dict[str, Any]:
        """
        Получает информацию о разрешениях пользователя
        
        Args:
            user: Объект пользователя
            
        Returns:
            Словарь с информацией о разрешениях
        """
        if not user:
            return {
                "roles": [],
                "permissions": [],
                "is_admin": False,
                "is_moderator": False,
                "is_seller": False,
                "highest_role": None
            }
        
        return get_client_permissions(user.roles)
    
    @staticmethod
    def get_ui_permissions(user: User) -> Dict[str, bool]:
        """
        Получает информацию о разрешениях для UI на основе ролей пользователя
        
        Args:
            user: Объект пользователя
            
        Returns:
            Словарь с информацией о разрешениях UI в формате {ключ: булево значение}
        """
        if not user:
            return {}
        
        return get_ui_permissions(user.roles) 