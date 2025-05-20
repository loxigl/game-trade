import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
import httpx
from httpx import Response, Request
import json

from src.services.client_auth import (
    ClientAuth, validate_client_credentials, 
    generate_client_auth_token, verify_client_auth_token
)
from src.config.settings import settings

class TestClientAuth:
    """
    Тесты для сервиса клиентской аутентификации
    """
    
    def test_client_auth_init(self):
        """
        Тест инициализации клиентского аутентификатора
        """
        # Создаем экземпляр
        auth = ClientAuth(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Проверяем атрибуты
        assert auth.client_id == "test_client"
        assert auth.client_secret == "test_secret"
    
    @patch('httpx.AsyncClient.post')
    async def test_client_auth_authenticate(self, mock_post):
        """
        Тест аутентификации клиента
        """
        # Настраиваем мок-ответ
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        # Создаем экземпляр
        auth = ClientAuth(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Вызываем аутентификацию
        token = await auth.authenticate("https://api.example.com/token")
        
        # Проверяем результат
        assert token == "test_token"
        
        # Проверяем вызов post
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Проверяем URL и данные
        assert args[0] == "https://api.example.com/token"
        assert "client_id" in kwargs["data"]
        assert "client_secret" in kwargs["data"]
        assert kwargs["data"]["client_id"] == "test_client"
        assert kwargs["data"]["client_secret"] == "test_secret"
        assert kwargs["data"]["grant_type"] == "client_credentials"
    
    @patch('httpx.AsyncClient.post')
    async def test_client_auth_authenticate_error(self, mock_post):
        """
        Тест обработки ошибок при аутентификации клиента
        """
        # Настраиваем мок-ответ с ошибкой
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Client authentication failed"
        }
        mock_post.return_value = mock_response
        
        # Создаем экземпляр
        auth = ClientAuth(
            client_id="invalid_client",
            client_secret="invalid_secret"
        )
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await auth.authenticate("https://api.example.com/token")
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Client authentication failed" in str(exc_info.value.detail)
    
    @patch('httpx.AsyncClient.post')
    async def test_client_auth_authenticate_network_error(self, mock_post):
        """
        Тест обработки сетевых ошибок при аутентификации клиента
        """
        # Настраиваем мок для вызова сетевой ошибки
        mock_post.side_effect = httpx.RequestError("Connection error")
        
        # Создаем экземпляр
        auth = ClientAuth(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await auth.authenticate("https://api.example.com/token")
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 500
        assert "Connection error" in str(exc_info.value.detail)
    
    @patch('src.services.client_auth.verify_client_auth_token')
    async def test_validate_client_credentials(self, mock_verify):
        """
        Тест валидации клиентских учетных данных
        """
        # Настраиваем мок функции верификации
        mock_verify.return_value = {"client_id": "valid_client", "scope": "api"}
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer valid_token"}
        
        # Вызываем функцию валидации
        client_data = await validate_client_credentials(request)
        
        # Проверяем результат
        assert client_data == {"client_id": "valid_client", "scope": "api"}
        
        # Проверяем вызов функции верификации
        mock_verify.assert_called_once_with("valid_token")
    
    @patch('src.services.client_auth.verify_client_auth_token')
    async def test_validate_client_credentials_no_token(self, mock_verify):
        """
        Тест валидации без токена аутентификации
        """
        # Создаем мок-объект запроса без заголовка авторизации
        request = MagicMock(spec=Request)
        request.headers = {}
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await validate_client_credentials(request)
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in str(exc_info.value.detail)
        
        # Проверяем, что функция верификации не вызывалась
        mock_verify.assert_not_called()
    
    @patch('src.services.client_auth.verify_client_auth_token')
    async def test_validate_client_credentials_invalid_token(self, mock_verify):
        """
        Тест валидации с невалидным токеном
        """
        # Настраиваем мок функции верификации для вызова исключения
        mock_verify.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid authentication token"
        )
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid_token"}
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await validate_client_credentials(request)
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in str(exc_info.value.detail)
        
        # Проверяем вызов функции верификации
        mock_verify.assert_called_once_with("invalid_token")
    
    @patch('src.services.jwt.create_access_token')
    def test_generate_client_auth_token(self, mock_create_token):
        """
        Тест генерации токена клиентской аутентификации
        """
        # Настраиваем мок функции создания токена
        mock_create_token.return_value = "generated_token"
        
        # Данные для токена
        client_id = "test_client"
        client_secret = "test_secret"
        
        # Вызываем функцию
        token = generate_client_auth_token(client_id, client_secret)
        
        # Проверяем результат
        assert token == "generated_token"
        
        # Проверяем вызов функции создания токена
        mock_create_token.assert_called_once()
        args, kwargs = mock_create_token.call_args
        data = args[0]
        
        # Проверяем данные токена
        assert data["client_id"] == client_id
        assert "exp" in data
        assert "iat" in data
    
    @patch('src.services.jwt.decode_token')
    def test_verify_client_auth_token(self, mock_decode_token):
        """
        Тест верификации токена клиентской аутентификации
        """
        # Настраиваем мок функции декодирования токена
        mock_decode_token.return_value = {
            "client_id": "test_client",
            "scope": "api",
            "exp": 1735689600,  # Срок действия в будущем
            "iat": 1704153600
        }
        
        # Вызываем функцию
        payload = verify_client_auth_token("valid_token")
        
        # Проверяем результат
        assert payload["client_id"] == "test_client"
        assert payload["scope"] == "api"
        
        # Проверяем вызов функции декодирования
        mock_decode_token.assert_called_once_with("valid_token")
    
    @patch('src.services.jwt.decode_token')
    def test_verify_client_auth_token_error(self, mock_decode_token):
        """
        Тест обработки ошибок при верификации токена
        """
        # Настраиваем мок функции декодирования для вызова исключения
        mock_decode_token.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid token"
        )
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            verify_client_auth_token("invalid_token")
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)
        
        # Проверяем вызов функции декодирования
        mock_decode_token.assert_called_once_with("invalid_token") 