import redis
from ..config.settings import settings

# Создаем соединение с Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis():
    """
    Функция для получения клиента Redis.
    Используется как зависимость в маршрутах FastAPI.
    """
    try:
        # Проверяем соединение
        redis_client.ping()
        return redis_client
    except redis.exceptions.ConnectionError:
        # В случае ошибки соединения можно реализовать
        # логику переподключения или вернуть ошибку
        raise ConnectionError("Не удается подключиться к Redis")

async def set_with_expiry(key: str, value: str, expiry_seconds: int = 3600):
    """
    Сохранение данных в Redis с указанием времени жизни.
    
    Args:
        key: Ключ для хранения
        value: Значение для хранения
        expiry_seconds: Время жизни в секундах (по умолчанию 1 час)
    """
    return redis_client.setex(key, expiry_seconds, value)

async def get_value(key: str):
    """
    Получение данных из Redis по ключу.
    
    Args:
        key: Ключ для получения данных
        
    Returns:
        Значение или None, если ключ не найден
    """
    return redis_client.get(key)

async def delete_key(key: str):
    """
    Удаление данных из Redis по ключу.
    
    Args:
        key: Ключ для удаления
        
    Returns:
        Количество удаленных ключей (0 или 1)
    """
    return redis_client.delete(key) 