"""
Сервис для работы с играми
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func

from ..models.categorization import Game
from ..schemas.categorization import GameCreate, GameUpdate
from ..schemas.base import PaginationParams

class GameService:
    """Сервис для управления играми"""
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
    
    def get_games(
        self, 
        pagination: PaginationParams,
        is_active: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Получение списка игр с фильтрацией и пагинацией
        
        Args:
            pagination: Параметры пагинации
            is_active: Фильтр по активности игры
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            
        Returns:
            Dict с играми и метаданными пагинации
        """
        query = self.db.query(Game)
        
        # Применяем фильтры
        if is_active is not None:
            query = query.filter(Game.is_active == is_active)
        
        # Подсчет общего количества
        total = query.count()
        
        # Применяем сортировку
        if hasattr(Game, sort_by):
            if sort_order.lower() == "asc":
                query = query.order_by(asc(getattr(Game, sort_by)))
            else:
                query = query.order_by(desc(getattr(Game, sort_by)))
        
        # Применяем пагинацию
        query = query.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        
        # Получаем результаты
        games = query.all()
        
        return {
            "items": games,
            "meta": {
                "total": total,
                "page": pagination.page,
                "limit": pagination.limit,
                "pages": (total + pagination.limit - 1) // pagination.limit
            }
        }
    
    def get_game_by_id(self, game_id: int) -> Game:
        """
        Получение игры по ID
        
        Args:
            game_id: ID игры
            
        Returns:
            Объект игры
            
        Raises:
            HTTPException: Если игра не найдена
        """
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Игра не найдена"
            )
        return game
    
    def create_game(self, game_data: GameCreate) -> Game:
        """
        Создание новой игры
        
        Args:
            game_data: Данные для создания игры
            
        Returns:
            Созданная игра
            
        Raises:
            HTTPException: Если игра с таким именем уже существует
        """
        # Проверяем, что игра с таким именем не существует
        existing_game = self.db.query(Game).filter(
            func.lower(Game.name) == func.lower(game_data.name)
        ).first()
        
        if existing_game:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Игра с таким именем уже существует"
            )
        
        # Создаем объект игры
        game = Game(
            name=game_data.name,
            description=game_data.description,
            logo_url=game_data.logo_url,
            is_active=game_data.is_active if game_data.is_active is not None else True
        )
        
        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)
        
        return game
    
    def update_game(self, game_id: int, game_data: GameUpdate) -> Game:
        """
        Обновление существующей игры
        
        Args:
            game_id: ID игры для обновления
            game_data: Новые данные игры
            
        Returns:
            Обновленная игра
            
        Raises:
            HTTPException: Если игра не найдена или новое имя уже занято
        """
        game = self.get_game_by_id(game_id)
        
        # Если изменяется имя, проверяем, что новое имя не занято
        if game_data.name is not None and game_data.name != game.name:
            existing_game = self.db.query(Game).filter(
                func.lower(Game.name) == func.lower(game_data.name),
                Game.id != game_id
            ).first()
            
            if existing_game:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Игра с таким именем уже существует"
                )
            
            game.name = game_data.name
        
        # Обновляем остальные поля, если они указаны
        if game_data.description is not None:
            game.description = game_data.description
        if game_data.logo_url is not None:
            game.logo_url = game_data.logo_url
        if game_data.is_active is not None:
            game.is_active = game_data.is_active
        
        self.db.commit()
        self.db.refresh(game)
        
        return game
    
    def delete_game(self, game_id: int) -> bool:
        """
        Удаление игры
        
        Args:
            game_id: ID игры для удаления
            
        Returns:
            True, если игра успешно удалена
            
        Raises:
            HTTPException: Если игра не найдена
        """
        game = self.get_game_by_id(game_id)
        
        self.db.delete(game)
        self.db.commit()
        
        return True 