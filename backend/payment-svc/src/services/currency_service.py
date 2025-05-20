"""
Сервис для конвертации валют и расчета комиссий
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import requests
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

from ..models.wallet import Currency
from ..database.connection import get_db

logger = logging.getLogger(__name__)

# Моковые курсы валют для разработки (не для продакшена)
DEFAULT_EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.85,
    "GBP": 0.75,
    "RUB": 90.0,
    "JPY": 110.0,
    "CNY": 6.5
}

# Настройки комиссий
FEE_SETTINGS = {
    "default": {
        "deposit": Decimal("0.01"),  # 1%
        "withdrawal": Decimal("0.02"),  # 2%
        "conversion": Decimal("0.005"),  # 0.5%
        "transfer": Decimal("0.005"),  # 0.5%
    },
    "premium": {
        "deposit": Decimal("0.005"),  # 0.5%
        "withdrawal": Decimal("0.01"),  # 1%
        "conversion": Decimal("0.0025"),  # 0.25%
        "transfer": Decimal("0.0"),  # бесплатно
    },
    "tier_thresholds": {
        "premium": Decimal("10000")  # Пользователи с балансом >= 10000 USD
    }
}

class CurrencyService:
    """
    Сервис для работы с валютами и комиссиями
    """
    def __init__(self, db: Session):
        self.db = db
        self.rates_cache = {}
        self.rates_cache_time = None
        self.cache_duration = timedelta(hours=1)  # Обновляем курсы каждый час
    
    async def get_exchange_rates(self, force_refresh: bool = False) -> Dict[str, float]:
        """
        Получает текущие курсы валют из кэша или API
        
        Args:
            force_refresh: Принудительно обновить данные из API
            
        Returns:
            Словарь курсов валют
        """
        # Проверяем кэш
        current_time = datetime.now()
        if not force_refresh and self.rates_cache and self.rates_cache_time and \
            current_time - self.rates_cache_time < self.cache_duration:
            return self.rates_cache
        
        # В неконечной среде используем моки
        if os.environ.get("ENVIRONMENT", "development") != "production":
            # Вносим немного вариативности в курсы
            import random
            rates = {
                k: v * (1 + (random.random() - 0.5) * 0.01)  # ±0.5% изменения
                for k, v in DEFAULT_EXCHANGE_RATES.items()
            }
            
            # Сохраняем в кэш
            self.rates_cache = rates
            self.rates_cache_time = current_time
            
            return rates
            
        # В продакшене используем реальный API
        try:
            # Здесь был бы запрос к реальному API курсов валют
            # Например, Open Exchange Rates или другой сервис
            api_key = os.environ.get("EXCHANGE_RATE_API_KEY")
            if not api_key:
                logger.warning("EXCHANGE_RATE_API_KEY не настроен, используем дефолтные курсы")
                rates = DEFAULT_EXCHANGE_RATES
            else:
                # Запрос к реальному API курсов валют
                response = requests.get(
                    f"https://openexchangerates.org/api/latest.json?app_id={api_key}",
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                rates = {currency: 1/data["rates"][currency] for currency in Currency}
                
            # Сохраняем в кэш
            self.rates_cache = rates
            self.rates_cache_time = current_time
                
            return rates
            
        except Exception as e:
            logger.error(f"Ошибка при получении курсов валют: {str(e)}")
            # В случае ошибки используем последние известные курсы
            if self.rates_cache:
                return self.rates_cache
            # Если кэш пуст, возвращаем дефолтные значения
            return DEFAULT_EXCHANGE_RATES
    
    async def convert_currency(
        self, 
        amount: Decimal, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Decimal:
        """
        Конвертирует сумму из одной валюты в другую
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            
        Returns:
            Сконвертированная сумма
        """
        if from_currency == to_currency:
            return amount
            
        rates = await self.get_exchange_rates()
        
        # Конвертируем в USD (базовая валюта), затем в целевую валюту
        amount_in_usd = Decimal(str(amount)) / Decimal(str(rates[from_currency]))
        converted_amount = amount_in_usd * Decimal(str(rates[to_currency]))
        
        # Округляем до 6 знаков после запятой
        return converted_amount.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    async def calculate_fee(
        self, 
        amount: Decimal, 
        transaction_type: str, 
        user_tier: str = "default"
    ) -> Decimal:
        """
        Рассчитывает комиссию за транзакцию
        
        Args:
            amount: Сумма транзакции
            transaction_type: Тип транзакции (deposit, withdrawal, conversion, transfer)
            user_tier: Уровень пользователя (default, premium)
            
        Returns:
            Сумма комиссии
        """
        # Получаем ставку комиссии для данного типа транзакции и уровня пользователя
        if transaction_type not in FEE_SETTINGS[user_tier]:
            raise ValueError(f"Неизвестный тип транзакции: {transaction_type}")
            
        fee_rate = FEE_SETTINGS[user_tier][transaction_type]
        fee_amount = amount * fee_rate
        
        # Округляем до 2 знаков после запятой
        return fee_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    async def preview_conversion(
        self, 
        amount: Decimal, 
        from_currency: Currency, 
        to_currency: Currency, 
        user_tier: str = "default"
    ) -> Dict[str, Any]:
        """
        Предпросмотр конвертации валюты с учетом комиссий
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            user_tier: Уровень пользователя
            
        Returns:
            Словарь с деталями конвертации
        """
        if from_currency == to_currency:
            return {
                "original_amount": amount,
                "fee": Decimal("0"),
                "fee_currency": from_currency,
                "amount_after_fee": amount,
                "converted_amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": Decimal("1"),
                "user_tier": user_tier,
                "timestamp": datetime.now().isoformat()
            }
            
        # Рассчитываем комиссию
        fee = await self.calculate_fee(amount, "conversion", user_tier)
        amount_after_fee = amount - fee
        
        # Конвертируем валюту
        converted_amount = await self.convert_currency(amount_after_fee, from_currency, to_currency)
        
        # Рассчитываем обменный курс
        rates = await self.get_exchange_rates()
        from_rate = Decimal(str(rates[from_currency]))
        to_rate = Decimal(str(rates[to_currency]))
        exchange_rate = to_rate / from_rate
        
        return {
            "original_amount": amount,
            "fee": fee,
            "fee_currency": from_currency,
            "amount_after_fee": amount_after_fee,
            "converted_amount": converted_amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": exchange_rate,
            "user_tier": user_tier,
            "timestamp": datetime.now().isoformat()
        }

@lru_cache
def get_currency_service(
    db: Session = Depends(get_db)
) -> CurrencyService:
    """
    Фабричная функция для получения экземпляра CurrencyService
    
    Args:
        db: Сессия SQLAlchemy
        
    Returns:
        Экземпляр CurrencyService
    """
    return CurrencyService(db) 