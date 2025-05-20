"""
Модели для статистики продаж и покупок
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.connection import Base

class SellerStatistics(Base):
    """
    Статистика продавца
    """
    __tablename__ = "seller_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Общая статистика
    total_sales = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Float, nullable=False, default=0.0)
    completed_sales = Column(Integer, nullable=False, default=0)
    cancelled_sales = Column(Integer, nullable=False, default=0)
    disputed_sales = Column(Integer, nullable=False, default=0)
    
    # Месячная статистика
    current_month_start = Column(DateTime(timezone=True), default=func.now())
    current_month_sales = Column(Integer, nullable=False, default=0)
    current_month_revenue = Column(Float, nullable=False, default=0.0)
    
    # Рейтинг
    average_rating = Column(Float, nullable=False, default=0.0)
    rating_count = Column(Integer, nullable=False, default=0)
    
    # Общие данные
    last_sale_date = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # JSON данные для дополнительной статистики
    extra_data = Column(JSON)
    
    # Отношения
    seller = relationship("User", foreign_keys=[seller_id])

class BuyerStatistics(Base):
    """
    Статистика покупателя
    """
    __tablename__ = "buyer_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Общая статистика
    total_purchases = Column(Integer, nullable=False, default=0)
    total_spent = Column(Float, nullable=False, default=0.0)
    
    # Месячная статистика
    current_month_start = Column(DateTime(timezone=True), default=func.now())
    current_month_purchases = Column(Integer, nullable=False, default=0)
    current_month_spent = Column(Float, nullable=False, default=0.0)
    
    # Общие данные
    last_purchase_date = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # JSON данные для дополнительной статистики
    extra_data = Column(JSON)
    
    # Отношения
    buyer = relationship("User", foreign_keys=[buyer_id])

class ProductStatistics(Base):
    """
    Статистика по продуктам/играм
    """
    __tablename__ = "product_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False, index=True)
    
    # Статистика продаж
    total_sales = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Float, nullable=False, default=0.0)
    average_price = Column(Float, nullable=False, default=0.0)
    
    # Временные метки
    first_sale_date = Column(DateTime(timezone=True))
    last_sale_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # JSON данные для дополнительной статистики
    extra_data = Column(JSON) 