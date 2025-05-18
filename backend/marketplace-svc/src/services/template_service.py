"""
Сервис для работы с шаблонами предметов
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_
import json

from ..models.categorization import (
    ItemTemplate, ItemCategory, Game, CategoryAttribute, AttributeType, 
    TemplateAttribute
)
from ..models.core import Image, ImageType
from ..schemas.categorization import (
    ItemTemplateCreate, ItemTemplateUpdate, 
    TemplateAttributeCreate, TemplateAttributeUpdate,
    CombinedAttributeValueResponse
)
from ..schemas.base import PaginationParams

class TemplateService:
    """Сервис для управления шаблонами предметов"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
    
    def get_templates(
        self, 
        pagination: PaginationParams,
        category_id: Optional[int] = None,
        game_id: Optional[int] = None,
        search_query: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Получение списка шаблонов предметов с фильтрацией, поиском и пагинацией
        
        Args:
            pagination: Параметры пагинации
            category_id: Фильтр по ID категории
            game_id: Фильтр по ID игры (выбирает шаблоны из всех категорий этой игры)
            search_query: Поисковый запрос для фильтрации по имени или описанию
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            
        Returns:
            Dict с шаблонами и метаданными пагинации
        """
        query = self.db.query(ItemTemplate).options(joinedload(ItemTemplate.category))
        
        # Применяем фильтры
        if category_id:
            query = query.filter(ItemTemplate.category_id == category_id)
        
        if game_id:
            query = query.join(ItemCategory).filter(ItemCategory.game_id == game_id)
        
        # Применяем поиск, если указан поисковый запрос
        if search_query:
            search_term = f"%{search_query.lower()}%"
            query = query.filter(
                or_(
                    func.lower(ItemTemplate.name).like(search_term),
                    func.lower(ItemTemplate.description).like(search_term)
                )
            )
        
        # Подсчет общего количества
        total = query.count()
        
        # Применяем сортировку
        if hasattr(ItemTemplate, sort_by):
            if sort_order.lower() == "asc":
                query = query.order_by(asc(getattr(ItemTemplate, sort_by)))
            else:
                query = query.order_by(desc(getattr(ItemTemplate, sort_by)))
        
        # Применяем пагинацию
        query = query.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        
        # Получаем результаты
        templates = query.all()
        
        return {
            "items": templates,
            "meta": {
                "total": total,
                "page": pagination.page,
                "limit": pagination.limit,
                "pages": (total + pagination.limit - 1) // pagination.limit
            }
        }
    
    def get_templates_by_category(
        self, 
        category_id: int,
        pagination: PaginationParams,
        search_query: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Получение шаблонов предметов для конкретной категории с поддержкой поиска
        
        Args:
            category_id: ID категории
            pagination: Параметры пагинации
            search_query: Поисковый запрос для фильтрации по имени или описанию
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            
        Returns:
            Dict с шаблонами и метаданными пагинации
            
        Raises:
            HTTPException: Если категория не найдена
        """
        # Проверяем, что категория существует
        category = self.db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        # Возвращаем шаблоны для этой категории
        return self.get_templates(
            pagination=pagination,
            category_id=category_id,
            search_query=search_query,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    def get_template_by_id(self, template_id: int) -> ItemTemplate:
        """
        Получение шаблона предмета по ID
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Объект шаблона
            
        Raises:
            HTTPException: Если шаблон не найден
        """
        template = self.db.query(ItemTemplate).filter(ItemTemplate.id == template_id).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шаблон предмета не найден"
            )
        return template
    
    def create_template(self, template_data: ItemTemplateCreate) -> ItemTemplate:
        """
        Создание нового шаблона предмета
        
        Args:
            template_data: Данные для создания шаблона
            
        Returns:
            Созданный шаблон
            
        Raises:
            HTTPException: Если категория не найдена или шаблон с таким именем уже существует
        """
        # Проверяем, что категория существует
        category = self.db.query(ItemCategory).filter(ItemCategory.id == template_data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        # Проверяем, что шаблон с таким именем не существует для данной категории
        existing_template = self.db.query(ItemTemplate).filter(
            ItemTemplate.category_id == template_data.category_id,
            func.lower(ItemTemplate.name) == func.lower(template_data.name)
        ).first()
        
        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шаблон с таким именем уже существует для данной категории"
            )
        
        # Создаем объект шаблона
        template = ItemTemplate(
            category_id=template_data.category_id,
            name=template_data.name,
            description=template_data.description
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    def update_template(self, template_id: int, template_data: ItemTemplateUpdate) -> ItemTemplate:
        """
        Обновление существующего шаблона предмета
        
        Args:
            template_id: ID шаблона для обновления
            template_data: Новые данные шаблона
            
        Returns:
            Обновленный шаблон
            
        Raises:
            HTTPException: Если шаблон не найден или новое имя уже занято
        """
        template = self.get_template_by_id(template_id)
        
        # Если изменяется имя, проверяем, что новое имя не занято
        if template_data.name is not None and template_data.name != template.name:
            existing_template = self.db.query(ItemTemplate).filter(
                ItemTemplate.category_id == template.category_id,
                func.lower(ItemTemplate.name) == func.lower(template_data.name),
                ItemTemplate.id != template_id
            ).first()
            
            if existing_template:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Шаблон с таким именем уже существует для данной категории"
                )
            
            template.name = template_data.name
        
        # Обновляем остальные поля, если они указаны
        if template_data.description is not None:
            template.description = template_data.description
        
        if template_data.is_tradable is not None:
            template.is_tradable = template_data.is_tradable
        
        if template_data.base_price is not None:
            template.base_price = template_data.base_price
        
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    def delete_template(self, template_id: int) -> None:
        """
        Удаление шаблона предмета
        
        Args:
            template_id: ID шаблона для удаления
            
        Raises:
            HTTPException: Если шаблон не найден или не может быть удален
        """
        template = self.get_template_by_id(template_id)
        
        # Проверяем, есть ли объявления, использующие этот шаблон
        if template.listings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить шаблон, так как с ним связаны объявления"
            )
        
        self.db.delete(template)
        self.db.commit()

    def get_template_attributes(self, template_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех атрибутов для шаблона, включая атрибуты категории и атрибуты шаблона
        
        Args:
            template_id: ID шаблона
        
        Returns:
            Список атрибутов в формате для ответа API
        
        Raises:
            HTTPException: Если шаблон не найден
        """
        template = self.get_template_by_id(template_id)
        
        # Получаем атрибуты категории
        category_attributes = self.db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == template.category_id
        ).all()
        
        # Получаем атрибуты шаблона
        template_attributes = self.db.query(TemplateAttribute).filter(
            TemplateAttribute.template_id == template_id
        ).all()
        
        # Формируем ответ в виде комбинированного списка атрибутов
        result = []
        
        # Добавляем атрибуты категории
        for attr in category_attributes:
            attribute_value = {
                "id": None,  # Будет заполнено при создании конкретного предмета
                "attribute_id": attr.id,
                "template_attribute_id": None,
                "attribute_name": attr.name,
                "attribute_type": attr.attribute_type,
                "attribute_source": "category",
                "is_required": attr.is_required,
                "value_string": None,
                "value_number": None,
                "value_boolean": None,
                "options": attr.options
            }
            
            # Устанавливаем дефолтное значение в зависимости от типа атрибута
            if attr.attribute_type == AttributeType.STRING or attr.attribute_type == AttributeType.ENUM:
                attribute_value["value_string"] = attr.default_value
            elif attr.attribute_type == AttributeType.NUMBER:
                try:
                    attribute_value["value_number"] = float(attr.default_value) if attr.default_value else None
                except (ValueError, TypeError):
                    attribute_value["value_number"] = None
            elif attr.attribute_type == AttributeType.BOOLEAN:
                attribute_value["value_boolean"] = attr.default_value == "true" if attr.default_value else False
                
            result.append(attribute_value)
        
        # Добавляем атрибуты шаблона
        for attr in template_attributes:
            attribute_value = {
                "id": None,  # Будет заполнено при создании конкретного предмета
                "attribute_id": None,
                "template_attribute_id": attr.id,
                "attribute_name": attr.name,
                "attribute_type": attr.attribute_type,
                "attribute_source": "template",
                "is_required": attr.is_required,
                "value_string": None,
                "value_number": None,
                "value_boolean": None,
                "options": attr.options
            }
            
            # Устанавливаем дефолтное значение в зависимости от типа атрибута
            if attr.attribute_type == AttributeType.STRING or attr.attribute_type == AttributeType.ENUM:
                attribute_value["value_string"] = attr.default_value
            elif attr.attribute_type == AttributeType.NUMBER:
                try:
                    attribute_value["value_number"] = float(attr.default_value) if attr.default_value else None
                except (ValueError, TypeError):
                    attribute_value["value_number"] = None
            elif attr.attribute_type == AttributeType.BOOLEAN:
                attribute_value["value_boolean"] = attr.default_value == "true" if attr.default_value else False
                
            result.append(attribute_value)
        
        return result

    def get_template_attribute_by_id(self, attribute_id: int) -> TemplateAttribute:
        """
        Получение атрибута шаблона по ID
        
        Args:
            attribute_id: ID атрибута
            
        Returns:
            Объект атрибута
            
        Raises:
            HTTPException: Если атрибут не найден
        """
        attribute = self.db.query(TemplateAttribute).filter(TemplateAttribute.id == attribute_id).first()
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Атрибут шаблона не найден"
            )
        return attribute

    def create_template_attribute(self, attribute_data: TemplateAttributeCreate) -> TemplateAttribute:
        """
        Создание нового атрибута шаблона
        
        Args:
            attribute_data: Данные для создания атрибута
            
        Returns:
            Созданный атрибут
            
        Raises:
            HTTPException: Если шаблон не найден или атрибут с таким именем уже существует
        """
        # Проверяем, что шаблон существует
        template = self.get_template_by_id(attribute_data.template_id)
        
        # Проверяем, что атрибут с таким именем не существует для данного шаблона
        existing_attribute = self.db.query(TemplateAttribute).filter(
            TemplateAttribute.template_id == attribute_data.template_id,
            func.lower(TemplateAttribute.name) == func.lower(attribute_data.name)
        ).first()
        
        if existing_attribute:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Атрибут с таким именем уже существует для данного шаблона"
            )
        
        # Проверяем, не совпадает ли имя атрибута с именем атрибута категории
        category_id = template.category_id
        existing_category_attribute = self.db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category_id,
            func.lower(CategoryAttribute.name) == func.lower(attribute_data.name)
        ).first()
        
        if existing_category_attribute:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Атрибут с таким именем уже существует в категории этого шаблона"
            )
        
        # Создаем объект атрибута
        attribute = TemplateAttribute(
            template_id=attribute_data.template_id,
            name=attribute_data.name,
            description=attribute_data.description,
            attribute_type=attribute_data.attribute_type,
            is_required=attribute_data.is_required,
            is_filterable=attribute_data.is_filterable,
            default_value=attribute_data.default_value,
            options=attribute_data.options
        )
        
        self.db.add(attribute)
        self.db.commit()
        self.db.refresh(attribute)
        
        return attribute

    def update_template_attribute(
        self, 
        attribute_id: int, 
        attribute_data: TemplateAttributeUpdate
    ) -> TemplateAttribute:
        """
        Обновление существующего атрибута шаблона
        
        Args:
            attribute_id: ID атрибута для обновления
            attribute_data: Новые данные атрибута
            
        Returns:
            Обновленный атрибут
            
        Raises:
            HTTPException: Если атрибут не найден или новое имя уже занято
        """
        attribute = self.get_template_attribute_by_id(attribute_id)
        
        # Если изменяется имя, проверяем, что новое имя не занято
        if attribute_data.name is not None and attribute_data.name != attribute.name:
            # Проверяем на уровне шаблона
            existing_attribute = self.db.query(TemplateAttribute).filter(
                TemplateAttribute.template_id == attribute.template_id,
                func.lower(TemplateAttribute.name) == func.lower(attribute_data.name),
                TemplateAttribute.id != attribute_id
            ).first()
            
            if existing_attribute:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Атрибут с таким именем уже существует для данного шаблона"
                )
            
            # Получаем шаблон и категорию
            template = self.get_template_by_id(attribute.template_id)
            
            # Проверяем на уровне категории
            existing_category_attribute = self.db.query(CategoryAttribute).filter(
                CategoryAttribute.category_id == template.category_id,
                func.lower(CategoryAttribute.name) == func.lower(attribute_data.name)
            ).first()
            
            if existing_category_attribute:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Атрибут с таким именем уже существует в категории этого шаблона"
                )
            
            attribute.name = attribute_data.name
        
        # Обновляем остальные поля, если они указаны
        if attribute_data.description is not None:
            attribute.description = attribute_data.description
        if attribute_data.attribute_type is not None:
            attribute.attribute_type = attribute_data.attribute_type
        if attribute_data.is_required is not None:
            attribute.is_required = attribute_data.is_required
        if attribute_data.is_filterable is not None:
            attribute.is_filterable = attribute_data.is_filterable
        if attribute_data.default_value is not None:
            attribute.default_value = attribute_data.default_value
        if attribute_data.options is not None:
            attribute.options = attribute_data.options
        
        self.db.commit()
        self.db.refresh(attribute)
        
        return attribute

    def delete_template_attribute(self, attribute_id: int) -> bool:
        """
        Удаление атрибута шаблона
        
        Args:
            attribute_id: ID атрибута для удаления
            
        Returns:
            True, если атрибут успешно удален
            
        Raises:
            HTTPException: Если атрибут не найден
        """
        attribute = self.get_template_attribute_by_id(attribute_id)
        
        self.db.delete(attribute)
        self.db.commit()
        
        return True

    def get_template_specific_attributes(self, template_id: int) -> List[TemplateAttribute]:
        """
        Получение атрибутов, специфичных для шаблона (не включая атрибуты категории)
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Список атрибутов шаблона
            
        Raises:
            HTTPException: Если шаблон не найден
        """
        # Проверяем, что шаблон существует
        self.get_template_by_id(template_id)
        
        # Получаем атрибуты
        attributes = self.db.query(TemplateAttribute).filter(
            TemplateAttribute.template_id == template_id
        ).all()
        
        return attributes
        
    def get_template_images(self, template_id: int) -> List[Image]:
        """
        Получение изображений для шаблона предмета
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Список изображений
        """
        # Проверяем, что шаблон существует
        self.get_template_by_id(template_id)
        
        # Получаем изображения
        images = self.db.query(Image).filter(
            Image.entity_id == template_id,
            Image.type == ImageType.ITEM_TEMPLATE
        ).order_by(Image.order_index).all()
        
        return images 