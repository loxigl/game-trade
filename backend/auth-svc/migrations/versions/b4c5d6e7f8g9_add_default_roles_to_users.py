"""add default roles to users

Revision ID: b4c5d6e7f8g9
Revises: a4b5c6d7e8f9
Create Date: 2025-05-15 10:15:45.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8g9'
down_revision: Union[str, None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Определяем таблицу users для обновления данных
    users = table(
        'users',
        column('id', sa.Integer),
        column('roles', postgresql.ARRAY(sa.String))
    )
    
    # Обновляем всех пользователей, у которых нет роли, 
    # устанавливаем базовую роль 'user'
    op.execute(
        users.update().where(users.c.roles == None).values(roles=["user"])
    )
    
    # Обновляем всех пользователей с ролью NULL, 
    # устанавливаем базовую роль 'user'
    op.execute(
        users.update().where(users.c.roles == sa.null()).values(roles=["user"])
    )
    
    # Обновляем всех пользователей с пустым массивом ролей, 
    # устанавливаем базовую роль 'user'
    op.execute(
        users.update().where(users.c.roles == '{}').values(roles=["user"])
    )
    
    # Настраиваем not null ограничение после обновления данных
    op.alter_column('users', 'roles',
                    existing_type=postgresql.ARRAY(sa.String()),
                    nullable=False,
                    server_default=sa.text("ARRAY['user']::VARCHAR[]")
    )


def downgrade() -> None:
    # Удаляем ограничение not null
    op.alter_column('users', 'roles',
                    existing_type=postgresql.ARRAY(sa.String()),
                    nullable=True,
                    server_default=None) 