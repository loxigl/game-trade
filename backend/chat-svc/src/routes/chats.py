"""
Маршруты для работы с чатами
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math
from datetime import datetime
import os

from ..database.connection import get_db
from ..schemas.chat import (
    ChatCreate, ChatResponse, ChatUpdate, ChatListResponse, ChatUpdateLinkings,
    MessageCreate, MessageResponse, MessageUpdate, MessageListResponse,
    AssignModeratorRequest, ResolveDisputeRequest
)
from ..services.chat_service import ChatService
from ..services.auth_service import get_current_user, require_moderator, User
from ..services.websocket_manager import websocket_manager

router = APIRouter(
    prefix="/chats",
    tags=["chats"],
    responses={401: {"description": "Не авторизован"}},
)


def serialize_for_websocket(data: dict) -> dict:
    """
    Сериализует данные для отправки через WebSocket, преобразуя datetime в ISO строки
    
    Args:
        data: Словарь с данными для сериализации
        
    Returns:
        Словарь с сериализованными datetime полями
    """
    result = data.copy()
    
    # Список полей, которые могут содержать datetime
    datetime_fields = ['created_at', 'updated_at', 'edited_at', 'joined_at', 'last_read_at', 'resolved_at']
    
    for field in datetime_fields:
        if field in result and result[field] is not None:
            if hasattr(result[field], 'isoformat'):
                result[field] = result[field].isoformat()
            elif isinstance(result[field], str):
                # Уже строка, оставляем как есть
                pass
            else:
                result[field] = str(result[field])
    
    # Обрабатываем вложенные списки (например, participants, moderators)
    if 'participants' in result and isinstance(result['participants'], list):
        result['participants'] = [serialize_for_websocket(p) if isinstance(p, dict) else p for p in result['participants']]
        
    if 'moderators' in result and isinstance(result['moderators'], list):
        result['moderators'] = [serialize_for_websocket(m) if isinstance(m, dict) else m for m in result['moderators']]
    
    return result


@router.post("/system/create", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_system_chat(
    chat_data: ChatCreate,
    system_token: str = Query(..., description="Системный токен"),
    db: Session = Depends(get_db)
):
    """
    Системное создание чата (для внутренних сервисов)
    
    Args:
        chat_data: Данные для создания чата
        system_token: Системный токен для авторизации
        db: Сессия базы данных
        
    Returns:
        Созданный чат
        
    Raises:
        HTTPException: Если системный токен неверный
    """
    # Проверяем системный токен (в продакшн можно использовать более сложную логику)
    expected_token = os.getenv("SYSTEM_TOKEN", "system_secret_token")
    if system_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный системный токен"
        )
    
    chat_service = ChatService(db)
    
    # Используем первого участника как создателя чата
    creator_id = chat_data.participant_ids[0] if chat_data.participant_ids else 1
    
    chat = chat_service.create_chat(chat_data, creator_id)
    
    # Возвращаем чат с дополнительной информацией
    chat_response = ChatResponse.from_orm(chat)
    chat_response.unread_count = 0
    
    return chat_response

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_data: ChatUpdateLinkings,
    db: Session = Depends(get_db)
): 
    chat_service = ChatService(db)
    chat = chat_service.update_chat_linkings(chat_id, chat_data)
    return ChatResponse.from_orm(chat)
    
@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового чата
    
    Args:
        chat_data: Данные для создания чата
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Созданный чат
    """
    chat_service = ChatService(db)
    
    # Проверяем, что создатель чата включен в список участников
    if current_user.id not in chat_data.participant_ids:
        chat_data.participant_ids.append(current_user.id)
    
    chat = chat_service.create_chat(chat_data, current_user.id)
    
    # Возвращаем чат с дополнительной информацией
    chat_response = ChatResponse.from_orm(chat)
    chat_response.unread_count = 0
    
    return chat_response


@router.get("", response_model=ChatListResponse)
async def get_user_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение чатов текущего пользователя
    
    Args:
        page: Номер страницы
        page_size: Размер страницы
        status: Фильтр по статусу чата
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список чатов пользователя
    """
    chat_service = ChatService(db)
    
    chats, total = chat_service.get_user_chats(
        user_id=current_user.id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # Добавляем дополнительную информацию к каждому чату
    chat_responses = []
    for chat in chats:
        chat_response = ChatResponse.from_orm(chat)
        
        # Количество непрочитанных сообщений
        chat_response.unread_count = chat_service.get_unread_count(chat.id, current_user.id)
        
        # Последнее сообщение
        messages, _ = chat_service.get_messages(chat.id, page=1, page_size=1)
        if messages:
            chat_response.last_message = messages[-1].content[:100] + "..." if len(messages[-1].content) > 100 else messages[-1].content
        
        chat_responses.append(chat_response)
    
    return ChatListResponse(
        chats=chat_responses,
        total=total,
        page=page,
        pages=math.ceil(total / page_size)
    )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение чата по ID
    
    Args:
        chat_id: ID чата
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Данные чата
        
    Raises:
        HTTPException: Если чат не найден или нет доступа
    """
    chat_service = ChatService(db)
    
    chat = chat_service.get_chat_by_id(chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден или нет доступа"
        )
    
    chat_response = ChatResponse.from_orm(chat)
    chat_response.unread_count = chat_service.get_unread_count(chat_id, current_user.id)
    
    return chat_response


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_data: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление чата
    
    Args:
        chat_id: ID чата
        chat_data: Данные для обновления
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Обновленный чат
        
    Raises:
        HTTPException: Если чат не найден или нет прав
    """
    chat_service = ChatService(db)
    
    # Проверяем доступ к чату
    if not chat_service.is_participant(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к чату"
        )
    
    chat = chat_service.update_chat(chat_id, chat_data)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Уведомляем участников об обновлении
    chat_data = serialize_for_websocket(ChatResponse.from_orm(chat).model_dump())
    await websocket_manager.send_chat_update(chat_id, chat_data)
    
    return ChatResponse.from_orm(chat)


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    chat_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создание сообщения в чате
    
    Args:
        chat_id: ID чата
        message_data: Данные сообщения
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Созданное сообщение
        
    Raises:
        HTTPException: Если чат не найден или нет доступа
    """
    chat_service = ChatService(db)
    
    # Проверяем доступ к чату
    if not chat_service.is_participant(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к чату"
        )
    
    message = chat_service.create_message(chat_id, message_data, current_user.id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    message_response = MessageResponse.from_orm(message)
    
    # Уведомляем участников о новом сообщении
    message_data = serialize_for_websocket(message_response.model_dump())
    await websocket_manager.send_message_notification(chat_id, message_data)
    
    return message_response


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение сообщений чата
    
    Args:
        chat_id: ID чата
        page: Номер страницы
        page_size: Размер страницы
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список сообщений
        
    Raises:
        HTTPException: Если чат не найден или нет доступа
    """
    chat_service = ChatService(db)
    
    messages, total = chat_service.get_messages(
        chat_id=chat_id,
        page=page,
        page_size=page_size,
        user_id=current_user.id
    )
    
    if not messages and total == 0 and not chat_service.is_participant(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к чату"
        )
    
    return MessageListResponse(
        messages=[MessageResponse.from_orm(message) for message in messages],
        total=total,
        page=page,
        pages=math.ceil(total / page_size)
    )


@router.patch("/{chat_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    chat_id: int,
    message_id: int,
    message_data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление сообщения
    
    Args:
        chat_id: ID чата
        message_id: ID сообщения
        message_data: Новые данные сообщения
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Обновленное сообщение
        
    Raises:
        HTTPException: Если сообщение не найдено или нет прав
    """
    chat_service = ChatService(db)
    
    message = chat_service.update_message(message_id, message_data, current_user.id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено или нет прав на редактирование"
        )
    
    message_response = MessageResponse.from_orm(message)
    
    # Уведомляем участников об обновлении сообщения
    message_data = serialize_for_websocket(message_response.model_dump())
    await websocket_manager.send_message_update(chat_id, message_data)
    
    return message_response


@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаление сообщения
    
    Args:
        chat_id: ID чата
        message_id: ID сообщения
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Raises:
        HTTPException: Если сообщение не найдено или нет прав
    """
    chat_service = ChatService(db)
    
    success = chat_service.delete_message(message_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено или нет прав на удаление"
        )
    
    # Уведомляем участников об удалении сообщения
    await websocket_manager.send_message_delete(chat_id, message_id)


@router.post("/{chat_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отметка сообщений как прочитанных
    
    Args:
        chat_id: ID чата
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Raises:
        HTTPException: Если чат не найден или нет доступа
    """
    chat_service = ChatService(db)
    
    success = chat_service.mark_messages_as_read(chat_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден или нет доступа"
        )


@router.post("/{chat_id}/moderator", status_code=status.HTTP_200_OK)
async def assign_moderator(
    chat_id: int,
    moderator_data: AssignModeratorRequest,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Назначение модератора чата
    
    Args:
        chat_id: ID чата
        moderator_data: Данные модератора
        current_user: Текущий пользователь (должен быть модератором/админом)
        db: Сессия базы данных
        
    Raises:
        HTTPException: Если чат не найден
    """
    chat_service = ChatService(db)
    
    moderator = chat_service.assign_moderator(
        chat_id=chat_id,
        moderator_id=moderator_data.moderator_id,
        assigned_by=current_user.id,
        reason=moderator_data.reason
    )
    
    if not moderator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось назначить модератора"
        )
    
    # Уведомляем участников чата
    await websocket_manager.send_moderator_assigned(chat_id, {
        "moderator_id": moderator.moderator_id,
        "assigned_by": moderator.assigned_by,
        "reason": moderator.reason,
        "timestamp": moderator.created_at.isoformat()
    })
    
    return {"message": "Модератор успешно назначен"}


@router.post("/{chat_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_dispute(
    chat_id: int,
    resolution_data: ResolveDisputeRequest,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Разрешение спора в чате
    
    Args:
        chat_id: ID чата
        resolution_data: Данные о разрешении
        current_user: Текущий пользователь (должен быть модератором)
        db: Сессия базы данных
        
    Raises:
        HTTPException: Если спор не найден или нет прав
    """
    chat_service = ChatService(db)
    
    success = chat_service.resolve_dispute(
        chat_id=chat_id,
        moderator_id=current_user.id,
        resolution_notes=resolution_data.resolution_notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Спор не найден или нет прав на разрешение"
        )
    
    return {"message": "Спор успешно разрешен"} 