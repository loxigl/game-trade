"""
Схемы для статистики продаж и транзакций
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class MonthlySale(BaseModel):
    """Продажи за месяц"""
    month: str
    sales: int
    revenue: float

    class Config:
        orm_mode = True

class GameDistribution(BaseModel):
    """Распределение продаж по играм"""
    game: str
    sales: int
    percentage: float

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

class TransactionSummaryResponse(BaseModel):
    """Сводка по транзакциям"""
    key: str
    count: int
    amount: float
    percentage: float

    class Config:
        orm_mode = True

class PopularGame(BaseModel):
    """Популярная игра"""
    id: int
    name: str
    logo_url: Optional[str] = None
    sales: int

    class Config:
        orm_mode = True 