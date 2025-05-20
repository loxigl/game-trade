from typing import Any, Generic, Optional, TypeVar, List, Dict
from pydantic import BaseModel, Field, computed_field, ConfigDict

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Параметры пагинации для API"""
    page: int = Field(1, ge=1, description="Номер страницы (от 1)")
    limit: int = Field(20, ge=1, le=100, description="Количество элементов на странице (от 1 до 100)")

    @computed_field
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "limit": 20
            }
        }
    )

class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой"""
    success: bool = Field(False, description="Статус выполнения (всегда False для ошибок)")
    error: str = Field(..., description="Сообщение об ошибке")
    code: int = Field(..., description="HTTP-код ошибки")
    details: Optional[Any] = Field(None, description="Дополнительная информация об ошибке")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "Ресурс не найден",
                "code": 404,
                "details": None
            }
        }
    )

class SuccessResponse(BaseModel, Generic[T]):
    """Схема успешного ответа"""
    success: bool = Field(default=True, description="Статус выполнения (всегда True для успешных запросов)")
    data: T = Field(..., description="Данные ответа")
    meta: Optional[Dict[str, Any]] = Field(None, description="Метаданные ответа")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {},
                "meta": {
                    "total": 100,
                    "page": 1,
                    "limit": 20
                }
            }
        }
    )