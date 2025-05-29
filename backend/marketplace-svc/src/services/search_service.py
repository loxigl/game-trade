"""
Сервис для поиска и фильтрации предметов на маркетплейсе
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, asc, desc, func, text
from fastapi import HTTPException, status

from ..models.core import Listing, ListingStatus
from ..models.categorization import (
    Game, ItemCategory, ItemTemplate, Item, CategoryAttribute, ItemAttributeValue
)
from ..schemas.base import PaginationParams
from ..schemas.search import SearchParams, FilterParams

class SearchService:
    """Сервис для поиска и фильтрации предметов на маркетплейсе"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
    
    def _get_category_with_subcategories(self, category_ids: List[int]) -> List[int]:
        """
        Получает список ID категорий включая все их подкатегории
        
        Args:
            category_ids: Список ID родительских категорий
            
        Returns:
            Расширенный список ID категорий включая подкатегории
        """
        if not category_ids:
            return []
        
        all_category_ids = set(category_ids)
        
        # Рекурсивно находим все подкатегории для каждой категории
        def find_subcategories(parent_ids: List[int]) -> List[int]:
            if not parent_ids:
                return []
            
            # Ищем прямые подкатегории
            subcategories = self.db.query(ItemCategory.id).filter(
                ItemCategory.parent_id.in_(parent_ids)
            ).all()
            
            subcategory_ids = [sub.id for sub in subcategories]
            
            if subcategory_ids:
                # Добавляем найденные подкатегории к общему списку
                all_category_ids.update(subcategory_ids)
                # Рекурсивно ищем подкатегории для найденных категорий
                find_subcategories(subcategory_ids)
            
            return subcategory_ids
        
        # Запускаем рекурсивный поиск
        find_subcategories(category_ids)
        
        return list(all_category_ids)
    
    def search_listings(
        self, 
        pagination: PaginationParams,
        search_params: SearchParams,
        filter_params: Optional[FilterParams] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_subcategories: bool = True
    ) -> Dict[str, Any]:
        """
        Поиск объявлений по различным критериям с фильтрацией и пагинацией
        
        Args:
            pagination: Параметры пагинации
            search_params: Параметры поиска (текст, категории, игры)
            filter_params: Параметры фильтрации (диапазон цен, атрибуты)
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            include_subcategories: Включать ли подкатегории при поиске по категориям
            
        Returns:
            Dict с результатами поиска и метаданными пагинации
        """
        # Строим базовый запрос с джойнами для доступа к связанным таблицам
        query = self.db.query(Listing).join(
            ItemTemplate, Listing.item_template_id == ItemTemplate.id
        ).join(
            ItemCategory, ItemTemplate.category_id == ItemCategory.id
        ).join(
            Game, ItemCategory.game_id == Game.id
        ).filter(
            # По умолчанию показываем только активные объявления
            Listing.status == ListingStatus.ACTIVE
        )
        
        # Применяем текстовый поиск, если указан
        if search_params.query:
            search_text = f"%{search_params.query}%"
            query = query.filter(or_(
                Listing.title.ilike(search_text),
                Listing.description.ilike(search_text),
                ItemTemplate.name.ilike(search_text),
                ItemTemplate.description.ilike(search_text),
                ItemCategory.name.ilike(search_text),
                Game.name.ilike(search_text)
            ))
        
        # Фильтрация по играм
        if search_params.game_ids and len(search_params.game_ids) > 0:
            query = query.filter(Game.id.in_(search_params.game_ids))
        
        # Фильтрация по категориям с учетом подкатегорий
        if search_params.category_ids and len(search_params.category_ids) > 0:
            if include_subcategories:
                # Получаем расширенный список категорий включая подкатегории
                expanded_category_ids = self._get_category_with_subcategories(search_params.category_ids)
                query = query.filter(ItemCategory.id.in_(expanded_category_ids))
            else:
                # Используем только указанные категории
                query = query.filter(ItemCategory.id.in_(search_params.category_ids))
        
        # Применяем дополнительные фильтры, если указаны
        if filter_params:
            # Фильтрация по цене
            if filter_params.min_price is not None:
                query = query.filter(Listing.price >= filter_params.min_price)
            
            if filter_params.max_price is not None:
                query = query.filter(Listing.price <= filter_params.max_price)
            
            # Фильтрация по валюте
            if filter_params.currency:
                query = query.filter(Listing.currency == filter_params.currency)
            
            # Фильтрация по атрибутам (сложная логика, требует дополнительных JOIN)
            if filter_params.attributes and len(filter_params.attributes) > 0:
                # Для каждого атрибута создаем подзапрос и применяем его
                for attr_id, attr_value in filter_params.attributes.items():
                    # Находим шаблоны предметов, у которых есть экземпляры с указанным атрибутом
                    # Это сложная часть запроса, которая может потребовать оптимизации
                    if isinstance(attr_value, str):  # Строковый атрибут
                        subquery = self.db.query(ItemAttributeValue.item_id).join(
                            Item, ItemAttributeValue.item_id == Item.id
                        ).filter(
                            ItemAttributeValue.attribute_id == attr_id,
                            ItemAttributeValue.value_string == attr_value
                        ).subquery()
                    elif isinstance(attr_value, (int, float)):  # Числовой атрибут
                        subquery = self.db.query(ItemAttributeValue.item_id).join(
                            Item, ItemAttributeValue.item_id == Item.id
                        ).filter(
                            ItemAttributeValue.attribute_id == attr_id,
                            ItemAttributeValue.value_number == attr_value
                        ).subquery()
                    elif isinstance(attr_value, bool):  # Булевый атрибут
                        subquery = self.db.query(ItemAttributeValue.item_id).join(
                            Item, ItemAttributeValue.item_id == Item.id
                        ).filter(
                            ItemAttributeValue.attribute_id == attr_id,
                            ItemAttributeValue.value_boolean == attr_value
                        ).subquery()
                    
                    # Применяем подзапрос к основному запросу
                    query = query.filter(Item.id.in_(subquery))
        
        # Подсчет общего количества результатов
        total = query.count()
        
        # Применяем сортировку
        if sort_by == "price":
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Listing.price))
            else:
                query = query.order_by(desc(Listing.price))
        elif sort_by == "views":
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Listing.views_count))
            else:
                query = query.order_by(desc(Listing.views_count))
        elif sort_by == "name":
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Listing.title))
            else:
                query = query.order_by(desc(Listing.title))
        else:  # По умолчанию сортировка по дате создания
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Listing.created_at))
            else:
                query = query.order_by(desc(Listing.created_at))
        
        # Применяем пагинацию
        query = query.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        
        # Подгружаем связанные сущности
        query = query.options(
            joinedload(Listing.seller),
            joinedload(Listing.item_template).joinedload(ItemTemplate.category)
        )
        
        # Получаем результаты
        listings = query.all()
        
        return {
            "items": listings,
            "meta": {
                "total": total,
                "page": pagination.page,
                "limit": pagination.limit,
                "pages": (total + pagination.limit - 1) // pagination.limit,
                "query": search_params.query if search_params.query else None,
                "included_subcategories": include_subcategories
            }
        }
    
    def get_filter_options(
        self, 
        game_id: Optional[int] = None, 
        category_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение доступных опций фильтрации для UI
        
        Args:
            game_id: ID игры для фильтрации категорий
            category_id: ID категории для фильтрации атрибутов
            
        Returns:
            Dict с доступными опциями фильтрации
        """
        result = {
            "games": [],
            "categories": [],
            "attributes": [],
            "price_range": {
                "min": 0,
                "max": 0,
                "currencies": []
            }
        }
        
        # Получаем список доступных игр
        games_query = self.db.query(
            Game.id, Game.name, Game.logo_url
        ).filter(
            Game.is_active == True
        ).order_by(Game.name)
        
        result["games"] = [
            {"id": g.id, "name": g.name, "logo_url": g.logo_url}
            for g in games_query.all()
        ]
        
        # Получаем список доступных категорий, фильтруя по игре, если указана
        categories_query = self.db.query(
            ItemCategory.id, 
            ItemCategory.name, 
            ItemCategory.icon_url, 
            ItemCategory.parent_id,
            ItemCategory.category_type,
            Game.id.label("game_id"), 
            Game.name.label("game_name")
        ).join(
            Game, ItemCategory.game_id == Game.id
        ).filter(
            Game.is_active == True
        )
        
        if game_id:
            categories_query = categories_query.filter(Game.id == game_id)
            
        categories_query = categories_query.order_by(Game.name, ItemCategory.name)
        
        result["categories"] = [
            {
                "id": c.id, 
                "name": c.name, 
                "icon_url": c.icon_url,
                "parent_id": c.parent_id,
                "category_type": c.category_type,
                "game_id": c.game_id,
                "game_name": c.game_name
            }
            for c in categories_query.all()
        ]
        
        # Получаем список атрибутов для фильтрации, если указана категория
        if category_id:
            attributes_query = self.db.query(
                CategoryAttribute
            ).filter(
                CategoryAttribute.category_id == category_id,
                CategoryAttribute.is_filterable == True
            ).order_by(CategoryAttribute.name)
            
            result["attributes"] = [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.attribute_type,
                    "options": a.options  # JSON строка с опциями для ENUM типа
                }
                for a in attributes_query.all()
            ]
        
        # Получаем диапазон цен (минимальная и максимальная цена)
        price_query = self.db.query(
            func.min(Listing.price).label("min_price"),
            func.max(Listing.price).label("max_price")
        ).filter(
            Listing.status == ListingStatus.ACTIVE
        )
        
        price_range = price_query.first()
        if price_range:
            result["price_range"]["min"] = float(price_range.min_price) if price_range.min_price else 0
            result["price_range"]["max"] = float(price_range.max_price) if price_range.max_price else 0
        
        # Получаем список используемых валют
        currencies_query = self.db.query(
            Listing.currency
        ).filter(
            Listing.status == ListingStatus.ACTIVE
        ).distinct().order_by(Listing.currency)
        
        result["price_range"]["currencies"] = [c.currency for c in currencies_query.all()]
        
        return result
    
    def get_category_hierarchy(self, category_id: int) -> Dict[str, Any]:
        """
        Получение иерархии категории (родители и дети)
        
        Args:
            category_id: ID категории
            
        Returns:
            Dict с информацией о категории и её иерархии
        """
        # Получаем основную информацию о категории
        category = self.db.query(ItemCategory).filter(
            ItemCategory.id == category_id
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        result = {
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "icon_url": category.icon_url,
                "category_type": category.category_type,
                "parent_id": category.parent_id
            },
            "breadcrumbs": [],
            "subcategories": []
        }
        
        # Строим breadcrumbs (путь к корню)
        current_category = category
        breadcrumbs = []
        
        while current_category:
            breadcrumbs.insert(0, {
                "id": current_category.id,
                "name": current_category.name,
                "icon_url": current_category.icon_url
            })
            
            if current_category.parent_id:
                current_category = self.db.query(ItemCategory).filter(
                    ItemCategory.id == current_category.parent_id
                ).first()
            else:
                current_category = None
        
        result["breadcrumbs"] = breadcrumbs
        
        # Получаем прямые подкатегории
        subcategories = self.db.query(ItemCategory).filter(
            ItemCategory.parent_id == category_id
        ).order_by(ItemCategory.order_index, ItemCategory.name).all()
        
        result["subcategories"] = [
            {
                "id": sub.id,
                "name": sub.name,
                "description": sub.description,
                "icon_url": sub.icon_url,
                "category_type": sub.category_type
            }
            for sub in subcategories
        ]
        
        return result
    
    def get_popular_items(self, limit: int = 10) -> List[Listing]:
        """
        Получение списка популярных товаров (по количеству просмотров)
        
        Args:
            limit: Максимальное количество результатов
            
        Returns:
            Список объявлений
        """
        query = self.db.query(Listing).filter(
            Listing.status == ListingStatus.ACTIVE
        ).order_by(
            desc(Listing.views_count)
        ).limit(limit)
        
        query = query.options(
            joinedload(Listing.seller),
            joinedload(Listing.item_template).joinedload(ItemTemplate.category)
        )
        
        return query.all()
    
    def get_trending_categories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получение списка популярных категорий (по количеству активных объявлений)
        
        Args:
            limit: Максимальное количество результатов
            
        Returns:
            Список категорий с дополнительной информацией
        """
        # Подсчитываем количество объявлений в каждой категории
        query = self.db.query(
            ItemCategory.id, 
            ItemCategory.name,
            ItemCategory.icon_url,
            ItemCategory.parent_id,
            ItemCategory.category_type,
            Game.id.label("game_id"),
            Game.name.label("game_name"),
            func.count(Listing.id).label("listings_count")
        ).join(
            ItemTemplate, ItemCategory.id == ItemTemplate.category_id
        ).join(
            Listing, ItemTemplate.id == Listing.item_template_id
        ).join(
            Game, ItemCategory.game_id == Game.id
        ).filter(
            Listing.status == ListingStatus.ACTIVE,
            Game.is_active == True
        ).group_by(
            ItemCategory.id, ItemCategory.name, ItemCategory.icon_url, 
            ItemCategory.parent_id, ItemCategory.category_type, Game.id, Game.name
        ).order_by(
            desc(text("listings_count"))
        ).limit(limit)
        
        result = []
        for row in query.all():
            result.append({
                "id": row.id,
                "name": row.name,
                "icon_url": row.icon_url,
                "parent_id": row.parent_id,
                "category_type": row.category_type,
                "game_id": row.game_id,
                "game_name": row.game_name,
                "listings_count": row.listings_count
            })
        
        return result
    
    def search_templates(
        self,
        pagination: PaginationParams,
        query: Optional[str] = None,
        category_id: Optional[int] = None,
        game_id: Optional[int] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        include_subcategories: bool = True
    ) -> Dict[str, Any]:
        """
        Поиск шаблонов предметов по тексту, категории или игре
        
        Args:
            pagination: Параметры пагинации
            query: Текст поиска (название шаблона)
            category_id: ID категории для фильтрации
            game_id: ID игры для фильтрации
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            include_subcategories: Включать ли подкатегории при поиске по категории
            
        Returns:
            Dict с результатами поиска и метаданными пагинации
        """
        # Строим запрос с джойнами для доступа к категориям и играм
        query_builder = self.db.query(ItemTemplate).join(
            ItemCategory, ItemTemplate.category_id == ItemCategory.id
        ).join(
            Game, ItemCategory.game_id == Game.id
        )
        
        # Применяем фильтр по тексту, если указан
        if query:
            search_text = f"%{query}%"
            query_builder = query_builder.filter(or_(
                ItemTemplate.name.ilike(search_text),
                ItemTemplate.description.ilike(search_text),
                ItemCategory.name.ilike(search_text),
                Game.name.ilike(search_text)
            ))
        
        # Фильтрация по категории с учетом подкатегорий
        if category_id:
            if include_subcategories:
                # Получаем расширенный список категорий включая подкатегории
                expanded_category_ids = self._get_category_with_subcategories([category_id])
                query_builder = query_builder.filter(ItemTemplate.category_id.in_(expanded_category_ids))
            else:
                query_builder = query_builder.filter(ItemTemplate.category_id == category_id)
        
        # Фильтрация по игре
        if game_id:
            query_builder = query_builder.filter(ItemCategory.game_id == game_id)
        
        # Подсчет общего количества результатов
        total = query_builder.count()
        
        # Применяем сортировку
        if sort_by in ["name", "created_at", "id"]:
            if sort_order.lower() == "asc":
                query_builder = query_builder.order_by(asc(getattr(ItemTemplate, sort_by)))
            else:
                query_builder = query_builder.order_by(desc(getattr(ItemTemplate, sort_by)))
        
        # Применяем пагинацию
        query_builder = query_builder.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        
        # Подгружаем связанные категории для отображения информации о категории
        query_builder = query_builder.options(joinedload(ItemTemplate.category))
        
        # Получаем результаты
        templates = query_builder.all()
        
        return {
            "items": templates,
            "meta": {
                "total": total,
                "page": pagination.page,
                "limit": pagination.limit,
                "pages": (total + pagination.limit - 1) // pagination.limit,
                "query": query if query else None,
                "included_subcategories": include_subcategories
            }
        }