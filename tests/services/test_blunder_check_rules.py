"""Unit tests for app/services/blunder_check_rules.py (SEED-261108-dk0, Phase 249).

No DB, no Maia. The tracer builds a synthetic game of GamePosition objects and runs the real
flaw pipeline's _run_all_moves_pass so the ES convention is the classifier's own, then drives
the app-owned selection rules to the expected case and window fit.
"""

from __future__ import annotations

import random
from collections import Counter

import pytest

from app.models.game_position import GamePosition
from app.services import blunder_check_rules as rules
from app.services.blunder_check_rules import (
    BETTER_MOVE_POINTS,
    BLUNDER_CHECK_SESSION_WINDOWS,
    BLUNDER_POINTS,
    ES_BAND_HIGH,
    ES_BAND_LOW,
    FOREIGN_BLUNDER_SHARE,
    FOREIGN_RATING_BAND,
    HAZARD,
    HERRING_OWN_SHARE,
    HERRING_SHARE,
    MAX_BLUNDER_POSITION,
    OWN_BLUNDER_SHARE,
    SAFE_POINTS,
    WINDOW_LENGTHS,
    MoveJudgement,
    blunder_es,
    blunder_position_weights,
    draw_slot_plan,
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
        # Three clean preceding moves in band: the blunder fits positions 1..4 but not 5.
        assert max_fit_position(preceding, es_before) == 4


class TestSharedImplementation:
    def test_report_reexports_are_the_app_objects(self) -> None:
        assert metrics.blunder_fits_position is rules.blunder_fits_position
        assert metrics.HAZARD is rules.HAZARD
        assert spot_check.draw_slot_plan is rules.draw_slot_plan
        assert spot_check.WindowShape is rules.WindowShape


class TestConstants:
    def test_named_constants(self) -> None:
        assert BETTER_MOVE_POINTS == 2
        assert BLUNDER_CHECK_SESSION_WINDOWS == 6
        assert (SAFE_POINTS, BLUNDER_POINTS) == (1, 3)
        assert (ES_BAND_LOW, ES_BAND_HIGH) == (0.10, 0.90)


class TestRetiredSelectionCode:
    def test_the_249_findability_rule_and_the_hazard_weights_are_gone(self) -> None:
        retired = (
            "findable",
            "FindabilityInputs",
            "_pair_passes",
            "REFUTATION_PROB_MIN",
            "BEST_PROB_MIN",
            "hazard_position_weights",
            "HazardWeights",
        )
        assert [name for name in retired if hasattr(rules, name)] == []
        assert [name for name in retired if hasattr(metrics, name)] == []


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


# ---------------------------------------------------------------------------
# 250 D-12 / D-13 / D-16 slot plans
# ---------------------------------------------------------------------------

DRAWS = 30000
SHARE_TOLERANCE = 0.02
PLAN_SEED = 250
SESSION_SEED = 12
SESSIONS = 1000
SESSION_SLOTS = 6
MANY_HERRINGS = 3


class TestSlotShares:
    def test_named_constants(self) -> None:
        assert (HERRING_SHARE, OWN_BLUNDER_SHARE) == (1 / 3, 1 / 3)
        assert FOREIGN_BLUNDER_SHARE == pytest.approx(1 / 3)
        assert HERRING_OWN_SHARE == pytest.approx(0.5)
        assert FOREIGN_RATING_BAND == 150

    def test_kind_and_origin_shares_match_d12_and_d16(self) -> None:
        rng = random.Random(PLAN_SEED)
        plans = [draw_slot_plan(rng) for _ in range(DRAWS)]
        herrings = [p for p in plans if p.shape.blunder_position is None]
        own_blunders = [p for p in plans if p.shape.blunder_position and p.origin == "own"]
        foreign_blunders = [p for p in plans if p.shape.blunder_position and p.origin == "foreign"]
        assert len(herrings) / DRAWS == pytest.approx(HERRING_SHARE, abs=SHARE_TOLERANCE)
        assert len(own_blunders) / DRAWS == pytest.approx(OWN_BLUNDER_SHARE, abs=SHARE_TOLERANCE)
        assert len(foreign_blunders) / DRAWS == pytest.approx(
            FOREIGN_BLUNDER_SHARE, abs=SHARE_TOLERANCE
        )
        own_herrings = sum(1 for p in herrings if p.origin == "own")
        assert own_herrings / len(herrings) == pytest.approx(HERRING_OWN_SHARE, abs=SHARE_TOLERANCE)

    def test_length_is_uniform_for_both_kinds(self) -> None:
        rng = random.Random(PLAN_SEED)
        plans = [draw_slot_plan(rng) for _ in range(DRAWS)]
        for blunder in (False, True):
            kind = [p for p in plans if (p.shape.blunder_position is not None) == blunder]
            lengths = Counter(p.shape.length for p in kind)
            for length in WINDOW_LENGTHS:
                assert lengths[length] / len(kind) == pytest.approx(
                    1 / len(WINDOW_LENGTHS), abs=SHARE_TOLERANCE
                )

    def test_blunder_position_follows_the_conditional_hazard(self) -> None:
        rng = random.Random(PLAN_SEED)
        blunders = [
            p.shape
            for p in (draw_slot_plan(rng) for _ in range(DRAWS))
            if p.shape.blunder_position is not None
        ]
        for length in WINDOW_LENGTHS:
            of_length = [s for s in blunders if s.length == length]
            positions = Counter(s.blunder_position for s in of_length)
            for position, weight in blunder_position_weights(length).items():
                assert positions[position] / len(of_length) == pytest.approx(
                    weight, abs=SHARE_TOLERANCE
                )

    def test_slots_are_drawn_independently(self) -> None:
        rng = random.Random(SESSION_SEED)
        herring_counts = [
            sum(
                1
                for _ in range(SESSION_SLOTS)
                if draw_slot_plan(rng).shape.blunder_position is None
            )
            for _ in range(SESSIONS)
        ]
        assert min(herring_counts) == 0, "some sessions carry no herring at all"
        assert max(herring_counts) >= MANY_HERRINGS, "some sessions carry three or more"


class TestBlunderPositionWeights:
    def test_length_three_is_proportional_to_the_geometric_hazard(self) -> None:
        weights = blunder_position_weights(3)
        raw = (1.0, 1 - HAZARD, (1 - HAZARD) ** 2)
        total = sum(raw)
        assert sum(weights.values()) == pytest.approx(1.0)
        assert [weights[k] for k in (1, 2, 3)] == pytest.approx([r / total for r in raw])
