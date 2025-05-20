import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, Request, Response
from src.services.rate_limiter import (
    RateLimiter, TokenBucket, RateLimitExceeded, 
    get_client_ip, rate_limit_middleware
)

class TestTokenBucket:
    """
    Тесты для алгоритма Token Bucket
    """
    
    def test_token_bucket_init(self):
        """
        Тест инициализации Token Bucket
        """
        # Создаем экземпляр с лимитом 10 запросов в секунду
        bucket = TokenBucket(max_tokens=10, refill_rate=10)
        
        assert bucket.max_tokens == 10
        assert bucket.refill_rate == 10
        assert bucket.tokens == 10  # Должен быть заполнен в начале
        assert bucket.last_refill > 0  # Должно быть текущее время в секундах
    
    def test_token_bucket_consume(self):
        """
        Тест потребления токенов
        """
        # Создаем экземпляр
        bucket = TokenBucket(max_tokens=5, refill_rate=5)
        
        # Потребляем токены
        assert bucket.consume(1) is True  # Должно быть успешно
        assert bucket.tokens == 4  # Осталось 4 токена
        
        assert bucket.consume(4) is True  # Потребляем все оставшиеся токены
        assert bucket.tokens == 0  # Не осталось токенов
        
        assert bucket.consume(1) is False  # Не хватает токенов
        assert bucket.tokens == 0  # Токены не изменились
    
    def test_token_bucket_refill(self):
        """
        Тест восполнения токенов
        """
        # Создаем экземпляр
        bucket = TokenBucket(max_tokens=10, refill_rate=10)
        
        # Потребляем токены
        bucket.consume(5)
        assert bucket.tokens == 5
        
        # Устанавливаем время последнего восполнения на 1 секунду назад
        bucket.last_refill = time.time() - 1
        
        # Вызываем восполнение (должно добавить 10 токенов за 1 секунду, но не больше max_tokens)
        bucket._refill()
        assert bucket.tokens == 10
        
        # Проверяем, что время последнего восполнения обновилось
        assert abs(bucket.last_refill - time.time()) < 0.1
    
    def test_token_bucket_partial_refill(self):
        """
        Тест частичного восполнения токенов
        """
        # Создаем экземпляр
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        
        # Потребляем все токены
        bucket.consume(100)
        assert bucket.tokens == 0
        
        # Устанавливаем время последнего восполнения на 0.5 секунды назад
        bucket.last_refill = time.time() - 0.5
        
        # Вызываем восполнение (должно добавить 5 токенов за 0.5 секунды)
        bucket._refill()
        assert bucket.tokens == 5
    
    def test_token_bucket_no_refill_too_soon(self):
        """
        Тест отсутствия восполнения, если прошло слишком мало времени
        """
        # Создаем экземпляр
        bucket = TokenBucket(max_tokens=10, refill_rate=10)
        
        # Потребляем токены
        bucket.consume(5)
        tokens_before = bucket.tokens
        
        # Устанавливаем время последнего восполнения на текущее
        bucket.last_refill = time.time()
        
        # Вызываем восполнение (не должно ничего добавить)
        bucket._refill()
        assert bucket.tokens == tokens_before

class TestRateLimiter:
    """
    Тесты для сервиса ограничения частоты запросов
    """
    
    @patch('src.services.rate_limiter.redis_client')
    def test_rate_limiter_init(self, mock_redis):
        """
        Тест инициализации RateLimiter
        """
        limiter = RateLimiter(
            key_prefix="test",
            max_requests=100,
            period=60,
            block_time=300
        )
        
        assert limiter.key_prefix == "test"
        assert limiter.max_requests == 100
        assert limiter.period == 60
        assert limiter.block_time == 300
    
    @patch('src.services.rate_limiter.redis_client')
    async def test_rate_limiter_check_limit_first_request(self, mock_redis):
        """
        Тест проверки лимита для первого запроса
        """
        # Настраиваем мок Redis
        mock_redis.get.return_value = None
        mock_redis.incr = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        # Создаем лимитер
        limiter = RateLimiter(
            key_prefix="test",
            max_requests=100,
            period=60,
            block_time=300
        )
        
        # Проверяем лимит
        await limiter.check_limit("127.0.0.1")
        
        # Проверяем вызовы Redis
        mock_redis.get.assert_called_once()
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @patch('src.services.rate_limiter.redis_client')
    async def test_rate_limiter_check_limit_under_limit(self, mock_redis):
        """
        Тест проверки лимита для запроса в пределах лимита
        """
        # Настраиваем мок Redis
        mock_redis.get.return_value = b"50"  # Уже было 50 запросов
        mock_redis.incr = AsyncMock()
        
        # Создаем лимитер
        limiter = RateLimiter(
            key_prefix="test",
            max_requests=100,
            period=60,
            block_time=300
        )
        
        # Проверяем лимит
        await limiter.check_limit("127.0.0.1")
        
        # Проверяем вызовы Redis
        mock_redis.get.assert_called_once()
        mock_redis.incr.assert_called_once()
    
    @patch('src.services.rate_limiter.redis_client')
    async def test_rate_limiter_check_limit_exceeded(self, mock_redis):
        """
        Тест проверки лимита при превышении
        """
        # Настраиваем мок Redis
        mock_redis.get.return_value = b"100"  # Уже было 100 запросов (достигнут лимит)
        mock_redis.set = AsyncMock()
        
        # Создаем лимитер
        limiter = RateLimiter(
            key_prefix="test",
            max_requests=100,
            period=60,
            block_time=300
        )
        
        # Проверяем, что вызывается исключение
        with pytest.raises(RateLimitExceeded):
            await limiter.check_limit("127.0.0.1")
        
        # Проверяем вызовы Redis
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()  # Должен быть вызов для блокировки клиента
    
    @patch('src.services.rate_limiter.redis_client')
    async def test_rate_limiter_check_limit_blocked(self, mock_redis):
        """
        Тест проверки лимита для заблокированного клиента
        """
        # Настраиваем мок Redis - клиент заблокирован
        mock_redis.get = AsyncMock(side_effect=[b"blocked", None])
        
        # Создаем лимитер
        limiter = RateLimiter(
            key_prefix="test",
            max_requests=100,
            period=60,
            block_time=300
        )
        
        # Проверяем, что вызывается исключение
        with pytest.raises(RateLimitExceeded):
            await limiter.check_limit("127.0.0.1")
        
        # Проверяем первый вызов Redis на проверку блокировки
        mock_redis.get.assert_called_once()
    
    def test_get_client_ip(self):
        """
        Тест извлечения IP-адреса клиента
        """
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        
        # Настраиваем заголовки для разных сценариев
        
        # 1. X-Forwarded-For заголовок
        request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        ip = get_client_ip(request)
        assert ip == "203.0.113.195"
        
        # 2. X-Real-IP заголовок
        request.headers = {"x-real-ip": "203.0.113.195"}
        ip = get_client_ip(request)
        assert ip == "203.0.113.195"
        
        # 3. Нет заголовков, используем client.host
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        ip = get_client_ip(request)
        assert ip == "127.0.0.1"
    
    @patch('src.services.rate_limiter.RateLimiter.check_limit')
    async def test_rate_limit_middleware(self, mock_check_limit):
        """
        Тест middleware для ограничения частоты запросов
        """
        # Создаем мок-объекты
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        response = MagicMock(spec=Response)
        
        # Настраиваем функцию call_next
        async def call_next(_request):
            return response
        
        # Вызываем middleware
        result = await rate_limit_middleware(request, call_next)
        
        # Проверяем вызов check_limit
        mock_check_limit.assert_called_once_with("127.0.0.1")
        
        # Проверяем результат
        assert result == response
    
    @patch('src.services.rate_limiter.RateLimiter.check_limit')
    async def test_rate_limit_middleware_exceeded(self, mock_check_limit):
        """
        Тест middleware при превышении лимита
        """
        # Настраиваем мок для вызова исключения
        mock_check_limit.side_effect = RateLimitExceeded("Rate limit exceeded")
        
        # Создаем мок-объекты
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        
        # Функция call_next (не должна вызываться)
        async def call_next(_request):
            pytest.fail("call_next не должен вызываться при превышении лимита")
        
        # Проверяем, что вызывается HTTP исключение
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_middleware(request, call_next)
        
        # Проверяем код статуса и сообщение
        assert exc_info.value.status_code == 429
        assert "Too Many Requests" in str(exc_info.value.detail) 