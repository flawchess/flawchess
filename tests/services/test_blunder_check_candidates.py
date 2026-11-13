"""Unit tests for app/services/blunder_check_candidates.py (SEED-261108-dk0, Phase 249).

No DB, no Maia. Games are built from transient GamePosition rows with chosen eval_cp lists
(row P's eval is the eval after the move played from P, white point of view), so the answer key
comes from the classifier's own _run_all_moves_pass, never from a re-derivation in the test.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import _SEVERITY_INT
from app.repositories.query_utils import mover_is_white_at_ply
from app.services.blunder_check_candidates import (
    BlunderCandidate,
    BlunderCase,
    GameCandidates,
    HerringRun,
    assign_windows,
    judge_game,
    judged_plies_for,
    lead_in_start,
    points_possible,
)
from app.services import blunder_check_rules
from app.services.blunder_check_rules import (
    BLUNDER_CHECK_SESSION_WINDOWS,
    BLUNDER_MAX_PRE_EVAL_CP,
    BLUNDER_MIN_OPENING_PLY,
    BLUNDER_MIN_PLY,
    FACEPALM_SCORE_MIN,
    MAX_BLUNDER_POSITION,
    WINDOW_LENGTHS,
    WindowShape,
    past_early_ply_floor,
)
from app.services.flaws_service import _run_all_moves_pass
from app.services.train_pool import HERRING_OPENING_PHASE

BLUNDER_SEVERITY = _SEVERITY_INT["blunder"]
MISTAKE_SEVERITY = _SEVERITY_INT["mistake"]
GAME_ID = 1
HOLD_CP = 100
# Miss fixtures start level so the opponent's gift (+300) is a blunder yet leaves the user's
# pre-blunder position inside the undecided band (+/- 300).
LEVEL_CP = 0
GIFT_CP = 300
FLAT_ROWS = 17
SCORE_EPSILON = 1e-6


@pytest.fixture(autouse=True)
def _no_early_ply_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """The short hand-built games below blunder at plies 4-8; the early-ply floor has its own
    tests (TestEarlyPlyFloor), which restore the real values."""
    monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", 0)
    monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_OPENING_PLY", 0)


@dataclass(frozen=True)
class _Flaw:
    """Satisfies FlawLike structurally."""

    ply: int
    severity: int = BLUNDER_SEVERITY
    is_miss: bool = False
    facepalm_score: float | None = 0.95


def _positions(evals: list[int]) -> list[GamePosition]:
    """Row 0 is the start position (no move); every later row carries the move played into it."""
    return [
        GamePosition(ply=i, eval_cp=cp, eval_mate=None, move_san=None if i == 0 else "x")
        for i, cp in enumerate(evals)
    ]


def _pure_miss_game() -> list[int]:
    """Level game, black blunders at ply 7 (to +300), white gives it all back at ply 8."""
    return [LEVEL_CP] * 7 + [GIFT_CP, LEVEL_CP]


def _mixed_game() -> list[int]:
    """Like the pure-miss game, but white returns more than the gift (eval -150 at ply 8)."""
    return [LEVEL_CP] * 7 + [GIFT_CP, -150]


def _allowed_game() -> list[int]:
    """White user blunders at ply 6 (+100 to -300) with no gift before it."""
    return [HOLD_CP] * 6 + [-300, -300, -300]


def _judge(
    evals: list[int],
    flaws: list[_Flaw],
    *,
    user_is_white: bool = True,
    key_plies: set[int] | None = None,
    served_plies: set[int] | None = None,
    served: list[tuple[int, int]] | None = None,
    positions: list[GamePosition] | None = None,
) -> GameCandidates | None:
    return judge_game(
        game_id=GAME_ID,
        user_is_white=user_is_white,
        positions=positions if positions is not None else _positions(evals),
        flaws=flaws,
        key_plies=key_plies if key_plies is not None else {f.ply for f in flaws},
        served_blunder_plies=served_plies or set(),
        served_ply_ranges=served or [],
    )


def _blunders(result: GameCandidates | None) -> tuple[BlunderCandidate, ...]:
    assert result is not None
    return result.blunders


def _candidate(
    game_id: int, ply: int = 8, max_position: int = 3, case: BlunderCase = "allowed"
) -> BlunderCandidate:
    preceding = tuple(range(ply - 2 * (MAX_BLUNDER_POSITION - 1), ply, 2))
    return BlunderCandidate(
        game_id=game_id,
        ply=ply,
        case=case,
        max_position=max_position,
        preceding_plies=preceding,
    )


def _game(
    game_id: int,
    blunders: tuple[BlunderCandidate, ...] = (),
    herrings: dict[int, tuple[HerringRun, ...]] | None = None,
) -> GameCandidates:
    return GameCandidates(
        game_id=game_id,
        blunders=blunders,
        herrings=herrings or {length: () for length in WINDOW_LENGTHS},
    )


class TestJudgeGameGoodBar:
    def test_good_bar_pure_miss_game_reaches_position_four(self) -> None:
        result = _judge(_pure_miss_game(), [_Flaw(ply=8, is_miss=True)])
        (candidate,) = _blunders(result)
        assert (candidate.case, candidate.max_position) == ("pure_miss", 4)
        assert candidate.preceding_plies == (2, 4, 6)

    def test_good_bar_inaccuracy_two_user_moves_back_caps_position_at_two(self) -> None:
        # White inaccuracy at ply 4, clean ply 6, blunder at ply 8 (probed: es 0.43 -> 0.19).
        evals = [0, 0, 0, 0, -80, -80, -80, -80, -400]
        all_moves = _run_all_moves_pass(_positions(evals))
        assert all_moves[4][1] == "inaccuracy"
        (candidate,) = _blunders(_judge(evals, [_Flaw(ply=8)]))
        assert candidate.max_position == 2

    def test_good_bar_inaccuracy_never_appears_in_a_herring_run(self) -> None:
        evals = [0, 0, 0, 0, -80] + [-80] * (FLAT_ROWS - 5)
        result = _judge(evals, [])
        assert result is not None
        runs = [run for runs in result.herrings.values() for run in runs]
        assert runs
        assert all(4 not in run.plies for run in runs)


class TestJudgeGameBand:
    def test_band_blunder_with_out_of_band_pre_move_es_is_not_a_candidate(self) -> None:
        # Black gifts +1000, white's pre-move ES is 0.975 > 0.90.
        evals = [HOLD_CP] * 7 + [1000, 0]
        assert _blunders(_judge(evals, [_Flaw(ply=8)])) == ()

    def test_band_herring_runs_skip_out_of_band_moves(self) -> None:
        # +1000 everywhere: every user move starts out of band, so no herring run exists.
        result = _judge([1000] * FLAT_ROWS, [])
        assert result is not None
        assert all(runs == () for runs in result.herrings.values())

    def test_band_flat_game_has_sliding_herring_runs_of_every_length(self) -> None:
        result = _judge([HOLD_CP] * FLAT_ROWS, [])
        assert result is not None
        user_moves = list(range(2, FLAT_ROWS, 2))
        for length in WINDOW_LENGTHS:
            runs = result.herrings[length]
            assert len(runs) == len(user_moves) - length + 1
            assert all(len(run.plies) == length for run in runs)
            assert all(run.game_id == GAME_ID for run in runs)


class TestFacepalmPredicate:
    """250 D-01 / D-09: one score gate, the same for every blunder case."""

    def test_passes_at_exactly_the_threshold(self) -> None:
        flaw = _Flaw(ply=6, facepalm_score=FACEPALM_SCORE_MIN)
        assert len(_blunders(_judge(_allowed_game(), [flaw]))) == 1

    def test_fails_just_under_the_threshold(self) -> None:
        flaw = _Flaw(ply=6, facepalm_score=FACEPALM_SCORE_MIN - SCORE_EPSILON)
        assert _blunders(_judge(_allowed_game(), [flaw])) == ()

    def test_null_score_is_excluded(self) -> None:
        assert _blunders(_judge(_allowed_game(), [_Flaw(ply=6, facepalm_score=None)])) == ()

    @pytest.mark.parametrize(
        ("evals_name", "ply", "is_miss", "case"),
        [
            ("allowed", 6, False, "allowed"),
            ("pure_miss", 8, True, "pure_miss"),
            ("mixed", 8, True, "mixed"),
        ],
    )
    def test_same_outcome_for_every_case(
        self, evals_name: str, ply: int, is_miss: bool, case: str
    ) -> None:
        # D-01: no special case for missed punishments; the score alone decides.
        games = {
            "allowed": _allowed_game(),
            "pure_miss": _pure_miss_game(),
            "mixed": _mixed_game(),
        }
        evals = games[evals_name]
        passing = _Flaw(ply=ply, is_miss=is_miss, facepalm_score=FACEPALM_SCORE_MIN)
        failing = _Flaw(ply=ply, is_miss=is_miss, facepalm_score=FACEPALM_SCORE_MIN - SCORE_EPSILON)
        (candidate,) = _blunders(_judge(evals, [passing]))
        assert candidate.case == case
        assert _blunders(_judge(evals, [failing])) == ()

    def test_unclassified_miss_is_excluded(self) -> None:
        # Black user blunders at ply 1, flagged a miss, but ply 0 has no entry so es_ref is unknown.
        flaw = _Flaw(ply=1, is_miss=True)
        assert _blunders(_judge([0, 500], [flaw], user_is_white=False)) == ()


class TestUndecidedPosition:
    """Phase 249 UAT: only blunders from an undecided game (+/- 300, no mate); a miss is judged
    on the position before the opponent's gift."""

    @staticmethod
    def _allowed_from(pre_cp: int) -> list[int]:
        # White blunders at ply 6 from pre_cp to 600 below it.
        return [pre_cp] * 6 + [pre_cp - 600] * 3

    def test_blunder_at_the_band_edge_is_a_candidate(self) -> None:
        for pre_cp in (BLUNDER_MAX_PRE_EVAL_CP, -BLUNDER_MAX_PRE_EVAL_CP):
            assert len(_blunders(_judge(self._allowed_from(pre_cp), [_Flaw(ply=6)]))) == 1

    def test_blunder_just_outside_the_band_is_excluded(self) -> None:
        for pre_cp in (BLUNDER_MAX_PRE_EVAL_CP + 1, -BLUNDER_MAX_PRE_EVAL_CP - 1):
            assert _blunders(_judge(self._allowed_from(pre_cp), [_Flaw(ply=6)])) == ()

    def test_blunder_inside_the_wider_es_band_but_outside_plus_three_is_excluded(self) -> None:
        # +500 is inside the D-05 ES band (0.86 < 0.90) but the game is already decided.
        assert _blunders(_judge(self._allowed_from(500), [_Flaw(ply=6)])) == ()

    def test_blunder_from_a_mate_score_is_excluded(self) -> None:
        positions = _positions(self._allowed_from(LEVEL_CP))
        positions[5] = GamePosition(ply=5, eval_cp=None, eval_mate=3, move_san="x")
        assert _blunders(_judge([], [_Flaw(ply=6)], positions=positions)) == ()

    def test_miss_of_a_large_gift_from_an_undecided_game_is_kept(self) -> None:
        # Black gifts +500 (outside +/- 300), but the game was level before the gift.
        evals = [LEVEL_CP] * 7 + [500, LEVEL_CP]
        assert len(_blunders(_judge(evals, [_Flaw(ply=8, is_miss=True)]))) == 1

    def test_miss_in_a_game_decided_before_the_gift_is_excluded(self) -> None:
        # White already +400 before black's gift to +900; white gives it back to +400.
        evals = [400] * 7 + [900, 400]
        assert _blunders(_judge(evals, [_Flaw(ply=8, is_miss=True)])) == ()


class TestEarlyPlyFloor:
    def test_floor_matches_personalized_puzzles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", BLUNDER_MIN_PLY)
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_OPENING_PLY", BLUNDER_MIN_OPENING_PLY)
        assert past_early_ply_floor(BLUNDER_MIN_PLY, None)
        assert not past_early_ply_floor(BLUNDER_MIN_PLY - 1, None)
        assert not past_early_ply_floor(BLUNDER_MIN_OPENING_PLY - 1, HERRING_OPENING_PHASE)
        assert past_early_ply_floor(BLUNDER_MIN_OPENING_PLY, HERRING_OPENING_PHASE)

    def test_blunder_before_the_floor_is_not_a_candidate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flaw = _Flaw(ply=6)
        assert len(_blunders(_judge(_allowed_game(), [flaw]))) == 1
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", flaw.ply + 1)
        assert _blunders(_judge(_allowed_game(), [flaw])) == ()

    def test_judged_moves_before_the_blunder_clear_the_floor_too(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Without a floor the blunder at ply 6 fits later positions (judging plies 4, 2, ...).
        flaw = _Flaw(ply=6)
        [unfloored] = _blunders(_judge(_allowed_game(), [flaw]))
        assert unfloored.max_position > 2
        # Floor at ply 4: only the user's move at ply 4 may be judged before the blunder.
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", 4)
        [capped] = _blunders(_judge(_allowed_game(), [flaw]))
        assert capped.max_position == 2
        # Floor at the blunder ply itself: it can only be the first judged move.
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", flaw.ply)
        [first_only] = _blunders(_judge(_allowed_game(), [flaw]))
        assert first_only.max_position == 1

    def test_all_safe_runs_never_include_a_ply_before_the_floor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        floor = 8
        monkeypatch.setattr(blunder_check_rules, "BLUNDER_MIN_PLY", floor)
        result = _judge([HOLD_CP] * FLAT_ROWS, [])
        assert result is not None
        runs = [run for runs in result.herrings.values() for run in runs]
        assert runs
        assert all(ply >= floor for run in runs for ply in run.plies)


class TestJudgeGameGuards:
    def test_stored_blunder_not_recomputed_as_blunder_is_excluded(self) -> None:
        assert _blunders(_judge([HOLD_CP] * FLAT_ROWS, [_Flaw(ply=4)])) == ()

    def test_stored_mistake_is_not_a_blunder_candidate(self) -> None:
        flaw = _Flaw(ply=6, severity=MISTAKE_SEVERITY)
        assert _blunders(_judge(_allowed_game(), [flaw])) == ()

    def test_opponent_parity_flaw_is_excluded(self) -> None:
        # Ply 7 is black's blunder; the user is white.
        flaw = _Flaw(ply=7)
        assert not mover_is_white_at_ply(7)
        assert _blunders(_judge(_pure_miss_game(), [flaw])) == ()

    def test_ply_outside_key_plies_is_excluded(self) -> None:
        flaw = _Flaw(ply=6)
        assert _blunders(_judge(_allowed_game(), [flaw], key_plies=set())) == ()

    def test_served_blunder_ply_is_excluded(self) -> None:
        flaw = _Flaw(ply=6)
        assert _blunders(_judge(_allowed_game(), [flaw], served_plies={6})) == ()

    def test_herring_run_touching_a_served_range_is_excluded(self) -> None:
        result = _judge([HOLD_CP] * FLAT_ROWS, [], served=[(2, 6)])
        assert result is not None
        for runs in result.herrings.values():
            for run in runs:
                assert not any(2 <= ply <= 6 for ply in run.plies)
        assert result.herrings[3]  # later runs survive

    def test_non_contiguous_positions_return_none(self) -> None:
        positions = _positions([HOLD_CP] * 6)
        positions[3] = GamePosition(ply=4, eval_cp=HOLD_CP, eval_mate=None, move_san="x")
        assert _judge([], [], positions=positions) is None
        assert _judge([HOLD_CP] * 6, []) is not None


class TestAssignWindows:
    def test_assign_blunder_slot_only_takes_candidates_that_reach_the_drawn_position(self) -> None:
        low = _game(1, (_candidate(1, max_position=2),))
        high = _game(2, (_candidate(2, max_position=4),))
        picks = assign_windows(
            {0: WindowShape(5, 3)}, [low, high], rng=random.Random(1), used_game_ids=set()
        )
        assert [p.game_id for p in picks] == [2]
        assert picks[0].shape == WindowShape(5, 3)

    def test_assign_fills_the_rarest_slot_first(self) -> None:
        # The only candidate reaching position 3 must not be consumed by the position-1 slot.
        deep = _game(1, (_candidate(1, max_position=3),))
        shallow = _game(2, (_candidate(2, max_position=1),))
        slots = {0: WindowShape(3, 1), 1: WindowShape(5, 3)}
        picks = assign_windows(slots, [deep, shallow], rng=random.Random(1), used_game_ids=set())
        by_slot = {p.slot: p.game_id for p in picks}
        assert by_slot == {0: 2, 1: 1}

    def test_assign_uses_at_most_one_window_per_game(self) -> None:
        only = _game(1, (_candidate(1, max_position=3),))
        slots = {0: WindowShape(4, 2), 1: WindowShape(4, 2)}
        picks = assign_windows(slots, [only], rng=random.Random(1), used_game_ids=set())
        assert len(picks) == 1

    def test_assign_skips_games_already_used(self) -> None:
        only = _game(1, (_candidate(1, max_position=3),))
        picks = assign_windows(
            {0: WindowShape(4, 2)}, [only], rng=random.Random(1), used_game_ids={1}
        )
        assert picks == []

    def test_assign_leaves_an_unfillable_slot_absent(self) -> None:
        only = _game(1, (_candidate(1, max_position=1),))
        slots = {0: WindowShape(4, 1), 1: WindowShape(5, 5)}
        picks = assign_windows(slots, [only], rng=random.Random(1), used_game_ids=set())
        assert [p.slot for p in picks] == [0]

    def test_assign_herring_slot_draws_from_its_own_length(self) -> None:
        run3 = HerringRun(1, (2, 4, 6))
        run4 = HerringRun(1, (2, 4, 6, 8))
        game = _game(1, herrings={3: (run3,), 4: (run4,), 5: ()})
        picks = assign_windows(
            {0: WindowShape(4, None)}, [game], rng=random.Random(1), used_game_ids=set()
        )
        (pick,) = picks
        assert (pick.case, pick.blunder_ply, pick.judged_plies) == ("herring", None, run4.plies)
        assert pick.first_ply == 2

    def test_assign_same_seed_gives_the_same_picks(self) -> None:
        games = [_game(i, (_candidate(i, max_position=5),)) for i in range(1, 30)]
        slots = {i: WindowShape(5, 2) for i in range(BLUNDER_CHECK_SESSION_WINDOWS)}
        first = assign_windows(slots, games, rng=random.Random(5), used_game_ids=set())
        second = assign_windows(slots, games, rng=random.Random(5), used_game_ids=set())
        assert first == second
        assert len({p.game_id for p in first}) == BLUNDER_CHECK_SESSION_WINDOWS

    def test_assign_blunder_window_judges_the_preceding_moves_then_the_blunder(self) -> None:
        game = _game(1, (_candidate(1, ply=12, max_position=5),))
        (pick,) = assign_windows(
            {0: WindowShape(5, 3)}, [game], rng=random.Random(1), used_game_ids=set()
        )
        assert pick.judged_plies == (8, 10, 12)
        assert pick.blunder_ply == 12
        assert pick.first_ply == 8

    def test_assign_composition_is_whatever_the_draw_produces(self) -> None:
        # A blunder slot with only herring supply stays empty; no blunder is forced in (D-11).
        herring_only = _game(1, herrings={3: (), 4: (HerringRun(1, (2, 4, 6, 8)),), 5: ()})
        slots = {0: WindowShape(5, 2), 1: WindowShape(4, None)}
        picks = assign_windows(slots, [herring_only], rng=random.Random(1), used_game_ids=set())
        assert [(p.slot, p.case) for p in picks] == [(1, "herring")]


class TestNoMissCap:
    def test_miss_pool_of_only_pure_misses_fills_every_blunder_slot(self) -> None:
        games = [_game(i, (_candidate(i, max_position=5, case="pure_miss"),)) for i in range(1, 20)]
        slots = {i: WindowShape(5, 1 + i % 3) for i in range(BLUNDER_CHECK_SESSION_WINDOWS)}
        picks = assign_windows(slots, games, rng=random.Random(3), used_game_ids=set())
        assert len(picks) == BLUNDER_CHECK_SESSION_WINDOWS
        assert {p.case for p in picks} == {"pure_miss"}

    def test_miss_at_position_one_has_the_opponents_blunder_as_last_lead_in_ply(self) -> None:
        evals = _pure_miss_game()
        all_moves = _run_all_moves_pass(_positions(evals))
        flaw = _Flaw(ply=8, is_miss=True)
        (candidate,) = _blunders(_judge(evals, [flaw]))
        game = _game(GAME_ID, (candidate,))
        (pick,) = assign_windows(
            {0: WindowShape(3, 1)}, [game], rng=random.Random(1), used_game_ids=set()
        )
        assert pick.first_ply == 8
        lead_in_last = pick.first_ply - 1
        assert not mover_is_white_at_ply(lead_in_last)
        assert all_moves[lead_in_last][1] == "blunder"


class TestPointsAndLeadIn:
    def test_points_possible_herring_is_one_per_move(self) -> None:
        assert points_possible(WindowShape(4, None)) == 4

    def test_points_possible_blunder_at_three_is_seven(self) -> None:
        assert points_possible(WindowShape(5, 3)) == 2 + 3 + 2

    def test_points_possible_blunder_at_position_one_has_no_safe_moves(self) -> None:
        assert points_possible(WindowShape(3, 1)) == 3 + 2

    def test_judged_plies_for_takes_the_last_preceding_plies(self) -> None:
        candidate = _candidate(1, ply=14, max_position=5)
        assert judged_plies_for(candidate, 1) == (14,)
        assert judged_plies_for(candidate, 3) == (10, 12, 14)

    def test_lead_in_start_is_clamped_at_the_game_start(self) -> None:
        assert lead_in_start(8) == 7
        assert lead_in_start(1) == 0
        assert lead_in_start(0) == 0


@pytest.mark.parametrize("length", WINDOW_LENGTHS)
def test_points_possible_herring_scales_with_window_length(length: int) -> None:
    assert points_possible(WindowShape(length, None)) == length
