from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey, Boolean, Text, JSON, UniqueConstraint, Table, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database.connection import Base
import enum

class AttributeType(str, enum.Enum):
    """Типы атрибутов для категорий"""
    STRING = "string"         # Строковый тип
    NUMBER = "number"         # Числовой тип
    BOOLEAN = "boolean"       # Логический тип
    DATE = "date"             # Дата
    URL = "url"               # Ссылка
    COLOR = "color"           # Цвет
    ENUM = "enum"             # Перечисление (выбор из списка)

class CategoryType(str, enum.Enum):
    """Типы категорий"""
    MAIN = "main"             # Основная категория
    SUB = "sub"               # Подкатегория

class Game(Base):
    """Игра, к которой относятся предметы"""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    logo_url = Column(String(255))
    website = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    categories = relationship("ItemCategory", back_populates="game")
    images = relationship("Image", 
        primaryjoin="and_(foreign(Image.entity_id)==Game.id, Image.type=='game')")

class ItemCategory(Base):
    """Категория предметов в игре"""
    __tablename__ = "item_categories"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("item_categories.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon_url = Column(String(255))
    # Тип категории: основная или подкатегория
    category_type = Column(String(50), default=CategoryType.MAIN)
    # Порядок отображения
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Уникальность имени категории в рамках игры и родительской категории
    __table_args__ = (
        UniqueConstraint('game_id', 'parent_id', 'name', name='uq_category_game_parent_name'),
    )
    
    # Отношения
    game = relationship("Game", back_populates="categories")
    parent = relationship("ItemCategory", remote_side=[id], backref="subcategories")
    attributes = relationship("CategoryAttribute", back_populates="category")
    item_templates = relationship("ItemTemplate", back_populates="category")
    images = relationship("Image", 
        primaryjoin="and_(foreign(Image.entity_id)==ItemCategory.id, Image.type=='category')")

class CategoryAttribute(Base):
    """Атрибут категории предметов"""
    __tablename__ = "category_attributes"
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("item_categories.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    attribute_type = Column(String(50), nullable=False)  # string, number, boolean, enum
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=False)
    default_value = Column(String(255))  # JSON строка с дефолтным значением
    options = Column(JSON)  # Опции для типа enum
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Уникальность имени атрибута в рамках категории
    __table_args__ = (
        UniqueConstraint('category_id', 'name', name='uq_attribute_category_name'),
    )
    
    # Отношения
    category = relationship("ItemCategory", back_populates="attributes")
    attribute_values = relationship("ItemAttributeValue", back_populates="attribute")

class ItemTemplate(Base):
    """Шаблон предмета (общие характеристики для группы однотипных предметов)"""
    __tablename__ = "item_templates"
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("item_categories.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    category = relationship("ItemCategory", back_populates="item_templates")
    items = relationship("Item", back_populates="template")
    listings = relationship("Listing", back_populates="item_template")
    template_attributes = relationship("TemplateAttribute", back_populates="template")

class TemplateAttribute(Base):
    """Атрибут шаблона предмета (характеристики, специфичные для конкретного шаблона)"""
    __tablename__ = "template_attributes"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("item_templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    attribute_type = Column(String(50), nullable=False)  # string, number, boolean, enum
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=False)
    default_value = Column(String(255))  # JSON строка с дефолтным значением
    options = Column(JSON)  # Опции для типа enum
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Уникальность имени атрибута в рамках шаблона
    __table_args__ = (
        UniqueConstraint('template_id', 'name', name='uq_attribute_template_name'),
    )
    
    # Отношения
    template = relationship("ItemTemplate", back_populates="template_attributes")
    attribute_values = relationship("ItemAttributeValue", 
                                   foreign_keys="[ItemAttributeValue.template_attribute_id]", 
                                   back_populates="template_attribute")

class Item(Base):
    """Конкретный экземпляр предмета"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("item_templates.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL для системных предметов
    is_tradable = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    template = relationship("ItemTemplate", back_populates="items")
    owner = relationship("User")
    attribute_values = relationship("ItemAttributeValue", back_populates="item")
    listing = relationship("Listing", back_populates="item", uselist=False)

class ItemAttributeValue(Base):
    """Значение атрибута для конкретного предмета"""
    __tablename__ = "item_attribute_values"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    attribute_id = Column(Integer, ForeignKey("category_attributes.id"), nullable=True)
    template_attribute_id = Column(Integer, ForeignKey("template_attributes.id"), nullable=True)
    
    # Храним значения разных типов в соответствующих колонках
    value_string = Column(String(255))
    value_number = Column(Float)
    value_boolean = Column(Boolean)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Уникальность комбинации item_id и attribute_id
    __table_args__ = (
        UniqueConstraint('item_id', 'attribute_id', name='uq_item_attribute'),
        UniqueConstraint('item_id', 'template_attribute_id', name='uq_item_template_attribute'),
        CheckConstraint('(attribute_id IS NOT NULL) OR (template_attribute_id IS NOT NULL)', 
                       name='chk_attribute_source')
    )
    
    # Отношения
    item = relationship("Item", back_populates="attribute_values")
    attribute = relationship("CategoryAttribute", foreign_keys=[attribute_id], back_populates="attribute_values")
    template_attribute = relationship("TemplateAttribute", foreign_keys=[template_attribute_id], back_populates="attribute_values") 