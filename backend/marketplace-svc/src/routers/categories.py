"""
Роутер для управления категориями предметов
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User
from ..services.category_service import CategoryService
from ..services.template_service import TemplateService
from ..schemas.categorization import (
    ItemCategoryCreate, ItemCategoryUpdate, ItemCategoryResponse,
    CategoryAttributeCreate, CategoryAttributeUpdate, CategoryAttributeResponse,
    ItemTemplateResponse
)
from ..schemas.base import PaginationParams, SuccessResponse

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.get("", response_model=SuccessResponse[List[ItemCategoryResponse]])
async def get_categories(
    pagination: PaginationParams = Depends(),
    game_id: Optional[int] = Query(None, description="Фильтр по ID игры"),
    parent_id: Optional[int] = Query(None, description="Фильтр по ID родительской категории"),
    category_type: Optional[str] = Query(None, description="Фильтр по типу категории (main/sub)"),
    search_query: Optional[str] = Query(None, description="Поисковый запрос по названию или описанию"),
    sort_by: str = Query("name", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получение списка категорий с возможностью фильтрации и пагинации
    """
    category_service = CategoryService(db)
    result = category_service.get_categories(
        pagination=pagination,
        game_id=game_id,
        parent_id=parent_id,
        category_type=category_type,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )


@router.get("/hierarchy", response_model=SuccessResponse[List[dict]])
async def get_category_hierarchy(
    game_id: Optional[int] = Query(None, description="Фильтр по ID игры"),
    db: Session = Depends(get_db)
):
    """
    Получение иерархии категорий в древовидной структуре.
    Возвращает категории с вложенными подкатегориями.
    """
    category_service = CategoryService(db)
    hierarchy = category_service.get_category_hierarchy(game_id=game_id)
    
    return SuccessResponse(
        data=hierarchy,
        meta={"description": "Иерархия категорий"}
    )


@router.get("/{category_id}", response_model=SuccessResponse[ItemCategoryResponse])
async def get_category(
    category_id: int = Path(..., description="ID категории"),
    db: Session = Depends(get_db)
):
    """
    Получение информации о конкретной категории по её ID
    """
    category_service = CategoryService(db)
    category = category_service.get_category_by_id(category_id)
    
    return SuccessResponse(data=category)


@router.post("", response_model=SuccessResponse[ItemCategoryResponse], status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: ItemCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создание новой категории.
    
    Можно указать parent_id для создания подкатегории.
    """
    category_service = CategoryService(db)
    category = category_service.create_category(category_data)
    
    return SuccessResponse(
        data=category,
        meta={"message": "Категория успешно создана"}
    )


@router.put("/{category_id}", response_model=SuccessResponse[ItemCategoryResponse])
async def update_category(
    category_data: ItemCategoryUpdate,
    category_id: int = Path(..., description="ID категории"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление информации о категории.
    
    Можно изменить родительскую категорию с помощью поля parent_id.
    """
    category_service = CategoryService(db)
    category = category_service.update_category(category_id, category_data)
    
    return SuccessResponse(
        data=category,
        meta={"message": "Категория успешно обновлена"}
    )


@router.delete("/{category_id}", response_model=SuccessResponse)
async def delete_category(
    category_id: int = Path(..., description="ID категории"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление категории.
    
    Категорию можно удалить только если у нее нет подкатегорий и шаблонов предметов.
    """
    category_service = CategoryService(db)
    category_service.delete_category(category_id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Категория успешно удалена"}
    )


# Работа с атрибутами категорий

@router.get("/{category_id}/attributes", response_model=SuccessResponse[List[CategoryAttributeResponse]])
async def get_category_attributes(
    category_id: int = Path(..., description="ID категории"),
    db: Session = Depends(get_db)
):
    """
    Получение списка атрибутов для конкретной категории
    """
    category_service = CategoryService(db)
    attributes = category_service.get_category_attributes(category_id)
    
    return SuccessResponse(data=attributes)


@router.post("/{category_id}/attributes", response_model=SuccessResponse[CategoryAttributeResponse], status_code=status.HTTP_201_CREATED)
async def create_category_attribute(
    attribute_data: CategoryAttributeCreate,
    category_id: int = Path(..., description="ID категории"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Добавление нового атрибута к категории
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    # Обеспечиваем, что атрибут создается для указанной категории
    attribute_data.category_id = category_id
    
    category_service = CategoryService(db)
    attribute = category_service.create_attribute(attribute_data)
    
    return SuccessResponse(
        data=attribute,
        meta={"message": "Атрибут успешно добавлен к категории"}
    )


@router.put("/{category_id}/attributes/{attribute_id}", response_model=SuccessResponse[CategoryAttributeResponse])
async def update_category_attribute(
    attribute_data: CategoryAttributeUpdate,
    category_id: int = Path(..., description="ID категории"),
    attribute_id: int = Path(..., description="ID атрибута"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление атрибута категории
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    category_service = CategoryService(db)
    
    # Проверяем, что атрибут принадлежит указанной категории
    attribute = category_service.get_attribute_by_id(attribute_id)
    if attribute.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Атрибут не принадлежит указанной категории"
        )
    
    updated_attribute = category_service.update_attribute(attribute_id, attribute_data)
    
    return SuccessResponse(
        data=updated_attribute,
        meta={"message": "Атрибут успешно обновлен"}
    )


@router.delete("/{category_id}/attributes/{attribute_id}", response_model=SuccessResponse)
async def delete_category_attribute(
    category_id: int = Path(..., description="ID категории"),
    attribute_id: int = Path(..., description="ID атрибута"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление атрибута категории
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    category_service = CategoryService(db)
    
    # Проверяем, что атрибут принадлежит указанной категории
    attribute = category_service.get_attribute_by_id(attribute_id)
    if attribute.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Атрибут не принадлежит указанной категории"
        )
    
    category_service.delete_attribute(attribute_id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Атрибут успешно удален"}
    )


# Получение шаблонов для категории
@router.get("/{category_id}/templates", response_model=SuccessResponse[List[ItemTemplateResponse]])
async def get_category_templates(
    category_id: int = Path(..., description="ID категории"),
    pagination: PaginationParams = Depends(),
    search_query: Optional[str] = Query(None, description="Поисковый запрос по названию или описанию"),
    sort_by: str = Query("name", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получение шаблонов предметов для указанной категории с возможностью поиска и пагинации
    """
    template_service = TemplateService(db)
    result = template_service.get_templates_by_category(
        category_id=category_id,
        pagination=pagination,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    ) 