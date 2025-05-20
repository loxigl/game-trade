"""
Сервис для периодической очистки устаревших записей идемпотентности
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from ..database.connection import get_db
from .idempotency_service import get_idempotency_service

logger = logging.getLogger(__name__)

class IdempotencyCleanupService:
    """
    Сервис для периодической очистки устаревших записей идемпотентности
    
    Запускает фоновую задачу, которая периодически удаляет истекшие записи
    идемпотентности из базы данных.
    """
    
    def __init__(self):
        """Инициализация сервиса очистки"""
        self._initialized = False
        self._running = False
        self.cleanup_interval = 60 * 60 * 12  # 12 часов (в секундах)
    
    async def initialize(self) -> None:
        """Инициализация сервиса"""
        if self._initialized:
            return
        
        # Запускаем фоновую задачу
        asyncio.create_task(self._background_cleanup_loop())
        
        logger.info("Сервис очистки записей идемпотентности инициализирован")
        self._initialized = True
    
    async def _background_cleanup_loop(self) -> None:
        """Фоновая задача для периодической очистки идемпотентных записей"""
        self._running = True
        
        logger.info(f"Запуск фоновой задачи очистки записей идемпотентности (интервал: {self.cleanup_interval} сек)")
        
        while self._running:
            try:
                # Выполняем очистку
                await self._cleanup_expired_records()
            except Exception as e:
                logger.error(f"Ошибка при очистке записей идемпотентности: {str(e)}")
            
            # Ждем до следующей очистки
            await asyncio.sleep(self.cleanup_interval)
    
    async def _cleanup_expired_records(self) -> None:
        """Очистка истекших записей идемпотентности"""
        # Получаем сессию БД
        db = next(get_db())
        
        try:
            # Получаем сервис идемпотентности
            idempotency_service = get_idempotency_service(db)
            
            # Очищаем истекшие записи
            count = await idempotency_service.cleanup_expired()
            
            if count > 0:
                logger.info(f"Очищено {count} истекших записей идемпотентности")
            else:
                logger.debug("Истекших записей идемпотентности не найдено")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке записей идемпотентности: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def stop(self) -> None:
        """Остановка сервиса"""
        self._running = False
        logger.info("Сервис очистки записей идемпотентности остановлен")

# Синглтон для сервиса очистки
_idempotency_cleanup_service_instance = None

async def get_idempotency_cleanup_service() -> IdempotencyCleanupService:
    """
    Получение экземпляра сервиса очистки записей идемпотентности
    
    Returns:
        Экземпляр IdempotencyCleanupService
    """
    global _idempotency_cleanup_service_instance
    
    if _idempotency_cleanup_service_instance is None:
        _idempotency_cleanup_service_instance = IdempotencyCleanupService()
        await _idempotency_cleanup_service_instance.initialize()
    
    return _idempotency_cleanup_service_instance

async def setup_idempotency_cleanup_service() -> None:
    """
    Настройка сервиса очистки записей идемпотентности
    """
    await get_idempotency_cleanup_service() 