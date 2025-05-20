from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Table, Text, Boolean, UniqueConstraint, Index, ForeignKeyConstraint, ARRAY
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from ..database.connection import Base
from sqlalchemy import JSON, Enum as SQLAlchemyEnum
import enum

class ListingStatus(str, enum.Enum):
    """Статусы объявлений"""
    DRAFT = "draft"         # Черновик
    PENDING = "pending"     # На модерации
    ACTIVE = "active"       # Активно
    PAUSED = "paused"       # Приостановлено
    SOLD = "sold"           # Продано
    EXPIRED = "expired"     # Истек срок
    REMOVED = "removed"     # Удалено

class TransactionStatus(str, enum.Enum):
    """Статусы транзакций"""
    PENDING = "pending"         # Ожидает оплаты
    PAID = "paid"               # Оплачено, ожидает передачи товара
    COMPLETED = "completed"     # Завершена успешно
    CANCELED = "canceled"     # Отменена
    REFUNDED = "refunded"       # Возвращены средства
    DISPUTED = "disputed"       # В споре

class ImageType(str, enum.Enum):
    """Типы изображений"""
    LISTING = "listing"         # Изображение объявления
    USER = "user"               # Аватар пользователя
    CATEGORY = "category"       # Иконка категории
    GAME = "game"               # Логотип игры
    OTHER = "other"             # Другое
    ITEM_TEMPLATE = "item_template"  # Изображение шаблона предмета
    ITEM = "item"             # Изображение конкретного предмета

class ImageStatus(str, enum.Enum):
    """Статусы изображений"""
    ACTIVE = "active"           # Активно
    DELETED = "deleted"         # Удалено
    UPLOADING = "uploading"   # Загружается
    PENDING = "pending"       # Ожидает проверки

class User(Base):
    """
    Модель пользователя в базе данных
    
    Примечание: В реальной системе это будет внешняя ссылка на auth-svc
    Здесь реализована как локальная таблица для демонстрации связей
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связи
    profile = relationship("Profile", back_populates="user", uselist=False)
    wallets = relationship("Wallet", back_populates="user")
    
    # Транзакции (должны быть определены в этом сервисе)
    buy_transactions = relationship("Transaction", back_populates="buyer", foreign_keys='Transaction.buyer_id')
    sell_transactions = relationship("Transaction", back_populates="seller", foreign_keys='Transaction.seller_id')

class Profile(Base):
    """
    Профиль пользователя с дополнительной информацией
    """
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    reputation_score = Column(Float, default=0.0, nullable=False)
    is_verified_seller = Column(Boolean, server_default=expression.false(), nullable=False)
    total_sales = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связь с пользователем
    user = relationship("User", back_populates="profile")

class SaleStatus(str, enum.Enum):
    """Статусы продажи для работы с платежами"""
    PENDING = "pending"           # Ожидает оплаты
    PAYMENT_PROCESSING = "payment_processing"  # Обработка оплаты
    DELIVERY_PENDING = "delivery_pending"  # Ожидает передачи товара
    COMPLETED = "completed"       # Завершена успешно
    CANCELED = "canceled"       # Отменена
    REFUNDED = "refunded"        # Возвращены средства
    DISPUTED = "disputed"        # В споре

class Sale(Base):
    """
    Модель продажи для работы с платежами
    
    Эта модель используется только для работы с платежами и содержит
    минимальный набор полей, необходимых для обработки платежей.
    Полная модель продажи находится в marketplace-svc.
    """
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    listing_id = Column(Integer, nullable=False, index=True)  # Внешний ключ на marketplace-svc
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    
    # Финансовая информация
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    
    # Статус и время
    status = Column(SQLAlchemyEnum(SaleStatus, name='salestatus', create_type=True, values_callable=lambda enum: [e.value for e in enum]), server_default=SaleStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительная информация
    extra_data = Column(JSON, nullable=True)
    
    # Связи
    transaction = relationship("Transaction", backref="sale")
    buyer = relationship("User", foreign_keys=[buyer_id], backref="purchases")
    seller = relationship("User", foreign_keys=[seller_id], backref="sales")

    def __repr__(self):
        return f"<Sale(id={self.id}, listing_id={self.listing_id}, status={self.status})>"

