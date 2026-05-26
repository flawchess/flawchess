"""DESTRUCTIVE — backfill required.

Drops user_benchmark_percentiles + benchmark_metric ENUM and recreates with
PK (user_id, metric, time_control_bucket) and 8-value ENUM per Phase 94.4
D-02 + D-13. Recovery via scripts/backfill_user_percentiles.py rerun (Plan 06).

This migration intentionally has no usable downgrade path: per CONTEXT D-02,
this product surface is non-critical and the canonical recovery path is the
backfill script, not a reverse migration. `downgrade()` is a no-op stub.

Per CONTEXT D-13 the new ENUM has exactly 8 values (in order):
    score_gap, achievable_score_gap, section2_score_gap_conv,
    section2_score_gap_parity, recovery_score_gap, time_pressure_score_gap,
    clock_gap, net_flag_rate

`recovery_score_gap` is rescued from the v1 drop list per CONTEXT D-05a
under the peer-relative framing.

Atomic-cutover discipline (D-10a): this migration ships in one squash-merged
PR with Plan 05b (service rewrite) and Plan 05c (API shaper + frontend types).
No interim deploy between 05a and 05b — the legacy interpolate_percentile
stub from Plan 04 is dormant in the interval.

Revision ID: 1945ae56aa20
Revises: fc000b5d0134
Create Date: 2026-05-26 22:26:51.045385+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1945ae56aa20"
down_revision: Union[str, Sequence[str], None] = "fc000b5d0134"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Module-level ENUM descriptors — create_type=False means Alembic controls the
# type lifecycle (we explicitly create/drop in upgrade(); SQLAlchemy never tries
# itself). The model side also uses create_type=False for the same reason
# (see app/models/user_benchmark_percentile.py).
new_benchmark_metric = postgresql.ENUM(
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    name="benchmark_metric",
    create_type=False,
)

# Cross-reference the existing time_control_bucket Postgres ENUM. The type is
# owned by an earlier migration (see app/models/game.py:33); do NOT recreate it.
time_control_bucket_enum = postgresql.ENUM(
    "bullet",
    "blitz",
    "rapid",
    "classical",
    name="timecontrolbucket",
    create_type=False,
)


def upgrade() -> None:
    """Destructively reshape user_benchmark_percentiles + benchmark_metric.

    Step order matters: drop the table FIRST (so no column depends on the
    ENUM), drop the implicit CAST that referenced the old ENUM, then drop the
    ENUM with CASCADE for belt-and-braces safety. Recreate the new 8-value
    ENUM, recreate the CAST, then recreate the table with the widened
    (user_id, metric, time_control_bucket) PK.
    """
    # 1. Drop the existing table.
    op.drop_table("user_benchmark_percentiles")

    # 2. Drop the implicit cast that depended on the old ENUM.
    op.execute("DROP CAST IF EXISTS (varchar AS benchmark_metric)")

    # 3. Drop the old ENUM type via CASCADE. CASCADE is defensive: at this
    # point the only dependent (the table column) was already dropped in
    # step 1, but CASCADE protects against any stray dependency we missed.
    op.execute("DROP TYPE IF EXISTS benchmark_metric CASCADE")

    # 4. Recreate the ENUM with the new 8-value set per CONTEXT D-13.
    new_benchmark_metric.create(op.get_bind(), checkfirst=True)

    # 5. Recreate the implicit varchar→benchmark_metric cast for asyncpg
    # compatibility (see the original add_user_benchmark_percentiles migration
    # for the full rationale — asyncpg sends Python str as varchar in prepared
    # statements; without this cast, raw SQL text inserts fail at runtime
    # even with a valid ENUM label).
    op.execute("CREATE CAST (varchar AS benchmark_metric) WITH INOUT AS IMPLICIT")

    # 6. Recreate the table with the widened PK
    # (user_id, metric, time_control_bucket).
    op.create_table(
        "user_benchmark_percentiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", new_benchmark_metric, nullable=False),
        sa.Column("time_control_bucket", time_control_bucket_enum, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),  # DOUBLE PRECISION
        sa.Column("n_games", sa.Integer(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=True),  # DOUBLE PRECISION NULL
        sa.Column("cdf_snapshot", sa.Date(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "metric", "time_control_bucket"),
    )


def downgrade() -> None:
    """No-op stub per CONTEXT D-02.

    This migration is intentionally forward-only: the table is a derived
    product surface and the canonical recovery path is rerunning the backfill
    script (scripts/backfill_user_percentiles.py, Plan 06) against the empty
    post-migration table. Implementing a true reverse migration would require
    storing the prior shape's data, which is not justified for a non-critical
    surface.
    """
    pass
