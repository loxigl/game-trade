"""
Сервис для обеспечения идемпотентности операций
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text
from ..database.connection import Base

logger = logging.getLogger(__name__)

# Кастомный JSON энкодер для обработки объектов datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class IdempotencyRecord(Base):
    """
    Модель для хранения информации об идемпотентных операциях
    """
    __tablename__ = "idempotency_records"
    
    key = Column(String(255), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    operation_type = Column(String(100), nullable=False, index=True)
    response_data = Column(Text, nullable=True)

class IdempotencyService:
    """
    Сервис для обеспечения идемпотентности операций
    
    Предотвращает дублирование операций путем отслеживания выполненных операций
    по уникальным ключам идемпотентности.
    """
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных
        """
        self.db = db
        self.ttl_days = 7  # По умолчанию записи хранятся 7 дней
        
    async def check_and_save(self, 
                      idempotency_key: str, 
                      operation_type: str,
                      response_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Проверить существование операции с указанным ключом идемпотентности и 
        сохранить новую запись, если операция еще не выполнялась
        
        Args:
            idempotency_key: Уникальный ключ операции
            operation_type: Тип операции
            response_data: Данные ответа операции
            
        Returns:
            None, если операция новая, или данные существующей операции
        """
        # Проверяем существование записи
        existing_record = self.db.query(IdempotencyRecord).filter(
            IdempotencyRecord.key == idempotency_key
        ).first()
        
        if existing_record:
            logger.info(f"Найдена существующая операция с ключом идемпотентности {idempotency_key}")
            # Если запись существует, возвращаем сохраненные данные
            if existing_record.response_data:
                return json.loads(existing_record.response_data)
            # Если данные не были сохранены, возвращаем пустой словарь
            return {}
        
        # Создаем новую запись
        expires_at = datetime.utcnow() + timedelta(days=self.ttl_days)
        
        new_record = IdempotencyRecord(
            key=idempotency_key,
            operation_type=operation_type,
            expires_at=expires_at,
            response_data=json.dumps(response_data, cls=DateTimeEncoder) if response_data else None
        )
        
        self.db.add(new_record)
        self.db.commit()
        
        logger.info(f"Создана новая запись идемпотентности для ключа {idempotency_key}")
        return None
    
    async def save_response(self, idempotency_key: str, response_data: Dict[str, Any]) -> None:
        """
        Сохранить данные ответа для существующей операции
        
        Args:
            idempotency_key: Уникальный ключ операции
            response_data: Данные ответа операции
        """
        existing_record = self.db.query(IdempotencyRecord).filter(
            IdempotencyRecord.key == idempotency_key
        ).first()
        
        if existing_record:
            existing_record.response_data = json.dumps(response_data, cls=DateTimeEncoder)
            self.db.commit()
            logger.info(f"Обновлены данные ответа для ключа идемпотентности {idempotency_key}")
    
    async def cleanup_expired(self) -> int:
        """
        Очистить истекшие записи идемпотентности
        
        Returns:
            Количество удаленных записей
        """
        # Находим и удаляем истекшие записи
        now = datetime.utcnow()
        expired_records = self.db.query(IdempotencyRecord).filter(
            IdempotencyRecord.expires_at < now
        ).all()
        
        count = len(expired_records)
        
        if count > 0:
            for record in expired_records:
                self.db.delete(record)
            self.db.commit()
            logger.info(f"Удалено {count} истекших записей идемпотентности")
        
        return count

def get_idempotency_service(db: Session) -> IdempotencyService:
    """
    Получение экземпляра сервиса идемпотентности
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Экземпляр IdempotencyService
    """
    return IdempotencyService(db) 