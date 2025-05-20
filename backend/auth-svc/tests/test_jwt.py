import pytest
import time
from datetime import datetime, timedelta
from jose import jwt, JWTError
from unittest.mock import patch, MagicMock

from src.services.jwt import (
    create_access_token, create_refresh_token, verify_token,
    is_token_blacklisted, blacklist_token, refresh_tokens, decode_token
)
from src.config.settings import settings

class TestJwtService:
    """
    Тесты для сервиса JWT токенов
    """
    
    def test_create_access_token(self):
        """
        Тест создания access токена
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем токен
        token = create_access_token(data)
        
        # Проверяем тип данных
        assert isinstance(token, str)
        
        # Декодируем токен и проверяем данные
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_create_refresh_token(self):
        """
        Тест создания refresh токена
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем токен
        token = create_refresh_token(data)
        
        # Проверяем тип данных
        assert isinstance(token, str)
        
        # Декодируем токен и проверяем данные
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_verify_token_success(self):
        """
        Тест успешной верификации токена
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем токен
        token = create_access_token(data)
        
        # Верифицируем токен
        with patch('src.services.jwt.is_token_blacklisted', return_value=False):
            payload = verify_token(token, token_type="access")
            
            # Проверяем данные в payload
            assert payload["sub"] == "1"
            assert payload["username"] == "testuser"
            assert payload["type"] == "access"
    
    def test_verify_token_invalid(self):
        """
        Тест верификации недействительного токена
        """
        # Создаем невалидный токен
        invalid_token = "invalid.token.string"
        
        # Проверяем, что верификация выбрасывает исключение
        with pytest.raises(JWTError):
            verify_token(invalid_token)
    
    def test_verify_token_type_mismatch(self):
        """
        Тест верификации токена с несоответствующим типом
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем access токен
        token = create_access_token(data)
        
        # Пытаемся верифицировать как refresh токен
        with pytest.raises(JWTError):
            verify_token(token, token_type="refresh")
    
    def test_blacklist_token(self):
        """
        Тест добавления токена в черный список
        """
        # Мокаем Redis клиент
        with patch('src.services.jwt.redis_client') as mock_redis:
            mock_redis.setex.return_value = True
            
            # Добавляем токен в черный список
            token_jti = "test-jti"
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            blacklist_token(token_jti, expires_at)
            
            # Проверяем, что была вызвана функция setex у Redis клиента
            mock_redis.setex.assert_called_once()
            
            # Проверяем аргументы вызова
            call_args = mock_redis.setex.call_args[0]
            assert call_args[0] == f"blacklist:{token_jti}"
            assert isinstance(call_args[1], int)
            assert call_args[2] == 1
    
    def test_is_token_blacklisted(self):
        """
        Тест проверки токена в черном списке
        """
        # Мокаем Redis клиент
        with patch('src.services.jwt.redis_client') as mock_redis:
            # Токен в черном списке
            mock_redis.exists.return_value = 1
            assert is_token_blacklisted("blacklisted-jti") is True
            
            # Токен не в черном списке
            mock_redis.exists.return_value = 0
            assert is_token_blacklisted("valid-jti") is False
    
    def test_refresh_tokens(self):
        """
        Тест обновления токенов
        """
        # Создаем refresh токен
        data = {"sub": "1", "username": "testuser"}
        token = create_refresh_token(data)
        
        # Мокаем функцию verify_token и blacklist_token
        with patch('src.services.jwt.verify_token') as mock_verify:
            with patch('src.services.jwt.blacklist_token') as mock_blacklist:
                # Настраиваем mock verify_token
                mock_verify.return_value = {
                    "sub": "1",
                    "username": "testuser",
                    "jti": "test-jti",
                    "exp": (datetime.utcnow() + timedelta(days=30)).timestamp()
                }
                
                # Получаем новые токены
                new_tokens = refresh_tokens(token)
                
                # Проверяем вызов функций
                mock_verify.assert_called_once_with(token, token_type="refresh")
                mock_blacklist.assert_called_once()
                
                # Проверяем результат
                assert "access_token" in new_tokens
                assert "refresh_token" in new_tokens
                assert isinstance(new_tokens["access_token"], str)
                assert isinstance(new_tokens["refresh_token"], str)
    
    def test_decode_token(self):
        """
        Тест декодирования токена
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем токен
        token = create_access_token(data)
        
        # Мокаем функцию is_token_blacklisted
        with patch('src.services.jwt.is_token_blacklisted', return_value=False):
            # Декодируем токен
            payload = decode_token(token)
            
            # Проверяем данные
            assert payload["sub"] == "1"
            assert payload["username"] == "testuser"
            assert payload["type"] == "access"
    
    def test_decode_token_expired(self):
        """
        Тест декодирования просроченного токена
        """
        # Создаем просроченный токен
        payload = {
            "sub": "1",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "jti": "test-jti",
            "type": "access"
        }
        
        expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        # Проверяем, что декодирование выбрасывает исключение
        with pytest.raises(JWTError):
            decode_token(expired_token)
    
    def test_decode_token_blacklisted(self):
        """
        Тест декодирования токена из черного списка
        """
        # Данные для токена
        data = {"sub": "1", "username": "testuser"}
        
        # Создаем токен
        token = create_access_token(data)
        
        # Мокаем функцию is_token_blacklisted
        with patch('src.services.jwt.is_token_blacklisted', return_value=True):
            # Проверяем, что декодирование выбрасывает исключение
            with pytest.raises(JWTError):
                decode_token(token) 