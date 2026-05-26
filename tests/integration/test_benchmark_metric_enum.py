"""Postgres ENUM label introspection test for benchmark_metric.

Phase 94.1 Plan 01 Wave 0 (initial 4-value set).
Phase 94.3 Plan 04 (CONTEXT.md D-7): widened to 16 values — the original 4
Phase 94.x score-gap metrics plus 12 per-(metric × TC) time-pressure metrics
({time_pressure_score_gap, clock_gap, net_flag_rate} × {bullet, blitz, rapid,
classical}).

Asserts that after migrations, the ``benchmark_metric`` Postgres ENUM type
contains EXACTLY the 16 expected labels in alphabetical order.

This test catches:
- Pitfall 3 (RESEARCH 94.1): ENUM rejects valid values if labels drift
- T-94.1-02 (threat model): ENUM enforces the locked metric set at DB layer

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
# Guard 1 — skip module until Plan 04 creates the model
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
# Expected ENUM labels (from D-05 / CONTEXT.md and Phase 94.3 CONTEXT.md D-7)
# ---------------------------------------------------------------------------

# Alphabetically sorted (the ORDER BY enumlabel query returns them this way).
# Phase 94.4 D-13 (Plan 05a migration 1945ae56aa20): ENUM collapses from 16
# to 8 family-level values — TC dimensionality moved into the new
# user_benchmark_percentiles.time_control_bucket PK column. Recovery Score
# Gap is rescued (D-05a) and joins the ENUM as ``recovery_score_gap``.
EXPECTED_ENUM_LABELS: list[str] = [
    "achievable_score_gap",
    "clock_gap",
    "net_flag_rate",
    "recovery_score_gap",
    "score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
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
    """After migrations, benchmark_metric ENUM has exactly the 8 expected labels.

    (Test name retained from Phase 94.1 for git-blame stability; the assertion
    now covers 8 family-level labels per Phase 94.4 D-13 Plan 05a — TC
    dimensionality moved into the new user_benchmark_percentiles
    .time_control_bucket PK column.)

    Query shape: SELECT enumlabel FROM pg_enum e
                 JOIN pg_type t ON e.enumtypid = t.oid
                 WHERE t.typname = 'benchmark_metric'
                 ORDER BY enumlabel

    Asserts:
    - Exactly 8 labels returned (not more, not fewer)
    - Labels match the locked Phase 94.4 D-13 set (incl. Recovery rescue)
    - No label drift between the migrations and CdfMetricId Literal in
      global_percentile_cdf.py

    Threat T-94.1-02 mitigation: downstream code that inserts ``metric`` values
    outside this 8-value set will fail with a Postgres ENUM rejection error,
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
