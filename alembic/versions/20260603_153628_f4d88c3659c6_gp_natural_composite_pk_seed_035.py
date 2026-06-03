"""gp natural composite pk (SEED-035)

Revision ID: f4d88c3659c6
Revises: 84fd28051d7d
Create Date: 2026-06-03 15:36:28.991618+00:00

SEED-035: replace the surrogate `game_positions.id` integer PK with the natural
composite PK (user_id, game_id, ply), and drop the now-redundant
`ix_gp_user_game_ply` index. The natural key is provably unique (36.5M rows =
36.5M distinct (game_id, ply) pairs), and the surrogate pkey index is ~1.3 GB
on prod with zero genuine scans and no inbound FKs, so reclaiming it is a clear
win.

WHY THE SEED's "PROMOTE ix_gp_user_game_ply IN PLACE" APPROACH IS NOT USED:
the seed proposed `ADD CONSTRAINT ... PRIMARY KEY USING INDEX ix_gp_user_game_ply`.
That is impossible: `ix_gp_user_game_ply` is a *partial* index
(WHERE ply BETWEEN 0 AND 17) WITH INCLUDE(full_hash, move_san). A PRIMARY KEY
requires a NON-partial unique index over exactly the key columns, so USING INDEX
cannot adopt it. The PK index is therefore built fresh (Step A below).

MIGRATION STRATEGY (two-phase, prod-safe; mirrors the autocommit_block prior art
in 20260601_154355_84fd28051d7d):
  Step 0: pre-drop FK guard — abort loudly if any inbound FK references
          game_positions.id (today none exist, verified in SEED-035; this guards
          a future schema addition from silently breaking on the prod run).
  Step A: build a fresh NON-partial UNIQUE index CONCURRENTLY over the full key
          (user_id, game_id, ply). On dev/test this is instant; on prod it is the
          ~500 MB build the seed flagged. CONCURRENTLY keeps it non-blocking and
          table-rewrite-free.
  Step B: drop the surrogate PK and adopt the new unique index as the PK via
          ADD CONSTRAINT ... PRIMARY KEY USING INDEX (a fast catalog op that takes
          a brief ACCESS EXCLUSIVE lock — acceptable — and renames the index to
          game_positions_pkey, avoiding a second index build).
  Step C: drop the surrogate `id` column.
  Step D: drop the now-redundant `ix_gp_user_game_ply` CONCURRENTLY (its
          (user_id, game_id, ply) key is absorbed by the new PK; the
          partial/INCLUDE specialization is acceptable to retire per SEED-035).

KEPT INTENTIONALLY: `ix_game_positions_game_id`. It backs the ON DELETE CASCADE
FK game_positions_game_id_fkey and is the more-used index (467k scans). This
migration does NOT touch it. Its prod-side bloat is reclaimed SEPARATELY by the
human-run ops script scripts/reindex_table.py (SEED-035 "quick win"),
NOT by this migration.

TRANSACTION / CONCURRENTLY RECONCILIATION: CREATE/DROP INDEX CONCURRENTLY cannot
run inside a transaction block. All DDL here runs inside ONE
`op.get_context().autocommit_block()`, which opens a raw connection without a
surrounding BEGIN so each statement auto-commits. The plain-DDL promotion
(DROP/ADD CONSTRAINT) and drop_column live inside the same autocommit_block and
are ordered AFTER the index build so the PK exists before the old index is
dropped. One structure, one block — simplest correct shape.

DEV vs PROD scope: on the dev/test DB the table is tiny so every operation is
instant and the CONCURRENTLY build is trivial. The prod run against 36.5M rows
needs the ~500 MB CONCURRENTLY index build timed against a prod-sized dataset and
is a DEPLOY-time / HUMAN-UAT concern — it is NOT validated by this migration's
dev round-trip, and completion does not depend on prod timing.

downgrade() is a DEV-ONLY escape hatch — it re-densifies the table (repopulates a
fresh surrogate id) and is NOT expected to run on prod.

Literal int / explicit column types only — migrations are version-pinned
snapshots and must NOT import live app constants (project rule). The
ix_gp_user_game_ply partial predicate + INCLUDE list recreated in downgrade is a
copy of the definition in app/models/game_position.py as of this migration.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4d88c3659c6"
down_revision: str | None = "84fd28051d7d"
branch_labels: str | None = None
depends_on: str | None = None


# Pre-drop FK guard (Step 0): abort the migration if any inbound FK references
# the surrogate game_positions.id column. Today the result is empty (verified in
# SEED-035), but this protects a future prod run from silently breaking if a new
# FK to game_positions.id is ever added before this migration ships.
_FK_GUARD_SQL = """
DO $$
DECLARE
    offending text;
BEGIN
    SELECT string_agg(conrelid::regclass::text || '.' || conname, ', ')
      INTO offending
      FROM pg_constraint c
      JOIN pg_attribute a
        ON a.attrelid = c.confrelid
       AND a.attnum = ANY (c.confkey)
     WHERE c.contype = 'f'
       AND c.confrelid = 'game_positions'::regclass
       AND a.attname = 'id';
    IF offending IS NOT NULL THEN
        RAISE EXCEPTION
            'SEED-035 migration aborted: inbound FK(s) reference game_positions.id (%). '
            'Drop or repoint them before dropping the surrogate PK.', offending;
    END IF;
END $$;
"""


def upgrade() -> None:
    """Replace surrogate id PK with composite (user_id, game_id, ply); drop ix_gp_user_game_ply."""
    # Step 0: fail loudly if any inbound FK still references game_positions.id.
    op.execute(_FK_GUARD_SQL)

    # CONCURRENTLY cannot run inside a transaction; autocommit_block opens a raw
    # connection without a surrounding BEGIN. The plain-DDL promotion + drop_column
    # below also live here (each statement auto-commits) and run AFTER the index
    # build so the PK exists before the old surrogate pkey/id are removed.
    with op.get_context().autocommit_block():
        # Step A: build a fresh NON-partial UNIQUE index over the full natural key.
        # (ix_gp_user_game_ply cannot be promoted in place — it is partial + INCLUDE.)
        op.create_index(
            "uq_gp_user_game_ply",
            "game_positions",
            ["user_id", "game_id", "ply"],
            unique=True,
            postgresql_concurrently=True,
        )

        # Step B: drop the surrogate PK and adopt the fresh unique index as the new
        # PK. USING INDEX renames uq_gp_user_game_ply -> game_positions_pkey with no
        # second index build (brief ACCESS EXCLUSIVE lock — acceptable).
        op.execute("ALTER TABLE game_positions DROP CONSTRAINT game_positions_pkey")
        op.execute(
            "ALTER TABLE game_positions "
            "ADD CONSTRAINT game_positions_pkey PRIMARY KEY USING INDEX uq_gp_user_game_ply"
        )

        # Step C: drop the surrogate id column (now unreferenced).
        op.drop_column("game_positions", "id")

        # Step D: drop the redundant partial+INCLUDE index. Its (user_id, game_id,
        # ply) key is absorbed by the new composite PK; the ply BETWEEN 0 AND 17 /
        # INCLUDE(full_hash, move_san) specialization is acceptable to retire
        # (SEED-035 "design"). KEEP ix_game_positions_game_id — not touched here.
        op.drop_index(
            "ix_gp_user_game_ply",
            table_name="game_positions",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    """DEV-ONLY reverse: re-add surrogate id PK, recreate ix_gp_user_game_ply.

    Re-densifies the table by repopulating a fresh BIGINT identity id. NOT
    expected to run on prod.
    """
    with op.get_context().autocommit_block():
        # Recreate the redundant partial+INCLUDE index first (copy of the ORM
        # definition as of this migration). Non-unique, partial WHERE ply BETWEEN
        # 0 AND 17, INCLUDE(full_hash, move_san).
        op.create_index(
            "ix_gp_user_game_ply",
            "game_positions",
            ["user_id", "game_id", "ply"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 0 AND 17"),
            postgresql_include=["full_hash", "move_san"],
        )

        # Drop the composite PK constraint (this drops game_positions_pkey, which
        # was the renamed uq_gp_user_game_ply unique index).
        op.execute("ALTER TABLE game_positions DROP CONSTRAINT game_positions_pkey")

        # Re-add the surrogate id column as a BIGINT identity and rebuild the
        # surrogate PK on it. GENERATED ... AS IDENTITY repopulates every existing
        # row with a fresh sequential id (re-densifies the table).
        op.execute(
            "ALTER TABLE game_positions "
            "ADD COLUMN id BIGINT GENERATED BY DEFAULT AS IDENTITY NOT NULL"
        )
        op.execute("ALTER TABLE game_positions ADD CONSTRAINT game_positions_pkey PRIMARY KEY (id)")
