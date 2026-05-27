"""Tests for ``app.services.canonical_slice_sql`` — Phase 94.2 pooled shape.

These tests assert the pooled-per-user contract (D-5 / D-6 / D-8 / D-1 in
``.planning/phases/94.2-pooled-per-user-percentile-redesign/94.2-CONTEXT.md``).
They replace the Phase 94.1 per-cell tests that asserted ``apply_floor``,
``elo_bucket`` projections, and ``g.time_control_bucket::text = su.tc_bucket``
predicates.

Preserved verbatim from 94.1:

* ``test_sparse_exclusion_sql_parametrises_columns`` — the helper is the
  only remaining consumer post-refactor (per RESEARCH §State of the Art /
  92.4 Pitfall 2).

Substring matching is the assertion style throughout. Byte-identical SQL
matching is enforced separately by
``tests/scripts/test_gen_global_percentile_cdf_unchanged.py`` in Plan 02.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

import pytest
from sqlalchemy import text

from app.services.canonical_slice_sql import (
    CLOCK_GAP_MIN_POOL_N,
    MEDIAN_ANCHOR_MIN_GAMES,
    NET_FLAG_RATE_MIN_POOL_N,
    RECENCY_WINDOW_MONTHS,
    RECENT_GAMES_PER_TC_CAP,
    TIME_PRESSURE_CLOCK_PCT_THRESHOLD,
    TIME_PRESSURE_MIN_PRESSURED_N,
    TimeControlBucket,
    _chesscom_conversion_values_sql,
    _recent_capped_per_tc_cte,
    elo_bucket_expr,
    equal_footing_filter_sql,
    per_user_cte_for,
    per_user_cte_median_anchor,
    selected_users_cte,
    sparse_exclusion_sql,
)
from app.services.chesscom_to_lichess import CHESSCOM_BLITZ_TO_LICHESS
from app.services.global_percentile_cdf import CdfMetricId

# ---------------------------------------------------------------------------
# Phase 94.4 Plan 10 Task 1.0 — Baseline SQL for the non-blend regression guard.
#
# Captured from ``per_user_cte_median_anchor('rapid', source='benchmark')``
# at the pre-Task-1 git state (a9d5431a). This constant is the regression
# pin for Plan 04's cohort-CDF benchmark-side call path. Test A1 asserts
# byte-for-byte equality against this string — any drift in the non-blend
# code path (whitespace, column reorder, helper extraction, comment change)
# trips the test deterministically.
# ---------------------------------------------------------------------------

_BASELINE_PER_USER_CTE_MEDIAN_ANCHOR_RAPID_BENCHMARK: str = (
    "recent_capped AS (\n"
    "  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at\n"
    "  FROM (\n"
    "    SELECT g.*,\n"
    "           row_number() OVER (PARTITION BY g.user_id\n"
    "                              ORDER BY g.played_at DESC) AS rn\n"
    "    FROM games g\n"
    "    JOIN selected_users su ON su.user_id = g.user_id\n"
    "    WHERE g.rated AND NOT g.is_computer_game\n"
    "      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL\n"
    "      AND g.played_at >= NOW() - INTERVAL '36 months'\n"
    "      AND abs((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)) <= 100\n"
    "      AND g.time_control_bucket = 'rapid'\n"
    "  ) g\n"
    "  WHERE g.rn <= 3000\n"
    "),\n"
    "recent_capped_no_daily AS (\n"
    "  SELECT rc.*\n"
    "  FROM recent_capped rc\n"
    "  JOIN games g ON g.id = rc.id\n"
    "  WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')\n"
    "    \n"
    "),\n"
    "per_user_anchor AS (\n"
    "  SELECT\n"
    "    rc.user_id,\n"
    "    percentile_cont(0.5) WITHIN GROUP (ORDER BY (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END))::int AS anchor_rating,\n"
    "    count(*) AS n_games\n"
    "  FROM recent_capped_no_daily rc\n"
    "  JOIN games g ON g.id = rc.id\n"
    "  GROUP BY rc.user_id\n"
    "  HAVING count(*) >= 30\n"
    ")"
)


# ---------------------------------------------------------------------------
# Parametrise constants.
# ---------------------------------------------------------------------------

_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
)
_SOURCES: tuple[Literal["benchmark", "single_user"], ...] = ("benchmark", "single_user")


# ---------------------------------------------------------------------------
# Test class: pooled shape.
# ---------------------------------------------------------------------------


class TestPooledShape:
    """Per-cell shape is replaced by a pooled per-user aggregate (D-5)."""

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_per_user_values_projection_emits_metric_value_and_n_games(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """``per_user_values`` must project exactly ``(metric_value, n_games)`` (D-9-amend)."""
        sql = per_user_cte_for(metric_id, source=source)
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1, f"per_user_values block missing for {metric_id}/{source}"
        block = sql[pv_idx:]
        assert "metric_value" in block, (
            f"per_user_values must project metric_value for {metric_id}/{source}"
        )
        assert "n_games" in block, (
            f"per_user_values must project n_games for {metric_id}/{source} (D-9-amend)"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_no_elo_bucket_or_tc_bucket_projection_on_per_user(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """The pooled per-user CTE must not project ``elo_bucket`` or carry a per-TC bucket column.

        ``time_control_bucket`` may still appear inside the
        ``ROW_NUMBER() OVER (PARTITION BY ... time_control_bucket ...)`` cap
        window, but neither ``elo_bucket`` nor a free ``tc_bucket`` may
        appear in the per-user projection.
        """
        sql = per_user_cte_for(metric_id, source=source)
        assert "elo_bucket" not in sql, (
            f"elo_bucket leaked into pooled SQL for {metric_id}/{source} (D-5)"
        )
        # Allow time_control_bucket only inside the row_number partition.
        non_window_tc = sql.replace("time_control_bucket", "")
        assert "tc_bucket" not in non_window_tc, (
            f"tc_bucket leaked into pooled SQL for {metric_id}/{source} (D-5)"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_no_per_tc_join_predicate(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """``g.time_control_bucket::text = su.tc_bucket`` must be absent on BOTH sources (D-5).

        Regression guard: a leftover per-TC predicate on single_user would
        zero out the pooled set (the single_user CTE no longer projects
        tc_bucket at all); on benchmark it would defeat the pooling intent.
        """
        sql = per_user_cte_for(metric_id, source=source)
        assert "g.time_control_bucket::text = su.tc_bucket" not in sql, (
            f"per-TC predicate must NOT appear in pooled CTE for {metric_id}/{source}"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_no_sparse_cell_literal_in_per_user_cte(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """Per-row sparse-cell exclusion is gone (D-1).

        The literal substring ``2400 AND tc_bucket = 'classical'`` (the
        signature of ``sparse_exclusion_sql("elo_bucket", "tc_bucket")``)
        must not appear in the rendered pooled CTE. Sparse-cell exclusion
        lives on cohort selection only.
        """
        sql = per_user_cte_for(metric_id, source=source)
        assert "tc_bucket = 'classical'" not in sql, (
            f"sparse_exclusion_sql leaked into pooled CTE for {metric_id}/{source}"
        )


# ---------------------------------------------------------------------------
# Test class: recency window.
# ---------------------------------------------------------------------------


class TestRecencyWindow:
    """36-month recency anchor + 3000-per-TC cap (D-5)."""

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_recent_per_tc_cap_substrings_present(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        sql = per_user_cte_for(metric_id, source=source)
        # Normalise whitespace so the multi-line SQL emission matches a single-line probe.
        normalised = " ".join(sql.split())
        assert (
            "row_number() OVER (PARTITION BY g.user_id, g.time_control_bucket "
            "ORDER BY g.played_at DESC)" in normalised
        ), f"ROW_NUMBER partition missing for {metric_id}/{source}"
        assert f"<= {RECENT_GAMES_PER_TC_CAP}" in sql, (
            f"recent-per-TC cap missing for {metric_id}/{source}"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_recency_window_default_uses_now(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """``snapshot_date=None`` (default) emits ``NOW() - INTERVAL '36 months'``."""
        sql = per_user_cte_for(metric_id, source=source)
        assert f"NOW() - INTERVAL '{RECENCY_WINDOW_MONTHS} months'" in sql, (
            f"NOW() recency anchor missing for {metric_id}/{source}"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_recency_window_explicit_snapshot_date(
        self, metric_id: CdfMetricId, source: Literal["benchmark", "single_user"]
    ) -> None:
        """Explicit ``date`` emits ``DATE 'YYYY-MM-DD' - INTERVAL '36 months'``."""
        sql = per_user_cte_for(metric_id, source=source, snapshot_date=date(2026, 3, 31))
        assert f"DATE '2026-03-31' - INTERVAL '{RECENCY_WINDOW_MONTHS} months'" in sql, (
            f"explicit DATE anchor missing for {metric_id}/{source}"
        )
        # Default NOW() must NOT be present when explicit date is given.
        assert "NOW() - INTERVAL" not in sql, (
            f"NOW() leaked into explicit-snapshot SQL for {metric_id}/{source}"
        )

    @pytest.mark.parametrize("metric_id", _METRICS)
    def test_cap_appears_once_per_builder_output(self, metric_id: CdfMetricId) -> None:
        """``<= {cap}`` should appear exactly once in the rendered SQL (single capping site)."""
        sql = per_user_cte_for(metric_id, source="single_user")
        cap_count = sql.count(f"<= {RECENT_GAMES_PER_TC_CAP}")
        assert cap_count == 1, (
            f"expected exactly one ``<= {RECENT_GAMES_PER_TC_CAP}`` occurrence for {metric_id}, "
            f"got {cap_count}"
        )


# ---------------------------------------------------------------------------
# Test class: inclusion floor.
# ---------------------------------------------------------------------------


class TestInclusionFloor:
    """Single ≥30 inclusion-floor gate per metric (D-6)."""

    def test_score_gap_having_gates_both_30(self) -> None:
        sql = per_user_cte_for("score_gap", source="single_user")
        assert "HAVING count(*) FILTER (WHERE has_endgame)     >= 30" in sql
        assert "AND count(*) FILTER (WHERE NOT has_endgame) >= 30" in sql

    def test_achievable_having_gates_di_ge_30(self) -> None:
        sql = per_user_cte_for("achievable_score_gap", source="single_user")
        assert "HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= 30" in sql

    def test_score_gap_bucket_conv_having_gates_30(self) -> None:
        sql = per_user_cte_for("score_gap_conv", source="single_user")
        # The HAVING gate inside per_user_bucket is "HAVING count(*) >= 30".
        assert "HAVING count(*) >= 30" in sql
        # And the per_user_values WHERE clause selects the conversion bucket.
        assert "bucket = 'conversion'" in sql

    def test_score_gap_bucket_parity_having_gates_30(self) -> None:
        sql = per_user_cte_for("score_gap_parity", source="single_user")
        assert "HAVING count(*) >= 30" in sql
        assert "bucket = 'parity'" in sql

    @pytest.mark.parametrize("metric_id", _METRICS)
    def test_apply_floor_argument_raises_typeerror(self, metric_id: CdfMetricId) -> None:
        """``apply_floor`` is removed from the public surface (D-8)."""
        with pytest.raises(TypeError):
            per_user_cte_for(
                metric_id,
                source="single_user",
                apply_floor=False,  # ty: ignore[unknown-argument]  # negative assertion: 94.2 removed apply_floor (D-8)
            )


# ---------------------------------------------------------------------------
# Test class: cohort dedup (selected_users_cte).
# ---------------------------------------------------------------------------


class TestCohortDedup:
    """Selected-users CTE — benchmark dedup (D-1), single_user CAST preserved."""

    def test_benchmark_cohort_groups_by_lower_username(self) -> None:
        sql = selected_users_cte(source="benchmark")
        assert "GROUP BY lower(bsu.lichess_username)" in sql, (
            "benchmark cohort must dedup by lower(lichess_username) (D-1)"
        )

    def test_benchmark_cohort_drops_sparse_only_members(self) -> None:
        sql = selected_users_cte(source="benchmark")
        assert "bool_or(NOT (bsu.rating_bucket = 2400 AND bsu.tc_bucket = 'classical'))" in sql, (
            "benchmark cohort must drop (2400, classical)-only members via bool_or (D-1)"
        )

    def test_benchmark_cohort_emits_user_id(self) -> None:
        """The pooled per-user CTE only needs ``user_id`` from the cohort CTE."""
        sql = selected_users_cte(source="benchmark")
        assert "AS user_id" in sql, "benchmark cohort must project user_id"
        # tc_bucket / selection_rating_bucket / median_elo are no longer needed.
        # No hard absence assertion — the next test class covers this.

    def test_single_user_cte_uses_cast_form(self) -> None:
        """V5 security: ``CAST(:user_id AS int)`` is load-bearing (94.1 Plan 09)."""
        sql = selected_users_cte(source="single_user")
        assert "CAST(:user_id AS int) AS user_id" in sql

    def test_single_user_cte_bindparam_detected_by_sqlalchemy(self) -> None:
        """``text(sql).compile().params`` must list ``user_id`` (regression #1)."""
        sql = selected_users_cte(source="single_user")
        params = list(text(sql).compile().params)
        assert params == ["user_id"], (
            f"expected exactly one bindparam 'user_id', got {params!r} "
            f"(SQLAlchemy did not detect :user_id — the `::int` shorthand "
            f"cast confuses the tokeniser; use CAST(:user_id AS int))"
        )

    def test_single_user_cte_round_trip_does_not_raise(self) -> None:
        """``text(sql).bindparams(user_id=42)`` must NOT raise ArgumentError."""
        sql = selected_users_cte(source="single_user")
        wrapped = f"WITH {sql} SELECT user_id FROM selected_users"
        bound = text(wrapped).bindparams(user_id=42)
        assert bound is not None

    def test_single_user_cte_no_benchmark_tables(self) -> None:
        """No benchmark-table joins on the single_user path."""
        sql = selected_users_cte(source="single_user")
        assert "benchmark_selected_users" not in sql
        assert "benchmark_ingest_checkpoints" not in sql


# ---------------------------------------------------------------------------
# Test class: exported helpers (preserved from 94.1).
# ---------------------------------------------------------------------------


class TestExportedHelpers:
    """``equal_footing_filter_sql`` / ``elo_bucket_expr`` / ``sparse_exclusion_sql`` still export."""

    def test_equal_footing_filter_sql_is_constant(self) -> None:
        first = equal_footing_filter_sql()
        second = equal_footing_filter_sql()
        assert first == second
        assert "<= 100" in first
        assert "white_rating" in first or "g.user_color" in first

    def test_elo_bucket_expr_format(self) -> None:
        expr = elo_bucket_expr("user_elo_at_game")
        lowered = expr.lower()
        assert "case when" in lowered
        assert "user_elo_at_game" in expr
        for anchor in ("800", "1200", "1600", "2000", "2400"):
            assert anchor in expr
        assert "null" in lowered

        # Alias substitutes cleanly.
        expr_alt = elo_bucket_expr("g_elo")
        assert "g_elo" in expr_alt
        assert "user_elo_at_game" not in expr_alt

    def test_sparse_exclusion_sql_parametrises_columns(self) -> None:
        """Preserved verbatim from 94.1 — column-substitution + injection-vector guard.

        The function itself is no longer invoked by ``per_user_cte_*``
        (D-1 — sparse exclusion lives at cohort selection now). It IS still
        used by ``scripts/gen_global_percentile_cdf.py:_build_per_bucket_sanity_query``,
        and the test verifies the substitution contract for that consumer.
        """
        standard = sparse_exclusion_sql("elo_bucket", "tc_bucket")
        assert "elo_bucket" in standard
        assert "tc_bucket" in standard
        assert "2400" in standard
        assert "classical" in standard

        alt = sparse_exclusion_sql("elo_col_alias", "tc_col_alias")
        assert "elo_col_alias" in alt
        assert "tc_col_alias" in alt
        assert "2400" in alt

        assert standard != alt

        for result in (standard, alt):
            lowered = result.lower()
            assert ";" not in result
            assert "union" not in lowered
            assert "drop" not in lowered


# ---------------------------------------------------------------------------
# Phase 94.3 Plan 02 — per-TC pooled-aggregate builders.
# ---------------------------------------------------------------------------

_TIME_PRESSURE_TCS: tuple[TimeControlBucket, ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)
_PER_TC_METRIC_FAMILIES: tuple[str, ...] = (
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)


class TestPerTcConstants:
    """Module-level constants for per-TC builders (Plan B Task 1; CONTEXT D-6)."""

    def test_time_pressure_clock_pct_threshold_is_locked_to_040(self) -> None:
        assert TIME_PRESSURE_CLOCK_PCT_THRESHOLD == 0.40

    def test_time_pressure_min_pressured_n_is_30(self) -> None:
        assert TIME_PRESSURE_MIN_PRESSURED_N == 30

    def test_clock_gap_min_pool_n_is_30(self) -> None:
        assert CLOCK_GAP_MIN_POOL_N == 30

    def test_net_flag_rate_min_pool_n_is_30(self) -> None:
        assert NET_FLAG_RATE_MIN_POOL_N == 30


class TestRecentCappedPerTcCte:
    """The per-TC variant of ``_recent_capped_cte`` (Plan B Task 1)."""

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_emits_per_tc_predicate(self, tc: TimeControlBucket) -> None:
        sql = _recent_capped_per_tc_cte(snapshot_date=None, tc=tc)
        assert f"g.time_control_bucket = '{tc}'" in sql, f"per-TC predicate missing for tc={tc!r}"

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_partition_collapses_to_per_user(self, tc: TimeControlBucket) -> None:
        """When restricted to one TC, ROW_NUMBER PARTITION simplifies to (user_id)."""
        sql = _recent_capped_per_tc_cte(snapshot_date=None, tc=tc)
        normalised = " ".join(sql.split())
        assert (
            "row_number() OVER (PARTITION BY g.user_id ORDER BY g.played_at DESC)" in normalised
        ), f"partition should collapse to per-user for tc={tc!r}"
        # The full per-(user, tc) partition from `_recent_capped_cte` must NOT appear here.
        assert "PARTITION BY g.user_id, g.time_control_bucket" not in normalised, (
            f"per-(user, TC) partition leaked into per-TC variant for tc={tc!r}"
        )

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_cap_present(self, tc: TimeControlBucket) -> None:
        sql = _recent_capped_per_tc_cte(snapshot_date=None, tc=tc)
        assert f"WHERE g.rn <= {RECENT_GAMES_PER_TC_CAP}" in sql

    def test_classical_tc_string_substitution(self) -> None:
        sql = _recent_capped_per_tc_cte(snapshot_date=None, tc="classical")
        assert "g.time_control_bucket = 'classical'" in sql
        assert "g.time_control_bucket = 'bullet'" not in sql

    def test_snapshot_date_default_renders_now(self) -> None:
        sql = _recent_capped_per_tc_cte(snapshot_date=None, tc="bullet")
        assert f"NOW() - INTERVAL '{RECENCY_WINDOW_MONTHS} months'" in sql

    def test_snapshot_date_explicit_renders_iso_date(self) -> None:
        sql = _recent_capped_per_tc_cte(snapshot_date=date(2026, 3, 31), tc="bullet")
        assert f"DATE '2026-03-31' - INTERVAL '{RECENCY_WINDOW_MONTHS} months'" in sql
        assert "NOW() - INTERVAL" not in sql


# ---------------------------------------------------------------------------
# Phase 94.3 Plan 02 — per-TC builders + dispatcher widening.
# ---------------------------------------------------------------------------


class TestPerTcBuilders:
    """The three new per-TC builder families (Plan B Task 2)."""

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_time_pressure_score_gap_emits_per_tc_predicate_and_dual_having(
        self, tc: TimeControlBucket, source: Literal["benchmark", "single_user"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_time_pressure_score_gap

        sql = per_user_cte_time_pressure_score_gap(tc, source=source)
        normalised = " ".join(sql.split())
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "HAVING count(*) FILTER (WHERE user_clock_pct < 0.40) >= 30" in normalised, (
            "user-pressured ≥30 HAVING gate missing"
        )
        assert "count(*) FILTER (WHERE opp_clock_pct < 0.40) >= 30" in normalised, (
            "opp-pressured ≥30 HAVING gate missing"
        )
        # per_user_values shape
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1
        block = sql[pv_idx:]
        assert "metric_value" in block
        assert "n_games" in block

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_clock_gap_emits_per_tc_predicate_and_pool_having(
        self, tc: TimeControlBucket, source: Literal["benchmark", "single_user"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_clock_gap

        sql = per_user_cte_clock_gap(tc, source=source)
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "HAVING count(*) >= 30" in sql
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1
        block = sql[pv_idx:]
        assert "metric_value" in block
        assert "n_games" in block

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_net_flag_rate_emits_per_tc_predicate_and_pool_having(
        self, tc: TimeControlBucket, source: Literal["benchmark", "single_user"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_net_flag_rate

        sql = per_user_cte_net_flag_rate(tc, source=source, snapshot_date=date(2026, 3, 31))
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "DATE '2026-03-31'" in sql, "snapshot_date should be threaded through"
        assert "HAVING count(*) >= 30" in sql
        pv_idx = sql.find("per_user_values")
        assert pv_idx != -1
        block = sql[pv_idx:]
        assert "metric_value" in block
        assert "n_games" in block


class TestPerTcDispatcher:
    """``per_user_cte_for`` widened with 12 new dispatch arms (Plan B Task 2)."""

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_dispatcher_routes_time_pressure_score_gap(self, tc: TimeControlBucket) -> None:
        metric_id = f"time_pressure_score_gap_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # 12 new metric IDs are widened in Plan C; Plan B dispatcher matches string literals
        normalised = " ".join(sql.split())
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "HAVING count(*) FILTER (WHERE user_clock_pct < 0.40) >= 30" in normalised

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_dispatcher_routes_clock_gap(self, tc: TimeControlBucket) -> None:
        metric_id = f"clock_gap_{tc}"
        sql = per_user_cte_for(metric_id, source="benchmark")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "HAVING count(*) >= 30" in sql

    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_dispatcher_routes_net_flag_rate(self, tc: TimeControlBucket) -> None:
        metric_id = f"net_flag_rate_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        assert f"g.time_control_bucket = '{tc}'" in sql
        assert "HAVING count(*) >= 30" in sql

    def test_dispatcher_raises_on_unknown_metric(self) -> None:
        with pytest.raises(ValueError, match=r"^Unknown metric_id:"):
            per_user_cte_for("does_not_exist_metric", source="single_user")  # ty: ignore[invalid-argument-type]  # negative assertion: arbitrary unknown ID

    @pytest.mark.parametrize("metric_family", _PER_TC_METRIC_FAMILIES)
    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_dispatcher_emits_per_tc_predicate_for_every_cell(
        self, metric_family: str, tc: TimeControlBucket
    ) -> None:
        """Parametrised over all 12 (metric × TC) cells (Plan B Task 2 Test 8)."""
        metric_id = f"{metric_family}_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        assert f"g.time_control_bucket = '{tc}'" in sql, f"per-TC predicate missing for {metric_id}"
        # Metric-specific floor signature.
        if metric_family == "time_pressure_score_gap":
            assert "HAVING count(*) FILTER" in sql, (
                f"per-pressure-cell HAVING missing for {metric_id}"
            )
        else:
            assert "HAVING count(*) >= 30" in sql, f"pooled ≥30 HAVING missing for {metric_id}"


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 02 — per_user_cte_median_anchor SQL builder.
# ---------------------------------------------------------------------------


_MEDIAN_ANCHOR_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")


class TestPerUserCteMedianAnchor:
    """Phase 94.4 D-04 / RESEARCH Pattern 6 — per-(user, TC) median rating anchor."""

    def test_median_anchor_min_games_constant_is_30(self) -> None:
        """MEDIAN_ANCHOR_MIN_GAMES constant locked to 30 per D-04."""
        assert MEDIAN_ANCHOR_MIN_GAMES == 30

    @pytest.mark.parametrize("tc", _MEDIAN_ANCHOR_TCS)
    def test_median_anchor_emits_per_user_anchor_cte(self, tc: TimeControlBucket) -> None:
        """Output includes a per_user_anchor CTE for every TC."""
        sql = per_user_cte_median_anchor(tc, source="benchmark")
        assert "per_user_anchor AS" in sql, f"per_user_anchor CTE missing for tc={tc!r}"

    @pytest.mark.parametrize("tc", _MEDIAN_ANCHOR_TCS)
    def test_median_anchor_uses_percentile_cont(self, tc: TimeControlBucket) -> None:
        """SQL uses percentile_cont(0.5) WITHIN GROUP (RESEARCH Pattern 6)."""
        sql = per_user_cte_median_anchor(tc, source="benchmark")
        assert "percentile_cont(0.5)" in sql, f"median aggregate missing for tc={tc!r}"
        assert "WITHIN GROUP" in sql, f"WITHIN GROUP clause missing for tc={tc!r}"

    @pytest.mark.parametrize("tc", _MEDIAN_ANCHOR_TCS)
    def test_daily_classical_drop_present_for_all_tcs(self, tc: TimeControlBucket) -> None:
        """Daily-classical drop (RESEARCH Pitfall 11) is unconditional on tc.

        The drop runs symmetrically for ALL 4 TCs: chess.com Daily games are
        bucketed `classical` by the import pipeline but the median anchor
        excludes them everywhere for structural symmetry (Pitfall 2).
        """
        sql = per_user_cte_median_anchor(tc, source="benchmark")
        assert "g.platform = 'chess.com'" in sql, (
            f"Daily drop chess.com clause missing for tc={tc!r}"
        )
        assert "time_control_str LIKE '1/%'" in sql, (
            f"Daily LIKE '1/%' clause missing for tc={tc!r}"
        )

    def test_platform_filter_lichess_emits_clause(self) -> None:
        """platform='lichess' adds AND g.platform = 'lichess' to the WHERE."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark", platform="lichess")
        assert "g.platform = 'lichess'" in sql

    def test_platform_filter_chesscom_emits_clause(self) -> None:
        """platform='chesscom' translates to AND g.platform = 'chess.com'.

        Phase 94.4 Plan 05b (Rule 1 auto-fix in canonical_slice_sql): the
        AnchorSource Literal value ``'chesscom'`` is mapped to the games
        table's storage literal ``'chess.com'`` (with the dot, per
        ``app/services/normalization.py``) at SQL-emit time. The builder
        accepts the dotless caller-side literal; the emitted SQL uses the
        dotted storage literal.
        """
        sql = per_user_cte_median_anchor("rapid", source="benchmark", platform="chesscom")
        assert "g.platform = 'chess.com'" in sql, (
            "platform='chesscom' must translate to the storage literal 'chess.com'"
        )

    def test_platform_none_omits_filter(self) -> None:
        """platform=None produces no platform filter beyond the Daily drop."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark", platform=None)
        # The Daily-drop clause references chess.com — that's expected. We need
        # to confirm there's no STANDALONE `AND g.platform = '<value>'` filter.
        # (We can't grep "g.platform = 'chess.com'" because the Daily drop uses
        # exactly that literal; instead assert the standalone-filter is
        # absent by looking for the exact emitted form.)
        assert "AND g.platform = 'lichess'" not in sql

    def test_default_min_games_uses_constant(self) -> None:
        """Default min_games is sourced from MEDIAN_ANCHOR_MIN_GAMES."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark")
        assert f"HAVING count(*) >= {MEDIAN_ANCHOR_MIN_GAMES}" in sql
        assert "HAVING count(*) >= 30" in sql  # belt-and-braces: also locked to 30

    def test_min_games_override_substitutes_in_having(self) -> None:
        """Explicit min_games override is f-stringed into the HAVING clause."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark", min_games=50)
        assert "HAVING count(*) >= 50" in sql
        assert "HAVING count(*) >= 30" not in sql, "Override must replace the default 30"

    @pytest.mark.parametrize("tc", _MEDIAN_ANCHOR_TCS)
    def test_emits_required_projection_columns(self, tc: TimeControlBucket) -> None:
        """per_user_anchor projects user_id, anchor_rating, n_games for the JOIN."""
        sql = per_user_cte_median_anchor(tc, source="benchmark")
        # Locate the per_user_anchor block.
        anchor_idx = sql.find("per_user_anchor AS")
        assert anchor_idx != -1
        block = sql[anchor_idx:]
        assert "user_id" in block, f"user_id projection missing for tc={tc!r}"
        assert "anchor_rating" in block, f"anchor_rating projection missing for tc={tc!r}"
        assert "n_games" in block, f"n_games projection missing for tc={tc!r}"

    def test_source_param_does_not_change_pooled_body(self) -> None:
        """source='benchmark' vs source='single_user' emits identical pooled body."""
        sql_bench = per_user_cte_median_anchor("rapid", source="benchmark")
        sql_single = per_user_cte_median_anchor("rapid", source="single_user")
        assert sql_bench == sql_single, (
            "source parameter must not alter the pooled body — cohort difference "
            "is exclusively in selected_users_cte (D-10)"
        )


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 1 — Pitfall 1 user_id widening on EXISTING 94.3
# per-TC builders. The cohort-CDF JOIN in Plan 04 requires user_id on the
# per_user_values projection of every per-TC builder so the (user_id) JOIN
# with per_user_anchor stays well-defined.
# ---------------------------------------------------------------------------


_PITFALL_1_EXISTING_94_3_BUILDERS: tuple[str, ...] = (
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)


def _per_user_values_block(sql: str) -> str:
    """Return the substring starting at the ``per_user_values AS`` CTE.

    Used by the Pitfall 1 assertions to scope the ``SELECT user_id,`` probe
    to the metric-emitting CTE rather than upstream CTEs (which may project
    ``user_id`` for unrelated reasons such as the per_user GROUP BY).
    """
    idx = sql.find("per_user_values AS")
    assert idx != -1, "per_user_values AS marker missing"
    return sql[idx:]


class TestPitfall1UserIdWideningExistingBuilders:
    """Phase 94.4 Plan 03 Task 1 — widen the 3 existing 94.3 per-TC builders.

    RESEARCH Pitfall 1 (lines 1168-1177): the cohort-CDF JOIN (Plan 04) joins
    ``per_user_values`` against ``per_user_anchor`` on ``user_id``. Without
    ``user_id`` exposed in ``per_user_values``, the JOIN loses user identity
    and the K=200 ranking by anchor distance is undefined.

    The widening is mechanical: prepend ``user_id,`` to the SELECT projection
    of ``per_user_values`` inside the 3 existing 94.3 per-TC builders
    (``per_user_cte_time_pressure_score_gap``, ``per_user_cte_clock_gap``,
    ``per_user_cte_net_flag_rate``). The upstream ``per_user`` CTE already
    GROUP BYs user_id (it's a per-user aggregate by construction) so no
    upstream change is needed.
    """

    @pytest.mark.parametrize("builder_family", _PITFALL_1_EXISTING_94_3_BUILDERS)
    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_per_user_values_projects_user_id_for_existing_per_tc_builders(
        self, builder_family: str, tc: TimeControlBucket
    ) -> None:
        """``per_user_values`` projects ``user_id`` on every (existing-family × TC) cell.

        Parametrised: 3 existing 94.3 builders × 4 TCs = 12 cases.
        """
        metric_id = f"{builder_family}_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        block = _per_user_values_block(sql)
        # Tolerant probe: accepts ``SELECT user_id,`` or ``SELECT\n  user_id,``
        # (multi-line emission). Use re.search with whitespace tolerance.
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"per_user_values must project user_id for {metric_id} "
            f"(Pitfall 1 — cohort-CDF JOIN requirement). Block was:\n{block[:400]}"
        )

    @pytest.mark.parametrize("builder_family", _PITFALL_1_EXISTING_94_3_BUILDERS)
    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_per_user_values_has_pitfall_1_comment_for_existing_builders(
        self, builder_family: str, tc: TimeControlBucket
    ) -> None:
        """Each widened ``per_user_values`` body carries a Pitfall 1 provenance comment.

        The comment is grep-able so future readers can trace the user_id
        projection to its source decision (RESEARCH Pitfall 1).
        """
        metric_id = f"{builder_family}_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        block = _per_user_values_block(sql)
        assert "user_id widened per Phase 94.4 Pitfall 1" in block, (
            f"Pitfall 1 provenance comment missing in per_user_values for {metric_id}; "
            f"block:\n{block[:400]}"
        )

    def test_non_per_tc_builders_are_not_touched_by_pitfall_1(self) -> None:
        """The 4 non-per-TC builders are NOT widened by Task 1 (scope guard).

        Task 1 is scoped to the 3 existing 94.3 per-TC builders. The original
        pooled builders (``per_user_cte_score_gap`` / ``per_user_cte_achievable``
        / ``per_user_cte_score_gap_bucket``) are widened in Task 2 only — Task 1 must
        leave them untouched so we can detect a scope leak.
        """
        for metric_id in _METRICS:
            sql = per_user_cte_for(metric_id, source="single_user")
            block = _per_user_values_block(sql)
            assert "user_id widened per Phase 94.4 Pitfall 1" not in block, (
                f"Pitfall 1 comment leaked into non-per-TC builder {metric_id} during Task 1; "
                f"that widening is Task 2 territory."
            )

    @pytest.mark.parametrize("builder_family", _PITFALL_1_EXISTING_94_3_BUILDERS)
    @pytest.mark.parametrize("tc", _TIME_PRESSURE_TCS)
    def test_widened_sql_parses_via_sqlalchemy_text(
        self, builder_family: str, tc: TimeControlBucket
    ) -> None:
        """SQLAlchemy ``text()`` accepts the widened SQL shape (parse-level smoke).

        Wraps the builder output in a minimal ``SELECT user_id FROM per_user_values``
        and asserts ``text(sql).compile()`` does not raise. This is a parser
        smoke test, not a DB-execution test — it catches malformed SQL emitted
        by the widening edit (e.g. trailing comma, dangling SELECT).
        """
        metric_id = f"{builder_family}_{tc}"
        sql = per_user_cte_for(metric_id, source="single_user")  # ty: ignore[invalid-argument-type]  # Plan C widens CdfMetricId
        # Prepend the single_user `selected_users` preamble so the WITH chain is complete.
        preamble = selected_users_cte(source="single_user")
        wrapped = f"WITH {preamble},\n{sql}\nSELECT user_id FROM per_user_values"
        compiled = text(wrapped).bindparams(user_id=42).compile()
        assert compiled is not None


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 2 — 4 new per-TC ΔES builders + score-gap-bucket bucket_label
# extension to include 'recovery'. RESEARCH Pattern 6 lines 569-669.
# ---------------------------------------------------------------------------


_NEW_PER_TC_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")
_SCORE_GAP_BUCKETS: tuple[Literal["conversion", "parity", "recovery"], ...] = (
    "conversion",
    "parity",
    "recovery",
)


class TestPerUserCteScoreGapTc:
    """``per_user_cte_score_gap_tc(tc, *, source, snapshot_date)`` (Task 2.1)."""

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_emits_per_tc_predicate(
        self, tc: TimeControlBucket, source: Literal["benchmark", "single_user"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source=source)
        assert f"g.time_control_bucket = '{tc}'" in sql, (
            f"per-TC predicate missing for tc={tc!r}/source={source!r}"
        )

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_per_user_values_projects_user_id_metric_value_n_games(
        self, tc: TimeControlBucket
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"per_user_values must project user_id for score_gap_tc({tc}) (Pitfall 1)"
        )
        assert "metric_value" in block
        assert "n_games" in block

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_metric_value_formula_matches_non_per_tc_analog(self, tc: TimeControlBucket) -> None:
        """metric_value formula mirrors per_user_cte_score_gap: eg_score - non_eg_score."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source="benchmark")
        assert "(eg_score - non_eg_score) AS metric_value" in sql, (
            f"score_gap metric_value formula divergent for tc={tc!r}"
        )

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_having_floors_match_non_per_tc_analog(self, tc: TimeControlBucket) -> None:
        """HAVING gates both ≥30 (endgame + non-endgame) per D-6."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source="benchmark")
        assert "HAVING count(*) FILTER (WHERE has_endgame)     >= 30" in sql
        assert "AND count(*) FILTER (WHERE NOT has_endgame) >= 30" in sql

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_pitfall_1_comment_present(self, tc: TimeControlBucket) -> None:
        """Per-TC builders emitted in Task 2 also carry the Pitfall 1 comment."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert "user_id widened per Phase 94.4 Pitfall 1" in block

    def test_source_mode_pooled_body_byte_identical(self) -> None:
        """source='benchmark' vs source='single_user' emit identical pooled body."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        bm = per_user_cte_score_gap_tc("blitz", source="benchmark")
        su = per_user_cte_score_gap_tc("blitz", source="single_user")
        assert bm == su, (
            "source parameter must not alter the pooled body for score_gap_tc "
            "(D-10 byte-identical guarantee)"
        )


class TestPerUserCteAchievableTc:
    """``per_user_cte_achievable_tc(tc, *, source, snapshot_date)`` (Task 2.2)."""

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_emits_per_tc_predicate(
        self, tc: TimeControlBucket, source: Literal["benchmark", "single_user"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        sql = per_user_cte_achievable_tc(tc, source=source)
        assert f"g.time_control_bucket = '{tc}'" in sql

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_per_user_values_projects_user_id_metric_value_n_games(
        self, tc: TimeControlBucket
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        sql = per_user_cte_achievable_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"per_user_values must project user_id for achievable_tc({tc}) (Pitfall 1)"
        )
        assert "metric_value" in block
        assert "n_games" in block

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_having_floor_matches_non_per_tc_analog(self, tc: TimeControlBucket) -> None:
        """HAVING gate ≥30 on count(d_i IS NOT NULL) per D-6."""
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        sql = per_user_cte_achievable_tc(tc, source="benchmark")
        assert "HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= 30" in sql

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_pitfall_1_comment_present(self, tc: TimeControlBucket) -> None:
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        sql = per_user_cte_achievable_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert "user_id widened per Phase 94.4 Pitfall 1" in block

    def test_source_mode_pooled_body_byte_identical(self) -> None:
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        bm = per_user_cte_achievable_tc("rapid", source="benchmark")
        su = per_user_cte_achievable_tc("rapid", source="single_user")
        assert bm == su


class TestPerUserCteSection2Tc:
    """``per_user_cte_score_gap_bucket_tc(tc, *, source, snapshot_date, bucket_label)`` (Task 2.4)."""

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_emits_per_tc_predicate_for_all_buckets(
        self,
        tc: TimeControlBucket,
        bucket_label: Literal["conversion", "parity", "recovery"],
        source: Literal["benchmark", "single_user"],
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        sql = per_user_cte_score_gap_bucket_tc(tc, source=source, bucket_label=bucket_label)
        assert f"g.time_control_bucket = '{tc}'" in sql

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    def test_per_user_values_projects_user_id_metric_value_n_games(
        self,
        tc: TimeControlBucket,
        bucket_label: Literal["conversion", "parity", "recovery"],
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        sql = per_user_cte_score_gap_bucket_tc(tc, source="benchmark", bucket_label=bucket_label)
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block), (
            f"per_user_values must project user_id for score_gap_bucket_tc({tc}, {bucket_label})"
        )
        assert "metric_value" in block
        assert "n_games" in block

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    def test_emits_bucket_where_dispatch(
        self,
        tc: TimeControlBucket,
        bucket_label: Literal["conversion", "parity", "recovery"],
    ) -> None:
        """``WHERE bucket = '{bucket_label}'`` dispatch is f-stringed correctly."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        sql = per_user_cte_score_gap_bucket_tc(tc, source="benchmark", bucket_label=bucket_label)
        assert f"WHERE bucket = '{bucket_label}'" in sql

    def test_recovery_branch_returns_non_empty_sql(self) -> None:
        """bucket_label='recovery' on per_user_cte_score_gap_bucket_tc emits valid SQL.

        The recovery rows are produced by the existing gap_rows CASE
        classification (entry_eval_mate < 0 user-color signed OR
        entry_eval_cp * sign <= -100). The widening is purely at the Literal
        type level + the bucket WHERE-clause dispatch.
        """
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        sql = per_user_cte_score_gap_bucket_tc("blitz", source="benchmark", bucket_label="recovery")
        assert sql
        assert "WHERE bucket = 'recovery'" in sql

    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    def test_source_mode_pooled_body_byte_identical(
        self, bucket_label: Literal["conversion", "parity", "recovery"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        bm = per_user_cte_score_gap_bucket_tc(
            "blitz", source="benchmark", bucket_label=bucket_label
        )
        su = per_user_cte_score_gap_bucket_tc(
            "blitz", source="single_user", bucket_label=bucket_label
        )
        assert bm == su


class TestPerUserCteSection2RecoveryWidening:
    """The existing (non-per-TC) ``per_user_cte_score_gap_bucket`` accepts ``bucket_label='recovery'``.

    Task 2.3 — the widening is purely at the Literal type level. The existing
    ``gap_rows`` CASE already classifies recovery rows (lines 502-512 of
    canonical_slice_sql.py): entry_eval_mate < 0 signed by user_color, OR
    entry_eval_cp * sign <= -100. The downstream WHERE clause selects rows
    where bucket = bucket_label, so 'recovery' just flips the dispatch.
    """

    def test_score_gap_bucket_accepts_recovery_bucket_label(self) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket

        sql = per_user_cte_score_gap_bucket(source="benchmark", bucket_label="recovery")
        assert sql
        assert "WHERE bucket = 'recovery'" in sql

    def test_score_gap_bucket_recovery_preserves_existing_conversion_parity_behavior(self) -> None:
        """The existing conversion / parity dispatch is byte-identical post-widening."""
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket

        sql_conv = per_user_cte_score_gap_bucket(source="benchmark", bucket_label="conversion")
        sql_par = per_user_cte_score_gap_bucket(source="benchmark", bucket_label="parity")
        assert "WHERE bucket = 'conversion'" in sql_conv
        assert "WHERE bucket = 'parity'" in sql_par
        # And the conversion/parity bodies still pool by user_id.
        assert "GROUP BY user_id, bucket" in sql_conv
        assert "GROUP BY user_id, bucket" in sql_par

    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    def test_score_gap_bucket_source_mode_byte_identical_for_all_buckets(
        self, bucket_label: Literal["conversion", "parity", "recovery"]
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket

        bm = per_user_cte_score_gap_bucket(source="benchmark", bucket_label=bucket_label)
        su = per_user_cte_score_gap_bucket(source="single_user", bucket_label=bucket_label)
        assert bm == su

    def test_score_gap_bucket_recovery_per_user_values_widening_optional(self) -> None:
        """The non-per-TC ``per_user_cte_score_gap_bucket`` is NOT touched by Plan 03 Pitfall 1.

        Pitfall 1 widening is scoped to per-TC builders only (Plan 04's cohort-CDF
        JOIN consumes per-TC builders, not the non-per-TC family). The non-per-TC
        score-gap-bucket builder's per_user_values is allowed to omit user_id under Plan 03.
        Plan 05 may revisit this when per-user service consumption is wired.
        """
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket

        sql = per_user_cte_score_gap_bucket(source="benchmark", bucket_label="recovery")
        block = _per_user_values_block(sql)
        # No Pitfall 1 comment — non-per-TC builder is out of Task 1/2 scope.
        assert "user_id widened per Phase 94.4 Pitfall 1" not in block


class TestPitfall1UserIdWideningNewBuilders:
    """The 4 new Task 2 per-TC builders all project user_id (Pitfall 1).

    This class covers the new builders explicitly so a regression in any
    one is caught even if the per-builder test classes above are restructured.
    Parametrized: 4 new builders × 4 TCs = 16 cells.
    """

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_score_gap_tc_user_id(self, tc: TimeControlBucket) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_tc

        sql = per_user_cte_score_gap_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block)

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    def test_achievable_tc_user_id(self, tc: TimeControlBucket) -> None:
        from app.services.canonical_slice_sql import per_user_cte_achievable_tc

        sql = per_user_cte_achievable_tc(tc, source="benchmark")
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block)

    @pytest.mark.parametrize("tc", _NEW_PER_TC_TCS)
    @pytest.mark.parametrize("bucket_label", _SCORE_GAP_BUCKETS)
    def test_score_gap_bucket_tc_user_id(
        self,
        tc: TimeControlBucket,
        bucket_label: Literal["conversion", "parity", "recovery"],
    ) -> None:
        from app.services.canonical_slice_sql import per_user_cte_score_gap_bucket_tc

        sql = per_user_cte_score_gap_bucket_tc(tc, source="benchmark", bucket_label=bucket_label)
        block = _per_user_values_block(sql)
        assert re.search(r"SELECT\s+user_id\s*,", block)
