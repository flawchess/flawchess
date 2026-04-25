"""add eval_depth eval_source_version to games

Revision ID: b11018499e4f
Revises: 2af113f4790f
Create Date: 2026-04-25 20:34:23.728546+00:00

Phase 69 INGEST-06. Adds two nullable columns to the canonical games table; applied
uniformly to dev/prod/test/benchmark via the canonical Alembic chain (INFRA-02).

- eval_depth (SmallInteger, nullable): populated from Lichess API metadata when surfaced.
  As of 2026-04-25, the Lichess /api/games/user NDJSON endpoint does NOT expose depth
  per-game (evals=true only adds [%eval] PGN annotations). All Lichess imports leave this
  NULL. Existing prod rows also stay NULL forever (no backfill, D-06).
- eval_source_version (String(50), nullable): constant "lichess-pgn" for Lichess imports;
  NULL for chess.com (chess.com has no eval coverage).

Centipawn convention: signed-from-white-POV, in centipawns (python-chess multiplies the
PGN pawn-unit value by 100). Verified in tests/test_benchmark_ingest.py::test_centipawn_convention.
"""

from alembic import op
import sqlalchemy as sa


revision: str = "b11018499e4f"
down_revision: str | None = "2af113f4790f"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("eval_depth", sa.SmallInteger(), nullable=True))
    op.add_column(
        "games", sa.Column("eval_source_version", sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("games", "eval_source_version")
    op.drop_column("games", "eval_depth")
