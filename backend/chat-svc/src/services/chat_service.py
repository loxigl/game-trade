"""
Сервис для управления чатами
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime

from ..models.chat import Chat, ChatParticipant, ChatMessage, ChatModerator, ChatType, ChatStatus, MessageType
from ..schemas.chat import ChatCreate, ChatUpdate, MessageCreate, MessageUpdate
from .rabbitmq_service import get_rabbitmq_service

logger = logging.getLogger(__name__)


class ChatService:
    """Сервис для управления чатами"""

    def __init__(self, db: Session):
        self.db = db

    def create_chat(self, chat_data: ChatCreate, creator_id: int) -> Chat:
        """
        Создание нового чата
        
        Args:
            chat_data: Данные для создания чата
            creator_id: ID создателя чата
            
        Returns:
            Созданный чат
        """
        # Создаем чат
        chat = Chat(
            type=chat_data.type,
            title=chat_data.title,
            listing_id=chat_data.listing_id,
            transaction_id=chat_data.transaction_id,
            chat_metadata=chat_data.chat_metadata
        )
        
        self.db.add(chat)
        self.db.flush()  # Получаем ID чата
        
        # Добавляем участников
        participants = []
        for user_id in chat_data.participant_ids:
            participant = ChatParticipant(
                chat_id=chat.id,
                user_id=user_id,
                role="admin" if user_id == creator_id else "participant"
            )
            participants.append(participant)
            self.db.add(participant)
        
        self.db.commit()
        self.db.refresh(chat)
        
        logger.info(f"Создан чат ID={chat.id} пользователем ID={creator_id}")
        return chat

    def get_chat_by_id(self, chat_id: int, user_id: Optional[int] = None) -> Optional[Chat]:
        """
        Получение чата по ID
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя (для проверки доступа)
            
        Returns:
            Чат или None
        """
        query = self.db.query(Chat).filter(Chat.id == chat_id)
        
        # Если указан пользователь, проверяем его участие в чате
        if user_id is not None:
            query = query.join(ChatParticipant).filter(ChatParticipant.user_id == user_id)
        
        return query.first()

    def get_user_chats(
        self, 
        user_id: int, 
        status: Optional[ChatStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Chat], int]:
        """
        Получение чатов пользователя
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу чата
            page: Номер страницы
            page_size: Размер страницы
            
        Returns:
            Кортеж (список чатов, общее количество)
        """
        query = (
            self.db.query(Chat)
            .join(ChatParticipant)
            .filter(ChatParticipant.user_id == user_id)
        )
        
        if status:
            query = query.filter(Chat.status == status)
            
        # Подсчет общего количества
        total = query.count()
        
        # Пагинация и сортировка
        chats = (
            query
            .order_by(desc(Chat.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        return chats, total

    def get_all_chats(
        self,
        status: Optional[ChatStatus] = None,
        chat_type: Optional[ChatType] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Chat], int]:
        """
        Получение всех чатов (для админов)
        
        Args:
            status: Фильтр по статусу
            chat_type: Фильтр по типу чата
            page: Номер страницы
            page_size: Размер страницы
            
        Returns:
            Кортеж (список чатов, общее количество)
        """
        query = self.db.query(Chat)
        
        if status:
            query = query.filter(Chat.status == status)
        if chat_type:
            query = query.filter(Chat.type == chat_type)
            
        total = query.count()
        
        chats = (
            query
            .order_by(desc(Chat.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        return chats, total

    def update_chat(self, chat_id: int, chat_data: ChatUpdate) -> Optional[Chat]:
        """
        Обновление чата
        
        Args:
            chat_id: ID чата
            chat_data: Данные для обновления
            
        Returns:
            Обновленный чат или None
        """
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return None
            
        # Обновляем поля
        if chat_data.title is not None:
            chat.title = chat_data.title
        if chat_data.status is not None:
            chat.status = chat_data.status
        if chat_data.chat_metadata is not None:
            chat.chat_metadata = chat_data.chat_metadata
            
        self.db.commit()
        self.db.refresh(chat)
        
        return chat

    def add_participant(self, chat_id: int, user_id: int, role: str = "participant") -> Optional[ChatParticipant]:
        """
        Добавление участника в чат
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            role: Роль участника
            
        Returns:
            Участник чата или None
        """
        # Проверяем, не является ли пользователь уже участником
        existing = (
            self.db.query(ChatParticipant)
            .filter(and_(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
            .first()
        )
        
        if existing:
            return existing
            
        participant = ChatParticipant(
            chat_id=chat_id,
            user_id=user_id,
            role=role
        )
        
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        
        return participant

    def remove_participant(self, chat_id: int, user_id: int) -> bool:
        """
        Удаление участника из чата
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            
        Returns:
            True если успешно удален
        """
        participant = (
            self.db.query(ChatParticipant)
            .filter(and_(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
            .first()
        )
        
        if participant:
            self.db.delete(participant)
            self.db.commit()
            return True
            
        return False

    def is_participant(self, chat_id: int, user_id: int) -> bool:
        """
        Проверка участия пользователя в чате
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            
        Returns:
            True если пользователь участник чата
        """
        participant = (
            self.db.query(ChatParticipant)
            .filter(and_(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
            .first()
        )
        
        return participant is not None

    def create_message(self, chat_id: int, message_data: MessageCreate, sender_id: Optional[int] = None) -> Optional[ChatMessage]:
        """
        Создание сообщения в чате
        
        Args:
            chat_id: ID чата
            message_data: Данные сообщения
            sender_id: ID отправителя (None для системных сообщений)
            
        Returns:
            Созданное сообщение или None
        """
        # Проверяем существование чата
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return None
            
        # Создаем сообщение
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            type=message_data.type,
            content=message_data.content,
            attachments=message_data.attachments,
            message_metadata=message_data.message_metadata
        )
        
        self.db.add(message)
        
        # Обновляем время последнего обновления чата
        chat.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message

    def get_messages(
        self,
        chat_id: int,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[int] = None
    ) -> tuple[List[ChatMessage], int]:
        """
        Получение сообщений чата
        
        Args:
            chat_id: ID чата
            page: Номер страницы
            page_size: Размер страницы
            user_id: ID пользователя (для проверки доступа)
            
        Returns:
            Кортеж (список сообщений, общее количество)
        """
        # Проверяем доступ к чату
        if user_id and not self.is_participant(chat_id, user_id):
            return [], 0
            
        query = (
            self.db.query(ChatMessage)
            .filter(and_(ChatMessage.chat_id == chat_id, ChatMessage.is_deleted == False))
        )
        
        total = query.count()
        
        messages = (
            query
            .order_by(desc(ChatMessage.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        # Возвращаем в хронологическом порядке
        messages.reverse()
        
        return messages, total

    def update_message(self, message_id: int, message_data: MessageUpdate, user_id: int) -> Optional[ChatMessage]:
        """
        Обновление сообщения
        
        Args:
            message_id: ID сообщения
            message_data: Новые данные сообщения
            user_id: ID пользователя (только автор может редактировать)
            
        Returns:
            Обновленное сообщение или None
        """
        message = (
            self.db.query(ChatMessage)
            .filter(and_(ChatMessage.id == message_id, ChatMessage.sender_id == user_id))
            .first()
        )
        
        if not message:
            return None
            
        message.content = message_data.content
        message.is_edited = True
        message.edited_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message

    def delete_message(self, message_id: int, user_id: int) -> bool:
        """
        Удаление сообщения
        
        Args:
            message_id: ID сообщения
            user_id: ID пользователя
            
        Returns:
            True если успешно удалено
        """
        message = (
            self.db.query(ChatMessage)
            .filter(and_(ChatMessage.id == message_id, ChatMessage.sender_id == user_id))
            .first()
        )
        
        if message:
            message.is_deleted = True
            message.deleted_at = datetime.utcnow()
            self.db.commit()
            return True
            
        return False

    def assign_moderator(self, chat_id: int, moderator_id: int, assigned_by: int, reason: Optional[str] = None) -> Optional[ChatModerator]:
        """
        Назначение модератора чата
        
        Args:
            chat_id: ID чата
            moderator_id: ID модератора
            assigned_by: ID пользователя, назначающего модератора
            reason: Причина назначения
            
        Returns:
            Объект модератора или None
        """
        # Проверяем, не назначен ли уже модератор
        existing = (
            self.db.query(ChatModerator)
            .filter(and_(
                ChatModerator.chat_id == chat_id,
                ChatModerator.moderator_id == moderator_id,
                ChatModerator.is_active == True
            ))
            .first()
        )
        
        if existing:
            return existing
            
        moderator = ChatModerator(
            chat_id=chat_id,
            moderator_id=moderator_id,
            assigned_by=assigned_by,
            reason=reason
        )
        
        self.db.add(moderator)
        
        # Обновляем статус чата
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if chat:
            chat.status = ChatStatus.DISPUTED
            
        self.db.commit()
        self.db.refresh(moderator)
        
        return moderator

    def resolve_dispute(self, chat_id: int, moderator_id: int, resolution_notes: str) -> bool:
        """
        Разрешение спора в чате
        
        Args:
            chat_id: ID чата
            moderator_id: ID модератора
            resolution_notes: Заметки о разрешении
            
        Returns:
            True если успешно разрешен
        """
        moderator = (
            self.db.query(ChatModerator)
            .filter(and_(
                ChatModerator.chat_id == chat_id,
                ChatModerator.moderator_id == moderator_id,
                ChatModerator.is_active == True
            ))
            .first()
        )
        
        if not moderator:
            return False
            
        # Обновляем модератора
        moderator.is_active = False
        moderator.resolved_at = datetime.utcnow()
        moderator.resolution_notes = resolution_notes
        
        # Обновляем статус чата
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if chat:
            chat.status = ChatStatus.RESOLVED
            
        self.db.commit()
        
        return True

    def mark_messages_as_read(self, chat_id: int, user_id: int) -> bool:
        """
        Отметка сообщений как прочитанных
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            
        Returns:
            True если успешно обновлено
        """
        participant = (
            self.db.query(ChatParticipant)
            .filter(and_(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
            .first()
        )
        
        if participant:
            participant.last_read_at = datetime.utcnow()
            self.db.commit()
            return True
            
        return False

    def get_unread_count(self, chat_id: int, user_id: int) -> int:
        """
        Получение количества непрочитанных сообщений
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            
        Returns:
            Количество непрочитанных сообщений
        """
        participant = (
            self.db.query(ChatParticipant)
            .filter(and_(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
            .first()
        )
        
        if not participant:
            return 0
            
        query = (
            self.db.query(func.count(ChatMessage.id))
            .filter(and_(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_deleted == False
            ))
        )
        
        if participant.last_read_at:
            query = query.filter(ChatMessage.created_at > participant.last_read_at)
            
        return query.scalar() or 0 