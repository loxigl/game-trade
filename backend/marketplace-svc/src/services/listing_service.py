"""
Сервис для работы с объявлениями маркетплейса
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func
import logging

from ..models.core import ImageType, Listing, User, ListingStatus
from ..models.categorization import ItemTemplate, ItemCategory, Item, ItemAttributeValue, CategoryAttribute, TemplateAttribute
from ..schemas.marketplace import ListingCreate, ListingUpdate
from ..schemas.base import PaginationParams
from ..services.image_service import ImageService
from .template_service import TemplateService

logger = logging.getLogger(__name__)
class ListingService:
    """Сервис для управления объявлениями маркетплейса"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
    
    def get_listings(
        self, 
        pagination: PaginationParams,
        status: Optional[ListingStatus] = None,
        seller_id: Optional[int] = None,
        item_template_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Получение списка объявлений с фильтрацией и пагинацией
        
        Args:
            pagination: Параметры пагинации
            status: Фильтр по статусу объявления
            seller_id: Фильтр по ID продавца
            item_template_id: Фильтр по ID шаблона предмета
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            
        Returns:
            Dict с объявлениями и метаданными пагинации
        """
        query = self.db.query(Listing)
        
        # Применяем фильтры
        if status:
            query = query.filter(Listing.status == status)
        if seller_id:
            query = query.filter(Listing.seller_id == seller_id)
        if item_template_id:
            query = query.filter(Listing.item_template_id == item_template_id)
        
        # Подсчет общего количества
        total = query.count()
        
        # Применяем сортировку
        if hasattr(Listing, sort_by):
            if sort_order.lower() == "asc":
                query = query.order_by(asc(getattr(Listing, sort_by)))
            else:
                query = query.order_by(desc(getattr(Listing, sort_by)))
        
        # Применяем пагинацию
        query = query.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        
        # Получаем результаты
        listings = query.all()
        
        return {
            "items": listings,
            "meta": {
                "total": total,
                "page": pagination.page,
                "limit": pagination.limit,
                "pages": (total + pagination.limit - 1) // pagination.limit
            }
        }
    
    def get_listing_by_id(self, listing_id: int) -> Listing:
        """
        Получение объявления по ID
        
        Args:
            listing_id: ID объявления
            
        Returns:
            Объект объявления
            
        Raises:
            HTTPException: Если объявление не найдено
        """
        listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объявление не найдено"
            )
        return listing
    
    def create_listing(self, listing_data: ListingCreate, user: User) -> Listing:
        """
        Создание нового объявления
        
        Args:
            listing_data: Данные для создания объявления
            user: Текущий пользователь (продавец)
            
        Returns:
            Созданное объявление
        """
        # Создаем предмет для объявления
        item = Item(
            owner_id=user.id,
            template_id=listing_data.item_template_id,
            is_tradable=True,
        )
        self.db.add(item)
        self.db.flush()
        
        # Создаем объект объявления
        listing = Listing(
            item_id=item.id,
            seller_id=user.id,
            item_template_id=listing_data.item_template_id,
            title=listing_data.title,
            description=listing_data.description,
            price=listing_data.price,
            currency=listing_data.currency,
            status=ListingStatus.PENDING
        )
        
        self.db.add(listing)
        
        
        # Обрабатываем атрибуты предмета, если они указаны
        if listing_data.attribute_values:
            for attr_value in listing_data.attribute_values:
                if attr_value.attribute_id:
                    item_attr = ItemAttributeValue(
                        item_id=item.id,
                        attribute_id=attr_value.attribute_id,
                        value_string=attr_value.value_string,
                        value_number=attr_value.value_number,
                        value_boolean=attr_value.value_boolean
                    )
                    self.db.add(item_attr)
                elif attr_value.template_attribute_id:
                    item_attr = ItemAttributeValue(
                        item_id=item.id,
                        template_attribute_id=attr_value.template_attribute_id,
                        value_string=attr_value.value_string,
                        value_number=attr_value.value_number,
                        value_boolean=attr_value.value_boolean
                    )
                    self.db.add(item_attr)
            
        
        self.db.commit()
        self.db.refresh(listing)
        logger.info(f"Объявление создано: {listing.id}")
        return listing
    
    def update_listing(self, listing_id: int, listing_data: ListingUpdate, user: User) -> Listing:
        """
        Обновление существующего объявления
        
        Args:
            listing_id: ID объявления для обновления
            listing_data: Новые данные объявления
            user: Текущий пользователь
            
        Returns:
            Обновленное объявление
            
        Raises:
            HTTPException: Если объявление не найдено или нет прав на редактирование
        """
        listing = self.get_listing_by_id(listing_id)
        
        # Проверяем, что пользователь является владельцем объявления
        if listing.seller_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для редактирования этого объявления"
            )
        # Обновляем поля, если они указаны
        if listing_data.title is not None:
            listing.title = listing_data.title
        if listing_data.description is not None:
            listing.description = listing_data.description
        if listing_data.price is not None:
            listing.price = listing_data.price
        if listing_data.currency is not None:
            listing.currency = listing_data.currency
        if listing_data.status is not None:
            # Если статус изменился на ACTIVE, проверяем, завершена ли модерация
            if listing_data.status == ListingStatus.ACTIVE and listing.status == ListingStatus.PENDING:
                # В реальном приложении здесь должна быть проверка, прошло ли объявление модерацию
                pass
            
            listing.status = listing_data.status
        image_service = ImageService(self.db)
        if listing_data.images is not None:
            for image in listing_data.images:
                if image.id is not None:
                    image_service.attach_image_to_entity(image.id, listing.id, ImageType.LISTING, user.id)
                    if image.is_main:
                        image_service.set_main_image(image.id, listing.id, ImageType.LISTING)
                    if image.order_index is not None:
                        image_service.update_image_order(image.id, image.order_index, user.id)
        if listing_data.deleted_image_ids is not None:
            for image_id in listing_data.deleted_image_ids:
                image_service.delete_image(image_id)
        self.db.commit()
        self.db.refresh(listing)
        
        return listing
    
    def delete_listing(self, listing_id: int, user: User) -> bool:
        """
        Удаление объявления
        
        Args:
            listing_id: ID объявления для удаления
            user: Текущий пользователь
            
        Returns:
            True, если объявление успешно удалено
            
        Raises:
            HTTPException: Если объявление не найдено или нет прав на удаление
        """
        listing = self.get_listing_by_id(listing_id)
        
        # Проверяем, что пользователь является владельцем объявления
        if listing.seller_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для удаления этого объявления"
            )
        
        self.db.delete(listing)
        self.db.commit()
        
        return True
    
    def get_listing_detail(self, listing_id: int) -> Dict[str, Any]:
        """
        Получение подробной информации об объявлении, включая шаблон предмета,
        атрибуты предмета и похожие объявления
        
        Args:
            listing_id: ID объявления
            
        Returns:
            Dict с объявлением и дополнительными данными
            
        Raises:
            HTTPException: Если объявление не найдено
        """
        # Получаем объявление с подгрузкой шаблона и предмета
        listing = self.db.query(Listing).options(
            joinedload(Listing.item_template),
            joinedload(Listing.item).joinedload(Item.attribute_values),
            joinedload(Listing.seller).joinedload(User.profile)
        ).filter(Listing.id == listing_id).first()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объявление не найдено"
            )
        
        # Увеличиваем счетчик просмотров
        listing.views_count += 1
        self.db.commit()
        
        # Получаем атрибуты предмета, если они есть
        item_attributes = []
        if listing.item:
            # Подгружаем связанные атрибуты для корректного отображения
            item_attrs_query = self.db.query(ItemAttributeValue).options(
                joinedload(ItemAttributeValue.attribute)
            ).filter(
                ItemAttributeValue.item_id == listing.item.id,
                ItemAttributeValue.attribute_id != None  # Это атрибуты категории
            )
            
            category_item_attributes = item_attrs_query.all()
            
            # Преобразуем в удобный формат для ответа
            formatted_item_attrs = []
            for attr_value in category_item_attributes:
                if not attr_value.attribute:
                    continue
                    
                attr_type = attr_value.attribute.attribute_type
                value_field = "value_string"
                if attr_type == "number":
                    value_field = "value_number"
                elif attr_type == "boolean":
                    value_field = "value_boolean"
                    
                formatted_item_attrs.append({
                    "id": attr_value.id,
                    "attribute_id": attr_value.attribute_id,
                    "attribute_name": attr_value.attribute.name,
                    "attribute_type": attr_type,
                    "value_string": attr_value.value_string,
                    "value_number": attr_value.value_number,
                    "value_boolean": attr_value.value_boolean
                })
            
            item_attributes = formatted_item_attrs
        
        # Получаем атрибуты шаблона
        template_attributes = []
        if listing.item:
            # Подгружаем связанные атрибуты для корректного отображения
            template_attrs_query = self.db.query(ItemAttributeValue).options(
                joinedload(ItemAttributeValue.template_attribute)
            ).filter(
                ItemAttributeValue.item_id == listing.item.id,
                ItemAttributeValue.template_attribute_id != None  # Это атрибуты шаблона
            )
            
            template_item_attributes = template_attrs_query.all()
            
            # Преобразуем в удобный формат для ответа
            formatted_template_attrs = []
            for attr_value in template_item_attributes:
                if not attr_value.template_attribute:
                    continue
                    
                attr_type = attr_value.template_attribute.attribute_type
                value_field = "value_string"
                if attr_type == "number":
                    value_field = "value_number"
                elif attr_type == "boolean":
                    value_field = "value_boolean"
                    
                formatted_template_attrs.append({
                    "id": attr_value.id,
                    "template_attribute_id": attr_value.template_attribute_id,
                    "attribute_name": attr_value.template_attribute.name,
                    "attribute_type": attr_type,
                    "value_string": attr_value.value_string,
                    "value_number": attr_value.value_number,
                    "value_boolean": attr_value.value_boolean
                })
            
            template_attributes = formatted_template_attrs
        
        # Получаем похожие объявления для этого шаблона или категории
        similar_listings = []
        if listing.item_template:
            # Получаем объявления с тем же шаблоном предмета
            similar_listings = self.db.query(Listing).filter(
                Listing.item_template_id == listing.item_template_id,
                Listing.id != listing_id,
                Listing.status == ListingStatus.ACTIVE
            ).order_by(Listing.price).limit(5).all()
            
            # Если похожих объявлений по шаблону не нашлось, ищем по категории
            if not similar_listings and listing.item_template.category_id:
                template_ids = self.db.query(ItemTemplate.id).filter(
                    ItemTemplate.category_id == listing.item_template.category_id
                ).all()
                template_ids = [t[0] for t in template_ids]
                
                similar_listings = self.db.query(Listing).filter(
                    Listing.item_template_id.in_(template_ids),
                    Listing.id != listing_id,
                    Listing.status == ListingStatus.ACTIVE
                ).order_by(Listing.price).limit(5).all()
        
        # Получаем рейтинг продавца
        seller_rating = None
        if listing.seller and hasattr(listing.seller, 'profile') and listing.seller.profile:
            seller_rating = listing.seller.profile.reputation_score
        
        return {
            "listing": listing,
            "item_attributes": item_attributes,
            "template_attributes": template_attributes,
            "similar_listings": similar_listings,
            "seller_rating": seller_rating
        }
    
    def increase_views_count(self, listing_id: int) -> Listing:
        """
        Увеличивает счётчик просмотров объявления
        
        Args:
            listing_id: ID объявления
            
        Returns:
            Обновленное объявление
        """
        listing = self.get_listing_by_id(listing_id)
        listing.views_count += 1
        self.db.commit()
        self.db.refresh(listing)
        return listing 