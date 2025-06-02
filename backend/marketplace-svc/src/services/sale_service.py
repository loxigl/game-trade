"""
Сервис для работы с продажами
"""
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta, timezone
from ..models.core import Sale, SaleStatus, Listing, User, Chat, Wallet, Transaction, TransactionStatus
from ..database.connection import get_db
from ..config.settings import get_settings
from .rabbitmq_service import get_rabbitmq_service
from .chat_client import get_chat_client
#from ..services.chat_service import ChatService
import logging

logger = logging.getLogger(__name__)
class SaleService:
    """
    Сервис для управления продажами
    """
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.rabbitmq = get_rabbitmq_service()
        self.chat_client = get_chat_client()
        # self.chat_service = ChatService(db)
        # Регистрируем обработчик для получения подтверждения о завершении транзакции
        asyncio.create_task(self._setup_message_handlers())
    
    async def _setup_message_handlers(self):
        """Настройка обработчиков сообщений RabbitMQ"""
        try:
            # Регистрируем обработчик для подтверждения завершения транзакции
            await self.rabbitmq.create_consumer(
                exchange_name=self.settings.RABBITMQ_EXCHANGE,
                queue_name="marketplace_sales_transaction_completed",
                routing_key="sales.transaction_completed",
                callback=self._handle_transaction_completed
            )
            logger.info("Registered transaction completion handler")
            
            # Регистрируем обработчик для события перевода средств в Escrow
            await self.rabbitmq.create_consumer(
                exchange_name=self.settings.RABBITMQ_EXCHANGE,
                queue_name="marketplace_escrow_funds_held",
                routing_key="escrow.funds_held",
                callback=self._handle_escrow_funds_held
            )
            logger.info("Registered escrow funds held handler")
        except Exception as e:
            logger.error(f"Error setting up message handlers: {str(e)}")
    
    async def _handle_transaction_completed(self, message: Dict[str, Any]):
        """
        Обработчик подтверждения завершения транзакции
        
        Args:
            message: Данные сообщения
        """
        logger.info(f"Received transaction completion confirmation: {message}")
        
        try:
            sale_id = message.get("sale_id")
            if not sale_id:
                logger.error("Missing sale_id in transaction completion message")
                return
            
            # Получаем продажу
            sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
            if not sale:
                logger.error(f"Sale {sale_id} not found")
                return
            
            # Обновляем информацию о транзакции
            if not sale.extra_data:
                sale.extra_data = {}
            
            sale.extra_data["transaction_completion"] = {
                "transaction_id": message.get("transaction_id"),
                "completed_at": message.get("completed_at"),
                "status": message.get("status"),
                "received_at": datetime.now().isoformat()
            }
            
            self.db.commit()
            logger.info(f"Updated sale {sale_id} with transaction completion info")
            
        except Exception as e:
            logger.error(f"Error handling transaction completion: {str(e)}")
            self.db.rollback()
    
    async def _handle_escrow_funds_held(self, message: Dict[str, Any]):
        """
        Обработчик события перевода средств в Escrow
        
        Args:
            message: Данные сообщения
        """
        logger.info(f"Received escrow funds held event: {message}")
        
        try:
            # Получаем данные из сообщения
            # transaction_id может быть как в корне сообщения, так и в поле data
            transaction_id = None
            
            # Получаем transaction_id
            if "transaction_id" in message:
                transaction_id = message.get("transaction_id")
            elif "data" in message and "transaction_id" in message["data"]:
                transaction_id = message["data"].get("transaction_id")
            
            logger.info(f"Извлеченный transaction_id: {transaction_id}")
            
            if not transaction_id:
                logger.error("Missing transaction_id in escrow funds held message")
                return
            
            logger.info(f"Ищем продажу для transaction_id={transaction_id}")
            
            # Извлекаем sale_id из сообщения - ПРИОРИТЕТ №1
            sale_id = None
            if "sale_id" in message:
                sale_id = message.get("sale_id")
            elif "data" in message and "sale_id" in message["data"]:
                sale_id = message["data"].get("sale_id")
            elif "data" in message and "data" in message["data"] and "sale_id" in message["data"]["data"]:
                sale_id = message["data"]["data"].get("sale_id")
            
            # Извлекаем необходимые данные для идентификации правильной продажи
            listing_id = None
            buyer_id = None
            seller_id = None
            
            # Извлекаем данные из разных мест сообщения
            if "listing_id" in message:
                listing_id = message.get("listing_id")
            if "buyer_id" in message:
                buyer_id = message.get("buyer_id")
            if "seller_id" in message:
                seller_id = message.get("seller_id")
                
            # Пробуем извлечь данные из вложенных структур
            if "data" in message:
                data = message["data"]
                if "listing_id" in data and not listing_id:
                    listing_id = data.get("listing_id")
                if "buyer_id" in data and not buyer_id:
                    buyer_id = data.get("buyer_id")
                if "seller_id" in data and not seller_id:
                    seller_id = data.get("seller_id")
                
                # Проверяем еще глубже вложенную структуру, если есть
                if "data" in data:
                    nested_data = data["data"]
                    if "listing_id" in nested_data and not listing_id:
                        listing_id = nested_data.get("listing_id")
                    if "buyer_id" in nested_data and not buyer_id:
                        buyer_id = nested_data.get("buyer_id")
                    if "seller_id" in nested_data and not seller_id:
                        seller_id = nested_data.get("seller_id")
            
            # Сначала проверяем, существует ли уже транзакция
            transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
            
            # Если транзакция не существует, сначала создаем её
            if not transaction:
                logger.info(f"Транзакция с ID={transaction_id} не найдена, создаем")
                
                # Извлекаем данные для транзакции из сообщения
                amount = 0.0
                currency = "USD"
                    
                # Пробуем извлечь дополнительные детали из вложенных структур
                if "data" in message:
                    if "amount" in message["data"]:
                        amount = float(message["data"].get("amount", 0))
                    if "currency" in message["data"]:
                        currency = message["data"].get("currency", "USD")
                
                # Создаем новую транзакцию
                try:
                    new_transaction = Transaction(
                        id=transaction_id,
                        listing_id=listing_id,
                        buyer_id=buyer_id,
                        seller_id=seller_id,
                        amount=amount,
                        currency=currency,
                        fee_amount=0.0,  # Устанавливаем базовые значения
                        status=TransactionStatus.PAID.value,  # Для escrow_held используем PAID
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    self.db.add(new_transaction)
                    self.db.commit()
                    logger.info(f"Создана новая транзакция ID={transaction_id} в marketplace-db")
                    transaction = new_transaction
                except Exception as e:
                    logger.error(f"Ошибка при создании транзакции: {str(e)}")
                    self.db.rollback()
                    # Если не удалось создать транзакцию, продолжить нельзя
                    return
            
            # Поиск продажи в следующем порядке приоритета:
            sale = None
            
            # 1. Если у нас есть sale_id, ищем по нему (приоритет #1)
            if sale_id:
                sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
                if sale:
                    logger.info(f"Найдена продажа по sale_id={sale_id}: id={sale.id}, status={sale.status}")
            
            # 2. Если продажа не найдена по sale_id, ищем по transaction_id
            if not sale:
                sale = self.db.query(Sale).filter(Sale.transaction_id == transaction_id).first()
                if sale:
                    logger.info(f"Найдена продажа по transaction_id={transaction_id}: id={sale.id}, status={sale.status}")
            
            # 3. Если продажа до сих пор не найдена, ищем по комбинации полей
            if not sale:
                logger.info(f"Продажа не найдена по sale_id или transaction_id, ищем по дополнительным параметрам")
                
                filters = [Sale.status == SaleStatus.PENDING.value]
                
                if listing_id:
                    filters.append(Sale.listing_id == listing_id)
                if buyer_id:
                    filters.append(Sale.buyer_id == buyer_id)
                if seller_id:
                    filters.append(Sale.seller_id == seller_id)
                
                # Если есть хоть какой-то фильтр кроме статуса, выполняем поиск
                if len(filters) > 1:
                    # Важно: берем САМУЮ НОВУЮ продажу по created_at
                    sale = self.db.query(Sale).filter(*filters).order_by(desc(Sale.created_at)).first()
                    
                    if sale:
                        logger.info(f"Найдена продажа по параметрам: id={sale.id}, buyer_id={sale.buyer_id}, seller_id={sale.seller_id}, listing_id={sale.listing_id}")
                    else:
                        # Если продажа не найдена даже с полными фильтрами, пробуем более простой поиск только по listing_id
                        if listing_id:
                            logger.info(f"Продажа не найдена по полным параметрам, ищем только по listing_id={listing_id}")
                            sale = self.db.query(Sale).filter(
                                Sale.listing_id == listing_id,
                                Sale.status == SaleStatus.PENDING.value
                            ).order_by(desc(Sale.created_at)).first()
            
            if not sale:
                logger.error(f"Не найдена подходящая продажа для транзакции {transaction_id}")
                return
            
            logger.info(f"Найдена продажа id={sale.id}, текущий status={sale.status}, transaction_id={sale.transaction_id}")
            
            # Обновляем статус продажи на "payment_processing"
            sale.status = SaleStatus.PAYMENT_PROCESSING.value
            
            # Сохраняем transaction_id если его еще нет
            if not sale.transaction_id:
                logger.info(f"Устанавливаем transaction_id={transaction_id} для продажи id={sale.id}")
                sale.transaction_id = transaction_id
            
            # Обновляем доп. информацию
            if not sale.extra_data:
                sale.extra_data = {}
            
            sale.extra_data["escrow_payment"] = {
                "transaction_id": transaction_id,
                "processed_at": datetime.now().isoformat(),
                "message": message
            }
            
            try:
                self.db.commit()
                logger.info(f"Updated sale {sale.id} status to PAYMENT_PROCESSING after escrow payment, transaction_id={sale.transaction_id}")
            except Exception as e:
                logger.error(f"Error updating sale with transaction: {str(e)}")
                self.db.rollback()
                # Проверяем, что может быть причиной ошибки внешнего ключа
                if "foreign key constraint" in str(e) and "sales_transaction_id_fkey" in str(e):
                    # Проверяем, что транзакция существует
                    t = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
                    if not t:
                        logger.error(f"Транзакция ID={transaction_id} все еще не существует после попытки создания")
            
            # Обновляем статус объявления, если необходимо
            try:
                listing = self.db.query(Listing).filter(Listing.id == sale.listing_id).first()
                if listing and listing.status == "active":
                    listing.status = "sold"
                    self.db.commit()
                    logger.info(f"Updated listing {listing.id} status to 'sold'")
            except Exception as e:
                logger.error(f"Error updating listing status: {str(e)}")
                # Не прерываем выполнение, так как основная задача - обновление статуса продажи
            
        except Exception as e:
            logger.error(f"Error handling escrow funds held: {str(e)}")
            self.db.rollback()
    
    async def initiate_sale(
        self,
        listing_id: int,
        buyer_id: int,
        wallet_id: Optional[int] = None,
        test_mode: bool = False  # Добавлен параметр для тестов
    ) -> Dict[str, Any]:
        """
        Инициировать продажу товара
        
        Args:
            listing_id: ID объявления
            buyer_id: ID покупателя
            wallet_id: ID кошелька покупателя (опционально)
            test_mode: Использовать тестовый режим (автоматически создает transaction_id)
            
        Returns:
            Информация о созданной продаже
            
        Raises:
            ValueError: Если объявление не найдено или недоступно для покупки
        """
        # Получаем объявление
        listing = self.db.query(Listing).filter(
            Listing.id == listing_id,
            Listing.status == 'active'
        ).first()
        
        if not listing:
            raise ValueError("Объявление не найдено или недоступно для покупки")
        
        # Проверяем, не является ли покупатель продавцом
        if listing.seller_id == buyer_id:
            raise ValueError("Нельзя купить свой собственный товар")
        
        # Создаем чат для общения покупателя и продавца
        chat = None
        try:
            # Получаем системный токен из настроек
            system_token = self.settings.SYSTEM_TOKEN
            
            chat = await self.chat_client.get_or_create_listing_chat(
                listing_id=listing_id,
                buyer_id=buyer_id,
                seller_id=listing.seller_id,
                listing_title=listing.title,
                system_token=system_token
            )
            
            if chat:
                logger.info(f"Chat created/found for listing {listing_id}: {chat.get('id')}")
            else:
                logger.warning(f"Failed to create chat for listing {listing_id}")
        except Exception as e:
            logger.error(f"Error creating chat for listing {listing_id}: {str(e)}")
            # Не прерываем создание продажи из-за ошибки чата
        
        # Получаем wallet_id, если он не был передан
        if wallet_id is None:
            wallet = self.db.query(Wallet).filter(Wallet.user_id == buyer_id).first()
            if wallet:
                wallet_id = wallet.id
        
        # Создаем запись о продаже
        sale = Sale(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            item_id=listing.item_id,
            price=listing.price,
            currency=listing.currency,
            status=SaleStatus.PENDING.value,
            chat_id=chat.get('id') if chat else None,  # Сохраняем ID чата
            description=f"Покупка товара из объявления #{listing.id}",
            extra_data={
                "listing_title": listing.title,
                "wallet_id": wallet_id,
                "chat_data": chat if chat else None  # Сохраняем данные чата в extra_data
            }
        )
        
        # Для тестирования: симулируем создание transaction_id
        # Временное решение, пока полный flow с payment-service не настроен
        if test_mode or self.settings.TEST_MODE:
            import random
            test_transaction_id = random.randint(1000, 9999)
            sale.transaction_id = test_transaction_id
            sale.status = SaleStatus.DELIVERY_PENDING.value  # Переводим в статус доставки для дальнейшего тестирования
            logger.info(f"TEST MODE: Создан тестовый transaction_id={test_transaction_id}")
        
        logger.info(f"Создается продажа: {sale}")
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)
        
        # Отправляем сообщение в RabbitMQ
        try:
            message = {
                "sale_id": sale.id,
                "listing_id": sale.listing_id,
                "buyer_id": sale.buyer_id,
                "seller_id": sale.seller_id,
                "price": float(sale.price),
                "currency": sale.currency,
                "status": sale.status,  # Уже является строковым значением
                "created_at": sale.created_at.isoformat(),
                "wallet_id": wallet_id,
                "transaction_id": sale.transaction_id  # Добавляем transaction_id если есть
            }
            
            await self.rabbitmq.publish(
                self.settings.RABBITMQ_EXCHANGE,
                self.settings.RABBITMQ_SALES_ROUTING_KEY,
                message
            )
            logger.info(f"Sale {sale.id} notification sent to RabbitMQ")
        except Exception as e:
            logger.error(f"Error sending sale notification to RabbitMQ: {str(e)}")
            # Не прерываем выполнение, так как продажа уже создана
        
        return self._format_sale_response(sale)
    
    async def get_sale(self, sale_id: int, user_id: int) -> Dict[str, Any]:
        """
        Получить информацию о продаже
        
        Args:
            sale_id: ID продажи
            user_id: ID пользователя, запрашивающего информацию
            
        Returns:
            Информация о продаже
            
        Raises:
            ValueError: Если продажа не найдена или пользователь не имеет к ней доступа
        """
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            or_(
                Sale.buyer_id == user_id,
                Sale.seller_id == user_id
            )
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или у вас нет к ней доступа")
        
        return self._format_sale_response(sale)
    
    async def get_user_sales(
        self,
        user_id: int,
        role: str = "buyer",  # или "seller"
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Получить список продаж пользователя
        
        Args:
            user_id: ID пользователя
            role: Роль пользователя в продажах ("buyer" или "seller")
            status: Фильтр по статусу (опционально)
            page: Номер страницы
            page_size: Размер страницы
            
        Returns:
            Список продаж с информацией о пагинации
        """
        query = self.db.query(Sale)
        
        # Фильтруем по роли
        if role == "buyer":
            query = query.filter(Sale.buyer_id == user_id)
        else:
            query = query.filter(Sale.seller_id == user_id)
        
        # Фильтруем по статусу, если указан
        if status:
            query = query.filter(Sale.status == status)
        
        # Подсчитываем общее количество
        total = query.count()
        
        # Применяем пагинацию
        sales = query.order_by(desc(Sale.created_at))\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        # Форматируем ответ
        items = [self._format_sale_response(sale) for sale in sales]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    
    async def update_sale_status(
        self,
        sale_id: int,
        user_id: int,
        new_status: SaleStatus,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обновить статус продажи
        
        Args:
            sale_id: ID продажи
            user_id: ID пользователя, обновляющего статус
            new_status: Новый статус
            reason: Причина изменения статуса (опционально)
            
        Returns:
            Обновленная информация о продаже
            
        Raises:
            ValueError: Если продажа не найдена или пользователь не имеет прав на изменение статуса
        """
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            or_(
                Sale.buyer_id == user_id,
                Sale.seller_id == user_id
            )
        ).first()
        
        if not sale:
            raise ValueError("Продажа не найдена или у вас нет прав на изменение её статуса")
        
        # Проверяем возможность изменения статуса
        if not self._can_update_status(sale.status, new_status, user_id == sale.seller_id):
            raise ValueError(f"Невозможно изменить статус с {sale.status} на {new_status}")
        
        # Обновляем статус
        sale.status = new_status
        sale.updated_at = datetime.now()
        
        if new_status == SaleStatus.COMPLETED:
            sale.completed_at = datetime.now()
            
            # Отправляем уведомление о завершении сделки в payment-service
            try:
                message = {
                    "sale_id": sale.id,
                    "transaction_id": sale.transaction_id,
                    "buyer_id": sale.buyer_id,
                    "seller_id": sale.seller_id,
                    "completed_at": sale.completed_at.isoformat(),
                    "reason": reason
                }
                
                await self.rabbitmq.publish(
                    self.settings.RABBITMQ_EXCHANGE,
                    "sales.completed",
                    message
                )
                logger.info(f"Sale {sale.id} completion notification sent to RabbitMQ")
            except Exception as e:
                logger.error(f"Error sending sale completion notification to RabbitMQ: {str(e)}")
                # Не прерываем выполнение, так как статус продажи уже обновлен
        
        # Добавляем причину в extra_data
        if reason:
            if not sale.extra_data:
                sale.extra_data = {}
            sale.extra_data["status_update"] = {
                "status": new_status,
                "reason": reason,
                "updated_by": user_id,
                "updated_at": datetime.now().isoformat()
            }
        
        self.db.commit()
        self.db.refresh(sale)
        
        return self._format_sale_response(sale)
    
    def _can_update_status(
        self,
        current_status: SaleStatus,
        new_status: SaleStatus,
        is_seller: bool
    ) -> bool:
        """
        Проверить возможность изменения статуса
        
        Args:
            current_status: Текущий статус
            new_status: Новый статус
            is_seller: Является ли пользователь продавцом
            
        Returns:
            True, если изменение статуса возможно
        """
        # Матрица возможных переходов статусов
        allowed_transitions = {
            SaleStatus.PENDING: {
                SaleStatus.PAYMENT_PROCESSING: True,  # Система
                SaleStatus.CANCELED: True,  # Любой участник
            },
            SaleStatus.PAYMENT_PROCESSING: {
                SaleStatus.DELIVERY_PENDING: True,  # Система после успешной оплаты
                SaleStatus.CANCELED: True,  # Любой участник
            },
            SaleStatus.DELIVERY_PENDING: {
                SaleStatus.COMPLETED: is_seller,  # Только продавец
                SaleStatus.DISPUTED: True,  # Любой участник
            },
            SaleStatus.COMPLETED: {
                SaleStatus.REFUNDED: True,  # Система
            },
            SaleStatus.DISPUTED: {
                SaleStatus.COMPLETED: True,  # Система после разрешения спора
                SaleStatus.REFUNDED: True,  # Система после разрешения спора
            },
            SaleStatus.CANCELED: set(),  # Финальный статус
            SaleStatus.REFUNDED: set(),  # Финальный статус
        }
        
        return new_status in allowed_transitions.get(current_status, set())
    
    def _format_sale_response(self, sale: Sale) -> Dict[str, Any]:
        """
        Форматировать информацию о продаже для ответа
        
        Args:
            sale: Объект продажи
            
        Returns:
            Отформатированная информация о продаже
        """
        # Обрабатываем status: если это строка, преобразуем в SaleStatus
        try:
            # Пытаемся конвертировать если это уже не SaleStatus
            status = sale.status if isinstance(sale.status, SaleStatus) else SaleStatus(sale.status)
        except (ValueError, TypeError):
            # Если не удается конвертировать, оставляем как есть
            status = sale.status
            logger.warning(f"Не удалось конвертировать статус продажи {sale.id} ({sale.status}) в SaleStatus")
        
        return {
            "id": sale.id,
            "listing_id": sale.listing_id,
            "listing_title": sale.listing.title if sale.listing else None,
            "buyer_id": sale.buyer_id,
            "buyer_name": sale.buyer.username if sale.buyer else None,
            "seller_id": sale.seller_id,
            "seller_name": sale.seller.username if sale.seller else None,
            "item_id": sale.item_id,
            "price": sale.price,
            "currency": sale.currency,
            "status": status,
            "created_at": sale.created_at.isoformat(),
            "updated_at": sale.updated_at.isoformat() if sale.updated_at else None,
            "completed_at": sale.completed_at.isoformat() if sale.completed_at else None,
            "chat_id": sale.chat_id,
            "transaction_id": sale.transaction_id,
            "description": sale.description,
            "extra_data": sale.extra_data
        } 