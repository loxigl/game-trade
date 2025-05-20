import pytest
from src.services.password import hash_password, verify_password, validate_password_strength

class TestPasswordService:
    """
    Тесты для сервиса работы с паролями
    """
    
    def test_hash_password(self):
        """
        Тест хеширования пароля
        """
        # Проверяем, что хеширование возвращает строку
        password = "testPassword123!"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        
        # Проверяем, что хеш не совпадает с паролем
        assert hashed != password
        
        # Проверяем, что хеши для одного и того же пароля отличаются (из-за соли)
        hashed2 = hash_password(password)
        assert hashed != hashed2
    
    def test_verify_password(self):
        """
        Тест верификации пароля
        """
        password = "testPassword123!"
        hashed = hash_password(password)
        
        # Проверяем, что верный пароль подтверждается
        assert verify_password(password, hashed) is True
        
        # Проверяем, что неверный пароль не подтверждается
        assert verify_password("wrongPassword", hashed) is False
        assert verify_password("TestPassword123!", hashed) is False  # Регистр имеет значение
    
    def test_validate_password_strength(self):
        """
        Тест валидации сложности пароля
        """
        # Проверяем валидный пароль
        is_valid, _ = validate_password_strength("StrongP@ssw0rd")
        assert is_valid is True
        
        # Проверяем пароль без заглавных букв
        is_valid, error = validate_password_strength("weakpassw0rd!")
        assert is_valid is False
        assert "заглавную букву" in error
        
        # Проверяем пароль без строчных букв
        is_valid, error = validate_password_strength("WEAKPASSW0RD!")
        assert is_valid is False
        assert "строчную букву" in error
        
        # Проверяем пароль без цифр
        is_valid, error = validate_password_strength("WeakPassword!")
        assert is_valid is False
        assert "цифру" in error
        
        # Проверяем пароль без специальных символов
        is_valid, error = validate_password_strength("WeakPassword123")
        assert is_valid is False
        assert "специальный символ" in error
        
        # Проверяем короткий пароль
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "не менее" in error 