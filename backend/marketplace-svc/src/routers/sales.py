"""
API роутер для работы с продажами
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database.connection import get_db
from ..services.sale_service import SaleService
from ..models.core import SaleStatus
from ..schemas.sales import (
    SaleResponse,
    SaleListResponse,
    SaleStatusUpdate
)
from ..dependencies import get_current_user
from ..models.core import User

router = APIRouter(
    prefix="/sales",
    tags=["sales"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/{listing_id}/initiate", response_model=SaleResponse)
async def initiate_sale(
    listing_id: int,
    test_mode: bool = Query(False, description="Использовать тестовый режим с автоматической генерацией transaction_id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Инициировать продажу товара
    
    Args:
        listing_id: ID объявления
        test_mode: Использовать тестовый режим (автоматически создает transaction_id)
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Информация о созданной продаже
        
    Raises:
        HTTPException: Если объявление не найдено или недоступно для покупки
    """
    logger = logging.getLogger(__name__)
    try:
        sale_service = SaleService(db)
        logger.info(f"Инициация продажи для listing_id={listing_id} пользователем id={current_user.id} (test_mode={test_mode})")
        sale = await sale_service.initiate_sale(
            listing_id=listing_id,
            buyer_id=current_user.id,
            test_mode=test_mode
        )
        logger.info(f"Продажа успешно создана: {sale}")
        
        # Явно валидируем ответ перед возвратом
        try:
            sale_response = SaleResponse.model_validate(sale)
            return sale_response
        except Exception as validate_err:
            logger.error(f"Ошибка валидации ответа: {str(validate_err)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при формировании ответа: {str(validate_err)}")
            
    except ValueError as e:
        logger.error(f"Ошибка валидации при инициации продажи: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Внутренняя ошибка при инициации продажи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о продаже
    
    Args:
        sale_id: ID продажи
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Информация о продаже
        
    Raises:
        HTTPException: Если продажа не найдена или пользователь не имеет к ней доступа
    """
    try:
        sale_service = SaleService(db)
        sale = await sale_service.get_sale(
            sale_id=sale_id,
            user_id=current_user.id
        )
        return sale
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.get("/", response_model=SaleListResponse)
async def get_user_sales(
    role: str = Query("buyer", enum=["buyer", "seller"]),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить список продаж пользователя
    
    Args:
        role: Роль пользователя в продажах ("buyer" или "seller")
        status: Фильтр по статусу (опционально)
        page: Номер страницы
        page_size: Размер страницы
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список продаж с информацией о пагинации
    """
    try:
        sale_service = SaleService(db)
        sales = await sale_service.get_user_sales(
            user_id=current_user.id,
            role=role,
            status=status,
            page=page,
            page_size=page_size
        )
        return sales
    except Exception as e:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.put("/{sale_id}/status", response_model=SaleResponse)
async def update_sale_status(
    sale_id: int,
    status_update: SaleStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновить статус продажи
    
    Args:
        sale_id: ID продажи
        status_update: Новый статус и причина изменения
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Обновленная информация о продаже
        
    Raises:
        HTTPException: Если продажа не найдена или пользователь не имеет прав на изменение статуса
    """
    try:
        sale_service = SaleService(db)
        sale = await sale_service.update_sale_status(
            sale_id=sale_id,
            user_id=current_user.id,
            new_status=status_update.status,
            reason=status_update.reason
        )
        return sale
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера") 