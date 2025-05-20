from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database.connection import Base
from .transaction import TransactionStatus

class TransactionHistory(Base):
    """
    Модель истории транзакций
    
    Отслеживает все изменения статусов транзакций и другие важные события
    """
    __tablename__ = "transaction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), 
                          nullable=False, index=True)
    
    # Статусы (до и после изменения)
    previous_status = Column(Enum(TransactionStatus), nullable=True)
    new_status = Column(Enum(TransactionStatus), nullable=False)
    
    # Метаданные
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    initiator_id = Column(Integer, nullable=True)  # ID пользователя, инициировавшего изменение
    initiator_type = Column(String, nullable=True)  # 'user', 'system', 'admin'
    reason = Column(Text, nullable=True)  # Причина изменения
    extra_data = Column(JSON, nullable=True)  # Дополнительные данные
    
    # Связи
    transaction = relationship("Transaction", backref="history")
    
    def __repr__(self):
        return f"<TransactionHistory(id={self.id}, transaction_id={self.transaction_id}, " \
               f"{self.previous_status} -> {self.new_status}, timestamp={self.timestamp})>" 