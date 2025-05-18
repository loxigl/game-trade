"""
Pydantic схемы для валидации данных API
"""

from .base import PaginationParams, ErrorResponse, SuccessResponse
from .user import UserCreate, UserUpdate, UserResponse
from .categorization import (
    GameCreate, GameUpdate, GameResponse,
    ItemCategoryCreate, ItemCategoryUpdate, ItemCategoryResponse,
    CategoryAttributeCreate, CategoryAttributeUpdate, CategoryAttributeResponse,
    ItemTemplateCreate, ItemTemplateUpdate, ItemTemplateResponse,
    ItemCreate, ItemUpdate, ItemResponse,
    ItemAttributeValueCreate, ItemAttributeValueUpdate, ItemAttributeValueResponse
)
from .marketplace import (
    ListingCreate, ListingUpdate, ListingResponse,
    TransactionCreate, TransactionUpdate, TransactionResponse
)
from .search import (
    SearchParams, FilterParams, FilterOptions,
    GameFilterOption, CategoryFilterOption, AttributeFilterOption,
    PriceRangeOption, TrendingCategory
) 