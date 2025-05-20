from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from uuid import UUID
from ..models.transaction import TransactionStatus, TransactionType
from .transaction_history import TransactionHistoryResponse

class TransactionBase(BaseModel):
    """Базовая схема для транзакций"""
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    currency: str = Field(default="USD", description="Валюта транзакции")
    fee_amount: Optional[float] = Field(default=0.0, ge=0, description="Сумма комиссии")
    fee_percentage: Optional[float] = Field(default=0.0, ge=0, le=100, description="Процент комиссии")
    type: TransactionType = Field(default=TransactionType.PURCHASE, description="Тип транзакции")
    description: Optional[str] = Field(default=None, description="Описание транзакции")
    notes: Optional[str] = Field(default=None, description="Дополнительные заметки")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные")
    external_reference: Optional[str] = Field(default=None, description="Внешний идентификатор")

class TransactionCreate(TransactionBase):
    """Схема для создания транзакции"""
    buyer_id: Optional[int] = Field(default=None, description="ID покупателя")
    seller_id: Optional[int] = Field(default=None, description="ID продавца")
    listing_id: Optional[int] = Field(default=None, description="ID объявления")
    item_id: Optional[int] = Field(default=None, description="ID товара")
    wallet_id: Optional[int] = Field(default=None, description="ID кошелька")
    parent_transaction_id: Optional[int] = Field(default=None, description="ID родительской транзакции")
    expiration_date: Optional[datetime] = Field(default=None, description="Дата истечения срока транзакции")
    days_to_complete: Optional[int] = Field(default=3, description="Количество дней на завершение транзакции")

    @validator('buyer_id', 'seller_id')
    def validate_users(cls, v, values):
        """Проверка наличия хотя бы одного пользователя для транзакции"""
        if 'type' in values and values['type'] == TransactionType.PURCHASE:
            if not v and 'buyer_id' not in values and 'seller_id' not in values:
                raise ValueError("Transaction must have at least one user (buyer or seller)")
        return v

class TransactionUpdate(BaseModel):
    """Схема для обновления транзакции"""
    status: Optional[TransactionStatus] = Field(default=None, description="Статус транзакции")
    notes: Optional[str] = Field(default=None, description="Дополнительные заметки")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные")
    external_reference: Optional[str] = Field(default=None, description="Внешний идентификатор")

class TransactionStatusUpdate(BaseModel):
    """Схема для обновления статуса транзакции"""
    reason: Optional[str] = Field(default=None, description="Причина изменения статуса")
    
class TransactionDisputeCreate(BaseModel):
    """Схема для создания спора"""
    reason: str = Field(..., description="Причина спора")
    
class TransactionActionResponse(BaseModel):
    """Схема для ответа с доступными действиями для транзакции"""
    actions: List[str] = Field(..., description="Список доступных действий")

class TransactionResponse(TransactionBase):
    """Схема для ответа с транзакцией"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_uid: str
    buyer_id: Optional[int] = None
    seller_id: Optional[int] = None
    listing_id: Optional[int] = None
    item_id: Optional[int] = None
    status: TransactionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    escrow_held_at: Optional[datetime] = None
    disputed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    dispute_reason: Optional[str] = None
    refund_reason: Optional[str] = None
    cancel_reason: Optional[str] = None
    wallet_id: Optional[int] = None
    parent_transaction_id: Optional[int] = None

class TransactionListResponse(BaseModel):
    """Схема для списка транзакций с пагинацией"""
    total: int
    items: List[TransactionResponse]
    page: int
    size: int
    pages: int 

class TransactionDetailsResponse(BaseModel):
    """Схема для детального ответа с полной информацией о транзакции"""
    transaction: Dict[str, Any] = Field(..., description="Основная информация о транзакции")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="История изменений статуса")
    sale: Optional[Dict[str, Any]] = Field(default=None, description="Информация о связанной продаже")
    buyer: Optional[Dict[str, Any]] = Field(default=None, description="Информация о покупателе")
    seller: Optional[Dict[str, Any]] = Field(default=None, description="Информация о продавце")
    item: Optional[Dict[str, Any]] = Field(default=None, description="Информация о товаре или услуге")
    escrow_info: Dict[str, Any] = Field(..., description="Информация об эскроу")
    time_info: Dict[str, Any] = Field(..., description="Временная информация о транзакции")
    available_actions: List[str] = Field(default_factory=list, description="Доступные действия с транзакцией")
    action_status: Dict[str, bool] = Field(default_factory=dict, description="Статус доступности каждого действия")
    payment_info: Dict[str, Any] = Field(default_factory=dict, description="Детальная информация о платеже")
    user_role: Optional[str] = Field(default=None, description="Роль текущего пользователя (buyer/seller/admin)")
    
    model_config = ConfigDict(from_attributes=True) 