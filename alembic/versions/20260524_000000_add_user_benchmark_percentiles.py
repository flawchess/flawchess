"""Add user_benchmark_percentiles table and benchmark_metric ENUM type.

This is FlawChess's first new Postgres ENUM type since the 2026-04-08
enum-conversion migration. The 4-value set mirrors ``CdfMetricId`` Literal in
``app/services/global_percentile_cdf.py``; future metric extensions require
``ALTER TYPE benchmark_metric ADD VALUE 'new_metric'`` in a follow-up
migration. See CONTEXT.md D-05.

Phase 94.1 Plan 04 — PCTL-08: persistent home for canonical-slice values +
percentiles. Composite PK (user_id, metric) — exactly one row per user per
metric at all times; recompute is UPSERT.

Revision ID: 82a2b6d4888f
Revises: bd54be3a66bf
Create Date: 2026-05-24 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "82a2b6d4888f"
down_revision: Union[str, Sequence[str], None] = "bd54be3a66bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Module-level ENUM descriptor — create_type=False means Alembic controls the
# lifecycle (create in upgrade, drop in downgrade). The model side also uses
# create_type=False for the same reason (see app/models/user_benchmark_percentile.py).
benchmark_metric_enum = postgresql.ENUM(
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    name="benchmark_metric",
    create_type=False,
)


def upgrade() -> None:
    """Create benchmark_metric ENUM type then user_benchmark_percentiles table.

    ORDER MATTERS (RESEARCH Pitfall 3): the ENUM type must be created BEFORE the
    table that references it — Postgres rejects a CREATE TABLE that references a
    type that doesn't yet exist.

    Also creates an implicit CAST from varchar to benchmark_metric. asyncpg
    sends Python ``str`` bind parameters as ``varchar`` in prepared statements; without
    this cast, raw SQL text inserts (e.g. in tests) fail with a type-mismatch
    error even though the string value is a valid ENUM label. The CAST is safe:
    invalid strings still raise a Postgres error at runtime; it only removes the
    manual ``::benchmark_metric`` cast requirement at the prepared-statement level.
    """
    # Step 1: create the ENUM type first
    benchmark_metric_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: add implicit varchar→benchmark_metric cast for asyncpg compatibility
    op.execute("CREATE CAST (varchar AS benchmark_metric) WITH INOUT AS IMPLICIT")

    # Step 3: create the table referencing the type
    op.create_table(
        "user_benchmark_percentiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", benchmark_metric_enum, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),  # DOUBLE PRECISION
        sa.Column("percentile", sa.Float(), nullable=True),  # DOUBLE PRECISION NULL
        sa.Column("n_games", sa.Integer(), nullable=False),
        sa.Column("cdf_snapshot", sa.Date(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "metric"),
    )


def downgrade() -> None:
    """Drop user_benchmark_percentiles table then benchmark_metric ENUM type.

    ORDER MATTERS (RESEARCH Pitfall 4): the table must be dropped BEFORE the type —
    Postgres refuses ``DROP TYPE benchmark_metric`` while any column still references
    it (``cannot drop type benchmark_metric because column ... depends on it``).

    Also drops the implicit varchar→benchmark_metric cast before dropping the type.
    """
    # Step 1: drop the table first
    op.drop_table("user_benchmark_percentiles")

    # Step 2: drop the implicit cast before dropping the type
    op.execute("DROP CAST IF EXISTS (varchar AS benchmark_metric)")

    # Step 3: drop the type after the referencing column and cast are gone
    benchmark_metric_enum.drop(op.get_bind(), checkfirst=True)
