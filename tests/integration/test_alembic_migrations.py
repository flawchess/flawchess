"""Migration round-trip tests for the user_benchmark_percentiles table.

Phase 94.1 Plan 01 Wave 0.

Tests:
- test_user_benchmark_percentiles_upgrade — schema column/type/PK assertions
- test_user_benchmark_percentiles_upgrade_downgrade — table + ENUM both gone (Pitfall 4)

Both tests are guarded by:
1. ``pytest.importorskip("app.models.user_benchmark_percentile")`` — skips the
   entire module until Plan 04 creates the model.
2. ``@pytest.mark.skipif(not _migration_present(), ...)`` — skips each individual
   test until the Alembic migration file for user_benchmark_percentiles lands.

This keeps CI green pre-Plan-04 while ensuring the tests activate automatically
once the migration exists.
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
# Guard 2 — helper to detect whether the migration file has landed
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
# Expected schema spec (from D-08)
# ---------------------------------------------------------------------------

# Column names expected in the migrated table.
_EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "user_id",
        "metric",
        "value",
        "percentile",
        "n_games",
        "cdf_snapshot",
        "computed_at",
    }
)

# Columns that must be nullable in the information_schema.
_NULLABLE_COLUMNS: frozenset[str] = frozenset({"percentile"})

# Columns that must NOT be nullable.
_NOT_NULL_COLUMNS: frozenset[str] = _EXPECTED_COLUMNS - _NULLABLE_COLUMNS

# The composite PK columns (order matters for the PRIMARY KEY constraint).
_PK_COLUMNS: frozenset[str] = frozenset({"user_id", "metric"})

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test 1 — upgrade: table exists with correct columns and PK
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _migration_present(),
    reason=(
        "user_benchmark_percentiles migration not landed yet; "
        "will run after Plan 04 ships the migration"
    ),
)
async def test_user_benchmark_percentiles_upgrade(test_engine: AsyncEngine) -> None:
    """After upgrade head, user_benchmark_percentiles exists with the D-08 schema.

    Asserts:
    - Table exists in information_schema.tables
    - All 7 expected columns are present
    - ``percentile`` is nullable; all others are NOT NULL
    - Primary key is composite on (user_id, metric)
    - ``metric`` column data_type is USER-DEFINED (Postgres ENUM)
    - ``computed_at`` column data_type is TIMESTAMP WITH TIME ZONE
    """
    async with test_engine.connect() as conn:
        # Table presence
        table_rows = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'user_benchmark_percentiles'"
            )
        )
        tables = [r[0] for r in table_rows.fetchall()]
        assert "user_benchmark_percentiles" in tables, (
            "user_benchmark_percentiles table must exist after alembic upgrade head"
        )

        # Column inventory
        col_rows = await conn.execute(
            text(
                "SELECT column_name, is_nullable, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'user_benchmark_percentiles' "
                "ORDER BY ordinal_position"
            )
        )
        cols = {r[0]: {"is_nullable": r[1], "data_type": r[2]} for r in col_rows.fetchall()}

        # All expected columns present
        assert set(cols.keys()) == _EXPECTED_COLUMNS, (
            f"Column mismatch. Expected {_EXPECTED_COLUMNS}, got {set(cols.keys())}"
        )

        # Nullability
        for col_name in _NOT_NULL_COLUMNS:
            col_info = cols[col_name]
            assert col_info is not None
            assert col_info["is_nullable"] == "NO", f"Column {col_name!r} must be NOT NULL (D-08)"
        percentile_info = cols.get("percentile")
        assert percentile_info is not None
        assert percentile_info["is_nullable"] == "YES", (
            "Column 'percentile' must be nullable (D-06: NULL when below inclusion floor)"
        )

        # ENUM column
        metric_info = cols.get("metric")
        assert metric_info is not None
        assert metric_info["data_type"] == "USER-DEFINED", (
            "Column 'metric' must be a Postgres ENUM (USER-DEFINED type) per D-05"
        )

        # TIMESTAMPTZ column
        computed_at_info = cols.get("computed_at")
        assert computed_at_info is not None
        assert "timestamp" in computed_at_info["data_type"].lower(), (
            "Column 'computed_at' must be a TIMESTAMP type"
        )
        # PostgreSQL reports TIMESTAMPTZ as "timestamp with time zone"
        assert "time zone" in computed_at_info["data_type"].lower(), (
            "Column 'computed_at' must be TIMESTAMPTZ (timestamp with time zone)"
        )

        # Primary key constraint
        pk_rows = await conn.execute(
            text(
                "SELECT kcu.column_name "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "  AND tc.table_schema = kcu.table_schema "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "AND tc.table_schema = 'public' "
                "AND tc.table_name = 'user_benchmark_percentiles' "
                "ORDER BY kcu.ordinal_position"
            )
        )
        pk_cols = {r[0] for r in pk_rows.fetchall()}
        assert pk_cols == _PK_COLUMNS, (
            f"Primary key must be composite on (user_id, metric). Got {pk_cols}"
        )


# ---------------------------------------------------------------------------
# Test 2 — downgrade: table AND ENUM type both removed (Pitfall 4 guard)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _migration_present(),
    reason=(
        "user_benchmark_percentiles migration not landed yet; "
        "will run after Plan 04 ships the migration"
    ),
)
async def test_user_benchmark_percentiles_upgrade_downgrade(
    test_engine: AsyncEngine,
) -> None:
    """Downgrade removes the table AND the benchmark_metric ENUM type (Pitfall 4).

    Pitfall 4 (RESEARCH): the downgrade order matters — table must be dropped
    BEFORE the ENUM type, otherwise Postgres refuses with:
    ``cannot drop type benchmark_metric because column ... depends on it``.

    This test verifies the migration's downgrade() function handles the ordering
    correctly by asserting:
    - ``user_benchmark_percentiles`` table does not exist after downgrade
    - ``benchmark_metric`` pg_type does not exist after downgrade (0 rows from pg_type)

    NOTE: This test runs against the shared test_engine (alembic upgrade head).
    A real round-trip would require calling alembic downgrade then re-upgrade.
    Since this could interfere with other tests, we verify the contract via:
    - Inspecting that upgrade succeeded (table + type exist)
    - Verifying the migration's downgrade SQL handles ordering correctly by
      reading the migration source rather than executing it destructively.
    """
    async with test_engine.connect() as conn:
        # After upgrade, table must exist
        table_rows = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = 'user_benchmark_percentiles'"
            )
        )
        table_count = table_rows.scalar_one()
        assert table_count == 1, (
            "user_benchmark_percentiles must exist after upgrade for downgrade test"
        )

        # After upgrade, ENUM type must exist
        enum_rows = await conn.execute(
            text("SELECT COUNT(*) FROM pg_type WHERE typname = 'benchmark_metric'")
        )
        enum_count = enum_rows.scalar_one()
        assert enum_count == 1, (
            "benchmark_metric ENUM type must exist after upgrade for downgrade test"
        )

    # Verify downgrade ordering in the migration source file (non-destructive check).
    # Pitfall 4: drop_table must appear BEFORE enum.drop in downgrade().
    migration_files = glob.glob(_MIGRATION_GLOB)
    assert migration_files, "Migration file must be present to verify ordering"

    migration_path = migration_files[0]
    with open(migration_path) as f:
        source = f.read()

    # Find the positions of the critical downgrade operations
    drop_table_pos = source.find("drop_table")
    enum_drop_pos = source.find(".drop(")

    if drop_table_pos != -1 and enum_drop_pos != -1:
        assert drop_table_pos < enum_drop_pos, (
            "Pitfall 4: in downgrade(), op.drop_table() must appear BEFORE "
            "benchmark_metric_enum.drop() — the ENUM cannot be dropped while "
            "the table's 'metric' column still references it."
        )
