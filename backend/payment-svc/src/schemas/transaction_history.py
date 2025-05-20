from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..models.transaction import TransactionStatus

class TransactionHistoryBase(BaseModel):
    """Базовая схема для истории транзакций"""
    transaction_id: int
    previous_status: Optional[TransactionStatus] = None
    new_status: TransactionStatus
    initiator_id: Optional[int] = None
    initiator_type: Optional[str] = None
    reason: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class TransactionHistoryCreate(TransactionHistoryBase):
    """Схема для создания записи в истории транзакций"""
    pass

class TransactionHistoryResponse(TransactionHistoryBase):
    """Схема для ответа с данными истории транзакций"""
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TransactionHistoryListResponse(BaseModel):
    """Схема для списка записей истории транзакций с пагинацией"""
    items: List[TransactionHistoryResponse]
    total: int
    page: int
    size: int
    pages: int 