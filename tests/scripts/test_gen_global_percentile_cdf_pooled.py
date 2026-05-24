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


# ---------------------------------------------------------------------------
# Phase 94.3 — IN_SCOPE_METRICS widened to 16 + helper-arms widened.
# ---------------------------------------------------------------------------

_PHASE_94_3_NEW_METRICS: tuple[str, ...] = (
    "time_pressure_score_gap_bullet",
    "time_pressure_score_gap_blitz",
    "time_pressure_score_gap_rapid",
    "time_pressure_score_gap_classical",
    "clock_gap_bullet",
    "clock_gap_blitz",
    "clock_gap_rapid",
    "clock_gap_classical",
    "net_flag_rate_bullet",
    "net_flag_rate_blitz",
    "net_flag_rate_rapid",
    "net_flag_rate_classical",
)


def test_in_scope_metrics_has_16_entries() -> None:
    """``IN_SCOPE_METRICS`` widens from 4 to 16 under Phase 94.3."""
    from scripts.gen_global_percentile_cdf import IN_SCOPE_METRICS

    assert len(IN_SCOPE_METRICS) == 16
    for new_id in _PHASE_94_3_NEW_METRICS:
        assert new_id in IN_SCOPE_METRICS, f"IN_SCOPE_METRICS missing {new_id!r}"


def test_cdf_metric_id_re_exported_from_service() -> None:
    """Script imports ``CdfMetricId`` from the service (single source of truth — RESEARCH §Pattern 3)."""
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "gen_global_percentile_cdf.py"
    src = script_path.read_text()
    assert "from app.services.global_percentile_cdf import" in src and "CdfMetricId" in src, (
        "scripts/gen_global_percentile_cdf.py must re-export CdfMetricId from the service "
        "(drift-impossibility per RESEARCH §Pattern 3)."
    )


@pytest.mark.parametrize("tc", ("bullet", "blitz", "rapid", "classical"))
def test_registry_entry_comment_time_pressure_mentions_pressured(tc: str) -> None:
    """Time-pressure per-TC inclusion-floor comment references the pressured-cell floor."""
    from scripts.gen_global_percentile_cdf import _registry_entry_comment

    metric_id = f"time_pressure_score_gap_{tc}"
    comment = _registry_entry_comment(metric_id)  # ty: ignore[invalid-argument-type]
    assert isinstance(comment, str) and comment
    assert "pressured" in comment.lower(), f"comment for {metric_id} missing 'pressured': {comment!r}"


@pytest.mark.parametrize("tc", ("bullet", "blitz", "rapid", "classical"))
def test_registry_entry_comment_clock_gap_mentions_clock_and_tc(tc: str) -> None:
    """Clock-gap per-TC comment references both ``clock`` and the TC bucket name."""
    from scripts.gen_global_percentile_cdf import _registry_entry_comment

    metric_id = f"clock_gap_{tc}"
    comment = _registry_entry_comment(metric_id)  # ty: ignore[invalid-argument-type]
    assert "clock" in comment.lower()
    assert tc in comment.lower()


@pytest.mark.parametrize("tc", ("bullet", "blitz", "rapid", "classical"))
def test_registry_entry_comment_net_flag_rate_references_pooled_floor(tc: str) -> None:
    """Net-flag-rate per-TC comment references the pooled-set ≥30 inclusion floor."""
    from scripts.gen_global_percentile_cdf import _registry_entry_comment

    metric_id = f"net_flag_rate_{tc}"
    comment = _registry_entry_comment(metric_id)  # ty: ignore[invalid-argument-type]
    assert "30" in comment, f"net_flag_rate_{tc} comment must reference the ≥30 floor: {comment!r}"


@pytest.mark.parametrize("metric_id", _PHASE_94_3_NEW_METRICS)
def test_metric_display_name_returns_readable_per_tc_label(metric_id: str) -> None:
    """Each new per-TC ID yields a non-empty human-readable display name with the TC suffix."""
    from scripts.gen_global_percentile_cdf import _metric_display_name

    name = _metric_display_name(metric_id)  # ty: ignore[invalid-argument-type]
    assert isinstance(name, str) and name
    # The TC bucket name should appear in the label (case-insensitive).
    tc = metric_id.rsplit("_", 1)[1]
    assert tc in name.lower(), f"display name for {metric_id!r} missing TC bucket: {name!r}"


def test_metric_display_name_raises_for_unknown_metric() -> None:
    """``_metric_display_name`` falls through to ``KeyError`` for unknown IDs (existing dict semantics)."""
    from scripts.gen_global_percentile_cdf import _metric_display_name

    with pytest.raises((KeyError, ValueError)):
        _metric_display_name("not_a_real_metric")  # ty: ignore[invalid-argument-type]
