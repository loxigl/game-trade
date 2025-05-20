"""
Сервис для управления состояниями транзакций с использованием конечного автомата
"""


import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified

from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.wallet import Wallet, WalletTransaction, WalletStatus
from ..schemas.transaction_history import TransactionHistoryCreate
from .state_machine import TransactionStateMachine, TransactionStateMachineFactory, TransactionEvent, InvalidTransitionError
from .event_service import EventType, EventPayload, get_event_service
from .transaction_history_service import TransactionHistoryService

logger = logging.getLogger(__name__)

class TransactionStateService:
    """Сервис для управления состояниями транзакций с использованием конечного автомата"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных
        """
        self.db = db
        self.event_service = get_event_service()
        self.history_service = TransactionHistoryService(db)
    
    def _record_state_change(self, 
                             transaction_id: int, 
                             previous_status: TransactionStatus, 
                             new_status: TransactionStatus, 
                             initiator_id: Optional[int] = None, 
                             initiator_type: str = "system", 
                             reason: Optional[str] = None,
                             extra_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Записывает изменение статуса транзакции в историю
        
        Args:
            transaction_id: ID транзакции
            previous_status: Предыдущий статус
            new_status: Новый статус
            initiator_id: ID инициатора изменения (пользователь, система)
            initiator_type: Тип инициатора (user, system, admin)
            reason: Причина изменения
            extra_data: Дополнительные данные
        """
        try:
            history_data = TransactionHistoryCreate(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_status,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                extra_data=extra_data
            )
            
            self.history_service.create_history_record(history_data)
            logger.info(f"Recorded state change for transaction {transaction_id}: {previous_status} -> {new_status}")
        except Exception as e:
            logger.error(f"Failed to record state change for transaction {transaction_id}: {str(e)}")
            # Не выбрасываем исключение, чтобы не блокировать основной процесс
    
    async def get_transaction_state_machine(self, transaction_id: int) -> TransactionStateMachine:
        """
        Получение конечного автомата для транзакции
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Конечный автомат для транзакции
            
        Raises:
            ValueError: Если транзакция не найдена
        """
        # Проверяем существование транзакции
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Получаем или создаем конечный автомат
        state_machine = TransactionStateMachineFactory.get_state_machine(transaction_id, transaction.status)
        
        # Синхронизируем состояние с базой данных, если нужно
        if state_machine.get_current_state() != transaction.status:
            logger.warning(f"Рассинхронизация состояния для транзакции {transaction_id}: "
                          f"БД: {transaction.status}, конечный автомат: {state_machine.get_current_state()}")
            # Создаем новый конечный автомат с правильным состоянием
            # Это может произойти, если состояние было изменено в обход конечного автомата
            TransactionStateMachineFactory._instances[transaction_id] = TransactionStateMachine(transaction_id, transaction.status)
            state_machine = TransactionStateMachineFactory._instances[transaction_id]
        
        return state_machine
    
    async def process_payment(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Обработка платежа и перевод средств в Escrow
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Получаем кошелек покупателя
        buyer_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.buyer_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not buyer_wallet:
            raise ValueError(f"Активный кошелек покупателя не найден")
        
        # Проверяем баланс в нужной валюте
        buyer_balance = buyer_wallet.balances.get(transaction.currency, 0)
        if buyer_balance < transaction.amount:
            raise ValueError("Недостаточно средств на кошельке покупателя")
        
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Начало process_payment для транзакции {transaction_id}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Сумма транзакции: {transaction.amount}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс покупателя: {buyer_balance}")
        
        # Получаем или создаем Escrow кошелек
        escrow_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == 0,  # Системный пользователь
            Wallet.is_default == True
        ).first()
        
        if not escrow_wallet:
            # Создаем системный Escrow кошелек
            escrow_wallet = Wallet(
                user_id=0,
                balances={transaction.currency: 0.0},
                status=WalletStatus.ACTIVE,
                is_default=True,
                notes="Системный Escrow кошелек"
            )
            self.db.add(escrow_wallet)
            self.db.commit()
            self.db.refresh(escrow_wallet)
            
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}")
        
        # Выполняем переход состояния
        try:
            # Начало транзакции БД
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(TransactionEvent.PROCESS_PAYMENT, data)
            logger.info(f"Текущее состояние транзакции: {state_machine.get_current_state()}")
            logger.info(f"Переход в состояние: {new_state}")
            #нужно проверить, есть ли такое состояние в конечном автомате и обновиться ли оно в автомате
            if new_state not in state_machine.get_states():
                raise InvalidTransitionError(f"Переход в состояние {new_state} недопустим")
            else:
                state_machine.update_state(new_state)
            
            # Если переход успешен, обновляем базу данных
            # Выполняем перевод средств из баланса покупателя
            current_balance = buyer_wallet.balances.get(transaction.currency, 0)
            buyer_wallet.balances[transaction.currency] = current_balance - transaction.amount
            # Маркируем балансы как измененные для SQLAlchemy
            buyer_wallet.balances = dict(buyer_wallet.balances)
            flag_modified(buyer_wallet, "balances")
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После списания с кошелька покупателя: баланс стал {buyer_wallet.balances.get(transaction.currency, 0)}")
            
            # Обновляем общий баланс в базе данных
            self.db.flush()
            
            # Создаем запись в истории кошелька покупателя
            buyer_wallet_transaction = WalletTransaction(
                wallet_id=buyer_wallet.id,
                transaction_id=transaction.id,
                amount=-transaction.amount,
                currency=transaction.currency,
                balance_before=current_balance,
                balance_after=buyer_wallet.balances.get(transaction.currency, 0),
                type="debit",
                description=f"Списание средств для Escrow платежа (ID: {transaction.id})"
            )
            self.db.add(buyer_wallet_transaction)
            
            # Пополняем Escrow кошелек
            escrow_current_balance = escrow_wallet.balances.get(transaction.currency, 0)
            escrow_wallet.balances[transaction.currency] = escrow_current_balance + transaction.amount
            # Маркируем балансы как измененные для SQLAlchemy
            escrow_wallet.balances = dict(escrow_wallet.balances)
            flag_modified(escrow_wallet, "balances")
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После зачисления в Escrow: баланс стал {escrow_wallet.balances.get(transaction.currency, 0)}")
            
            # Создаем запись в истории кошелька Escrow
            escrow_wallet_transaction = WalletTransaction(
                wallet_id=escrow_wallet.id,
                transaction_id=transaction.id,
                amount=transaction.amount,
                currency=transaction.currency,
                balance_before=escrow_current_balance,
                balance_after=escrow_wallet.balances.get(transaction.currency, 0),
                type="credit",
                description=f"Зачисление средств в Escrow (ID: {transaction.id})"
            )
            self.db.add(escrow_wallet_transaction)
            
            # Обновляем состояние транзакции в БД
            transaction.status = new_state
            transaction.escrow_held_at = datetime.utcnow()
            flag_modified(transaction, "status")
            flag_modified(transaction, "escrow_held_at")
            
            # Сохраняем все изменения
            self.db.commit()
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После commit: баланс покупателя: {buyer_wallet.balances.get(transaction.currency, 0)}, баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}")
            
            # Проверяем сохранились ли изменения
            self.db.refresh(buyer_wallet)
            self.db.refresh(escrow_wallet)
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После refresh: баланс покупателя: {buyer_wallet.balances.get(transaction.currency, 0)}, баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}")
            
            # Записываем изменение статуса в историю
            initiator_id = data.get("initiator_id") if data else None
            initiator_type = data.get("initiator_type", "user") if data else "system"
            reason = data.get("reason") if data else "Средства переведены в Escrow"
            
            self._record_state_change(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_state,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                extra_data=data
            )
            
            self.db.refresh(transaction)
            
            # Проверка балансов напрямую из БД после всех операций
            try:
                fresh_buyer_wallet = self.db.query(Wallet).filter(
                    Wallet.user_id == transaction.buyer_id,
                    Wallet.status == WalletStatus.ACTIVE
                ).first()
                
                fresh_escrow_wallet = self.db.query(Wallet).filter(
                    Wallet.user_id == 0,
                    Wallet.is_default == True
                ).first()
                
                if fresh_buyer_wallet:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] Проверка из БД: Кошелек покупателя ID={fresh_buyer_wallet.id}, баланс={fresh_buyer_wallet.balances.get(transaction.currency, 0)}")
                
                if fresh_escrow_wallet:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] Проверка из БД: Escrow кошелек ID={fresh_escrow_wallet.id}, баланс={fresh_escrow_wallet.balances.get(transaction.currency, 0)}")
                    
                # Проверяем историю транзакций кошелька
                recent_wallet_transactions = self.db.query(WalletTransaction).filter(
                    WalletTransaction.transaction_id == transaction.id
                ).order_by(WalletTransaction.id.desc()).limit(5).all()
                
                logger.info(f"[ОТЛАДКА БАЛАНСОВ] Последние транзакции кошельков для транзакции {transaction.id}:")
                for wt in recent_wallet_transactions:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] - Кошелек ID={wt.wallet_id}, тип={wt.type}, сумма={wt.amount}, balance_before={wt.balance_before}, balance_after={wt.balance_after}")
            except Exception as e:
                logger.error(f"[ОТЛАДКА БАЛАНСОВ] Ошибка при проверке балансов из БД: {str(e)}")
            
            return transaction
            
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при обработке платежа: {str(e)}")
            raise
    
    async def complete_transaction(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Завершение транзакции и перевод средств продавцу
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Получаем кошельки продавца и Escrow
        seller_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.seller_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not seller_wallet:
            raise ValueError(f"Активный кошелек продавца не найден")
        
        # Проверяем наличие валюты в balances кошелька
        if transaction.currency not in seller_wallet.balances:
            # Инициализируем баланс для этой валюты
            seller_wallet.balances[transaction.currency] = 0.0
            
        escrow_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == 0,
            Wallet.is_default == True
        ).first()
        
        if not escrow_wallet:
            raise ValueError("Системный Escrow кошелек не найден")
        
        # Расчет суммы за вычетом комиссии
        final_amount = transaction.amount
        if transaction.fee_amount:
            final_amount -= transaction.fee_amount
        
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Начало complete_transaction для транзакции {transaction_id}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Сумма транзакции: {transaction.amount}, комиссия: {transaction.fee_amount}, чистая выплата продавцу: {final_amount}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс продавца: {seller_wallet.balances.get(transaction.currency, 0)}")
        
        # Выполняем переход состояния
        try:
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(TransactionEvent.RELEASE_FROM_ESCROW, data)
            
            # Если переход успешен, обновляем базу данных
            # Списываем с Escrow кошелька
            escrow_current_balance = escrow_wallet.balances.get(transaction.currency, 0)
            escrow_wallet.balances[transaction.currency] = escrow_current_balance - transaction.amount
            # Маркируем балансы как измененные для SQLAlchemy
            escrow_wallet.balances = dict(escrow_wallet.balances)
            flag_modified(escrow_wallet, "balances")
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После списания с Escrow: баланс Escrow стал {escrow_wallet.balances.get(transaction.currency, 0)}")
            
            # Создаем запись в истории кошелька Escrow
            escrow_wallet_transaction = WalletTransaction(
                wallet_id=escrow_wallet.id,
                transaction_id=transaction.id,
                amount=-transaction.amount,
                currency=transaction.currency,
                balance_before=escrow_current_balance,
                balance_after=escrow_wallet.balances.get(transaction.currency, 0),
                type="debit",
                description=f"Списание средств из Escrow для выплаты продавцу (ID: {transaction.id})"
            )
            self.db.add(escrow_wallet_transaction)
            
            # Пополняем кошелек продавца (за вычетом комиссии)
            seller_current_balance = seller_wallet.balances.get(transaction.currency, 0)
            seller_wallet.balances[transaction.currency] = seller_current_balance + final_amount
            # Маркируем балансы как измененные для SQLAlchemy
            seller_wallet.balances = dict(seller_wallet.balances)
            flag_modified(seller_wallet, "balances")
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После зачисления продавцу: баланс продавца стал {seller_wallet.balances.get(transaction.currency, 0)}")
            
            # Создаем запись в истории кошелька продавца
            seller_wallet_transaction = WalletTransaction(
                wallet_id=seller_wallet.id,
                transaction_id=transaction.id,
                amount=final_amount,
                currency=transaction.currency,
                balance_before=seller_current_balance,
                balance_after=seller_wallet.balances.get(transaction.currency, 0),
                type="credit",
                description=f"Получение средств за продажу (ID: {transaction.id})"
            )
            self.db.add(seller_wallet_transaction)
            
            # Если есть комиссия, можем добавить её на системный кошелек комиссий
            if transaction.fee_amount and transaction.fee_amount > 0:
                # Получаем или создаем системный кошелек комиссий
                fee_wallet = self.db.query(Wallet).filter(
                    Wallet.user_id == 0,
                    Wallet.is_system_fee == True
                ).first()
                
                if not fee_wallet:
                    fee_wallet = Wallet(
                        user_id=0,
                        balances={transaction.currency: 0.0},
                        status=WalletStatus.ACTIVE,
                        is_default=False,
                        is_system_fee=True,
                        notes="Системный кошелек комиссий"
                    )
                    self.db.add(fee_wallet)
                    self.db.flush()
                
                # Инициализируем баланс для этой валюты, если необходимо
                if transaction.currency not in fee_wallet.balances:
                    fee_wallet.balances[transaction.currency] = 0.0
                
                fee_current_balance = fee_wallet.balances.get(transaction.currency, 0)
                logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс кошелька комиссий: {fee_current_balance}")
                
                # Пополняем кошелек комиссий
                fee_wallet.balances[transaction.currency] = fee_current_balance + transaction.fee_amount
                # Маркируем балансы как измененные для SQLAlchemy
                fee_wallet.balances = dict(fee_wallet.balances)
                flag_modified(fee_wallet, "balances")
                logger.info(f"[ОТЛАДКА БАЛАНСОВ] После зачисления комиссии: баланс кошелька комиссий стал {fee_wallet.balances.get(transaction.currency, 0)}")
                
                # Создаем запись в истории кошелька комиссий
                fee_wallet_transaction = WalletTransaction(
                    wallet_id=fee_wallet.id,
                    transaction_id=transaction.id,
                    amount=transaction.fee_amount,
                    currency=transaction.currency,
                    balance_before=fee_current_balance,
                    balance_after=fee_wallet.balances.get(transaction.currency, 0),
                    type="credit",
                    description=f"Комиссия за транзакцию (ID: {transaction.id})"
                )
                self.db.add(fee_wallet_transaction)
            
            # Обновляем состояние транзакции в БД
            transaction.status = new_state
            transaction.completed_at = datetime.utcnow()
            flag_modified(transaction, "status")
            flag_modified(transaction, "completed_at")
            
            # Сохраняем все изменения
            self.db.commit()
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После commit: баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}, баланс продавца: {seller_wallet.balances.get(transaction.currency, 0)}")
            
            # Проверяем сохранились ли изменения в базе
            self.db.refresh(escrow_wallet)
            self.db.refresh(seller_wallet)
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После refresh: баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}, баланс продавца: {seller_wallet.balances.get(transaction.currency, 0)}")
            
            # Записываем изменение статуса в историю
            initiator_id = data.get("initiator_id") if data else None
            initiator_type = data.get("initiator_type", "user") if data else "system"
            reason = data.get("reason") if data else "Транзакция успешно завершена"
            
            self._record_state_change(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_state,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                extra_data=data
            )
            
            self.db.refresh(transaction)
            
            # Проверка балансов напрямую из БД после всех операций
            try:
                fresh_escrow_wallet = self.db.query(Wallet).filter(
                    Wallet.user_id == 0,
                    Wallet.is_default == True
                ).first()
                
                fresh_seller_wallet = self.db.query(Wallet).filter(
                    Wallet.user_id == transaction.seller_id,
                    Wallet.status == WalletStatus.ACTIVE
                ).first()
                
                if fresh_escrow_wallet:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] Проверка из БД: Escrow кошелек ID={fresh_escrow_wallet.id}, баланс={fresh_escrow_wallet.balances.get(transaction.currency, 0)}")
                
                if fresh_seller_wallet:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] Проверка из БД: Кошелек продавца ID={fresh_seller_wallet.id}, баланс={fresh_seller_wallet.balances.get(transaction.currency, 0)}")
                    
                # Проверяем историю транзакций кошелька
                recent_wallet_transactions = self.db.query(WalletTransaction).filter(
                    WalletTransaction.transaction_id == transaction.id
                ).order_by(WalletTransaction.id.desc()).limit(5).all()
                
                logger.info(f"[ОТЛАДКА БАЛАНСОВ] Последние транзакции кошельков для транзакции {transaction.id}:")
                for wt in recent_wallet_transactions:
                    logger.info(f"[ОТЛАДКА БАЛАНСОВ] - Кошелек ID={wt.wallet_id}, тип={wt.type}, сумма={wt.amount}, balance_before={wt.balance_before}, balance_after={wt.balance_after}")
            except Exception as e:
                logger.error(f"[ОТЛАДКА БАЛАНСОВ] Ошибка при проверке балансов из БД: {str(e)}")
            
            return transaction
            
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при завершении транзакции: {str(e)}")
            raise
    
    async def refund_transaction(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Возврат средств покупателю
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Получаем кошельки покупателя и Escrow
        buyer_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == transaction.buyer_id,
            Wallet.status == WalletStatus.ACTIVE
        ).first()
        
        if not buyer_wallet:
            raise ValueError(f"Активный кошелек покупателя не найден")
        
        # Проверяем наличие валюты в balances кошелька
        if transaction.currency not in buyer_wallet.balances:
            # Инициализируем баланс для этой валюты
            buyer_wallet.balances[transaction.currency] = 0.0
        
        escrow_wallet = self.db.query(Wallet).filter(
            Wallet.user_id == 0,
            Wallet.is_default == True
        ).first()
        
        if not escrow_wallet:
            raise ValueError("Системный Escrow кошелек не найден")
            
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Начало refund_transaction для транзакции {transaction_id}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Сумма транзакции: {transaction.amount}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}")
        logger.info(f"[ОТЛАДКА БАЛАНСОВ] Текущий баланс покупателя: {buyer_wallet.balances.get(transaction.currency, 0)}")
            
        # Выполняем переход состояния
        try:
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(TransactionEvent.REFUND, data)
            
            # Если переход успешен, обновляем базу данных
            # Списываем с Escrow кошелька
            escrow_current_balance = escrow_wallet.balances.get(transaction.currency, 0)
            escrow_wallet.balances[transaction.currency] = escrow_current_balance - transaction.amount
            # Маркируем балансы как измененные для SQLAlchemy
            escrow_wallet.balances = dict(escrow_wallet.balances)
            flag_modified(escrow_wallet, "balances")
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После списания с Escrow: баланс Escrow стал {escrow_wallet.balances.get(transaction.currency, 0)}")
            
            # Создаем запись в истории кошелька Escrow
            escrow_wallet_transaction = WalletTransaction(
                wallet_id=escrow_wallet.id,
                transaction_id=transaction.id,
                amount=-transaction.amount,
                currency=transaction.currency,
                balance_before=escrow_current_balance,
                balance_after=escrow_wallet.balances.get(transaction.currency, 0),
                type="debit",
                description=f"Списание средств из Escrow для возврата покупателю (ID: {transaction.id})"
            )
            self.db.add(escrow_wallet_transaction)
            
            # Пополняем кошелек покупателя
            buyer_current_balance = buyer_wallet.balances.get(transaction.currency, 0)
            buyer_wallet.balances[transaction.currency] = buyer_current_balance + transaction.amount
            # Маркируем балансы как измененные для SQLAlchemy
            buyer_wallet.balances = dict(buyer_wallet.balances)
            flag_modified(buyer_wallet, "balances")
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После зачисления покупателю: баланс покупателя стал {buyer_wallet.balances.get(transaction.currency, 0)}")
            
            # Создаем запись в истории кошелька покупателя
            buyer_wallet_transaction = WalletTransaction(
                wallet_id=buyer_wallet.id,
                transaction_id=transaction.id,
                amount=transaction.amount,
                currency=transaction.currency,
                balance_before=buyer_current_balance,
                balance_after=buyer_wallet.balances.get(transaction.currency, 0),
                type="credit",
                description=f"Возврат средств (ID: {transaction.id})"
            )
            self.db.add(buyer_wallet_transaction)
            
            # Обновляем состояние транзакции в БД
            transaction.status = new_state
            flag_modified(transaction, "status")
            
            # Сохраняем все изменения
            self.db.commit()
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После commit: баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}, баланс покупателя: {buyer_wallet.balances.get(transaction.currency, 0)}")
            
            # Проверяем сохранились ли изменения
            self.db.refresh(escrow_wallet)
            self.db.refresh(buyer_wallet)
            
            logger.info(f"[ОТЛАДКА БАЛАНСОВ] После refresh: баланс Escrow: {escrow_wallet.balances.get(transaction.currency, 0)}, баланс покупателя: {buyer_wallet.balances.get(transaction.currency, 0)}")
            
            # Записываем изменение статуса в историю
            initiator_id = data.get("initiator_id") if data else None
            initiator_type = data.get("initiator_type", "user") if data else "system"
            reason = data.get("reason") if data else "Возврат средств покупателю"
            
            self._record_state_change(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_state,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                extra_data=data
            )
            
            self.db.refresh(transaction)
            
            return transaction
            
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при возврате средств: {str(e)}")
            raise
    
    async def dispute_transaction(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Открытие спора по транзакции
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Выполняем переход состояния
        try:
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(TransactionEvent.DISPUTE, data)
            
            # Если переход успешен, обновляем базу данных
            transaction.status = new_state
            transaction.disputed_at = datetime.utcnow()
            if data and "reason" in data:
                transaction.dispute_reason = data["reason"]
            if data and "evidence" in data:
                transaction.dispute_evidence = data["evidence"]
            
            # Сохраняем все изменения
            self.db.commit()
            
            # Записываем изменение статуса в историю
            initiator_id = data.get("initiator_id") if data else None
            initiator_type = data.get("initiator_type", "user") if data else "system"
            reason = data.get("reason") if data else "Открыт спор по транзакции"
            
            self._record_state_change(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_state,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                extra_data=data
            )
            
            self.db.refresh(transaction)
            
            return transaction
            
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при открытии спора: {str(e)}")
            raise
    
    async def resolve_dispute(self, transaction_id: int, in_favor_of_seller: bool, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Разрешение спора по транзакции
        
        Args:
            transaction_id: ID транзакции
            in_favor_of_seller: Разрешение в пользу продавца (True) или покупателя (False)
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Выполняем переход состояния
        try:
            # Определяем, какой переход нужно выполнить в зависимости от решения
            event = TransactionEvent.RESOLVE_IN_FAVOR_OF_SELLER if in_favor_of_seller else TransactionEvent.RESOLVE_IN_FAVOR_OF_BUYER
            
            # Дополняем данные информацией о решении
            full_data = data or {}
            full_data["in_favor_of_seller"] = in_favor_of_seller
            
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(event, full_data)
            
            # Если переход успешен, обновляем базу данных
            transaction.status = new_state
            transaction.resolved_at = datetime.utcnow()
            transaction.resolution_type = "seller" if in_favor_of_seller else "buyer"
            
            if full_data and "resolution" in full_data:
                transaction.resolution_details = full_data["resolution"]
            
            # Выполняем соответствующее действие в зависимости от решения
            if in_favor_of_seller:
                # Вызываем метод complete_transaction для завершения транзакции
                # с другими параметрами инициализации для записи в историю
                resolution_data = {
                    "initiator_id": full_data.get("initiator_id"),
                    "initiator_type": "admin",
                    "reason": full_data.get("resolution", "Спор разрешен в пользу продавца")
                }
                return await self.complete_transaction(transaction_id, resolution_data)
            else:
                # Вызываем метод refund_transaction для возврата средств
                # с другими параметрами инициализации для записи в историю
                resolution_data = {
                    "initiator_id": full_data.get("initiator_id"),
                    "initiator_type": "admin",
                    "reason": full_data.get("resolution", "Спор разрешен в пользу покупателя")
                }
                return await self.refund_transaction(transaction_id, resolution_data)
                
            # Записываем изменение статуса в историю
            initiator_id = full_data.get("initiator_id")
            initiator_type = "admin"
            reason = full_data.get("resolution", "Спор разрешен в пользу " + ("продавца" if in_favor_of_seller else "покупателя"))
            
            self._record_state_change(
                transaction_id=transaction_id,
                previous_status=previous_status,
                new_status=new_state,
                initiator_id=initiator_id,
                initiator_type=initiator_type,
                reason=reason,
                metadata=full_data
            )
                
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при разрешении спора: {str(e)}")
            raise
    
    async def cancel_transaction(self, transaction_id: int, data: Optional[Dict[str, Any]] = None) -> Transaction:
        """
        Отмена транзакции
        
        Args:
            transaction_id: ID транзакции
            data: Дополнительные данные
            
        Returns:
            Обновленная транзакция
            
        Raises:
            ValueError: Если транзакция не найдена
            InvalidTransitionError: Если переход недопустим
        """
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Транзакция с ID {transaction_id} не найдена")
        
        # Сохраняем предыдущий статус
        previous_status = transaction.status
        
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Если транзакция находится в статусе ESCROW_HELD, нужно вернуть средства
        needs_refund = transaction.status == TransactionStatus.ESCROW_HELD
        
        # Выполняем переход состояния
        try:
            # Выполняем переход состояния в конечном автомате
            new_state = state_machine.trigger(TransactionEvent.CANCEL, data)
            
            if needs_refund:
                # Создаем новые данные для рефанда с сохранением оригинальных данных
                refund_data = data.copy() if data else {}
                refund_data["reason"] = refund_data.get("reason", "Отмена транзакции")
                refund_data["canceled"] = True
                
                # Вызываем метод возврата средств с указанной причиной
                return await self.refund_transaction(transaction_id, refund_data)
            else:
                # Просто обновляем статус транзакции
                transaction.status = new_state
                transaction.canceled_at = datetime.utcnow()
                if data and "reason" in data:
                    transaction.cancel_reason = data["reason"]
                
                # Сохраняем все изменения
                self.db.commit()
                
                # Записываем изменение статуса в историю
                initiator_id = data.get("initiator_id") if data else None
                initiator_type = data.get("initiator_type", "user") if data else "system"
                reason = data.get("reason") if data else "Транзакция отменена"
                
                self._record_state_change(
                    transaction_id=transaction_id,
                    previous_status=previous_status,
                    new_status=new_state,
                    initiator_id=initiator_id,
                    initiator_type=initiator_type,
                    reason=reason,
                    extra_data=data
                )
                
                self.db.refresh(transaction)
                
                return transaction
                
        except InvalidTransitionError as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при отмене транзакции: {str(e)}")
            raise
    
    async def get_available_actions(self, transaction_id: int) -> List[str]:
        """
        Получение списка доступных действий для транзакции
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            Список доступных действий
            
        Raises:
            ValueError: Если транзакция не найдена
        """
        # Получаем конечный автомат
        state_machine = await self.get_transaction_state_machine(transaction_id)
        
        # Получаем доступные события
        available_events = state_machine.get_available_events()
        
        # Преобразуем события в действия для пользовательского интерфейса
        action_map = {
            TransactionEvent.PROCESS_PAYMENT: "process_payment",
            TransactionEvent.RELEASE_FROM_ESCROW: "complete",
            TransactionEvent.REFUND: "refund",
            TransactionEvent.DISPUTE: "dispute",
            TransactionEvent.RESOLVE_DISPUTE: "resolve_dispute",
            TransactionEvent.CANCEL: "cancel",
            TransactionEvent.FAIL: "fail"
        }
        
        return [action_map[event] for event in available_events]

# Фабрика для получения сервиса
def get_transaction_state_service(db: Session) -> TransactionStateService:
    """
    Получение экземпляра сервиса управления состояниями транзакций
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Экземпляр TransactionStateService
    """
    return TransactionStateService(db) 