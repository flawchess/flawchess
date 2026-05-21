"""add evals_completed_at to games

Phase 91: tracks per-game Stockfish eval completion so the cold-drain
coroutine (run_eval_drain) can pick up uncompleted games without
re-evaluating already-processed rows. A partial index on (id) WHERE
evals_completed_at IS NULL enables fast LIFO drain picks and cheap
per-user COUNT queries for GET /imports/eval-coverage.

See also: SEED-023-two-lane-import-defer-stockfish.md (locked architecture).

Revision ID: bd54be3a66bf
Revises: e925558020b9
Create Date: 2026-05-21 01:50:28.860559+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd54be3a66bf"
down_revision: Union[str, None] = "e925558020b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add evals_completed_at column, partial index, and one-shot backfill.

    Step 1: nullable TIMESTAMPTZ column for per-game eval completion tracking.
    Step 2: partial index on (id) WHERE evals_completed_at IS NULL — enables
            fast LIFO drain picks (ORDER BY id DESC LIMIT 10) and cheap
            per-user COUNT queries.
    Step 3: backfill — all pre-Phase-91 games have already been through the
            import-time eval pass. Mark them completed so the cold drain skips
            them. Uses COALESCE(imported_at, NOW()) — imported_at is the only
            timestamp column on games (RESEARCH OQ-3, CONTEXT D-08 corrected).
    """
    op.add_column(
        "games",
        sa.Column("evals_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index — drain pick query (ORDER BY id DESC LIMIT 10) and
    # eval-coverage COUNT both predicate on evals_completed_at IS NULL.
    # String form (not sa.text) — matches project convention in 20260427_*.py
    # and 20260504_*.py (most recent partial index migrations).
    op.create_index(
        "ix_games_evals_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where="evals_completed_at IS NULL",
    )
    # Backfill: mark all existing rows as evaluated (CONTEXT D-08, corrected per
    # RESEARCH OQ-3). imported_at is the correct fallback — games table has only
    # imported_at as its timestamp column (no other timestamp variants exist).
    op.execute(
        "UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW()) "
        "WHERE evals_completed_at IS NULL"
    )


def downgrade() -> None:
    """Remove the partial index and evals_completed_at column."""
    op.drop_index(
        "ix_games_evals_pending",
        table_name="games",
        postgresql_where="evals_completed_at IS NULL",
    )
    op.drop_column("games", "evals_completed_at")
