import pytest
from fastapi import status
from unittest.mock import patch

class TestAccountAPI:
    """
    Тесты для API управления аккаунтом пользователя
    """
    
    def test_get_current_account(self, client, user_token, test_user):
        """
        Тест получения данных текущего пользователя
        """
        # Отправляем запрос на получение данных пользователя
        response = client.get(
            "/account/me",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["is_active"] == test_user.is_active
        assert data["is_verified"] == test_user.is_verified
        assert data["roles"] == test_user.roles
    
    def test_get_current_account_unauthorized(self, client):
        """
        Тест получения данных пользователя без авторизации
        """
        # Отправляем запрос без токена
        response = client.get("/account/me")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
    
    def test_update_account(self, client, user_token, test_db, test_user):
        """
        Тест обновления данных пользователя
        """
        # Данные для обновления
        update_data = {
            "username": "updated_user",
            "email": "updated@example.com"
        }
        
        # Отправляем запрос на обновление данных
        response = client.patch(
            "/account/me",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["email"] == update_data["email"]
        assert data["id"] == test_user.id
        
        # Проверяем, что данные обновлены в БД
        test_db.refresh(test_user)
        assert test_user.username == update_data["username"]
        assert test_user.email == update_data["email"]
        assert test_user.is_verified is False  # Email изменен, верификация сброшена
    
    def test_update_account_password(self, client, user_token, test_db, test_user):
        """
        Тест обновления пароля пользователя
        """
        # Данные для обновления
        update_data = {
            "password": "NewPassword123!"
        }
        
        # Отправляем запрос на обновление пароля
        response = client.patch(
            "/account/me",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что пароль обновлен в БД
        from src.services.password import verify_password
        test_db.refresh(test_user)
        assert verify_password("NewPassword123!", test_user.hashed_password) is True
        assert verify_password("password123", test_user.hashed_password) is False
    
    def test_update_account_weak_password(self, client, user_token):
        """
        Тест обновления пароля со слабым паролем
        """
        # Данные для обновления со слабым паролем
        update_data = {
            "password": "weak"
        }
        
        # Отправляем запрос на обновление пароля
        response = client.patch(
            "/account/me",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        # Проверяем на наличие частичного сообщения - точный текст может варьироваться
        assert "пароль" in data["detail"].lower()
    
    def test_delete_account(self, client, user_token, test_db, test_user):
        """
        Тест удаления аккаунта пользователя
        """
        # Отправляем запрос на удаление аккаунта
        response = client.delete(
            "/account/me",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Проверяем, что пользователь удален из БД
        user = test_db.query(User).filter(User.id == test_user.id).first()
        assert user is None
    
    def test_get_user_roles(self, client, user_token, test_user):
        """
        Тест получения списка ролей пользователя
        """
        # Отправляем запрос на получение ролей
        response = client.get(
            "/account/roles",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert set(data) == set(test_user.roles)
    
    def test_change_password(self, client, user_token, test_db, test_user):
        """
        Тест изменения пароля пользователя
        """
        # Данные для запроса
        password_data = {
            "current_password": "password123",
            "new_password": "NewPassword123!"
        }
        
        # Отправляем запрос на изменение пароля
        response = client.post(
            "/account/change-password",
            json=password_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "успешно изменен" in data["message"]
        
        # Проверяем, что пароль изменен в БД
        from src.services.password import verify_password
        test_db.refresh(test_user)
        assert verify_password("NewPassword123!", test_user.hashed_password) is True
        assert verify_password("password123", test_user.hashed_password) is False
    
    def test_change_password_incorrect_current(self, client, user_token):
        """
        Тест изменения пароля с неверным текущим паролем
        """
        # Данные для запроса с неверным текущим паролем
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "NewPassword123!"
        }
        
        # Отправляем запрос на изменение пароля
        response = client.post(
            "/account/change-password",
            json=password_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Неверный текущий пароль" in data["detail"]
    
    def test_change_password_weak_new(self, client, user_token):
        """
        Тест изменения пароля со слабым новым паролем
        """
        # Данные для запроса со слабым новым паролем
        password_data = {
            "current_password": "password123",
            "new_password": "weak"
        }
        
        # Отправляем запрос на изменение пароля
        response = client.post(
            "/account/change-password",
            json=password_data,
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        # Проверяем на наличие частичного сообщения - точный текст может варьироваться
        assert "пароль" in data["detail"].lower()
    
    def test_get_current_user_permissions(self, client, user_token):
        """
        Тест получения информации о разрешениях пользователя
        """
        # Отправляем запрос на получение разрешений
        response = client.get(
            "/account/permissions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "roles" in data
        assert "permissions" in data
        assert "is_admin" in data
        assert "is_moderator" in data
        assert "is_seller" in data
        assert "highest_role" in data
    
    def test_get_current_user_ui_permissions(self, client, user_token):
        """
        Тест получения информации о разрешениях для UI
        """
        # Отправляем запрос на получение разрешений для UI
        response = client.get(
            "/account/ui-permissions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "canViewProfile" in data
        assert "canEditProfile" in data
        # Другие разрешения UI зависят от ролей пользователя
        
from src.models.user import User 