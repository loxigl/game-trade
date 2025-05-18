from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from ..models.example import Example
from ..schemas.example import ExampleCreate, ExampleUpdate
from ..core.database import get_async_db

class ExampleService:
    """
    Сервис для работы с примерами.
    
    Реализует бизнес-логику для работы с примерами, включая CRUD операции.
    """
    
    async def get_db(self) -> AsyncSession:
        """
        Получение сессии базы данных.
        
        Возвращает:
            AsyncSession: Асинхронная сессия базы данных.
        """
        async for db in get_async_db():
            return db
    
    async def get_all(self) -> List[Example]:
        """
        Получение всех примеров.
        
        Возвращает:
            List[Example]: Список всех примеров.
        """
        db = await self.get_db()
        result = await db.execute(select(Example))
        return result.scalars().all()
    
    async def get_by_id(self, example_id: int) -> Optional[Example]:
        """
        Получение примера по ID.
        
        Аргументы:
            example_id (int): ID примера для получения.
            
        Возвращает:
            Optional[Example]: Пример, если найден, иначе None.
        """
        db = await self.get_db()
        result = await db.execute(select(Example).filter(Example.id == example_id))
        return result.scalar_one_or_none()
    
    async def create(self, data: ExampleCreate) -> Example:
        """
        Создание нового примера.
        
        Аргументы:
            data (ExampleCreate): Данные для создания примера.
            
        Возвращает:
            Example: Созданный пример.
        """
        db = await self.get_db()
        example = Example(**data.model_dump())
        db.add(example)
        await db.commit()
        await db.refresh(example)
        return example
    
    async def update(self, example_id: int, data: ExampleUpdate) -> Optional[Example]:
        """
        Обновление существующего примера.
        
        Аргументы:
            example_id (int): ID примера для обновления.
            data (ExampleUpdate): Данные для обновления.
            
        Возвращает:
            Optional[Example]: Обновленный пример, если найден, иначе None.
        """
        db = await self.get_db()
        
        # Фильтруем None значения, чтобы не обновлять поля, которые не были указаны
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        
        if not update_data:
            # Если нет данных для обновления, просто возвращаем существующий пример
            return await self.get_by_id(example_id)
        
        # Выполняем обновление
        result = await db.execute(
            update(Example)
            .where(Example.id == example_id)
            .values(**update_data)
            .returning(Example)
        )
        await db.commit()
        
        return result.scalar_one_or_none()
    
    async def delete(self, example_id: int) -> bool:
        """
        Удаление примера.
        
        Аргументы:
            example_id (int): ID примера для удаления.
            
        Возвращает:
            bool: True, если пример был удален, иначе False.
        """
        db = await self.get_db()
        result = await db.execute(
            delete(Example).where(Example.id == example_id)
        )
        await db.commit()
        
        # rowcount сообщает, сколько строк было удалено
        return result.rowcount > 0 