"""
Схемы для API продаж
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from ..models.core import SaleStatus

class SaleBase(BaseModel):
    """Базовая схема продажи"""
    listing_id: int
    price: float
    currency: str = "USD"
    description: Optional[str] = None

class SaleCreate(SaleBase):
    """Схема для создания продажи"""
    wallet_id: Optional[int] = None

class SaleStatusUpdate(BaseModel):
    """Схема для обновления статуса продажи"""
    status: SaleStatus
    reason: Optional[str] = None

class SaleResponse(SaleBase):
    """Схема для ответа с информацией о продаже"""
    id: int
    buyer_id: int
    buyer_name: Optional[str]
    seller_id: int
    seller_name: Optional[str]
    item_id: int
    status: SaleStatus
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    chat_id: Optional[int]
    transaction_id: Optional[int]
    listing_title: Optional[str]
    extra_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class SaleListResponse(BaseModel):
    """Схема для ответа со списком продаж"""
    items: List[SaleResponse]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True 