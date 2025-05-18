from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

# Базовая схема пользователя
class UserBase(BaseModel):
    """Базовая схема пользователя, содержащая общие поля"""
    username: str = Field(..., min_length=3, max_length=50, example="johndoe")
    email: EmailStr = Field(..., example="john.doe@example.com")

# Схема для создания пользователя
class UserCreate(UserBase):
    """Схема для создания нового пользователя"""
    password: str = Field(..., min_length=8, max_length=100, example="SecureP@ssw0rd")

# Схема для обновления пользователя
class UserUpdate(BaseModel):
    """Схема для обновления данных существующего пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, example="johndoe2")
    email: Optional[EmailStr] = Field(None, example="john.new@example.com")
    password: Optional[str] = Field(None, min_length=8, max_length=100, example="NewSecureP@ssw0rd")

# Схема для ответа по пользователю
class UserResponse(UserBase):
    """Схема для предоставления информации о пользователе в API"""
    id: int = Field(..., example=123)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 42,
                "username": "johndoe",
                "email": "john.doe@example.com",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }

# Схема профиля пользователя
class ProfileBase(BaseModel):
    """Базовая схема профиля пользователя"""
    avatar_url: Optional[str] = Field(None, example="https://example.com/avatar.jpg")
    bio: Optional[str] = Field(None, max_length=500, example="Enthusiastic gamer with a passion for rare items.")

class ProfileCreate(ProfileBase):
    """Схема для создания профиля пользователя"""
    user_id: int = Field(..., example=42)

class ProfileUpdate(ProfileBase):
    """Схема для обновления профиля пользователя"""
    pass

class ProfileResponse(ProfileBase):
    """Схема для предоставления информации о профиле пользователя"""
    id: int = Field(..., example=42)
    user_id: int = Field(..., example=42)
    reputation_score: float = Field(..., example=4.8)
    is_verified_seller: bool = Field(..., example=True)
    total_sales: int = Field(..., example=23)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 42,
                "user_id": 42,
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "Enthusiastic gamer with a passion for rare items.",
                "reputation_score": 4.8,
                "is_verified_seller": True,
                "total_sales": 23,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        } 