import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from src.services.authorization import (
    has_required_permissions, authorize_user, 
    verify_user_permissions, get_user_permissions
)
from src.services.roles import Role, Permission

class TestAuthorizationService:
    """
    Тесты для сервиса авторизации
    """
    
    def test_has_required_permissions(self):
        """
        Тест проверки на наличие необходимых разрешений
        """
        # Пользователь с разрешениями
        user_permissions = [
            Permission.READ_PUBLIC,
            Permission.EDIT_OWN_CONTENT,
            Permission.MANAGE_ORDERS
        ]
        
        # Проверка на одно разрешение
        assert has_required_permissions(user_permissions, [Permission.READ_PUBLIC]) is True
        
        # Проверка на несколько разрешений
        assert has_required_permissions(
            user_permissions, 
            [Permission.READ_PUBLIC, Permission.EDIT_OWN_CONTENT]
        ) is True
        
        # Проверка на отсутствующее разрешение
        assert has_required_permissions(user_permissions, [Permission.MANAGE_USERS]) is False
        
        # Проверка с пустым списком требуемых разрешений
        assert has_required_permissions(user_permissions, []) is True
        
        # Проверка с пустым списком разрешений пользователя
        assert has_required_permissions([], [Permission.READ_PUBLIC]) is False
    
    @patch('src.services.authorization.get_user_by_id')
    def test_get_user_permissions(self, mock_get_user):
        """
        Тест получения разрешений пользователя
        """
        # Создаем мок-объект пользователя
        mock_user = MagicMock()
        mock_user.roles = ["user", "seller"]
        mock_get_user.return_value = mock_user
        
        # Получаем разрешения
        permissions = get_user_permissions(1)
        
        # Проверяем, что функция get_user_by_id была вызвана
        mock_get_user.assert_called_once_with(1)
        
        # Проверяем, что у пользователя есть базовые разрешения из ролей user и seller
        assert Permission.READ_PUBLIC in permissions
        assert Permission.EDIT_OWN_CONTENT in permissions
        
        # Проверяем, что у обычного пользователя нет админских разрешений
        assert Permission.MANAGE_USERS not in permissions
        assert Permission.MANAGE_SYSTEM not in permissions
    
    @patch('src.services.authorization.get_user_by_id')
    def test_get_user_permissions_nonexistent_user(self, mock_get_user):
        """
        Тест получения разрешений несуществующего пользователя
        """
        # Возвращаем None для имитации отсутствия пользователя
        mock_get_user.return_value = None
        
        # Проверяем, что функция возвращает пустой список
        permissions = get_user_permissions(999)
        assert permissions == []
        
        # Проверяем, что функция get_user_by_id была вызвана
        mock_get_user.assert_called_once_with(999)
    
    @patch('src.services.authorization.get_user_permissions')
    def test_verify_user_permissions(self, mock_get_permissions):
        """
        Тест верификации разрешений пользователя
        """
        # Настраиваем мок-объект для возврата списка разрешений
        mock_get_permissions.return_value = [
            Permission.READ_PUBLIC,
            Permission.EDIT_OWN_CONTENT
        ]
        
        # Проверяем верификацию с валидными разрешениями
        assert verify_user_permissions(1, [Permission.READ_PUBLIC]) is True
        
        # Проверяем верификацию с несколькими требуемыми разрешениями
        assert verify_user_permissions(
            1, 
            [Permission.READ_PUBLIC, Permission.EDIT_OWN_CONTENT]
        ) is True
        
        # Проверяем верификацию с отсутствующим разрешением
        assert verify_user_permissions(1, [Permission.MANAGE_USERS]) is False
        
        # Проверяем, что функция get_user_permissions была вызвана
        mock_get_permissions.assert_called_with(1)
    
    @patch('src.services.jwt.decode_token')
    @patch('src.services.authorization.verify_user_permissions')
    async def test_authorize_user(self, mock_verify_permissions, mock_decode_token):
        """
        Тест авторизации пользователя на основе JWT токена
        """
        # Настраиваем мок-объекты
        mock_decode_token.return_value = {"sub": "1", "username": "testuser"}
        mock_verify_permissions.return_value = True
        
        # Создаем mock для запроса и авторизационных данных
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_token")
        
        # Вызываем функцию авторизации
        user_data = await authorize_user(request, credentials, [Permission.READ_PUBLIC])
        
        # Проверяем, что функции были вызваны
        mock_decode_token.assert_called_once_with("fake_token")
        mock_verify_permissions.assert_called_once_with(1, [Permission.READ_PUBLIC])
        
        # Проверяем результат
        assert user_data["user_id"] == 1
        assert user_data["username"] == "testuser"
    
    @patch('src.services.jwt.decode_token')
    @patch('src.services.authorization.verify_user_permissions')
    async def test_authorize_user_insufficient_permissions(self, mock_verify_permissions, mock_decode_token):
        """
        Тест авторизации пользователя с недостаточными разрешениями
        """
        # Настраиваем мок-объекты
        mock_decode_token.return_value = {"sub": "1", "username": "testuser"}
        mock_verify_permissions.return_value = False
        
        # Создаем mock для запроса и авторизационных данных
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_token")
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await authorize_user(request, credentials, [Permission.MANAGE_SYSTEM])
        
        # Проверяем, что функции были вызваны
        mock_decode_token.assert_called_once_with("fake_token")
        mock_verify_permissions.assert_called_once_with(1, [Permission.MANAGE_SYSTEM])
        
        # Проверяем код статуса исключения
        assert exc_info.value.status_code == 403
    
    @patch('src.services.jwt.decode_token')
    async def test_authorize_user_invalid_token(self, mock_decode_token):
        """
        Тест авторизации пользователя с невалидным токеном
        """
        # Настраиваем мок-объект для имитации невалидного токена
        mock_decode_token.side_effect = HTTPException(status_code=401, detail="Invalid token")
        
        # Создаем mock для запроса и авторизационных данных
        request = MagicMock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await authorize_user(request, credentials, [Permission.READ_PUBLIC])
        
        # Проверяем, что функция decode_token была вызвана
        mock_decode_token.assert_called_once_with("invalid_token")
        
        # Проверяем код статуса исключения
        assert exc_info.value.status_code == 401 