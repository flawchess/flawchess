"""Pooled-shape parity assertions for the live per-TC CTE builders — Phase 94.2 Plan 01.

This module replaces the Phase 94.1 SC-7 numerical-parity gate (which
seeded a test DB, ran both code paths, and asserted ``abs(bm - su) < 1e-9``
per user_id). The 94.1 test asserted shape via aggregation over the
per-cell ``per_user`` CTE — that shape is gone in 94.2 (no per-cell rows
to aggregate over; ``per_user_values`` already pools to one row per user).

94.2 structural contract (D-10 "drift remains structurally impossible"):

The live per-TC builders (``per_user_cte_score_gap_tc``,
``per_user_cte_achievable_tc``, ``per_user_cte_score_gap_bucket_tc``,
``per_user_cte_time_pressure_score_gap``, ``per_user_cte_clock_gap``,
``per_user_cte_net_flag_rate``) produce the SAME pooled CTE body on both
``source="benchmark"`` and ``source="single_user"``. The only structural
difference between the two paths is the ``selected_users`` CTE preamble,
which is composed separately by ``selected_users_cte(source=...)`` and
concatenated by the consumer.

* Neither rendered fragment contains the per-TC equality predicate
  ``g.time_control_bucket::text = su.tc_bucket`` — D-5 pools across
  all TCs the user has played, universally.

The numerical-parity claim is now structurally trivial: identical SQL
emits identical values. We assert the structural identity via byte-equal
string comparison after whitespace normalisation.

Phase 94.3 Plan 02 extension: per-(metric × TC) parity assertions guard
against the per-TC restriction being introduced at the wrong layer
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

from app.services.canonical_slice_sql import (
    RECENT_GAMES_PER_TC_CAP,
    per_user_cte_achievable_tc,
    per_user_cte_clock_gap,
    per_user_cte_net_flag_rate,
    per_user_cte_score_gap_bucket_tc,
    per_user_cte_score_gap_tc,
    per_user_cte_time_pressure_score_gap,
)

_SOURCES: tuple[Literal["benchmark", "single_user"], ...] = ("benchmark", "single_user")

# Phase 94.3 — 12 per-(metric_family × TC) combinations. Parametrised
# here so the parity assertion is run once per cell.
_PER_TC_METRIC_FAMILIES: tuple[str, ...] = (
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)
_PER_TC_TCS: tuple[Literal["bullet", "blitz", "rapid", "classical"], ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)


def _normalise_whitespace(sql: str) -> str:
    """Collapse all whitespace runs to a single space and strip ends."""
    return re.sub(r"\s+", " ", sql).strip()


def _call_per_tc_builder(
    family: str,
    tc: Literal["bullet", "blitz", "rapid", "classical"],
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Dispatch to the live per-TC builder by family name."""
    if family == "time_pressure_score_gap":
        return per_user_cte_time_pressure_score_gap(tc, source=source, snapshot_date=snapshot_date)
    if family == "clock_gap":
        return per_user_cte_clock_gap(tc, source=source, snapshot_date=snapshot_date)
    if family == "net_flag_rate":
        return per_user_cte_net_flag_rate(tc, source=source, snapshot_date=snapshot_date)
    raise ValueError(f"Unknown family: {family!r}")


# ---------------------------------------------------------------------------
# Phase 94.3 Plan 02 — per-(metric × TC) parity assertions (12 cells).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tc", _PER_TC_TCS)
@pytest.mark.parametrize("family", _PER_TC_METRIC_FAMILIES)
def test_pooled_per_tc_cte_body_is_identical_across_sources(
    family: str, tc: Literal["bullet", "blitz", "rapid", "classical"]
) -> None:
    """The per-TC pooled CTE body must be byte-identical across sources (RESEARCH §Pitfall 2).

    Locating the per-TC restriction inside the shared builder
    (``canonical_slice_sql._recent_capped_per_tc_cte``) makes drift between
    CDF construction (Plan C) and per-user lookup (Plan D) structurally
    impossible. If a future "simplifying" reviewer moves the
    ``AND g.time_control_bucket = '{tc}'`` predicate to the consumer layer,
    this assertion catches it because the two paths would diverge (the
    script-injected predicate would only appear on the benchmark side).

    Parametrised over all 12 (family × TC) cells.
    """
    bm = _call_per_tc_builder(family, tc, source="benchmark", snapshot_date=date(2026, 3, 31))
    su = _call_per_tc_builder(family, tc, source="single_user", snapshot_date=date(2026, 3, 31))
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per-TC pooled CTE body diverged between sources for {family}/{tc}; "
        f"the per-TC restriction must live ONLY in canonical_slice_sql._recent_capped_per_tc_cte, "
        f"not in the consumer layer."
    )


@pytest.mark.parametrize("tc", _PER_TC_TCS)
@pytest.mark.parametrize("family", _PER_TC_METRIC_FAMILIES)
def test_pooled_per_tc_cte_contains_per_tc_predicate(
    family: str, tc: Literal["bullet", "blitz", "rapid", "classical"]
) -> None:
    """Every per-TC builder output must contain the per-TC predicate (D-10 invariant)."""
    for source in _SOURCES:
        sql = _call_per_tc_builder(family, tc, source=source)
        assert f"g.time_control_bucket = '{tc}'" in sql, (
            f"per-TC predicate '{tc}' missing on {source} for {family}/{tc}"
        )


@pytest.mark.parametrize("tc", _PER_TC_TCS)
@pytest.mark.parametrize("family", _PER_TC_METRIC_FAMILIES)
def test_pooled_per_tc_cte_emits_per_user_values_with_metric_value_and_n_games(
    family: str, tc: Literal["bullet", "blitz", "rapid", "classical"]
) -> None:
    """``per_user_values(metric_value, n_games)`` shape identical on both sources (D-9-amend)."""
    bm = _call_per_tc_builder(family, tc, source="benchmark")
    su = _call_per_tc_builder(family, tc, source="single_user")
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1, f"per_user_values missing on {label}/{family}/{tc}"
        block = sql[pv_idx:]
        assert "metric_value" in block, (
            f"metric_value missing in per_user_values for {label}/{family}/{tc}"
        )
        assert "n_games" in block, f"n_games missing in per_user_values for {label}/{family}/{tc}"


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 3 — source-mode parity for the 4 new per-TC ΔES
# builders. Each new builder is called directly here (not through
# the dispatcher widening to expose them via the
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

    Also asserts the recent_capped prelude presence and per_user_values shape
    (folded from the deleted non-per-TC tests, now verified on a live builder).
    """
    bm = per_user_cte_score_gap_tc(tc, source="benchmark", snapshot_date=date(2026, 3, 31))
    su = per_user_cte_score_gap_tc(tc, source="single_user", snapshot_date=date(2026, 3, 31))
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"per_user_cte_score_gap_tc({tc}) pooled body diverged between sources"
    )
    # Prelude substring guard (formerly in test_pooled_cte_contains_recent_capped_prelude).
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        assert "recent_capped AS (" in sql, (
            f"recent_capped CTE missing on {label}/score_gap_tc/{tc}"
        )
        assert f"<= {RECENT_GAMES_PER_TC_CAP}" in sql, (
            f"recent-per-TC cap missing on {label}/score_gap_tc/{tc}"
        )
        assert "INTERVAL '36 months'" in sql, (
            f"36-month recency window missing on {label}/score_gap_tc/{tc}"
        )
    # per_user_values shape guard (formerly in test_pooled_cte_emits_per_user_values_*).
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1, f"per_user_values missing on {label}/score_gap_tc/{tc}"
        block = sql[pv_idx:]
        assert "metric_value" in block, (
            f"metric_value missing in per_user_values for {label}/score_gap_tc/{tc}"
        )
        assert "n_games" in block, (
            f"n_games missing in per_user_values for {label}/score_gap_tc/{tc}"
        )


@pytest.mark.parametrize("tc", _PLAN_03_NEW_TCS)
def test_achievable_tc_pooled_body_byte_identical_across_sources(
    tc: Literal["bullet", "blitz", "rapid", "classical"],
) -> None:
    """``per_user_cte_achievable_tc`` emits identical pooled body across sources."""

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


@pytest.mark.parametrize("tc", _PER_TC_TCS)
@pytest.mark.parametrize("family", _PER_TC_METRIC_FAMILIES)
def test_existing_94_3_per_tc_pooled_body_byte_identical_after_pitfall_1(
    family: str, tc: Literal["bullet", "blitz", "rapid", "classical"]
) -> None:
    """After the Pitfall 1 widening (Task 1) the 3 existing per-TC builders
    must STILL show source-mode parity — the widening is applied equally
    to both source modes (the per_user_values projection is in the shared
    pooled body, not in the cohort-specific preamble).

    Parametrised over 3 builders × 4 TCs = 12 cells.
    """
    bm = _call_per_tc_builder(family, tc, source="benchmark", snapshot_date=date(2026, 3, 31))
    su = _call_per_tc_builder(family, tc, source="single_user", snapshot_date=date(2026, 3, 31))
    assert _normalise_whitespace(bm) == _normalise_whitespace(su), (
        f"existing 94.3 per-TC builder {family}/{tc} lost source-mode parity after Pitfall 1 widening"
    )
    # And both sides expose user_id in per_user_values.
    for sql, label in ((bm, "benchmark"), (su, "single_user")):
        pv_idx = sql.find("per_user_values AS")
        assert pv_idx != -1
        block = sql[pv_idx:]
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"user_id projection missing on {label} for {family}/{tc} (Pitfall 1)"
        )
