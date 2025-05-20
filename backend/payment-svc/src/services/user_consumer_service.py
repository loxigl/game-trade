"""
Сервис для обработки событий пользователя из RabbitMQ
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.core import User
from ..database.connection import get_db
from .rabbitmq_service import get_rabbitmq_service

logger = logging.getLogger(__name__)

# Константы для обменников и очередей
USER_EXCHANGE = "user_events"
USER_QUEUE_PAYMENT = "payment_user_events"
USER_CREATED_KEY = "user.created"
USER_UPDATED_KEY = "user.updated"
USER_DELETED_KEY = "user.deleted"

class UserConsumerService:
    """
    Сервис для обработки событий пользователя из очереди RabbitMQ
    """
    
    @staticmethod
    async def setup_consumers():
        """
        Настраивает потребителей сообщений для событий пользователя
        """
        rabbit_service = get_rabbitmq_service()
        
        # Создаем потребителя для созданных пользователей
        await rabbit_service.create_consumer(
            exchange_name=USER_EXCHANGE,
            queue_name=USER_QUEUE_PAYMENT,
            routing_key=USER_CREATED_KEY,
            callback=UserConsumerService.handle_user_created
        )
        
        # Создаем потребителя для обновленных пользователей
        await rabbit_service.create_consumer(
            exchange_name=USER_EXCHANGE,
            queue_name=USER_QUEUE_PAYMENT,
            routing_key=USER_UPDATED_KEY,
            callback=UserConsumerService.handle_user_updated
        )
        
        # Создаем потребителя для удаленных пользователей
        await rabbit_service.create_consumer(
            exchange_name=USER_EXCHANGE,
            queue_name=USER_QUEUE_PAYMENT,
            routing_key=USER_DELETED_KEY,
            callback=UserConsumerService.handle_user_deleted
        )
        
        logger.info("User event consumers set up successfully")
    
    @staticmethod
    async def handle_user_created(message: Dict[str, Any]):
        """
        Обработчик события создания пользователя
        
        Args:
            message: Данные сообщения из RabbitMQ
        """
        try:
            # Получаем данные пользователя из сообщения
            user_data = message.get("user", {})
            if not user_data or "id" not in user_data:
                logger.error("Invalid user_created message format")
                return
            
            # Получаем сессию БД
            db = next(get_db())
            
            # Проверяем, существует ли пользователь в локальной БД
            existing_user = db.query(User).filter(User.id == user_data["id"]).first()
            if existing_user:
                logger.info(f"User {user_data['id']} already exists in payment-svc")
                # Обновляем данные пользователя
                existing_user.username = user_data.get("username", existing_user.username)
                existing_user.email = user_data.get("email", existing_user.email)
                db.commit()
                logger.info(f"Updated user {user_data['id']} in payment-svc")
                return
            
            # Создаем пользователя в локальной БД
            new_user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            logger.info(f"Created user {user_data['id']} in payment-svc")
            
        except Exception as e:
            logger.error(f"Error handling user_created event: {str(e)}")
            if 'db' in locals():
                db.rollback()
    
    @staticmethod
    async def handle_user_updated(message: Dict[str, Any]):
        """
        Обработчик события обновления пользователя
        
        Args:
            message: Данные сообщения из RabbitMQ
        """
        try:
            # Получаем данные пользователя из сообщения
            user_data = message.get("user", {})
            if not user_data or "id" not in user_data:
                logger.error("Invalid user_updated message format")
                return
            
            # Получаем сессию БД
            db = next(get_db())
            
            # Находим пользователя в БД
            user = db.query(User).filter(User.id == user_data["id"]).first()
            
            # Если пользователь не найден, создаем его
            if not user:
                user = User(
                    id=user_data["id"],
                    username=user_data.get("username", ""),
                    email=user_data.get("email", "")
                )
                db.add(user)
                logger.info(f"Created missing user {user_data['id']} in payment-svc")
            else:
                # Обновляем данные пользователя
                user.username = user_data.get("username", user.username)
                user.email = user_data.get("email", user.email)
                logger.info(f"Updated user {user_data['id']} in payment-svc")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error handling user_updated event: {str(e)}")
            if 'db' in locals():
                db.rollback()
    
    @staticmethod
    async def handle_user_deleted(message: Dict[str, Any]):
        """
        Обработчик события удаления пользователя
        
        Args:
            message: Данные сообщения из RabbitMQ
        """
        try:
            # Получаем ID пользователя из сообщения
            user_id = message.get("user_id")
            
            # Проверяем формат сообщения
            if not user_id:
                user_data = message.get("user", {})
                if user_data and "id" in user_data:
                    user_id = user_data["id"]
                else:
                    logger.error("Invalid user_deleted message format")
                    return
            
            # Получаем сессию БД
            db = next(get_db())
            
            # Находим пользователя в БД и удаляем его
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found in payment-svc for deletion")
                return
                
            # Удаляем пользователя
            db.delete(user)
            db.commit()
            logger.info(f"Deleted user {user_id} in payment-svc")
            
        except Exception as e:
            logger.error(f"Error handling user_deleted event: {str(e)}")
            if 'db' in locals():
                db.rollback() 