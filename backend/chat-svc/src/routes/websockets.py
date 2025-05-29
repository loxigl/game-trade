"""
Маршруты для WebSocket соединений
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..services.websocket_manager import websocket_manager
from ..services.auth_service import auth_service
from ..services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_websocket_token(token: str) -> int:
    """
    Получение ID пользователя из токена для WebSocket
    
    Args:
        token: JWT токен
        
    Returns:
        ID пользователя
        
    Raises:
        Exception: Если токен недействителен
    """
    logger.info(f"get_user_from_websocket_token: {token}")
    user_data = await auth_service.validate_token(token)
    logger.info(f"user_data: {user_data}")
    if not user_data or not user_data.get("is_valid"):
        logger.info(f"Недействительный токен: {user_data}")
        raise Exception("Недействительный токен")
    
    return user_data["user_id"]


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT токен для аутентификации")
):
    """
    WebSocket соединение для пользователя
    
    Args:
        websocket: WebSocket соединение
        token: JWT токен
    """
    try:
        # Аутентификация пользователя
        user_id = await get_user_from_websocket_token(token)
        
        # Подключаем пользователя
        await websocket_manager.connect_user(websocket, user_id)
        
        logger.info(f"WebSocket соединение установлено для пользователя {user_id}")
        
        # Основной цикл обработки сообщений
        while True:
            try:
                # Получаем сообщение от клиента
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                message_data = message.get("data", {})
                
                # Обрабатываем различные типы сообщений
                await handle_websocket_message(websocket, user_id, message_type, message_data)
                
            except json.JSONDecodeError:
                logger.error(f"Получено некорректное JSON сообщение от пользователя {user_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Некорректный формат сообщения"}
                }))
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения от пользователя {user_id}: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Ошибка обработки сообщения"}
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket соединение закрыто для пользователя {user_id if 'user_id' in locals() else 'неизвестно'}")
        
    except Exception as e:
        logger.error(f"Ошибка WebSocket аутентификации: {str(e)}")
        await websocket.close(code=4001, reason="Ошибка аутентификации")
        
    finally:
        # Отключаем пользователя
        await websocket_manager.disconnect_user(websocket)


async def handle_websocket_message(websocket: WebSocket, user_id: int, message_type: str, message_data: dict):
    """
    Обработка WebSocket сообщений
    
    Args:
        websocket: WebSocket соединение
        user_id: ID пользователя
        message_type: Тип сообщения
        message_data: Данные сообщения
    """
    try:
        if message_type == "join_chat":
            # Подписка на чат
            chat_id = message_data.get("chat_id")
            if not chat_id:
                raise ValueError("chat_id обязателен")
            
            # Проверяем доступ к чату
            # Здесь можно добавить проверку через chat_service.is_participant
            
            await websocket_manager.join_chat(websocket, chat_id)
            
            # Отправляем подтверждение
            await websocket.send_text(json.dumps({
                "type": "joined_chat",
                "data": {"chat_id": chat_id}
            }))
            
        elif message_type == "leave_chat":
            # Отписка от чата
            chat_id = message_data.get("chat_id")
            if not chat_id:
                raise ValueError("chat_id обязателен")
            
            await websocket_manager.leave_chat(websocket, chat_id)
            
            # Отправляем подтверждение
            await websocket.send_text(json.dumps({
                "type": "left_chat",
                "data": {"chat_id": chat_id}
            }))
            
        elif message_type == "typing":
            # Уведомление о печатании
            chat_id = message_data.get("chat_id")
            is_typing = message_data.get("is_typing", False)
            
            if not chat_id:
                raise ValueError("chat_id обязателен")
            
            await websocket_manager.handle_typing(websocket, chat_id, is_typing)
            
        elif message_type == "ping":
            # Пинг для поддержания соединения
            await websocket.send_text(json.dumps({
                "type": "pong",
                "data": {"timestamp": message_data.get("timestamp")}
            }))
            
        else:
            logger.warning(f"Неизвестный тип сообщения: {message_type}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": f"Неизвестный тип сообщения: {message_type}"}
            }))
            
    except ValueError as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": str(e)}
        }))
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения типа {message_type}: {str(e)}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": "Внутренняя ошибка сервера"}
        }))


@router.websocket("/ws/chat/{chat_id}")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(..., description="JWT токен для аутентификации")
):
    """
    WebSocket соединение для конкретного чата
    
    Args:
        websocket: WebSocket соединение
        chat_id: ID чата
        token: JWT токен
    """
    try:
        # Аутентификация пользователя
        user_id = await get_user_from_websocket_token(token)
        
        # Подключаем пользователя
        await websocket_manager.connect_user(websocket, user_id)
        
        # Сразу подписываемся на чат
        await websocket_manager.join_chat(websocket, chat_id)
        
        logger.info(f"Пользователь {user_id} подключился к чату {chat_id}")
        
        # Основной цикл обработки сообщений
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                message_data = message.get("data", {})
                
                # Для этого эндпоинта автоматически добавляем chat_id
                message_data["chat_id"] = chat_id
                
                await handle_websocket_message(websocket, user_id, message_type, message_data)
                
            except json.JSONDecodeError:
                logger.error(f"Получено некорректное JSON сообщение в чате {chat_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Некорректный формат сообщения"}
                }))
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения в чате {chat_id}: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Ошибка обработки сообщения"}
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket соединение с чатом {chat_id} закрыто")
        
    except Exception as e:
        logger.error(f"Ошибка WebSocket для чата {chat_id}: {str(e)}")
        await websocket.close(code=4001, reason="Ошибка соединения")
        
    finally:
        # Отключаем пользователя
        await websocket_manager.disconnect_user(websocket) 