"""
Схемы Pydantic для чатов и сообщений
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ChatType(str, Enum):
    """Типы чатов"""
    LISTING = "listing"
    COMPLETION = "completion"
    SUPPORT = "support"
    DISPUTE = "dispute"


class ChatStatus(str, Enum):
    """Статусы чатов"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class MessageType(str, Enum):
    """Типы сообщений"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


# Схемы для чатов
class ChatCreate(BaseModel):
    """Схема для создания чата"""
    type: ChatType = ChatType.LISTING
    title: Optional[str] = None
    listing_id: Optional[int] = None
    transaction_id: Optional[int] = None
    participant_ids: List[int] = Field(..., description="Список ID участников чата")
    chat_metadata: Optional[Dict[str, Any]] = None


class ChatUpdate(BaseModel):
    """Схема для обновления чата"""
    title: Optional[str] = None
    status: Optional[ChatStatus] = None
    chat_metadata: Optional[Dict[str, Any]] = None

class ChatUpdateLinkings(BaseModel):
    """Схема для обновления связей чата"""
    transaction_id: Optional[int] = None
    listing_id: Optional[int] = None

class ChatParticipantResponse(BaseModel):
    """Схема участника чата"""
    id: int
    user_id: int
    role: str
    is_muted: bool
    joined_at: datetime
    last_read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatModeratorResponse(BaseModel):
    """Схема модератора чата"""
    id: int
    moderator_id: int
    assigned_by: int
    reason: Optional[str] = None
    is_active: bool
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Схема ответа с информацией о чате"""
    id: int
    type: ChatType
    status: ChatStatus
    title: Optional[str] = None
    listing_id: Optional[int] = None
    transaction_id: Optional[int] = None
    chat_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    participants: List[ChatParticipantResponse] = []
    moderators: List[ChatModeratorResponse] = []
    unread_count: Optional[int] = None
    last_message: Optional[str] = None

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Схема для списка чатов"""
    chats: List[ChatResponse]
    total: int
    page: int
    pages: int


# Схемы для сообщений
class MessageCreate(BaseModel):
    """Схема для создания сообщения"""
    content: str = Field(..., min_length=1, max_length=4000)
    type: MessageType = MessageType.TEXT
    attachments: Optional[List[Dict[str, Any]]] = None
    message_metadata: Optional[Dict[str, Any]] = None


class MessageUpdate(BaseModel):
    """Схема для обновления сообщения"""
    content: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    """Схема ответа с сообщением"""
    id: int
    chat_id: int
    sender_id: Optional[int] = None
    type: MessageType
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None
    message_metadata: Optional[Dict[str, Any]] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Схема для списка сообщений"""
    messages: List[MessageResponse]
    total: int
    page: int
    pages: int


# Схемы для WebSocket
class WebSocketMessage(BaseModel):
    """Схема для WebSocket сообщений"""
    type: str  # "message", "user_joined", "user_left", "typing", etc.
    data: Dict[str, Any]


class TypingNotification(BaseModel):
    """Схема для уведомления о наборе текста"""
    user_id: int
    chat_id: int
    is_typing: bool


# Схемы для модерации
class AssignModeratorRequest(BaseModel):
    """Запрос на назначение модератора"""
    moderator_id: int
    reason: Optional[str] = None


class ResolveDisputeRequest(BaseModel):
    """Запрос на разрешение спора"""
    resolution_notes: str 