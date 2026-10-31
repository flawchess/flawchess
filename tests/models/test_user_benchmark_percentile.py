"""Model-level tests for ``UserBenchmarkPercentile`` / ``BenchmarkCohortCdf`` metadata.

Phase 243 replaced the native ``benchmark_metric`` ENUM descriptor with TEXT + CHECK
(the allowed ids are generated from the ``CdfMetricId`` Literal) and widened the PK
with a ``color`` column. These tests pin that metadata without a database.
"""

from __future__ import annotations

import typing

from typing import cast

from sqlalchemy import CheckConstraint, Table

from app.models.benchmark_cohort_cdf import BenchmarkCohortCdf
from app.models.user_benchmark_percentile import (
    BENCHMARK_METRIC_VALUES,
    PERCENTILE_COLORS,
    UserBenchmarkPercentile,
    benchmark_metric_check_sql,
)
from app.services.global_percentile_cdf import CdfMetricId

_EXPECTED_PK: tuple[str, ...] = ("user_id", "metric", "time_control_bucket", "color")


def _check_names(model: type) -> set[str]:
    table = cast(Table, model.__table__)  # ty: ignore[unresolved-attribute]  # declarative __table__
    return {str(c.name) for c in table.constraints if isinstance(c, CheckConstraint)}


def test_metric_values_are_the_cdf_metric_id_literal() -> None:
    """The CHECK value set is the CdfMetricId Literal, including both opening ids."""
    assert BENCHMARK_METRIC_VALUES == typing.get_args(CdfMetricId)
    assert "opening_worse_rate" in BENCHMARK_METRIC_VALUES
    assert "opening_better_rate" in BENCHMARK_METRIC_VALUES


def test_check_sql_lists_exactly_the_metric_values() -> None:
    """``benchmark_metric_check_sql()`` renders ``metric IN (...)`` over every value, nothing else."""
    sql = benchmark_metric_check_sql()
    assert sql.startswith("metric IN (")
    listed = [part.strip().strip("'") for part in sql[len("metric IN (") : -1].split(",")]
    assert tuple(listed) == BENCHMARK_METRIC_VALUES


def test_primary_key_includes_color() -> None:
    """The PK is (user_id, metric, time_control_bucket, color)."""
    pk_columns = tuple(c.name for c in UserBenchmarkPercentile.__mapper__.primary_key)
    assert set(pk_columns) == set(_EXPECTED_PK)
    assert len(pk_columns) == len(_EXPECTED_PK)


def test_color_defaults_to_all() -> None:
    """The ``color`` server default is 'all' and the allowed colours are all/white/black."""
    color_column = UserBenchmarkPercentile.__table__.c.color
    assert color_column.server_default is not None
    assert str(color_column.server_default.arg) == "all"
    assert set(PERCENTILE_COLORS) == {"all", "white", "black"}


def test_check_constraints_are_declared_on_both_tables() -> None:
    """Both CHECK names the migration creates are declared on the ORM tables."""
    assert {
        "ck_user_benchmark_percentiles_metric",
        "ck_user_benchmark_percentiles_color",
    } <= _check_names(UserBenchmarkPercentile)
    assert "ck_benchmark_cohort_cdf_metric" in _check_names(BenchmarkCohortCdf)
