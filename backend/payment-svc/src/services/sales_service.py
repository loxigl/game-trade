"""
Сервис для работы с продажами маркетплейса
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.core import User
from ..database.connection import get_db

class SalesService:
    """
    Сервис для управления продажами маркетплейса
    """
    def __init__(self, db: Session):
        self.db = db
        
    async def get_pending_sales(
        self, 
        seller_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Получение ожидающих подтверждения продаж для продавца
        
        Args:
            seller_id: ID продавца
            page: Номер страницы для пагинации
            page_size: Количество элементов на странице
            
        Returns:
            Словарь с списком продаж и информацией о пагинации
        """
        # Получаем статусы транзакций, которые считаются "ожидающими подтверждения"
        pending_statuses = [
            TransactionStatus.PENDING,
            TransactionStatus.ESCROW_HELD
        ]
        
        # Запрос транзакций с пагинацией
        query = self.db.query(Transaction).filter(
            Transaction.seller_id == seller_id,
            Transaction.status.in_(pending_statuses),
            Transaction.type == TransactionType.PURCHASE
        ).order_by(desc(Transaction.created_at))
        
        # Подсчет общего количества
        total_count = query.count()
        
        # Применяем пагинацию
        transactions = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Формируем список продаж
        sales_list = []
        for tx in transactions:
            # Получаем данные покупателя
            buyer = self.db.query(User).filter(User.id == tx.buyer_id).first()
            buyer_name = buyer.username if buyer else f"User{tx.buyer_id}"
            
            # Извлекаем информацию об игре из extra_data (если есть)
            game_info = None
            if tx.extra_data and 'game' in tx.extra_data:
                game_info = tx.extra_data['game']
            else:
                # Если информации нет, предоставляем базовые данные
                game_info = {
                    "id": 0,
                    "name": "Неизвестная игра",
                    "image": None
                }
            
            # Формируем объект продажи
            sales_list.append({
                "id": tx.id,
                "listingId": tx.listing_id or 0,
                "listingTitle": tx.description or f"Транзакция #{tx.id}",
                "buyerId": tx.buyer_id,
                "buyerName": buyer_name,
                "price": tx.amount,
                "currency": tx.currency,
                "status": tx.status,
                "createdAt": tx.created_at.isoformat(),
                "expiresAt": tx.expiration_date.isoformat() if tx.expiration_date else None,
                "gameInfo": game_info
            })
        
        # Вычисляем количество страниц
        pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return {
            "items": sales_list,
            "total": total_count,
            "page": page,
            "size": page_size,
            "pages": pages
        }
    
    async def confirm_sale(self, sale_id: int, user_id: int) -> Dict[str, Any]:
        """
        Подтверждение продажи продавцом
        
        Args:
            sale_id: ID продажи (транзакции)
            user_id: ID продавца, выполняющего подтверждение
            
        Returns:
            Обновленная информация о продаже
            
        Raises:
            ValueError: Если транзакция не найдена или продавец не имеет прав на подтверждение
        """
        # Находим транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == sale_id,
            Transaction.seller_id == user_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Транзакция {sale_id} не найдена или у вас нет прав на её подтверждение")
        
        # Проверяем, что статус позволяет подтверждение
        if transaction.status != TransactionStatus.ESCROW_HELD:
            raise ValueError(f"Невозможно подтвердить транзакцию в статусе {transaction.status}")
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.now()
        transaction.updated_at = datetime.now()
        
        # Добавляем информацию в notes
        transaction.notes = (transaction.notes or "") + f"\nПодтверждено продавцом {user_id} в {datetime.now()}"
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(transaction)
        
        # Получаем данные покупателя
        buyer = self.db.query(User).filter(User.id == transaction.buyer_id).first()
        buyer_name = buyer.username if buyer else f"User{transaction.buyer_id}"
        
        # Извлекаем информацию об игре
        game_info = None
        if transaction.extra_data and 'game' in transaction.extra_data:
            game_info = transaction.extra_data['game']
        else:
            # Если информации нет, предоставляем базовые данные
            game_info = {
                "id": 0,
                "name": "Неизвестная игра",
                "image": None
            }
            
        # Формируем ответ
        return {
            "id": transaction.id,
            "listingId": transaction.listing_id or 0,
            "listingTitle": transaction.description or f"Транзакция #{transaction.id}",
            "buyerId": transaction.buyer_id,
            "buyerName": buyer_name,
            "price": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "createdAt": transaction.created_at.isoformat(),
            "expiresAt": transaction.expiration_date.isoformat() if transaction.expiration_date else None,
            "gameInfo": game_info
        }
    
    async def reject_sale(self, sale_id: int, user_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Отклонение продажи продавцом
        
        Args:
            sale_id: ID продажи (транзакции)
            user_id: ID продавца, выполняющего отклонение
            reason: Причина отклонения
            
        Returns:
            Обновленная информация о продаже
            
        Raises:
            ValueError: Если транзакция не найдена или продавец не имеет прав на отклонение
        """
        # Находим транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == sale_id,
            Transaction.seller_id == user_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Транзакция {sale_id} не найдена или у вас нет прав на её отклонение")
        
        # Проверяем, что статус позволяет отклонение
        allowed_statuses = [TransactionStatus.PENDING, TransactionStatus.ESCROW_HELD]
        if transaction.status not in allowed_statuses:
            raise ValueError(f"Невозможно отклонить транзакцию в статусе {transaction.status}")
        
        # Обновляем статус транзакции
        transaction.status = TransactionStatus.CANCELED
        transaction.updated_at = datetime.now()
        
        # Добавляем информацию в notes
        note = f"\nОтклонено продавцом {user_id} в {datetime.now()}"
        if reason:
            note += f". Причина: {reason}"
        transaction.notes = (transaction.notes or "") + note
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(transaction)
        
        # Получаем данные покупателя
        buyer = self.db.query(User).filter(User.id == transaction.buyer_id).first()
        buyer_name = buyer.username if buyer else f"User{transaction.buyer_id}"
        
        # Извлекаем информацию об игре
        game_info = None
        if transaction.extra_data and 'game' in transaction.extra_data:
            game_info = transaction.extra_data['game']
        else:
            # Если информации нет, предоставляем базовые данные
            game_info = {
                "id": 0,
                "name": "Неизвестная игра",
                "image": None
            }
            
        # Формируем ответ
        return {
            "id": transaction.id,
            "listingId": transaction.listing_id or 0,
            "listingTitle": transaction.description or f"Транзакция #{transaction.id}",
            "buyerId": transaction.buyer_id,
            "buyerName": buyer_name,
            "price": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "createdAt": transaction.created_at.isoformat(),
            "expiresAt": transaction.expiration_date.isoformat() if transaction.expiration_date else None,
            "gameInfo": game_info
        }

    async def get_completed_sales(
        self, 
        seller_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Получение завершенных продаж для продавца
        
        Args:
            seller_id: ID продавца
            page: Номер страницы для пагинации
            page_size: Количество элементов на странице
            
        Returns:
            Словарь с списком продаж и информацией о пагинации
        """
        # Запрос транзакций со статусом COMPLETED с пагинацией
        query = self.db.query(Transaction).filter(
            Transaction.seller_id == seller_id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.type == TransactionType.PURCHASE
        ).order_by(desc(Transaction.created_at))
        
        # Подсчет общего количества
        total_count = query.count()
        
        # Применяем пагинацию
        transactions = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Формируем список продаж
        sales_list = []
        for tx in transactions:
            # Получаем данные покупателя
            buyer = self.db.query(User).filter(User.id == tx.buyer_id).first()
            buyer_name = buyer.username if buyer else f"User{tx.buyer_id}"
            
            # Извлекаем информацию об игре из extra_data (если есть)
            game_info = None
            if tx.extra_data and 'game' in tx.extra_data:
                game_info = tx.extra_data['game']
            else:
                # Если информации нет, предоставляем базовые данные
                game_info = {
                    "id": 0,
                    "name": "Неизвестная игра",
                    "image": None
                }
            
            # Формируем объект продажи
            sales_list.append({
                "id": tx.id,
                "listingId": tx.listing_id or 0,
                "listingTitle": tx.description or f"Транзакция #{tx.id}",
                "buyerId": tx.buyer_id,
                "buyerName": buyer_name,
                "price": tx.amount,
                "currency": tx.currency,
                "status": tx.status,
                "createdAt": tx.created_at.isoformat(),
                "completedAt": tx.completed_at.isoformat() if tx.completed_at else None,
                "gameInfo": game_info
            })
        
        # Вычисляем количество страниц
        pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return {
            "items": sales_list,
            "total": total_count,
            "page": page,
            "size": page_size,
            "pages": pages
        }

def get_sales_service(db: Session):
    """
    Функция-провайдер для получения экземпляра SalesService
    """
    return SalesService(db) 