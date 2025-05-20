from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Table, Text, Boolean, UniqueConstraint, Index, ForeignKeyConstraint, JSON
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from ..database.connection import Base
import enum
from typing import Optional, Dict, Any, List
import uuid

class Currency(str, enum.Enum):
    """Поддерживаемые валюты"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    RUB = "RUB"
    JPY = "JPY"
    CNY = "CNY"

class WalletStatus(str, enum.Enum):
    """Статусы кошелька"""
    ACTIVE = "active"          # Активен
    BLOCKED = "blocked"        # Заблокирован
    PENDING = "pending"        # Ожидает верификации
    CLOSED = "closed"          # Закрыт

class WalletTransaction(Base):
    """
    Запись о транзакции в кошельке
    
    Отражает движение средств на балансе кошелька
    """
    __tablename__ = "wallet_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), 
                      nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), 
                           nullable=True, index=True)
    
    # Финансовые данные
    amount = Column(Float, nullable=False)  # может быть положительным или отрицательным
    currency = Column(Enum(Currency), nullable=False, index=True)  # Валюта операции
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Информация
    type = Column(String, nullable=False, index=True)  # credit (пополнение), debit (списание)
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Время операции
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        nullable=False, index=True)
    
    # Связи
    wallet = relationship("Wallet", back_populates="transactions_log")
    
    # Индексы
    __table_args__ = (
        Index('idx_wallet_txn_wallet_created', 'wallet_id', 'created_at'),
        Index('idx_wallet_txn_currency', 'currency'),
    )

class Wallet(Base):
    """
    Модель кошелька пользователя
    
    Хранит информацию о балансах в различных валютах и истории операций.
    Поддерживает мультивалютные операции в рамках одного кошелька.
    """
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_uid = Column(String(36), unique=True, nullable=False, 
                       default=lambda: str(uuid.uuid4()))
    
    # Связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Финансовая информация - балансы в разных валютах
    # Формат: {"USD": 1000.0, "EUR": 750.0, ...}
    balances = Column(JSON, nullable=False, default=lambda: {})
    
    # Статусы и настройки
    status = Column(Enum(WalletStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]), default=WalletStatus.ACTIVE.value, 
                   nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    is_system_escrow = Column(Boolean, default=False, nullable=False)
    is_system_fee = Column(Boolean, default=False, nullable=False)
    
    # Ограничения по валютам
    # Формат: {"USD": {"daily": 10000.0, "monthly": 50000.0}, "EUR": {...}}
    limits = Column(JSON, nullable=False, default=lambda: {
        "USD": {"daily": 10000.0, "monthly": 50000.0},
        "EUR": {"daily": 9000.0, "monthly": 45000.0},
        "GBP": {"daily": 8000.0, "monthly": 40000.0},
        "RUB": {"daily": 700000.0, "monthly": 3500000.0},
        "JPY": {"daily": 1000000.0, "monthly": 5000000.0},
        "CNY": {"daily": 70000.0, "monthly": 350000.0}
    })
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet")
    transactions_log = relationship("WalletTransaction", back_populates="wallet", 
                                  cascade="all, delete-orphan")
    
    # Индексы - теперь один пользователь может иметь только один кошелек
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_wallet'),
        Index('idx_wallet_user_status', 'user_id', 'status'),
    ) 