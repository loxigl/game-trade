"""Dynamic categorization schema

Revision ID: 002
Revises: 001
Create Date: 2025-05-15 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Создаем ENUM для типов атрибутов
    attribute_type_enum = ENUM(
        'string', 'number', 'boolean', 'date', 'url', 'color', 'enum', 
        name='attributetype', 
        create_type=True
    )
    attribute_type_enum.create(op.get_bind())
    
    # Создаем таблицу games (игры)
    op.create_table('games',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_games_id'), 'games', ['id'], unique=False)
    op.create_index(op.f('ix_games_name'), 'games', ['name'], unique=True)
    
    # Создаем таблицу item_categories (категории предметов)
    op.create_table('item_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_item_categories_id'), 'item_categories', ['id'], unique=False)
    op.create_index(op.f('ix_item_categories_name'), 'item_categories', ['name'], unique=False)
    
    # Создаем таблицу category_attributes (атрибуты категорий)
    op.create_table('category_attributes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attribute_type', sa.Enum('string', 'number', 'boolean', 'date', 'url', 'color', 'enum', name='attributetype'), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_filterable', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('default_value', sa.String(), nullable=True),
        sa.Column('options', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['item_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_attributes_id'), 'category_attributes', ['id'], unique=False)
    
    # Создаем таблицу item_templates (шаблоны предметов)
    op.create_table('item_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(), nullable=True),
        sa.Column('is_tradable', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('base_price', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['item_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_item_templates_id'), 'item_templates', ['id'], unique=False)
    op.create_index(op.f('ix_item_templates_name'), 'item_templates', ['name'], unique=False)
    
    # Создаем таблицу items (предметы)
    op.create_table('items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('condition', sa.Float(), server_default=sa.text('100.0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['item_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_items_id'), 'items', ['id'], unique=False)
    
    # Создаем таблицу item_attribute_values (значения атрибутов предметов)
    op.create_table('item_attribute_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('attribute_id', sa.Integer(), nullable=False),
        sa.Column('value_string', sa.String(), nullable=True),
        sa.Column('value_number', sa.Float(), nullable=True),
        sa.Column('value_boolean', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['attribute_id'], ['category_attributes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_item_attribute_values_id'), 'item_attribute_values', ['id'], unique=False)
    
    # Добавляем поле item_template_id в таблицу listings
    op.add_column('listings', sa.Column('item_template_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'fk_listings_item_template', 'listings', 'item_templates',
        ['item_template_id'], ['id'], ondelete='CASCADE'
    )

def downgrade():
    # Удаляем внешний ключ и колонку item_template_id из listings
    op.drop_constraint('fk_listings_item_template', 'listings', type_='foreignkey')
    op.drop_column('listings', 'item_template_id')
    
    # Удаляем таблицы в обратном порядке
    op.drop_index(op.f('ix_item_attribute_values_id'), table_name='item_attribute_values')
    op.drop_table('item_attribute_values')
    
    op.drop_index(op.f('ix_items_id'), table_name='items')
    op.drop_table('items')
    
    op.drop_index(op.f('ix_item_templates_name'), table_name='item_templates')
    op.drop_index(op.f('ix_item_templates_id'), table_name='item_templates')
    op.drop_table('item_templates')
    
    op.drop_index(op.f('ix_category_attributes_id'), table_name='category_attributes')
    op.drop_table('category_attributes')
    
    op.drop_index(op.f('ix_item_categories_name'), table_name='item_categories')
    op.drop_index(op.f('ix_item_categories_id'), table_name='item_categories')
    op.drop_table('item_categories')
    
    op.drop_index(op.f('ix_games_name'), table_name='games')
    op.drop_index(op.f('ix_games_id'), table_name='games')
    op.drop_table('games')
    
    # Удаляем ENUM тип
    sa.Enum(name='attributetype').drop(op.get_bind()) 