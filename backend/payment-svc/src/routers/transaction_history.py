"""
API маршруты для работы с историей транзакций
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import csv
import io
import json

from ..database.connection import get_db
from ..models.transaction import TransactionStatus
from ..schemas.transaction_history import TransactionHistoryResponse, TransactionHistoryListResponse
from ..services.transaction_history_service import TransactionHistoryService, get_transaction_history_service

router = APIRouter(
    prefix="/transactions/history",
    tags=["transaction_history"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "История транзакций не найдена"},
        422: {"description": "Ошибка валидации данных"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)

logger = logging.getLogger(__name__)

@router.get(
    "",
    response_model=TransactionHistoryListResponse,
    summary="Получение истории транзакций",
    description="""
    Возвращает историю транзакций с пагинацией и фильтрацией.
    
    - Поддерживает фильтрацию по пользователю, статусу и датам
    - Результаты сортируются по дате (новые сверху)
    - Обычные пользователи могут видеть только свою историю
    - Администраторы могут видеть историю всех транзакций
    - Поддерживает пагинацию с ограничением размера страницы
    - Даты можно указать в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    """
)
async def get_transactions_history(
    user_id: Optional[int] = Query(None, description="ID пользователя для фильтрации"),
    status: Optional[TransactionStatus] = Query(None, description="Статус транзакций для фильтрации"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата фильтрации (YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата фильтрации (YYYY-MM-DDTHH:MM:SS)"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    history_service: TransactionHistoryService = Depends(get_transaction_history_service),
):
    """
    Получение истории транзакций с пагинацией и фильтрацией.
    """
    logger.info(f"Запрос истории транзакций: user_id={user_id}, status={status}, page={page}, page_size={page_size}")
    return history_service.get_transactions_history(
        user_id=user_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

@router.get(
    "/{transaction_id}",
    response_model=List[TransactionHistoryResponse],
    summary="Получение истории конкретной транзакции",
    description="""
    Возвращает полную историю изменений конкретной транзакции.
    
    - Включает все изменения статуса и дополнительные данные
    - Показывает, кто и когда внес изменения
    - Содержит причины изменений и комментарии
    - Обычные пользователи могут видеть только свои транзакции
    - Администраторы могут видеть историю любых транзакций
    - Если транзакция не найдена, возвращает ошибку 404
    """
)
async def get_transaction_history(
    transaction_id: int = Path(..., description="ID транзакции"),
    history_service: TransactionHistoryService = Depends(get_transaction_history_service),
):
    """
    Получение истории конкретной транзакции.
    """
    logger.info(f"Запрос истории для транзакции ID {transaction_id}")
    return history_service.get_transaction_history(transaction_id)

@router.get(
    "/{transaction_id}/timeline",
    response_model=List[TransactionHistoryResponse],
    summary="Получение таймлайна транзакции",
    description="""
    Возвращает таймлайн изменений статусов транзакции.
    
    - Записи отсортированы по времени (от старых к новым)
    - Включает все изменения статуса и важные события
    - Показывает последовательность действий
    - Содержит информацию об инициаторах изменений
    - Подходит для отображения прогресса транзакции
    """
)
async def get_transaction_timeline(
    transaction_id: int = Path(..., description="ID транзакции"),
    history_service: TransactionHistoryService = Depends(get_transaction_history_service),
):
    """
    Получение таймлайна изменений статусов транзакции (отсортированных по времени).
    """
    logger.info(f"Запрос таймлайна для транзакции ID {transaction_id}")
    return history_service.get_transaction_timeline(transaction_id)

@router.get(
    "/{transaction_id}/export",
    response_class=Response,
    summary="Экспорт истории транзакции",
    description="""
    Экспортирует историю транзакции в CSV или JSON формате.
    
    - Поддерживает форматы CSV и JSON
    - Включает все изменения статуса и события
    - Содержит полную информацию о транзакции
    - Файл автоматически скачивается браузером
    - CSV формат удобен для импорта в Excel
    - JSON формат подходит для программной обработки
    
    **Параметры:**
    - `format`: Формат экспорта (csv или json)
    - `transaction_id`: ID транзакции
    
    **Возвращает:**
    - Файл в выбранном формате
    - Заголовок Content-Disposition для скачивания
    """
)
async def export_transaction_history(
    transaction_id: int = Path(..., description="ID транзакции"),
    format: str = Query("csv", description="Формат экспорта (csv, json)"),
    history_service: TransactionHistoryService = Depends(get_transaction_history_service),
):
    """
    Экспорт истории транзакции в формате CSV или JSON.
    """
    logger.info(f"Экспорт истории транзакции ID {transaction_id} в формате {format}")
    
    # Получаем историю транзакции
    history = history_service.get_transaction_timeline(transaction_id)
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"История для транзакции {transaction_id} не найдена"
        )
    
    if format.lower() == "csv":
        # Создаем CSV из данных
        output = io.StringIO()
        fieldnames = ["id", "transaction_id", "previous_status", "new_status", 
                     "timestamp", "initiator_id", "initiator_type", "reason", "extra_data"]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for record in history:
            writer.writerow({
                "id": record.id,
                "transaction_id": record.transaction_id,
                "previous_status": record.previous_status,
                "new_status": record.new_status,
                "timestamp": record.timestamp.isoformat(),
                "initiator_id": record.initiator_id,
                "initiator_type": record.initiator_type,
                "reason": record.reason,
                "extra_data": json.dumps(record.extra_data) if record.extra_data else None
            })
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=transaction_{transaction_id}_history.csv"
            }
        )
    
    elif format.lower() == "json":
        # Создаем JSON из данных
        history_data = []
        for record in history:
            history_data.append({
                "id": record.id,
                "transaction_id": record.transaction_id,
                "previous_status": record.previous_status.value if record.previous_status else None,
                "new_status": record.new_status.value,
                "timestamp": record.timestamp.isoformat(),
                "initiator_id": record.initiator_id,
                "initiator_type": record.initiator_type,
                "reason": record.reason,
                "extra_data": record.extra_data
            })
            
        return Response(
            content=json.dumps(history_data, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=transaction_{transaction_id}_history.json"
            }
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат экспорта: {format}. Поддерживаемые форматы: csv, json"
        )

@router.get("/report", response_class=Response)
async def generate_transactions_report(
    user_id: Optional[int] = Query(None, description="ID пользователя для фильтрации"),
    status: Optional[TransactionStatus] = Query(None, description="Статус транзакций для фильтрации"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата фильтрации (YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата фильтрации (YYYY-MM-DDTHH:MM:SS)"),
    format: str = Query("csv", description="Формат экспорта (csv, json)"),
    db: Session = Depends(get_db),
    history_service: TransactionHistoryService = Depends(get_transaction_history_service)
):
    """
    Генерация отчета по истории транзакций с фильтрацией.
    """
    logger.info(f"Генерация отчета по транзакциям: user_id={user_id}, status={status}, format={format}")
    
    # Установка значений по умолчанию для дат, если не указаны
    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=30)  # По умолчанию отчет за 30 дней
    
    # Получаем все записи истории для отчета (без пагинации)
    history_records = []
    
    # Используем TransactionHistoryService для получения данных с учетом фильтров
    page = 1
    page_size = 1000  # Большой размер страницы для уменьшения количества запросов
    
    while True:
        response = history_service.get_transactions_history(
            user_id=user_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        if not response.items:
            break
            
        history_records.extend(response.items)
        
        if page >= response.pages:
            break
            
        page += 1
    
    if not history_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не найдено записей истории транзакций с указанными параметрами"
        )
    
    if format.lower() == "csv":
        # Создаем CSV отчет
        output = io.StringIO()
        fieldnames = ["id", "transaction_id", "previous_status", "new_status", 
                     "timestamp", "initiator_id", "initiator_type", "reason", "extra_data"]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for record in history_records:
            writer.writerow({
                "id": record.id,
                "transaction_id": record.transaction_id,
                "previous_status": record.previous_status.value if record.previous_status else None,
                "new_status": record.new_status.value,
                "timestamp": record.timestamp.isoformat(),
                "initiator_id": record.initiator_id,
                "initiator_type": record.initiator_type,
                "reason": record.reason,
                "extra_data": json.dumps(record.extra_data) if record.extra_data else None
            })
        
        filename = f"transaction_report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    elif format.lower() == "json":
        # Создаем JSON отчет
        report_data = []
        for record in history_records:
            report_data.append({
                "id": record.id,
                "transaction_id": record.transaction_id,
                "previous_status": record.previous_status.value if record.previous_status else None,
                "new_status": record.new_status.value,
                "timestamp": record.timestamp.isoformat(),
                "initiator_id": record.initiator_id,
                "initiator_type": record.initiator_type,
                "reason": record.reason,
                "extra_data": record.extra_data
            })
            
        filename = f"transaction_report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.json"
        return Response(
            content=json.dumps(report_data, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат экспорта: {format}. Поддерживаемые форматы: csv, json"
        ) 