from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Схемы для ожидающих подтверждения продаж
class GameInfo(BaseModel):
    """Информация об игре для продажи"""
    id: int
    name: str
    image: Optional[str] = None

class PendingSaleResponse(BaseModel):
    """Схема ответа для одной ожидающей подтверждения продажи"""
    id: int
    listingId: int
    listingTitle: str
    buyerId: int
    buyerName: str
    price: float
    currency: str
    status: str = Field(..., description="Статус продажи: pending, payment_processing, delivery_pending, completed, canceled, disputed")
    createdAt: str
    expiresAt: Optional[str] = None
    gameInfo: Optional[GameInfo] = None

    model_config = ConfigDict(from_attributes=True)

class PendingSaleListResponse(BaseModel):
    """Схема ответа для списка ожидающих подтверждения продаж с пагинацией"""
    items: List[PendingSaleResponse]
    total: int
    page: int
    size: int
    pages: int

# Схемы для статистики продавца
class MonthlySale(BaseModel):
    """Ежемесячные продажи"""
    month: str
    sales: int
    revenue: float

class GameDistribution(BaseModel):
    """Распределение продаж по играм"""
    game: str
    sales: int
    percentage: float

class SellerStatisticsResponse(BaseModel):
    """Статистика продавца"""
    totalSales: int
    totalRevenue: float
    averagePrice: float
    popularGame: str
    completionRate: float
    returnRate: float
    pendingTransactions: int
    monthlySales: List[MonthlySale]
    gameDistribution: List[GameDistribution]

    model_config = ConfigDict(from_attributes=True)

class TransactionSummaryResponse(BaseModel):
    """Сводка по транзакциям"""
    key: str
    count: int
    amount: float
    percentage: float

    model_config = ConfigDict(from_attributes=True) 