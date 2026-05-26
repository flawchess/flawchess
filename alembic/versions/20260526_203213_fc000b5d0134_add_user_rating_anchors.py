"""Add user_rating_anchors table per Phase 94.4 D-04.

Stores per-(user, TC) rating anchors populated by Stage A at import time.
Lichess-precedence rule (D-12) lives in the Python wrapper (Plan 05), not in
this migration. The ``anchor_source`` Postgres ENUM has exactly two values
(``lichess`` / ``chesscom``); the ENUM lifecycle is owned by this migration
(``create_type=False`` on the model side) per project precedent
(``app/models/user_benchmark_percentile.py``).

Three-step upgrade (RESEARCH Pitfall 3 — order matters):
  1. Create the ``anchor_source`` ENUM type via the module-level descriptor.
  2. Add an implicit ``CAST (varchar AS anchor_source) WITH INOUT AS IMPLICIT``
     so asyncpg's prepared-statement varchar binds round-trip without manual
     ``::anchor_source`` casts (mirrors the user_benchmark_percentiles migration).
  3. Create the table referencing the type. The ``time_control_bucket`` ENUM
     is cross-referenced via ``postgresql.ENUM(name='time_control_bucket',
     create_type=False)`` — it was created by an earlier migration and MUST
     NOT be recreated here.

Three-step downgrade (RESEARCH Pitfall 4 — reverse order):
  1. Drop the table (must precede DROP TYPE because the column depends on it).
  2. Drop the implicit CAST.
  3. Drop the ENUM type.

The ``chesscom_raw_rating`` column is nullable per D-07 bullet 4: populated
only when ``source_platform = 'chesscom'`` to disclose conversion provenance
in the tooltip; NULL when ``source_platform = 'lichess'``.

Revision ID: fc000b5d0134
Revises: fd5b551f381c
Create Date: 2026-05-26 20:32:13.827158+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fc000b5d0134"
down_revision: Union[str, Sequence[str], None] = "fd5b551f381c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Module-level ENUM descriptors — create_type=False so SQLAlchemy never
# attempts CREATE/DROP TYPE outside our explicit .create()/.drop() calls.
#
# anchor_source: NEW type created by this migration.
anchor_source_enum = postgresql.ENUM(
    "lichess",
    "chesscom",
    name="anchor_source",
    create_type=False,
)

# timecontrolbucket: EXISTING type created by an earlier migration. We
# reference it by name only and MUST NOT call .create() on it here — that
# would raise DuplicateObject in production. Note the Postgres type name is
# ``timecontrolbucket`` (no underscores; defined in app/models/game.py:33-40
# as SAEnum(..., name="timecontrolbucket")).
time_control_bucket_enum = postgresql.ENUM(
    name="timecontrolbucket",
    create_type=False,
)


def upgrade() -> None:
    """Create anchor_source ENUM, implicit CAST, then user_rating_anchors table.

    ORDER MATTERS (RESEARCH Pitfall 3): the ENUM type must be created BEFORE
    the table that references it — Postgres rejects a CREATE TABLE that
    references a type that doesn't yet exist.
    """
    # Step 1: create the anchor_source ENUM type.
    anchor_source_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: add implicit varchar→anchor_source cast for asyncpg compatibility.
    # asyncpg sends Python ``str`` bind parameters as varchar in prepared
    # statements; without this cast, raw SQL text inserts fail with a
    # type-mismatch even though the string is a valid ENUM label.
    op.execute("CREATE CAST (varchar AS anchor_source) WITH INOUT AS IMPLICIT")

    # Step 3: create the table. time_control_bucket_enum is cross-referenced
    # by name only — no .create() call (the type already exists).
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
        sa.Column("source_platform", anchor_source_enum, nullable=False),
        sa.Column("chesscom_raw_rating", sa.Integer(), nullable=True),
        sa.Column("n_games", sa.Integer(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "time_control_bucket"),
    )


def downgrade() -> None:
    """Drop user_rating_anchors table, implicit CAST, then anchor_source ENUM.

    ORDER MATTERS (RESEARCH Pitfall 4): the table must be dropped BEFORE the
    type — Postgres refuses DROP TYPE while any column still references it.
    """
    # Step 1: drop the table.
    op.drop_table("user_rating_anchors")

    # Step 2: drop the implicit cast before dropping the type.
    op.execute("DROP CAST IF EXISTS (varchar AS anchor_source)")

    # Step 3: drop the anchor_source ENUM type. time_control_bucket_enum is
    # NOT dropped — it remains in use by other tables.
    anchor_source_enum.drop(op.get_bind(), checkfirst=True)
