"""CHECK-constraint introspection test for the ``metric`` and ``color`` columns.

Phase 243 (migration b7e4c2a9f013) replaced the native ``benchmark_metric`` Postgres
ENUM with TEXT + CHECK on ``user_benchmark_percentiles`` and ``benchmark_cohort_cdf``,
and added the ``color`` column with its own CHECK. The allowed ``metric`` set is
generated from the ``CdfMetricId`` Literal, so this test pins that the DB constraint
equals the Literal (13 ids, both opening ids included, none of the 12 dead
TC-suffixed legacy labels) and that a dead label is rejected.
"""

from __future__ import annotations

import re
import typing

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user_benchmark_percentile import PERCENTILE_COLORS
from app.services.global_percentile_cdf import CdfMetricId

pytestmark = pytest.mark.asyncio

_EXPECTED_METRIC_COUNT: int = 13
_LEGACY_TC_SUFFIXED_LABEL: str = "conversion_rate_bullet"
_QUOTED_LITERAL = re.compile(r"'([^']+)'")


async def _allowed_values(conn, constraint_name: str) -> set[str]:
    """Parse the quoted literals out of ``pg_get_constraintdef`` of a CHECK constraint."""
    result = await conn.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"
        ).bindparams(name=constraint_name)
    )
    definition = result.scalar_one()
    return set(_QUOTED_LITERAL.findall(definition))


async def test_benchmark_metric_enum_type_is_gone(test_engine: AsyncEngine) -> None:
    """No native ``benchmark_metric`` type remains, and ``metric`` is TEXT on both tables."""
    async with test_engine.connect() as conn:
        type_count = (
            await conn.execute(
                text("SELECT COUNT(*) FROM pg_type WHERE typname = 'benchmark_metric'")
            )
        ).scalar_one()
        assert type_count == 0
        for table in ("user_benchmark_percentiles", "benchmark_cohort_cdf"):
            data_type = (
                await conn.execute(
                    text(
                        "SELECT data_type FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :t AND column_name = 'metric'"
                    ).bindparams(t=table)
                )
            ).scalar_one()
            assert data_type == "text", f"{table}.metric must be TEXT, got {data_type}"


@pytest.mark.parametrize(
    "constraint_name",
    ["ck_user_benchmark_percentiles_metric", "ck_benchmark_cohort_cdf_metric"],
)
async def test_metric_check_equals_cdf_metric_id_literal(
    test_engine: AsyncEngine, constraint_name: str
) -> None:
    """The DB CHECK allows exactly the ``CdfMetricId`` members (13 ids)."""
    expected = set(typing.get_args(CdfMetricId))
    async with test_engine.connect() as conn:
        allowed = await _allowed_values(conn, constraint_name)
    assert allowed == expected
    assert len(allowed) == _EXPECTED_METRIC_COUNT
    assert {"opening_worse_rate", "opening_better_rate"} <= allowed
    assert _LEGACY_TC_SUFFIXED_LABEL not in allowed


async def test_color_check_allows_all_white_black(test_engine: AsyncEngine) -> None:
    """The colour CHECK allows exactly 'all', 'white' and 'black'."""
    async with test_engine.connect() as conn:
        allowed = await _allowed_values(conn, "ck_user_benchmark_percentiles_color")
    assert allowed == set(PERCENTILE_COLORS) == {"all", "white", "black"}


async def test_dead_metric_label_is_rejected(test_engine: AsyncEngine) -> None:
    """Inserting a legacy TC-suffixed metric violates the CHECK (rolled back, no residue)."""
    async with test_engine.connect() as conn:
        with pytest.raises(IntegrityError):
            await conn.execute(
                text(
                    "INSERT INTO benchmark_cohort_cdf "
                    "(metric, anchor_elo, tc, percentile, value) "
                    "VALUES (:metric, 1200, 'blitz', 50, 0.5)"
                ).bindparams(metric=_LEGACY_TC_SUFFIXED_LABEL)
            )
        await conn.rollback()
