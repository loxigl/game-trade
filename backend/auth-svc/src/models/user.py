from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ARRAY
from sqlalchemy.sql import expression
from datetime import datetime
from ..database.connection import Base

class User(Base):
    """
    Модель пользователя в базе данных
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    is_verified = Column(Boolean, server_default=expression.false(), nullable=False)
    is_admin = Column(Boolean, server_default=expression.false(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Новые поля для управления ролями и безопасностью
    roles = Column(ARRAY(String), server_default="{'user'}", nullable=False)
    last_password_change = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    failed_login_attempts = Column(Integer, server_default="0", nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True) 