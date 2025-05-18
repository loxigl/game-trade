"""
Сервис для работы с категориями предметов
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func

from ..models.categorization import ItemCategory, CategoryAttribute, Game, CategoryType
from ..schemas.categorization import (
    ItemCategoryCreate, ItemCategoryUpdate,
    CategoryAttributeCreate, CategoryAttributeUpdate
)
from ..schemas.base import PaginationParams

class CategoryService:
    """Сервис для управления категориями предметов"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
    
    def get_categories(
        self, 
        pagination: PaginationParams = None,
        game_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        category_type: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Получение списка категорий с фильтрацией и пагинацией
        
        Args:
            pagination: Параметры пагинации
            game_id: ID игры для фильтрации
            parent_id: ID родительской категории для фильтрации подкатегорий
            category_type: Тип категории (main/sub) для фильтрации
            search_query: Поисковый запрос
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
        
        Returns:
            Dict с ключами "items" (список категорий) и "meta" (мета-информация пагинации)
        """
        query = self.db.query(ItemCategory)
        
        # Фильтры
        if game_id:
            query = query.filter(ItemCategory.game_id == game_id)
        
        # Фильтр по родительской категории (None для корневых категорий)
        if parent_id is not None:
            query = query.filter(ItemCategory.parent_id == parent_id)
        
        # Фильтр по типу категории
        if category_type:
            query = query.filter(ItemCategory.category_type == category_type)
        
        # Поиск по названию и описанию
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                (ItemCategory.name.ilike(search_term)) |
                (ItemCategory.description.ilike(search_term))
            )
        
        # Подсчет общего количества записей
        total_count = query.count()
        
        # Сортировка
        if sort_by and hasattr(ItemCategory, sort_by):
            sort_column = getattr(ItemCategory, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # По умолчанию сортируем сначала по order_index, затем по name
            query = query.order_by(asc(ItemCategory.order_index), asc(ItemCategory.name))
        
        # Пагинация
        if pagination:
            query = query.offset(pagination.skip).limit(pagination.limit)
        
        categories = query.all()
        
        # Формируем мета-информацию о пагинации
        meta = {
            "total": total_count,
            "page": pagination.page if pagination else 1,
            "pages": (total_count + pagination.limit - 1) // pagination.limit if pagination else 1,
            "page_size": pagination.limit if pagination else len(categories)
        }
        
        return {
            "items": categories,
            "meta": meta
        }
    
    def get_category_by_id(self, category_id: int) -> ItemCategory:
        """
        Получение категории по ID
        
        Args:
            category_id: ID категории
        
        Returns:
            Объект категории
        
        Raises:
            HTTPException: Если категория не найдена
        """
        category = self.db.query(ItemCategory).filter(ItemCategory.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        return category
    
    def get_category_hierarchy(self, game_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение иерархии категорий в древовидной структуре
        
        Args:
            game_id: Optional ID игры для фильтрации категорий
        
        Returns:
            Древовидная структура категорий
        """
        # Получаем сначала все корневые категории (без parent_id)
        query = self.db.query(ItemCategory).filter(ItemCategory.parent_id == None)
        
        # Если указан ID игры, фильтруем по нему
        if game_id:
            query = query.filter(ItemCategory.game_id == game_id)
        
        # Сортируем по order_index и имени
        query = query.order_by(asc(ItemCategory.order_index), asc(ItemCategory.name))
        
        # Получаем корневые категории
        root_categories = query.all()
        
        # Рекурсивно строим дерево категорий
        result = []
        for category in root_categories:
            category_tree = self._build_category_tree(category)
            result.append(category_tree)
        
        return result
    
    def _build_category_tree(self, category: ItemCategory) -> Dict[str, Any]:
        """
        Рекурсивно строит дерево для категории и всех ее подкатегорий
        
        Args:
            category: Объект категории
        
        Returns:
            Словарь с данными категории и подкатегориями
        """
        # Сортируем подкатегории по order_index и имени
        subcategories = sorted(
            category.subcategories, 
            key=lambda x: (x.order_index, x.name)
        )
        
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "icon_url": category.icon_url,
            "game_id": category.game_id,
            "category_type": category.category_type,
            "order_index": category.order_index,
            "parent_id": category.parent_id,
            "subcategories": [
                self._build_category_tree(subcat) for subcat in subcategories
            ]
        }
    
    def create_category(self, category_data: ItemCategoryCreate) -> ItemCategory:
        """
        Создание новой категории
        
        Args:
            category_data: Данные для создания категории
        
        Returns:
            Созданная категория
        """
        # Проверяем существование игры
        game = self.db.query(Game).filter(Game.id == category_data.game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Игра не найдена"
            )
        
        # Если указана родительская категория, проверяем ее существование
        if category_data.parent_id:
            parent_category = self.db.query(ItemCategory).filter(
                ItemCategory.id == category_data.parent_id
            ).first()
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Родительская категория не найдена"
                )
            
            # Убеждаемся, что родительская категория относится к той же игре
            if parent_category.game_id != category_data.game_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Родительская категория должна относиться к той же игре"
                )
            
            # Устанавливаем тип подкатегории, если не указан явно
            if not category_data.category_type:
                category_data.category_type = CategoryType.SUB
        
        # Создаем новую категорию
        category_dict = category_data.dict()
        new_category = ItemCategory(**category_dict)
        self.db.add(new_category)
        
        try:
            self.db.commit()
            self.db.refresh(new_category)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка при создании категории: {str(e)}"
            )
        
        return new_category
    
    def update_category(self, category_id: int, category_data: ItemCategoryUpdate) -> ItemCategory:
        """
        Обновление категории
        
        Args:
            category_id: ID категории для обновления
            category_data: Данные для обновления
        
        Returns:
            Обновленная категория
        """
        # Проверяем существование категории
        category = self.get_category_by_id(category_id)
        
        # Проверяем родительскую категорию, если указана
        if category_data.parent_id is not None:
            # Если устанавливается в None, значит категория становится корневой
            if category_data.parent_id == 0:
                category_data.parent_id = None
                # Если явно не указан тип, устанавливаем MAIN для корневой категории
                if not category_data.category_type:
                    category_data.category_type = CategoryType.MAIN
            else:
                # Проверяем существование родительской категории
                parent_category = self.db.query(ItemCategory).filter(
                    ItemCategory.id == category_data.parent_id
                ).first()
                if not parent_category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Родительская категория не найдена"
                    )
                
                # Убеждаемся, что родительская категория относится к той же игре
                if parent_category.game_id != category.game_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Родительская категория должна относиться к той же игре"
                    )
                
                # Проверяем на циклические зависимости
                if category_id == category_data.parent_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Категория не может быть родительской для самой себя"
                    )
                
                # Проверяем, что родительская категория не является дочерней для текущей
                if self._is_descendant(category_id, category_data.parent_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Циклическая зависимость в иерархии категорий"
                    )
                
                # Если явно не указан тип, устанавливаем SUB для подкатегории
                if not category_data.category_type:
                    category_data.category_type = CategoryType.SUB
        
        # Обновляем категорию
        update_data = category_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(category)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка при обновлении категории: {str(e)}"
            )
        
        return category
    
    def _is_descendant(self, parent_id: int, child_id: int) -> bool:
        """
        Проверяет, является ли категория с child_id потомком категории с parent_id
        
        Args:
            parent_id: ID предполагаемого родителя
            child_id: ID предполагаемого потомка
        
        Returns:
            True, если child_id является потомком parent_id, иначе False
        """
        child = self.db.query(ItemCategory).filter(ItemCategory.id == child_id).first()
        if not child:
            return False
        
        # Проверяем всех предков child_id
        current_id = child.parent_id
        visited = set()
        
        while current_id is not None and current_id not in visited:
            if current_id == parent_id:
                return True
            
            visited.add(current_id)
            current = self.db.query(ItemCategory).filter(ItemCategory.id == current_id).first()
            if not current:
                break
            
            current_id = current.parent_id
        
        return False
    
    def delete_category(self, category_id: int) -> bool:
        """
        Удаление категории
        
        Args:
            category_id: ID категории для удаления
        
        Returns:
            True в случае успеха
        """
        # Проверяем существование категории
        category = self.get_category_by_id(category_id)
        
        # Проверяем, есть ли подкатегории
        subcategories = self.db.query(ItemCategory).filter(ItemCategory.parent_id == category_id).all()
        if subcategories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить категорию с подкатегориями. Сначала удалите все подкатегории."
            )
        
        # Проверяем, есть ли шаблоны предметов в категории
        from ..models.categorization import ItemTemplate
        templates = self.db.query(ItemTemplate).filter(ItemTemplate.category_id == category_id).all()
        if templates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить категорию, содержащую шаблоны предметов. Сначала удалите все шаблоны."
            )
        
        # Удаляем атрибуты категории
        self.db.query(CategoryAttribute).filter(CategoryAttribute.category_id == category_id).delete()
        
        # Удаляем саму категорию
        self.db.delete(category)
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка при удалении категории: {str(e)}"
            )
        
        return True
    
    def get_category_attributes(self, category_id: int) -> List[CategoryAttribute]:
        """
        Получение атрибутов категории
        
        Args:
            category_id: ID категории
            
        Returns:
            Список атрибутов категории
            
        Raises:
            HTTPException: Если категория не найдена
        """
        # Проверяем, что категория существует
        self.get_category_by_id(category_id)
        
        # Получаем атрибуты
        attributes = self.db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category_id
        ).all()
        
        return attributes
    
    def get_attribute_by_id(self, attribute_id: int) -> CategoryAttribute:
        """
        Получение атрибута по ID
        
        Args:
            attribute_id: ID атрибута
            
        Returns:
            Объект атрибута
            
        Raises:
            HTTPException: Если атрибут не найден
        """
        attribute = self.db.query(CategoryAttribute).filter(
            CategoryAttribute.id == attribute_id
        ).first()
        
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Атрибут не найден"
            )
        
        return attribute
    
    def create_attribute(self, attribute_data: CategoryAttributeCreate) -> CategoryAttribute:
        """
        Создание нового атрибута категории
        
        Args:
            attribute_data: Данные для создания атрибута
            
        Returns:
            Созданный атрибут
            
        Raises:
            HTTPException: Если категория не найдена или атрибут с таким именем уже существует
        """
        # Проверяем, что категория существует
        self.get_category_by_id(attribute_data.category_id)
        
        # Проверяем, что атрибут с таким именем не существует для данной категории
        existing_attribute = self.db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == attribute_data.category_id,
            func.lower(CategoryAttribute.name) == func.lower(attribute_data.name)
        ).first()
        
        if existing_attribute:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Атрибут с таким именем уже существует для данной категории"
            )
        
        # Создаем объект атрибута
        attribute = CategoryAttribute(
            category_id=attribute_data.category_id,
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
    
    def update_attribute(
        self, 
        attribute_id: int, 
        attribute_data: CategoryAttributeUpdate
    ) -> CategoryAttribute:
        """
        Обновление существующего атрибута
        
        Args:
            attribute_id: ID атрибута для обновления
            attribute_data: Новые данные атрибута
            
        Returns:
            Обновленный атрибут
            
        Raises:
            HTTPException: Если атрибут не найден или новое имя уже занято
        """
        attribute = self.get_attribute_by_id(attribute_id)
        
        # Если изменяется имя, проверяем, что новое имя не занято
        if attribute_data.name is not None and attribute_data.name != attribute.name:
            existing_attribute = self.db.query(CategoryAttribute).filter(
                CategoryAttribute.category_id == attribute.category_id,
                func.lower(CategoryAttribute.name) == func.lower(attribute_data.name),
                CategoryAttribute.id != attribute_id
            ).first()
            
            if existing_attribute:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Атрибут с таким именем уже существует для данной категории"
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
    
    def delete_attribute(self, attribute_id: int) -> bool:
        """
        Удаление атрибута
        
        Args:
            attribute_id: ID атрибута для удаления
            
        Returns:
            True, если атрибут успешно удален
            
        Raises:
            HTTPException: Если атрибут не найден
        """
        attribute = self.get_attribute_by_id(attribute_id)
        
        self.db.delete(attribute)
        self.db.commit()
        
        return True 