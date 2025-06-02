"""
API маршруты для работы с транзакциями
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Header, Request, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
import httpx

from ..schemas.transaction_history import TransactionHistoryResponse
from ..services.transaction_history_service import TransactionHistoryService
from ..database.connection import get_db
from ..models.transaction import TransactionStatus, TransactionType
from ..schemas.transaction import (
    TransactionBase, TransactionCreate, TransactionUpdate, 
    TransactionResponse, TransactionListResponse, TransactionStatusUpdate, TransactionDisputeCreate,
    TransactionActionResponse, TransactionDetailsResponse
)
from ..services.transaction_service import get_transaction_service
from ..services.transaction_state_service import get_transaction_state_service
from ..services.idempotency_service import get_idempotency_service
from ..services.sales_service import get_sales_service
from ..dependencies.auth import User, get_current_active_user, AuthService, get_current_user
from ..models.core import Sale, User
from ..config import get_settings


settings = get_settings()

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Транзакция не найдена"},
        409: {"description": "Конфликт состояния транзакции"},
        422: {"description": "Ошибка валидации данных"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)

logger = logging.getLogger(__name__)

# Функция для получения информации о пользователе из auth-сервиса
async def get_user_by_id(user_id: int) -> Dict[str, Any]:
    """
    Получает информацию о пользователе из auth-сервиса по его ID
    """
    try:
        auth_service_url = settings.AUTH_SERVICE_URL
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{auth_service_url}/users/{user_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Ошибка при получении пользователя с ID {user_id}: {response.status_code}")
                return None
    except Exception as e:
        logging.error(f"Ошибка при запросе к auth-сервису: {str(e)}")
        return None


@router.get("/debug-auth", tags=["debug"])
async def debug_auth(request: Request):
    """Эндпоинт для отладки авторизации"""
    auth_header = request.headers.get("Authorization", "не найден")
    
    user_info = None
    try:
        user_info = await AuthService.get_current_user(request)
    except Exception as e:
        return {
            "auth_header": auth_header,
            "error": str(e),
            "current_user": None
        }
    
    return {
        "auth_header": auth_header[:20] + "..." if len(auth_header) > 20 else auth_header,
        "current_user": user_info.dict() if user_info else None
    }


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание транзакции",
    description="""
    Создает новую транзакцию в системе.
    
    - Поддерживает различные типы транзакций (покупка, продажа, перевод и т.д.)
    - Требует указания суммы, валюты и описания
    - Может включать дополнительные метаданные
    - Поддерживает идемпотентность через X-Idempotency-Key
    - Автоматически проверяет права доступа и валидирует данные
    """
)
async def create_transaction(
    transaction_data: TransactionCreate = Body(..., description="Данные для создания транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создать новую транзакцию
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="create_transaction"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        transaction_service = get_transaction_service(db)
        transaction = await transaction_service.create_transaction(transaction_data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка создания транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при создании транзакции"
        )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Получение транзакции",
    description="""
    Возвращает информацию о конкретной транзакции.
    
    - Включает полную информацию о транзакции, включая статус и историю
    - Проверяет права доступа (пользователь может видеть только свои транзакции)
    - Администраторы могут видеть любые транзакции
    - Если транзакция не найдена, возвращает ошибку 404
    """
)
async def get_transaction(
    transaction_id: int = Path(..., description="ID транзакции"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о транзакции по ID
    """
    try:
        transaction_service = get_transaction_service(db)
        transaction = await transaction_service.get_transaction(transaction_id)
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Транзакция с ID {transaction_id} не найдена"
            )
        
        return transaction
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Ошибка при получении транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при получении транзакции"
        )


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="Получение списка транзакций",
    description="""
    Возвращает список транзакций с пагинацией и фильтрацией.
    
    - Поддерживает фильтрацию по пользователю и статусу
    - Результаты сортируются по дате создания (новые сверху)
    - Обычные пользователи могут видеть только свои транзакции
    - Администраторы могут видеть все транзакции
    - Поддерживает пагинацию с ограничением размера страницы
    """
)
async def get_transactions(
    user_id: Optional[int] = Query(None, description="ID пользователя (покупателя или продавца)"),
    status_filter: Optional[TransactionStatus] = Query(None, description="Статус транзакций", alias="status"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(10, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    role: Optional[str] = Query(None, description="Роль пользователя"),
    is_seller_view: bool = Query(False, description="Вид транзакций продавца")
):
    """
    Получить список транзакций с фильтрацией и пагинацией
    """
    try:
        if is_seller_view:
            role = "seller"
        else:
            role = "buyer"
        transaction_service = get_transaction_service(db)
        
        # Получаем транзакции с учетом пагинации
        if not user_id:
            user_id=current_user.id
            
        
        transactions = await transaction_service.get_user_transactions(
                user_id=user_id, 
                status=status_filter,
                skip=(page - 1) * page_size,
                limit=page_size,
                role=role
        )
        total = await transaction_service.count_user_transactions(user_id=user_id, status=status_filter,role=role)
        # Формируем ответ с пагинацией
        return {
            "items": transactions,
            "total": total,
            "page": page,
            "size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size > 0 else 0
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка транзакций: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при получении списка транзакций"
        )


@router.get(
    "/{transaction_id}/actions",
    response_model=TransactionActionResponse,
    summary="Получение доступных действий",
    description="""
    Возвращает список доступных действий для транзакции.
    
    - Действия зависят от текущего статуса транзакции
    - Учитывает права доступа пользователя
    - Может включать действия: подтверждение, отмена, открытие спора и т.д.
    - Если транзакция не найдена, возвращает ошибку 404
    """
)
async def get_available_actions(
    transaction_id: int = Path(..., description="ID транзакции"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получить список доступных действий для транзакции
    """
    try:
        transaction_state_service = get_transaction_state_service(db)
        actions = await transaction_state_service.get_available_actions(transaction_id)
        
        return {"actions": actions}
    except ValueError as e:
        logger.error(f"Ошибка получения доступных действий: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении доступных действий: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при получении доступных действий"
        )


@router.post(
    "/{transaction_id}/escrow",
    response_model=TransactionResponse,
    summary="Обработка платежа через эскроу",
    description="""
    Обрабатывает платеж через систему эскроу.
    
    - Переводит средства в эскроу
    - Требует подтверждения от обеих сторон
    - Поддерживает идемпотентность
    - Проверяет права доступа и состояние транзакции
    - Возвращает обновленную информацию о транзакции
    """
)
async def process_escrow_payment(
    transaction_id: int = Path(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    data: Dict[str, Any] = Body(None, description="Дополнительные данные для обработки платежа"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Перевести средства в Escrow для транзакции
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="process_escrow_payment"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.process_payment(transaction_id, data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка перевода средств в Escrow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при переводе средств в Escrow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при переводе средств в Escrow"
        )


@router.post("/{transaction_id}/complete", response_model=TransactionResponse)
async def complete_transaction(
    transaction_id: int = Path(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    data: Dict[str, Any] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Завершить транзакцию и перевести средства продавцу
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="complete_transaction"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.complete_transaction(transaction_id, data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка завершения транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при завершении транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при завершении транзакции"
        )


@router.post("/{transaction_id}/refund", response_model=TransactionResponse)
async def refund_transaction(
    transaction_id: int = Path(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    status_update: TransactionStatusUpdate = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отменить транзакцию и вернуть средства покупателю
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="refund_transaction"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        data = {"reason": status_update.reason} if status_update and status_update.reason else None
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.refund_transaction(transaction_id, data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка возврата средств: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате средств: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при возврате средств"
        )


@router.post(
    "/{transaction_id}/dispute",
    response_model=TransactionResponse,
    summary="Открытие спора",
    description="""
    Открывает спор по транзакции.
    
    - Требует указания причины спора
    - Блокирует средства в эскроу
    - Уведомляет обе стороны о споре
    - Поддерживает идемпотентность
    - Проверяет возможность открытия спора
    """
)
async def dispute_transaction(
    transaction_id: int = Path(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    dispute_data: TransactionDisputeCreate = Body(None, description="Данные для открытия спора"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Открыть спор по транзакции
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="dispute_transaction"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        data = {"reason": dispute_data.reason} if dispute_data and dispute_data.reason else None
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.dispute_transaction(transaction_id, data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка открытия спора: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при открытии спора: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при открытии спора"
        )


@router.post(
    "/{transaction_id}/resolve",
    response_model=TransactionResponse,
    summary="Разрешение спора",
    description="""
    Разрешает спор по транзакции.
    
    - Требует указания решения (в пользу продавца или покупателя)
    - Может включать комментарий к решению
    - Выполняет перевод средств согласно решению
    - Поддерживает идемпотентность
    - Доступно только администраторам
    """
)
async def resolve_dispute(
    transaction_id: int = Path(..., description="ID транзакции"),
    in_favor_of_seller: bool = Query(..., description="Решение в пользу продавца (true) или покупателя (false)"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    dispute_resolution: TransactionDisputeCreate = Body(None, description="Данные для разрешения спора"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Разрешить спор по транзакции
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="resolve_dispute"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        data = {"reason": dispute_resolution.reason, "resolution": "seller" if in_favor_of_seller else "buyer"} if dispute_resolution else {"resolution": "seller" if in_favor_of_seller else "buyer"}
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.resolve_dispute(
            transaction_id, in_favor_of_seller, data
        )
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка разрешения спора: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при разрешении спора: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при разрешении спора"
        )


@router.post("/{transaction_id}/cancel", response_model=TransactionResponse)
async def cancel_transaction(
    transaction_id: int = Path(..., description="ID транзакции"),
    x_idempotency_key: Optional[str] = Header(None, description="Ключ идемпотентности для предотвращения дублирования операций"),
    status_update: TransactionStatusUpdate = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отменить транзакцию
    """
    # Проверка идемпотентности
    if x_idempotency_key:
        idempotency_service = get_idempotency_service(db)
        existing_response = await idempotency_service.check_and_save(
            idempotency_key=x_idempotency_key,
            operation_type="cancel_transaction"
        )
        
        if existing_response:
            logger.info(f"Возвращаем результат предыдущей операции для ключа {x_idempotency_key}")
            return existing_response
    
    try:
        data = {"reason": status_update.reason} if status_update and status_update.reason else None
        transaction_state_service = get_transaction_state_service(db)
        transaction = await transaction_state_service.cancel_transaction(transaction_id, data)
        
        # Сохраняем ответ для идемпотентности
        if x_idempotency_key:
            idempotency_service = get_idempotency_service(db)
            # Создаем и сериализуем объект Pydantic вместо __dict__
            transaction_response = TransactionResponse.model_validate(transaction)
            await idempotency_service.save_response(x_idempotency_key, transaction_response.model_dump())
        
        return transaction
    except ValueError as e:
        logger.error(f"Ошибка отмены транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене транзакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при отмене транзакции"
        )


@router.get(
    "/{transaction_id}/details",
    response_model=TransactionDetailsResponse,
    summary="Получение детальной информации о транзакции",
    description="""
    Возвращает подробную информацию о транзакции, включая данные об участниках и товаре.
    
    - Содержит полную информацию о транзакции, участниках сделки и товаре
    - Включает историю изменений статусов транзакции
    - Предоставляет доступные действия для текущего статуса
    - Содержит информацию об Escrow
    - Поддерживает данные о связанной продаже, если она существует
    """
)
async def get_transaction_details(
    transaction_id: int = Path(..., description="ID транзакции"),
    current_user: User = Depends(get_current_active_user),
    current_user_info:str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TransactionDetailsResponse:
    token = current_user_info.token
    # Получаем основную информацию о транзакции
    transaction_service = get_transaction_service(db)
    transaction = await transaction_service.get_transaction(transaction_id)
    logger.info(f"Транзакция: {transaction}")
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транзакция не найдена"
        )
    
    # Проверяем права доступа (пользователь должен быть покупателем или продавцом)
    if transaction.buyer_id != current_user.id and transaction.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой транзакции"
        )
    
    # Получаем историю транзакции
    history_service = TransactionHistoryService(db)
    history = history_service.get_transaction_timeline(transaction_id)
    
    
    # Получаем информацию о продавце из auth-сервиса
    seller = None
    if transaction.seller_id:
        try:
            seller_data = await get_user_by_id(transaction.seller_id)
            if seller_data:
                seller = {
                    "id": seller_data.get("id"),
                    "username": seller_data.get("username"),
                    "email": seller_data.get("email"),
                    "avatar": seller_data.get("profile", {}).get("avatar_url"),
                    "rating": seller_data.get("profile", {}).get("rating", 0),
                    "registration_date": seller_data.get("created_at"),
                    "verified": seller_data.get("is_verified", False),
                    "total_sales": seller_data.get("profile", {}).get("total_sales", 0),
                    "contacts": seller_data.get("profile", {}).get("contacts", {}),
                }
        except Exception as e:
            logging.error(f"Не удалось получить информацию о продавце: {str(e)}")
    
    # Получаем информацию о покупателе из auth-сервиса
    buyer = None
    if transaction.buyer_id:
        try:
            buyer_data = await get_user_by_id(transaction.buyer_id)
            if buyer_data:
                buyer = {
                    "id": buyer_data.get("id"),
                    "username": buyer_data.get("username"),
                    "email": buyer_data.get("email"),
                    "avatar": buyer_data.get("profile", {}).get("avatar_url"),
                    "rating": buyer_data.get("profile", {}).get("rating", 0),
                    "registration_date": buyer_data.get("created_at"),
                    "verified": buyer_data.get("is_verified", False),
                    "total_purchases": buyer_data.get("profile", {}).get("total_purchases", 0),
                    "contacts": buyer_data.get("profile", {}).get("contacts", {}),
                }
        except Exception as e:
            logging.error(f"Не удалось получить информацию о покупателе: {str(e)}")
    
    # Получаем информацию о товаре через API marketplace
    item_details = None
    listing_id = transaction.listing_id
    if listing_id:
        try:
            marketplace_service_url = settings.MARKETPLACE_SERVICE_URL
            logger.info(f"Попытка получить информацию о товаре. ID листинга: {listing_id}, URL: {marketplace_service_url}")
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                response = await client.get(f"{marketplace_service_url}/listings/{listing_id}",headers=headers)
                
                if response.status_code == 200:
                    listing_data = response.json()
                    item_details = {
                        "id": listing_data.get("id"),
                        "title": listing_data.get("title"),
                        "description": listing_data.get("description"),
                        "price": listing_data.get("price"),
                        "currency": listing_data.get("currency"),
                        "category": listing_data.get("category"),
                        "condition": listing_data.get("condition"),
                        "images": listing_data.get("images", [])[:3],  # Первые 3 изображения
                        "created_at": listing_data.get("created_at"),
                        "tags": listing_data.get("tags", []),
                        "location": listing_data.get("location"),
                    }
        except Exception as e:
            logging.error(f"Не удалось получить информацию о товаре: {str(e)}")
    
    # Получаем информацию о продаже, если она связана с транзакцией
    sale = None
    if transaction.extra_data and "sale_id" in transaction.extra_data:
        try:
            sale_id = int(transaction.extra_data["sale_id"])
            
            # Получаем детали продажи через API marketplace
            marketplace_service_url = settings.MARKETPLACE_SERVICE_URL
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                response = await client.get(f"{marketplace_service_url}/sales/{sale_id}",headers=headers)
                if response.status_code == 200:
                    sale = response.json()
        except Exception as e:
            logger.info(f"url: {marketplace_service_url}/sales/{sale_id}")
            logging.error(f"Не удалось получить информацию о продаже: {str(e)}")

    
    # Информация об эскроу
    escrow_info = {
        "is_in_escrow": transaction.status == TransactionStatus.ESCROW_HELD,
        "days_in_escrow": None,
        "escrow_start_date": transaction.escrow_held_at.isoformat() if getattr(transaction, 'escrow_held_at', None) else None,
        "escrow_end_date": None,
        "wallet_id": getattr(transaction, 'wallet_id', None)
    }
    
    if getattr(transaction, 'escrow_held_at', None):
        from datetime import datetime
        days_in_escrow = (datetime.now(timezone.utc) - transaction.escrow_held_at).days
        escrow_info["days_in_escrow"] = days_in_escrow
        
        # Вычисляем предполагаемую дату завершения Escrow (если применимо)
        if getattr(transaction, 'expiration_date', None):
            escrow_info["escrow_end_date"] = transaction.expiration_date.isoformat()
    
    # Информация о сроках
    time_info = {
        "is_expired": False,
        "days_left": None,
        "created_date": transaction.created_at.isoformat() if getattr(transaction, 'created_at', None) else None,
        "updated_date": transaction.updated_at.isoformat() if getattr(transaction, 'updated_at', None) else None,
        "completed_date": transaction.completed_at.isoformat() if getattr(transaction, 'completed_at', None) else None,
        "expiration_date": transaction.expiration_date.isoformat() if getattr(transaction, 'expiration_date', None) else None,
    }
    
    if getattr(transaction, 'expiration_date', None):
        days_left = (transaction.expiration_date - datetime.now(timezone.utc)).days
        time_info["days_left"] = days_left
        time_info["is_expired"] = days_left < 0
    
    # Определение доступных действий
    transaction_state_service = get_transaction_state_service(db)
    available_actions = await transaction_state_service.get_available_actions(transaction_id)
    
    # Статус действий
    action_status = {
        "can_complete": "complete" in available_actions,
        "can_refund": "refund" in available_actions,
        "can_dispute": "dispute" in available_actions,
        "can_cancel": "cancel" in available_actions,
        "can_resolve_dispute": "resolve_dispute" in available_actions and current_user.is_admin,
    }
    
    # Дополнительная информация о платеже
    payment_info = {
        "amount": float(transaction.amount) if getattr(transaction, 'amount', None) else 0.0,
        "currency": getattr(transaction, 'currency', 'USD'),
        "fee_amount": float(transaction.fee_amount) if getattr(transaction, 'fee_amount', None) else 0.0,
        "fee_percentage": float(transaction.fee_percentage) if getattr(transaction, 'fee_percentage', None) else 0.0,
        "total_amount": float(transaction.amount) if getattr(transaction, 'amount', None) else 0.0,
        "payment_method": "wallet",  # По умолчанию
        "transaction_uid": str(transaction.transaction_uid) if getattr(transaction, 'transaction_uid', None) else None,
    }
    
    # Преобразуем объект транзакции в словарь
    transaction_dict = {
        "id": transaction.id,
        "transaction_uid": str(transaction.transaction_uid) if getattr(transaction, 'transaction_uid', None) else None,
        "buyer_id": getattr(transaction, 'buyer_id', None),
        "seller_id": getattr(transaction, 'seller_id', None),
        "listing_id": getattr(transaction, 'listing_id', None),
        "item_id": getattr(transaction, 'item_id', None),
        "amount": float(transaction.amount) if getattr(transaction, 'amount', None) else 0.0,
        "currency": getattr(transaction, 'currency', 'USD'),
        "fee_amount": float(transaction.fee_amount) if getattr(transaction, 'fee_amount', None) is not None else 0,
        "fee_percentage": float(transaction.fee_percentage) if getattr(transaction, 'fee_percentage', None) is not None else 0,
        "status": getattr(transaction, 'status', TransactionStatus.PENDING).value,
        "type": getattr(transaction, 'type', None).value if getattr(transaction, 'type', None) else None,
        "created_at": transaction.created_at.isoformat() if getattr(transaction, 'created_at', None) else None,
        "updated_at": transaction.updated_at.isoformat() if getattr(transaction, 'updated_at', None) else None,
        "completed_at": transaction.completed_at.isoformat() if getattr(transaction, 'completed_at', None) else None,
        "disputed_at": transaction.disputed_at.isoformat() if getattr(transaction, 'disputed_at', None) else None,
        "refunded_at": transaction.refunded_at.isoformat() if getattr(transaction, 'refunded_at', None) else None,
        "canceled_at": transaction.canceled_at.isoformat() if getattr(transaction, 'canceled_at', None) else None,
        "escrow_held_at": transaction.escrow_held_at.isoformat() if getattr(transaction, 'escrow_held_at', None) else None,
        "description": getattr(transaction, 'description', None),
        "notes": getattr(transaction, 'notes', None),
        "extra_data": getattr(transaction, 'extra_data', None),
        "dispute_reason": getattr(transaction, 'dispute_reason', None),
        "refund_reason": getattr(transaction, 'refund_reason', None),
        "cancel_reason": getattr(transaction, 'cancel_reason', None),
    }
    
    # Преобразуем историю транзакций
    history_data = []
    if history:
        for item in history:
            # Определяем тип действия на основе изменения статуса
            action = "status_change"
            if getattr(item, 'previous_status', None) is None and getattr(item, 'new_status', None) == TransactionStatus.PENDING:
                action = "create"
            
            history_data.append({
                "id": getattr(item, 'id', None),
                "transaction_id": getattr(item, 'transaction_id', None),
                "action": action,
                "from_status": getattr(item, 'previous_status', None),
                "to_status": getattr(item, 'new_status', None),
                "timestamp": item.timestamp.isoformat() if getattr(item, 'timestamp', None) else None,
                "user_id": getattr(item, 'initiator_id', None),
                "notes": getattr(item, 'reason', None),
                "metadata": getattr(item, 'extra_data', None)
            })
    
    # Формируем полный ответ
    return {
        "transaction": transaction_dict,
        "history": history_data,
        "seller": seller,
        "buyer": buyer,
        "item": item_details,
        "sale": sale,
        "escrow_info": escrow_info,
        "time_info": time_info,
        "available_actions": available_actions,
        "action_status": action_status,
        "payment_info": payment_info,
        "user_role": "buyer" if transaction.buyer_id == current_user.id else "seller" if transaction.seller_id == current_user.id else "admin"
    } 