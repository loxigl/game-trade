from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict
from ..models.categorization import AttributeType

# === Game schemas ===
class GameBase(BaseModel):
    """Базовая схема игры"""
    name: str = Field(..., min_length=2, max_length=100, example="Counter-Strike: Global Offensive")
    description: Optional[str] = Field(None, max_length=1000, example="Популярный многопользовательский шутер с богатой экосистемой торговли скинами")
    logo_url: Optional[str] = Field(None, example="https://example.com/csgo-logo.png")
    is_active: Optional[bool] = Field(True, example=True)

class GameCreate(GameBase):
    """Схема для создания новой игры"""
    pass

class GameUpdate(BaseModel):
    """Схема для обновления информации об игре"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Counter-Strike 2")
    description: Optional[str] = Field(None, max_length=1000, example="Обновленная версия CS:GO с улучшенным графическим движком")
    logo_url: Optional[str] = Field(None, example="https://example.com/cs2-logo.png")
    is_active: Optional[bool] = Field(None, example=True)

class GameResponse(GameBase):
    """Схема для предоставления информации об игре"""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Counter-Strike: Global Offensive",
                "description": "Популярный многопользовательский шутер с богатой экосистемой торговли скинами",
                "logo_url": "https://example.com/csgo-logo.png",
                "is_active": True,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }
    )

# === ItemCategory schemas ===
class ItemCategoryBase(BaseModel):
    """Базовая схема категории предметов"""
    name: str = Field(..., min_length=2, max_length=100, example="Ножи")
    description: Optional[str] = Field(None, max_length=1000, example="Различные виды ножей в CS:GO")
    icon_url: Optional[str] = Field(None, example="https://example.com/knife-icon.png")
    parent_id: Optional[int] = Field(None, example=1, description="ID родительской категории")
    category_type: Optional[str] = Field("main", example="main", description="Тип категории: main или sub")
    order_index: Optional[int] = Field(0, example=1, description="Порядок отображения")

class ItemCategoryCreate(ItemCategoryBase):
    """Схема для создания категории предметов"""
    game_id: int = Field(..., example=1, description="ID игры, к которой относится категория")

class ItemCategoryUpdate(BaseModel):
    """Схема для обновления категории предметов"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Ножи")
    description: Optional[str] = Field(None, max_length=1000, example="Различные виды ножей в CS:GO")
    icon_url: Optional[str] = Field(None, example="https://example.com/knife-icon.png")
    parent_id: Optional[int] = Field(None, example=1, description="ID родительской категории")
    category_type: Optional[str] = Field(None, example="main", description="Тип категории: main или sub")
    order_index: Optional[int] = Field(None, example=1, description="Порядок отображения")

# Базовая схема ответа для категории без рекурсивных зависимостей
class ItemCategoryResponseBase(ItemCategoryBase):
    """Базовая схема для ответа с категорией предметов без рекурсии"""
    id: int
    game_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Схема для вложенной родительской категории (без subcategories)
class ParentCategoryResponse(ItemCategoryResponseBase):
    """Схема для родительской категории без подкатегорий"""
    pass

# Обновленная схема ответа с ограничением рекурсии
class ItemCategoryResponse(ItemCategoryResponseBase):
    """Схема для ответа с категорией предметов с ограниченной рекурсией"""
    subcategories: Optional[List['ItemCategoryResponse']] = None
    parent: Optional[ParentCategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)

ItemCategoryResponse.model_rebuild()

# === CategoryAttribute schemas ===
class CategoryAttributeBase(BaseModel):
    """Базовая схема атрибута категории"""
    name: str = Field(..., min_length=2, max_length=100, example="Редкость")
    description: Optional[str] = Field(None, max_length=1000, example="Уровень редкости предмета")
    attribute_type: AttributeType = Field(..., example=AttributeType.STRING)
    is_required: bool = Field(False, example=True)
    is_filterable: bool = Field(False, example=True)
    default_value: Optional[str] = Field(None, example="Обычный")
    options: Optional[str] = Field(None, example='["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный"]')

class CategoryAttributeCreate(CategoryAttributeBase):
    """Схема для создания нового атрибута категории"""
    category_id: int = Field(..., example=1)

class CategoryAttributeUpdate(BaseModel):
    """Схема для обновления атрибута категории"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Уровень редкости")
    description: Optional[str] = Field(None, max_length=1000, example="Классификация редкости предмета")
    attribute_type: Optional[AttributeType] = Field(None, example=AttributeType.ENUM)
    is_required: Optional[bool] = Field(None, example=True)
    is_filterable: Optional[bool] = Field(None, example=True)
    default_value: Optional[str] = Field(None, example="Обычный")
    options: Optional[str] = Field(None, example='["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный", "Древний"]')

class CategoryAttributeResponse(CategoryAttributeBase):
    """Схема для предоставления информации об атрибуте категории"""
    id: int = Field(..., example=1)
    category_id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "category_id": 1,
                "name": "Редкость",
                "description": "Уровень редкости предмета",
                "attribute_type": "enum",
                "is_required": True,
                "is_filterable": True,
                "default_value": "Обычный",
                "options": '["Обычный", "Необычный", "Редкий", "Мифический", "Легендарный"]',
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }
    )

# === TemplateAttribute schemas ===
class TemplateAttributeBase(BaseModel):
    """Базовая схема атрибута шаблона"""
    name: str = Field(..., min_length=2, max_length=100, example="Сила")
    description: Optional[str] = Field(None, max_length=1000, example="Показатель силы перчаток")
    attribute_type: AttributeType = Field(..., example=AttributeType.NUMBER)
    is_required: bool = Field(False, example=True)
    is_filterable: bool = Field(False, example=True)
    default_value: Optional[str] = Field(None, example="10")
    options: Optional[str] = Field(None, example='["5", "10", "15", "20", "25"]')

class TemplateAttributeCreate(TemplateAttributeBase):
    """Схема для создания нового атрибута шаблона"""
    template_id: int = Field(..., example=1)

class TemplateAttributeUpdate(BaseModel):
    """Схема для обновления атрибута шаблона"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Магическая сила")
    description: Optional[str] = Field(None, max_length=1000, example="Показатель магической силы перчаток")
    attribute_type: Optional[AttributeType] = Field(None, example=AttributeType.NUMBER)
    is_required: Optional[bool] = Field(None, example=True)
    is_filterable: Optional[bool] = Field(None, example=True)
    default_value: Optional[str] = Field(None, example="15")
    options: Optional[str] = Field(None, example='["5", "10", "15", "20", "25", "30"]')

class TemplateAttributeResponse(TemplateAttributeBase):
    """Схема для предоставления информации об атрибуте шаблона"""
    id: int = Field(..., example=1)
    template_id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "template_id": 1,
                "name": "Сила",
                "description": "Показатель силы перчаток",
                "attribute_type": "number",
                "is_required": True,
                "is_filterable": True,
                "default_value": "10",
                "options": '["5", "10", "15", "20", "25"]',
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }

# === ItemTemplate schemas ===
class ItemTemplateBase(BaseModel):
    """Базовая схема шаблона предметов"""
    name: str = Field(..., min_length=2, max_length=100, example="Керамбит | Градиент")
    description: Optional[str] = Field(None, max_length=1000, example="Изогнутый нож с градиентной раскраской")
    icon_url: Optional[str] = Field(None, example="https://example.com/karambit-fade.png")
    is_tradable: bool = Field(True, example=True)
    base_price: float = Field(0.0, ge=0.0, example=299.99)

class ItemTemplateCreate(ItemTemplateBase):
    """Схема для создания нового шаблона предметов"""
    category_id: int = Field(..., example=1)

class ItemTemplateUpdate(BaseModel):
    """Схема для обновления шаблона предметов"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Керамбит | Мраморный градиент")
    description: Optional[str] = Field(None, max_length=1000, example="Изогнутый нож с мраморной текстурой и градиентной раскраской")
    icon_url: Optional[str] = Field(None, example="https://example.com/karambit-marble-fade.png")
    is_tradable: Optional[bool] = Field(None, example=True)
    base_price: Optional[float] = Field(None, ge=0.0, example=349.99)

class ItemTemplateResponse(ItemTemplateBase):
    """Схема для предоставления информации о шаблоне предметов"""
    id: int = Field(..., example=1)
    category_id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")
    category: Optional[ItemCategoryResponseBase] = None
    attributes: Optional[List[Union[CategoryAttributeResponse, TemplateAttributeResponse]]] = []
    template_attributes: Optional[List[TemplateAttributeResponse]] = []

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "category_id": 1,
                "name": "Керамбит | Градиент",
                "description": "Изогнутый нож с градиентной раскраской",
                "icon_url": "https://example.com/karambit-fade.png",
                "is_tradable": True,
                "base_price": 299.99,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }
    )

# === ItemAttributeValue schemas ===
class ItemAttributeValueBase(BaseModel):
    """Базовая схема значения атрибута предмета"""
    attribute_id: int = Field(..., example=1)
    value_string: Optional[str] = Field(None, example="Легендарный")
    value_number: Optional[float] = Field(None, example=None)
    value_boolean: Optional[bool] = Field(None, example=None)

class ItemAttributeValueCreate(ItemAttributeValueBase):
    """Схема для создания нового значения атрибута предмета"""
    pass

class ItemAttributeValueUpdate(BaseModel):
    """Схема для обновления значения атрибута предмета"""
    value_string: Optional[str] = Field(None, example="Древний")
    value_number: Optional[float] = Field(None, example=None)
    value_boolean: Optional[bool] = Field(None, example=None)

class ItemAttributeValueResponse(ItemAttributeValueBase):
    """Схема для предоставления информации о значении атрибута предмета"""
    id: int = Field(..., example=1)
    item_id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "item_id": 1,
                "attribute_id": 1,
                "value_string": "Легендарный",
                "value_number": None,
                "value_boolean": None,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00"
            }
        }

# === Item schemas ===
class ItemBase(BaseModel):
    """Базовая схема предмета"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Керамбит | Градиент (Заводская новая)")
    condition: float = Field(100.0, ge=0.0, le=100.0, example=98.5)

class ItemCreate(ItemBase):
    """Схема для создания нового предмета"""
    template_id: int = Field(..., example=1)
    owner_id: int = Field(..., example=42)
    attribute_values: List[ItemAttributeValueCreate] = Field([], example=[])

class ItemUpdate(BaseModel):
    """Схема для обновления предмета"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, example="Керамбит | Градиент (Немного поношенное)")
    condition: Optional[float] = Field(None, ge=0.0, le=100.0, example=87.3)
    owner_id: Optional[int] = Field(None, example=43)

class ItemResponse(ItemBase):
    """Схема для предоставления информации о предмете"""
    id: int = Field(..., example=1)
    template_id: int = Field(..., example=1)
    owner_id: int = Field(..., example=42)
    created_at: datetime = Field(..., example="2025-01-01T00:00:00")
    updated_at: Optional[datetime] = Field(None, example="2025-01-02T00:00:00")
    attribute_values: List[ItemAttributeValueResponse] = Field([], example=[])

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "template_id": 1,
                "owner_id": 42,
                "name": "Керамбит | Градиент (Заводская новая)",
                "condition": 98.5,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00",
                "attribute_values": [
                    {
                        "id": 1,
                        "item_id": 1,
                        "attribute_id": 1,
                        "value_string": "Легендарный",
                        "value_number": None,
                        "value_boolean": None
                    }
                ]
            }
        }

# Схемы для атрибутов шаблонов
class CombinedAttributeValueResponse(BaseModel):
    """Схема ответа для объединенных значений атрибутов (категории и шаблона)"""
    id: Optional[int] = None  # ID значения атрибута (для существующих значений)
    attribute_id: Optional[int] = None  # ID атрибута категории
    template_attribute_id: Optional[int] = None  # ID атрибута шаблона
    attribute_name: str  # Название атрибута
    attribute_type: str  # Тип атрибута
    attribute_source: str  # Источник атрибута ("category" или "template")
    is_required: bool  # Обязательный ли атрибут
    value_string: Optional[str] = None
    value_number: Optional[float] = None
    value_boolean: Optional[bool] = None
    options: Optional[str] = None  # Возможные значения для enum

    class Config:
        from_attributes = True

# Существующая схема TemplateAttributeValueResponse
class TemplateAttributeValueResponse(BaseModel):
    """Схема ответа для значения атрибута шаблона"""
    attribute_id: int
    attribute_name: str
    attribute_type: str
    value_string: Optional[str] = None
    value_number: Optional[float] = None
    value_boolean: Optional[bool] = None

    class Config:
        from_attributes = True
