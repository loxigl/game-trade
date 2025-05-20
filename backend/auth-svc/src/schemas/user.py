from pydantic import BaseModel, EmailStr, Field, model_validator, validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """Базовые поля пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        """Проверка сложности пароля"""
        # Простая валидация - минимум 8 символов, содержит цифру и букву
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        return v

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str
    
    @model_validator(mode='after')
    def check_username_or_email(cls, values):
        if not values.username and not values.email:
            raise ValueError('Должен быть указан либо email, либо username')
        return values

class UserResponse(UserBase):
    """Схема для ответа с данными пользователя"""
    id: int
    is_active: bool
    is_verified: bool
    is_admin: bool
    roles: List[str]  # Добавляем поле ролей
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    """Схема для обновления данных пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        """Проверка сложности пароля"""
        if v is None:  # Пропускаем валидацию, если пароль не указан
            return v
        
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isalpha() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        return v

class Token(BaseModel):
    """Схема для JWT токена"""
    access_token: str
    refresh_token: str  # Добавляем поле refresh_token
    token_type: str = "bearer"
    
class TokenData(BaseModel):
    """Схема для полезной нагрузки JWT токена"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    exp: Optional[datetime] = None

class TokenValidateRequest(BaseModel):
    """Схема для запроса валидации токена"""
    token: str
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }

class TokenValidateResponse(BaseModel):
    """Схема для ответа валидации токена"""
    is_valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    
    class Config:
        schema_extra = {
            "example": {
                "is_valid": True,
                "user_id": 1,
                "username": "testuser"
            }
        } 