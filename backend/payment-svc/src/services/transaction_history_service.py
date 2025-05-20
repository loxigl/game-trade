"""
Сервис для работы с историей транзакций
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, case, literal_column, extract
from fastapi import Depends
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta

from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.transaction_history import TransactionHistory
from ..schemas.transaction_history import TransactionHistoryCreate, TransactionHistoryResponse, TransactionHistoryListResponse
from ..database.connection import get_db

logger = logging.getLogger(__name__)

class TransactionHistoryService:
    """Сервис для работы с историей транзакций"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_history_record(self, data: TransactionHistoryCreate) -> TransactionHistory:
        """Создание новой записи в истории транзакций"""
        history_record = TransactionHistory(
            transaction_id=data.transaction_id,
            previous_status=data.previous_status,
            new_status=data.new_status,
            initiator_id=data.initiator_id,
            initiator_type=data.initiator_type,
            reason=data.reason,
            extra_data=data.extra_data
        )
        
        self.db.add(history_record)
        self.db.commit()
        self.db.refresh(history_record)
        
        logger.info(f"Created transaction history record: {history_record.id} for transaction {data.transaction_id}")
        return history_record
    
    def get_transaction_history(self, transaction_id: int) -> List[TransactionHistory]:
        """Получение истории для конкретной транзакции"""
        return self.db.query(TransactionHistory).filter(
            TransactionHistory.transaction_id == transaction_id
        ).order_by(TransactionHistory.timestamp.desc()).all()
    
    def get_transactions_history(
        self, 
        user_id: Optional[int] = None,
        status: Optional[TransactionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> TransactionHistoryListResponse:
        """Получение истории транзакций с пагинацией и фильтрацией"""
        # Подготовка базового запроса
        query = self.db.query(TransactionHistory)
        
        # Применение фильтров
        if user_id is not None:
            # Находим транзакции, где пользователь является покупателем или продавцом
            transaction_ids = self.db.query(Transaction.id).filter(
                (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
            ).scalar_subquery()
            
            query = query.filter(TransactionHistory.transaction_id.in_(transaction_ids))
        
        if status is not None:
            query = query.filter(TransactionHistory.new_status == status)
        
        if start_date is not None:
            query = query.filter(TransactionHistory.timestamp >= start_date)
        
        if end_date is not None:
            query = query.filter(TransactionHistory.timestamp <= end_date)
        
        # Получение общего количества записей
        total = query.count()
        
        # Рассчет пагинации
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        
        # Получение результатов с пагинацией и сортировкой
        items = query.order_by(TransactionHistory.timestamp.desc()).offset(offset).limit(page_size).all()
        
        return TransactionHistoryListResponse(
            items=items,
            total=total,
            page=page,
            size=page_size,
            pages=pages
        )
    
    def get_transaction_timeline(self, transaction_id: int) -> List[TransactionHistory]:
        """Получение таймлайна для конкретной транзакции"""
        return self.db.query(TransactionHistory).filter(
            TransactionHistory.transaction_id == transaction_id
        ).order_by(TransactionHistory.timestamp.asc()).all()
    
    def get_recent_history(self, limit: int = 50) -> List[TransactionHistory]:
        """Получение последних изменений в истории транзакций"""
        return self.db.query(TransactionHistory).order_by(
            TransactionHistory.timestamp.desc()
        ).limit(limit).all()

    # Новые методы для статистики и аналитики
    
    def get_transaction_status_distribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Получение распределения транзакций по статусам
        
        Возвращает словарь, где ключи - это статусы транзакций, 
        а значения - количество транзакций в этом статусе
        """
        # Базовый запрос к транзакциям
        query = self.db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        )
        
        # Применяем фильтры
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        if user_id:
            query = query.filter(
                (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
            )
        
        # Группировка по статусу
        result = query.group_by(Transaction.status).all()
        
        # Преобразуем результат в словарь
        return {status.value: count for status, count in result}
    
    def get_transaction_volume_by_period(
        self,
        period: str = 'day',  # 'day', 'week', 'month'
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение объема транзакций по периодам
        
        Args:
            period: Период группировки ('day', 'week', 'month')
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            status: Фильтр по статусу транзакции
            
        Returns:
            Список словарей с периодами и объемами транзакций
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Определяем групповую функцию в зависимости от периода
        if period == 'day':
            date_trunc = func.date_trunc('day', Transaction.created_at).label('period')
        elif period == 'week':
            date_trunc = func.date_trunc('week', Transaction.created_at).label('period')
        elif period == 'month':
            date_trunc = func.date_trunc('month', Transaction.created_at).label('period')
        else:
            raise ValueError(f"Неподдерживаемый период группировки: {period}")
        
        # Подготавливаем базовый запрос
        query = self.db.query(
            date_trunc,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('volume')
        ).filter(
            Transaction.created_at.between(start_date, end_date)
        )
        
        # Применяем фильтр по статусу, если указан
        if status:
            query = query.filter(Transaction.status == status)
        
        # Группировка по периоду и сортировка
        result = query.group_by(date_trunc).order_by(date_trunc).all()
        
        # Преобразуем результат в список словарей
        return [
            {
                'period': period_date.isoformat() if period_date else None,
                'count': count,
                'volume': float(volume) if volume else 0.0
            }
            for period_date, count, volume in result
        ]
    
    def get_transaction_time_to_completion(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Рассчитывает среднее время до завершения транзакций
        
        Returns:
            Словарь со средним, минимальным и максимальным временем в часах
        """
        # Подзапрос для выбора первой записи PENDING и последней записи COMPLETED для каждой транзакции
        subquery = self.db.query(
            TransactionHistory.transaction_id,
            func.min(case(
                [(TransactionHistory.new_status == TransactionStatus.PENDING, TransactionHistory.timestamp)]
            )).label('start_time'),
            func.max(case(
                [(TransactionHistory.new_status == TransactionStatus.COMPLETED, TransactionHistory.timestamp)]
            )).label('end_time')
        )
        
        # Применяем фильтры по дате, если указаны
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append(TransactionHistory.timestamp >= start_date)
            if end_date:
                conditions.append(TransactionHistory.timestamp <= end_date)
            if conditions:
                subquery = subquery.filter(and_(*conditions))
        
        # Фильтр по пользователю, если указан
        if user_id:
            transaction_ids = self.db.query(Transaction.id).filter(
                (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
            ).scalar_subquery()
            
            subquery = subquery.filter(TransactionHistory.transaction_id.in_(transaction_ids))
        
        # Группировка по ID транзакции
        subquery = subquery.group_by(TransactionHistory.transaction_id).subquery()
        
        # Основной запрос для расчета времени до завершения
        query = self.db.query(
            func.avg(func.extract('epoch', subquery.c.end_time - subquery.c.start_time) / 3600).label('avg_hours'),
            func.min(func.extract('epoch', subquery.c.end_time - subquery.c.start_time) / 3600).label('min_hours'),
            func.max(func.extract('epoch', subquery.c.end_time - subquery.c.start_time) / 3600).label('max_hours')
        ).filter(
            subquery.c.start_time.isnot(None),
            subquery.c.end_time.isnot(None)
        )
        
        result = query.first()
        
        return {
            'avg_hours': float(result.avg_hours) if result.avg_hours else 0.0,
            'min_hours': float(result.min_hours) if result.min_hours else 0.0,
            'max_hours': float(result.max_hours) if result.max_hours else 0.0
        }
    
    def get_dispute_rate(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Рассчитывает частоту возникновения споров
        
        Returns:
            Словарь со статистикой по спорам
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Общее количество транзакций за период
        total_transactions = self.db.query(func.count(Transaction.id)).filter(
            Transaction.created_at.between(start_date, end_date)
        ).scalar()
        
        # Количество транзакций, у которых был статус DISPUTED
        disputed_transactions = self.db.query(func.count(Transaction.id)).filter(
            Transaction.status == TransactionStatus.DISPUTED,
            Transaction.created_at.between(start_date, end_date)
        ).scalar()
        
        # Рассчитываем процент споров
        dispute_rate = 0.0
        if total_transactions > 0:
            dispute_rate = (disputed_transactions / total_transactions) * 100.0
        
        return {
            'total_transactions': total_transactions,
            'disputed_transactions': disputed_transactions,
            'dispute_rate': dispute_rate
        }
    
    def get_user_transaction_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Получение сводной информации по транзакциям пользователя
        
        Returns:
            Словарь со статистикой по транзакциям пользователя
        """
        # Подсчет количества транзакций как покупатель и как продавец
        buyer_count = self.db.query(func.count(Transaction.id)).filter(
            Transaction.buyer_id == user_id
        ).scalar()
        
        seller_count = self.db.query(func.count(Transaction.id)).filter(
            Transaction.seller_id == user_id
        ).scalar()
        
        # Суммы транзакций
        buyer_volume = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.buyer_id == user_id
        ).scalar()
        
        seller_volume = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.seller_id == user_id
        ).scalar()
        
        # Распределение по статусам для покупателя
        buyer_status_distribution = self.db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.buyer_id == user_id
        ).group_by(Transaction.status).all()
        
        buyer_statuses = {
            status.value: count for status, count in buyer_status_distribution
        }
        
        # Распределение по статусам для продавца
        seller_status_distribution = self.db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.seller_id == user_id
        ).group_by(Transaction.status).all()
        
        seller_statuses = {
            status.value: count for status, count in seller_status_distribution
        }
        
        # Формируем итоговый результат
        return {
            'as_buyer': {
                'count': buyer_count,
                'volume': float(buyer_volume) if buyer_volume else 0.0,
                'status_distribution': buyer_statuses
            },
            'as_seller': {
                'count': seller_count,
                'volume': float(seller_volume) if seller_volume else 0.0,
                'status_distribution': seller_statuses
            },
            'total': {
                'count': buyer_count + seller_count,
                'volume': float((buyer_volume or 0) + (seller_volume or 0))
            }
        }

# Зависимость для FastAPI
def get_transaction_history_service(db: Session = Depends(get_db)) -> TransactionHistoryService:
    return TransactionHistoryService(db) 