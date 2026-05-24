"""Phase 94.2 Plan 02 Task 1 behavior tests for the pooled CDF SQL builder.

Verifies that ``_build_metric_breakpoint_query`` consumes the post-94.1 pooled
SQL surface from ``app.services.canonical_slice_sql`` and threads the
``snapshot_date`` argument through.

Distinct from ``test_gen_global_percentile_cdf_unchanged.py`` (the byte-identical
canary): these tests assert structural properties (CTE presence, predicates
absent, CLI flag wiring) so they don't churn with whitespace-only edits.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

# Make the scripts/ directory importable for the module-under-test.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.gen_global_percentile_cdf import (  # noqa: E402
    _build_metric_breakpoint_query,
    _build_per_bucket_sanity_query,
    _default_snapshot_date,
)

_METRICS = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
)


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_has_one_selected_users_block(metric_id: str) -> None:
    """The output must contain exactly one ``selected_users AS (`` block."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert sql.count("selected_users AS (") == 1, sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_emits_pooled_per_user_values(metric_id: str) -> None:
    """The final SELECT must be percentile_cont over the pooled per_user_values CTE."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert "per_user_values" in sql
    assert "percentile_cont(" in sql
    assert "count(*) AS n_users" in sql
    assert "FROM per_user_values" in sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_threads_snapshot_date(metric_id: str) -> None:
    """``snapshot_date`` MUST be embedded in the 36-month recency window."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert "DATE '2026-03-31' - INTERVAL '36 months'" in sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_has_dedup_cohort_filter(metric_id: str) -> None:
    """selected_users CTE must dedup via the bool_or NOT-(2400, classical) clause (D-1)."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert "bool_or(NOT (bsu.rating_bucket = 2400 AND bsu.tc_bucket = 'classical'))" in sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_pools_across_tcs(metric_id: str) -> None:
    """No per-TC predicate ``g.time_control_bucket::text = su.tc_bucket`` anywhere (D-5)."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert "g.time_control_bucket::text = su.tc_bucket" not in sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_breakpoint_query_no_apply_floor(metric_id: str) -> None:
    """Pitfall canary: ``apply_floor`` argument is removed under 94.2 (D-8)."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]
    assert "apply_floor" not in sql


@pytest.mark.parametrize("metric_id", _METRICS)
def test_per_bucket_sanity_query_still_renders(metric_id: str) -> None:
    """``_build_per_bucket_sanity_query`` is preserved verbatim as a diagnostic."""
    sql = _build_per_bucket_sanity_query(metric_id)  # ty: ignore[invalid-argument-type]
    assert "elo_bucket" in sql
    assert "median_v" in sql
    assert "skew" in sql


def test_sanity_query_function_carries_deprecation_disclaimer() -> None:
    """``_build_per_bucket_sanity_query.__doc__`` must flag the 94.2 no-longer-CDF status."""
    doc = _build_per_bucket_sanity_query.__doc__
    assert doc is not None
    assert "Phase 94.2" in doc
    # Accept either "no longer reflect production CDF" or "...reflects production CDF".
    assert ("no longer reflects production CDF" in doc) or (
        "no longer reflect production CDF" in doc
    )


def test_default_snapshot_date_matches_benchmark_db_snapshot_month() -> None:
    """Default snapshot date is the last day of ``BENCHMARK_DB_SNAPSHOT_MONTH``."""
    assert _default_snapshot_date() == date(2026, 3, 31)


def test_cli_help_lists_snapshot_date_flag() -> None:
    """``--help`` must surface the ``--snapshot-date`` flag with the YYYY-MM-DD default."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    completed = subprocess.run(
        ["uv", "run", "python", "scripts/gen_global_percentile_cdf.py", "--help"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--snapshot-date" in completed.stdout
    assert "2026-03-31" in completed.stdout
