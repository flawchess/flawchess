"""widen material_signature to varchar 80

Revision ID: fb1fad671a94
Revises: b4ede5562e92
Create Date: 2026-04-01 18:31:25.399849+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb1fad671a94'
down_revision: Union[str, Sequence[str], None] = 'b4ede5562e92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen material_signature from VARCHAR(40) to VARCHAR(80).

    Custom-position games (chess.com "from position") can have non-standard
    piece counts, producing signatures longer than 40 chars.
    """
    op.alter_column(
        'game_positions',
        'material_signature',
        existing_type=sa.String(40),
        type_=sa.String(65),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert material_signature back to VARCHAR(40)."""
    op.alter_column(
        'game_positions',
        'material_signature',
        existing_type=sa.String(65),
        type_=sa.String(40),
        existing_nullable=True,
    )
