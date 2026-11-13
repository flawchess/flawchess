"""Pure unit tests for scripts/blunder_check/metrics.py (SEED-261108-dk0, Phase 248).

No DB, no Maia. The tracer builds a synthetic game of GamePosition objects and runs the
real flaw pipeline's _run_all_moves_pass so the ES convention is the classifier's own.
"""

from __future__ import annotations

import pytest

from app.models.game_position import GamePosition
from app.services.flaws_service import INACCURACY_DROP, _MoveEntry, _run_all_moves_pass
from scripts.blunder_check.metrics import (
    HAZARD,
    EloBucket,
    WINDOW_LENGTHS,
    MoveJudgement,
    SupplyRates,
    auc,
    blunder_es,
    capped_blunder_supply,
    count_herring_windows,
    elo_bucket,
    estimated_user_windows,
    flaw_control,
    herring_flags,
    quartiles,
    weighted_fit_share,
    blunder_fits_position,
    blunder_position_marginals,
    in_band,
    miss_case,
    user_move_judgements,
)

BAND_LOW = 0.40
BAND_HIGH = 0.90
HAZARD_TOLERANCE = 1e-3
BLUNDER_PLY = 8
OPPONENT_BLUNDER_PLY = 7
HOLD_CP = 100
GIFT_CP = 500


def _synthetic_game() -> list[GamePosition]:
    """White user holds +100 cp, black blunders at ply 7 (to +500), white gives it back at ply 8."""
    evals = [HOLD_CP] * (BLUNDER_PLY + 1)
    evals[OPPONENT_BLUNDER_PLY] = GIFT_CP
    return [GamePosition(eval_cp=cp, eval_mate=None) for cp in evals]


class TestTracer:
    def test_blunder_case_and_window_fit_from_real_pipeline(self) -> None:
        all_moves = _run_all_moves_pass(_synthetic_game())
        assert all_moves[OPPONENT_BLUNDER_PLY][1] == "blunder"
        assert all_moves[BLUNDER_PLY][1] == "blunder"

        es_before, es_played, es_ref = blunder_es(all_moves, BLUNDER_PLY)
        assert es_before is not None and es_played is not None and es_ref is not None
        # The user gave the whole gift back: played ES equals the reference ES.
        assert miss_case(True, es_ref, es_played) == "pure_miss"

        judgements = user_move_judgements(
            all_moves, list(range(1, BLUNDER_PLY + 1)), user_is_white=True
        )
        assert [j.ply for j in judgements] == [2, 4, 6, 8]
        preceding = [j for j in judgements if j.ply < BLUNDER_PLY]
        assert all(j.good for j in preceding)
        assert blunder_fits_position(preceding, es_before, 4, BAND_LOW, BAND_HIGH)
        # Position 5 needs four preceding Good in-band moves; only three exist.
        assert not blunder_fits_position(preceding, es_before, 5, BAND_LOW, BAND_HIGH)

    def test_out_of_band_preceding_move_breaks_the_fit(self) -> None:
        preceding = [
            MoveJudgement(2, True, 0.55),
            MoveJudgement(4, True, 0.97),
            MoveJudgement(6, True, 0.55),
        ]
        assert not blunder_fits_position(preceding, 0.6, 4, BAND_LOW, BAND_HIGH)
        assert blunder_fits_position(preceding, 0.6, 2, BAND_LOW, BAND_HIGH)

    def test_non_good_preceding_move_breaks_the_fit(self) -> None:
        preceding = [MoveJudgement(2, True, 0.55), MoveJudgement(4, False, 0.55)]
        assert not blunder_fits_position(preceding, 0.6, 3, BAND_LOW, BAND_HIGH)

    def test_position_one_needs_only_the_blunder_in_band(self) -> None:
        assert blunder_fits_position([], 0.6, 1, BAND_LOW, BAND_HIGH)
        assert not blunder_fits_position([], 0.95, 1, BAND_LOW, BAND_HIGH)
        assert not blunder_fits_position([], None, 1, BAND_LOW, BAND_HIGH)

    def test_inaccuracy_is_not_good(self) -> None:
        # ~0.07 ES drop on the user's move at ply 2 is an inaccuracy: severity set, so not Good.
        positions = [
            GamePosition(eval_cp=0, eval_mate=None),
            GamePosition(eval_cp=0, eval_mate=None),
            GamePosition(eval_cp=-80, eval_mate=None),
        ]
        all_moves = _run_all_moves_pass(positions)
        assert all_moves[2][1] == "inaccuracy"
        judgements = user_move_judgements(all_moves, [1, 2], user_is_white=True)
        assert [(j.ply, j.good) for j in judgements] == [(2, False)]

    def test_missing_ply_is_not_good(self) -> None:
        judgements = user_move_judgements({}, [2], user_is_white=True)
        assert judgements == [MoveJudgement(2, False, None)]

    def test_blunder_es_without_previous_entry(self) -> None:
        all_moves = _run_all_moves_pass(_synthetic_game())
        es_before, es_played, es_ref = blunder_es(
            {BLUNDER_PLY: all_moves[BLUNDER_PLY]}, BLUNDER_PLY
        )
        assert es_before is not None and es_played is not None
        assert es_ref is None
        assert blunder_es({}, BLUNDER_PLY) == (None, None, None)


class TestMissCase:
    def test_boundary_is_inclusive(self) -> None:
        es_ref = 0.7
        boundary = es_ref - INACCURACY_DROP
        assert miss_case(True, es_ref, boundary) == "pure_miss"
        assert miss_case(True, es_ref, boundary - 1e-9) == "mixed"

    def test_not_a_miss_is_allowed_regardless_of_es(self) -> None:
        assert miss_case(False, 0.9, 0.1) == "allowed"
        assert miss_case(False, None, None) == "allowed"

    def test_unknown_reference_is_unclassified(self) -> None:
        assert miss_case(True, None, 0.5) == "unclassified"
        assert miss_case(True, 0.5, None) == "unclassified"


class TestInBand:
    def test_edges_inclusive_and_none(self) -> None:
        assert in_band(BAND_LOW, BAND_LOW, BAND_HIGH)
        assert in_band(BAND_HIGH, BAND_LOW, BAND_HIGH)
        assert not in_band(BAND_HIGH + 1e-9, BAND_LOW, BAND_HIGH)
        assert not in_band(None, BAND_LOW, BAND_HIGH)


class TestBlunderPositionMarginals:
    def test_d12_numbers(self) -> None:
        # Hand-derived: length uniform over 3, 4, 5 and position k within a length L weighted
        # h * (1 - h)^(k - 1) / (1 - (1 - h)^L); only L = 5 reaches position 5, so its marginal is
        # (1 / 3) * 0.265 * 0.735^4 / (1 - 0.735^5) = 0.0328.
        w = blunder_position_marginals()
        expected = {1: 0.3837, 2: 0.2820, 3: 0.2073, 4: 0.0942, 5: 0.0328}
        for k, value in expected.items():
            assert w[k] == pytest.approx(value, abs=HAZARD_TOLERANCE / 10)
        assert sum(w.values()) == pytest.approx(1.0)

    def test_defaults_match_constants_and_a_single_length_is_the_conditional_weights(self) -> None:
        assert blunder_position_marginals() == blunder_position_marginals(WINDOW_LENGTHS)
        single = blunder_position_marginals((3,))
        assert set(single) == {1, 2, 3}
        assert single[1] > single[2] > single[3]
        assert HAZARD == pytest.approx(0.265)


class TestEloBucket:
    def test_edges(self) -> None:
        assert elo_bucket(799.9) == "<800"
        assert elo_bucket(800.0) == "800-1199"
        assert elo_bucket(1199.9) == "800-1199"
        assert elo_bucket(1600.0) == "1600-1999"
        assert elo_bucket(2399.9) == "2000-2399"
        assert elo_bucket(2400.0) == "2400+"


class TestHerringWindows:
    def test_disjoint_windows_per_run(self) -> None:
        flags = [True, True, True, False, True, True, True, True, True, True]
        assert count_herring_windows(flags, 3) == 3

    def test_empty_and_all_false(self) -> None:
        assert count_herring_windows([], 3) == 0
        assert count_herring_windows([False] * 6, 3) == 0

    def test_flags_require_good_and_in_band(self) -> None:
        judgements = [
            MoveJudgement(2, True, 0.55),
            MoveJudgement(4, False, 0.55),
            MoveJudgement(6, True, 0.99),
            MoveJudgement(8, True, 0.40),
        ]
        assert herring_flags(judgements, BAND_LOW, BAND_HIGH) == [True, False, False, True]


class TestSupply:
    def test_cap_binds_or_not(self) -> None:
        assert capped_blunder_supply(70, 50, 0.30) == pytest.approx(100, abs=1e-9)
        assert capped_blunder_supply(70, 10, 0.30) == pytest.approx(80, abs=1e-9)

    def test_weighted_fit_share(self) -> None:
        weights = blunder_position_marginals()
        fit = {1: 1.0, 2: 0.5, 3: 0.0, 4: 0.0, 5: 0.0}
        assert weighted_fit_share(fit, weights) == pytest.approx(
            0.3837 + 0.5 * 0.2820, abs=HAZARD_TOLERANCE
        )

    def test_estimated_user_windows(self) -> None:
        rates: dict[EloBucket, SupplyRates] = {
            "1200-1599": SupplyRates(non_pure_rate=0.2, pure_rate=0.2, fit_share=0.5)
        }
        expected = (20 + min(20, 0.3 / 0.7 * 20)) * 0.5
        assert estimated_user_windows({"1200-1599": 100}, rates) == pytest.approx(
            expected, abs=1e-6
        )
        # A bucket with no rates contributes nothing.
        assert estimated_user_windows({"1200-1599": 100, "2400+": 50}, rates) == pytest.approx(
            expected, abs=1e-6
        )


class TestStatistics:
    def test_auc_with_tie(self) -> None:
        assert auc([0.5, 0.4], [0.1, 0.4]) == pytest.approx(0.875)

    def test_auc_empty_is_none(self) -> None:
        assert auc([], [0.1]) is None
        assert auc([0.1], []) is None

    def test_quartiles(self) -> None:
        assert quartiles([1, 2, 3, 4, 5]) == (2.0, 3.0, 4.0)
        assert quartiles([1.0]) is None


class TestFlawControl:
    def test_agreement_counts(self) -> None:
        all_moves: dict[int, _MoveEntry] = {
            3: ("black", "mistake", 0.6, 0.45),
            8: ("white", "blunder", 0.6, 0.3),
            9: ("black", "inaccuracy", 0.5, 0.44),
        }
        assert flaw_control(all_moves, {3: 1, 8: 2}) == (2, 2)

    def test_mismatch_missing_and_unstored_are_disagreements(self) -> None:
        all_moves: dict[int, _MoveEntry] = {
            3: ("black", "mistake", 0.6, 0.45),
            8: ("white", "blunder", 0.6, 0.3),
        }
        # severity mismatch at 3, stored-only ply 5, recomputed-only ply 8; none agree.
        assert flaw_control(all_moves, {3: 2, 5: 1}) == (0, 3)
