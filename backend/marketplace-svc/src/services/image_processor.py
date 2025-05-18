"""
Сервис для обработки изображений из очереди RabbitMQ
"""

import os
import asyncio
from typing import Dict, Any
import logging
from PIL import Image as PILImage
from io import BytesIO

from .rabbitmq_service import get_rabbitmq_service
from ..config.settings import get_settings
from ..database.connection import get_async_db as get_db_session
from ..models.core import Image

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Сервис для обработки изображений, полученных из очереди RabbitMQ
    Обрабатывает изображения асинхронно: изменяет размер, создает миниатюры и т.д.
    """

    def __init__(self):
        """Инициализация сервиса"""
        self.settings = get_settings()
        self.rabbitmq = get_rabbitmq_service()
        self.upload_dir = os.path.join(os.getcwd(), "uploads")

        # Создаем директории для миниатюр и обработанных изображений
        self.thumbs_dir = os.path.join(self.upload_dir, "thumbs")
        os.makedirs(self.thumbs_dir, exist_ok=True)

    async def start_consumer(self):
        """Запуск потребителя сообщений из очереди RabbitMQ"""
        await self.rabbitmq.create_consumer(
            self.settings.RABBITMQ_EXCHANGE,
            self.settings.RABBITMQ_IMAGES_QUEUE,
            self.settings.RABBITMQ_IMAGES_ROUTING_KEY,
            self.process_image_message
        )
        logger.info("Image consumer started")

    async def process_image_message(self, message: Dict[str, Any]):
        """
        Обработка сообщения с изображением

        Args:
            message: Сообщение из очереди RabbitMQ
        """
        logger.info(f"Processing image message: {message}")

        try:
            image_id = message.get("image_id")
            file_path = message.get("file_path")

            if not image_id or not file_path or not os.path.exists(file_path):
                logger.error(f"Invalid message or file not found: {message}")
                return

            # Создаем миниатюру
            thumbnail_path = await self.create_thumbnail(file_path)

            # Обновляем запись в базе данных
            await self.update_image_record(image_id, thumbnail_path)

            logger.info(f"Image {image_id} processed successfully")
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")

    async def create_thumbnail(self, file_path: str, size: tuple = (200, 200)) -> str:
        """
        Создание миниатюры изображения

        Args:
            file_path: Путь к исходному файлу
            size: Размер миниатюры (ширина, высота)

        Returns:
            Путь к созданной миниатюре
        """
        # Получаем имя файла
        filename = os.path.basename(file_path)
        thumbnail_path = os.path.join(self.thumbs_dir, f"thumb_{filename}")

        # Создаем миниатюру
        try:
            with PILImage.open(file_path) as img:
                img.thumbnail(size)
                img.save(thumbnail_path)
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return ""

        return thumbnail_path

    async def update_image_record(self, image_id: int, thumbnail_path: str):
        """
        Обновление записи об изображении в базе данных

        Args:
            image_id: ID изображения
            thumbnail_path: Путь к миниатюре
        """
        async with get_db_session() as session:
            # Получаем изображение из базы данных
            image = await session.get(Image, image_id)
            if not image:
                logger.error(f"Image {image_id} not found in database")
                return

            # Обновляем путь к миниатюре
            image.thumbnail_path = thumbnail_path
            image.is_processed = True

            # Сохраняем изменения
            await session.commit()

            logger.info(f"Image record {image_id} updated with thumbnail path")


async def start_image_processor():
    """
    Запуск обработчика изображений как отдельный сервис
    """
    processor = ImageProcessor()
    await processor.start_consumer()

    # Держим сервис запущенным
    while True:
        await asyncio.sleep(3600)  # Проверяем каждый час

if __name__ == "__main__":
    # Запускаем обработчик изображений
    asyncio.run(start_image_processor())
