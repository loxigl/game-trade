"""
Модели для чатов и сообщений
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .base import Base, TimestampMixin


class ChatType(PyEnum):
    """Типы чатов"""
    LISTING = "listing"  # Чат по объявлению
    COMPLETION = "completion"  # Чат для подтверждения завершения сделки
    SUPPORT = "support"  # Чат с поддержкой
    DISPUTE = "dispute"  # Чат для разрешения споров


class ChatStatus(PyEnum):
    """Статусы чатов"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class MessageType(PyEnum):
    """Типы сообщений"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class Chat(Base, TimestampMixin):
    """Модель чата"""
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ChatType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ChatType.LISTING.value)
    status = Column(Enum(ChatStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ChatStatus.ACTIVE.value)
    title = Column(String(255), nullable=True)
    
    # Связанные объекты
    listing_id = Column(Integer, nullable=True)  # ID объявления из marketplace-svc
    transaction_id = Column(Integer, nullable=True)  # ID транзакции из payment-svc
    
    # Метаданные
    chat_metadata = Column(JSON, nullable=True)
    
    # Связи
    participants = relationship("ChatParticipant", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    moderators = relationship("ChatModerator", back_populates="chat", cascade="all, delete-orphan")


class ChatParticipant(Base, TimestampMixin):
    """Участник чата"""
    __tablename__ = "chat_participants"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, nullable=False)  # ID пользователя из auth-svc
    
    # Роль в чате
    role = Column(String(50), nullable=False, default="participant")  # participant, moderator, admin
    
    # Настройки участника
    is_muted = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime, nullable=True)
    
    # Связи
    chat = relationship("Chat", back_populates="participants")


class ChatMessage(Base, TimestampMixin):
    """Сообщение в чате"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, nullable=True)  # None для системных сообщений
    
    # Содержимое сообщения
    type = Column(Enum(MessageType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=MessageType.TEXT.value)
    content = Column(Text, nullable=False)
    
    # Файлы и изображения
    attachments = Column(JSON, nullable=True)  # Список файлов/изображений
    
    # Метаданные
    message_metadata = Column(JSON, nullable=True)
    
    # Статус сообщения
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Связи
    chat = relationship("Chat", back_populates="messages")


class ChatModerator(Base, TimestampMixin):
    """Модератор чата"""
    __tablename__ = "chat_moderators"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    moderator_id = Column(Integer, nullable=False)  # ID модератора из auth-svc
    assigned_by = Column(Integer, nullable=False)  # ID пользователя, назначившего модератора
    
    # Причина назначения модератора
    reason = Column(Text, nullable=True)
    
    # Статус модерации
    is_active = Column(Boolean, default=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Связи
    chat = relationship("Chat", back_populates="moderators") 