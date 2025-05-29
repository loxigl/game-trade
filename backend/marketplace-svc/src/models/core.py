from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Table, Text, Boolean, UniqueConstraint, Index, ForeignKeyConstraint, ARRAY
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from ..database.connection import Base
import enum
from sqlalchemy import JSON, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class SaleStatus(str, enum.Enum):
    """Статусы продажи"""
    PENDING = "pending"           # Ожидает оплаты
    PAYMENT_PROCESSING = "payment_processing"  # Обработка оплаты
    DELIVERY_PENDING = "delivery_pending"  # Ожидает передачи товара
    COMPLETED = "completed"       # Завершена успешно
    CANCELED = "canceled"       # Отменена
    REFUNDED = "refunded"        # Возвращены средства
    DISPUTED = "disputed"   

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
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    is_verified = Column(Boolean, server_default=expression.false(), nullable=False)
    is_admin = Column(Boolean, server_default=expression.false(), nullable=False)
    roles = Column(ARRAY(String), server_default="{'user'}", nullable=False)
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
    item_id = Column(Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(SQLAlchemyEnum(ListingStatus, name='listingstatus', create_type=True, values_callable=lambda enum: [e.value for e in enum]), server_default=ListingStatus.PENDING.value, nullable=False)
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
    status = Column(SQLAlchemyEnum(TransactionStatus, name='transactionstatus', create_type=True, values_callable=lambda enum: [e.value for e in enum]), server_default=TransactionStatus.PENDING.value, nullable=False)
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
    type = Column(SQLAlchemyEnum(ImageType, name="imagetype", create_type=True, values_callable=lambda enum: [e.value for e in enum]), nullable=False, server_default=ImageType.OTHER.value)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(512), nullable=False)
    content_type = Column(String(100))
    is_main = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    status = Column(SQLAlchemyEnum(ImageStatus, name="imagestatus", create_type=True, values_callable=lambda enum: [e.value for e in enum]), nullable=False, default=ImageStatus.ACTIVE.value)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    owner = relationship("User", back_populates="owned_images")
    
    # Индексы для быстрого поиска изображений
    __table_args__ = (
        Index('idx_images_entity_type', 'entity_id', 'type'),
    ) 

class Chat(Base):
    """
    Модель чата между покупателем и продавцом
    """
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Связи
    buyer = relationship("User", foreign_keys=[buyer_id], backref="buyer_chats")
    seller = relationship("User", foreign_keys=[seller_id], backref="seller_chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, buyer_id={self.buyer_id}, seller_id={self.seller_id})>"

class ChatMessage(Base):
    """
    Модель сообщения в чате
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связи
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", backref="sent_messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, chat_id={self.chat_id}, sender_id={self.sender_id})>"

     # В споре

class Sale(Base):
    """
    Модель продажи товара
    """
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="SET NULL"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    
    # Информация о товаре
    item_id = Column(Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    
    # Статус и время
    status = Column(SQLAlchemyEnum(SaleStatus, name='salestatus', native_enum=True, create_type=True, values_callable=lambda enum: [e.value for e in enum]), server_default=SaleStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительная информация
    description = Column(Text, nullable=True)
    chat_id = Column(Integer, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Связи
    transaction = relationship("Transaction", backref="sale")
    listing = relationship("Listing", backref="sales")
    buyer = relationship("User", foreign_keys=[buyer_id], backref="purchases")
    seller = relationship("User", foreign_keys=[seller_id], backref="sales")
    item = relationship("Item", backref="sales")
    
    def __repr__(self):
        return f"<Sale(id={self.id}, listing_id={self.listing_id}, status={self.status})>" 