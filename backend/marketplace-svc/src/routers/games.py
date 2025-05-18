"""
Роутер для управления играми
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies.db import get_db
from ..dependencies.auth import get_current_user, get_current_active_user
from ..models.core import User
from ..services.game_service import GameService
from ..schemas.categorization import GameCreate, GameUpdate, GameResponse
from ..schemas.base import PaginationParams, SuccessResponse

router = APIRouter(
    prefix="/games",
    tags=["games"],
    responses={
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Нет прав доступа"},
        404: {"description": "Ресурс не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


@router.get("", response_model=SuccessResponse[List[GameResponse]])
async def get_games(
    pagination: PaginationParams = Depends(),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности игры"),
    sort_by: str = Query("name", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получение списка игр с возможностью фильтрации и пагинации
    """
    game_service = GameService(db)
    result = game_service.get_games(
        pagination=pagination,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return SuccessResponse(
        data=result["items"],
        meta=result["meta"]
    )


@router.get("/{game_id}", response_model=SuccessResponse[GameResponse])
async def get_game(
    game_id: int = Path(..., description="ID игры"),
    db: Session = Depends(get_db)
):
    """
    Получение информации о конкретной игре по её ID
    """
    game_service = GameService(db)
    game = game_service.get_game_by_id(game_id)
    
    return SuccessResponse(data=game)


@router.post("", response_model=SuccessResponse[GameResponse], status_code=status.HTTP_201_CREATED)
async def create_game(
    game_data: GameCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создание новой игры
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    game_service = GameService(db)
    game = game_service.create_game(game_data)
    
    return SuccessResponse(
        data=game,
        meta={"message": "Игра успешно создана"}
    )


@router.put("/{game_id}", response_model=SuccessResponse[GameResponse])
async def update_game(
    game_data: GameUpdate,
    game_id: int = Path(..., description="ID игры"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Обновление информации об игре
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    game_service = GameService(db)
    game = game_service.update_game(game_id, game_data)
    
    return SuccessResponse(
        data=game,
        meta={"message": "Игра успешно обновлена"}
    )


@router.delete("/{game_id}", response_model=SuccessResponse)
async def delete_game(
    game_id: int = Path(..., description="ID игры"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Удаление игры
    
    Требуются права администратора (в будущей реализации)
    """
    # TODO: Добавить проверку прав администратора
    
    game_service = GameService(db)
    game_service.delete_game(game_id)
    
    return SuccessResponse(
        data=None,
        meta={"message": "Игра успешно удалена"}
    ) 