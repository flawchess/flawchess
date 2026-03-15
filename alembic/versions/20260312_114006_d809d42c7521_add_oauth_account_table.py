"""add_oauth_account_table

Revision ID: d809d42c7521
Revises: ea8ca9526dcf
Create Date: 2026-03-12 11:40:06.119821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd809d42c7521'
down_revision: Union[str, Sequence[str], None] = 'ea8ca9526dcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create oauth_account table for FastAPI-Users OAuth integration."""
    op.create_table(
        'oauth_account',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('oauth_name', sa.String(length=100), nullable=False),
        sa.Column('access_token', sa.String(length=1024), nullable=False),
        sa.Column('expires_at', sa.Integer(), nullable=True),
        sa.Column('refresh_token', sa.String(length=1024), nullable=True),
        sa.Column('account_id', sa.String(length=320), nullable=False),
        sa.Column('account_email', sa.String(length=320), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_oauth_account_oauth_name'), 'oauth_account', ['oauth_name'], unique=False)
    op.create_index(op.f('ix_oauth_account_account_id'), 'oauth_account', ['account_id'], unique=False)


def downgrade() -> None:
    """Drop oauth_account table."""
    op.drop_index(op.f('ix_oauth_account_account_id'), table_name='oauth_account')
    op.drop_index(op.f('ix_oauth_account_oauth_name'), table_name='oauth_account')
    op.drop_table('oauth_account')
