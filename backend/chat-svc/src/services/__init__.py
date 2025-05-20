"""
Модуль с сервисами для chat-svc
"""

from .rabbitmq_service import get_rabbitmq_service
from .message_handler import setup_rabbitmq_consumers

__all__ = [
    "get_rabbitmq_service",
    "setup_rabbitmq_consumers",
] 