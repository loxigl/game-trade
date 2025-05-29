"""
Обработчики сообщений RabbitMQ для chat-svc
"""

import logging
from typing import Dict, Any, Callable, Awaitable
import asyncio
import json

from .rabbitmq_service import get_rabbitmq_service, RabbitMQService

logger = logging.getLogger(__name__)

# Тип для обработчика сообщений
MessageHandler = Callable[[Dict[str, Any]], Awaitable[None]]

# Хранилище пользователей (в реальном проекте должно быть в базе данных)
users = {}


async def handle_user_created(message: Dict[str, Any]) -> None:
    """
    Обработчик события создания пользователя
    
    Args:
        message: Данные сообщения
    """
    logger.info(f"Получено сообщение о создании пользователя: {message}")
    
    try:
        user_data = message.get("user", {})
        if not user_data or not user_data.get("id"):
            logger.error("Некорректный формат сообщения о создании пользователя")
            return
            
        # Добавляем пользователя в хранилище
        user_id = user_data["id"]
        users[user_id] = {
            "id": user_id,
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "is_active": user_data.get("is_active", True),
            "roles": user_data.get("roles", []),
            "created_at": user_data.get("created_at")
        }
        
        logger.info(f"Пользователь добавлен в хранилище chat-svc: ID={user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке создания пользователя: {str(e)}")


async def handle_user_updated(message: Dict[str, Any]) -> None:
    """
    Обработчик события обновления пользователя
    
    Args:
        message: Данные сообщения
    """
    logger.info(f"Получено сообщение об обновлении пользователя: {message}")
    
    try:
        user_data = message.get("user", {})
        if not user_data or not user_data.get("id"):
            logger.error("Некорректный формат сообщения об обновлении пользователя")
            return
            
        user_id = user_data["id"]
        if user_id in users:
            # Обновляем существующего пользователя
            users[user_id].update({
                "username": user_data.get("username", users[user_id]["username"]),
                "email": user_data.get("email", users[user_id]["email"]),
                "is_active": user_data.get("is_active", users[user_id]["is_active"]),
                "roles": user_data.get("roles", users[user_id]["roles"])
            })
            logger.info(f"Обновлен пользователь в хранилище chat-svc: ID={user_id}")
        else:
            # Если пользователя нет, создаем нового
            users[user_id] = {
                "id": user_id,
                "username": user_data.get("username", ""),
                "email": user_data.get("email", ""),
                "is_active": user_data.get("is_active", True),
                "roles": user_data.get("roles", [])
            }
            logger.info(f"Создан пользователь в хранилище chat-svc: ID={user_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления пользователя: {str(e)}")


async def handle_user_deleted(message: Dict[str, Any]) -> None:
    """
    Обработчик события удаления пользователя
    
    Args:
        message: Данные сообщения
    """
    logger.info(f"Получено сообщение об удалении пользователя: {message}")
    
    try:
        user_id = message.get("user_id")
        if not user_id:
            logger.error("Некорректный формат сообщения об удалении пользователя")
            return
            
        if user_id in users:
            # Помечаем пользователя как неактивного
            users[user_id]["is_active"] = False
            logger.info(f"Пользователь в chat-svc с ID={user_id} помечен как неактивный")
        else:
            logger.warning(f"Пользователь с ID={user_id} не найден в хранилище chat-svc")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления пользователя: {str(e)}")


async def handle_completion_chat_request(message: Dict[str, Any]) -> None:
    """
    Обработчик события запроса на открытие чата для подтверждения доставки
    
    Args:
        message: Данные сообщения
    """
    logger.info(f"Получено сообщение о необходимости открытия окна чата для подтверждения доставки: {message}")
    
    try:
        event_type = message.get("event_type")
        if event_type != "open_completion_chat":
            logger.warning(f"Неожиданный тип события: {event_type}")
            return
            
        sale_id = message.get("sale_id")
        buyer_id = message.get("buyer_id")
        seller_id = message.get("seller_id")
        transaction_id = message.get("transaction_id")
        
        if not sale_id or not buyer_id or not seller_id or not transaction_id:
            logger.error("Некорректный формат сообщения для открытия чата")
            return
        
        # Создаем идентификатор чата для подтверждения доставки
        chat_id = f"completion_{sale_id}"
        
        # В реальной системе здесь создается запись о чате в базе данных
        # и отправляется уведомление пользователям
        
        # Отправляем системное сообщение в чат
        system_message = {
            "type": "system",
            "chat_id": chat_id,
            "content": "Покупатель инициировал подтверждение завершения доставки. Пожалуйста, обсудите детали завершения заказа.",
            "timestamp": message.get("timestamp"),
            "message_metadata": {
                "sale_id": sale_id,
                "transaction_id": transaction_id
            }
        }
        
        # Публикуем системное сообщение в обменник чатов
        rabbitmq = get_rabbitmq_service()
        await rabbitmq.publish(
            exchange="chat_messages",
            routing_key=f"chat.{chat_id}",
            message=system_message
        )
        
        logger.info(f"Системное сообщение отправлено в чат ID={chat_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на открытие чата: {str(e)}")


async def setup_rabbitmq_consumers() -> None:
    """
    Настройка потребителей сообщений RabbitMQ
    """
    # Получаем экземпляр сервиса RabbitMQ
    rabbitmq = get_rabbitmq_service()
    
    # Словарь с обработчиками сообщений для разных событий
    # Ключ: (exchange_name, routing_key)
    handlers = {
        ("user_events", "user.created"): handle_user_created,
        ("user_events", "user.updated"): handle_user_updated,
        ("user_events", "user.deleted"): handle_user_deleted,
        ("notification_events", "notification.chat.required"): handle_completion_chat_request,
    }
    
    # Регистрируем обработчики для разных типов сообщений
    for (exchange_name, routing_key), handler in handlers.items():
        queue_name = f"chat_svc_{exchange_name}_{routing_key.replace('.', '_')}"
        
        # Регистрируем потребителя
        await rabbitmq.create_consumer(exchange_name, queue_name, routing_key, handler)
        
        logger.info(f"Зарегистрирован обработчик для {exchange_name} -> {routing_key} -> {queue_name}") 