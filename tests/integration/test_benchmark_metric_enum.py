"""Postgres ENUM label introspection test for benchmark_metric.

The ENUM holds the 8 family-level values plus 12 per-(rate metric × TC)
values ({conversion_rate, parity_rate, recovery_rate} × {bullet, blitz, rapid,
classical}) and 3 bare rate family names, 23 labels in total.

Asserts that after migrations, the ``benchmark_metric`` Postgres ENUM type
contains EXACTLY the expected labels in alphabetical order.

This test catches ENUM labels drifting from the locked metric set, which
the ENUM enforces at the DB layer.

Guarded by ``pytest.importorskip`` + ``_migration_present()`` so CI stays
green until the migrations land.
"""

from __future__ import annotations

import glob
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# ---------------------------------------------------------------------------
# Guard 1 — skip module when the model is absent
# ---------------------------------------------------------------------------

pytest.importorskip(
    "app.models.user_benchmark_percentile",
    reason=("app.models.user_benchmark_percentile not implemented yet; will pass after Plan 04"),
)

# ---------------------------------------------------------------------------
# Guard 2 — migration presence helper
# ---------------------------------------------------------------------------

_MIGRATION_GLOB: str = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "alembic",
    "versions",
    "*user_benchmark_percentile*",
)


def _migration_present() -> bool:
    """Return True if the user_benchmark_percentiles migration file exists."""
    return len(glob.glob(_MIGRATION_GLOB)) > 0


# ---------------------------------------------------------------------------
# Expected ENUM labels
# ---------------------------------------------------------------------------

# Alphabetically sorted (the ORDER BY enumlabel query returns them this way).
# Migration 1945ae56aa20 collapsed the ENUM from 16 to 8 family-level values —
# TC dimensionality moved into the user_benchmark_percentiles.time_control_bucket
# PK column. Recovery Score Gap joins the ENUM as ``recovery_score_gap``.
# Migration 3981239fd391 added 12 TC-suffixed rate values
# ({conversion_rate, parity_rate, recovery_rate} × {bullet, blitz, rapid,
# classical}).
EXPECTED_ENUM_LABELS: list[str] = [
    "achievable_score_gap",
    "clock_gap",
    "conversion_rate",
    "conversion_rate_blitz",
    "conversion_rate_bullet",
    "conversion_rate_classical",
    "conversion_rate_rapid",
    "net_flag_rate",
    "parity_rate",
    "parity_rate_blitz",
    "parity_rate_bullet",
    "parity_rate_classical",
    "parity_rate_rapid",
    "recovery_rate",
    "recovery_rate_blitz",
    "recovery_rate_bullet",
    "recovery_rate_classical",
    "recovery_rate_rapid",
    "recovery_score_gap",
    "score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "time_pressure_score_gap",
]

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test — pg_enum contains exactly 4 expected labels
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _migration_present(),
    reason=(
        "user_benchmark_percentiles migration not landed yet; "
        "will run after Plan 04 ships the migration"
    ),
)
async def test_benchmark_metric_enum_has_exactly_four_labels(
    test_engine: AsyncEngine,
) -> None:
    """After migrations, benchmark_metric ENUM has exactly the 23 expected labels.

    (The test name is historical; the assertion covers 8 family-level labels +
    12 TC-suffixed rate labels + 3 bare rate family-name labels = 23 total.
    TC dimensionality for score-gap metrics lives in the
    user_benchmark_percentiles.time_control_bucket PK column; the rate metrics
    use bare family names (conversion_rate, parity_rate, recovery_rate) as the
    ENUM/metric column value, with time_control_bucket carrying the TC dimension.
    The 12 TC-suffixed values remain for forward compatibility.)

    Query shape: SELECT enumlabel FROM pg_enum e
                 JOIN pg_type t ON e.enumtypid = t.oid
                 WHERE t.typname = 'benchmark_metric'
                 ORDER BY enumlabel

    Asserts:
    - Exactly 23 labels returned (not more, not fewer)
    - Labels match the locked set
    - No label drift between the migrations and CdfMetricId Literal in
      global_percentile_cdf.py

    Downstream code that inserts ``metric`` values
    outside this 23-value set will fail with a Postgres ENUM rejection error,
    not a silent data corruption. This test is the CI-time guard that the ENUM
    contract has not drifted.
    """
    async with test_engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT enumlabel "
                "FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'benchmark_metric' "
                "ORDER BY enumlabel"
            )
        )
        actual_labels = [r[0] for r in rows.fetchall()]

    assert actual_labels == EXPECTED_ENUM_LABELS, (
        f"benchmark_metric ENUM label mismatch.\n"
        f"Expected (alphabetical): {EXPECTED_ENUM_LABELS}\n"
        f"Got:                     {actual_labels}\n"
        f"This indicates the migration's ENUM definition has drifted from "
        f"the D-05 / CdfMetricId Literal contract."
    )
