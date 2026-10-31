"""opening-out metrics and percentile colour

Revision ID: b7e4c2a9f013
Revises: 5448f030de58
Create Date: 2026-10-31 12:00:00.000000+00:00

Phase 243 (SEED-206 "out of the opening" worse/better rates), storage side.

1. ``metric`` on ``user_benchmark_percentiles`` and ``benchmark_cohort_cdf`` moves from
   the native ``benchmark_metric`` ENUM to TEXT + CHECK over the 13 live CdfMetricId
   values (root CLAUDE.md: avoid native ENUMs, align existing columns when touched).
   Adding the two new ids to a native ENUM would have needed ``ALTER TYPE ADD VALUE``
   and every future id another one; with a CHECK the model derives the allowed set
   from ``typing.get_args(CdfMetricId)``.
2. ``user_benchmark_percentiles`` gains ``color`` TEXT NOT NULL DEFAULT 'all' with a
   CHECK ('all' | 'white' | 'black') and a 4-column PK
   ``(user_id, metric, time_control_bucket, color)``. ``'all'`` is the colour-agnostic
   row every Endgames family writes; ``'white'`` / ``'black'`` are the per-colour
   opening rows. The CDF stays colour-pooled (D-04), so ``benchmark_cohort_cdf`` has no
   colour column.

The ENUM-to-TEXT conversion is rated "costly" (not "one-way"): the downgrade recreates
the ENUM and casts back. Only rows on dead labels are unrecoverable. The 12 TC-suffixed
labels (``conversion_rate_bullet`` ...) were added and superseded within one PR and are
never written by the current code path; the upgrade deletes any such row before adding
the CHECK (so a deploy never fails on a dead label) and logs the deleted count per
table, so the deletion is never silent.

The value lists below are frozen literals: a migration is a standalone artifact and
must not import live application code.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4c2a9f013"
down_revision: Union[str, Sequence[str], None] = "5448f030de58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_logger = logging.getLogger("alembic.runtime.migration")

# The 13 CdfMetricId values after Phase 243.
_METRIC_VALUES: tuple[str, ...] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
    "opening_worse_rate",
    "opening_better_rate",
)
_OPENING_OUT_VALUES: tuple[str, ...] = ("opening_worse_rate", "opening_better_rate")

# The 23 labels of the benchmark_metric ENUM before this migration, in the order the
# model listed them (8 families, 12 TC-suffixed rate labels, 3 bare rate families).
_LEGACY_ENUM_LABELS: tuple[str, ...] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    "conversion_rate_bullet",
    "conversion_rate_blitz",
    "conversion_rate_rapid",
    "conversion_rate_classical",
    "parity_rate_bullet",
    "parity_rate_blitz",
    "parity_rate_rapid",
    "parity_rate_classical",
    "recovery_rate_bullet",
    "recovery_rate_blitz",
    "recovery_rate_rapid",
    "recovery_rate_classical",
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
)
_COLOR_VALUES: tuple[str, ...] = ("all", "white", "black")

_USER_TABLE = "user_benchmark_percentiles"
_CDF_TABLE = "benchmark_cohort_cdf"
_METRIC_CHECK_USER = "ck_user_benchmark_percentiles_metric"
_METRIC_CHECK_CDF = "ck_benchmark_cohort_cdf_metric"
_COLOR_CHECK = "ck_user_benchmark_percentiles_color"
_PK_NAME = "user_benchmark_percentiles_pkey"


def _sql_in(values: Sequence[str]) -> str:
    """Render ``('a', 'b', ...)`` from the frozen literal tuples above (no user input)."""
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def _delete_rows_outside_metric_set() -> None:
    """Delete rows whose metric is not a live id; log each non-zero count (never silent)."""
    bind = op.get_bind()
    for table in (_USER_TABLE, _CDF_TABLE):
        result = bind.execute(
            sa.text(f"DELETE FROM {table} WHERE metric::text NOT IN {_sql_in(_METRIC_VALUES)}")
        )
        if result.rowcount:
            _logger.warning(
                "Deleted %s rows with a dead benchmark_metric label from %s",
                result.rowcount,
                table,
            )


def upgrade() -> None:
    """ENUM -> TEXT + CHECK on both tables, then add the colour column and the 4-column PK."""
    _delete_rows_outside_metric_set()

    for table in (_USER_TABLE, _CDF_TABLE):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN metric TYPE text USING metric::text")
    # The implicit varchar -> benchmark_metric cast (created for asyncpg) depends on the
    # type and must go first; a TEXT column needs no cast.
    op.execute("DROP CAST IF EXISTS (varchar AS benchmark_metric)")
    op.execute("DROP TYPE benchmark_metric")

    op.create_check_constraint(
        _METRIC_CHECK_USER, _USER_TABLE, f"metric IN {_sql_in(_METRIC_VALUES)}"
    )
    op.create_check_constraint(
        _METRIC_CHECK_CDF, _CDF_TABLE, f"metric IN {_sql_in(_METRIC_VALUES)}"
    )

    op.add_column(
        _USER_TABLE,
        sa.Column("color", sa.Text(), nullable=False, server_default="all"),
    )
    op.create_check_constraint(_COLOR_CHECK, _USER_TABLE, f"color IN {_sql_in(_COLOR_VALUES)}")

    op.drop_constraint(_PK_NAME, _USER_TABLE, type_="primary")
    op.create_primary_key(
        _PK_NAME, _USER_TABLE, ["user_id", "metric", "time_control_bucket", "color"]
    )


def downgrade() -> None:
    """Reverse: 3-column PK, drop colour rows, restore the ENUM and cast back."""
    op.drop_constraint(_PK_NAME, _USER_TABLE, type_="primary")
    # A 3-column PK cannot hold per-colour rows: they are derived data (Stage B
    # recomputes them), so they are dropped.
    op.execute(f"DELETE FROM {_USER_TABLE} WHERE color <> 'all'")
    op.drop_constraint(_COLOR_CHECK, _USER_TABLE, type_="check")
    op.drop_column(_USER_TABLE, "color")
    op.create_primary_key(_PK_NAME, _USER_TABLE, ["user_id", "metric", "time_control_bucket"])

    # The opening ids do not exist in the old ENUM; their rows are derived data too.
    for table in (_USER_TABLE, _CDF_TABLE):
        op.execute(f"DELETE FROM {table} WHERE metric IN {_sql_in(_OPENING_OUT_VALUES)}")
    op.drop_constraint(_METRIC_CHECK_USER, _USER_TABLE, type_="check")
    op.drop_constraint(_METRIC_CHECK_CDF, _CDF_TABLE, type_="check")

    op.execute(f"CREATE TYPE benchmark_metric AS ENUM {_sql_in(_LEGACY_ENUM_LABELS)}")
    op.execute("CREATE CAST (varchar AS benchmark_metric) WITH INOUT AS IMPLICIT")
    for table in (_USER_TABLE, _CDF_TABLE):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN metric TYPE benchmark_metric "
            "USING metric::benchmark_metric"
        )
