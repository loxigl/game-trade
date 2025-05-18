"""
Сервис для ограничения частоты запросов (rate limiting)
"""
from fastapi import Request, HTTPException, status
from redis import Redis
from datetime import datetime, timedelta
import time
from ..config.settings import settings

# Инициализация Redis для хранения информации о запросах
redis_client = Redis.from_url(settings.REDIS_URL)

class RateLimiter:
    """
    Класс для ограничения частоты запросов
    """
    def __init__(self, times: int = 5, seconds: int = 60):
        """
        Инициализация лимитера
        
        Args:
            times: Максимальное количество запросов
            seconds: Период времени в секундах
        """
        self.times = times
        self.seconds = seconds
    
    async def __call__(self, request: Request):
        """
        Проверка ограничения запросов
        
        Args:
            request: Запрос FastAPI
            
        Raises:
            HTTPException: Если превышен лимит запросов
        """
        # Получаем IP-адрес клиента
        ip = request.client.host
        
        # Формируем ключ для Redis
        key = f"rate_limit:{ip}:{request.url.path}"
        
        # Получаем текущее время
        current_time = time.time()
        
        # Получаем список запросов для данного ключа
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, current_time - self.seconds)
        pipe.zrange(key, 0, -1)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, self.seconds)
        result = pipe.execute()
        
        # Получаем запросы из результата выполнения
        requests_count = len(result[1])
        
        # Проверяем, не превышен ли лимит
        if requests_count >= self.times:
            retry_after = int(self.seconds - (current_time - float(result[1][0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много запросов. Повторите попытку через {retry_after} секунд.",
                headers={"Retry-After": str(retry_after)}
            )

# Функция для создания зависимости с настраиваемыми лимитами
def rate_limit(times: int = 5, seconds: int = 60):
    """
    Создает зависимость для ограничения частоты запросов
    
    Args:
        times: Максимальное количество запросов
        seconds: Период времени в секундах
        
    Returns:
        Зависимость RateLimiter
    """
    return RateLimiter(times, seconds) 