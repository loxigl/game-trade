"""
Роутер для управления изображениями
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Path, Query, Form, Body, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_active_user
from ..models.core import User, ImageType, ImageStatus
from ..services.image_service import ImageService
from ..schemas.marketplace import ImageResponse, ImageUpdate
from ..schemas.base import SuccessResponse

router = APIRouter(
    prefix="/images",
    tags=["images"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.post("", response_model=SuccessResponse[ImageResponse], status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    image_type: ImageType = Form(...),
    entity_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Загрузка нового изображения
    """
    image_service = ImageService(db)
    image = await image_service.save_image(
        file=file,
        user_id=current_user.id,
        image_type=image_type,
        entity_id=entity_id
    )
    
    return SuccessResponse(
        data=image,
        meta={"message": "Изображение успешно загружено"}
    )


@router.get("/{image_id}", response_model=SuccessResponse[ImageResponse])
async def get_image_info(
    image_id: int = Path(..., description="ID изображения"),
    db: Session = Depends(get_db)
):
    """
    Получение информации об изображении по его ID
    """
    image_service = ImageService(db)
    image = image_service.get_image_by_id(image_id)
    
    return SuccessResponse(data=image)


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: int = Path(..., description="ID изображения"),
    db: Session = Depends(get_db)
):
    """
    Получение файла изображения
    """
    image_service = ImageService(db)
    image = image_service.get_image_by_id(image_id)
    
    if image.status == ImageStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Изображение удалено"
        )
    
    if not os.path.exists(image.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл изображения не найден на сервере"
        )
    
    return FileResponse(
        image.file_path,
        media_type=image.content_type,
        filename=image.original_filename
    )


@router.get("/entity/{entity_id}", response_model=SuccessResponse[List[ImageResponse]])
async def get_entity_images(
    entity_id: int = Path(..., description="ID сущности"),
    image_type: ImageType = Query(..., description="Тип изображения"),
    db: Session = Depends(get_db)
):
    """
    Получение всех изображений, связанных с определенной сущностью
    """
    image_service = ImageService(db)
    images = image_service.get_entity_images(entity_id, image_type)
    
    return SuccessResponse(data=images)


@router.get("/user/my", response_model=SuccessResponse[List[ImageResponse]])
async def get_my_images(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение всех изображений текущего пользователя
    """
    image_service = ImageService(db)
    images = image_service.get_user_images(current_user.id)
    
    return SuccessResponse(data=images)


@router.delete("/{image_id}", response_model=SuccessResponse)
async def delete_image(
    image_id: int = Path(..., description="ID изображения"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление изображения
    """
    image_service = ImageService(db)
    image_service.delete_image(image_id, current_user.id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Изображение успешно удалено"}
    )


@router.put("/{image_id}/order", response_model=SuccessResponse[ImageResponse])
async def update_image_order(
    order_index: int = Body(..., embed=True),
    image_id: int = Path(..., description="ID изображения"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление порядка отображения изображения
    """
    image_service = ImageService(db)
    image = image_service.update_image_order(
        image_id=image_id,
        new_order=order_index,
        user_id=current_user.id
    )
    
    return SuccessResponse(
        data=image,
        meta={"message": "Порядок изображения успешно обновлен"}
    )


@router.put("/{image_id}/main", response_model=SuccessResponse[ImageResponse])
async def set_main_image(
    entity_id: int = Body(..., embed=True),
    image_type: ImageType = Body(..., embed=True),
    image_id: int = Path(..., description="ID изображения"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Установка главного изображения для сущности
    """
    image_service = ImageService(db)
    image = image_service.set_main_image(
        entity_id=entity_id,
        image_type=image_type,
        image_id=image_id,
    )
    
    return SuccessResponse(
        data=image,
        meta={"message": "Главное изображение успешно установлено"}
    )


@router.put("/{image_id}/attach", response_model=SuccessResponse[ImageResponse])
async def attach_image_to_entity(
    entity_id: int = Body(..., embed=True),
    image_type: ImageType = Body(..., embed=True),
    image_id: int = Path(..., description="ID изображения"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Привязка существующего изображения к сущности
    """
    image_service = ImageService(db)
    image = image_service.attach_image_to_entity(
        image_id=image_id,
        entity_id=entity_id,
        image_type=image_type,
        user_id=current_user.id
    )
    
    return SuccessResponse(
        data=image,
        meta={"message": "Изображение успешно привязано к сущности"}
    ) 