"""Pooled-shape parity assertions for ``per_user_cte_for`` — Phase 94.2 Plan 01.

This module replaces the Phase 94.1 SC-7 numerical-parity gate (which
seeded a test DB, ran both code paths, and asserted ``abs(bm - su) < 1e-9``
per user_id). The 94.1 test asserted shape via aggregation over the
per-cell ``per_user`` CTE — that shape is gone in 94.2 (no per-cell rows
to aggregate over; ``per_user_values`` already pools to one row per user).

94.2 structural contract (D-10 "drift remains structurally impossible"):

* ``per_user_cte_for(metric, source="benchmark")`` and
  ``per_user_cte_for(metric, source="single_user")`` produce the SAME
  pooled CTE body. The only structural difference between the two paths
  is the ``selected_users`` CTE preamble, which is composed separately
  by ``selected_users_cte(source=...)`` and concatenated by the consumer.

* Neither rendered fragment contains the per-TC equality predicate
  ``g.time_control_bucket::text = su.tc_bucket`` — D-5 pools across
  all TCs the user has played, universally.

The numerical-parity claim is now structurally trivial: identical SQL
emits identical values. We assert the structural identity via byte-equal
string comparison after whitespace normalisation.

Phase 94.3 Plan 02 extension: 12 new per-(metric × TC) parity assertions
guard against the per-TC restriction being introduced at the wrong layer
(RESEARCH §Pitfall 2). If a future refactor "simplifies" by injecting
``AND g.time_control_bucket = '{tc}'`` at the script (Plan C) or service
(Plan D) layer instead of inside ``canonical_slice_sql.py``, these
assertions will surface the drift via diverging benchmark vs single_user
SQL bodies.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

import pytest

from app.services.canonical_slice_sql import per_user_cte_for
from app.services.global_percentile_cdf import CdfMetricId

_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
)
_SOURCES: tuple[Literal["benchmark", "single_user"], ...] = ("benchmark", "single_user")

# Phase 94.3 — 12 per-(metric_family × TC) combinations covered by the new
# dispatcher arms in ``canonical_slice_sql.per_user_cte_for``. Parametrised
# here so the parity assertion is run once per cell.
_PER_TC_METRIC_FAMILIES: tuple[str, ...] = (
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)
_PER_TC_TCS: tuple[str, ...] = ("bullet", "blitz", "rapid", "classical")
_PER_TC_METRIC_IDS: tuple[str, ...] = tuple(
    f"{family}_{tc}" for family in _PER_TC_METRIC_FAMILIES for tc in _PER_TC_TCS
)


def _normalise_whitespace(sql: str) -> str:
    """Collapse all whitespace runs to a single space and strip ends."""
    return re.sub(r"\s+", " ", sql).strip()


@pytest.mark.parametrize("metric_id", _METRICS)
def test_pooled_cte_body_is_identical_across_sources(metric_id: CdfMetricId) -> None:
    """The pooled per-user CTE body is byte-identical between benchmark and single_user (D-10).

    ``per_user_cte_for`` does NOT include the ``selected_users`` CTE preamble
    in its output (that's composed separately by ``selected_users_cte``).
    What this builder returns is the shared pooled body — which must be the
    same regardless of cohort definition.
    """
    bm = per_user_cte_for(metric_id, source="benchmark")
    su = per_user_cte_for(metric_id, source="single_user")
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"pooled CTE body diverged between sources for {metric_id}; "
        f"the only allowed structural diff lives in selected_users_cte()."
    )


@pytest.mark.parametrize("metric_id", _METRICS)
@pytest.mark.parametrize("source", _SOURCES)
def test_no_per_tc_predicate_on_either_source(
    metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
) -> None:
    """``g.time_control_bucket::text = su.tc_bucket`` is gone on BOTH sources (D-5).

    A leftover predicate on either side would defeat cross-TC pooling.
    """
    sql = per_user_cte_for(metric_id, source=source)
    assert "g.time_control_bucket::text = su.tc_bucket" not in sql, (
        f"per-TC predicate must be absent on {source} for {metric_id} (D-5)"
    )


@pytest.mark.parametrize("metric_id", _METRICS)
def test_pooled_cte_contains_recent_capped_prelude(metric_id: CdfMetricId) -> None:
    """Both sources include the shared ``recent_capped`` 1000-per-TC + 36mo prelude (D-5)."""
    bm = per_user_cte_for(metric_id, source="benchmark")
    su = per_user_cte_for(metric_id, source="single_user")
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        assert "recent_capped AS (" in sql, f"recent_capped CTE missing on {label}/{metric_id}"
        assert "<= 1000" in sql, f"1000-per-TC cap missing on {label}/{metric_id}"
        assert "INTERVAL '36 months'" in sql, (
            f"36-month recency window missing on {label}/{metric_id}"
        )


@pytest.mark.parametrize("metric_id", _METRICS)
def test_pooled_cte_emits_per_user_values_with_metric_value_and_n_games(
    metric_id: CdfMetricId,
) -> None:
    """``per_user_values(metric_value, n_games)`` shape is identical on both sources (D-9-amend)."""
    bm = per_user_cte_for(metric_id, source="benchmark")
    su = per_user_cte_for(metric_id, source="single_user")
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1, f"per_user_values missing on {label}/{metric_id}"
        block = sql[pv_idx:]
        assert "metric_value" in block, (
            f"metric_value missing in per_user_values for {label}/{metric_id}"
        )
        assert "n_games" in block, f"n_games missing in per_user_values for {label}/{metric_id}"


# ---------------------------------------------------------------------------
# Phase 94.3 Plan 02 — per-(metric × TC) parity assertions (12 new cells).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metric_id", _PER_TC_METRIC_IDS)
def test_pooled_per_tc_cte_body_is_identical_across_sources(metric_id: str) -> None:
    """The per-TC pooled CTE body must be byte-identical across sources (RESEARCH §Pitfall 2).

    Locating the per-TC restriction inside the shared builder
    (``canonical_slice_sql._recent_capped_per_tc_cte``) makes drift between
    CDF construction (Plan C) and per-user lookup (Plan D) structurally
    impossible. If a future "simplifying" reviewer moves the
    ``AND g.time_control_bucket = '{tc}'`` predicate to the consumer layer,
    this assertion catches it because the two paths would diverge (the
    script-injected predicate would only appear on the benchmark side).

    Parametrised over all 12 (metric × TC) cells.
    """
    bm = per_user_cte_for(metric_id, source="benchmark", snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    su = per_user_cte_for(metric_id, source="single_user", snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per-TC pooled CTE body diverged between sources for {metric_id}; "
        f"the per-TC restriction must live ONLY in canonical_slice_sql._recent_capped_per_tc_cte, "
        f"not in the consumer layer."
    )


@pytest.mark.parametrize("metric_id", _PER_TC_METRIC_IDS)
def test_pooled_per_tc_cte_contains_per_tc_predicate(metric_id: str) -> None:
    """Every per-TC builder output must contain the per-TC predicate (D-10 invariant)."""
    # Derive the expected tc from the metric_id suffix.
    tc = metric_id.rsplit("_", 1)[-1]
    assert tc in {"bullet", "blitz", "rapid", "classical"}, f"unexpected tc suffix on {metric_id}"
    for source in _SOURCES:
        sql = per_user_cte_for(metric_id, source=source)  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        assert f"g.time_control_bucket = '{tc}'" in sql, (
            f"per-TC predicate '{tc}' missing on {source} for {metric_id}"
        )


@pytest.mark.parametrize("metric_id", _PER_TC_METRIC_IDS)
def test_pooled_per_tc_cte_emits_per_user_values_with_metric_value_and_n_games(
    metric_id: str,
) -> None:
    """``per_user_values(metric_value, n_games)`` shape identical on both sources (D-9-amend)."""
    bm = per_user_cte_for(metric_id, source="benchmark")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    su = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1, f"per_user_values missing on {label}/{metric_id}"
        block = sql[pv_idx:]
        assert "metric_value" in block, (
            f"metric_value missing in per_user_values for {label}/{metric_id}"
        )
        assert "n_games" in block, f"n_games missing in per_user_values for {label}/{metric_id}"


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 3 — source-mode parity for the 4 new per-TC ΔES
# builders. Each new builder is called directly here (not through
# per_user_cte_for) because the dispatcher widening to expose them via the
# CdfMetricId Literal lands in Plan 04 (atomic-cutover sequence).
# ---------------------------------------------------------------------------

_PLAN_03_NEW_TCS: tuple[Literal["bullet", "blitz", "rapid", "classical"], ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)
_PLAN_03_SCORE_GAP_BUCKETS: tuple[Literal["conversion", "parity", "recovery"], ...] = (
    "conversion",
    "parity",
    "recovery",
)


@pytest.mark.parametrize("tc", _PLAN_03_NEW_TCS)
def test_score_gap_tc_pooled_body_byte_identical_across_sources(
    tc: Literal["bullet", "blitz", "rapid", "classical"],
) -> None:
    """``per_user_cte_score_gap_tc`` emits identical pooled body across sources.

    Source-mode parity for the new Task 2 per-TC builder. The pooled body
    after the selected_users CTE switch must be byte-identical between
    benchmark and single_user (D-10 invariant; the cohort difference lives
    entirely in ``selected_users_cte``).
    """
    from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

    bm = per_user_cte_score_gap_tc(tc, source="benchmark", snapshot_date=date(2026, 3, 31))
    su = per_user_cte_score_gap_tc(tc, source="single_user", snapshot_date=date(2026, 3, 31))
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per_user_cte_score_gap_tc({tc}) pooled body diverged between sources"
    )


@pytest.mark.parametrize("tc", _PLAN_03_NEW_TCS)
def test_achievable_tc_pooled_body_byte_identical_across_sources(
    tc: Literal["bullet", "blitz", "rapid", "classical"],
) -> None:
    """``per_user_cte_achievable_tc`` emits identical pooled body across sources."""
    from app.services.canonical_slice_sql import per_user_cte_achievable_tc

    bm = per_user_cte_achievable_tc(tc, source="benchmark", snapshot_date=date(2026, 3, 31))
    su = per_user_cte_achievable_tc(tc, source="single_user", snapshot_date=date(2026, 3, 31))
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per_user_cte_achievable_tc({tc}) pooled body diverged between sources"
    )


@pytest.mark.parametrize("tc", _PLAN_03_NEW_TCS)
@pytest.mark.parametrize("bucket_label", _PLAN_03_SCORE_GAP_BUCKETS)
def test_score_gap_bucket_tc_pooled_body_byte_identical_across_sources(
    tc: Literal["bullet", "blitz", "rapid", "classical"],
    bucket_label: Literal["conversion", "parity", "recovery"],
) -> None:
    """``per_user_cte_score_gap_bucket_tc`` emits identical pooled body across sources.

    Parametrised over all 12 (tc × bucket_label) cells.
    """
    from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

    bm = per_user_cte_score_gap_bucket_tc(
        tc, source="benchmark", snapshot_date=date(2026, 3, 31), bucket_label=bucket_label
    )
    su = per_user_cte_score_gap_bucket_tc(
        tc, source="single_user", snapshot_date=date(2026, 3, 31), bucket_label=bucket_label
    )
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per_user_cte_score_gap_bucket_tc({tc}, {bucket_label}) pooled body diverged across sources"
    )


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 3 — regression for existing 94.3 per-TC builders
# after the Pitfall 1 user_id widening (Task 1). The widening is applied
# uniformly to both source modes, so parity must continue to hold.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metric_id", _PER_TC_METRIC_IDS)
def test_existing_94_3_per_tc_pooled_body_byte_identical_after_pitfall_1(
    metric_id: str,
) -> None:
    """After the Pitfall 1 widening (Task 1) the 3 existing per-TC builders
    must STILL show source-mode parity — the widening is applied equally
    to both source modes (the per_user_values projection is in the shared
    pooled body, not in the cohort-specific preamble).

    Parametrised over 3 builders × 4 TCs = 12 cells.
    """
    bm = per_user_cte_for(metric_id, source="benchmark", snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    su = per_user_cte_for(metric_id, source="single_user", snapshot_date=date(2026, 3, 31))  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"existing 94.3 per-TC builder {metric_id} lost source-mode parity after Pitfall 1 widening"
    )
    # And both sides expose user_id in per_user_values.
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values AS")
        assert pv_idx != -1
        block = sql[pv_idx:]
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"user_id projection missing on {label} for {metric_id} (Pitfall 1)"
        )
