"""
Маршруты API для операций с валютами и комиссиями
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models.wallet import Currency, Wallet
from ..schemas.wallet import CurrencyConversionRequest, CurrencyConversionResponse, ExchangeRatesResponse
from ..services.currency_service import get_currency_service, CurrencyService
from ..services.wallet_service import get_wallet_service, WalletService
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/currency",
    tags=["currency"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Валюта или курс не найден"},
        422: {"description": "Ошибка валидации данных"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)

@router.get(
    "/rates",
    response_model=ExchangeRatesResponse,
    summary="Получение курсов валют",
    description="""
    Возвращает текущие курсы валют относительно базовой валюты.
    
    - По умолчанию базовая валюта - USD
    - Курсы обновляются автоматически по расписанию
    - Можно принудительно обновить курсы
    - Включает временную метку последнего обновления
    - Поддерживает все основные валюты системы
    
    **Пример ответа:**
    ```json
    {
        "base_currency": "USD",
        "rates": {
            "EUR": 0.85,
            "RUB": 75.50
        },
        "timestamp": "2024-03-20T10:00:00Z"
    }
    ```
    """
)
async def get_exchange_rates(
    base_currency: Currency = Query(Currency.USD, description="Базовая валюта для курсов обмена"),
    force_refresh: bool = Query(False, description="Принудительно обновить курсы из API"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Получает текущие курсы валют, по умолчанию относительно USD
    """
    currency_service = get_currency_service(db)
    rates = await currency_service.get_exchange_rates(force_refresh=force_refresh)
    
    # Преобразуем все курсы относительно базовой валюты
    base_rate = rates[base_currency]
    normalized_rates = {
        currency: rate / base_rate 
        for currency, rate in rates.items()
    }
    
    return {
        "base_currency": base_currency,
        "rates": normalized_rates,
        "timestamp": currency_service.rates_cache_time.isoformat() if currency_service.rates_cache_time else None
    }

@router.post("/convert/preview", response_model=CurrencyConversionResponse)
async def preview_currency_conversion(
    conversion_data: CurrencyConversionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Предварительный расчет конвертации валюты с учетом комиссий
    """
    currency_service = get_currency_service(db)
    wallet_service = get_wallet_service(db)
    
    # Получаем кошелек пользователя
    wallet = await wallet_service.get_wallet_by_user_id(current_user.user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")
    
    # Проверяем, что у пользователя достаточно средств
    if not await wallet_service.has_sufficient_balance(
        wallet.id, conversion_data.amount, conversion_data.from_currency
    ):
        raise HTTPException(
            status_code=400, 
            detail=f"Недостаточно средств в {conversion_data.from_currency}"
        )
    
    # Рассчитываем предварительную конвертацию
    conversion_preview = await currency_service.preview_conversion(
        Decimal(str(conversion_data.amount)),
        conversion_data.from_currency,
        conversion_data.to_currency
    )
    
    # Добавляем информацию о кошельке
    conversion_preview["wallet_id"] = wallet.id
    
    return conversion_preview

@router.post(
    "/convert/execute",
    response_model=CurrencyConversionResponse,
    summary="Выполнение конвертации валют",
    description="""
    Выполняет конвертацию валюты с учетом текущих курсов и комиссий.
    
    - Проверяет достаточность средств
    - Применяет текущие курсы обмена
    - Учитывает комиссии системы
    - Создает записи о транзакциях
    - Возвращает детали конвертации
    
    **Параметры запроса:**
    - `wallet_id`: ID кошелька
    - `from_currency`: Исходная валюта
    - `to_currency`: Целевая валюта
    - `amount`: Сумма для конвертации
    
    **Возможные ошибки:**
    - Недостаточно средств
    - Неверный курс обмена
    - Неподдерживаемая валюта
    - Ошибка при создании транзакций
    """
)
async def execute_currency_conversion(
    conversion_data: CurrencyConversionRequest = Body(..., description="Данные для конвертации валюты"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Выполняет конвертацию валюты и обновляет баланс кошелька
    """
    currency_service = get_currency_service(db)
    wallet_service = get_wallet_service(db)
    
    # Получаем кошелек пользователя
    wallet = await wallet_service.get_wallet_by_user_id(current_user.user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")
    
    # Проверяем, что у пользователя достаточно средств
    if not await wallet_service.has_sufficient_balance(
        wallet.id, conversion_data.amount, conversion_data.from_currency
    ):
        raise HTTPException(
            status_code=400, 
            detail=f"Недостаточно средств в {conversion_data.from_currency}"
        )
    
    # Рассчитываем предварительную конвертацию
    conversion_preview = await currency_service.preview_conversion(
        Decimal(str(conversion_data.amount)),
        conversion_data.from_currency,
        conversion_data.to_currency
    )
    
    # Выполняем конвертацию
    transaction = await wallet_service.convert_currency(
        wallet_id=wallet.id,
        amount=Decimal(str(conversion_data.amount)),
        from_currency=conversion_data.from_currency,
        to_currency=conversion_data.to_currency,
        fee=conversion_preview["fee"],
        exchange_rate=conversion_preview["exchange_rate"]
    )
    
    # Добавляем информацию о транзакции
    result = dict(conversion_preview)
    result.update({
        "transaction_id": transaction.id,
        "status": transaction.status,
        "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
    })
    
    return result

@router.get(
    "/fees",
    response_model=Dict[str, Any],
    summary="Получение информации о комиссиях",
    description="""
    Возвращает информацию о текущих комиссиях системы.
    
    - Включает комиссии для разных типов операций
    - Показывает пороговые значения для разных уровней
    - Содержит специальные условия для премиум-пользователей
    - Комиссии указаны в процентах от суммы операции
    
    **Структура ответа:**
    ```json
    {
        "fees": {
            "default": {
                "transaction": "1.5",
                "conversion": "0.5",
                "withdrawal": "2.0"
            },
            "premium": {
                "transaction": "1.0",
                "conversion": "0.3",
                "withdrawal": "1.5"
            }
        },
        "tier_thresholds": {
            "silver": "1000",
            "gold": "5000",
            "platinum": "10000"
        }
    }
    ```
    """
)
async def get_fee_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Получает информацию о текущих комиссиях
    """
    from ..services.currency_service import FEE_SETTINGS
    
    return {
        "fees": {
            "default": {
                k: str(v) for k, v in FEE_SETTINGS["default"].items()
            },
            "premium": {
                k: str(v) for k, v in FEE_SETTINGS["premium"].items()
            }
        },
        "tier_thresholds": {
            k: str(v) for k, v in FEE_SETTINGS["tier_thresholds"].items()
        }
    } 