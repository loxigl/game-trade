"""add roles and security fields

Revision ID: a4b5c6d7e8f9
Revises: 10f3a8a68c28
Create Date: 2025-05-14 10:15:45.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = '10f3a8a68c28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поле roles типа ARRAY
    op.add_column('users', sa.Column('roles', postgresql.ARRAY(sa.String()), 
                                     server_default="{'user'}", nullable=False))
    
    # Добавляем поля для безопасности аккаунта
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(timezone=True), 
                                     server_default=sa.text('now()'), nullable=False))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), 
                                     server_default='0', nullable=False))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(timezone=True), 
                                     nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(), 
                                     nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), 
                                     nullable=True))


def downgrade() -> None:
    # Удаляем все добавленные поля в обратном порядке
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'roles') 