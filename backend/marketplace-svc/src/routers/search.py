"""
Роутер для поиска и фильтрации предметов на маркетплейсе
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Body, Path
from sqlalchemy.orm import Session

from ..dependencies.db import get_db
from ..services.search_service import SearchService
from ..schemas.marketplace import ListingResponse
from ..schemas.categorization import ItemTemplateResponse
from ..schemas.search import (
    SearchParams, FilterParams, FilterOptions,
    TrendingCategory
)
from ..schemas.base import PaginationParams, SuccessResponse

router = APIRouter(
    prefix="/search",
    tags=["search"],
    responses={
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.post("/listings", response_model=SuccessResponse[List[ListingResponse]])
async def search_listings(
    search_params: SearchParams,
    filter_params: Optional[FilterParams] = None,
    pagination: PaginationParams = Depends(),
    sort_by: str = Query("created_at", description="Поле для сортировки (price, views, name, created_at)"),
    sort_order: str = Query("desc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Поиск объявлений по различным критериям с фильтрацией и пагинацией
    """
    search_service = SearchService(db)
    result = search_service.search_listings(
        pagination=pagination,
        search_params=search_params,
        filter_params=filter_params,
        sort_by=sort_by,
        sort_order=sort_order
    )
    print([ListingResponse.from_orm(item) for item in result["items"]])

    return SuccessResponse(
        data=[ListingResponse.from_orm(item) for item in result["items"]],
        meta=result["meta"]
    )


@router.get("/filter-options", response_model=SuccessResponse[FilterOptions])
async def get_filter_options(
    game_id: Optional[int] = Query(None, description="ID игры для фильтрации категорий"),
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации атрибутов"),
    db: Session = Depends(get_db)
):
    """
    Получение доступных опций фильтрации для UI
    """
    search_service = SearchService(db)
    filter_options = search_service.get_filter_options(
        game_id=game_id,
        category_id=category_id
    )

    return SuccessResponse(data=filter_options)


@router.get("/popular", response_model=SuccessResponse[List[ListingResponse]])
async def get_popular_items(
    limit: int = Query(10, description="Максимальное количество результатов", ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Получение списка популярных товаров (по количеству просмотров)
    """
    search_service = SearchService(db)
    popular_items = search_service.get_popular_items(limit=limit)

    return SuccessResponse(data=popular_items)


@router.get("/trending-categories", response_model=SuccessResponse[List[TrendingCategory]])
async def get_trending_categories(
    limit: int = Query(5, description="Максимальное количество результатов", ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Получение списка популярных категорий (по количеству активных объявлений)
    """
    search_service = SearchService(db)
    trending_categories = search_service.get_trending_categories(limit=limit)

    return SuccessResponse(data=trending_categories)


@router.get("/templates", response_model=SuccessResponse[List[ItemTemplateResponse]])
async def search_templates(
    pagination: PaginationParams = Depends(),
    query: Optional[str] = Query(None, description="Текст для поиска шаблонов"), 
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    game_id: Optional[int] = Query(None, description="ID игры для фильтрации"),
    sort_by: str = Query("name", description="Поле для сортировки (name, created_at, id)"),
    sort_order: str = Query("asc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Поиск шаблонов предметов по тексту, категории или игре.
    Используется для выбора шаблона при создании объявления.
    """
    search_service = SearchService(db)
    result = search_service.search_templates(
        pagination=pagination,
        query=query,
        category_id=category_id,
        game_id=game_id,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )
