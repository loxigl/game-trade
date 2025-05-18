"""
Схемы для работы с токенами аутентификации
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class TokenResponse(BaseModel):
    """
    Ответ с токенами доступа и обновления
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    """
    Запрос на обновление токена
    """
    refresh_token: str = Field(..., description="Refresh токен для обновления")

class LoginRequest(BaseModel):
    """
    Запрос на аутентификацию пользователя
    """
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль пользователя")
    remember_me: Optional[bool] = Field(False, description="Флаг запоминания пользователя")

class TokenPayload(BaseModel):
    """
    Полезная нагрузка JWT токена
    """
    sub: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = []
    exp: Optional[int] = None
    jti: Optional[str] = None
    type: Optional[str] = None

class TokenBlacklistRequest(BaseModel):
    """
    Запрос на добавление токена в черный список
    """
    token: str = Field(..., description="JWT токен для добавления в черный список") 