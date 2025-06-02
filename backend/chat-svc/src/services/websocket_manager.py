"""
Менеджер WebSocket соединений для чатов
"""

import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Менеджер WebSocket соединений"""

    def __init__(self):
        # Словарь: chat_id -> список соединений
        self.chat_connections: Dict[int, List[WebSocket]] = {}
        
        # Словарь: user_id -> список соединений 
        self.user_connections: Dict[int, List[WebSocket]] = {}
        
        # Словарь: websocket -> user_id для быстрого поиска
        self.connection_users: Dict[WebSocket, int] = {}
        
        # Словарь: websocket -> set(chat_ids) для отслеживания подписок
        self.connection_chats: Dict[WebSocket, Set[int]] = {}
        
        # Список пользователей, которые сейчас печатают: chat_id -> set(user_ids)
        self.typing_users: Dict[int, Set[int]] = {}

    async def connect_user(self, websocket: WebSocket, user_id: int):
        """
        Подключение пользователя по WebSocket
        
        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя
        """
        await websocket.accept()
        
        # Добавляем соединение к пользователю
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        
        # Сохраняем связь websocket -> user_id
        self.connection_users[websocket] = user_id
        self.connection_chats[websocket] = set()
        
        logger.info(f"Пользователь {user_id} подключился через WebSocket")

    async def disconnect_user(self, websocket: WebSocket):
        """
        Отключение пользователя
        
        Args:
            websocket: WebSocket соединение
        """
        user_id = self.connection_users.get(websocket)
        if not user_id:
            return
            
        # Убираем соединение из всех чатов
        subscribed_chats = self.connection_chats.get(websocket, set())
        for chat_id in subscribed_chats:
            await self.leave_chat(websocket, chat_id)
            
        # Убираем соединение от пользователя
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Убираем из словарей отслеживания
        self.connection_users.pop(websocket, None)
        self.connection_chats.pop(websocket, None)
        
        logger.info(f"Пользователь {user_id} отключился от WebSocket")

    async def join_chat(self, websocket: WebSocket, chat_id: int):
        """
        Подписка на чат
        
        Args:
            websocket: WebSocket соединение
            chat_id: ID чата
        """
        # Добавляем соединение к чату
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = []
        
        if websocket not in self.chat_connections[chat_id]:
            self.chat_connections[chat_id].append(websocket)
        
        # Отмечаем подписку
        if websocket in self.connection_chats:
            self.connection_chats[websocket].add(chat_id)
        
        user_id = self.connection_users.get(websocket)
        logger.info(f"Пользователь {user_id} подписался на чат {chat_id}")
        
        # Уведомляем других участников о подключении
        await self.broadcast_to_chat(chat_id, {
            "type": "user_joined",
            "data": {
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_websocket=websocket)

    async def leave_chat(self, websocket: WebSocket, chat_id: int):
        """
        Отписка от чата
        
        Args:
            websocket: WebSocket соединение
            chat_id: ID чата
        """
        # Убираем соединение из чата
        if chat_id in self.chat_connections:
            if websocket in self.chat_connections[chat_id]:
                self.chat_connections[chat_id].remove(websocket)
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        # Убираем подписку
        if websocket in self.connection_chats:
            self.connection_chats[websocket].discard(chat_id)
        
        # Убираем из списка печатающих
        if chat_id in self.typing_users:
            user_id = self.connection_users.get(websocket)
            if user_id:
                self.typing_users[chat_id].discard(user_id)
                if not self.typing_users[chat_id]:
                    del self.typing_users[chat_id]
        
        user_id = self.connection_users.get(websocket)
        logger.info(f"Пользователь {user_id} отписался от чата {chat_id}")
        
        # Уведомляем других участников об отключении
        await self.broadcast_to_chat(chat_id, {
            "type": "user_left",
            "data": {
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """
        Отправка сообщения конкретному пользователю
        
        Args:
            user_id: ID пользователя
            message: Сообщение для отправки
        """
        if user_id not in self.user_connections:
            return
            
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for websocket in self.user_connections[user_id]:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                disconnected.append(websocket)
        
        # Убираем отключенные соединения
        for websocket in disconnected:
            await self.disconnect_user(websocket)

    async def broadcast_to_chat(
        self, 
        chat_id: int, 
        message: Dict[str, Any], 
        exclude_websocket: Optional[WebSocket] = None
    ):
        """
        Рассылка сообщения всем участникам чата
        
        Args:
            chat_id: ID чата
            message: Сообщение для рассылки
            exclude_websocket: WebSocket, который нужно исключить из рассылки
        """
        if chat_id not in self.chat_connections:
            return
            
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for websocket in self.chat_connections[chat_id]:
            if websocket == exclude_websocket:
                continue
                
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                user_id = self.connection_users.get(websocket)
                logger.error(f"Ошибка отправки сообщения в чат {chat_id} пользователю {user_id}: {e}")
                disconnected.append(websocket)
        
        # Убираем отключенные соединения
        for websocket in disconnected:
            await self.disconnect_user(websocket)

    async def handle_typing(self, websocket: WebSocket, chat_id: int, is_typing: bool):
        """
        Обработка уведомлений о печатании
        
        Args:
            websocket: WebSocket соединение
            chat_id: ID чата
            is_typing: True если пользователь печатает
        """
        user_id = self.connection_users.get(websocket)
        if not user_id:
            return
            
        # Обновляем состояние печатания
        if chat_id not in self.typing_users:
            self.typing_users[chat_id] = set()
            
        if is_typing:
            self.typing_users[chat_id].add(user_id)
        else:
            self.typing_users[chat_id].discard(user_id)
            if not self.typing_users[chat_id]:
                del self.typing_users[chat_id]
        
        # Уведомляем других участников
        await self.broadcast_to_chat(chat_id, {
            "type": "typing",
            "data": {
                "user_id": user_id,
                "chat_id": chat_id,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_websocket=websocket)

    async def send_message_notification(self, chat_id: int, message_data: Dict[str, Any]):
        """
        Отправка уведомления о новом сообщении
        
        Args:
            chat_id: ID чата
            message_data: Данные сообщения
        """
        await self.broadcast_to_chat(chat_id, {
            "type": "new_message",
            "data": message_data
        })

    def get_chat_participants_count(self, chat_id: int) -> int:
        """
        Получение количества подключенных участников чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Количество подключенных участников
        """
        if chat_id not in self.chat_connections:
            return 0
        return len(self.chat_connections[chat_id])

    def is_user_online(self, user_id: int) -> bool:
        """
        Проверка, подключен ли пользователь
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь подключен
        """
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0


# Singleton экземпляр
websocket_manager = WebSocketManager() 