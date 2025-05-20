from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from ..models.wallet import Currency, WalletStatus
from ..models.transaction import TransactionStatus

class WalletBase(BaseModel):
    """Базовая схема для кошельков"""
    user_id: int = Field(..., description="ID пользователя-владельца кошелька")
    is_default: bool = Field(default=False, description="Является ли кошелёк основным для пользователя")
    notes: Optional[str] = Field(default=None, description="Примечания к кошельку")

class WalletCreate(WalletBase):
    """Схема для создания кошелька"""
    initial_balances: Optional[Dict[Currency, float]] = Field(
        default_factory=dict,
        description="Начальные балансы в различных валютах"
    )
    
    @validator('initial_balances')
    def validate_initial_balances(cls, v):
        """Проверяет корректность начальных балансов"""
        if v:
            for currency, amount in v.items():
                if amount < 0:
                    raise ValueError(f"Начальный баланс в {currency} не может быть отрицательным")
        return v

class WalletUpdate(BaseModel):
    """Схема для обновления кошелька"""
    is_default: Optional[bool] = Field(default=None, description="Является ли кошелёк основным для пользователя")
    notes: Optional[str] = Field(default=None, description="Примечания к кошельку")
    status: Optional[WalletStatus] = Field(default=None, description="Статус кошелька")

class WalletResponse(WalletBase):
    """Схема ответа с данными кошелька"""
    id: int = Field(..., description="ID кошелька")
    balances: Dict[Currency, float] = Field(..., description="Балансы в различных валютах")
    status: WalletStatus = Field(..., description="Статус кошелька")
    created_at: datetime = Field(..., description="Дата и время создания кошелька")
    updated_at: Optional[datetime] = Field(default=None, description="Дата и время последнего обновления кошелька")
    limits: Optional[Dict[str, Any]] = Field(default=None, description="Лимиты кошелька")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные кошелька")
    
    model_config = ConfigDict(from_attributes=True)

class WalletListResponse(BaseModel):
    """Схема ответа со списком кошельков"""
    total: int = Field(..., description="Общее количество кошельков")
    items: List[WalletResponse] = Field(..., description="Список кошельков")
    page: int = Field(..., description="Номер текущей страницы")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")

class WalletBalanceResponse(BaseModel):
    """Схема ответа с балансом кошелька"""
    wallet_id: int = Field(..., description="ID кошелька")
    balances: Dict[Currency, float] = Field(..., description="Балансы в различных валютах")
    total_usd_equivalent: float = Field(..., description="Общая сумма в эквиваленте USD")
    updated_at: datetime = Field(..., description="Дата и время обновления баланса")

class WalletTransactionBase(BaseModel):
    """Базовая схема для транзакций кошелька"""
    amount: Decimal = Field(..., description="Сумма транзакции", ge=0)
    currency: Currency = Field(..., description="Валюта транзакции")
    description: Optional[str] = Field(default=None, description="Описание транзакции")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные транзакции")

class WalletTransactionCreate(WalletTransactionBase):
    """Схема для создания транзакции кошелька"""
    wallet_id: int = Field(..., description="ID кошелька")
    type: str = Field(..., description="Тип транзакции (credit/debit)")
    transaction_id: Optional[int] = Field(default=None, description="ID связанной транзакции")

class WalletTransactionResponse(BaseModel):
    """Схема ответа с данными транзакции кошелька"""
    id: int = Field(..., description="ID транзакции")
    wallet_id: int = Field(..., description="ID кошелька")
    amount: float = Field(..., description="Сумма транзакции")
    currency: Currency = Field(..., description="Валюта транзакции")
    direction: str = Field(..., description="Направление транзакции (in/out)")
    type: str = Field(..., description="Тип транзакции")
    status: str = Field(..., description="Статус транзакции")
    description: Optional[str] = Field(default=None, description="Описание транзакции")
    created_at: datetime = Field(..., description="Дата и время создания транзакции")
    updated_at: Optional[datetime] = Field(default=None, description="Дата и время последнего обновления транзакции")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные транзакции")
    
    model_config = ConfigDict(from_attributes=True)

class WalletTransactionListResponse(BaseModel):
    """Схема ответа со списком транзакций кошелька"""
    total: int = Field(..., description="Общее количество транзакций")
    items: List[WalletTransactionResponse] = Field(..., description="Список транзакций")
    page: int = Field(..., description="Номер текущей страницы")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")

class CurrencyConversionRequest(BaseModel):
    """Схема запроса на конвертацию валюты"""
    amount: Decimal = Field(..., description="Сумма для конвертации", gt=0)
    from_currency: Currency = Field(..., description="Исходная валюта")
    to_currency: Currency = Field(..., description="Целевая валюта")
    
    @validator('to_currency')
    def currencies_must_differ(cls, v, values):
        if 'from_currency' in values and v == values['from_currency']:
            raise ValueError("Исходная и целевая валюты должны отличаться")
        return v

class CurrencyConversionResponse(BaseModel):
    """Схема ответа с результатом конвертации валюты"""
    original_amount: Decimal = Field(..., description="Исходная сумма")
    fee: Decimal = Field(..., description="Комиссия за конвертацию")
    fee_currency: Currency = Field(..., description="Валюта комиссии")
    amount_after_fee: Decimal = Field(..., description="Сумма после вычета комиссии")
    converted_amount: Decimal = Field(..., description="Сконвертированная сумма")
    from_currency: Currency = Field(..., description="Исходная валюта")
    to_currency: Currency = Field(..., description="Целевая валюта")
    exchange_rate: Decimal = Field(..., description="Обменный курс")
    user_tier: Optional[str] = Field(default=None, description="Уровень пользователя для комиссий")
    wallet_id: Optional[int] = Field(default=None, description="ID кошелька")
    transaction_id: Optional[int] = Field(default=None, description="ID транзакции (если выполнена)")
    status: Optional[str] = Field(default=None, description="Статус транзакции (если выполнена)")
    timestamp: str = Field(..., description="Временная метка операции")
    completed_at: Optional[str] = Field(default=None, description="Время завершения операции")

class ExchangeRatesResponse(BaseModel):
    """Схема ответа с курсами валют"""
    base_currency: Currency = Field(..., description="Базовая валюта для курсов")
    rates: Dict[Currency, float] = Field(..., description="Курсы валют относительно базовой")
    timestamp: Optional[str] = Field(default=None, description="Временная метка курсов")

class WithdrawalRequest(BaseModel):
    """Схема запроса на вывод средств"""
    amount: Decimal = Field(..., description="Сумма для вывода", gt=0)
    currency: Currency = Field(..., description="Валюта вывода")
    withdrawal_method: str = Field(..., description="Метод вывода (bank_transfer, card, crypto)")
    recipient_details: Dict[str, Any] = Field(..., description="Данные получателя")
    description: Optional[str] = Field(default=None, description="Описание вывода")
    request_ip: Optional[str] = Field(default=None, description="IP-адрес клиента")
    
    @validator('recipient_details')
    def validate_recipient_details(cls, v, values):
        if 'withdrawal_method' not in values:
            return v
            
        method = values['withdrawal_method']
        if method == 'bank_transfer':
            required_fields = ['account_number', 'bank_name', 'beneficiary_name']
        elif method == 'card':
            required_fields = ['card_number', 'card_holder']
        elif method == 'crypto':
            required_fields = ['wallet_address', 'network']
        else:
            raise ValueError(f"Неподдерживаемый метод вывода: {method}")
            
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Для метода {method} требуется поле {field}")
                
        return v

class WithdrawalVerificationRequest(BaseModel):
    """Схема запроса на верификацию вывода"""
    transaction_id: int = Field(..., description="ID транзакции")
    verification_code: str = Field(..., description="Код верификации")

class WithdrawalResponse(BaseModel):
    """Схема ответа с данными запроса на вывод"""
    transaction_id: int = Field(..., description="ID транзакции")
    status: str = Field(..., description="Статус вывода")
    amount: Decimal = Field(..., description="Сумма вывода")
    currency: Currency = Field(..., description="Валюта вывода")
    created_at: datetime = Field(..., description="Дата и время создания запроса")
    updated_at: Optional[datetime] = Field(default=None, description="Дата и время последнего обновления")
    completed_at: Optional[datetime] = Field(default=None, description="Дата и время завершения")
    verification_required: bool = Field(..., description="Требуется ли верификация")
    verification_id: Optional[str] = Field(default=None, description="ID верификации")
    withdrawal_method: str = Field(..., description="Метод вывода")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные")

class WithdrawalListResponse(BaseModel):
    """Схема ответа со списком запросов на вывод"""
    total: int = Field(..., description="Общее количество запросов")
    items: List[WithdrawalResponse] = Field(..., description="Список запросов на вывод")
    page: int = Field(..., description="Номер текущей страницы")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц") 