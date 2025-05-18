from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Table, Text, Boolean, UniqueConstraint, Index, ForeignKeyConstraint
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from ..database.connection import Base
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
    CANCELLED = "cancelled"     # Отменена
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
    listings = relationship("Listing", back_populates="seller", foreign_keys='Listing.seller_id')
    buy_transactions = relationship("Transaction", back_populates="buyer", foreign_keys='Transaction.buyer_id')
    sell_transactions = relationship("Transaction", back_populates="seller", foreign_keys='Transaction.seller_id')
    owned_images = relationship("Image", back_populates="owner")

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

class Wallet(Base):
    """
    Кошелек пользователя
    """
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связь с пользователем
    user = relationship("User", back_populates="wallets")

class Listing(Base):
    """
    Объявление о продаже товара
    """
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Новое поле - внешний ключ на шаблон предмета
    item_template_id = Column(Integer, ForeignKey("item_templates.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(ListingStatus), default=ListingStatus.PENDING, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связи
    seller = relationship("User", back_populates="listings", foreign_keys=[seller_id])
    transactions = relationship("Transaction", back_populates="listing")
    # Новая связь с шаблоном предмета
    item_template = relationship("ItemTemplate", back_populates="listings")
    item = relationship("Item", back_populates="listing",uselist=False)
    images = relationship(
        "Image", 
        primaryjoin="and_(foreign(Image.entity_id)==Listing.id, Image.type=='listing')",
        viewonly=True
    )

class Transaction(Base):
    """
    Транзакция между покупателем и продавцом
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    fee_amount = Column(Float, default=0.0, nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    listing = relationship("Listing", back_populates="transactions")
    buyer = relationship("User", back_populates="buy_transactions", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="sell_transactions", foreign_keys=[seller_id])

class Image(Base):
    """Изображения для различных типов сущностей"""
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entity_id = Column(Integer, nullable=True)  # ID связанной сущности
    type = Column(Enum(ImageType), nullable=False, default=ImageType.OTHER)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(512), nullable=False)
    content_type = Column(String(100))
    is_main = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    status = Column(Enum(ImageStatus), nullable=False, default=ImageStatus.ACTIVE)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    owner = relationship("User", back_populates="owned_images")
    
    # Индексы для быстрого поиска изображений
    __table_args__ = (
        Index('idx_images_entity_type', 'entity_id', 'type'),
    ) 