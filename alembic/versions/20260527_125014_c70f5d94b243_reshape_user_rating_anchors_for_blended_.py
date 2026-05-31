"""Reshape user_rating_anchors per the D-12 Reversal Amendment (CONTEXT 2026-05-27).

Drops source_platform + chesscom_raw_rating; adds n_chesscom_games,
n_lichess_games, chesscom_median_native, lichess_median_native. TRUNCATEs
user_benchmark_percentiles in the same migration because its rows reference
anchors that no longer exist. Both tables repopulate from Plan 12's backfill.
No data preservation needed (derived tables -- see CONTEXT D-02).

The anchor_source Postgres ENUM type is dropped in this migration because no
column references it after user_rating_anchors is dropped and recreated without
a source_platform column.

Step order in upgrade():
  1. TRUNCATE user_benchmark_percentiles -- derived-table dependency; clear
     before anchor schema changes so no orphan row references survive.
  2. TRUNCATE user_rating_anchors -- clear before dropping (defensive).
  3. DROP TABLE user_rating_anchors -- remove old schema entirely.
  4. DROP CAST IF EXISTS (varchar AS anchor_source) -- implicit cast Plan 02
     created; IF EXISTS for idempotency on partial-rollback DBs.
  5. DROP anchor_source ENUM type -- no remaining column references it.
  6. CREATE TABLE user_rating_anchors -- new blended-anchor schema.

downgrade() is a no-op stub per CONTEXT D-02 sanction for derived tables
(see CONTEXT.md §Amendment §"Migration strategy", locked 2026-05-27):
restoring data requires a full backfill rerun against the prior schema, which
is not reversible via a migration.

Revision ID: c70f5d94b243
Revises: 4c42ebc87b7f
Create Date: 2026-05-27 12:50:14.746432+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c70f5d94b243"
down_revision: Union[str, Sequence[str], None] = "4c42ebc87b7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Cross-reference the existing time_control_bucket Postgres ENUM. The type is
# owned by an earlier migration (see app/models/game.py:33); do NOT recreate it.
time_control_bucket_enum = postgresql.ENUM(
    name="timecontrolbucket",
    create_type=False,
)


def upgrade() -> None:
    """Drop-and-recreate user_rating_anchors per the D-12 Reversal Amendment.

    See module docstring for the rationale and step order.
    """
    # Step 1: TRUNCATE derived-table dependency FIRST. user_benchmark_percentiles
    # rows are keyed on anchors that are about to be destroyed; clearing them
    # avoids orphan data. Plan 12's backfill repopulates both tables.
    op.execute("TRUNCATE TABLE user_benchmark_percentiles")

    # Step 2: TRUNCATE user_rating_anchors before dropping. Defensive: not
    # strictly required when the whole table is dropped, but makes intent explicit
    # and consistent with the pattern in CONTEXT §Amendment §"Migration strategy".
    op.execute("TRUNCATE TABLE user_rating_anchors")

    # Step 3: Drop the old table entirely (removes source_platform,
    # chesscom_raw_rating, n_games columns along with it).
    op.drop_table("user_rating_anchors")

    # Step 4: Drop the implicit varchar->anchor_source cast that Plan 02's
    # migration created. IF EXISTS for idempotency on DBs where the cast was
    # already cleaned up in an earlier partial migration.
    op.execute("DROP CAST IF EXISTS (varchar AS anchor_source)")

    # Step 5: Drop the anchor_source Postgres ENUM type. The type has no
    # remaining column references after Step 3 dropped the only table that
    # used it. checkfirst=True provides idempotency.
    sa.Enum(name="anchor_source").drop(op.get_bind(), checkfirst=True)

    # Step 6: Recreate user_rating_anchors with the blended-anchor column set.
    # New columns vs old schema:
    #   ADDED:   n_chesscom_games INTEGER NOT NULL DEFAULT 0
    #   ADDED:   n_lichess_games  INTEGER NOT NULL DEFAULT 0
    #   ADDED:   chesscom_median_native INTEGER NULL
    #   ADDED:   lichess_median_native  INTEGER NULL
    #   DROPPED: source_platform anchor_source NOT NULL
    #   DROPPED: chesscom_raw_rating INTEGER NULL
    #   DROPPED: n_games INTEGER NOT NULL
    #   UNCHANGED: user_id (PK FK), time_control_bucket (PK), anchor_rating, computed_at
    op.create_table(
        "user_rating_anchors",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("time_control_bucket", time_control_bucket_enum, nullable=False),
        sa.Column("anchor_rating", sa.Integer(), nullable=False),
        sa.Column("n_chesscom_games", sa.Integer(), nullable=False),
        sa.Column("n_lichess_games", sa.Integer(), nullable=False),
        sa.Column("chesscom_median_native", sa.Integer(), nullable=True),
        sa.Column("lichess_median_native", sa.Integer(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "time_control_bucket"),
    )


def downgrade() -> None:
    """No-op stub per CONTEXT D-02 and the D-12 Reversal Amendment (2026-05-27).

    Restoring the pre-amendment schema requires: dropping the new table,
    recreating the anchor_source ENUM, recreating user_rating_anchors with
    source_platform + chesscom_raw_rating + n_games columns, and re-running
    the Stage A / backfill to repopulate. That sequence is destructive and
    out of scope for an Alembic downgrade. Refer to CONTEXT.md §Amendment
    §"Migration strategy" (lines 318-323) for the recovery path.
    """
    pass
