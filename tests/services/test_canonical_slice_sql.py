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
    _recent_capped_per_tc_cte,
    elo_bucket_expr,
    equal_footing_filter_sql,
    per_user_cte_for,
    per_user_cte_median_anchor,
    selected_users_cte,
    sparse_exclusion_sql,
)
from app.services.global_percentile_cdf import CdfMetricId

# ---------------------------------------------------------------------------
# Parametrise constants.
# ---------------------------------------------------------------------------

_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
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
    """36-month recency anchor + 1000-per-TC cap (D-5)."""

    @pytest.mark.parametrize("metric_id", _METRICS)
    @pytest.mark.parametrize("source", _SOURCES)
    def test_recent_1000_per_tc_cap_substrings_present(
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
            f"1000-per-TC cap missing for {metric_id}/{source}"
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
        """``<= 1000`` should appear exactly once in the rendered SQL (single capping site)."""
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

    def test_section2_conv_having_gates_30(self) -> None:
        sql = per_user_cte_for("section2_score_gap_conv", source="single_user")
        # The HAVING gate inside per_user_bucket is "HAVING count(*) >= 30".
        assert "HAVING count(*) >= 30" in sql
        # And the per_user_values WHERE clause selects the conversion bucket.
        assert "bucket = 'conversion'" in sql

    def test_section2_parity_having_gates_30(self) -> None:
        sql = per_user_cte_for("section2_score_gap_parity", source="single_user")
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
        """platform='chesscom' adds AND g.platform = 'chesscom' to the WHERE."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark", platform="chesscom")
        assert "g.platform = 'chesscom'" in sql

    def test_platform_none_omits_filter(self) -> None:
        """platform=None produces no platform filter beyond the Daily drop."""
        sql = per_user_cte_median_anchor("rapid", source="benchmark", platform=None)
        # The Daily-drop clause references chess.com — that's expected. We need
        # to confirm there's no STANDALONE `AND g.platform = '<value>'` filter.
        assert "AND g.platform = 'lichess'" not in sql
        assert "AND g.platform = 'chesscom'" not in sql

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
