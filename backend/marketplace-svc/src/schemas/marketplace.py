from typing import Optional, List, Any, Dict, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from ..models.core import ListingStatus, TransactionStatus, ImageType, ImageStatus

from .user import UserResponse
from .categorization import ItemTemplateResponse, CategoryAttributeResponse, ItemAttributeValueResponse, TemplateAttributeValueResponse, ItemAttributeValueCreate


# === Image schemas ===
class ImageBase(BaseModel):
    """Базовая схема изображения"""
    entity_id: Optional[int] = None
    type: ImageType

    class Config:
        from_attributes = True


class ImageCreate(ImageBase):
    """Схема для создания изображения"""
    pass


class ImageUpdate(BaseModel):
    """Схема для обновления изображения"""
    is_main: Optional[bool] = None
    order_index: Optional[int] = None

    class Config:
        from_attributes = True


class ImageResponse(ImageBase):
    """Схема для ответа с изображением"""
    id: int
    owner_id: int
    filename: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    is_main: bool
    order_index: int
    status: ImageStatus
    created_at: datetime
    updated_at: datetime

    # Дополнительно добавляем поля с прямыми URL
    url: Optional[str] = None

    @validator('url', always=True)
    def set_url(cls, v, values):
        """Генерируем URL для доступа к изображению через API"""
        if 'id' not in values:
            return None
        return f"/api/marketplace/images/{values['id']}/file"

    class Config:
        from_attributes = True


# === Listing schemas ===
class ListingBase(BaseModel):
    """Базовая схема объявления"""
    item_template_id: int
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    is_negotiable: bool = False

    class Config:
        from_attributes = True


class ListingCreate(ListingBase):
    """Схема для создания объявления"""
    item_id: Optional[int] = None
    category_id: Optional[int] = None
    attribute_values: Optional[List[Dict[str, Any]]] = None


class ListingUpdate(BaseModel):
    """Схема для обновления объявления"""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_negotiable: Optional[bool] = None

    class Config:
        from_attributes = True


class ListingResponse(ListingBase):
    """Схема для ответа с объявлением"""
    id: int
    seller_id: int
    item_id: Optional[int] = None
    status: ListingStatus
    views_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    seller: Optional[UserResponse] = None
    images: Optional[List[ImageResponse]] = []

    class Config:
        from_attributes = True


class ListingDetailResponse(ListingResponse):
    """Расширенная схема для детального представления объявления"""
    item_template: Optional[ItemTemplateResponse] = None
    item_attributes: Optional[List[ItemAttributeValueResponse]] = []
    template_attributes: Optional[List[TemplateAttributeValueResponse]] = []
    all_attributes: Optional[List[Dict[str, Any]]] = []
    similar_listings: Optional[List[ListingResponse]] = []
    seller_rating: Optional[float] = None

    @validator('all_attributes', always=True)
    def combine_attributes(cls, v, values):
        """Объединяет атрибуты категории и шаблона в один список"""
        combined_attrs = []
        
        # Добавляем атрибуты предмета
        if 'item_attributes' in values and values['item_attributes']:
            for attr in values['item_attributes']:
                item_attr = attr.dict()
                combined_attrs.append(item_attr)
        
        # Добавляем атрибуты шаблона
        if 'template_attributes' in values and values['template_attributes']:
            for attr in values['template_attributes']:
                template_attr = attr.dict()
                template_attr['is_template_attr'] = True
                combined_attrs.append(template_attr)
        
        return combined_attrs
    
    class Config:
        from_attributes = True


# === Transaction schemas ===
class TransactionBase(BaseModel):
    """Базовая схема транзакции"""
    listing_id: int
    price: float
    currency: str = "USD"

    class Config:
        from_attributes = True


class TransactionCreate(TransactionBase):
    """Схема для создания транзакции"""
    pass


class TransactionUpdate(BaseModel):
    """Схема для обновления транзакции"""
    status: Optional[TransactionStatus] = None

    class Config:
        from_attributes = True


class TransactionResponse(TransactionBase):
    """Схема для ответа с транзакцией"""
    id: int
    buyer_id: int
    seller_id: int
    fee: float
    status: TransactionStatus
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    buyer: Optional[UserResponse] = None
    seller: Optional[UserResponse] = None
    listing: Optional[ListingResponse] = None

    class Config:
        from_attributes = True
