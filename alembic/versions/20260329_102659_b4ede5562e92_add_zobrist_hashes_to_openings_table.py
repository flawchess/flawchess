"""add zobrist hashes to openings table

Revision ID: b4ede5562e92
Revises: 1b941ecba0a6
Create Date: 2026-03-29 10:26:59.770809+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4ede5562e92'
down_revision: Union[str, Sequence[str], None] = '1b941ecba0a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Zobrist hash columns to openings table and rebuild the dedup view."""
    op.add_column('openings', sa.Column('full_hash', sa.BigInteger(), nullable=True))
    op.add_column('openings', sa.Column('white_hash', sa.BigInteger(), nullable=True))
    op.add_column('openings', sa.Column('black_hash', sa.BigInteger(), nullable=True))

    # Recreate view to include the new columns
    op.execute("DROP VIEW IF EXISTS openings_dedup")
    op.execute("""
        CREATE VIEW openings_dedup AS
        SELECT DISTINCT ON (eco, name)
            id, eco, name, pgn, ply_count, fen, full_hash, white_hash, black_hash
        FROM openings
        ORDER BY eco, name, id
    """)


def downgrade() -> None:
    """Remove Zobrist hash columns and restore original view."""
    op.execute("DROP VIEW IF EXISTS openings_dedup")
    op.execute("""
        CREATE VIEW openings_dedup AS
        SELECT DISTINCT ON (eco, name)
            id, eco, name, pgn, ply_count, fen
        FROM openings
        ORDER BY eco, name, id
    """)
    op.drop_column('openings', 'black_hash')
    op.drop_column('openings', 'white_hash')
    op.drop_column('openings', 'full_hash')
