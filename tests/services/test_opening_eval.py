"""Unit tests for app.services.opening_eval (Openings-only baseline-centred eval, D-13)."""

import math

import pytest

from app.repositories.stats_repository import OpeningPhaseEntryMetrics
from app.services.opening_eval import (
    CENTIPAWNS_PER_PAWN,
    empty_opening_eval_fields,
    finalize_opening_eval,
    resolve_eval_baseline_pawns,
)
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
    OPENING_INSIGHTS_CI_Z_95,
)


def _metrics(evals_cp: list[int]) -> OpeningPhaseEntryMetrics:
    return OpeningPhaseEntryMetrics(
        eval_sum_mg=float(sum(evals_cp)),
        eval_sumsq_mg=float(sum(cp * cp for cp in evals_cp)),
        eval_n_mg=len(evals_cp),
        mate_n_mg=0,
        null_eval_n_mg=0,
        outlier_n_mg=0,
    )


# 12 games, mean exactly +25 cp, non-zero variance.
_MEAN_PLUS_25 = [5, 15, 20, 25, 25, 25, 25, 25, 30, 35, 45, 25]


class TestResolveEvalBaseline:
    def test_white_black_and_none(self) -> None:
        assert resolve_eval_baseline_pawns("white") == EVAL_BASELINE_PAWNS_WHITE
        assert resolve_eval_baseline_pawns("black") == EVAL_BASELINE_PAWNS_BLACK
        # None follows the existing "None means white" convention.
        assert resolve_eval_baseline_pawns(None) == EVAL_BASELINE_PAWNS_WHITE


class TestFinalizeOpeningEval:
    def test_fixture_mean_is_exactly_plus_25(self) -> None:
        assert sum(_MEAN_PLUS_25) / len(_MEAN_PLUS_25) == 25

    def test_white_mean_at_the_baseline_reads_as_typical(self) -> None:
        fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), "white")
        assert fields["eval_confidence"] == "low"
        assert fields["eval_p_value"] == pytest.approx(1.0)

    def test_same_sums_as_black_are_far_from_the_black_baseline(self) -> None:
        """+25 cp is 50 cp above Black's -25 cp baseline, so it is a strong signal."""
        fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), "black")
        assert fields["eval_p_value"] is not None
        assert fields["eval_p_value"] < 0.01
        assert fields["eval_confidence"] == "high"

    def test_avg_eval_pawns_is_the_raw_uncentred_mean(self) -> None:
        for color in ("white", "black"):
            fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), color)
            assert fields["avg_eval_pawns"] == pytest.approx(25 / CENTIPAWNS_PER_PAWN)

    def test_ci_is_the_95_percent_normal_interval_around_the_mean(self) -> None:
        """D-33: the one CI pair is 95% (z95 * sd / sqrt(n)), symmetric around the mean."""
        evals = _MEAN_PLUS_25
        n = len(evals)
        mean = sum(evals) / n
        sd = math.sqrt(sum((cp - mean) ** 2 for cp in evals) / (n - 1))
        expected_half_pawns = OPENING_INSIGHTS_CI_Z_95 * sd / math.sqrt(n) / CENTIPAWNS_PER_PAWN

        fields = finalize_opening_eval(_metrics(evals), "white")

        assert fields["avg_eval_pawns"] is not None
        assert fields["eval_ci_low_pawns"] is not None
        assert fields["eval_ci_high_pawns"] is not None
        assert fields["eval_ci_high_pawns"] - fields["avg_eval_pawns"] == pytest.approx(
            expected_half_pawns
        )
        assert fields["avg_eval_pawns"] - fields["eval_ci_low_pawns"] == pytest.approx(
            expected_half_pawns
        )

    def test_no_99_percent_fields_are_returned(self) -> None:
        fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), "white")
        assert not any("ci99" in key for key in fields)
        assert not any("ci99" in key for key in empty_opening_eval_fields())

    def test_none_metrics_return_empty_fields(self) -> None:
        assert finalize_opening_eval(None, "white") == empty_opening_eval_fields()

    def test_zero_sample_returns_empty_fields(self) -> None:
        assert finalize_opening_eval(_metrics([]), "black") == empty_opening_eval_fields()

    def test_single_game_has_a_mean_but_no_ci(self) -> None:
        fields = finalize_opening_eval(_metrics([40]), "white")
        assert fields["avg_eval_pawns"] == pytest.approx(0.40)
        assert fields["eval_n"] == 1
        assert fields["eval_confidence"] == "low"
        assert fields["eval_ci_low_pawns"] is None
        assert fields["eval_ci_high_pawns"] is None

    def test_color_none_uses_the_white_baseline(self) -> None:
        none_fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), None)
        white_fields = finalize_opening_eval(_metrics(_MEAN_PLUS_25), "white")
        assert none_fields == white_fields

    def test_p_value_matches_a_hand_computed_z_test(self) -> None:
        evals = [10, 30, 50, 70, 90, 20, 40, 60, 80, 100, 35, 65]
        n = len(evals)
        mean = sum(evals) / n
        variance = sum((cp - mean) ** 2 for cp in evals) / (n - 1)
        z = (mean - EVAL_BASELINE_PAWNS_WHITE * CENTIPAWNS_PER_PAWN) / math.sqrt(variance / n)
        expected_p = math.erfc(abs(z) / math.sqrt(2.0))

        fields = finalize_opening_eval(_metrics(evals), "white")

        assert fields["eval_p_value"] == pytest.approx(expected_p)
