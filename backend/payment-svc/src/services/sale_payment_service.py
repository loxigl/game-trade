"""
Сервис для обработки платежей по продажам
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from ..models.core import Sale, SaleStatus
from ..models.transaction import Transaction, TransactionStatus
from ..services.wallet_service import WalletService
from ..models.wallet import Wallet, WalletStatus
from ..services.statistics_service import get_statistics_service
from ..services.rabbitmq_service import get_rabbitmq_service

class SalePaymentService:
    """
    Сервис для управления платежами по продажам
    """
    def __init__(self, db: Session):
        self.db = db
        self.wallet_service = WalletService(db)
    
    async def initiate_payment(
        self,
        sale_id: int,
        wallet_id: int
    ) -> Dict[str, Any]:
        """
        Инициировать платеж по продаже
        
        Args:
            sale_id: ID продажи
            wallet_id: ID кошелька покупателя
            
        Returns:
            Информация о созданной транзакции
            
        Raises:
            ValueError: Если продажа не найдена или недоступна для оплаты
        """
        # Получаем продажу
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.status == SaleStatus.PENDING.value
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или недоступна для оплаты")
        
        # Проверяем баланс покупателя
        wallet_balance = await self.wallet_service.get_wallet_balance(wallet_id)
        if wallet_balance.get(sale.currency, 0) < sale.price:
            raise ValueError("Недостаточно средств на кошельке")
        
        # Создаем транзакцию
        transaction = await self._create_transaction(sale, wallet_id)
        
        # Обновляем статус продажи
        sale.transaction_id = transaction.id
        sale.status = SaleStatus.PAYMENT_PROCESSING
        sale.updated_at = datetime.now()
        
        # Списываем средства с кошелька покупателя
        from ..schemas.wallet import WalletTransactionCreate, Currency
        
        try:
            # Создаем транзакцию списания с кошелька покупателя
            await self.wallet_service.create_wallet_transaction(
                WalletTransactionCreate(
                    wallet_id=wallet_id,
                    amount=sale.price,
                    currency=Currency(sale.currency),
                    type="debit",
                    description=f"Оплата заказа #{sale_id} и перевод на эскроу",
                    extra_data={
                        "sale_id": sale.id,
                        "transaction_id": transaction.id,
                        "type": "escrow_payment"
                    },
                    transaction_id=transaction.id
                )
            )
            
            # Находим или создаем системный кошелек эскроу
            escrow_wallet = await self.get_escrow_wallet()
            
            # Переводим средства на эскроу-счет
            await self.wallet_service.create_wallet_transaction(
                WalletTransactionCreate(
                    wallet_id=escrow_wallet.id,
                    amount=sale.price,
                    currency=Currency(sale.currency),
                    type="credit",
                    description=f"Получение средств на эскроу для заказа #{sale_id}",
                    extra_data={
                        "sale_id": sale.id,
                        "transaction_id": transaction.id,
                        "buyer_id": sale.buyer_id,
                        "seller_id": sale.seller_id,
                        "type": "escrow_receive"
                    },
                    transaction_id=transaction.id
                )
            )
            
            # Обновляем extra_data транзакции
            transaction_extra_data = transaction.extra_data or {}
            transaction_extra_data.update({
                "escrow_funded": True,
                "escrow_funded_at": datetime.now().isoformat(),
                "wallet_id": wallet_id,
                "escrow_wallet_id": escrow_wallet.id
            })
            transaction.extra_data = transaction_extra_data
            
        except Exception as e:
            # В случае ошибки отменяем транзакцию и возвращаем статус продажи
            self.db.rollback()
            raise ValueError(f"Ошибка при списании средств: {str(e)}")
        
        self.db.commit()
        self.db.refresh(sale)
        self.db.refresh(transaction)
        
        return {
            "sale": self._format_sale_response(sale),
            "transaction": self._format_transaction_response(transaction)
        }
    
    async def confirm_payment(
        self,
        sale_id: int,
        transaction_id: int
    ) -> Dict[str, Any]:
        """
        Подтвердить платеж по продаже
        
        Args:
            sale_id: ID продажи
            transaction_id: ID транзакции
            
        Returns:
            Обновленная информация о продаже и транзакции
            
        Raises:
            ValueError: Если продажа или транзакция не найдены
        """
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.transaction_id == transaction_id,
            Sale.status == SaleStatus.PAYMENT_PROCESSING
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или недоступна для подтверждения")
        
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.status == TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            raise ValueError("Транзакция не найдена или уже обработана")
        
        # Проверяем, что средства были переведены на эскроу
        if not transaction.extra_data or not transaction.extra_data.get("escrow_funded"):
            raise ValueError("Эскроу-платеж не был инициирован. Необходимо сначала выполнить перевод средств на эскроу")
        
        # Обновляем статусы
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.now()
        
        # Обновляем информацию об эскроу-платеже
        transaction_extra_data = transaction.extra_data or {}
        transaction_extra_data.update({
            "escrow_confirmed": True,
            "escrow_confirmed_at": datetime.now().isoformat()
        })
        transaction.extra_data = transaction_extra_data
        
        sale.status = SaleStatus.DELIVERY_PENDING
        sale.updated_at = datetime.now()
        
        # Обновляем extra_data продажи
        sale_extra_data = sale.extra_data or {}
        sale_extra_data.update({
            "payment_confirmed": True,
            "payment_confirmed_at": datetime.now().isoformat(),
            "escrow_status": "active"
        })
        sale.extra_data = sale_extra_data
        
        self.db.commit()
        self.db.refresh(sale)
        self.db.refresh(transaction)
        
        # Отправляем уведомление о подтверждении платежа
        try:
            rabbitmq_service = get_rabbitmq_service()
            notification_data = {
                "event_type": "payment_confirmed",
                "sale_id": sale_id,
                "transaction_id": transaction_id,
                "buyer_id": sale.buyer_id,
                "seller_id": sale.seller_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "timestamp": datetime.now().isoformat(),
                "escrow_status": "active"
            }
            
            await rabbitmq_service.publish(
                exchange="notification_events",
                routing_key="notification.payment.confirmed",
                message=notification_data
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка при отправке уведомления о подтверждении платежа: {str(e)}")
        
        return {
            "sale": self._format_sale_response(sale),
            "transaction": self._format_transaction_response(transaction)
        }
    
    async def reject_payment(
        self,
        sale_id: int,
        transaction_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отклонить платеж по продаже
        
        Args:
            sale_id: ID продажи
            transaction_id: ID транзакции
            reason: Причина отклонения (опционально)
            
        Returns:
            Обновленная информация о продаже и транзакции
            
        Raises:
            ValueError: Если продажа или транзакция не найдены
        """
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.transaction_id == transaction_id,
            Sale.status == SaleStatus.PAYMENT_PROCESSING
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или недоступна для отклонения")
        
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.status == TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            raise ValueError("Транзакция не найдена или уже обработана")
        
        # Обновляем статусы
        transaction.status = TransactionStatus.REJECTED
        transaction.updated_at = datetime.now()
        
        # Обновляем extra_data для транзакции
        if reason:
            transaction_extra_data = transaction.extra_data or {}
            transaction_extra_data["rejection_reason"] = reason
            transaction.extra_data = transaction_extra_data
        
        sale.status = SaleStatus.CANCELED
        sale.updated_at = datetime.now()
        
        # Обновляем extra_data для продажи
        if reason:
            sale_extra_data = sale.extra_data or {}
            sale_extra_data["cancellation_reason"] = reason
            sale.extra_data = sale_extra_data
        
        self.db.commit()
        self.db.refresh(sale)
        self.db.refresh(transaction)
        
        return {
            "sale": self._format_sale_response(sale),
            "transaction": self._format_transaction_response(transaction)
        }
    
    async def   _create_transaction(self, sale: Sale, wallet_id: int) -> Transaction:
        """
        Создать транзакцию для продажи
        
        Args:
            sale: Объект продажи
            wallet_id: ID кошелька покупателя
            
        Returns:
            Созданная транзакция
        """
        transaction = Transaction(
            buyer_id=sale.buyer_id,
            seller_id=sale.seller_id,
            listing_id=sale.listing_id,
            item_id=None,
            amount=sale.price,
            currency=sale.currency,
            type="purchase",
            status=TransactionStatus.PENDING,
            description=f"Оплата за товар из объявления #{sale.listing_id}",
            extra_data={
                "sale_id": sale.id,
                "wallet_id": wallet_id
            }
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction
    
    def _format_sale_response(self, sale: Sale) -> Dict[str, Any]:
        """
        Форматировать информацию о продаже для ответа
        
        Args:
            sale: Объект продажи
            
        Returns:
            Отформатированная информация о продаже
        """
        return {
            "id": sale.id,
            "listing_id": sale.listing_id,
            "buyer_id": sale.buyer_id,
            "seller_id": sale.seller_id,
            "price": sale.price,
            "currency": sale.currency,
            "status": sale.status,
            "created_at": sale.created_at.isoformat(),
            "updated_at": sale.updated_at.isoformat() if sale.updated_at else None,
            "completed_at": sale.completed_at.isoformat() if sale.completed_at else None,
            "transaction_id": sale.transaction_id,
            "extra_data": sale.extra_data
        }
    
    def _format_transaction_response(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Форматировать информацию о транзакции для ответа
        
        Args:
            transaction: Объект транзакции
            
        Returns:
            Отформатированная информация о транзакции
        """
        return {
            "id": transaction.id,
            "buyer_id": transaction.buyer_id,
            "seller_id": transaction.seller_id,
            "listing_id": transaction.listing_id,
            "item_id": transaction.item_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "type": transaction.type,
            "status": transaction.status,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
            "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
            "description": transaction.description,
            "extra_data": transaction.extra_data
        }
    
    async def complete_delivery(
        self,
        sale_id: int,
        transaction_id: int,
        buyer_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Подтвердить завершение доставки и успешное выполнение заказа,
        перевести средства продавцу и обновить статистику
        
        Args:
            sale_id: ID продажи
            transaction_id: ID транзакции
            buyer_comment: Комментарий покупателя (опционально)
            
        Returns:
            Обновленная информация о продаже и транзакции
            
        Raises:
            ValueError: Если продажа или транзакция не найдены или не в статусе ожидания доставки
        """
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.transaction_id == transaction_id,
            Sale.status == SaleStatus.DELIVERY_PENDING
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или недоступна для подтверждения доставки")
        
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.status == TransactionStatus.COMPLETED
        ).first()
        
        if not transaction:
            raise ValueError("Транзакция не найдена или в неправильном статусе")
        
        # Проверяем, что эскроу-платеж был инициирован
        if not transaction.extra_data or not transaction.extra_data.get("escrow_funded"):
            raise ValueError("Эскроу-платеж не был инициирован для этой продажи")
        
        # Обновляем статусы
        sale.status = SaleStatus.COMPLETED
        sale.updated_at = datetime.now()
        sale.completed_at = datetime.now()
        
        # Обновляем extra_data с комментарием покупателя и информацией об эскроу
        sale_extra_data = sale.extra_data or {}
        sale_extra_data.update({
            "buyer_completion_comment": buyer_comment,
            "completion_date": datetime.now().isoformat(),
            "escrow_status": "ready_for_release"
        })
        sale.extra_data = sale_extra_data
        
        # Обновляем информацию об эскроу в транзакции
        transaction_extra_data = transaction.extra_data or {}
        transaction_extra_data.update({
            "delivery_completed": True,
            "delivery_completed_at": datetime.now().isoformat(),
            "escrow_status": "ready_for_release"
        })
        transaction.extra_data = transaction_extra_data
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(sale)
        self.db.refresh(transaction)
        
        # Добавляем запись в статистику
        try:
            statistics_service = get_statistics_service(self.db)
            await statistics_service.record_sale_completion(sale_id, transaction.seller_id, transaction.buyer_id)
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка при обновлении статистики: {str(e)}")
        
        # Отправляем уведомление в RabbitMQ для открытия чата
        try:
            chat_data = {
                "event_type": "open_completion_chat",
                "sale_id": sale_id,
                "buyer_id": sale.buyer_id,
                "seller_id": sale.seller_id,
                "transaction_id": transaction_id,
                "timestamp": datetime.now().isoformat(),
                "listing_id": sale.listing_id,
                "escrow_status": "ready_for_release"
            }
            
            rabbitmq_service = get_rabbitmq_service()
            await rabbitmq_service.publish(
                exchange="notification_events",
                routing_key="notification.chat.required",
                message=chat_data
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка при отправке уведомления в чат: {str(e)}")
        
        return {
            "sale": self._format_sale_response(sale),
            "transaction": self._format_transaction_response(transaction),
            "status": "success",
            "message": "Доставка подтверждена, заказ успешно завершен",
            "escrow_status": "ready_for_release"
        }
    
    async def request_funds_release(
        self,
        sale_id: int,
        transaction_id: int,
        wallet_id: int,
        withdrawal_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Запрос продавца на вывод средств после завершения продажи и эскроу
        
        Args:
            sale_id: ID продажи
            transaction_id: ID транзакции
            wallet_id: ID кошелька продавца для вывода средств
            withdrawal_details: Детали вывода средств (опционально)
            
        Returns:
            Информация о запросе на вывод средств
            
        Raises:
            ValueError: Если продажа не завершена или средства уже выведены
        """
        # Проверяем, что продажа существует и имеет правильный статус
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.transaction_id == transaction_id,
            Sale.status == SaleStatus.COMPLETED
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или не имеет статуса 'завершено'")
        
        # Проверяем, что транзакция существует и имеет правильный статус
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.seller_id == sale.seller_id
        ).first()
        
        if not transaction:
            raise ValueError("Транзакция не найдена или не связана с этим продавцом")
        
        # Проверяем, что средства не были уже выведены
        if transaction.extra_data and transaction.extra_data.get("funds_released"):
            raise ValueError("Средства уже были выведены для этой продажи")
        
        # Расчет суммы для вывода (сумма транзакции за вычетом комиссии)
        final_amount = transaction.amount
        if transaction.fee_amount:
            final_amount -= transaction.fee_amount
            
        from ..services.wallet_service import get_wallet_service
        wallet_service = get_wallet_service(self.db)
        
        # Проверяем, что кошелек принадлежит продавцу
        wallet = await wallet_service.get_wallet(wallet_id)
        if wallet.user_id != sale.seller_id:
            raise ValueError("Указанный кошелек не принадлежит продавцу")
        
        # Находим эскроу-кошелек
        escrow_wallet_id = transaction.extra_data.get("escrow_wallet_id") if transaction.extra_data else None
        if not escrow_wallet_id:
            raise ValueError("Информация об эскроу-кошельке отсутствует в транзакции")
            
        try:
            escrow_wallet = await wallet_service.get_wallet(escrow_wallet_id)
        except:
            raise ValueError("Эскроу-кошелек не найден")
            
        # Проверяем, что на эскроу-кошельке достаточно средств
        escrow_balance = await wallet_service.get_wallet_balance(escrow_wallet.id)
        if escrow_balance.get(transaction.currency, 0) < final_amount:
            raise ValueError(f"Недостаточно средств на эскроу-кошельке: {escrow_balance.get(transaction.currency, 0)} < {final_amount}")
        
        from ..schemas.wallet import Currency
        from ..schemas.wallet import WalletTransactionCreate
        
        try:
            # Списываем средства с эскроу-кошелька
            await wallet_service.create_wallet_transaction(
                WalletTransactionCreate(
                    wallet_id=escrow_wallet.id,
                    amount=final_amount,
                    currency=Currency(transaction.currency),
                    type="debit",
                    description=f"Списание средств с эскроу для продажи #{sale_id} (транзакция #{transaction_id})",
                    extra_data={
                        "sale_id": sale_id,
                        "transaction_id": transaction_id,
                        "seller_id": sale.seller_id,
                        "type": "escrow_release"
                    },
                    transaction_id=transaction_id
                )
            )
            
            # Добавляем средства на баланс кошелька продавца
            wallet_transaction = await wallet_service.create_wallet_transaction(
                WalletTransactionCreate(
                    wallet_id=wallet_id,
                    amount=final_amount,
                    currency=Currency(transaction.currency),
                    type="credit",
                    description=f"Получение средств от продажи #{sale_id} (транзакция #{transaction_id})",
                    reference_id=str(transaction_id),
                    extra_data={
                        "sale_id": sale_id,
                        "transaction_id": transaction_id,
                        "escrow_wallet_id": escrow_wallet.id,
                        "type": "seller_receive_from_escrow"
                    }
                )
            )
            
            # Обновляем данные транзакции и продажи
            transaction.extra_data = transaction.extra_data or {}
            transaction.extra_data["funds_released"] = True
            transaction.extra_data["funds_released_at"] = datetime.now().isoformat()
            transaction.extra_data["funds_released_to_wallet_id"] = wallet_id
            transaction.extra_data["escrow_status"] = "released"
            
            sale.extra_data = sale.extra_data or {}
            sale.extra_data["funds_released"] = True
            sale.extra_data["funds_released_at"] = datetime.now().isoformat()
            sale.extra_data["escrow_status"] = "released"
            
            self.db.commit()
            
            # Отправляем уведомление о выводе средств
            try:
                rabbitmq_service = get_rabbitmq_service()
                notification_data = {
                    "event_type": "funds_released",
                    "sale_id": sale_id,
                    "transaction_id": transaction_id,
                    "seller_id": sale.seller_id,
                    "amount": final_amount,
                    "currency": transaction.currency,
                    "timestamp": datetime.now().isoformat(),
                    "escrow_status": "released"
                }
                
                await rabbitmq_service.publish(
                    exchange="notification_events",
                    routing_key="notification.funds.released",
                    message=notification_data
                )
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                print(f"Ошибка при отправке уведомления о выводе средств: {str(e)}")
            
            return {
                "status": "success",
                "message": "Средства успешно зачислены на баланс кошелька",
                "sale_id": sale_id,
                "transaction_id": transaction_id,
                "amount": final_amount,
                "currency": transaction.currency,
                "wallet_id": wallet_id,
                "wallet_transaction_id": wallet_transaction.id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Ошибка при выводе средств: {str(e)}")
    
    async def get_escrow_wallet(self) -> Wallet:
        """
        Получает или создает системный кошелек эскроу
        
        Returns:
            Объект кошелька эскроу
        """
        # Находим системный кошелек эскроу
        escrow_wallet = self.db.query(Wallet).filter(Wallet.user_id == 0).first()
        
        # Если кошелек не существует, создаем его
        if not escrow_wallet:
            escrow_wallet = Wallet(
                user_id=0,  # Системный пользователь для эскроу
                balances={},
                limits=None,
                status=WalletStatus.ACTIVE,
                is_default=True,
                notes="Системный эскроу-кошелек"
            )
            self.db.add(escrow_wallet)
            self.db.commit()
            self.db.refresh(escrow_wallet)
        
        return escrow_wallet 