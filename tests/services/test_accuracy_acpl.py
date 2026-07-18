"""Unit tests for app.services.accuracy_acpl — lichess-compatible accuracy + ACPL.

Covers Phase 178 D-07..D-11 (SEED-110): the pure formula port of lichess's own
Win%/per-move-accuracy/windowed-game-accuracy/ACPL formulas.

The primary correctness proof is `test_acpl_fixture`: lichess game 296343's
real, dev-DB-verified `eval_cp` sequence (`[VERIFIED: dev DB game 296343]` —
NOT the RESEARCH.md/PLAN.md prose copy, which drops one of the five
consecutive zeros at ply 9-13; re-confirmed against `game_positions` directly)
reproduces lichess's own imported `white_acpl=18`/`black_acpl=61` exactly.
This single reproduction simultaneously validates sign convention + the
post-move-shift mapping + mover parity + the ACPL formula (RESEARCH §
"Worked example — game 296343").

DB-free: no session fixture, no `GamePosition` ORM rows — `Pos` below is a
lightweight stand-in matching `accuracy_acpl.PositionLike`'s duck-typed shape
(`ply`, `eval_cp`, `eval_mate`), so this file runs in a few seconds.
"""

from dataclasses import dataclass

import pytest

from app.services.accuracy_acpl import (
    AccuracyAcplResult,
    compute_game_accuracy_acpl,
    move_accuracy,
    win_pct,
)


@dataclass
class Pos:
    """Minimal PositionLike stand-in: only the three fields the compute module reads."""

    ply: int
    eval_cp: int | None = None
    eval_mate: int | None = None


# Game 296343 (lichess), White-POV post-move-shifted eval_cp by ply, 0..24.
# [VERIFIED: dev DB `SELECT ply, eval_cp FROM game_positions WHERE game_id = 296343
#  ORDER BY ply` — five consecutive zeros at plies 9-13, terminal ply 25 has NULL
#  eval_cp (irrelevant: it is never read, see accuracy_acpl.py module docstring).]
GAME_296343_EVAL_CP_SEQUENCE = [
    18, 25, 0, 11, -21, -25, -26, -28, -18, 0, 0, 0, 0, 0,
    -3, 209, 44, 63, 62, 58, 55, 88, 88, 519, 557,
]  # fmt: skip

# Lichess's own imported accuracy/ACPL for game 296343 (computed by lichess with
# the same formula this module ports) — the reconciliation targets.
GAME_296343_WHITE_ACPL = 18
GAME_296343_BLACK_ACPL = 61
GAME_296343_WHITE_ACCURACY = 84
GAME_296343_BLACK_ACCURACY = 61
ACCURACY_RECONCILIATION_TOLERANCE = 1.0


def _build_296343_positions() -> list[Pos]:
    """Build the 26-row (ply 0..25) position list for game 296343."""
    positions = [Pos(ply=p, eval_cp=cp) for p, cp in enumerate(GAME_296343_EVAL_CP_SEQUENCE)]
    positions.append(Pos(ply=25, eval_cp=None, eval_mate=None))  # terminal, legitimately NULL
    return positions


class TestAcplFixture:
    """The primary correctness proof: sign + shift + parity + ACPL, all at once."""

    def test_acpl_fixture(self) -> None:
        result = compute_game_accuracy_acpl(_build_296343_positions())
        assert result is not None
        assert result.white_acpl == GAME_296343_WHITE_ACPL
        assert result.black_acpl == GAME_296343_BLACK_ACPL


class TestWinPctAndMoveAccuracy:
    """D-08 (Win%) and D-09 (per-move accuracy) formula coverage."""

    def test_win_pct_zero_is_fifty(self) -> None:
        assert win_pct(0) == pytest.approx(50.0, abs=1e-9)

    def test_win_pct_preceiling_matches_beyond_ceiling(self) -> None:
        """win_pct(1000) == win_pct(5000): the ±1000 cap applies BEFORE the sigmoid."""
        assert win_pct(1000) == pytest.approx(win_pct(5000), abs=1e-9)

    def test_win_pct_symmetric(self) -> None:
        for cp in (-1500, -300, -1, 0, 1, 300, 1500):
            assert win_pct(cp) + win_pct(-cp) == pytest.approx(100.0, abs=1e-9)

    def test_move_accuracy_no_worsening_is_exactly_100(self) -> None:
        assert move_accuracy(60.0, 60.0) == 100.0
        assert move_accuracy(40.0, 90.0) == 100.0  # improved position

    def test_move_accuracy_large_drop_trends_toward_zero(self) -> None:
        assert move_accuracy(90.0, 5.0) < 20.0

    def test_move_accuracy_plus_one_bonus_present(self) -> None:
        """The trailing +1 uncertainty bonus (Pitfall 3) shifts the raw formula by exactly 1."""
        before, after = 70.0, 50.0
        with_bonus = move_accuracy(before, after)
        # Hand-computed via the exact D-09 constants, without the +1 term.
        import math

        from app.services.accuracy_acpl import MOVE_ACC_A, MOVE_ACC_B, MOVE_ACC_C

        without_bonus = MOVE_ACC_A * math.exp(MOVE_ACC_B * (before - after)) + MOVE_ACC_C
        assert with_bonus - without_bonus == pytest.approx(1.0, abs=1e-9)

    def test_move_accuracy_known_value_reproduces_lichess_fixture(self) -> None:
        """Regression pin on the exact D-09 formula (hand-computed reference value)."""
        assert move_accuracy(70.0, 50.0) == pytest.approx(41.016818741417126, abs=1e-9)


class TestGameAccuracyFixture:
    """D-10 windowed aggregation, reconciled against lichess's own published accuracy."""

    def test_game_accuracy_fixture(self) -> None:
        result = compute_game_accuracy_acpl(_build_296343_positions())
        assert result is not None
        assert result.white_accuracy is not None
        assert result.black_accuracy is not None
        assert result.white_accuracy == pytest.approx(
            GAME_296343_WHITE_ACCURACY, abs=ACCURACY_RECONCILIATION_TOLERANCE
        )
        assert result.black_accuracy == pytest.approx(
            GAME_296343_BLACK_ACCURACY, abs=ACCURACY_RECONCILIATION_TOLERANCE
        )


class TestIncompleteSequenceReturnsNone:
    """Complete-Sequence Gate (Pitfall 6): a stamp-complete game can still have holes."""

    def test_interior_hole_returns_none(self) -> None:
        # 4-move game; ply=1's row is an interior hole (both eval_cp/eval_mate NULL) —
        # it is simultaneously the "after" of move 1 and the "before" of move 2.
        positions = [
            Pos(ply=0, eval_cp=10),
            Pos(ply=1, eval_cp=None, eval_mate=None),
            Pos(ply=2, eval_cp=5),
            Pos(ply=3, eval_cp=-5),
            Pos(ply=4, eval_cp=None, eval_mate=None),  # terminal, not a hole
        ]
        assert compute_game_accuracy_acpl(positions) is None

    def test_terminal_null_alone_is_not_a_hole(self) -> None:
        """Only the terminal position is NULL (game 296343 shape) — must NOT return None."""
        result = compute_game_accuracy_acpl(_build_296343_positions())
        assert result is not None


class TestEdgeCases:
    """D-07 edge-case checklist: 0/1-move games, mid-game mate, checkmate, harmonic-zero."""

    def test_zero_move_game_returns_none(self) -> None:
        # Only the (unmovable) initial/terminal position exists — no move was played.
        positions = [Pos(ply=0, eval_cp=None, eval_mate=None)]
        assert compute_game_accuracy_acpl(positions) is None

    def test_one_move_game_white_computed_black_none(self) -> None:
        positions = [
            Pos(ply=0, eval_cp=20),
            Pos(ply=1, eval_cp=None, eval_mate=None),  # terminal
        ]
        result = compute_game_accuracy_acpl(positions)
        assert isinstance(result, AccuracyAcplResult)
        assert result.white_accuracy is not None
        assert result.white_acpl is not None
        assert result.black_accuracy is None
        assert result.black_acpl is None

    def test_mid_game_mate_eval_routes_through_ceiling(self) -> None:
        """A mid-game eval_mate (eval_cp NULL) must never route through the plain-cp path.

        White's move at ply 0 delivers a forced mate (eval_mate=+5, White winning):
        the resolved White-POV cp must be exactly +CP_CEILING (1000), so the loss
        for that move is 0 (delivering mate cannot be a "loss").
        """
        positions = [
            Pos(ply=0, eval_cp=None, eval_mate=5),  # White has forced mate after move 0
            Pos(ply=1, eval_cp=100),  # Black's reply, back to a plain cp eval
            Pos(ply=2, eval_cp=None, eval_mate=None),  # terminal
        ]
        result = compute_game_accuracy_acpl(positions)
        assert result is not None
        assert result.white_acpl == 0

    def test_checkmating_final_move_handled_without_error(self) -> None:
        """The last move's row has NULL eval (game-over) — must not raise, loss treated as 0."""
        positions = [
            Pos(ply=0, eval_cp=11),
            Pos(ply=1, eval_cp=-5),
            Pos(ply=2, eval_cp=None, eval_mate=None),  # last move's row: legitimately NULL
            Pos(ply=3, eval_cp=None, eval_mate=None),  # terminal
        ]
        result = compute_game_accuracy_acpl(positions)
        assert result is not None
        assert result.white_acpl == 2  # (4 + 0) / 2, mate-delivered move contributes 0 loss
        assert result.black_acpl == 0

    def test_literal_zero_accuracy_move_does_not_raise_in_harmonic_mean(self) -> None:
        """A full mate-to-mate reversal drives one move's accuracy to exactly 0.0.

        `compute_color_accuracy`'s harmonic-mean step must not raise ZeroDivisionError.
        """
        assert move_accuracy(win_pct(1000), win_pct(-1000)) == 0.0  # sanity: 0.0 is reachable

        positions = [
            Pos(ply=0, eval_cp=None, eval_mate=5),  # White mates after move 0 (+1000 cp)
            Pos(ply=1, eval_cp=None, eval_mate=-5),  # Black mates back after move 1 (-1000 cp)
            Pos(ply=2, eval_cp=50),
            Pos(ply=3, eval_cp=None, eval_mate=None),  # terminal
        ]
        result = compute_game_accuracy_acpl(positions)  # must not raise
        assert result is not None
        assert result.white_accuracy is not None
        assert result.black_accuracy is not None
