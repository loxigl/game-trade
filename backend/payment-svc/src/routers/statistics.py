"""
Роутер для статистики по продажам и транзакциям
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User
from ..schemas.base import SuccessResponse
from ..schemas.statistics import SellerStatisticsResponse, TransactionSummaryResponse, PopularGame
from ..services.statistics_service import get_statistics_service

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.get("/seller", response_model=SuccessResponse[SellerStatisticsResponse])
async def get_seller_statistics(
    seller_id: Optional[int] = Query(None, description="ID продавца"),
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение статистики продаж для продавца
    """
    # Проверка прав доступа - пользователь должен запрашивать только свою статистику
    if seller_id and seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: вы можете просматривать только свою статистику продаж"
        )
    
    # Если ID продавца не указан, используем ID текущего пользователя
    if not seller_id:
        seller_id = current_user.id
    
    # Валидация периода
    if period not in ["week", "month", "quarter", "year", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый период. Допустимые значения: week, month, quarter, year, all"
        )
    
    # Получаем статистику через сервис
    statistics_service = get_statistics_service(db)
    
    try:
        result = await statistics_service.get_seller_statistics(
            seller_id=seller_id,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        
        return SuccessResponse(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики продаж: {str(e)}"
        )


@router.get("/transactions/summary", response_model=SuccessResponse[List[TransactionSummaryResponse]])
async def get_transaction_summary(
    seller_id: Optional[int] = Query(None, description="ID продавца"),
    group_by: str = Query("month", description="Параметр группировки (month, game, status, type)"),
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение сводки по транзакциям продавца с группировкой
    """
    # Проверка прав доступа - пользователь должен запрашивать только свою статистику
    if seller_id and seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: вы можете просматривать только свою сводку по транзакциям"
        )
    
    # Если ID продавца не указан, используем ID текущего пользователя
    if not seller_id:
        seller_id = current_user.id
    
    # Валидация параметров
    if group_by not in ["month", "game", "status", "type"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый параметр группировки. Допустимые значения: month, game, status, type"
        )
    
    if period not in ["week", "month", "quarter", "year", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый период. Допустимые значения: week, month, quarter, year, all"
        )
    
    # Получаем сводку через сервис
    statistics_service = get_statistics_service(db)
    
    try:
        result = await statistics_service.get_transaction_summary(
            seller_id=seller_id,
            group_by=group_by,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        
        return SuccessResponse(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении сводки по транзакциям: {str(e)}"
        )


@router.get("/popular-games", response_model=SuccessResponse[List[PopularGame]])
async def get_popular_games(
    limit: int = Query(10, description="Количество игр в результатах", ge=1, le=100),
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    db: Session = Depends(get_db)
):
    """
    Получение списка популярных игр на основе статистики продаж
    """
    # Валидация периода
    if period not in ["week", "month", "quarter", "year", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый период. Допустимые значения: week, month, quarter, year, all"
        )
    
    # Получаем статистику через сервис
    statistics_service = get_statistics_service(db)
    
    try:
        result = await statistics_service.get_popular_games(
            period=period,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        return SuccessResponse(
            data=result,
            meta={
                "period": period,
                "limit": limit,
                "total": len(result)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении популярных игр: {str(e)}"
        ) 