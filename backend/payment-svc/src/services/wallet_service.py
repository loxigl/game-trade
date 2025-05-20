"""
Сервис для работы с кошельками, включая мультивалютность и интеграцию со Stripe
"""

from decimal import Decimal
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, update
import uuid  # Добавляем импорт uuid для генерации идентификаторов
import random  # Добавляем импорт random для генерации случайных чисел


from ..models.wallet import Wallet, WalletTransaction, Currency, WalletStatus
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..schemas.wallet import (
    WalletCreate, WalletUpdate, WalletResponse, WalletTransactionCreate, 
    WalletBalanceResponse, CurrencyConversionRequest, WithdrawalRequest
)
from .stripe_service import get_stripe_service, StripeService
from ..services.auth_service import AuthService
from ..models.core import User
from ..dependencies.auth import get_token

logger = logging.getLogger(__name__)

class WalletService:
    """
    Сервис для управления кошельками пользователей и транзакциями
    """
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса кошельков
        
        Args:
            db: Сессия базы данных
        """
        self.db = db
        self.stripe_service = get_stripe_service(db)
    
    async def create_wallet(self, wallet_data: WalletCreate, token: str=Depends(get_token)) -> Wallet:
        """
        Создает новый кошелек для пользователя
        
        Args:
            wallet_data: Данные для создания кошелька
            token: Токен пользователя для проверки в auth-svc
            
        Returns:
            Созданный объект кошелька
        """
        # Проверяем существование пользователя в локальной БД
        user = self.db.query(User).filter(User.id == wallet_data.user_id).first()
        if not user:
            # Пытаемся создать пользователя в локальной БД на основе данных из auth-svc
            user = await AuthService.create_user(token, self.db)
            if not user:
                raise HTTPException(
                    status_code=400,
                    detail=f"Не удалось создать или найти пользователя с ID {wallet_data.user_id}"
                )

        # Проверяем существование кошелька для этого пользователя
        existing_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == wallet_data.user_id
        ).first()
        
        if existing_wallet:
            raise HTTPException(
                status_code=400, 
                detail=f"Кошелек для пользователя {wallet_data.user_id} уже существует"
            )
        
        # Инициализация балансов
        initial_balances = {}
        if wallet_data.initial_balances:
            # Преобразуем Enum ключи в строки для хранения в JSON
            initial_balances = {
                currency.value: amount 
                for currency, amount in wallet_data.initial_balances.items()
            }
        
        # Инициализация лимитов
        limits = None
        
        # Создаем кошелек
        wallet = Wallet(
            user_id=wallet_data.user_id,
            balances=initial_balances,
            limits=limits,  # Если None, будут использованы значения по умолчанию
            is_default=wallet_data.is_default,
            notes=wallet_data.notes
        )
        
        # Если это первый кошелек пользователя, делаем его по умолчанию
        if wallet.is_default is None:
            wallet.is_default = True
        
       
        
        self.db.add(wallet)
        
        # Если кошелек по умолчанию, обновляем все другие кошельки пользователя
        if wallet.is_default:
            self.db.query(Wallet).filter(
                Wallet.user_id == wallet_data.user_id,
                Wallet.id != wallet.id
            ).update({"is_default": False})
        
        self.db.commit()
        self.db.refresh(wallet)
        
        # Создаем записи транзакций для начальных балансов
        for currency_str, amount in initial_balances.items():
            if amount > 0:
                # Создаем транзакцию депозита для каждой ненулевой валюты
                await self.create_wallet_transaction(
                    WalletTransactionCreate(
                        wallet_id=wallet.id,
                        amount=amount,
                        currency=Currency(currency_str),
                        type="credit",
                        description="Начальный депозит"
                    )
                )
        
        return wallet
    
    async def get_wallet(self, wallet_id: int) -> Wallet:
        """
        Получает кошелек по ID
        
        Args:
            wallet_id: ID кошелька
            
        Returns:
            Объект кошелька
        """
        wallet = self.db.query(Wallet).filter(Wallet.id == wallet_id).first()
        
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Кошелек с ID {wallet_id} не найден")
        
        return wallet
    
    async def get_wallet_by_uid(self, wallet_uid: str) -> Wallet:
        """
        Получает кошелек по UID
        
        Args:
            wallet_uid: UID кошелька
            
        Returns:
            Объект кошелька
        """
        wallet = self.db.query(Wallet).filter(Wallet.wallet_uid == wallet_uid).first()
        
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Кошелек с UID {wallet_uid} не найден")
        
        return wallet
    
    async def get_user_wallet(self, user_id: int) -> Wallet:
        """
        Получает кошелек пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Объект кошелька
        """
        wallet = self.db.query(Wallet).filter(
            Wallet.user_id == user_id
        ).first()
        
        if not wallet:
            raise HTTPException(status_code=404, 
                              detail=f"Кошелек для пользователя с ID {user_id} не найден")
        
        return wallet
    
    async def update_wallet(self, wallet_id: int, wallet_data: WalletUpdate) -> Wallet:
        """
        Обновляет кошелек
        
        Args:
            wallet_id: ID кошелька
            wallet_data: Данные для обновления
            
        Returns:
            Обновленный объект кошелька
        """
        wallet = await self.get_wallet(wallet_id)
        
        # Обновляем поля
        if wallet_data.is_default is not None:
            wallet.is_default = wallet_data.is_default
            # Если делаем кошелек по умолчанию, обновляем другие кошельки пользователя
            if wallet.is_default:
                self.db.query(Wallet).filter(
                    Wallet.user_id == wallet.user_id,
                    Wallet.id != wallet.id
                ).update({"is_default": False})
        
        if wallet_data.status is not None:
            wallet.status = wallet_data.status
        
        if wallet_data.notes is not None:
            wallet.notes = wallet_data.notes
        
        # Обновляем лимиты
        if wallet_data.limits:
            current_limits = wallet.limits or {}
            
            for currency, limit_updates in wallet_data.limits.items():
                currency_str = currency.value
                
                if currency_str not in current_limits:
                    current_limits[currency_str] = {}
                
                if limit_updates.daily is not None:
                    current_limits[currency_str]["daily"] = limit_updates.daily
                
                if limit_updates.monthly is not None:
                    current_limits[currency_str]["monthly"] = limit_updates.monthly
            
            wallet.limits = current_limits
        
        wallet.updated_at = func.now()
        self.db.commit()
        self.db.refresh(wallet)
        
        return wallet
    
    async def deactivate_wallet(self, wallet_id: int) -> Wallet:
        """
        Деактивирует кошелек
        
        Args:
            wallet_id: ID кошелька
            
        Returns:
            Обновленный объект кошелька
        """
        wallet = await self.get_wallet(wallet_id)
        
        if wallet.status == WalletStatus.CLOSED:
            raise HTTPException(status_code=400, detail="Кошелек уже закрыт")
        
        wallet.status = WalletStatus.CLOSED
        wallet.updated_at = func.now()
        self.db.commit()
        self.db.refresh(wallet)
        
        return wallet
    
    async def get_wallet_balance(self, wallet_id: int) -> Dict[str, float]:
        """
        Получает баланс кошелька по всем валютам
        
        Args:
            wallet_id: ID кошелька
            
        Returns:
            Словарь с балансами по валютам
        """
        wallet = await self.get_wallet(wallet_id)
        
        # Обновляем время последней активности
        wallet.last_activity_at = func.now()
        self.db.commit()
        
        return wallet.balances
    
    async def create_wallet_transaction(self, tx_data: WalletTransactionCreate) -> WalletTransaction:
        """
        Создает новую транзакцию кошелька
        
        Args:
            tx_data: Данные транзакции
            
        Returns:
            Созданная транзакция
        """
        logger.info(f"Создание транзакции кошелька: wallet_id={tx_data.wallet_id}, amount={tx_data.amount}, currency={tx_data.currency}, type={tx_data.type}")
        
        wallet = await self.get_wallet(tx_data.wallet_id)
        
        # Проверяем статус кошелька
        if wallet.status != WalletStatus.ACTIVE:
            logger.error(f"Невозможно выполнить транзакцию: кошелек имеет статус {wallet.status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Невозможно выполнить транзакцию: кошелек имеет статус {wallet.status}"
            )
        
        currency_str = tx_data.currency.value
        
        # Инициализируем баланс валюты, если его ещё нет
        if currency_str not in wallet.balances:
            logger.info(f"Инициализация баланса валюты {currency_str} для кошелька {wallet.id}")
            wallet.balances[currency_str] = 0.0
            # Маркируем балансы как измененные для SQLAlchemy
            wallet.balances = dict(wallet.balances)
        
        current_balance = wallet.balances[currency_str]
        logger.info(f"Текущий баланс кошелька {wallet.id}: {current_balance} {currency_str}")
        
        # Проверяем достаточность средств для списания
        if tx_data.type == "debit" and current_balance < tx_data.amount:
            logger.error(f"Недостаточно средств: требуется {tx_data.amount} {currency_str}, доступно {current_balance}")
            raise HTTPException(
                status_code=400, 
                detail=f"Недостаточно средств: требуется {tx_data.amount} {currency_str}, доступно {current_balance}"
            )
        
        # Вычисляем новый баланс
        if tx_data.type == "credit":
            new_balance = Decimal(str(current_balance)) + Decimal(str(tx_data.amount))
        elif tx_data.type == "debit":
            new_balance = Decimal(str(current_balance)) - Decimal(str(tx_data.amount))
        else:  # конвертация или другие типы
            new_balance = Decimal(str(current_balance))
        
        logger.info(f"Новый баланс кошелька {wallet.id}: {new_balance} {currency_str} (было {current_balance})")
        
        # Создаем запись транзакции
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            transaction_id=tx_data.transaction_id,
            amount=float(tx_data.amount),
            currency=tx_data.currency,
            balance_before=float(current_balance),
            balance_after=float(new_balance),
            type=tx_data.type,
            description=tx_data.description,
            extra_data=tx_data.extra_data
        )
        
        # Обновляем баланс кошелька в памяти
        wallet.balances[currency_str] = float(new_balance)
        # Маркируем балансы как измененные для SQLAlchemy
        wallet.balances = dict(wallet.balances)
        wallet.last_activity_at = func.now()
        
        # Сохраняем транзакцию
        self.db.add(transaction)
        
        # Явно обновляем кошелек через SQL запрос
        update_stmt = update(Wallet).where(Wallet.id == wallet.id).values(
            balances=wallet.balances,
            last_activity_at=func.now(),
            updated_at=func.now()
        )
        self.db.execute(update_stmt)
        
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"Транзакция кошелька {transaction.id} успешно создана, баланс обновлен: {new_balance} {currency_str}")
        
        return transaction
    
    async def get_wallet_transactions(self, wallet_id: int, 
                                    page: int = 1, page_size: int = 20,
                                    currency: Optional[Currency] = None) -> Tuple[List[WalletTransaction], int]:
        """
        Получает историю транзакций кошелька с пагинацией
        
        Args:
            wallet_id: ID кошелька
            page: Номер страницы
            page_size: Размер страницы
            currency: Фильтр по валюте
            
        Returns:
            Кортеж (список транзакций, общее количество)
        """
        # Проверяем, что кошелек существует
        await self.get_wallet(wallet_id)
        
        query = self.db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet_id)
        
        # Применяем фильтр по валюте, если указан
        if currency:
            query = query.filter(WalletTransaction.currency == currency)
        
        # Получаем общее количество записей
        total = query.count()
        
        # Применяем пагинацию и сортировку
        transactions = query.order_by(desc(WalletTransaction.created_at))\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        return transactions, total
    
    async def convert_currency(self, wallet_id: int, conversion_data: CurrencyConversionRequest) -> Tuple[WalletTransaction, WalletTransaction]:
        """
        Конвертирует валюту внутри кошелька
        
        Args:
            wallet_id: ID кошелька
            conversion_data: Данные для конвертации
            
        Returns:
            Кортеж (транзакция списания, транзакция зачисления)
        """
        wallet = await self.get_wallet(wallet_id)
        
        # Проверяем статус кошелька
        if wallet.status != WalletStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Невозможно выполнить конвертацию: кошелек имеет статус {wallet.status}"
            )
        
        from_currency_str = conversion_data.from_currency.value
        to_currency_str = conversion_data.to_currency.value
        
        # Проверяем, что валюта источника есть в кошельке и на ней достаточно средств
        if from_currency_str not in wallet.balances:
            wallet.balances[from_currency_str] = 0.0
        
        if wallet.balances[from_currency_str] < conversion_data.amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Недостаточно средств: требуется {conversion_data.amount} {from_currency_str}, доступно {wallet.balances[from_currency_str]}"
            )
        
        # Получаем курс обмена (в реальном приложении здесь был бы запрос к сервису курсов валют)
        exchange_rate = self._get_mock_exchange_rate(conversion_data.from_currency, conversion_data.to_currency)
        # Преобразуем exchange_rate из float в Decimal для совместимости с Decimal amount
        converted_amount = conversion_data.amount * Decimal(str(exchange_rate))
        
        # Создаем общее описание операции
        description = f"Конвертация из {from_currency_str} в {to_currency_str}"
        extra_data = {
            "conversion_id": str(uuid.uuid4()),
            "exchange_rate": exchange_rate
        }
        
        # Создаем транзакцию списания
        debit_tx = await self.create_wallet_transaction(
            WalletTransactionCreate(
                wallet_id=wallet.id,
                amount=conversion_data.amount,
                currency=conversion_data.from_currency,
                type="debit",
                description=f"{description} (списание)",
                extra_data=extra_data
            )
        )
        
        # Создаем транзакцию зачисления
        credit_tx = await self.create_wallet_transaction(
            WalletTransactionCreate(
                wallet_id=wallet.id,
                amount=converted_amount,
                currency=conversion_data.to_currency,
                type="credit",
                description=f"{description} (зачисление)",
                extra_data=extra_data
            )
        )
        
        return debit_tx, credit_tx
    
    def _get_mock_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> float:
        """
        Возвращает моковый курс обмена между валютами
        
        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            
        Returns:
            Курс обмена
        """
        # Моковые курсы (в реальном приложении здесь был бы запрос к внешнему API)
        rates = {
            "USD": {"EUR": 0.93, "GBP": 0.80, "RUB": 90.0, "JPY": 150.0, "CNY": 7.2},
            "EUR": {"USD": 1.07, "GBP": 0.86, "RUB": 97.0, "JPY": 160.0, "CNY": 7.7},
            "GBP": {"USD": 1.25, "EUR": 1.16, "RUB": 113.0, "JPY": 187.0, "CNY": 9.0},
            "RUB": {"USD": 0.011, "EUR": 0.01, "GBP": 0.0088, "JPY": 1.6, "CNY": 0.08},
            "JPY": {"USD": 0.0067, "EUR": 0.0062, "GBP": 0.0053, "RUB": 0.62, "CNY": 0.048},
            "CNY": {"USD": 0.14, "EUR": 0.13, "GBP": 0.11, "RUB": 12.5, "JPY": 20.8}
        }
        
        from_str = from_currency.value
        to_str = to_currency.value
        
        # Если конвертируем в ту же валюту
        if from_str == to_str:
            return 1.0
        
        # Получаем курс обмена
        if from_str in rates and to_str in rates[from_str]:
            return rates[from_str][to_str]
        
        # Если прямого курса нет, используем USD как промежуточную валюту
        if from_str != "USD" and to_str != "USD":
            usd_to_from = rates["USD"][from_str]
            usd_to_to = rates["USD"][to_str]
            return 1 / usd_to_from * usd_to_to
        
        # Если и это не удалось, возвращаем заглушку
        return 1.0
    
    async def create_deposit(self, wallet_id: int, amount: float, 
                           currency: Currency, description: str = None,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Создает депозит на кошелек через Stripe
        
        Args:
            wallet_id: ID кошелька
            amount: Сумма депозита
            currency: Валюта депозита
            description: Описание платежа
            metadata: Дополнительные метаданные
            
        Returns:
            Данные созданного платежного намерения
        """
        wallet = await self.get_wallet(wallet_id)
        
        # Проверяем статус кошелька
        if wallet.status != WalletStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Невозможно выполнить депозит: кошелек имеет статус {wallet.status}"
            )
        
        # Подготавливаем метаданные
        tx_metadata = metadata or {}
        tx_metadata.update({
            "wallet_id": wallet_id,
            "currency": currency.value,
            "operation": "deposit"
        })
        
        # Создаем платежное намерение в Stripe
        payment_intent = await self.stripe_service.create_payment_intent(
            amount=amount,
            currency=currency,
            metadata=tx_metadata,
            description=description or f"Пополнение кошелька {wallet.wallet_uid}"
        )
        
        # Создаем запись транзакции в БД
        transaction = Transaction(
            wallet_id=wallet.id,
            amount=amount,
            currency=currency,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            extra_data={
                "payment_intent": payment_intent["id"],
                "client_secret": payment_intent["client_secret"],
                "provider": "stripe",
                "provider_transaction_id": payment_intent["id"]
            }
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Обновляем метаданные платежного намерения, добавляя ID транзакции
        payment_intent["metadata"]["transaction_id"] = transaction.id
        
        return {
            "payment_intent": payment_intent,
            "transaction_id": transaction.id
        }
    
    async def process_payment_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает вебхук о платеже от Stripe
        
        Args:
            event_data: Данные события
            
        Returns:
            Результат обработки
        """
        event_type = event_data.get("type")
        payment_intent = event_data.get("data", {}).get("object", {})
        payment_intent_id = payment_intent.get("id")
        
        if not payment_intent_id:
            raise HTTPException(status_code=400, detail="Недопустимые данные события")
        
        # Получаем все депозитные транзакции в статусе ожидания
        pending_transactions = self.db.query(Transaction).filter(
            Transaction.type == TransactionType.DEPOSIT,
            Transaction.status == TransactionStatus.PENDING
        ).all()
        
        # Находим нужную транзакцию через проверку payment_intent_id в extra_data
        transaction = None
        for tx in pending_transactions:
            if tx.extra_data and tx.extra_data.get("payment_intent") == payment_intent_id:
                transaction = tx
                break
        
        if not transaction:
            logger.warning(f"Транзакция для payment_intent {payment_intent_id} не найдена")
            return {"status": "ignored", "reason": "transaction_not_found"}
        
        # Обрабатываем различные типы событий
        if event_type == "payment_intent.succeeded":
            # Платеж успешно проведен
            if transaction.status != TransactionStatus.COMPLETED:
                # Обновляем статус транзакции
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = func.now()
                self.db.commit()
                
                logger.info(f"Транзакция {transaction.id} обновлена, статус: COMPLETED, начинаем зачисление средств на кошелек {transaction.wallet_id}")
                
                try:
                # Зачисляем средства на кошелек
                    wallet_tx = await self.create_wallet_transaction(
                    WalletTransactionCreate(
                        wallet_id=transaction.wallet_id,
                            transaction_id=transaction.id,
                        amount=transaction.amount,
                        currency=transaction.currency,
                        type="credit",
                            description=f"Пополнение счета через {transaction.extra_data.get('provider', 'Stripe')}",
                            extra_data={"source_transaction_id": transaction.id}
                        )
                    )
                    
                    logger.info(f"Средства успешно зачислены на кошелек {transaction.wallet_id}, создана транзакция кошелька {wallet_tx.id}")
                    
                    return {
                        "success": True,
                        "transaction_id": transaction.id,
                        "wallet_tx_id": wallet_tx.id,
                        "status": "completed",
                        "amount": transaction.amount,
                        "currency": transaction.currency
                    }
                except Exception as e:
                    logger.error(f"Ошибка при зачислении средств на кошелек: {str(e)}")
                    raise
            
            return {
                "status": "processed", 
                "transaction_id": transaction.id, 
                "wallet_id": transaction.wallet_id
            }
            
        elif event_type == "payment_intent.canceled":
            # Платеж отменен
            transaction.status = TransactionStatus.CANCELED
            self.db.commit()
            
            return {
                "status": "processed", 
                "transaction_id": transaction.id, 
                "wallet_id": transaction.wallet_id
            }
            
        elif event_type == "payment_intent.failed":
            # Платеж не прошел
            transaction.status = TransactionStatus.FAILED
            self.db.commit()
            
            return {
                "status": "processed", 
                "transaction_id": transaction.id, 
                "wallet_id": transaction.wallet_id
            }
        
        # Для других типов событий просто логируем
        return {"status": "ignored", "reason": "event_type_not_handled", "event_type": event_type}
    
    async def create_withdrawal_request(self, wallet_id: int, 
                                      withdrawal_data: WithdrawalRequest) -> Dict[str, Any]:
        """
        Создает запрос на вывод средств с кошелька
        
        Args:
            wallet_id: ID кошелька
            withdrawal_data: Данные запроса на вывод
            
        Returns:
            Данные созданного запроса на вывод
        """
        wallet = await self.get_wallet(wallet_id)
        
        # Проверяем статус кошелька
        if wallet.status != WalletStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400, 
                detail=f"Невозможно выполнить вывод: кошелек имеет статус {wallet.status}"
            )
        
        currency_str = withdrawal_data.currency.value
        
        # Проверяем наличие достаточного баланса для вывода
        if currency_str not in wallet.balances or wallet.balances[currency_str] < withdrawal_data.amount:
            current_balance = wallet.balances.get(currency_str, 0)
            raise HTTPException(
                status_code=400, 
                detail=f"Недостаточно средств: запрошено {withdrawal_data.amount} {currency_str}, доступно {current_balance}"
            )
        
        # Проверяем лимиты на вывод
        if not self._check_withdrawal_limits(wallet, withdrawal_data.amount, withdrawal_data.currency):
            raise HTTPException(
                status_code=400, 
                detail="Превышен лимит на вывод средств"
            )
        
        # Создаем запись транзакции вывода в БД
        transaction = Transaction(
            wallet_id=wallet.id,
            amount=withdrawal_data.amount,
            currency=withdrawal_data.currency,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.VERIFICATION_REQUIRED,  # Требуется верификация
            extra_data={
                "provider": "stripe",
                "user_id": wallet.user_id,
                "withdrawal_method": withdrawal_data.withdrawal_method,
                "recipient_details": withdrawal_data.recipient_details,
                "verification_id": str(uuid.uuid4()),  # Генерируем ID для верификации
                "request_ip": withdrawal_data.request_ip
            }
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Отправляем email с кодом подтверждения (в реальном приложении)
        # В моковой версии просто логируем
        verification_code = self._generate_verification_code()
        logger.info(f"Отправлен код верификации {verification_code} для вывода {transaction.id}")
        
        # Добавляем код верификации в БД (в хешированном виде в реальном приложении)
        transaction.extra_data["verification_code"] = verification_code
        self.db.commit()
        
        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "amount": transaction.amount,
            "currency": transaction.currency.value,
            "verification_required": True,
            "verification_id": transaction.extra_data["verification_id"]
        }
    
    def _generate_verification_code(self) -> str:
        """
        Генерирует код верификации для вывода средств
        
        Returns:
            Сгенерированный код
        """
        # В реальном приложении использовали бы более надежный метод
        # и отправляли бы код по email или SMS
        return f"{random.randint(100000, 999999)}"
    
    def _check_withdrawal_limits(self, wallet: Wallet, amount: float, currency: Currency) -> bool:
        """
        Проверяет лимиты на вывод средств
        
        Args:
            wallet: Объект кошелька
            amount: Сумма вывода
            currency: Валюта вывода
            
        Returns:
            True, если вывод не превышает лимиты, иначе False
        """
        currency_str = currency.value
        
        # Получаем лимиты для валюты (или значения по умолчанию)
        limits = wallet.limits.get(currency_str, {}) if wallet.limits else {}
        
        # Если лимиты не заданы, считаем что ограничений нет
        if not limits:
            return True
        
        # Проверяем дневной лимит
        daily_limit = limits.get("daily")
        if daily_limit is not None:
            # Получаем сумму выводов за текущий день
            today = datetime.now().date()
            daily_withdrawals = self.db.query(func.sum(Transaction.amount))\
                .filter(
                    Transaction.wallet_id == wallet.id,
                    Transaction.currency == currency,
                    Transaction.type == TransactionType.WITHDRAWAL,
                    Transaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.PENDING, TransactionStatus.VERIFICATION_REQUIRED]),
                    func.date(Transaction.created_at) == today
                ).scalar() or 0
            
            if daily_withdrawals + amount > daily_limit:
                return False
        
        # Проверяем месячный лимит
        monthly_limit = limits.get("monthly")
        if monthly_limit is not None:
            # Получаем первый день текущего месяца
            today = datetime.now().date()
            first_day_of_month = today.replace(day=1)
            
            # Получаем сумму выводов за текущий месяц
            monthly_withdrawals = self.db.query(func.sum(Transaction.amount))\
                .filter(
                    Transaction.wallet_id == wallet.id,
                    Transaction.currency == currency,
                    Transaction.type == TransactionType.WITHDRAWAL,
                    Transaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.PENDING, TransactionStatus.VERIFICATION_REQUIRED]),
                    func.date(Transaction.created_at) >= first_day_of_month
                ).scalar() or 0
            
            if monthly_withdrawals + amount > monthly_limit:
                return False
        
        return True
    
    async def verify_withdrawal(self, transaction_id: int, verification_code: str) -> Dict[str, Any]:
        """
        Верифицирует запрос на вывод средств
        
        Args:
            transaction_id: ID транзакции вывода
            verification_code: Код верификации
            
        Returns:
            Данные обновленной транзакции
        """
        # Находим транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.type == TransactionType.WITHDRAWAL,
            Transaction.status == TransactionStatus.VERIFICATION_REQUIRED
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=404, 
                detail="Транзакция не найдена или не требует верификации"
            )
        
        # Проверяем код верификации
        if transaction.extra_data.get("verification_code") != verification_code:
            # В реальном приложении увеличивали бы счетчик неудачных попыток
            raise HTTPException(status_code=400, detail="Неверный код верификации")
        
        # Переводим транзакцию в статус "В обработке"
        transaction.status = TransactionStatus.PENDING
        transaction.updated_at = func.now()
        
        # Удаляем код верификации из данных транзакции
        transaction.extra_data.pop("verification_code", None)
        
        self.db.commit()
        self.db.refresh(transaction)
        
        # Запускаем процесс вывода средств через Stripe
        # В моковой версии сразу переходим к обработке
        await self._process_withdrawal(transaction)
        
        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "amount": transaction.amount,
            "currency": transaction.currency.value
        }
    
    async def _process_withdrawal(self, transaction: Transaction) -> None:
        """
        Обрабатывает верифицированный вывод средств
        
        Args:
            transaction: Объект транзакции вывода
        """
        wallet = self.db.query(Wallet).filter(Wallet.id == transaction.wallet_id).first()
        if not wallet:
            transaction.status = TransactionStatus.FAILED
            transaction.extra_data["error"] = "Кошелек не найден"
            self.db.commit()
            return
        
        currency_str = transaction.currency.value
        
        # Проверяем баланс еще раз перед списанием
        if currency_str not in wallet.balances or wallet.balances[currency_str] < transaction.amount:
            transaction.status = TransactionStatus.FAILED
            transaction.extra_data["error"] = "Недостаточно средств"
            self.db.commit()
            return
        
        try:
            # Создаем транзакцию списания с кошелька
            await self.create_wallet_transaction(
                WalletTransactionCreate(
                    wallet_id=wallet.id,
                    amount=transaction.amount,
                    currency=transaction.currency,
                    type="debit",
                    description=f"Вывод средств (ID: {transaction.id})",
                    transaction_id=transaction.id
                )
            )
            
            # В реальной интеграции здесь был бы вызов Stripe Payout API
            # В моковой версии просто устанавливаем статус "Завершено"
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = func.now()
            transaction.extra_data["payout_details"] = {
                "payout_id": f"po_{str(uuid.uuid4())[:18]}",
                "status": "paid",
                "arrival_date": (datetime.now() + timedelta(days=2)).timestamp()
            }
            
            # Сохраняем изменения
            self.db.commit()
            logger.info(f"Вывод средств успешно обработан: ID {transaction.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке вывода {transaction.id}: {str(e)}")
            transaction.status = TransactionStatus.FAILED
            transaction.extra_data["error"] = str(e)
            self.db.commit()

    async def cancel_withdrawal(self, transaction_id: int) -> Dict[str, Any]:
        """
        Отменяет запрос на вывод средств
        
        Args:
            transaction_id: ID транзакции вывода
            
        Returns:
            Данные обновленной транзакции
        """
        # Находим транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.type == TransactionType.WITHDRAWAL,
            Transaction.status.in_([TransactionStatus.VERIFICATION_REQUIRED, TransactionStatus.PENDING])
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=404, 
                detail="Транзакция не найдена или не может быть отменена"
            )
        
        # Меняем статус на "Отменена"
        transaction.status = TransactionStatus.CANCELED
        transaction.updated_at = func.now()
        transaction.extra_data["canceled_at"] = datetime.now().isoformat()
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "amount": transaction.amount,
            "currency": transaction.currency.value
        }
    
    async def get_withdrawal_requests(self, user_id: int, 
                                    page: int = 1, page_size: int = 20,
                                    status: Optional[TransactionStatus] = None) -> Tuple[List[Transaction], int]:
        """
        Получает историю запросов на вывод средств пользователя с пагинацией
        
        Args:
            user_id: ID пользователя
            page: Номер страницы
            page_size: Размер страницы
            status: Фильтр по статусу
            
        Returns:
            Кортеж (список транзакций, общее количество)
        """
        query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.WITHDRAWAL
        )
        
        # Применяем фильтр по статусу, если указан
        if status:
            query = query.filter(Transaction.status == status)
        
        # Получаем общее количество записей
        total = query.count()
        
        # Применяем пагинацию и сортировку
        transactions = query.order_by(desc(Transaction.created_at))\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        return transactions, total
    
    async def get_admin_withdrawal_requests(self, 
                                        page: int = 1, page_size: int = 20,
                                        status: Optional[TransactionStatus] = None) -> Tuple[List[Transaction], int]:
        """
        Получает историю запросов на вывод средств для администраторов с пагинацией
        
        Args:
            page: Номер страницы
            page_size: Размер страницы
            status: Фильтр по статусу
            
        Returns:
            Кортеж (список транзакций, общее количество)
        """
        query = self.db.query(Transaction).filter(
            Transaction.type == TransactionType.WITHDRAWAL
        )
        
        # Применяем фильтр по статусу, если указан
        if status:
            query = query.filter(Transaction.status == status)
        
        # Получаем общее количество записей
        total = query.count()
        
        # Применяем пагинацию и сортировку
        transactions = query.order_by(desc(Transaction.created_at))\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        return transactions, total
        
    async def admin_approve_withdrawal(self, transaction_id: int) -> Dict[str, Any]:
        """
        Подтверждает запрос на вывод средств администратором
        
        Args:
            transaction_id: ID транзакции вывода
            
        Returns:
            Данные обновленной транзакции
        """
        # Находим транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.type == TransactionType.WITHDRAWAL,
            Transaction.status == TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=404, 
                detail="Транзакция не найдена или не может быть подтверждена"
            )
        
        # Добавляем информацию о подтверждении
        transaction.extra_data["admin_approved"] = True
        transaction.extra_data["admin_approved_at"] = datetime.now().isoformat()
        
        self.db.commit()
        self.db.refresh(transaction)
        
        # Запускаем процесс вывода средств
        await self._process_withdrawal(transaction)
        
        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "amount": transaction.amount,
            "currency": transaction.currency.value
        }

    async def get_transaction(self, transaction_id: int) -> Transaction:
        """
        Получает транзакцию по ID
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Объект транзакции
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Транзакция с ID {transaction_id} не найдена")
        
        return transaction

    
    async def get_wallets(self, page: int = 1, size: int = 20, user_id: Optional[int] = None, status: Optional[WalletStatus] = None) -> Tuple[List[Wallet], int]:
        """
        Получает список кошельков с пагинацией и фильтрацией
        
        Args:
            page: Номер страницы
            size: Размер страницы
            user_id: ID пользователя
            status: Статус кошелька

        Returns:
            Кортеж (список кошельков, общее количество)
        """
        query = self.db.query(Wallet)
        
        if user_id:
            query = query.filter(Wallet.user_id == user_id)
        
        if status:
            query = query.filter(Wallet.status == status.value)
        
        total = query.count()
        
        # Получаем кошельки и явно преобразуем в список
        wallets = list(query.order_by(desc(Wallet.created_at))\
            .offset((page - 1) * size)\
            .limit(size)\
            .all())
        
        return wallets, total




def get_wallet_service(db: Session) -> WalletService:
    """
    Фабричная функция для получения экземпляра сервиса кошельков
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Экземпляр сервиса кошельков
    """
    return WalletService(db) 