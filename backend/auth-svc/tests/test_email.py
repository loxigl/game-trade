import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from email.message import EmailMessage
import aiosmtplib

from src.services.email import (
    EmailService, construct_email_message, 
    send_verification_email, send_password_reset_email
)
from src.config.settings import settings

class TestEmailService:
    """
    Тесты для сервиса отправки электронной почты
    """
    
    def test_construct_email_message(self):
        """
        Тест создания объекта сообщения электронной почты
        """
        # Параметры сообщения
        sender = "test@example.com"
        recipient = "user@example.com"
        subject = "Test Subject"
        body = "Test Body"
        
        # Создаем сообщение
        message = construct_email_message(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body
        )
        
        # Проверяем тип и содержимое
        assert isinstance(message, EmailMessage)
        assert message["From"] == sender
        assert message["To"] == recipient
        assert message["Subject"] == subject
        assert message.get_content() == body
        assert message.get_content_type() == "text/plain"
    
    def test_construct_email_message_html(self):
        """
        Тест создания объекта сообщения электронной почты с HTML
        """
        # Параметры сообщения
        sender = "test@example.com"
        recipient = "user@example.com"
        subject = "Test Subject"
        body = "<p>Test Body</p>"
        
        # Создаем сообщение
        message = construct_email_message(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            is_html=True
        )
        
        # Проверяем тип и содержимое
        assert isinstance(message, EmailMessage)
        assert message["From"] == sender
        assert message["To"] == recipient
        assert message["Subject"] == subject
        assert message.get_content() == body
        assert message.get_content_type() == "text/html"
    
    @patch('aiosmtplib.send')
    async def test_email_service_send_email(self, mock_send):
        """
        Тест отправки электронного письма
        """
        # Настраиваем мок
        mock_send.return_value = AsyncMock()
        
        # Создаем сервис
        email_service = EmailService()
        
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = "test@example.com"
        message["To"] = "user@example.com"
        message["Subject"] = "Test Subject"
        message.set_content("Test Body")
        
        # Отправляем письмо
        await email_service.send_email(message)
        
        # Проверяем, что функция отправки была вызвана
        mock_send.assert_called_once()
    
    @patch('aiosmtplib.send')
    async def test_email_service_send_email_error(self, mock_send):
        """
        Тест обработки ошибок при отправке электронного письма
        """
        # Настраиваем мок для вызова исключения
        mock_send.side_effect = aiosmtplib.SMTPException("SMTP error")
        
        # Создаем сервис
        email_service = EmailService()
        
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = "test@example.com"
        message["To"] = "user@example.com"
        message["Subject"] = "Test Subject"
        message.set_content("Test Body")
        
        # Отправляем письмо и проверяем обработку ошибки
        with pytest.raises(Exception) as exc_info:
            await email_service.send_email(message)
        
        # Проверяем, что исключение содержит нужное сообщение
        assert "Error sending email" in str(exc_info.value)
        assert "SMTP error" in str(exc_info.value)
    
    @patch('src.services.email.EmailService.send_email')
    async def test_send_verification_email(self, mock_send_email):
        """
        Тест отправки письма с подтверждением электронной почты
        """
        # Данные для теста
        email = "user@example.com"
        token = "verification_token"
        username = "testuser"
        
        # Отправляем письмо
        await send_verification_email(email, token, username)
        
        # Проверяем, что метод отправки был вызван
        mock_send_email.assert_called_once()
        
        # Получаем аргументы вызова
        message = mock_send_email.call_args[0][0]
        
        # Проверяем содержимое письма
        assert message["To"] == email
        assert message["From"] == settings.EMAIL_FROM
        assert "Подтверждение" in message["Subject"]
        
        # Проверяем, что в тексте есть токен
        content = message.get_content()
        assert token in content
        assert username in content
        assert settings.FRONTEND_URL in content
    
    @patch('src.services.email.EmailService.send_email')
    async def test_send_password_reset_email(self, mock_send_email):
        """
        Тест отправки письма для сброса пароля
        """
        # Данные для теста
        email = "user@example.com"
        token = "reset_token"
        username = "testuser"
        
        # Отправляем письмо
        await send_password_reset_email(email, token, username)
        
        # Проверяем, что метод отправки был вызван
        mock_send_email.assert_called_once()
        
        # Получаем аргументы вызова
        message = mock_send_email.call_args[0][0]
        
        # Проверяем содержимое письма
        assert message["To"] == email
        assert message["From"] == settings.EMAIL_FROM
        assert "Сброс пароля" in message["Subject"]
        
        # Проверяем, что в тексте есть токен
        content = message.get_content()
        assert token in content
        assert username in content
        assert settings.FRONTEND_URL in content
        
    @patch('src.services.email.construct_email_message')
    @patch('src.services.email.EmailService.send_email')
    async def test_email_templates_content(self, mock_send_email, mock_construct_message):
        """
        Тест содержимого шаблонов электронных писем
        """
        # Создаем мок для возврата сообщения
        message = MagicMock(spec=EmailMessage)
        mock_construct_message.return_value = message
        
        # Отправляем письма с разными шаблонами
        await send_verification_email("user@example.com", "token123", "username")
        
        # Проверяем параметры вызова для письма верификации
        verify_call = mock_construct_message.call_args_list[0][1]
        assert verify_call["is_html"] is True
        assert "подтверждения регистрации" in verify_call["subject"]
        assert "token123" in verify_call["body"]
        assert "username" in verify_call["body"]
        
        # Отправляем письмо сброса пароля
        await send_password_reset_email("user@example.com", "token456", "username")
        
        # Проверяем параметры вызова для письма сброса пароля
        reset_call = mock_construct_message.call_args_list[1][1]
        assert reset_call["is_html"] is True
        assert "сброса пароля" in reset_call["subject"]
        assert "token456" in reset_call["body"]
        assert "username" in reset_call["body"] 