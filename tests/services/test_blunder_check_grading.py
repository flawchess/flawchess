"""Unit tests for the pure blunder-check grading module (Phase 249-04).

Coverage:
- test_grade_*            : the D-12/D-13 answer table (all six results)
- test_effective_*        : answers past the ceiling become timeouts (D-18)
- test_timer_*            : remaining time never includes the animation allowance (D-18)
- test_score_pct_*        : D-14 floor percentage
- test_window_*           : snapshot move math helpers
- test_graded_moves_*     : the better-move set is one derivation for every case (D-17)
- test_precedence_*       : better-move tier precedence (D-17)
"""

from __future__ import annotations

import datetime
import inspect
from typing import Any

import pytest

from app.services.blunder_check_grading import (
    ANSWER_CEILING_S,
    MOVE_TIMER_SECONDS,
    MS_PER_SECOND,
    NETWORK_GRACE_S,
    PROMPT_ANIMATION_ALLOWANCE_S,
    AnswerGrade,
    AnswerKindName,
    MoveTierName,
    better_move_graded_moves,
    effective_answer,
    fen_before_ply,
    grade_answer,
    is_legal_uci,
    judged_ply,
    resolve_better_move_tier,
    score_pct,
    timer_remaining_ms,
    uci_at,
    window_ucis,
)
from app.services.blunder_check_rules import BLUNDER_POINTS, SAFE_POINTS
from app.services.train_pool import ServerGradedMove

_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_T0 = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_WINDOW_POINTS = 2


def _grade(
    answer: AnswerKindName, *, blunder: bool, last: bool = False, points: int = _WINDOW_POINTS
) -> AnswerGrade:
    return grade_answer(
        is_blunder_move=blunder, is_last_judged_move=last, answer=answer, window_points=points
    )


def test_ceiling_is_the_sum_of_the_three_named_parts() -> None:
    assert ANSWER_CEILING_S == MOVE_TIMER_SECONDS + PROMPT_ANIMATION_ALLOWANCE_S + NETWORK_GRACE_S


def test_grade_caught_awards_blunder_points_and_ends() -> None:
    grade = _grade("blunder", blunder=True)
    assert grade == AnswerGrade("caught", BLUNDER_POINTS, 0, True, "caught", True)


def test_grade_missed_forfeits_window_points() -> None:
    grade = _grade("safe", blunder=True)
    assert grade == AnswerGrade("missed", 0, _WINDOW_POINTS, True, "missed", False)


def test_grade_timeout_on_blunder_counts_as_missed() -> None:
    grade = _grade("timeout", blunder=True)
    assert grade == AnswerGrade("timeout_blunder", 0, _WINDOW_POINTS, True, "missed", False)


def test_grade_false_alarm_keeps_safe_points_and_ends() -> None:
    grade = _grade("blunder", blunder=False)
    assert grade == AnswerGrade("false_alarm", 0, 0, True, "false_alarm", False)


def test_grade_correct_safe_continues() -> None:
    grade = _grade("safe", blunder=False)
    assert grade == AnswerGrade("correct_safe", SAFE_POINTS, 0, False, None, False)


def test_grade_correct_safe_on_last_judged_move_clears() -> None:
    grade = _grade("safe", blunder=False, last=True)
    assert grade == AnswerGrade("correct_safe", SAFE_POINTS, 0, True, "cleared", False)


def test_grade_timeout_on_safe_forfeits_and_continues() -> None:
    grade = _grade("timeout", blunder=False)
    assert grade == AnswerGrade("timeout_safe", 0, _WINDOW_POINTS, False, None, False)


def test_grade_timeout_on_last_safe_move_forfeits_and_clears() -> None:
    grade = _grade("timeout", blunder=False, last=True)
    assert grade == AnswerGrade("timeout_safe", 0, _WINDOW_POINTS, True, "cleared", False)


def test_grade_forfeit_equals_the_points_passed_in() -> None:
    assert _grade("safe", blunder=True, points=5).points_forfeited == 5
    assert _grade("timeout", blunder=False, points=0).points_forfeited == 0


def test_effective_answer_at_the_ceiling_stays_and_one_ms_later_times_out() -> None:
    ceiling_ms = ANSWER_CEILING_S * MS_PER_SECOND
    assert effective_answer("safe", ceiling_ms) == "safe"
    assert effective_answer("safe", ceiling_ms + 1) == "timeout"
    assert effective_answer("blunder", ceiling_ms + 1) == "timeout"


def test_effective_answer_timeout_stays_timeout() -> None:
    assert effective_answer("timeout", 0) == "timeout"
    assert effective_answer("timeout", ANSWER_CEILING_S * MS_PER_SECOND * 2) == "timeout"


@pytest.mark.parametrize(
    ("elapsed_s", "expected_ms"),
    [(0, 10000), (2, 8000), (5, 5000), (10, 0), (20, 0)],
)
def test_timer_remaining_has_no_animation_allowance(elapsed_s: int, expected_ms: int) -> None:
    now = _T0 + datetime.timedelta(seconds=elapsed_s)
    assert timer_remaining_ms(_T0, now) == expected_ms


def test_timer_remaining_clamps_a_future_stamp_to_the_full_timer() -> None:
    assert timer_remaining_ms(_T0 + datetime.timedelta(seconds=5), _T0) == 10000


@pytest.mark.parametrize(
    ("points", "possible", "expected"),
    [(4, 10, 40), (1, 3, 33), (0, 5, 0), (5, 5, 100), (3, 0, 0)],
)
def test_score_pct_floors(points: int, possible: int, expected: int) -> None:
    assert score_pct(points, possible) == expected


def test_window_helpers_follow_the_snapshot_math() -> None:
    ucis = window_ucis("e2e4 e7e5 g1f3 b8c6")
    assert ucis == ["e2e4", "e7e5", "g1f3", "b8c6"]
    assert judged_ply(10, 1) == 10
    assert judged_ply(10, 3) == 14
    assert uci_at(ucis, 8, 8) == "e2e4"
    assert uci_at(ucis, 8, 11) == "b8c6"
    assert uci_at(ucis, 8, 12) is None
    assert uci_at(ucis, 8, 7) is None


def test_window_fen_before_ply_replays_the_snapshot() -> None:
    ucis = ["e2e4", "e7e5"]
    assert fen_before_ply(_START_FEN, ucis, 0, 0) == _START_FEN
    after_one = fen_before_ply(_START_FEN, ucis, 0, 1)
    assert after_one.startswith("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b")


_SOFT_BLOB: list[Any] = [{"b": 50, "bm": None, "s": 40, "sm": None, "su": "e2e4"}]


def test_graded_moves_soft_blob_gives_key_and_runner_up() -> None:
    moves = better_move_graded_moves(
        blunder_ply=0, key_uci="d2d4", missed_pv_lines=_SOFT_BLOB, fen=_START_FEN
    )
    assert [(m.uci, m.tier) for m in moves] == [("d2d4", "good"), ("e2e4", "good")]


def test_graded_moves_is_independent_of_the_window_case() -> None:
    """The helper takes no case argument: the same inputs always give the same set (D-17)."""
    first = better_move_graded_moves(
        blunder_ply=0, key_uci="d2d4", missed_pv_lines=_SOFT_BLOB, fen=_START_FEN
    )
    second = better_move_graded_moves(
        blunder_ply=0, key_uci="d2d4", missed_pv_lines=_SOFT_BLOB, fen=_START_FEN
    )
    assert first == second


def test_graded_moves_none_blob_is_empty() -> None:
    assert (
        better_move_graded_moves(
            blunder_ply=0, key_uci="d2d4", missed_pv_lines=None, fen=_START_FEN
        )
        == ()
    )


_KEY = "d2d4"
_BLUNDER = "e2e4"
_GRADED = (
    ServerGradedMove(uci="c2c4", tier="inaccuracy", es_before=0.6, es_after=0.55),
    ServerGradedMove(uci="g1f3", tier="good", es_before=0.6, es_after=0.59),
)
_UNGRADED = "b1c3"


def _tier(
    played: str, client: MoveTierName, graded: tuple[ServerGradedMove, ...] = _GRADED
) -> MoveTierName:
    return resolve_better_move_tier(
        played_uci=played,
        key_uci=_KEY,
        blunder_uci=_BLUNDER,
        graded_moves=graded,
        client_tier=client,
    )


def test_precedence_key_is_good_even_when_the_client_says_wrong() -> None:
    assert _tier(_KEY, "wrong") == "good"


def test_precedence_own_blunder_is_wrong_even_when_the_client_says_good() -> None:
    assert _tier(_BLUNDER, "good") == "wrong"


def test_precedence_own_blunder_beats_a_graded_entry_for_the_same_move() -> None:
    graded = (ServerGradedMove(uci=_BLUNDER, tier="good", es_before=0.6, es_after=0.6),)
    assert _tier(_BLUNDER, "good", graded) == "wrong"


@pytest.mark.parametrize(
    ("played", "expected"), [("c2c4", "inaccuracy"), ("g1f3", "good")], ids=["inacc", "good"]
)
def test_precedence_server_graded_entry_overrides_the_client(played: str, expected: str) -> None:
    assert _tier(played, "wrong") == expected
    assert _tier(played, "good") == expected


@pytest.mark.parametrize("client", ["good", "inaccuracy", "wrong"])
def test_precedence_off_key_ungraded_move_takes_the_client_tier(client: MoveTierName) -> None:
    assert _tier(_UNGRADED, client) == client
    assert _tier("c2c4", client, ()) == client


def test_precedence_first_graded_match_wins() -> None:
    graded = (
        ServerGradedMove(uci="c2c4", tier="inaccuracy", es_before=0.6, es_after=0.55),
        ServerGradedMove(uci="c2c4", tier="good", es_before=0.6, es_after=0.6),
    )
    assert _tier("c2c4", "wrong", graded) == "inaccuracy"


def test_precedence_has_no_window_case_input() -> None:
    # D-17: allowed / pure-miss / mixed windows resolve identically, so there is no case input.
    params = inspect.signature(resolve_better_move_tier).parameters
    assert not {"window_case", "case"} & set(params)


def test_is_legal_uci_accepts_legal_and_rejects_the_rest() -> None:
    assert is_legal_uci(_START_FEN, "e2e4")
    assert not is_legal_uci(_START_FEN, "e2e5")
    assert not is_legal_uci(_START_FEN, "a1a1")
    assert not is_legal_uci(_START_FEN, "zzzz")


def test_graded_moves_drops_an_illegal_entry() -> None:
    blob: list[Any] = [{"b": 50, "bm": None, "s": 40, "sm": None, "su": "e2e5"}]
    moves = better_move_graded_moves(
        blunder_ply=0, key_uci="d2d4", missed_pv_lines=blob, fen=_START_FEN
    )
    assert [m.uci for m in moves] == ["d2d4"]
