"""create openings table

Revision ID: 1b941ecba0a6
Revises: fb62990270fd
Create Date: 2026-03-28 19:40:57.321501+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b941ecba0a6'
down_revision: Union[str, Sequence[str], None] = 'fb62990270fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('openings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('eco', sa.String(length=10), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('pgn', sa.Text(), nullable=False),
    sa.Column('ply_count', sa.SmallInteger(), nullable=False),
    sa.Column('fen', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('eco', 'name', 'pgn', name='uq_openings_eco_name_pgn')
    )
    op.create_index('ix_openings_eco_name', 'openings', ['eco', 'name'], unique=False)
    op.execute("""
        CREATE VIEW openings_dedup AS
        SELECT DISTINCT ON (eco, name)
            id, eco, name, pgn, ply_count, fen
        FROM openings
        ORDER BY eco, name, id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW IF EXISTS openings_dedup")
    op.drop_index('ix_openings_eco_name', table_name='openings')
    op.drop_table('openings')
