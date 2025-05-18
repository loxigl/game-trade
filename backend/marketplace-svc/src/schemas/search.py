"""
Pydantic схемы для поиска и фильтрации
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

class SearchParams(BaseModel):
    """Параметры поиска"""
    query: Optional[str] = Field(None, description="Текст поискового запроса")
    game_ids: Optional[List[int]] = Field(None, description="Список ID игр для фильтрации")
    category_ids: Optional[List[int]] = Field(None, description="Список ID категорий для фильтрации")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "керамбит",
                "game_ids": [1],
                "category_ids": [3, 4]
            }
        }

class FilterParams(BaseModel):
    """Параметры фильтрации"""
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Валюта (USD, EUR, и т.д.)")
    attributes: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        None,
        description="Словарь атрибутов для фильтрации (ID атрибута: значение)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "min_price": 50.0,
                "max_price": 500.0,
                "currency": "USD",
                "attributes": {
                    "1": "Легендарный",  # ID 1: значение "Легендарный" для атрибута "Редкость"
                    "2": True           # ID 2: значение True для атрибута "StatTrak™"
                }
            }
        }

class GameFilterOption(BaseModel):
    """Опция фильтрации по игре"""
    id: int
    name: str
    logo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class CategoryFilterOption(BaseModel):
    """Опция фильтрации по категории"""
    id: int
    name: str
    icon_url: Optional[str] = None
    game_id: int
    game_name: str
    
    class Config:
        from_attributes = True

class AttributeFilterOption(BaseModel):
    """Опция фильтрации по атрибуту"""
    id: int
    name: str
    type: str
    options: Optional[str] = None  # JSON строка с опциями для ENUM типа
    
    class Config:
        from_attributes = True

class PriceRangeOption(BaseModel):
    """Опция фильтрации по диапазону цен"""
    min: float
    max: float
    currencies: List[str]
    
    class Config:
        from_attributes = True

class FilterOptions(BaseModel):
    """Доступные опции фильтрации"""
    games: List[GameFilterOption]
    categories: List[CategoryFilterOption]
    attributes: List[AttributeFilterOption]
    price_range: PriceRangeOption
    
    class Config:
        from_attributes = True

class TrendingCategory(BaseModel):
    """Популярная категория"""
    id: int
    name: str
    icon_url: Optional[str] = None
    game_id: int
    game_name: str
    listings_count: int
    
    class Config:
        from_attributes = True 