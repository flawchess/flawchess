"""partial-index hash columns at ply<=28 (SEED-033)

Revision ID: 84fd28051d7d
Revises: 02099d78ce65
Create Date: 2026-06-01 15:43:55.503650+00:00

SEED-033: Rebuild the three Zobrist-hash indexes on game_positions as partial
indexes (WHERE ply <= 28) to reclaim ~3 GB of index footprint. The explorer
is hard-capped at ply 28 (MAX_EXPLORER_PLY in app/models/game_position.py),
so no hash lookup can ever target a position past the boundary -- the win is
unconditional.

CONCURRENTLY note: CREATE/DROP INDEX CONCURRENTLY cannot run inside a
transaction. All DDL here is wrapped in op.get_context().autocommit_block()
which opens a raw connection without a surrounding BEGIN. See Alembic cookbook
and the prior art in alembic/versions/20260426_201533_80e22b38993a_...py.

Temp-name + rename trick: to avoid a name clash while both old (full) and new
(partial) indexes coexist, the new index is built under a _partial suffix, then
the old index is dropped CONCURRENTLY (fast -- no ACCESS EXCLUSIVE), then the
new index is renamed to the canonical name via ALTER INDEX (catalog-only op,
safe outside CONCURRENTLY). The final names match app/models/game_position.py
so Alembic autogenerate sees no drift.

Literal 28 vs constant: migration files are version-pinned snapshots and must
NOT import live app constants that can drift. The literal 28 here must stay
equal to MAX_EXPLORER_PLY in app/models/game_position.py. If the cap changes,
write a new migration rather than editing this one (already-applied migrations
are immutable snapshots).

Affected indexes:
  ix_gp_user_full_hash_move_san  (user_id, full_hash, move_san)
  ix_gp_user_white_hash          (user_id, white_hash)
  ix_gp_user_black_hash          (user_id, black_hash)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "84fd28051d7d"
down_revision: str | None = "02099d78ce65"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Rebuild three hash indexes as partial WHERE ply <= 28."""
    # CONCURRENTLY cannot run inside a transaction; autocommit_block opens a
    # raw connection without a surrounding BEGIN. See Alembic cookbook.
    with op.get_context().autocommit_block():
        # --- ix_gp_user_full_hash_move_san ---
        # Step 1: build new partial index under a temp name (no clash with existing)
        op.create_index(
            "ix_gp_user_full_hash_move_san_partial",
            "game_positions",
            ["user_id", "full_hash", "move_san"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply <= 28"),
        )
        # Step 2: drop the old full index CONCURRENTLY
        op.drop_index(
            "ix_gp_user_full_hash_move_san",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        # Step 3: rename new partial index to canonical name (fast catalog-only op)
        op.execute(
            'ALTER INDEX "ix_gp_user_full_hash_move_san_partial" '
            'RENAME TO "ix_gp_user_full_hash_move_san"'
        )

        # --- ix_gp_user_white_hash ---
        op.create_index(
            "ix_gp_user_white_hash_partial",
            "game_positions",
            ["user_id", "white_hash"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply <= 28"),
        )
        op.drop_index(
            "ix_gp_user_white_hash",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        op.execute(
            'ALTER INDEX "ix_gp_user_white_hash_partial" '
            'RENAME TO "ix_gp_user_white_hash"'
        )

        # --- ix_gp_user_black_hash ---
        op.create_index(
            "ix_gp_user_black_hash_partial",
            "game_positions",
            ["user_id", "black_hash"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply <= 28"),
        )
        op.drop_index(
            "ix_gp_user_black_hash",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        op.execute(
            'ALTER INDEX "ix_gp_user_black_hash_partial" '
            'RENAME TO "ix_gp_user_black_hash"'
        )


def downgrade() -> None:
    """Reverse: rebuild full (non-partial) indexes, drop partial ones."""
    # Same CONCURRENTLY + temp-name + rename pattern as upgrade.
    with op.get_context().autocommit_block():
        # --- ix_gp_user_full_hash_move_san ---
        op.create_index(
            "ix_gp_user_full_hash_move_san_full",
            "game_positions",
            ["user_id", "full_hash", "move_san"],
            unique=False,
            postgresql_concurrently=True,
            # No postgresql_where -- restores full (non-partial) index
        )
        op.drop_index(
            "ix_gp_user_full_hash_move_san",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        op.execute(
            'ALTER INDEX "ix_gp_user_full_hash_move_san_full" '
            'RENAME TO "ix_gp_user_full_hash_move_san"'
        )

        # --- ix_gp_user_white_hash ---
        op.create_index(
            "ix_gp_user_white_hash_full",
            "game_positions",
            ["user_id", "white_hash"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_gp_user_white_hash",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        op.execute(
            'ALTER INDEX "ix_gp_user_white_hash_full" '
            'RENAME TO "ix_gp_user_white_hash"'
        )

        # --- ix_gp_user_black_hash ---
        op.create_index(
            "ix_gp_user_black_hash_full",
            "game_positions",
            ["user_id", "black_hash"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_gp_user_black_hash",
            table_name="game_positions",
            postgresql_concurrently=True,
        )
        op.execute(
            'ALTER INDEX "ix_gp_user_black_hash_full" '
            'RENAME TO "ix_gp_user_black_hash"'
        )
