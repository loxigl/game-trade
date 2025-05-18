"""
Роутер для управления шаблонами предметов
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User
from ..services.template_service import TemplateService
from ..schemas.categorization import (
    ItemTemplateCreate, ItemTemplateUpdate, ItemTemplateResponse,
    TemplateAttributeCreate, TemplateAttributeUpdate, TemplateAttributeResponse,
    CombinedAttributeValueResponse
)
from ..schemas.base import PaginationParams, SuccessResponse

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.get("", response_model=SuccessResponse[List[ItemTemplateResponse]])
async def get_templates(
    pagination: PaginationParams = Depends(),
    category_id: Optional[int] = Query(None, description="Фильтр по ID категории"),
    game_id: Optional[int] = Query(None, description="Фильтр по ID игры"),
    search_query: Optional[str] = Query(None, description="Поисковый запрос по названию или описанию"),
    sort_by: str = Query("name", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получение списка шаблонов предметов с возможностью фильтрации, поиска и пагинации
    """
    template_service = TemplateService(db)
    result = template_service.get_templates(
        pagination=pagination,
        category_id=category_id,
        game_id=game_id,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )


@router.get("/{template_id}", response_model=SuccessResponse[ItemTemplateResponse])
async def get_template(
    template_id: int = Path(..., description="ID шаблона"),
    db: Session = Depends(get_db)
):
    """
    Получение информации о конкретном шаблоне предмета по его ID
    """
    template_service = TemplateService(db)
    template = template_service.get_template_by_id(template_id)
    
    return SuccessResponse(data=template)


@router.post("", response_model=SuccessResponse[ItemTemplateResponse], status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ItemTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового шаблона предмета
    
    Пользователи могут создавать собственные шаблоны, если существующие не подходят
    """
    template_service = TemplateService(db)
    template = template_service.create_template(template_data)
    
    return SuccessResponse(
        data=template,
        meta={"message": "Шаблон предмета успешно создан"}
    )


@router.put("/{template_id}", response_model=SuccessResponse[ItemTemplateResponse])
async def update_template(
    template_data: ItemTemplateUpdate,
    template_id: int = Path(..., description="ID шаблона"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление информации о шаблоне предмета
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    template_service = TemplateService(db)
    template = template_service.update_template(template_id, template_data)
    
    return SuccessResponse(
        data=template,
        meta={"message": "Шаблон предмета успешно обновлен"}
    )


@router.delete("/{template_id}", response_model=SuccessResponse)
async def delete_template(
    template_id: int = Path(..., description="ID шаблона"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление шаблона предмета
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    template_service = TemplateService(db)
    template_service.delete_template(template_id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Шаблон предмета успешно удален"}
    )


@router.get("/{template_id}/attributes", response_model=SuccessResponse[List[CombinedAttributeValueResponse]])
async def get_template_attributes(
    template_id: int = Path(..., description="ID шаблона"),
    db: Session = Depends(get_db)
):
    """
    Получение списка атрибутов для конкретного шаблона, включая атрибуты категории и атрибуты шаблона
    """
    template_service = TemplateService(db)
    attributes = template_service.get_template_attributes(template_id)
    
    return SuccessResponse(data=attributes)

@router.get("/{template_id}/specific-attributes", response_model=SuccessResponse[List[TemplateAttributeResponse]])
async def get_template_specific_attributes(
    template_id: int = Path(..., description="ID шаблона"),
    db: Session = Depends(get_db)
):
    """
    Получение списка атрибутов, специфичных для конкретного шаблона (не включая атрибуты категории)
    """
    template_service = TemplateService(db)
    attributes = template_service.get_template_specific_attributes(template_id)
    
    return SuccessResponse(data=attributes)

@router.post("/{template_id}/attributes", response_model=SuccessResponse[TemplateAttributeResponse], status_code=status.HTTP_201_CREATED)
async def create_template_attribute(
    attribute_data: TemplateAttributeCreate,
    template_id: int = Path(..., description="ID шаблона"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Добавление нового атрибута к шаблону
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    # Обеспечиваем, что атрибут создается для указанного шаблона
    attribute_data.template_id = template_id
    
    template_service = TemplateService(db)
    attribute = template_service.create_template_attribute(attribute_data)
    
    return SuccessResponse(
        data=attribute,
        meta={"message": "Атрибут успешно добавлен к шаблону"}
    )

@router.put("/{template_id}/attributes/{attribute_id}", response_model=SuccessResponse[TemplateAttributeResponse])
async def update_template_attribute(
    attribute_data: TemplateAttributeUpdate,
    template_id: int = Path(..., description="ID шаблона"),
    attribute_id: int = Path(..., description="ID атрибута"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление атрибута шаблона
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    template_service = TemplateService(db)
    
    # Проверяем, что атрибут принадлежит указанному шаблону
    attribute = template_service.get_template_attribute_by_id(attribute_id)
    if attribute.template_id != template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Атрибут не принадлежит указанному шаблону"
        )
    
    updated_attribute = template_service.update_template_attribute(attribute_id, attribute_data)
    
    return SuccessResponse(
        data=updated_attribute,
        meta={"message": "Атрибут успешно обновлен"}
    )

@router.delete("/{template_id}/attributes/{attribute_id}", response_model=SuccessResponse)
async def delete_template_attribute(
    template_id: int = Path(..., description="ID шаблона"),
    attribute_id: int = Path(..., description="ID атрибута"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление атрибута шаблона
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    template_service = TemplateService(db)
    
    # Проверяем, что атрибут принадлежит указанному шаблону
    attribute = template_service.get_template_attribute_by_id(attribute_id)
    if attribute.template_id != template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Атрибут не принадлежит указанному шаблону"
        )
    
    template_service.delete_template_attribute(attribute_id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Атрибут успешно удален"}
    ) 