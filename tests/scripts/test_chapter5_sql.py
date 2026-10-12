"""DB-free assertions on the benchmarks §5 SQL shape and metric list (Phase 239-01).

The numeric diff gate (tests/scripts/benchmarks/test_chapter5_diff.py) needs the benchmark DB
and is excluded from normal pytest runs by pyproject addopts. This file is deliberately NOT
under tests/scripts/benchmarks/ so the normal suite pins the SQL text and the pure helpers:
the full-analysis basis, the metric lists, the cell floor and the safe verdict.
"""

from __future__ import annotations

import pytest

from scripts.benchmarks import chapter5, distribution as dist

# The 12 flaw-delta metrics, in report order (combos and the overall flaw rate are gone).
EXPECTED_FLAW_KEYS = [
    "mistake",
    "blunder",
    "low_clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame_phase",
    "miss",
    "lucky",
    "reversed",
    "squandered",
]

# Removed metric keys / the old cheap-eval basis must not appear in any §5 SQL string.
REMOVED_METRIC_KEYS = ("hasty_miss", "low_clock_miss", "flaw_rate")
OLD_BASIS_PREDICATE = "g.evals_completed_at IS NOT NULL"


def _distribution(n: int, *, p25: float = -0.001, p75: float = 0.001) -> dist.Distribution:
    return dist.Distribution(
        n=n, mean=0.0, sd=0.002, p05=-0.003, p25=p25, p50=0.0, p75=p75, p95=0.003
    )


def _marginal(label: str, n: int, mean: float = 0.0, var: float = 1e-6) -> dist.Marginal:
    return dist.Marginal(label=label, dist=_distribution(n), mean_raw=mean, var=var)


class TestFullAnalysisBasis:
    def test_tranches_are_classical_and_rapid_only(self) -> None:
        assert chapter5.FULL_ANALYSIS_TRANCHES == ("classical", "rapid")

    def test_base_cte_reads_the_lane_with_all_completion_predicates(self) -> None:
        cte = chapter5._base_games_cte()
        assert "FROM benchmark_selection bs" in cte
        assert "bs.armed" in cte
        assert "bs.tc_tranche IN ('classical', 'rapid')" in cte
        assert "g.full_evals_completed_at IS NOT NULL" in cte
        assert "g.full_pv_completed_at IS NOT NULL" in cte
        assert "g.blobs_completed_at IS NOT NULL" in cte
        # BASE_GAME_FILTER carries the TC anchor that keeps one selected_users row per game.
        assert "g.time_control_bucket::text = su.tc_bucket" in cte

    def test_blitz_and_bullet_never_enter_the_basis(self) -> None:
        cte = chapter5._base_games_cte()
        assert "'blitz'" not in cte
        assert "'bullet'" not in cte

    def test_per_user_and_viability_sql_embed_the_same_base_cte(self) -> None:
        cte = chapter5._base_games_cte()
        assert cte in chapter5._per_user_cte()
        assert cte in chapter5._viability_sql()

    @pytest.mark.parametrize("builder", ["_per_user_cte", "_viability_sql"])
    def test_old_cheap_eval_basis_and_removed_metrics_are_gone(self, builder: str) -> None:
        text = getattr(chapter5, builder)()
        assert OLD_BASIS_PREDICATE not in text
        for key in REMOVED_METRIC_KEYS:
            assert key not in text


class TestFlawMetricList:
    def test_exactly_the_twelve_keys_in_order(self) -> None:
        assert [k for k, _ in chapter5.FLAW_DELTA_METRICS] == EXPECTED_FLAW_KEYS

    def test_delta_column_follows_the_key(self) -> None:
        for key, col in chapter5.FLAW_DELTA_METRICS:
            assert col == f"delta_{key}"

    def test_predicates_cover_exactly_the_metric_keys(self) -> None:
        assert set(chapter5._FLAW_TAG_PREDICATES) == set(EXPECTED_FLAW_KEYS)

    def test_noise_variance_column_per_metric(self) -> None:
        cte = chapter5._per_user_cte()
        for key in EXPECTED_FLAW_KEYS:
            assert f"AS nv_{key}" in cte


class TestCellFloor:
    def test_level_below_floor_leaves_marginals_and_is_listed_thin(self) -> None:
        thin_n = chapter5._CELL_CONTRIBUTOR_FLOOR - 1
        elo = [_marginal("800", 120, mean=0.001), _marginal("1200", 150, mean=-0.001)]
        tc = [
            _marginal("rapid", 400, mean=0.0005),
            _marginal("classical", thin_n, mean=-0.0005),
        ]
        block = chapter5._assemble_block(_distribution(500), elo, tc)
        assert [m["label"] for m in block["tc_marginal"]] == ["rapid"]
        assert [m["label"] for m in block["elo_marginal"]] == ["800", "1200"]
        assert block["thin_levels"] == ["TC classical"]

    def test_level_at_floor_is_kept(self) -> None:
        at_floor = chapter5._CELL_CONTRIBUTOR_FLOOR
        tc = [_marginal("rapid", 400), _marginal("classical", at_floor)]
        block = chapter5._assemble_block(_distribution(500), [], tc)
        assert [m["label"] for m in block["tc_marginal"]] == ["rapid", "classical"]
        assert block["thin_levels"] == []

    def test_thin_level_does_not_feed_the_verdict(self) -> None:
        # classical is thin and wildly different; once dropped, TC has one level -> no verdict.
        tc = [_marginal("rapid", 400, mean=0.0), _marginal("classical", 5, mean=1.0)]
        block = chapter5._assemble_block(_distribution(500), [], tc)
        assert all(v["axis"] != "TC" for v in block["verdicts"])


class TestSafeVerdict:
    def test_single_level_yields_none_instead_of_raising(self) -> None:
        assert chapter5._safe_verdict("TC", [_marginal("rapid", 400)]) is None

    def test_zero_pooled_sd_yields_none_instead_of_raising(self) -> None:
        zero_var = [_marginal("rapid", 400, var=0.0), _marginal("classical", 400, var=0.0)]
        assert chapter5._safe_verdict("TC", zero_var) is None

    def test_two_eligible_levels_yield_a_verdict(self) -> None:
        two = [_marginal("rapid", 400, mean=0.0), _marginal("classical", 400, mean=0.002)]
        verdict = chapter5._safe_verdict("TC", two)
        assert verdict is not None
        assert verdict["axis"] == "TC"
        assert verdict["pair"] == ("rapid", "classical")

    def test_assemble_block_only_lists_computable_axes(self) -> None:
        tc = [_marginal("rapid", 400, mean=0.0), _marginal("classical", 400, mean=0.002)]
        block = chapter5._assemble_block(_distribution(800), [_marginal("800", 800)], tc)
        assert [v["axis"] for v in block["verdicts"]] == ["TC"]


class TestZoneViability:
    def test_degenerate_pooled_iqr_flags_the_block(self) -> None:
        degenerate = _distribution(100, p25=0.0, p75=0.0)
        block = chapter5._assemble_block(degenerate, [], [])
        assert block["degenerate"] is True

    def test_non_degenerate_pooled_iqr_does_not_flag_the_block(self) -> None:
        assert chapter5._assemble_block(_distribution(100), [], [])["degenerate"] is False

    def test_zone_viable_rule(self) -> None:
        assert chapter5._is_zone_viable(False, chapter5.VIABILITY_MIN_PCT_NONZERO) is True
        assert chapter5._is_zone_viable(False, chapter5.VIABILITY_MIN_PCT_NONZERO - 0.1) is False
        assert chapter5._is_zone_viable(True, 100.0) is False
