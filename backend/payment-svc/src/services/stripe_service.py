"""
Моковая реализация Stripe API для неоконечной среды разработки.
Эмулирует основные функции Stripe для обработки платежей.
"""

import logging
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import json
from enum import Enum
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.wallet import Wallet, Currency

logger = logging.getLogger(__name__)

class MockPaymentStatus(str, Enum):
    """Статусы платежей, соответствующие статусам Stripe"""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"

class StripeService:
    """
    Моковая реализация сервиса Stripe для работы с платежами
    
    Эмулирует основные функции Stripe API для тестирования и разработки
    """
    
    def __init__(self, db: Session = None):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных (опционально)
        """
        self.db = db
        self._payment_intents = {}  # Хранилище для платежных намерений
        self._customers = {}  # Моковое хранилище клиентов
        self._webhook_events = []  # История событий веб-хуков
        self._api_key = "sk_test_mock_api_key"  # Фиктивный API ключ
        self._payment_methods = self._generate_mock_payment_methods()  # Предварительно созданные методы оплаты
        
        # Эмуляция задержки и уровня успешности для имитации реального поведения API
        self._delay_range = (0.1, 0.5)  # Задержка между 100-500 мс
        self._success_rate = 0.95  # 95% транзакций успешны
        
        logger.info("Инициализирован моковый сервис Stripe")
    
    def _generate_id(self, prefix: str) -> str:
        """
        Генерирует фиктивный ID в формате Stripe
        
        Args:
            prefix: Префикс ID (например, "pi_" для payment intent)
            
        Returns:
            Сгенерированный ID
        """
        random_part = str(uuid.uuid4()).replace("-", "")[:20]
        return f"{prefix}_{random_part}"
    
    def _simulate_api_delay(self):
        """Имитирует задержку API"""
        delay = random.uniform(*self._delay_range)
        time.sleep(delay)
    
    def _simulate_api_error(self, error_rate: float = None) -> bool:
        """
        Имитирует случайную ошибку API с заданной частотой
        
        Args:
            error_rate: Вероятность ошибки (по умолчанию использует 1 - success_rate)
            
        Returns:
            True, если произошла ошибка, False в противном случае
        """
        if error_rate is None:
            error_rate = 1.0 - self._success_rate
        
        return random.random() < error_rate
    
    def _generate_mock_payment_methods(self) -> Dict[str, Dict[str, Any]]:
        """
        Генерирует моковые методы оплаты
        
        Returns:
            Словарь с моковыми методами оплаты
        """
        payment_methods = {}
        
        # Visa
        visa_pm = {
            "id": self._generate_id("pm"),
            "object": "payment_method",
            "type": "card",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": datetime.now().year + 1
            },
            "created": int(time.time())
        }
        payment_methods[visa_pm["id"]] = visa_pm
        
        # Mastercard
        mc_pm = {
            "id": self._generate_id("pm"),
            "object": "payment_method",
            "type": "card",
            "card": {
                "brand": "mastercard",
                "last4": "5555",
                "exp_month": 6,
                "exp_year": datetime.now().year + 2
            },
            "created": int(time.time())
        }
        payment_methods[mc_pm["id"]] = mc_pm
        
        return payment_methods
    
    async def create_payment_intent(self, amount: float, currency: Currency, 
                                    metadata: Dict[str, Any] = None, 
                                    description: str = None) -> Dict[str, Any]:
        """
        Создает платежное намерение (Payment Intent)
        
        Args:
            amount: Сумма платежа (в минимальных единицах валюты, например центах)
            currency: Валюта платежа
            metadata: Метаданные платежа
            description: Описание платежа
            
        Returns:
            Данные созданного платежного намерения
        """
        self._simulate_api_delay()
        
        if self._simulate_api_error(0.05):  # 5% вероятность ошибки при создании
            raise HTTPException(status_code=500, detail="Не удалось создать payment intent")
        
        intent_id = self._generate_id("pi")
        client_secret = f"{intent_id}_secret_{str(uuid.uuid4())[:8]}"
        
        # Конвертируем amount в "центы" (как это делает Stripe)
        amount_in_cents = int(amount * 100)
        
        payment_intent = {
            "id": intent_id,
            "object": "payment_intent",
            "amount": amount_in_cents,
            "currency": currency.lower(),
            "status": MockPaymentStatus.REQUIRES_PAYMENT_METHOD,
            "client_secret": client_secret,
            "created": int(time.time()),
            "description": description,
            "metadata": metadata or {},
            "payment_method": None,
            "payment_method_types": ["card"],
            "next_action": None
        }
        
        self._payment_intents[intent_id] = payment_intent
        logger.info(f"Создан payment intent: {intent_id} на сумму {amount} {currency}")
        
        return payment_intent
    
    async def confirm_payment_intent(self, payment_intent_id: str, 
                                     payment_method_id: str = None) -> Dict[str, Any]:
        """
        Подтверждает платежное намерение
        
        Args:
            payment_intent_id: ID платежного намерения
            payment_method_id: ID метода оплаты
            
        Returns:
            Обновленные данные платежного намерения
        """
        self._simulate_api_delay()
        
        if payment_intent_id not in self._payment_intents:
            raise HTTPException(status_code=404, detail="Payment intent не найден")
        
        payment_intent = self._payment_intents[payment_intent_id]
        
        # Если не указан метод оплаты, используем случайный из доступных
        if not payment_method_id and self._payment_methods:
            payment_method_id = random.choice(list(self._payment_methods.keys()))
        
        # Проверяем существование метода оплаты
        if payment_method_id and payment_method_id not in self._payment_methods:
            if len(self._payment_methods) > 0:
                # Если метода нет, но есть другие, используем случайный
                payment_method_id = random.choice(list(self._payment_methods.keys()))
            else:
                raise HTTPException(status_code=400, detail="Недопустимый payment_method_id")
        
        payment_intent["payment_method"] = payment_method_id
        
        # Имитируем различные пути прохождения платежа
        random_val = random.random()
        if random_val < 0.03:  # 3% требуют дополнительных действий
            payment_intent["status"] = MockPaymentStatus.REQUIRES_ACTION
            payment_intent["next_action"] = {
                "type": "redirect_to_url",
                "redirect_to_url": {
                    "url": f"https://mock-3ds.example.com/auth?payment={payment_intent_id}"
                }
            }
        elif random_val < 0.08:  # 5% переходят в обработку
            payment_intent["status"] = MockPaymentStatus.PROCESSING
        elif random_val < 0.11:  # 3% платежей не проходят
            payment_intent["status"] = MockPaymentStatus.FAILED
            payment_intent["last_payment_error"] = {
                "code": "card_declined",
                "message": "Платеж отклонен банком-эмитентом."
            }
        else:  # 89% сразу успешны
            payment_intent["status"] = MockPaymentStatus.SUCCEEDED
        
        # Сохраняем обновленный статус
        self._payment_intents[payment_intent_id] = payment_intent
        
        # Создаем вебхук-событие, если статус конечный
        if payment_intent["status"] in [MockPaymentStatus.SUCCEEDED, MockPaymentStatus.FAILED]:
            event_type = f"payment_intent.{payment_intent['status']}"
            self._create_webhook_event(event_type, payment_intent)
        
        logger.info(f"Payment intent {payment_intent_id} подтвержден со статусом {payment_intent['status']}")
        
        return payment_intent
    
    async def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Получает платежное намерение по ID
        
        Args:
            payment_intent_id: ID платежного намерения
            
        Returns:
            Данные платежного намерения
        """
        self._simulate_api_delay()
        
        if payment_intent_id not in self._payment_intents:
            raise HTTPException(status_code=404, detail="Payment intent не найден")
        
        return self._payment_intents[payment_intent_id]
    
    async def cancel_payment_intent(self, payment_intent_id: str, 
                                    cancellation_reason: str = None) -> Dict[str, Any]:
        """
        Отменяет платежное намерение
        
        Args:
            payment_intent_id: ID платежного намерения
            cancellation_reason: Причина отмены
            
        Returns:
            Обновленные данные платежного намерения
        """
        self._simulate_api_delay()
        
        if payment_intent_id not in self._payment_intents:
            raise HTTPException(status_code=404, detail="Payment intent не найден")
        
        payment_intent = self._payment_intents[payment_intent_id]
        
        # Проверяем, можно ли отменить
        if payment_intent["status"] in [MockPaymentStatus.SUCCEEDED, MockPaymentStatus.CANCELED]:
            raise HTTPException(status_code=400, 
                                detail=f"Невозможно отменить платеж в статусе {payment_intent['status']}")
        
        payment_intent["status"] = MockPaymentStatus.CANCELED
        payment_intent["cancellation_reason"] = cancellation_reason or "requested_by_customer"
        
        # Создаем вебхук-событие
        self._create_webhook_event("payment_intent.canceled", payment_intent)
        
        logger.info(f"Payment intent {payment_intent_id} отменен")
        
        return payment_intent
    
    async def create_refund(self, payment_intent_id: str, amount: Optional[float] = None, 
                            reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Создает возврат платежа
        
        Args:
            payment_intent_id: ID платежного намерения
            amount: Сумма возврата (если None, то полный возврат)
            reason: Причина возврата
            
        Returns:
            Данные созданного возврата
        """
        self._simulate_api_delay()
        
        if payment_intent_id not in self._payment_intents:
            raise HTTPException(status_code=404, detail="Payment intent не найден")
        
        payment_intent = self._payment_intents[payment_intent_id]
        
        if payment_intent["status"] != MockPaymentStatus.SUCCEEDED:
            raise HTTPException(status_code=400, 
                                detail="Возврат возможен только для успешно завершенных платежей")
        
        refund_id = self._generate_id("re")
        refund_amount = amount * 100 if amount is not None else payment_intent["amount"]
        
        refund = {
            "id": refund_id,
            "object": "refund",
            "amount": refund_amount,
            "currency": payment_intent["currency"],
            "payment_intent": payment_intent_id,
            "status": "succeeded",
            "reason": reason or "requested_by_customer",
            "created": int(time.time())
        }
        
        # Сохраняем информацию о возврате в payment intent
        if "refunds" not in payment_intent:
            payment_intent["refunds"] = {"data": []}
        
        payment_intent["refunds"]["data"].append(refund)
        payment_intent["refunded"] = True if refund_amount == payment_intent["amount"] else False
        payment_intent["amount_refunded"] = refund_amount
        
        # Создаем вебхук-событие
        self._create_webhook_event("charge.refunded", {
            "refund": refund,
            "payment_intent": payment_intent_id
        })
        
        logger.info(f"Создан возврат {refund_id} для payment intent {payment_intent_id}")
        
        return refund
    
    def _create_webhook_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает моковое событие вебхука
        
        Args:
            event_type: Тип события
            data: Данные события
            
        Returns:
            Созданное событие
        """
        event_id = self._generate_id("evt")
        
        event = {
            "id": event_id,
            "object": "event",
            "api_version": "2023-10-16",
            "created": int(time.time()),
            "type": event_type,
            "data": {
                "object": data
            }
        }
        
        self._webhook_events.append(event)
        logger.debug(f"Создано webhook событие: {event_type} для объекта {data.get('id', 'unknown')}")
        
        return event
    
    async def get_latest_webhook_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает последние события вебхуков
        
        Args:
            limit: Максимальное количество событий
            
        Returns:
            Список событий
        """
        return sorted(self._webhook_events, key=lambda x: x["created"], reverse=True)[:limit]
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает событие вебхука
        
        Args:
            event_data: Данные события
            
        Returns:
            Результат обработки события
        """
        # В моковой реализации просто логируем событие
        logger.info(f"Получено webhook событие: {event_data.get('type')}")
        
        # Здесь может быть логика для обработки разных типов событий
        
        return {"status": "processed"}

def get_stripe_service(db: Session = None) -> StripeService:
    """
    Фабричная функция для получения экземпляра сервиса Stripe
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Экземпляр сервиса Stripe
    """
    return StripeService(db) 