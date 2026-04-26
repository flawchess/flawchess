"""add ix_gp_user_game_ply partial composite index for opening insights

Revision ID: 80e22b38993a
Revises: 6809b7c79eb3
Create Date: 2026-04-26 20:15:33.347823+00:00

Phase 70 (v1.13). Composite covering index on game_positions used by the
opening_insights_service transition aggregation.

Column order (user_id, game_id, ply) is LOAD-BEARING — it matches the LAG
window's PARTITION BY game_id ORDER BY ply within a per-user predicate, so
PostgreSQL streams rows directly from the index without a re-sort. INCLUDE
keeps full_hash and move_san on the leaf pages so query plans report
Heap Fetches: 0. Partial-on-(ply BETWEEN 1 AND 17) keeps the index ~9%
of table size.

DO NOT reorder these columns "for symmetry" with sibling ix_gp_user_*
indexes. Verified 2026-04-26 against dev DB:
  user 7  (Hikaru, 65k games / 5.7M positions): 2.0 s -> 816 ms
  user 28 (5,045 games / 336k positions):       65 ms (Index Only Scan)

First migration in this project to use postgresql_concurrently=True.
CONCURRENTLY cannot run inside a transaction, hence the
op.get_context().autocommit_block() wrapper. On first prod deploy,
expect a 30-60 s build for the heaviest user before the backend
container completes startup.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "80e22b38993a"
down_revision: str | None = "6809b7c79eb3"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # CONCURRENTLY cannot run inside a transaction; autocommit_block opens a
    # raw connection without a surrounding BEGIN. See Alembic cookbook.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_gp_user_game_ply",
            "game_positions",
            ["user_id", "game_id", "ply"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
            postgresql_include=["full_hash", "move_san"],
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_gp_user_game_ply",
            table_name="game_positions",
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
        )
