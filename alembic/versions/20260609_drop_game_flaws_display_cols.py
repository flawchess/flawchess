"""drop game_flaws display columns (es_before, es_after, move_san)

Revision ID: f8a2d1c9b345
Revises: e1a7c93b6f02
Create Date: 2026-06-09

Phase 112 (D-07): drop es_before, es_after, move_san from game_flaws.
These three columns were display-only payload stored at classify time (SEED-038).
After Phase 112 they are sourced at query time via a game_positions join in
query_flaws (D-08 — two aliased LEFT JOINs on (game_id, user_id, ply) and ply-1).

`fen` is intentionally KEPT: game_positions stores only Zobrist hashes (no FEN),
so fen is the one denormalized display column that cannot be recovered without
replaying the PGN (Pitfall 4 in 112-CONTEXT.md).

Dev-only migration (v1.24 unshipped — no production data to preserve). Re-run
`uv run python scripts/backfill_flaws.py --db dev` after applying to dev users.

Literal column types only — no import of live app constants (per project rule,
same as 20260607_alter_game_flaws_impact_cols.py).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a2d1c9b345"
down_revision: str = "e1a7c93b6f02"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("game_flaws", "es_before")
    op.drop_column("game_flaws", "es_after")
    op.drop_column("game_flaws", "move_san")


def downgrade() -> None:
    # Re-add as nullable so existing rows don't break on rollback.
    # Re-added in reverse order to match original column layout.
    op.add_column("game_flaws", sa.Column("move_san", sa.String(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_after", sa.Float(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_before", sa.Float(), nullable=True))
