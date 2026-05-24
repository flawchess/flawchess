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
"""

from __future__ import annotations

import re
from typing import Literal

import pytest

from app.services.canonical_slice_sql import per_user_cte_for
from app.services.global_percentile_cdf import CdfMetricId

_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
)
_SOURCES: tuple[Literal["benchmark", "single_user"], ...] = ("benchmark", "single_user")


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
