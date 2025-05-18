"""
Сервис для отправки email сообщений
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config.settings import settings
import logging

# Логгер для фиксации ошибок отправки email
logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Отправляет email сообщение
    
    Args:
        to_email: Email получателя
        subject: Тема письма
        html_content: HTML содержимое письма
        
    Returns:
        True, если письмо отправлено успешно, иначе False
    """
    try:
        # Настройка сообщения
        message = MIMEMultipart()
        message["From"] = settings.EMAIL_FROM
        message["To"] = to_email
        message["Subject"] = subject
        
        # Добавляем HTML содержимое
        message.attach(MIMEText(html_content, "html"))
        
        # Подключаемся к SMTP серверу
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.ehlo()
        
        # Используем TLS, если необходимо
        if settings.SMTP_TLS:
            server.starttls()
            server.ehlo()
        
        # Аутентификация, если необходимо
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        # Отправляем сообщение
        server.sendmail(settings.EMAIL_FROM, to_email, message.as_string())
        
        # Закрываем соединение
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки email на {to_email}: {str(e)}")
        return False

async def send_verification_email(to_email: str, token: str) -> bool:
    """
    Отправляет email для подтверждения адреса электронной почты
    
    Args:
        to_email: Email получателя
        token: Токен подтверждения
        
    Returns:
        True, если письмо отправлено успешно, иначе False
    """
    # Формируем ссылку для подтверждения
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    # Содержимое письма
    subject = "Подтверждение регистрации"
    html_content = f"""
    <html>
        <body>
            <h2>Подтверждение регистрации</h2>
            <p>Спасибо за регистрацию! Пожалуйста, подтвердите ваш email, перейдя по ссылке:</p>
            <p><a href="{verification_url}">Подтвердить email</a></p>
            <p>Если вы не регистрировались на нашем сайте, просто проигнорируйте это сообщение.</p>
            <p>Ссылка действительна в течение 24 часов.</p>
        </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content)

async def send_password_reset_email(to_email: str, token: str) -> bool:
    """
    Отправляет email с инструкциями по сбросу пароля
    
    Args:
        to_email: Email получателя
        token: Токен сброса пароля
        
    Returns:
        True, если письмо отправлено успешно, иначе False
    """
    # Формируем ссылку для сброса пароля
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    # Содержимое письма
    subject = "Сброс пароля"
    html_content = f"""
    <html>
        <body>
            <h2>Сброс пароля</h2>
            <p>Мы получили запрос на сброс пароля для вашей учетной записи. Если вы не запрашивали сброс пароля, проигнорируйте это сообщение.</p>
            <p>Для сброса пароля перейдите по ссылке:</p>
            <p><a href="{reset_url}">Сбросить пароль</a></p>
            <p>Ссылка действительна в течение 1 часа.</p>
        </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content) 