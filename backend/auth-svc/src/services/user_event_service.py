"""
Сервис для публикации событий пользователя в RabbitMQ.
Этот сервис отвечает за отправку сообщений о создании, обновлении и удалении пользователей.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from ..models.user import User
from .rabbitmq_service import get_rabbitmq_service

logger = logging.getLogger(__name__)

# Константы для обменников и ключей маршрутизации
USER_EXCHANGE = "user_events"
USER_CREATED_KEY = "user.created"
USER_UPDATED_KEY = "user.updated"
USER_DELETED_KEY = "user.deleted"

class UserEventService:
    """
    Сервис для публикации событий пользователя в RabbitMQ.
    """
    
    @staticmethod
    async def publish_user_created(user: User) -> None:
        """
        Публикует событие о создании нового пользователя
        
        Args:
            user: Объект пользователя
        """
        rabbit_service = get_rabbitmq_service()
        
        # Подготавливаем данные для сообщения
        user_data = {
            "event_type": "user_created",
            "timestamp": datetime.utcnow().isoformat(),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "roles": user.roles,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
        
        try:
            # Публикуем сообщение
            await rabbit_service.publish(
                exchange_name=USER_EXCHANGE,
                routing_key=USER_CREATED_KEY,
                message=user_data
            )
            logger.info(f"Published user_created event for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to publish user_created event: {str(e)}")

    @staticmethod
    async def publish_user_updated(user: User) -> None:
        """
        Публикует событие об обновлении пользователя
        
        Args:
            user: Объект пользователя
        """
        rabbit_service = get_rabbitmq_service()
        
        # Подготавливаем данные для сообщения
        user_data = {
            "event_type": "user_updated",
            "timestamp": datetime.utcnow().isoformat(),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "roles": user.roles,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        }
        
        try:
            # Публикуем сообщение
            await rabbit_service.publish(
                exchange_name=USER_EXCHANGE,
                routing_key=USER_UPDATED_KEY,
                message=user_data
            )
            logger.info(f"Published user_updated event for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to publish user_updated event: {str(e)}")

    @staticmethod
    async def publish_user_deleted(user_id: int) -> None:
        """
        Публикует событие об удалении пользователя
        
        Args:
            user_id: ID удаленного пользователя
        """
        rabbit_service = get_rabbitmq_service()
        
        # Подготавливаем данные для сообщения
        user_data = {
            "event_type": "user_deleted",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        
        try:
            # Публикуем сообщение
            await rabbit_service.publish(
                exchange_name=USER_EXCHANGE,
                routing_key=USER_DELETED_KEY,
                message=user_data
            )
            logger.info(f"Published user_deleted event for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to publish user_deleted event: {str(e)}") 