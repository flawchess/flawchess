"""add benchmark_cohort_cdf

Schema-only migration that creates the ``benchmark_cohort_cdf`` table.
LONG layout per CONTEXT D-01: one row per breakpoint, composite PK
(metric, anchor_elo, tc, percentile). ~130k rows after seeding by Plan 03.

Both ENUM types (``benchmark_metric``, ``timecontrolbucket``) are referenced
by name only via ``postgresql.ENUM(..., create_type=False)`` so this migration
does NOT attempt to CREATE or DROP them — they are owned by earlier migrations.
This mirrors the pattern in ``fc000b5d0134_add_user_rating_anchors.py`` which
cross-references ``timecontrolbucket`` the same way.

SCHEMA ONLY — no data rows written here. Seeding is ``scripts/seed_cohort_cdf.py``'s job.

Downgrade drops only ``benchmark_cohort_cdf``; it does NOT touch the shared
ENUMs (T-99.1-01 mitigation: downgrade must not break other tables).

Revision ID: d0a962b51c68
Revises: 52c928794fe7
Create Date: 2026-05-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d0a962b51c68"
down_revision: str | Sequence[str] | None = "52c928794fe7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# EXISTING ENUM types — referenced by name only, create_type=False so the
# migration never emits CREATE TYPE (both types are owned by earlier migrations).
# benchmark_metric: first created by 20260524_000000_add_user_benchmark_percentiles.py,
#   extended by 20260530_extend_benchmark_metric_for_rate_percentiles.py and
#   20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py.
# timecontrolbucket: first created by the initial games migration; cross-
#   referenced by name as per the fc000b5d0134_add_user_rating_anchors.py precedent.
_benchmark_metric = postgresql.ENUM(name="benchmark_metric", create_type=False)
_timecontrolbucket = postgresql.ENUM(name="timecontrolbucket", create_type=False)


def upgrade() -> None:
    """Create benchmark_cohort_cdf table (schema-only, no data)."""
    op.create_table(
        "benchmark_cohort_cdf",
        sa.Column("metric", _benchmark_metric, nullable=False),
        sa.Column("anchor_elo", sa.SmallInteger(), nullable=False),
        sa.Column("tc", _timecontrolbucket, nullable=False),
        sa.Column("percentile", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Double(), nullable=False),
        sa.Column("n_users", sa.Integer(), nullable=True),
        sa.Column("snapshot_month", sa.String(length=7), nullable=True),
        sa.PrimaryKeyConstraint("metric", "anchor_elo", "tc", "percentile"),
    )


def downgrade() -> None:
    """Drop benchmark_cohort_cdf table only; shared ENUMs are not touched."""
    op.drop_table("benchmark_cohort_cdf")
