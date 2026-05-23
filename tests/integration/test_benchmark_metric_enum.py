"""Postgres ENUM label introspection test for benchmark_metric.

Phase 94.1 Plan 01 Wave 0.

Asserts that after migration, the ``benchmark_metric`` Postgres ENUM type
contains EXACTLY the 4 expected labels in alphabetical order.

This test catches:
- Pitfall 3 (RESEARCH): ENUM rejects valid values if labels drift
- Discretion item (CONTEXT.md): "assert ENUM contains exactly 4 values"
- T-94.1-02 (threat model): ENUM enforces 4 metric values at DB layer

Guarded by ``pytest.importorskip`` + ``_migration_present()`` so CI stays
green until Plan 04 ships the migration.
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
# Expected ENUM labels (from D-05 / CONTEXT.md)
# ---------------------------------------------------------------------------

# Alphabetically sorted (the ORDER BY enumlabel query returns them this way).
EXPECTED_ENUM_LABELS: list[str] = [
    "achievable_score_gap",
    "score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
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
    """After migration, benchmark_metric ENUM has exactly the 4 expected labels.

    Query shape: SELECT enumlabel FROM pg_enum e
                 JOIN pg_type t ON e.enumtypid = t.oid
                 WHERE t.typname = 'benchmark_metric'
                 ORDER BY enumlabel

    Asserts:
    - Exactly 4 labels returned (not more, not fewer)
    - Labels match the locked D-05 set (alphabetical order)
    - No label drift between the migration and CdfMetricId Literal in global_percentile_cdf.py

    Threat T-94.1-02 mitigation: downstream code that inserts ``metric`` values
    outside this 4-value set will fail with a Postgres ENUM rejection error,
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
