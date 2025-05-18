"""
Сервис для работы с изображениями
"""
import os
import uuid
import aiofiles
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

from ..models.core import User, Image, ImageType, ImageStatus, Listing
from ..schemas.marketplace import ImageCreate, ImageUpdate
from ..config.settings import get_settings
from .rabbitmq_service import get_rabbitmq_service

class ImageService:
    """Сервис для управления загрузкой, хранением и удалением изображений"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
        self.settings = get_settings()
        self.rabbitmq = get_rabbitmq_service()
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        
        # Создаем директорию для загрузок, если она не существует
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_image(self, file: UploadFile, entity_id: int, image_type: ImageType, user_id: int) -> Image:
        """
        Сохранение изображения
        
        Args:
            file: Загруженный файл
            entity_id: ID сущности (листинга, категории и т.д.)
            image_type: Тип изображения
            
        Returns:
            Объект изображения из базы данных
            
        Raises:
            HTTPException: Если изображение не удалось сохранить
        """
        # Проверяем тип файла
        content_type = file.content_type
        if not content_type or not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл должен быть изображением"
            )
        
        # Создаем уникальное имя файла
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        filename = f"{uuid.uuid4()}{file_ext}"
        
        # Путь к файлу
        file_path = os.path.join(self.upload_dir, filename)
        
        # Сохраняем файл
        try:
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при сохранении файла: {str(e)}"
            )
        
        # Создаем запись в базе данных
        image = Image(
            filename=filename,
            owner_id=user_id,
            original_filename=file.filename,
            content_type=content_type,
            type=image_type.value,
            entity_id=entity_id,
            file_path=file_path
        )
        
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        
        # Отправляем сообщение в RabbitMQ для асинхронной обработки изображения
        await self._send_image_to_queue(image.id, file_path, image_type.value)
        
        return image
    
    async def _send_image_to_queue(self, image_id: int, file_path: str, image_type: str) -> None:
        """
        Отправка изображения в очередь RabbitMQ для обработки
        
        Args:
            image_id: ID изображения
            file_path: Путь к файлу
            image_type: Тип изображения
        """
        message = {
            "image_id": image_id,
            "file_path": file_path,
            "image_type": image_type
        }
        
        try:
            await self.rabbitmq.publish(
                self.settings.RABBITMQ_EXCHANGE,
                self.settings.RABBITMQ_IMAGES_ROUTING_KEY,
                message
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            print(f"Error sending image to queue: {str(e)}")
    
    def get_image_by_id(self, image_id: int) -> Image:
        """
        Получить изображение по ID
        
        Args:
            image_id: ID изображения
            
        Returns:
            Объект изображения
            
        Raises:
            HTTPException: Если изображение не найдено
        """
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Изображение не найдено"
            )
        
        return image
        
    def get_entity_images(self, entity_id: int, image_type: ImageType) -> List[Image]:
        """
        Получение изображений для сущности
        
        Args:
            entity_id: ID сущности
            image_type: Тип изображения
            
        Returns:
            Список изображений
        """
        return self.db.query(Image).filter(
            Image.entity_id == entity_id,
            Image.type == image_type.value
        ).order_by(Image.order_index).all()
    
    def get_user_images(self, user_id: int) -> List[Image]:
        """
        Получить все изображения, загруженные пользователем
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список изображений
        """
        images = self.db.query(Image).filter(
            Image.owner_id == user_id,
            Image.status == ImageStatus.ACTIVE
        ).order_by(desc(Image.created_at)).all()
        
        return images
    
    def delete_image(self, image_id: int) -> bool:
        """
        Удаление изображения
        
        Args:
            image_id: ID изображения
            
        Returns:
            True, если изображение успешно удалено
            
        Raises:
            HTTPException: Если изображение не найдено
        """
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Изображение не найдено"
            )
        
        # Удаляем файл
        file_path = os.path.join(self.upload_dir, image.filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Логируем ошибку, но продолжаем выполнение
            print(f"Error deleting file: {str(e)}")
        
        # Удаляем запись из базы данных
        self.db.delete(image)
        self.db.commit()
        
        return True
    
    def update_image_order(
        self, 
        image_id: int,
        new_order: int,
        user_id: int
    ) -> Image:
        """
        Обновить порядок отображения изображения
        
        Args:
            image_id: ID изображения
            new_order: Новый порядковый индекс
            user_id: ID пользователя, выполняющего обновление
            
        Returns:
            Обновленный объект изображения
            
        Raises:
            HTTPException: При ошибке или отсутствии прав
        """
        image = self.get_image_by_id(image_id)
        
        # Проверяем права на изменение
        if image.owner_id != user_id:
            # TODO: Добавить проверку прав администратора
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для изменения этого изображения"
            )
        
        # Обновляем порядок
        image.order_index = new_order
        self.db.commit()
        self.db.refresh(image)
        
        return image
    
    def set_main_image(self, image_id: int, entity_id: int, image_type: ImageType) -> bool:
        """
        Установка главного изображения
        
        Args:
            image_id: ID изображения
            entity_id: ID сущности
            image_type: Тип изображения
            
        Returns:
            True, если изображение успешно установлено как главное
            
        Raises:
            HTTPException: Если изображение не найдено или не принадлежит указанной сущности
        """
        # Проверяем, что изображение существует и принадлежит указанной сущности
        image = self.db.query(Image).filter(
            Image.id == image_id,
            Image.entity_id == entity_id,
            Image.type == image_type.value
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Изображение не найдено или не принадлежит указанной сущности"
            )
        
        # Сбрасываем флаг is_main для всех изображений этой сущности
        self.db.query(Image).filter(
            Image.entity_id == entity_id,
            Image.type == image_type.value
        ).update({"is_main": False})
        
        # Устанавливаем флаг is_main для выбранного изображения
        image.is_main = True
        
        self.db.commit()
        
        return image
    
    def attach_image_to_entity(
        self, 
        image_id: int, 
        entity_id: int, 
        image_type: ImageType,
        user_id: int
    ) -> Image:
        """
        Привязать существующее изображение к сущности
        
        Args:
            image_id: ID изображения
            entity_id: ID сущности
            image_type: Тип изображения
            user_id: ID пользователя, выполняющего привязку
            
        Returns:
            Обновленный объект изображения
            
        Raises:
            HTTPException: При ошибке или отсутствии прав
        """
        image = self.get_image_by_id(image_id)
        
        # Проверяем права на изменение
        if image.owner_id != user_id:
            # TODO: Добавить проверку прав администратора
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для изменения этого изображения"
            )
        
        # Проверяем, что сущность существует (для разных типов сущностей)
        if image_type == ImageType.LISTING:
            entity = self.db.query(Listing).filter(Listing.id == entity_id).first()
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Объявление не найдено"
                )
                
            # Проверка, что пользователь владеет объявлением
            if entity.seller_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав для привязки изображения к этому объявлению"
                )
                
        # TODO: Добавить проверки для других типов сущностей
        
        # Обновляем связь изображения
        image.entity_id = entity_id
        image.type = image_type
        
        # Если это первое изображение, делаем его главным
        existing_images = self.get_entity_images(entity_id, image_type)
        if not existing_images:
            image.is_main = True
        
        self.db.commit()
        self.db.refresh(image)
        
        return image 