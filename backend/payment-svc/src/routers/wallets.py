"""
Маршруты API для работы с кошельками
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.connection import get_db
from ..models.wallet import Currency, WalletStatus
from ..models.transaction import TransactionStatus
from ..schemas.wallet import (
    WalletCreate, WalletTransactionResponseMinimal, WalletUpdate, WalletResponse, WalletListResponse,
    WalletBalanceResponse, WalletTransactionResponse, WalletTransactionListResponse,
    CurrencyConversionRequest, WithdrawalRequest, WithdrawalVerificationRequest,
    WithdrawalResponse, WithdrawalListResponse, WalletTransactionCreate
)
from ..services.wallet_service import get_wallet_service, WalletService
from ..services.stripe_service import get_stripe_service, StripeService
from ..dependencies import get_current_user, get_current_admin_user
from ..dependencies.auth import get_token
from ..services.auth_service import AuthService, UserInfo

router = APIRouter(
    prefix="/wallets",
    tags=["wallets"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Кошелек не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)

async def get_full_user_data(userInfo: UserInfo = Depends(get_current_user)):
    """Получает полные данные пользователя из auth-svc"""
    auth_service = AuthService()
    user_data = await auth_service.get_user_data(userInfo.token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не удалось получить данные пользователя")
    return user_data

@router.post(
    "",
    response_model=WalletResponse,
    status_code=201,
    summary="Создание кошелька",
    description="""
    Создает новый кошелек для пользователя.
    
    - Обычные пользователи могут создавать кошельки только для себя
    - Администраторы могут создавать кошельки для любого пользователя
    - Для каждого пользователя можно создать только один кошелек
    - Если пользователь не существует в локальной БД, он будет создан автоматически
    """
)
async def create_wallet(
    wallet_data: WalletCreate = Body(..., description="Данные для создания кошелька"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data),
    token: str = Depends(get_token)
):
    """
    Создает новый кошелек для текущего пользователя.
    """
    # Если пользователь не админ, разрешаем создать кошелек только для себя
    if current_user.id != wallet_data.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания кошелька другому пользователю")
    
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.create_wallet(wallet_data, token)
    
    return wallet

@router.get(
    "",
    response_model=WalletListResponse,
    summary="Получение списка кошельков",
    description="""
    Возвращает список кошельков с пагинацией и фильтрацией.
    
    - Обычные пользователи могут видеть только свои кошельки
    - Администраторы могут видеть все кошельки
    - Результаты можно фильтровать по статусу и пользователю
    - Если у пользователя нет кошельков, возвращается пустой список
    """
)
async def get_wallets(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    user_id: Optional[int] = Query(None, description="Фильтр по ID пользователя"),
    status: Optional[WalletStatus] = Query(None, description="Фильтр по статусу кошелька"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает список кошельков с пагинацией и фильтрацией.
    Обычные пользователи могут видеть только свои кошельки.
    Админы могут видеть все кошельки.
    Если у пользователя нет кошельков, возвращается пустой список.
    """
    # Для обычных пользователей всегда устанавливаем их ID в качестве фильтра
    if not current_user.is_admin:
        user_id = current_user.id
    
    # Если статус не указан, используем ACTIVE по умолчанию
    if status is None:
        status = WalletStatus.ACTIVE
    
    wallet_service = get_wallet_service(db)
    wallets, total = await wallet_service.get_wallets(page, size, user_id, status)
    
    # Убеждаемся, что wallets это список
    wallets_list = list(wallets) if wallets is not None else []
    
    # Вычисляем общее количество страниц
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Формируем ответ в соответствии с WalletListResponse
    return {
        "total": total,
        "items": wallets_list,  # Используем гарантированно список
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Получение кошелька по ID",
    description="""
    Возвращает информацию о конкретном кошельке.
    
    - Обычные пользователи могут видеть только свои кошельки
    - Администраторы могут видеть любой кошелек
    - Если кошелек не найден, возвращается ошибка 404
    """
)
async def get_wallet(
    wallet_id: int = Path(..., description="ID кошелька"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает информацию о кошельке по его ID.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к этому кошельку")
    
    return wallet

@router.get(
    "/by-uid/{wallet_uid}",
    response_model=WalletResponse,
    summary="Получение кошелька по UID",
    description="""
    Возвращает информацию о кошельке по его уникальному идентификатору.
    
    - UID кошелька генерируется автоматически при создании
    - Формат UID: wlt_XXXXXXXXXXXX
    - Обычные пользователи могут видеть только свои кошельки
    - Администраторы могут видеть любой кошелек
    """
)
async def get_wallet_by_uid(
    wallet_uid: str = Path(..., description="Уникальный идентификатор кошелька"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает информацию о кошельке по его UID.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet_by_uid(wallet_uid)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к этому кошельку")
    
    return wallet

@router.get(
    "/user/{user_id}",
    response_model=WalletResponse,
    summary="Получение кошелька пользователя",
    description="""
    Возвращает кошелек пользователя.
    
    - Обычные пользователи могут видеть только свой кошелек
    - Администраторы могут видеть кошелек любого пользователя
    - Если у пользователя нет кошелька, возвращается ошибка 404
    """
)
async def get_user_wallet(
    user_id: int = Path(..., description="ID пользователя"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает кошелек пользователя.
    """
    # Проверяем права доступа
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к кошельку другого пользователя")
    
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_user_wallet(user_id)
    
    return wallet

@router.patch("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(
    wallet_id: int,
    wallet_data: WalletUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Обновляет информацию о кошельке.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для изменения кошелька")
    
    # Статус могут менять только админы
    if wallet_data.status is not None and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Изменение статуса кошелька доступно только администраторам")
    
    updated_wallet = await wallet_service.update_wallet(wallet_id, wallet_data)
    return updated_wallet

@router.get("/{wallet_id}/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает текущий баланс кошелька по всем валютам.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к этому кошельку")
    
    balances = await wallet_service.get_wallet_balance(wallet_id)
    
    return {
        "wallet_id": wallet.id,
        "wallet_uid": wallet.wallet_uid,
        "balances": balances,
        "last_updated": wallet.updated_at or wallet.created_at
    }

@router.get(
    "/{wallet_id}/transactions",
    response_model=WalletTransactionListResponse,
    summary="Получение транзакций кошелька",
    description="""
    Возвращает историю транзакций кошелька с пагинацией.
    
    - Транзакции сортируются по дате создания (новые сверху)
    - Можно фильтровать по валюте
    - Обычные пользователи могут видеть только транзакции своих кошельков
    - Администраторы могут видеть транзакции любого кошелька
    """
)
async def get_wallet_transactions(
    wallet_id: int = Path(..., description="ID кошелька"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    currency: Optional[Currency] = Query(None, description="Фильтр по валюте"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает историю транзакций кошелька с пагинацией.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для доступа к этому кошельку")
    
    transactions, total = await wallet_service.get_wallet_transactions(
        wallet_id=wallet_id,
        page=page,
        page_size=size,
        currency=currency
    )
    
    # Убеждаемся, что transactions это список
    transactions_list = list(transactions) if transactions is not None else []
    
    # Вычисляем общее количество страниц
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Преобразуем записи модели WalletTransaction в формат ответа WalletTransactionResponse
    response_items = []
    for tx in transactions_list:
        # Определяем direction на основе типа транзакции
        direction = "in" if tx.type == "credit" else "out"
        
        # Статус для wallet transactions всегда completed
        status = "completed"
        
        # Создаем объект ответа
        response_item = {
            "id": tx.id,
            "wallet_id": tx.wallet_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "direction": direction,
            "type": tx.type,
            "status": status,
            "description": tx.description,
            "created_at": tx.created_at,
            "updated_at": None,  # У WalletTransaction нет поля updated_at
            "extra_data": tx.extra_data
        }
        response_items.append(response_item)
    
    return {
        "total": total,
        "items": response_items,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.post(
    "/{wallet_id}/convert",
    response_model=Dict[str, Any],
    summary="Конвертация валюты",
    description="""
    Конвертирует валюту внутри кошелька.
    
    - Создает две транзакции: списание исходной валюты и зачисление целевой
    - Применяются текущие курсы обмена и комиссии
    - Требуется достаточный баланс в исходной валюте
    - Поддерживается идемпотентность через X-Idempotency-Key
    """
)
async def convert_currency(
    wallet_id: int = Path(..., description="ID кошелька"),
    conversion_data: CurrencyConversionRequest = Body(..., description="Данные для конвертации"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Конвертирует валюту внутри кошелька.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для операций с этим кошельком")
    
    debit_tx, credit_tx = await wallet_service.convert_currency(wallet_id, conversion_data)
    debit_tx_response = WalletTransactionResponseMinimal(
        id=debit_tx.id,
        wallet_id=debit_tx.wallet_id,
        amount=debit_tx.amount,
        currency=debit_tx.currency,
        type=debit_tx.type,

        created_at=debit_tx.created_at,
    )
    credit_tx_response = WalletTransactionResponseMinimal(
        id=credit_tx.id,
        wallet_id=credit_tx.wallet_id,
        amount=credit_tx.amount,
        currency=credit_tx.currency,
        type=credit_tx.type,
        created_at=credit_tx.created_at,
    )
    
    return {
        "success": True,
        "debit_transaction": debit_tx_response,
        "credit_transaction": credit_tx_response,
        "exchange_rate": credit_tx.amount / debit_tx.amount
    }

@router.post("/{wallet_id}/deposit", response_model=Dict[str, Any])
async def create_deposit(
    wallet_id: int,
    amount: float = Body(..., gt=0, description="Сумма пополнения"),
    currency: Currency = Body(..., description="Валюта пополнения"),
    description: Optional[str] = Body(None, description="Описание платежа"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Создает платежное намерение для пополнения кошелька через Stripe.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для операций с этим кошельком")
    
    # Добавляем информацию о пользователе в метаданные
    metadata = {
        "user_id": current_user.id,
        "user_email": current_user.email
    }
    
    deposit_result = await wallet_service.create_deposit(
        wallet_id=wallet_id,
        amount=amount,
        currency=currency,
        description=description,
        metadata=metadata
    )
    
    return {
        "success": True,
        "payment_intent_id": deposit_result["payment_intent"]["id"],
        "client_secret": deposit_result["payment_intent"]["client_secret"],
        "transaction_id": deposit_result["transaction_id"]
    }

@router.post("/{wallet_id}/deposit/{transaction_id}/simulate-success", response_model=Dict[str, Any])
async def simulate_successful_deposit(
    wallet_id: int,
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Эмулирует получение вебхука от Stripe о успешном платеже.
    Для тестирования и разработки.
    """
    wallet_service = get_wallet_service(db)
    # Для тестирования убрали проверку прав доступа
    
    # Получаем транзакцию
    transaction = await wallet_service.get_transaction(transaction_id)
    
    if transaction.wallet_id != wallet_id:
        raise HTTPException(status_code=400, detail="Транзакция не принадлежит указанному кошельку")
    
    # Проверяем, есть ли необходимые данные
    payment_intent_id = None
    if transaction.extra_data:
        payment_intent_id = transaction.extra_data.get("payment_intent")
    
    if not payment_intent_id:
        raise HTTPException(status_code=400, detail="Невозможно найти ID платежного намерения для транзакции")
    
    # Эмулируем вебхук о успешном платеже
    mock_event_data = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": payment_intent_id,
                "status": "succeeded",
                "amount": float(transaction.amount),
                "currency": transaction.currency
            }
        }
    }
    
    # Обрабатываем эмулированный вебхук
    result = await wallet_service.process_payment_webhook(mock_event_data)
    
    return {
        "success": True,
        "message": "Платеж успешно эмулирован и обработан",
        "result": result
    }

@router.post("/webhooks/stripe", response_model=Dict[str, Any])
async def process_stripe_webhook(
    event_data: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Обрабатывает webhook-уведомления от Stripe.
    """
    wallet_service = get_wallet_service(db)
    
    # В реальном приложении здесь нужно проверить подпись webhook
    # и запустить обработку в фоновой задаче

    if background_tasks:
        # Обработка в фоновой задаче для быстрого ответа
        background_tasks.add_task(wallet_service.process_payment_webhook, event_data)
        return {"status": "processing"}
    else:
        # Синхронная обработка
        result = await wallet_service.process_payment_webhook(event_data)
        return result

@router.get("/admin/health", response_model=Dict[str, Any])
async def stripe_health_check(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Проверяет состояние интеграции со Stripe (только для администраторов).
    """
    stripe_service = get_stripe_service(db)
    
    # В реальной интеграции здесь был бы запрос к Stripe API для проверки подключения
    # В моковой версии просто возвращаем положительный статус
    
    return {
        "status": "ok",
        "provider": "stripe",
        "mode": "mock",
        "webhooks": await stripe_service.get_latest_webhook_events(limit=5)
    }

@router.post("/{wallet_id}/withdraw", response_model=WithdrawalResponse)
async def create_withdrawal_request(
    wallet_id: int,
    withdrawal_data: WithdrawalRequest,
    request_ip: str = Query(None, description="IP-адрес клиента"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Создает запрос на вывод средств с кошелька.
    Требует верификации перед обработкой.
    """
    wallet_service = get_wallet_service(db)
    wallet = await wallet_service.get_wallet(wallet_id)
    
    # Проверяем права доступа
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для операций с этим кошельком")
    
    # Добавляем IP в данные запроса, если не указан
    if not withdrawal_data.request_ip and request_ip:
        withdrawal_data.request_ip = request_ip
    
    # Создаем запрос на вывод
    withdrawal_result = await wallet_service.create_withdrawal_request(
        wallet_id=wallet_id,
        withdrawal_data=withdrawal_data
    )
    
    return WithdrawalResponse(
        transaction_id=withdrawal_result["transaction_id"],
        status=withdrawal_result["status"],
        amount=withdrawal_result["amount"],
        currency=withdrawal_result["currency"],
        created_at=datetime.now(),  # В реальном приложении брали бы из БД
        verification_required=withdrawal_result["verification_required"],
        verification_id=withdrawal_result.get("verification_id"),
        withdrawal_method=withdrawal_data.withdrawal_method,
        extra_data={
            "recipient_details_mask": "***"  # Маскируем детали получателя в ответе
        }
    )

@router.post("/withdrawals/{transaction_id}/verify", response_model=WithdrawalResponse)
async def verify_withdrawal(
    transaction_id: int,
    verification_data: WithdrawalVerificationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Верифицирует запрос на вывод средств с помощью кода верификации.
    """
    wallet_service = get_wallet_service(db)
    
    # Проверяем соответствие ID транзакции
    if transaction_id != verification_data.transaction_id:
        raise HTTPException(status_code=400, detail="ID транзакции в пути и в теле запроса не совпадают")
    
    # Получаем транзакцию для проверки прав
    transaction = await wallet_service.get_transaction(transaction_id)
    
    # Проверяем, что пользователь имеет право на эту операцию
    wallet = await wallet_service.get_wallet(transaction.wallet_id)
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для верификации этого вывода")
    
    # Верифицируем вывод
    result = await wallet_service.verify_withdrawal(
        transaction_id=transaction_id,
        verification_code=verification_data.verification_code
    )
    
    # Обогащаем ответ дополнительными данными
    return WithdrawalResponse(
        transaction_id=result["transaction_id"],
        status=result["status"],
        amount=result["amount"],
        currency=result["currency"],
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        completed_at=transaction.completed_at,
        verification_required=False,  # Уже верифицирован
        withdrawal_method=transaction.extra_data.get("withdrawal_method", "unknown"),
        extra_data={
            "payout_details": transaction.extra_data.get("payout_details")
        }
    )

@router.post("/withdrawals/{transaction_id}/cancel", response_model=WithdrawalResponse)
async def cancel_withdrawal(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Отменяет запрос на вывод средств, если он еще не обработан.
    """
    wallet_service = get_wallet_service(db)
    
    # Получаем транзакцию для проверки прав
    transaction = await wallet_service.get_transaction(transaction_id)
    
    # Проверяем, что пользователь имеет право на эту операцию
    wallet = await wallet_service.get_wallet(transaction.wallet_id)
    if wallet.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав для отмены этого вывода")
    
    # Отменяем вывод
    result = await wallet_service.cancel_withdrawal(transaction_id=transaction_id)
    
    # Обогащаем ответ дополнительными данными
    return WithdrawalResponse(
        transaction_id=result["transaction_id"],
        status=result["status"],
        amount=result["amount"],
        currency=result["currency"],
        created_at=transaction.created_at,
        updated_at=datetime.now(),
        verification_required=False,
        withdrawal_method=transaction.extra_data.get("withdrawal_method", "unknown"),
        extra_data={
            "canceled_at": transaction.extra_data.get("canceled_at")
        }
    )

@router.get("/withdrawals", response_model=WithdrawalListResponse)
async def get_withdrawal_requests(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status: Optional[TransactionStatus] = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db),
    current_user = Depends(get_full_user_data)
):
    """
    Возвращает историю запросов на вывод средств текущего пользователя.
    """
    wallet_service = get_wallet_service(db)
    
    # Получаем запросы на вывод пользователя
    withdrawals, total = await wallet_service.get_withdrawal_requests(
        user_id=current_user.id,
        page=page,
        page_size=size,
        status=status
    )
    
    # Убеждаемся, что withdrawals это список
    withdrawals_list = list(withdrawals) if withdrawals is not None else []
    
    # Вычисляем общее количество страниц
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Преобразуем результаты в ответ
    items = [
        WithdrawalResponse(
            transaction_id=w.id,
            status=w.status.value,
            amount=w.amount,
            currency=w.currency.value,
            created_at=w.created_at,
            updated_at=w.updated_at,
            completed_at=w.completed_at,
            verification_required=w.status == TransactionStatus.VERIFICATION_REQUIRED,
            verification_id=w.extra_data.get("verification_id"),
            withdrawal_method=w.extra_data.get("withdrawal_method", "unknown"),
            extra_data={
                "payout_details": w.extra_data.get("payout_details")
            }
        )
        for w in withdrawals_list
    ]
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/admin/withdrawals", response_model=WithdrawalListResponse)
async def admin_get_withdrawal_requests(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status: Optional[TransactionStatus] = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Возвращает историю всех запросов на вывод средств (только для администраторов).
    """
    wallet_service = get_wallet_service(db)
    
    # Получаем все запросы на вывод
    withdrawals, total = await wallet_service.get_admin_withdrawal_requests(
        page=page,
        page_size=size,
        status=status
    )
    
    # Убеждаемся, что withdrawals это список
    withdrawals_list = list(withdrawals) if withdrawals is not None else []
    
    # Вычисляем общее количество страниц
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Преобразуем результаты в ответ
    items = [
        WithdrawalResponse(
            transaction_id=w.id,
            status=w.status.value,
            amount=w.amount,
            currency=w.currency.value,
            created_at=w.created_at,
            updated_at=w.updated_at,
            completed_at=w.completed_at,
            verification_required=w.status == TransactionStatus.VERIFICATION_REQUIRED,
            verification_id=w.extra_data.get("verification_id"),
            withdrawal_method=w.extra_data.get("withdrawal_method", "unknown"),
            extra_data={
                "user_id": w.user_id,
                "wallet_id": w.wallet_id,
                "payout_details": w.extra_data.get("payout_details"),
                "request_ip": w.extra_data.get("request_ip")
            }
        )
        for w in withdrawals_list
    ]
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.post("/admin/withdrawals/{transaction_id}/approve", response_model=WithdrawalResponse)
async def admin_approve_withdrawal(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Подтверждает запрос на вывод средств администратором (для крупных сумм).
    """
    wallet_service = get_wallet_service(db)
    
    # Подтверждаем вывод администратором
    result = await wallet_service.admin_approve_withdrawal(transaction_id=transaction_id)
    
    # Получаем транзакцию для дополнительных данных
    transaction = await wallet_service.get_transaction(transaction_id)
    
    # Обогащаем ответ дополнительными данными
    return WithdrawalResponse(
        transaction_id=result["transaction_id"],
        status=result["status"],
        amount=result["amount"],
        currency=result["currency"],
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        completed_at=transaction.completed_at,
        verification_required=False,
        withdrawal_method=transaction.extra_data.get("withdrawal_method", "unknown"),
        extra_data={
            "admin_approved": transaction.extra_data.get("admin_approved"),
            "admin_approved_by": current_user.id,
            "payout_details": transaction.extra_data.get("payout_details")
        }
    ) 