import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

class TestRegisterAPI:
    """
    Тесты для API регистрации пользователей
    """
    
    def test_register_user_success(self, client, test_db):
        """
        Тест успешной регистрации пользователя
        """
        # Данные для запроса
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password123!"
        }
        
        # Отправляем запрос на регистрацию
        response = client.post("/register", json=register_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == register_data["username"]
        assert data["email"] == register_data["email"]
        assert "id" in data
        assert "is_active" in data
        assert "is_verified" in data
        assert data["roles"] == ["user"]
        
        # Проверяем, что пользователь создан в БД
        from src.models.user import User
        user = test_db.query(User).filter(User.email == register_data["email"]).first()
        assert user is not None
        assert user.username == register_data["username"]
        assert user.email == register_data["email"]
        assert user.hashed_password != register_data["password"]  # Пароль должен быть захеширован
    
    def test_register_duplicate_username(self, client, test_user):
        """
        Тест регистрации с существующим именем пользователя
        """
        # Данные для запроса с существующим именем пользователя
        register_data = {
            "username": "testuser",  # Такой пользователь уже существует (из фикстуры)
            "email": "newuser@example.com",
            "password": "Password123!"
        }
        
        # Отправляем запрос на регистрацию
        response = client.post("/register", json=register_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data
        assert "уже существует" in data["detail"]
    
    def test_register_duplicate_email(self, client, test_user):
        """
        Тест регистрации с существующим email
        """
        # Данные для запроса с существующим email
        register_data = {
            "username": "newuser",
            "email": "test@example.com",  # Такой email уже существует (из фикстуры)
            "password": "Password123!"
        }
        
        # Отправляем запрос на регистрацию
        response = client.post("/register", json=register_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data
        assert "уже существует" in data["detail"]
    
    def test_register_weak_password(self, client):
        """
        Тест регистрации со слабым паролем
        """
        # Данные для запроса со слабым паролем
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak"  # Слишком короткий и простой пароль
        }
        
        # Отправляем запрос на регистрацию
        response = client.post("/register", json=register_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        # Проверяем на наличие частичного сообщения - точный текст может варьироваться
        assert "пароль" in data["detail"].lower()
    
    def test_verify_email_success(self, client, test_db):
        """
        Тест успешного подтверждения email
        """
        # Создаем пользователя с неподтвержденным email
        from src.models.user import User
        from src.services.password import hash_password
        from datetime import datetime, timedelta
        
        verification_token = "test-token"
        user = User(
            username="unverified",
            email="unverified@example.com",
            hashed_password=hash_password("password123"),
            is_active=True,
            is_verified=False,
            password_reset_token=verification_token,
            password_reset_expires=datetime.utcnow() + timedelta(hours=1)
        )
        test_db.add(user)
        test_db.commit()
        
        # Отправляем запрос на подтверждение email
        response = client.get(f"/verify-email/{verification_token}")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "успешно подтвержден" in data["message"]
        
        # Проверяем, что пользователь обновлен в БД
        test_db.refresh(user)
        assert user.is_verified is True
        assert user.password_reset_token is None
    
    def test_verify_email_invalid_token(self, client):
        """
        Тест подтверждения email с неверным токеном
        """
        # Отправляем запрос с неверным токеном
        response = client.get("/verify-email/invalid-token")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "недействителен" in data["detail"]
    
    def test_verify_email_expired_token(self, client, test_db):
        """
        Тест подтверждения email с просроченным токеном
        """
        # Создаем пользователя с просроченным токеном
        from src.models.user import User
        from src.services.password import hash_password
        from datetime import datetime, timedelta
        
        verification_token = "expired-token"
        user = User(
            username="expired",
            email="expired@example.com",
            hashed_password=hash_password("password123"),
            is_active=True,
            is_verified=False,
            password_reset_token=verification_token,
            password_reset_expires=datetime.utcnow() - timedelta(hours=1)  # Уже истек
        )
        test_db.add(user)
        test_db.commit()
        
        # Отправляем запрос с просроченным токеном
        response = client.get(f"/verify-email/{verification_token}")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_410_GONE
        data = response.json()
        assert "detail" in data
        assert "истек" in data["detail"]
    
    def test_reset_password_request(self, client, test_user):
        """
        Тест запроса на сброс пароля
        """
        # Данные для запроса
        email_data = {
            "email": "test@example.com"
        }
        
        # Отправляем запрос на сброс пароля
        response = client.post("/reset-password-request", json=email_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "message" in data
        assert "инструкции" in data["message"]
    
    def test_reset_password(self, client, test_db):
        """
        Тест сброса пароля
        """
        # Создаем пользователя с токеном сброса пароля
        from src.models.user import User
        from src.services.password import hash_password, verify_password
        from datetime import datetime, timedelta
        
        reset_token = "reset-token"
        user = User(
            username="reset",
            email="reset@example.com",
            hashed_password=hash_password("oldpassword"),
            is_active=True,
            is_verified=True,
            password_reset_token=reset_token,
            password_reset_expires=datetime.utcnow() + timedelta(hours=1)
        )
        test_db.add(user)
        test_db.commit()
        
        # Данные для запроса
        reset_data = {
            "password": "NewPassword123!"
        }
        
        # Отправляем запрос на сброс пароля
        response = client.post(f"/reset-password/{reset_token}", json=reset_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "успешно изменен" in data["message"]
        
        # Проверяем, что пароль изменен
        test_db.refresh(user)
        assert user.password_reset_token is None
        assert user.password_reset_expires is None
        assert verify_password("NewPassword123!", user.hashed_password) is True
        assert verify_password("oldpassword", user.hashed_password) is False
    
    def test_reset_password_invalid_token(self, client):
        """
        Тест сброса пароля с неверным токеном
        """
        # Данные для запроса
        reset_data = {
            "password": "NewPassword123!"
        }
        
        # Отправляем запрос с неверным токеном
        response = client.post("/reset-password/invalid-token", json=reset_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "недействителен" in data["detail"]
    
    def test_reset_password_expired_token(self, client, test_db):
        """
        Тест сброса пароля с просроченным токеном
        """
        # Создаем пользователя с просроченным токеном сброса пароля
        from src.models.user import User
        from src.services.password import hash_password
        from datetime import datetime, timedelta
        
        reset_token = "expired-reset-token"
        user = User(
            username="expired_reset",
            email="expired_reset@example.com",
            hashed_password=hash_password("oldpassword"),
            is_active=True,
            is_verified=True,
            password_reset_token=reset_token,
            password_reset_expires=datetime.utcnow() - timedelta(hours=1)  # Уже истек
        )
        test_db.add(user)
        test_db.commit()
        
        # Данные для запроса
        reset_data = {
            "password": "NewPassword123!"
        }
        
        # Отправляем запрос с просроченным токеном
        response = client.post(f"/reset-password/{reset_token}", json=reset_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_410_GONE
        data = response.json()
        assert "detail" in data
        assert "истек" in data["detail"]
    
    def test_reset_password_weak_password(self, client, test_db):
        """
        Тест сброса пароля со слабым паролем
        """
        # Создаем пользователя с токеном сброса пароля
        from src.models.user import User
        from src.services.password import hash_password
        from datetime import datetime, timedelta
        
        reset_token = "weak-reset-token"
        user = User(
            username="weak_reset",
            email="weak_reset@example.com",
            hashed_password=hash_password("oldpassword"),
            is_active=True,
            is_verified=True,
            password_reset_token=reset_token,
            password_reset_expires=datetime.utcnow() + timedelta(hours=1)
        )
        test_db.add(user)
        test_db.commit()
        
        # Данные для запроса со слабым паролем
        reset_data = {
            "password": "weak"
        }
        
        # Отправляем запрос со слабым паролем
        response = client.post(f"/reset-password/{reset_token}", json=reset_data)
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        # Проверяем на наличие частичного сообщения - точный текст может варьироваться
        assert "пароль" in data["detail"].lower() 