"""game_positions composite FK (game_id, user_id) -> games(id, user_id) (SEED-041 item 5)

Revision ID: c8d2e0f3a4b5
Revises: b7c1d9e2f3a4
Create Date: 2026-06-10 18:45:00.000000+00:00

SEED-041 §B1: replace the two single-column FKs on game_positions
(game_id -> games.id, user_id -> users.id) with ONE composite FK
(game_id, user_id) -> games(id, user_id). Two wins:
  1. Halves per-row FK trigger work on COPY import — the 12.7M `users FOR KEY
     SHARE` locks (one of the import path's hidden taxes) disappear; the
     referential chain to users stays intact transitively via
     games.user_id -> users.id (CASCADE).
  2. Strengthens integrity: it enforces that a position's denormalized user_id
     actually matches the owning game's user_id — an invariant the old
     user_id -> users FK did not check at all.

REAL CONSTRAINT NAMES (verified against the live DB; the SEED's assumed
`game_positions_user_id_fkey` was wrong):
  - user_id FK: fk_game_positions_user_id (created in 20260324_185335)
  - game_id FK: game_positions_game_id_fkey (auto-named)

KEPT: ix_game_positions_game_id (index=True on the model's game_id) — it backs
the ON DELETE CASCADE on the positions side and the eval-drain UPDATE. NOT touched.

STRATEGY (prod-safe; CONCURRENTLY + NOT VALID/VALIDATE):
  - Build the unique index games(id, user_id) CONCURRENTLY (the FK target needs a
    unique index; ~20 MB on prod). Required before the FK can be added.
  - ADD CONSTRAINT ... NOT VALID (fast, brief lock — skips the full-table scan),
    then VALIDATE CONSTRAINT (scans without blocking writes). On prod the table is
    ~44M rows; on dev it is instant.
  - Drop the two old FKs (IF EXISTS for retry-safety).

All DDL runs in op.get_context().autocommit_block() because CREATE INDEX
CONCURRENTLY cannot run inside a transaction; the ADD/VALIDATE/DROP statements
each auto-commit there too (prior art: 20260603_153628_f4d88c3659c6).

Literal names/types only — migrations are version-pinned snapshots.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d2e0f3a4b5"
down_revision: str | None = "b7c1d9e2f3a4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add the composite FK (game_id, user_id) -> games(id, user_id); drop the two old FKs."""
    with op.get_context().autocommit_block():
        # FK target: a unique index on (id, user_id). CONCURRENTLY, non-blocking.
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_games_id_user_id "
            "ON games (id, user_id)"
        )
        # Add NOT VALID first (fast), then validate (non-blocking scan).
        op.execute(
            "ALTER TABLE game_positions ADD CONSTRAINT game_positions_game_user_fkey "
            "FOREIGN KEY (game_id, user_id) REFERENCES games (id, user_id) "
            "ON DELETE CASCADE NOT VALID"
        )
        op.execute("ALTER TABLE game_positions VALIDATE CONSTRAINT game_positions_game_user_fkey")
        # Drop the two superseded single-column FKs.
        op.execute("ALTER TABLE game_positions DROP CONSTRAINT IF EXISTS game_positions_game_id_fkey")
        op.execute("ALTER TABLE game_positions DROP CONSTRAINT IF EXISTS fk_game_positions_user_id")


def downgrade() -> None:
    """Restore the two single-column FKs; drop the composite FK + its unique index."""
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TABLE game_positions ADD CONSTRAINT game_positions_game_id_fkey "
            "FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE"
        )
        op.execute(
            "ALTER TABLE game_positions ADD CONSTRAINT fk_game_positions_user_id "
            "FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE"
        )
        op.execute(
            "ALTER TABLE game_positions DROP CONSTRAINT IF EXISTS game_positions_game_user_fkey"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_games_id_user_id")
