"""
Роутер для управления объявлениями маркетплейса
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User
from ..services.listing_service import ListingService
from ..services.template_service import TemplateService
from ..schemas.marketplace import ListingCreate, ListingUpdate, ListingResponse, ListingDetailResponse
from ..schemas.categorization import ItemTemplateCreate
from ..schemas.base import PaginationParams, SuccessResponse

router = APIRouter(
    prefix="/listings",
    tags=["listings"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.get("", response_model=SuccessResponse[List[ListingResponse]])
async def get_listings(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Фильтр по статусу объявления"),
    seller_id: Optional[int] = Query(None, description="Фильтр по ID продавца"),
    item_template_id: Optional[int] = Query(None, description="Фильтр по ID шаблона предмета"),
    sort_by: str = Query("created_at", description="Поле для сортировки"),
    sort_order: str = Query("desc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получение списка объявлений с возможностью фильтрации и пагинации
    """
    listing_service = ListingService(db)
    result = listing_service.get_listings(
        pagination=pagination,
        status=status,
        seller_id=seller_id,
        item_template_id=item_template_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )

@router.get("/my-listings", response_model=SuccessResponse[List[ListingResponse]])
async def get_my_listings(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Фильтр по статусу объявления"),
    sort_by: str = Query("created_at", description="Поле для сортировки"),
    sort_order: str = Query("desc", description="Порядок сортировки (asc или desc)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка объявлений текущего пользователя
    """
    listing_service = ListingService(db)
    result = listing_service.get_listings(
        pagination=pagination,
        status=status,
        seller_id=current_user.id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )




@router.get("/{listing_id}", response_model=SuccessResponse[ListingDetailResponse])
async def get_listing(
    listing_id: int = Path(..., description="ID объявления"),
    db: Session = Depends(get_db)
):
    """
    Получение подробной информации о конкретном объявлении по его ID,
    включая атрибуты предмета, атрибуты шаблона, похожие объявления и информацию о продавце
    """
    listing_service = ListingService(db)
    result = listing_service.get_listing_detail(listing_id)
    
    # Преобразуем результат сервиса в формат ответа API
    response_data = ListingDetailResponse.from_orm(result["listing"])
    
    # Добавляем атрибуты и дополнительную информацию
    response_data.item_attributes = result["item_attributes"]
    response_data.template_attributes = result["template_attributes"]
    response_data.similar_listings = result["similar_listings"]
    response_data.seller_rating = result["seller_rating"]
    
    # Объединяем все атрибуты для более удобного отображения на фронтенде
    all_attributes = []
    
    # Добавляем атрибуты категории
    for attr in result["item_attributes"]:
        attr["attribute_source"] = "category"
        all_attributes.append(attr)
    
    # Добавляем атрибуты шаблона
    for attr in result["template_attributes"]:
        attr["attribute_source"] = "template"
        all_attributes.append(attr)
    
    response_data.all_attributes = all_attributes
    
    return SuccessResponse(data=response_data)


@router.post("", response_model=SuccessResponse[ListingResponse], status_code=status.HTTP_201_CREATED)
async def create_listing(
    listing_data: ListingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового объявления о продаже
    
    Принимает атрибуты предмета и может также учитывать атрибуты шаблона
    """
    listing_service = ListingService(db)
    
    # Проверяем, есть ли данные о шаблоне для этого объявления
    if listing_data.item_template_id:
        # Получаем атрибуты шаблона и включаем их в создание объявления
        template_service = TemplateService(db)
        template_attributes = template_service.get_template_attributes(listing_data.item_template_id)
        
        # Добавить код для обработки атрибутов шаблона
        # В реальном приложении здесь можно реализовать логику объединения атрибутов
    
    listing = listing_service.create_listing(listing_data, current_user)
    
    return SuccessResponse(
        data=listing,
        meta={"message": "Объявление успешно создано и отправлено на модерацию"}
    )


@router.put("/{listing_id}", response_model=SuccessResponse[ListingResponse])
async def update_listing(
    listing_data: ListingUpdate,
    listing_id: int = Path(..., description="ID объявления"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление информации об объявлении
    """
    listing_service = ListingService(db)
    listing = listing_service.update_listing(listing_id, listing_data, current_user)
    
    return SuccessResponse(
        data=listing,
        meta={"message": "Объявление успешно обновлено"}
    )


@router.delete("/{listing_id}", response_model=SuccessResponse)
async def delete_listing(
    listing_id: int = Path(..., description="ID объявления"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление объявления
    """
    listing_service = ListingService(db)
    listing_service.delete_listing(listing_id, current_user)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Объявление успешно удалено"}
    )



@router.get("/{listing_id}/detail", response_model=SuccessResponse[ListingDetailResponse])
async def get_listing_detail(
    listing_id: int = Path(..., description="ID объявления"),
    db: Session = Depends(get_db)
):
    """
    Получение подробной информации о конкретном объявлении,
    включая атрибуты предмета, атрибуты шаблона, похожие объявления и информацию о продавце
    """
    listing_service = ListingService(db)
    result = listing_service.get_listing_detail(listing_id)
    
    # Преобразуем результат сервиса в формат ответа API
    response_data = ListingDetailResponse.from_orm(result["listing"])
    response_data.item_attributes = result["item_attributes"]
    response_data.template_attributes = result["template_attributes"]
    response_data.similar_listings = result["similar_listings"]
    response_data.seller_rating = result["seller_rating"]
    
    return SuccessResponse(data=response_data)


# Схема для создания кастомного объявления с новым шаблоном
class CustomListingCreate(BaseModel):
    """Схема для создания объявления с новым кастомным шаблоном"""
    # Данные шаблона
    category_id: int
    template_name: str
    template_description: Optional[str] = None
    
    # Данные объявления
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    is_negotiable: bool = False

@router.post("/custom", response_model=SuccessResponse[ListingResponse], status_code=status.HTTP_201_CREATED)
async def create_custom_listing(
    listing_data: CustomListingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового объявления о продаже с собственным шаблоном предмета.
    Позволяет создать новый шаблон, если существующие не подходят.
    """
    # Создаем новый шаблон
    template_service = TemplateService(db)
    template_data = ItemTemplateCreate(
        category_id=listing_data.category_id,
        name=listing_data.template_name,
        description=listing_data.template_description
    )
    
    try:
        new_template = template_service.create_template(template_data)
    except HTTPException as e:
        if e.status_code == status.HTTP_400_BAD_REQUEST and "уже существует" in e.detail:
            # Если шаблон с таким именем уже существует, получаем его
            # Примечание: это потенциально может привести к неожиданному поведению, 
            # но для упрощения демонстрации мы так делаем
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шаблон с таким именем уже существует. Попробуйте использовать другое имя или выбрать существующий шаблон."
            )
        else:
            # Пробрасываем другие ошибки
            raise
    
    # Создаем объявление на основе нового шаблона
    listing_service = ListingService(db)
    listing_create_data = ListingCreate(
        item_template_id=new_template.id,
        title=listing_data.title,
        description=listing_data.description,
        price=listing_data.price,
        currency=listing_data.currency,
        is_negotiable=listing_data.is_negotiable
    )
    
    listing = listing_service.create_listing(listing_create_data, current_user)
    
    return SuccessResponse(
        data=listing,
        meta={
            "message": "Объявление с новым шаблоном успешно создано и отправлено на модерацию",
            "template_id": new_template.id,
            "template_name": new_template.name
        }
    ) 