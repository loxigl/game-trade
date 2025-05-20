import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from src.services.auth_middleware import (
    auth_middleware, get_token_from_request, 
    JWTBearer, require_auth
)
from src.services.roles import Permission

class TestAuthMiddleware:
    """
    Тесты для middleware аутентификации
    """
    
    @patch('src.services.jwt.verify_token')
    async def test_auth_middleware_valid_token(self, mock_verify_token):
        """
        Тест middleware с валидным токеном
        """
        # Настраиваем мок функции верификации
        mock_verify_token.return_value = {
            "sub": "1",
            "username": "testuser",
            "roles": ["user"]
        }
        
        # Создаем мок-объекты запроса и ответа
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer valid_token"}
        
        response = MagicMock(spec=Response)
        
        # Создаем функцию call_next
        async def call_next(_request):
            return response
        
        # Вызываем middleware
        result = await auth_middleware(request, call_next)
        
        # Проверяем, что функция верификации была вызвана
        mock_verify_token.assert_called_once_with("valid_token")
        
        # Проверяем, что middleware вернул правильный ответ
        assert result == response
        
        # Проверяем, что в запрос добавлены данные пользователя
        assert hasattr(request.state, "user")
        assert request.state.user["user_id"] == 1
        assert request.state.user["username"] == "testuser"
        assert request.state.user["roles"] == ["user"]
    
    @patch('src.services.jwt.verify_token')
    async def test_auth_middleware_no_token(self, mock_verify_token):
        """
        Тест middleware без токена
        """
        # Создаем мок-объекты запроса и ответа
        request = MagicMock(spec=Request)
        request.headers = {}  # Нет заголовка Authorization
        
        response = MagicMock(spec=Response)
        
        # Создаем функцию call_next
        async def call_next(_request):
            return response
        
        # Вызываем middleware
        result = await auth_middleware(request, call_next)
        
        # Проверяем, что функция верификации не была вызвана
        mock_verify_token.assert_not_called()
        
        # Проверяем, что middleware пропустил запрос
        assert result == response
        
        # Проверяем, что в запрос не добавлены данные пользователя
        assert not hasattr(request.state, "user")
    
    @patch('src.services.jwt.verify_token')
    async def test_auth_middleware_invalid_token(self, mock_verify_token):
        """
        Тест middleware с невалидным токеном
        """
        # Настраиваем мок функции верификации для вызова исключения
        mock_verify_token.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid token"
        )
        
        # Создаем мок-объекты запроса и ответа
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid_token"}
        
        response = MagicMock(spec=Response)
        
        # Создаем функцию call_next
        async def call_next(_request):
            return response
        
        # Вызываем middleware и проверяем, что запрос пропускается, несмотря на ошибку в токене
        result = await auth_middleware(request, call_next)
        
        # Проверяем, что функция верификации была вызвана
        mock_verify_token.assert_called_once_with("invalid_token")
        
        # Проверяем, что middleware пропустил запрос
        assert result == response
        
        # Проверяем, что в запрос не добавлены данные пользователя
        assert not hasattr(request.state, "user")
    
    def test_get_token_from_request(self):
        """
        Тест извлечения токена из запроса
        """
        # Создаем мок-объект запроса с токеном
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test_token"}
        
        # Извлекаем токен
        token = get_token_from_request(request)
        
        # Проверяем результат
        assert token == "test_token"
    
    def test_get_token_from_request_missing(self):
        """
        Тест извлечения токена из запроса без заголовка
        """
        # Создаем мок-объект запроса без заголовка
        request = MagicMock(spec=Request)
        request.headers = {}
        
        # Извлекаем токен
        token = get_token_from_request(request)
        
        # Проверяем результат
        assert token is None
    
    def test_get_token_from_request_invalid_format(self):
        """
        Тест извлечения токена из запроса с неверным форматом
        """
        # Создаем мок-объект запроса с неверным форматом токена
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "NotBearer test_token"}
        
        # Извлекаем токен
        token = get_token_from_request(request)
        
        # Проверяем результат
        assert token is None
    
    @patch('src.services.jwt.verify_token')
    async def test_jwt_bearer_call(self, mock_verify_token):
        """
        Тест JWTBearer.__call__ с валидным токеном
        """
        # Настраиваем мок функции верификации
        mock_verify_token.return_value = {
            "sub": "1",
            "username": "testuser"
        }
        
        # Создаем экземпляр JWTBearer
        jwt_bearer = JWTBearer()
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        
        # Создаем объект авторизационных данных
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        # Вызываем метод __call__
        result = await jwt_bearer(request, credentials)
        
        # Проверяем результат
        assert result == credentials.credentials
        
        # Проверяем вызов функции верификации
        mock_verify_token.assert_called_once_with("valid_token")
    
    @patch('src.services.jwt.verify_token')
    async def test_jwt_bearer_call_invalid_token(self, mock_verify_token):
        """
        Тест JWTBearer.__call__ с невалидным токеном
        """
        # Настраиваем мок функции верификации для вызова исключения
        mock_verify_token.side_effect = HTTPException(
            status_code=401, 
            detail="Invalid token"
        )
        
        # Создаем экземпляр JWTBearer
        jwt_bearer = JWTBearer()
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        
        # Создаем объект авторизационных данных
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await jwt_bearer(request, credentials)
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)
        
        # Проверяем вызов функции верификации
        mock_verify_token.assert_called_once_with("invalid_token")
    
    def test_jwt_bearer_wrong_scheme(self):
        """
        Тест JWTBearer с неверной схемой аутентификации
        """
        # Создаем экземпляр JWTBearer
        jwt_bearer = JWTBearer()
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        
        # Создаем объект авторизационных данных с неверной схемой
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="some_credentials")
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            asyncio_run(jwt_bearer(request, credentials))
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Invalid authentication scheme" in str(exc_info.value.detail)
    
    @patch('src.services.authorization.authorize_user')
    async def test_require_auth_with_permissions(self, mock_authorize_user):
        """
        Тест декоратора require_auth с требуемыми разрешениями
        """
        # Настраиваем мок функции авторизации
        mock_authorize_user.return_value = {
            "user_id": 1,
            "username": "testuser",
            "roles": ["user", "admin"]
        }
        
        # Создаем декорированную функцию
        @require_auth([Permission.READ_PUBLIC])
        async def protected_endpoint(request: Request):
            return {"message": "Protected data"}
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        # Вызываем защищенную функцию
        result = await protected_endpoint(request, credentials)
        
        # Проверяем результат
        assert result == {"message": "Protected data"}
        
        # Проверяем вызов функции авторизации
        mock_authorize_user.assert_called_once_with(request, credentials, [Permission.READ_PUBLIC])
    
    @patch('src.services.authorization.authorize_user')
    async def test_require_auth_without_permissions(self, mock_authorize_user):
        """
        Тест декоратора require_auth без требуемых разрешений
        """
        # Настраиваем мок функции авторизации
        mock_authorize_user.return_value = {
            "user_id": 1,
            "username": "testuser",
            "roles": ["user"]
        }
        
        # Создаем декорированную функцию без требуемых разрешений
        @require_auth()
        async def protected_endpoint(request: Request):
            return {"message": "Authenticated data"}
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        # Вызываем защищенную функцию
        result = await protected_endpoint(request, credentials)
        
        # Проверяем результат
        assert result == {"message": "Authenticated data"}
        
        # Проверяем вызов функции авторизации с пустым списком разрешений
        mock_authorize_user.assert_called_once_with(request, credentials, [])
    
    @patch('src.services.authorization.authorize_user')
    async def test_require_auth_unauthorized(self, mock_authorize_user):
        """
        Тест декоратора require_auth с ошибкой авторизации
        """
        # Настраиваем мок функции авторизации для вызова исключения
        mock_authorize_user.side_effect = HTTPException(
            status_code=401, 
            detail="Unauthorized"
        )
        
        # Создаем декорированную функцию
        @require_auth([Permission.MANAGE_USERS])
        async def protected_endpoint(request: Request):
            return {"message": "Admin data"}
        
        # Создаем мок-объект запроса
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(request, credentials)
        
        # Проверяем код ошибки и сообщение
        assert exc_info.value.status_code == 401
        assert "Unauthorized" in str(exc_info.value.detail)
        
        # Проверяем вызов функции авторизации
        mock_authorize_user.assert_called_once_with(request, credentials, [Permission.MANAGE_USERS])

# Вспомогательная функция для запуска асинхронных функций в синхронных тестах
def asyncio_run(coroutine):
    """Запускает корутину и возвращает результат"""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coroutine) 