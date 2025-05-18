from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...schemas.example import ExampleResponse, ExampleCreate, ExampleUpdate
from ...services.example import ExampleService
from ...dependencies.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ExampleResponse])
async def get_examples():
    """
    Получение списка всех примеров.
    
    Возвращает:
        List[ExampleResponse]: Список всех примеров.
    """
    service = ExampleService()
    return await service.get_all()


@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(example_id: int):
    """
    Получение конкретного примера по его ID.
    
    Аргументы:
        example_id (int): ID примера для получения.
        
    Возвращает:
        ExampleResponse: Данные примера.
        
    Raises:
        HTTPException: Если пример не найден.
    """
    service = ExampleService()
    example = await service.get_by_id(example_id)
    
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пример с ID {example_id} не найден"
        )
    
    return example


@router.post("/", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    # Опционально: требуем авторизацию пользователя
    # current_user = Depends(get_current_user)
):
    """
    Создание нового примера.
    
    Аргументы:
        data (ExampleCreate): Данные для создания примера.
        
    Возвращает:
        ExampleResponse: Созданный пример.
    """
    service = ExampleService()
    return await service.create(data)


@router.put("/{example_id}", response_model=ExampleResponse)
async def update_example(
    example_id: int,
    data: ExampleUpdate,
    # Опционально: требуем авторизацию пользователя
    # current_user = Depends(get_current_user)
):
    """
    Обновление существующего примера.
    
    Аргументы:
        example_id (int): ID примера для обновления.
        data (ExampleUpdate): Данные для обновления.
        
    Возвращает:
        ExampleResponse: Обновленный пример.
        
    Raises:
        HTTPException: Если пример не найден.
    """
    service = ExampleService()
    example = await service.update(example_id, data)
    
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пример с ID {example_id} не найден"
        )
    
    return example


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: int,
    # Опционально: требуем авторизацию пользователя
    # current_user = Depends(get_current_user)
):
    """
    Удаление примера.
    
    Аргументы:
        example_id (int): ID примера для удаления.
        
    Raises:
        HTTPException: Если пример не найден.
    """
    service = ExampleService()
    success = await service.delete(example_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пример с ID {example_id} не найден"
        )
    
    return None 