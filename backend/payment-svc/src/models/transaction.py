from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Table, Text, Boolean, UniqueConstraint, Index, ForeignKeyConstraint, JSON
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from ..database.connection import Base
import enum
from typing import Optional, Dict, Any, List
import uuid

class TransactionStatus(str, enum.Enum):
    """Статусы транзакций для работы с Escrow"""
    PENDING = "pending"          # Ожидает оплаты
    ESCROW_HELD = "escrow_held"  # Средства в Escrow
    COMPLETED = "completed"      # Транзакция успешно завершена
    REFUNDED = "refunded"        # Средства возвращены покупателю
    DISPUTED = "disputed"        # Транзакция в споре
    CANCELED = "canceled"      # Отменена
    FAILED = "failed"            # Не удалось обработать

class TransactionType(str, enum.Enum):
    """Типы транзакций"""
    PURCHASE = "purchase"        # Покупка
    DEPOSIT = "deposit"          # Пополнение
    WITHDRAWAL = "withdrawal"    # Вывод средств
    REFUND = "refund"            # Возврат
    FEE = "fee"                  # Комиссия
    SYSTEM = "system"            # Системная операция

class Transaction(Base):
    """
    Модель транзакции
    
    Хранит информацию о денежном переводе между пользователями
    или между пользователем и системой
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_uid = Column(String(36), unique=True, nullable=False, 
                            default=lambda: str(uuid.uuid4()))
    
    # Связи с пользователями
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Связь с объявлением/товаром (из внешней системы)
    listing_id = Column(Integer, nullable=True)
    item_id = Column(Integer, nullable=True)
    
    # Финансовая информация
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    fee_amount = Column(Float, default=0.0, nullable=False)
    fee_percentage = Column(Float, default=0.0, nullable=False)
    
    # Статус и тип транзакции
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, 
                   nullable=False, index=True)
    type = Column(Enum(TransactionType), default=TransactionType.PURCHASE, 
                 nullable=False, index=True)
    
    # Сроки и время
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    escrow_held_at = Column(DateTime(timezone=True), nullable=True)  # Время перевода средств в Escrow
    disputed_at = Column(DateTime(timezone=True), nullable=True)  # Время создания спора
    refunded_at = Column(DateTime(timezone=True), nullable=True)  # Время возврата средств
    canceled_at = Column(DateTime(timezone=True), nullable=True)  # Время отмены транзакции
    
    # Дополнительная информация
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Хранение дополнительных данных в JSON
    external_reference = Column(String, nullable=True, index=True)  # Внешний ID для интеграций
    dispute_reason = Column(Text, nullable=True)  # Причина спора
    refund_reason = Column(Text, nullable=True)  # Причина возврата
    cancel_reason = Column(Text, nullable=True)  # Причина отмены
    
    # Связь с кошельком
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), 
                      nullable=True, index=True)
    wallet = relationship("Wallet", back_populates="transactions")
    
    # Связи с пользователями
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buy_transactions")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="sell_transactions")
    
    # Связь с родительской транзакцией (например, для возвратов или связанных операций)
    parent_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    parent_transaction = relationship("Transaction", remote_side=[id], backref="child_transactions")
    
    # Индексы
    __table_args__ = (
        Index('idx_transactions_buyer_seller', 'buyer_id', 'seller_id'),
        Index('idx_transactions_status_created', 'status', 'created_at'),
        Index('idx_transactions_type_status', 'type', 'status'),
    ) 