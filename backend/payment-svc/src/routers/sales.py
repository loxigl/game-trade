"""
Роутер для управления продажами маркетплейса
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status, Header, Body
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from ..database.connection import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User, Sale
from ..schemas.base import PaginationParams, SuccessResponse
from ..schemas.marketplace import PendingSaleResponse, PendingSaleListResponse
from ..services.sale_payment_service import SalePaymentService

router = APIRouter(
    prefix="/sales",
    tags=["sales"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)

class CompletionRequest(BaseModel):
    """Схема запроса для подтверждения завершения доставки"""
    comment: Optional[str] = None

class FundsReleaseRequest(BaseModel):
    """Схема запроса для вывода средств продавцом"""
    wallet_id: int
    withdrawal_details: Optional[Dict[str, Any]] = None

@router.post("/{sale_id}/initiate-payment", response_model=SuccessResponse[Dict[str, Any]])
async def initiate_payment(
    sale_id: int = Path(..., description="ID продажи"),
    wallet_id: int = Query(..., description="ID кошелька покупателя"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Инициировать платеж по продаже
    """
    payment_service = SalePaymentService(db)
    
    try:
        result = await payment_service.initiate_payment(
            sale_id=sale_id,
            wallet_id=wallet_id
        )
        
        return SuccessResponse(
            data=result,
            meta={"message": "Платеж успешно инициирован"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при инициировании платежа: {str(e)}"
        )

@router.post("/{sale_id}/confirm", response_model=SuccessResponse[Dict[str, Any]])
async def confirm_payment(
    sale_id: int = Path(..., description="ID продажи"),
    transaction_id: int = Query(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Подтвердить платеж по продаже
    """
    payment_service = SalePaymentService(db)
    
    try:
        result = await payment_service.confirm_payment(
            sale_id=sale_id,
            transaction_id=transaction_id
        )
        
        return SuccessResponse(
            data=result,
            meta={"message": "Платеж успешно подтвержден"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при подтверждении платежа: {str(e)}"
        )

@router.post("/{sale_id}/reject", response_model=SuccessResponse[Dict[str, Any]])
async def reject_payment(
    sale_id: int = Path(..., description="ID продажи"),
    transaction_id: int = Query(..., description="ID транзакции"),
    reason: Optional[str] = Query(None, description="Причина отклонения"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отклонить платеж по продаже
    """
    payment_service = SalePaymentService(db)
    
    try:
        result = await payment_service.reject_payment(
            sale_id=sale_id,
            transaction_id=transaction_id,
            reason=reason
        )
        
        return SuccessResponse(
            data=result,
            meta={"message": f"Платеж отклонен: {reason}" if reason else "Платеж отклонен"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отклонении платежа: {str(e)}"
        )

@router.get("/pending", response_model=SuccessResponse[PendingSaleListResponse])
async def get_pending_sales(
    pagination: PaginationParams = Depends(),
    seller_id: Optional[int] = Query(None, description="ID продавца"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка ожидающих подтверждения продаж с пагинацией
    """
    # Проверка прав доступа - пользователь должен запрашивать только свои продажи
    if seller_id and seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: вы можете просматривать только свои продажи"
        )
    
    # Если ID продавца не указан, используем ID текущего пользователя
    if not seller_id:
        seller_id = current_user.id
    
    # Получаем данные через сервис
    payment_service = SalePaymentService(db)
    result = await payment_service.get_pending_sales(
        seller_id=seller_id,
        page=pagination.page,
        page_size=pagination.limit
    )
    
    return SuccessResponse(data=result)

@router.get("/completed", response_model=SuccessResponse[PendingSaleListResponse])
async def get_completed_sales(
    pagination: PaginationParams = Depends(),
    seller_id: Optional[int] = Query(None, description="ID продавца"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка завершенных продаж с пагинацией
    """
    # Проверка прав доступа - пользователь должен запрашивать только свои продажи
    if seller_id and seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: вы можете просматривать только свои продажи"
        )
    
    # Если ID продавца не указан, используем ID текущего пользователя
    if not seller_id:
        seller_id = current_user.id
    
    # Получаем данные через сервис
    payment_service = SalePaymentService(db)
    result = await payment_service.get_completed_sales(
        seller_id=seller_id,
        page=pagination.page,
        page_size=pagination.limit
    )
    
    return SuccessResponse(data=result)

@router.post("/{sale_id}/complete-delivery", response_model=SuccessResponse[Dict[str, Any]])
async def complete_delivery(
    sale_id: int = Path(..., description="ID продажи"),
    transaction_id: int = Query(..., description="ID транзакции"),
    request_data: CompletionRequest = Body(..., description="Данные для завершения доставки"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Подтвердить завершение доставки и успешное выполнение заказа.
    Это действие:
    1. Изменяет статус оплаты
    2. Добавляет запись в статистику
    3. Открывает окно чата с продавцом для подтверждения
    """
    # Проверяем, что пользователь является покупателем данной продажи
    payment_service = SalePaymentService(db)
    
    try:
        result = await payment_service.complete_delivery(
            sale_id=sale_id,
            transaction_id=transaction_id,
            buyer_comment=request_data.comment
        )
        
        return SuccessResponse(
            data=result,
            meta={"message": "Доставка успешно подтверждена. Открыт чат с продавцом."}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при подтверждении доставки: {str(e)}"
        )

@router.post("/{sale_id}/release-funds", response_model=SuccessResponse[Dict[str, Any]])
async def release_funds(
    sale_id: int = Path(..., description="ID продажи"),
    transaction_id: int = Query(..., description="ID транзакции"),
    request_data: FundsReleaseRequest = Body(..., description="Данные для вывода средств"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Запрос продавца на вывод средств после завершения продажи и эскроу.
    Это действие:
    1. Проверяет, что продажа завершена
    2. Проверяет, что кошелек принадлежит продавцу
    3. Начисляет средства на баланс кошелька продавца
    4. Отправляет уведомление о выводе средств
    """
    payment_service = SalePaymentService(db)
    
    # Дополнительная проверка, что пользователь является продавцом
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.transaction_id == transaction_id
    ).first()
    
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продажа не найдена"
        )
    
    if sale.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: вы не являетесь продавцом этой продажи"
        )
    
    try:
        result = await payment_service.request_funds_release(
            sale_id=sale_id,
            transaction_id=transaction_id,
            wallet_id=request_data.wallet_id,
            withdrawal_details=request_data.withdrawal_details
        )
        
        return SuccessResponse(
            data=result,
            meta={"message": "Средства успешно зачислены на баланс кошелька"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выводе средств: {str(e)}"
        ) 