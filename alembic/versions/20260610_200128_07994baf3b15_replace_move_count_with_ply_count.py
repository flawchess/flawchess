"""replace move_count with ply_count

Revision ID: 07994baf3b15
Revises: d9e3f1a4b5c6
Create Date: 2026-06-10 20:01:28.168330+00:00

Single in-transaction migration: adds nullable ply_count, backfills it from
max(ply) per game via game_positions, then drops move_count.

Backfill identity: game_positions.ply is 0-based and contiguous per game,
so max(ply) per game equals the exact half-move count (len(nodes) in zobrist.py).
The 971 position-less games (where move_count was already NULL) stay NULL.

Measured on prod (2026-06-10): the max(ply) aggregate runs in 3.2s at 33MB
peak over 43.9M game_positions rows; the write touches ~590k games rows;
sub-10s total. Runs at container startup before uvicorn serves (entrypoint.sh),
so there is no NULL window and no HUMAN gate required.

downgrade() reverses the operation: re-adds move_count as nullable and
approximates the old full-move count via (ply_count + 1) / 2 (integer division).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "07994baf3b15"
down_revision: Union[str, Sequence[str], None] = "d9e3f1a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable ply_count, backfill from game_positions, drop move_count."""
    # Step 1: add nullable ply_count column.
    op.add_column("games", sa.Column("ply_count", sa.Integer(), nullable=True))

    # Step 2: backfill ply_count from game_positions.
    # max(ply) per game equals the exact half-move count (plies are 0-based contiguous).
    # Games with no positions (NULL move_count previously) keep ply_count = NULL.
    op.execute(
        "UPDATE games g SET ply_count = sub.mp "
        "FROM (SELECT game_id, max(ply) AS mp FROM game_positions GROUP BY game_id) sub "
        "WHERE g.id = sub.game_id"
    )

    # Step 3: drop the old full-move count column.
    op.drop_column("games", "move_count")


def downgrade() -> None:
    """Re-add move_count, approximate from ply_count, drop ply_count."""
    # Step 1: re-add nullable move_count column.
    op.add_column("games", sa.Column("move_count", sa.Integer(), nullable=True))

    # Step 2: approximate move_count as (ply_count + 1) / 2 (integer division).
    # This reproduces the original full-move count for even and odd ply counts.
    op.execute(
        "UPDATE games SET move_count = (ply_count + 1) / 2 WHERE ply_count IS NOT NULL"
    )

    # Step 3: drop ply_count.
    op.drop_column("games", "ply_count")
