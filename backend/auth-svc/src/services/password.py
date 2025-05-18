"""
Сервис для безопасной работы с паролями
"""
import re
import bcrypt
from typing import Tuple
from ..config.settings import settings

def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием bcrypt
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        Хешированный пароль в виде строки
    """
    # Используем настройки из конфигурации для определения сложности хеширования
    salt = bcrypt.gensalt(rounds=12)  # Значение по умолчанию, если не указано в settings
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие открытого пароля хешированному
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Ранее хешированный пароль
        
    Returns:
        True если пароль соответствует хешу, иначе False
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Проверяет пароль на соответствие требованиям безопасности
    
    Args:
        password: Пароль для проверки
        
    Returns:
        Кортеж (is_valid, error_message), где:
        - is_valid: True если пароль соответствует всем требованиям, иначе False
        - error_message: Сообщение с причиной отказа или пустая строка
    """
    # Проверка длины пароля
    min_length = 8  # Значение по умолчанию, если не указано в settings
    if len(password) < min_length:
        return False, f"Пароль должен содержать не менее {min_length} символов"
    
    # Проверка наличия различных типов символов
    patterns = {
        r'[A-Z]': "хотя бы одну заглавную букву",
        r'[a-z]': "хотя бы одну строчную букву",
        r'[0-9]': "хотя бы одну цифру",
        r'[!@#$%^&*(),.?":{}|<>]': "хотя бы один специальный символ"
    }
    
    for pattern, message in patterns.items():
        if not re.search(pattern, password):
            return False, f"Пароль должен содержать {message}"
    
    return True, "" 