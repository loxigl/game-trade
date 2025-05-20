from fastapi import APIRouter
from .transaction import router as transaction_router
from .transaction_history import router as transaction_history_router
from .statistics import router as statistics_router
from .sales import router as sales_router
from .wallets import router as wallets_router
from .currency import router as currency_router

router = APIRouter()

__all__ = ["transaction_router", "sales_router", "wallets_router", "transaction_history_router", "statistics_router", "currency_router"] 