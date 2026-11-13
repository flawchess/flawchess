"""Unit tests for app/services/blunder_check_rules.py (SEED-261108-dk0, Phase 249).

No DB, no Maia. The tracer builds a synthetic game of GamePosition objects and runs the real
flaw pipeline's _run_all_moves_pass so the ES convention is the classifier's own, then drives
the app-owned selection rules to the expected case and window fit.
"""

from __future__ import annotations

from app.models.game_position import GamePosition
from app.services import blunder_check_rules as rules
from app.services.blunder_check_rules import (
    BEST_PROB_MIN,
    BETTER_MOVE_POINTS,
    BLUNDER_CHECK_SESSION_WINDOWS,
    BLUNDER_POINTS,
    ES_BAND_HIGH,
    ES_BAND_LOW,
    MAX_BLUNDER_POSITION,
    REFUTATION_PROB_MIN,
    SAFE_POINTS,
    FindabilityInputs,
    MoveJudgement,
    blunder_es,
    findable,
    max_fit_position,
    miss_case,
    user_move_judgements,
)
from app.services.flaws_service import _run_all_moves_pass
from scripts.blunder_check import metrics, spot_check

BLUNDER_PLY = 8
OPPONENT_BLUNDER_PLY = 7
HOLD_CP = 100
GIFT_CP = 500
IN_BAND_ES = 0.55
OUT_OF_BAND_ES = 0.95


def _synthetic_game() -> list[GamePosition]:
    """White user holds +100 cp, black blunders at ply 7 (to +500), white gives it back at ply 8."""
    evals = [HOLD_CP] * (BLUNDER_PLY + 1)
    evals[OPPONENT_BLUNDER_PLY] = GIFT_CP
    return [GamePosition(eval_cp=cp, eval_mate=None) for cp in evals]


def _inputs(
    refutation: tuple[float | None, int | None] = (None, None),
    best: tuple[float | None, int | None] = (None, None),
) -> FindabilityInputs:
    return FindabilityInputs(
        refutation_prob=refutation[0],
        refutation_rank=refutation[1],
        best_prob=best[0],
        best_rank=best[1],
    )


class TestTracer:
    def test_app_rules_judge_a_synthetic_game_end_to_end(self) -> None:
        all_moves = _run_all_moves_pass(_synthetic_game())
        assert all_moves[OPPONENT_BLUNDER_PLY][1] == "blunder"
        assert all_moves[BLUNDER_PLY][1] == "blunder"

        es_before, es_played, es_ref = blunder_es(all_moves, BLUNDER_PLY)
        assert es_before is not None and es_played is not None and es_ref is not None
        # The user gave the whole gift back, so this blunder is a pure miss.
        case = miss_case(True, es_ref, es_played)
        assert case == "pure_miss"

        judgements = user_move_judgements(
            all_moves, list(range(1, BLUNDER_PLY + 1)), user_is_white=True
        )
        preceding = [j for j in judgements if j.ply < BLUNDER_PLY]
        assert all(j.good for j in preceding)
        # Pure miss: the best pair decides; 0.25 clears X' = 0.2, the refutation pair is ignored.
        assert findable(case, _inputs(best=(0.25, 3)), REFUTATION_PROB_MIN, BEST_PROB_MIN)
        assert not findable(
            case, _inputs(best=(0.1, 3), refutation=(0.9, 1)), REFUTATION_PROB_MIN, BEST_PROB_MIN
        )
        # Three clean preceding moves in band: the blunder fits positions 1..4 but not 5.
        assert max_fit_position(preceding, es_before) == 4


class TestSharedImplementation:
    def test_report_reexports_are_the_app_objects(self) -> None:
        assert metrics.findable is rules.findable
        assert metrics.blunder_fits_position is rules.blunder_fits_position
        assert metrics.HAZARD is rules.HAZARD
        assert spot_check.draw_window_shape is rules.draw_window_shape
        assert spot_check.WindowShape is rules.WindowShape


class TestConstants:
    def test_named_constants(self) -> None:
        assert BETTER_MOVE_POINTS == 2
        assert BLUNDER_CHECK_SESSION_WINDOWS == 6
        assert (SAFE_POINTS, BLUNDER_POINTS) == (1, 3)
        assert (ES_BAND_LOW, ES_BAND_HIGH) == (0.10, 0.90)
        assert (REFUTATION_PROB_MIN, BEST_PROB_MIN) == (0.3, 0.2)


class TestMaxFitPosition:
    def test_no_preceding_moves_in_band_is_position_one(self) -> None:
        assert max_fit_position([], IN_BAND_ES) == 1

    def test_inaccuracy_two_moves_back_caps_the_position(self) -> None:
        preceding = [
            MoveJudgement(2, False, IN_BAND_ES),
            MoveJudgement(4, True, IN_BAND_ES),
            MoveJudgement(6, True, IN_BAND_ES),
        ]
        # Position 3 needs the last two moves clean; position 4 would need the inaccuracy.
        assert max_fit_position(preceding, IN_BAND_ES) == 3

    def test_inaccuracy_directly_before_leaves_only_position_one(self) -> None:
        preceding = [MoveJudgement(2, True, IN_BAND_ES), MoveJudgement(4, False, IN_BAND_ES)]
        assert max_fit_position(preceding, IN_BAND_ES) == 1

    def test_out_of_band_pre_move_es_fits_nowhere(self) -> None:
        assert max_fit_position([], OUT_OF_BAND_ES) == 0
        assert max_fit_position([], None) == 0

    def test_five_clean_preceding_moves_reach_the_maximum(self) -> None:
        preceding = [MoveJudgement(ply, True, IN_BAND_ES) for ply in range(2, 12, 2)]
        assert len(preceding) == MAX_BLUNDER_POSITION
        assert max_fit_position(preceding, IN_BAND_ES) == MAX_BLUNDER_POSITION

    def test_out_of_band_preceding_move_caps_the_position(self) -> None:
        preceding = [
            MoveJudgement(2, True, OUT_OF_BAND_ES),
            MoveJudgement(4, True, IN_BAND_ES),
            MoveJudgement(6, True, IN_BAND_ES),
        ]
        assert max_fit_position(preceding, IN_BAND_ES) == 3
