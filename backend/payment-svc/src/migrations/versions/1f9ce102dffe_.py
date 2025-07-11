"""empty message

Revision ID: 1f9ce102dffe
Revises: 
Create Date: 2025-05-19 13:09:49.743526

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f9ce102dffe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('idempotency_records',
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('operation_type', sa.String(length=100), nullable=False),
    sa.Column('response_data', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_idempotency_records_key'), 'idempotency_records', ['key'], unique=False)
    op.create_index(op.f('ix_idempotency_records_operation_type'), 'idempotency_records', ['operation_type'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('avatar_url', sa.String(), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('reputation_score', sa.Float(), nullable=False),
    sa.Column('is_verified_seller', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('total_sales', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)
    op.create_table('wallets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('wallet_uid', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('balances', sa.JSON(), nullable=False),
    sa.Column('status', sa.Enum('active', 'blocked', 'pending', 'closed', name='walletstatus'), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('limits', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', name='uq_user_wallet'),
    sa.UniqueConstraint('wallet_uid')
    )
    op.create_index('idx_wallet_user_status', 'wallets', ['user_id', 'status'], unique=False)
    op.create_index(op.f('ix_wallets_id'), 'wallets', ['id'], unique=False)
    op.create_index(op.f('ix_wallets_status'), 'wallets', ['status'], unique=False)
    op.create_index(op.f('ix_wallets_user_id'), 'wallets', ['user_id'], unique=False)
    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_uid', sa.String(length=36), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=True),
    sa.Column('seller_id', sa.Integer(), nullable=True),
    sa.Column('listing_id', sa.Integer(), nullable=True),
    sa.Column('item_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sa.String(), nullable=False),
    sa.Column('fee_amount', sa.Float(), nullable=False),
    sa.Column('fee_percentage', sa.Float(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ESCROW_HELD', 'COMPLETED', 'REFUNDED', 'DISPUTED', 'CANCELED', 'FAILED', name='transactionstatus'), nullable=False),
    sa.Column('type', sa.Enum('PURCHASE', 'DEPOSIT', 'WITHDRAWAL', 'REFUND', 'FEE', 'SYSTEM', name='transactiontype'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('escrow_held_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('disputed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.Column('external_reference', sa.String(), nullable=True),
    sa.Column('dispute_reason', sa.Text(), nullable=True),
    sa.Column('refund_reason', sa.Text(), nullable=True),
    sa.Column('cancel_reason', sa.Text(), nullable=True),
    sa.Column('wallet_id', sa.Integer(), nullable=True),
    sa.Column('parent_transaction_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['parent_transaction_id'], ['transactions.id'], ),
    sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('transaction_uid')
    )
    op.create_index('idx_transactions_buyer_seller', 'transactions', ['buyer_id', 'seller_id'], unique=False)
    op.create_index('idx_transactions_status_created', 'transactions', ['status', 'created_at'], unique=False)
    op.create_index('idx_transactions_type_status', 'transactions', ['type', 'status'], unique=False)
    op.create_index(op.f('ix_transactions_buyer_id'), 'transactions', ['buyer_id'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_transactions_external_reference'), 'transactions', ['external_reference'], unique=False)
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_seller_id'), 'transactions', ['seller_id'], unique=False)
    op.create_index(op.f('ix_transactions_status'), 'transactions', ['status'], unique=False)
    op.create_index(op.f('ix_transactions_type'), 'transactions', ['type'], unique=False)
    op.create_index(op.f('ix_transactions_wallet_id'), 'transactions', ['wallet_id'], unique=False)
    op.create_table('sales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.Integer(), nullable=True),
    sa.Column('listing_id', sa.Integer(), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=False),
    sa.Column('seller_id', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('currency', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'payment_processing', 'delivery_pending', 'completed', 'canceled', 'refunded', 'disputed', name='salestatus'), server_default='pending', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_buyer_id'), 'sales', ['buyer_id'], unique=False)
    op.create_index(op.f('ix_sales_id'), 'sales', ['id'], unique=False)
    op.create_index(op.f('ix_sales_listing_id'), 'sales', ['listing_id'], unique=False)
    op.create_index(op.f('ix_sales_seller_id'), 'sales', ['seller_id'], unique=False)
    op.create_table('transaction_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.Integer(), nullable=False),
    sa.Column('previous_status', sa.Enum('PENDING', 'ESCROW_HELD', 'COMPLETED', 'REFUNDED', 'DISPUTED', 'CANCELED', 'FAILED', name='transactionstatus'), nullable=True),
    sa.Column('new_status', sa.Enum('PENDING', 'ESCROW_HELD', 'COMPLETED', 'REFUNDED', 'DISPUTED', 'CANCELED', 'FAILED', name='transactionstatus'), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('initiator_id', sa.Integer(), nullable=True),
    sa.Column('initiator_type', sa.String(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transaction_history_id'), 'transaction_history', ['id'], unique=False)
    op.create_index(op.f('ix_transaction_history_timestamp'), 'transaction_history', ['timestamp'], unique=False)
    op.create_index(op.f('ix_transaction_history_transaction_id'), 'transaction_history', ['transaction_id'], unique=False)
    op.create_table('wallet_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sa.Enum('USD', 'EUR', 'GBP', 'RUB', 'JPY', 'CNY', name='currency'), nullable=False),
    sa.Column('balance_before', sa.Float(), nullable=False),
    sa.Column('balance_after', sa.Float(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_wallet_txn_currency', 'wallet_transactions', ['currency'], unique=False)
    op.create_index('idx_wallet_txn_wallet_created', 'wallet_transactions', ['wallet_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_created_at'), 'wallet_transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_currency'), 'wallet_transactions', ['currency'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_id'), 'wallet_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_transaction_id'), 'wallet_transactions', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_type'), 'wallet_transactions', ['type'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_wallet_id'), 'wallet_transactions', ['wallet_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_wallet_transactions_wallet_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_type'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_transaction_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_currency'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_created_at'), table_name='wallet_transactions')
    op.drop_index('idx_wallet_txn_wallet_created', table_name='wallet_transactions')
    op.drop_index('idx_wallet_txn_currency', table_name='wallet_transactions')
    op.drop_table('wallet_transactions')
    op.drop_index(op.f('ix_transaction_history_transaction_id'), table_name='transaction_history')
    op.drop_index(op.f('ix_transaction_history_timestamp'), table_name='transaction_history')
    op.drop_index(op.f('ix_transaction_history_id'), table_name='transaction_history')
    op.drop_table('transaction_history')
    op.drop_index(op.f('ix_sales_seller_id'), table_name='sales')
    op.drop_index(op.f('ix_sales_listing_id'), table_name='sales')
    op.drop_index(op.f('ix_sales_id'), table_name='sales')
    op.drop_index(op.f('ix_sales_buyer_id'), table_name='sales')
    op.drop_table('sales')
    op.drop_index(op.f('ix_transactions_wallet_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_type'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_status'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_seller_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_external_reference'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_buyer_id'), table_name='transactions')
    op.drop_index('idx_transactions_type_status', table_name='transactions')
    op.drop_index('idx_transactions_status_created', table_name='transactions')
    op.drop_index('idx_transactions_buyer_seller', table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_wallets_user_id'), table_name='wallets')
    op.drop_index(op.f('ix_wallets_status'), table_name='wallets')
    op.drop_index(op.f('ix_wallets_id'), table_name='wallets')
    op.drop_index('idx_wallet_user_status', table_name='wallets')
    op.drop_table('wallets')
    op.drop_index(op.f('ix_profiles_id'), table_name='profiles')
    op.drop_table('profiles')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_idempotency_records_operation_type'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_key'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
    # ### end Alembic commands ### 