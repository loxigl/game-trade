from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database.connection import get_db
from ..models.core import Listing, Sale, Transaction, User, ListingStatus, SaleStatus, TransactionStatus
from ..models.categorization import Game, ItemTemplate, ItemCategory, Item
from ..dependencies.auth import get_current_active_user, get_current_user
from ..schemas.marketplace import ListingResponse
from ..schemas.base import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"]
)

@router.get("/listings/by-ids", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_listings_by_ids(
    listing_ids: List[int] = Query(..., description="Список ID объявлений"),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о нескольких объявлениях для статистики.
    Используется payment-svc для сбора данных о продажах.
    """
    results = []
    
    for listing_id in listing_ids:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            continue
            
        # Получаем информацию об игре
        game_name = "Неизвестно"
        if listing.item_template and listing.item_template.category and listing.item_template.category.game:
            game_name = listing.item_template.category.game.name
        
        results.append({
            "id": listing.id,
            "title": listing.title,
            "price": float(listing.price),
            "game_name": game_name,
            "seller_id": listing.seller_id,
            "created_at": listing.created_at.isoformat() if listing.created_at else None,
            "status": listing.status
        })
    
    return SuccessResponse(
        data=results,
        meta={"total": len(results)}
    )

@router.get("/game-sales", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_game_sales_statistics(
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    db: Session = Depends(get_db)
):
    """
    Получить статистику продаж по играм.
    Используется payment-svc для анализа продаж по играм.
    """
    # Определяем временной диапазон
    if not end_date:
        end_date = datetime.now()
        
    if not start_date:
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = end_date - timedelta(days=365 * 2)  # за 2 года
    
    # Подзапрос для получения информации о категории и игре
    game_sales = db.query(
        Game.id.label('game_id'),
        Game.name.label('game_name'),
        func.count(Sale.id).label('sales_count'),
        func.sum(Sale.price).label('total_revenue')
    ).join(
        ItemCategory, ItemCategory.game_id == Game.id
    ).join(
        ItemTemplate, ItemTemplate.category_id == ItemCategory.id
    ).join(
        Listing, Listing.item_template_id == ItemTemplate.id
    ).join(
        Sale, Sale.listing_id == Listing.id
    ).filter(
        Sale.created_at.between(start_date, end_date),
        Sale.status.in_([SaleStatus.COMPLETED.value, SaleStatus.DELIVERY_PENDING.value])
    ).group_by(
        Game.id, Game.name
    ).order_by(
        desc('sales_count')
    ).all()
    
    results = []
    total_sales = sum(sales_count for _, _, sales_count, _ in game_sales) if game_sales else 0
    
    for game_id, game_name, sales_count, total_revenue in game_sales:
        percentage = round((sales_count / total_sales) * 100, 1) if total_sales > 0 else 0
        
        results.append({
            "game": game_name,
            "sales": int(sales_count),
            "percentage": percentage,
            "revenue": float(total_revenue) if total_revenue else 0.0
        })
    
    # Если нет данных, добавляем пустые значения
    if not results:
        results = [{
            "game": "Нет данных",
            "sales": 0,
            "percentage": 100.0,
            "revenue": 0.0
        }]
    
    return SuccessResponse(
        data=results,
        meta={
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_sales": total_sales
        }
    )

@router.get("/popular-games", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_popular_games(
    limit: int = Query(10, description="Количество игр в результате"),
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    db: Session = Depends(get_db)
):
    """
    Получить список популярных игр по количеству продаж.
    Используется payment-svc для определения популярных игр.
    """
    # Определяем временной диапазон
    if not end_date:
        end_date = datetime.now()
        
    if not start_date:
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = end_date - timedelta(days=365 * 2)  # за 2 года
    
    popular_games = db.query(
        Game.id.label('game_id'),
        Game.name.label('game_name'),
        Game.logo_url.label('logo_url'),
        func.count(Sale.id).label('sales_count')
    ).join(
        ItemCategory, ItemCategory.game_id == Game.id
    ).join(
        ItemTemplate, ItemTemplate.category_id == ItemCategory.id
    ).join(
        Listing, Listing.item_template_id == ItemTemplate.id
    ).join(
        Sale, Sale.listing_id == Listing.id
    ).filter(
        Sale.created_at.between(start_date, end_date),
        Sale.status.in_([SaleStatus.COMPLETED.value, SaleStatus.DELIVERY_PENDING.value])
    ).group_by(
        Game.id, Game.name, Game.logo_url
    ).order_by(
        desc('sales_count')
    ).limit(limit).all()
    
    results = []
    
    for game_id, game_name, logo_url, sales_count in popular_games:
        results.append({
            "id": game_id,
            "name": game_name,
            "logo_url": logo_url,
            "sales": int(sales_count)
        })
    
    # Если нет данных, возвращаем пустой список
    if not results:
        results = [{
            "id": 0,
            "name": "Нет данных",
            "logo_url": None,
            "sales": 0
        }]
    
    return SuccessResponse(
        data=results,
        meta={
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

@router.get("/game-statistics", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_game_statistics(
    db: Session = Depends(get_db),
    period: str = Query("month", description="Период статистики (week, month, quarter, year, all)"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата")
):
    """
    Получить общую статистику по играм.
    """
    # Определяем временной диапазон
    if not end_date:
        end_date = datetime.now()
        
    if not start_date:
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = end_date - timedelta(days=365 * 2)  # за 2 года
    
    # Получаем все активные игры
    games = db.query(Game).filter(Game.is_active == True).all()
    
    results_per_game = []
    for game in games:
        # Получаем количество продаж для этой игры
        sales_count = db.query(func.count(Sale.id)).join(
            Listing, Sale.listing_id == Listing.id
        ).join(
            ItemTemplate, Listing.item_template_id == ItemTemplate.id
        ).join(
            ItemCategory, ItemTemplate.category_id == ItemCategory.id
        ).filter(
            ItemCategory.game_id == game.id,
            Sale.created_at.between(start_date, end_date),
            Sale.status.in_([SaleStatus.COMPLETED.value, SaleStatus.DELIVERY_PENDING.value])
        ).scalar() or 0
        
        # Получаем общую сумму продаж
        total_revenue = db.query(func.sum(Sale.price)).join(
            Listing, Sale.listing_id == Listing.id
        ).join(
            ItemTemplate, Listing.item_template_id == ItemTemplate.id
        ).join(
            ItemCategory, ItemTemplate.category_id == ItemCategory.id
        ).filter(
            ItemCategory.game_id == game.id,
            Sale.created_at.between(start_date, end_date),
            Sale.status.in_([SaleStatus.COMPLETED.value, SaleStatus.DELIVERY_PENDING.value])
        ).scalar() or 0
        
        results_per_game.append({
            "game": game.name,
            "sales": int(sales_count),
            "revenue": float(total_revenue),
            "game_id": game.id,
            "logo_url": game.logo_url
        })
    
    # Сортируем по количеству продаж
    results_per_game.sort(key=lambda x: x["sales"], reverse=True)
    
    # Считаем общее количество продаж и процент для каждой игры
    total_sales = sum(game["sales"] for game in results_per_game)
    
    for game in results_per_game:
        game["percentage"] = round((game["sales"] / total_sales) * 100, 1) if total_sales > 0 else 0
    
    # Если нет данных, добавляем пустое значение
    if not results_per_game:
        results_per_game = [{
            "game": "Нет данных",
            "sales": 0,
            "revenue": 0.0,
            "percentage": 100.0,
            "game_id": 0,
            "logo_url": None
        }]
    
    return SuccessResponse(
        data=results_per_game,
        meta={
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_sales": total_sales
        }
    )

@router.get("/listing/{listing_id}", response_model=SuccessResponse[Dict[str, Any]])
async def get_listing_statistics(
    listing_id: int = Path(..., description="ID объявления"),
    db: Session = Depends(get_db)
):
    """
    Получить статистику по конкретному объявлению.
    Используется payment-svc для получения детальной информации об объявлении.
    """
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объявление с ID {listing_id} не найдено"
        )
    
    # Получаем информацию об игре и категории
    game_name = "Неизвестно"
    category_name = "Неизвестно"
    
    if listing.item_template and listing.item_template.category:
        category = listing.item_template.category
        category_name = category.name
        
        if category.game:
            game_name = category.game.name
    
    # Получаем количество завершенных продаж
    completed_sales = db.query(func.count(Sale.id)).filter(
        Sale.listing_id == listing_id,
        Sale.status.in_([SaleStatus.COMPLETED.value, SaleStatus.DELIVERY_PENDING.value])
    ).scalar() or 0
    
    # Получаем данные о просмотрах
    views_count = listing.views_count or 0
    
    result = {
        "id": listing.id,
        "title": listing.title,
        "price": float(listing.price),
        "currency": listing.currency,
        "game": game_name,
        "category": category_name,
        "seller_id": listing.seller_id,
        "status": listing.status,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
        "views_count": views_count,
        "completed_sales": completed_sales,
        "item_template_id": listing.item_template_id
    }
    
    return SuccessResponse(
        data=result,
        meta={"listing_id": listing_id}
    )