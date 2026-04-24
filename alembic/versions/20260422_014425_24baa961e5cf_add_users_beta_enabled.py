"""add users.beta_enabled

Revision ID: 24baa961e5cf
Revises: 85dfef624a19
Create Date: 2026-04-22 01:44:25.198109+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24baa961e5cf'
down_revision: Union[str, Sequence[str], None] = '85dfef624a19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # BETA-01 / D-18: add the beta_enabled boolean flag to users, defaulting
    # to false on existing rows. No index — only read as part of a single-row
    # /users/me/profile fetch, never used as a scanning WHERE filter.
    op.add_column(
        "users",
        sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "beta_enabled")
