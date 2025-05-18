from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExampleBase(BaseModel):
    """Базовая схема для примера"""
    title: str = Field(..., min_length=1, max_length=100, description="Название примера")
    description: Optional[str] = Field(None, max_length=1000, description="Описание примера")


class ExampleCreate(ExampleBase):
    """Схема для создания примера"""
    # Можно добавить дополнительные поля, которые нужны только при создании
    status: str = Field("active", description="Статус примера")


class ExampleUpdate(BaseModel):
    """Схема для обновления примера"""
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="Название примера")
    description: Optional[str] = Field(None, max_length=1000, description="Описание примера")
    status: Optional[str] = Field(None, description="Статус примера")


class ExampleResponse(ExampleBase):
    """Схема для ответа с примером"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Позволяет конвертировать ORM модели в схемы 