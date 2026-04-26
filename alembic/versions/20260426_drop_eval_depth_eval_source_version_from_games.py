"""drop eval_depth and eval_source_version from games

Revision ID: 6809b7c79eb3
Revises: b11018499e4f
Create Date: 2026-04-26 16:00:00.000000+00:00

Phase 69 hot-patch (post-smoke). The two columns added by b11018499e4f turned out
to be dead weight in the actual ingest path:

- eval_depth: the Lichess /api/games/user endpoint emits PGN [%eval cp] annotations
  with no depth field. There is nothing to populate this column from. Verified
  against the benchmark DB after the smoke ingest (`--per-cell 3`, 289k games):
  every annotation is the bare "[%eval N.NN]" form, never "[%eval N.NN,DEPTH]".
- eval_source_version: only one value ever set ("lichess-pgn"), zero information
  content. "Has Lichess evals" filtering is done at the position level
  (game_positions.eval_cp IS NOT NULL).

If a future eval source (dump-based import, custom Stockfish runs) needs a
discriminator, reintroduce a column at that point.

INGEST-06 reduced to centipawn-convention verification only (see REQUIREMENTS.md).
"""

from alembic import op
import sqlalchemy as sa


revision: str = "6809b7c79eb3"
down_revision: str | None = "b11018499e4f"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("games", "eval_source_version")
    op.drop_column("games", "eval_depth")


def downgrade() -> None:
    op.add_column("games", sa.Column("eval_depth", sa.SmallInteger(), nullable=True))
    op.add_column("games", sa.Column("eval_source_version", sa.String(length=50), nullable=True))
