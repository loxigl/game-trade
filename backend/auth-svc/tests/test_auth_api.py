import pytest
from fastapi import status
from unittest.mock import patch
from src.services.jwt import decode_token

class TestAuthAPI:
    """
    Тесты для API аутентификации
    """
    
    def test_login_success(self, client, test_user):
        """
        Тест успешного входа пользователя
        """
        # Данные для запроса
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        # Отправляем запрос на вход
        response = client.post("/login", json=login_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Проверяем токены
        with patch('src.services.jwt.is_token_blacklisted', return_value=False):
            payload = decode_token(data["access_token"])
            assert payload["sub"] == str(test_user.id)
            assert payload["username"] == test_user.username
    
    def test_login_invalid_credentials(self, client, test_user):
        """
        Тест входа с неверными данными
        """
        # Данные для запроса с неверным паролем
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        # Отправляем запрос на вход
        response = client.post("/login", json=login_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Неверное имя пользователя или пароль" in data["detail"]
    
    def test_login_nonexistent_user(self, client):
        """
        Тест входа с несуществующим пользователем
        """
        # Данные для запроса с несуществующим пользователем
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        # Отправляем запрос на вход
        response = client.post("/login", json=login_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Неверное имя пользователя или пароль" in data["detail"]
    
    def test_refresh_token(self, client, user_token):
        """
        Тест обновления токена
        """
        # Данные для запроса
        refresh_data = {
            "refresh_token": user_token["refresh_token"]
        }
        
        # Отправляем запрос на обновление токена
        with patch('src.services.jwt.verify_token') as mock_verify:
            with patch('src.services.jwt.blacklist_token') as mock_blacklist:
                # Настраиваем мок
                mock_verify.return_value = {
                    "sub": "1",
                    "username": "testuser",
                    "jti": "test-jti",
                    "exp": 1999999999
                }
                
                response = client.post("/refresh", json=refresh_data)
                
                # Проверяем ответ
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
    
    def test_refresh_token_missing(self, client):
        """
        Тест обновления токена без предоставления токена
        """
        # Данные для запроса без refresh токена
        refresh_data = {}
        
        # Отправляем запрос на обновление токена
        response = client.post("/refresh", json=refresh_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "Отсутствует refresh токен" in data["detail"]
    
    def test_refresh_token_invalid(self, client):
        """
        Тест обновления токена с невалидным токеном
        """
        # Данные для запроса с невалидным refresh токеном
        refresh_data = {
            "refresh_token": "invalid.token.string"
        }
        
        # Отправляем запрос на обновление токена
        response = client.post("/refresh", json=refresh_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Недействительный refresh токен" in data["detail"]
    
    def test_logout(self, client, user_token):
        """
        Тест выхода из системы
        """
        # Данные для запроса
        logout_data = {
            "access_token": user_token["access_token"],
            "refresh_token": user_token["refresh_token"]
        }
        
        # Мокаем функцию jwt.decode и blacklist_token
        with patch('jose.jwt.decode') as mock_decode:
            with patch('src.routes.auth.blacklist_token') as mock_blacklist:
                # Настраиваем мок
                mock_decode.return_value = {
                    "jti": "test-jti",
                    "exp": 1999999999
                }
                
                # Отправляем запрос на выход
                response = client.post("/logout", json=logout_data)
                
                # Проверяем ответ
                assert response.status_code == status.HTTP_204_NO_CONTENT
                assert response.content == b''  # Пустой ответ
    
    def test_validate_token_valid(self, client, user_token):
        """
        Тест валидации токена (валидный токен)
        """
        # Данные для запроса
        validate_data = {
            "token": user_token["access_token"]
        }
        
        # Отправляем запрос на валидацию токена
        with patch('src.routes.auth.decode_token') as mock_decode:
            # Настраиваем мок
            mock_decode.return_value = {
                "sub": "1",
                "username": "testuser"
            }
            
            response = client.post("/validate", json=validate_data)
            
            # Проверяем ответ
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert data["user_id"] == 1
            assert data["username"] == "testuser"
    
    def test_validate_token_invalid(self, client):
        """
        Тест валидации токена (невалидный токен)
        """
        # Данные для запроса с невалидным токеном
        validate_data = {
            "token": "invalid.token.string"
        }
        
        # Отправляем запрос на валидацию токена
        response = client.post("/validate", json=validate_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is False
        assert data["user_id"] is None
        assert data["username"] is None
    
    def test_health_check(self, client):
        """
        Тест проверки состояния сервиса
        """
        response = client.get("/health")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth"
        assert "timestamp" in data
        assert data["database"] == "connected" 