"""Add ix_game_flaws_blob_backfill — partial index for the tier-4 blob-backfill lottery.

The Plan-02 tier-4 lottery in the Phase-145 corpus backfill picks a game whose
game_flaw rows still have allowed_pv_lines IS NULL (blobs not yet written). Without
this index, the lottery would seq-scan all ~3.18M rows in game_flaws on every remote-
worker idle poll, because the candidate predicate (allowed_pv_lines IS NULL) has no
covering index.

This partial index limits the scan to the backfill-pending rows only. As the backfill
completes (blobs or D-06 sentinels are written to each row), rows leave the index, so
it shrinks towards near-empty by the time the rollout finishes. In steady state after
backfill the index is effectively empty and imposes negligible overhead.

The index is on game_id so the lottery can retrieve the game_id of a candidate row
directly from the index without a heap fetch; the ORDER BY in the lottery is a
random exponential key (no index can serve it), but the cost driver is the candidate
gather, not the small sort.

Created non-concurrently (inside transaction) following the project's other
partial-index migrations (ix_games_pv_backfill_pending, ix_games_needs_engine_full_evals,
ix_games_user_evals_pending): migrations run against a quiescent backend at container
startup via deploy/entrypoint.sh, and CONCURRENTLY cannot run inside a transaction.

Revision ID: c3f5d1e8a092
Revises: 0b6ac7a4b59a
Create Date: 2026-06-30 22:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f5d1e8a092"
down_revision: Union[str, None] = "0b6ac7a4b59a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_game_flaws_blob_backfill",
        "game_flaws",
        ["game_id"],
        unique=False,
        postgresql_where=sa.text("allowed_pv_lines IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_game_flaws_blob_backfill", table_name="game_flaws")
