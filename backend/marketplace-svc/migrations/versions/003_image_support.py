"""
Добавление поддержки загрузки и хранения изображений

Revision ID: 003
Revises: 002
Create Date: 2023-06-10 12:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Создание enum типов
    op.execute("""
        CREATE TYPE image_type AS ENUM (
            'listing', 
            'user', 
            'category', 
            'game', 
            'other'
        )
    """)
    
    op.execute("""
        CREATE TYPE image_status AS ENUM (
            'active', 
            'deleted'
        )
    """)
    
    # Создание таблицы изображений
    op.create_table(
        'images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.Enum('listing', 'user', 'category', 'game', 'other', name='image_type'), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('is_main', sa.Boolean(), default=False),
        sa.Column('order_index', sa.Integer(), default=0),
        sa.Column('status', sa.Enum('active', 'deleted', name='image_status'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индекса для быстрого поиска изображений по сущности и типу
    op.create_index('idx_images_entity_type', 'images', ['entity_id', 'type'])

def downgrade():
    # Удаление таблицы и enum-типов
    op.drop_index('idx_images_entity_type')
    op.drop_table('images')
    op.execute('DROP TYPE image_status')
    op.execute('DROP TYPE image_type') 