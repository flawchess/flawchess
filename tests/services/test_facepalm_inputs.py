"""Tests for the stored material inputs (Phase 259 D-02 to D-04, D-13)."""

from __future__ import annotations

import chess
import pytest

from app.services.blunder_check_rules import FACEPALM_MISSED_MATE, MATE_LOSS
from app.services.facepalm_inputs import facepalm_material_inputs
from app.services.line_material import (
    LINE_LOSS_DEPTHS,
    quiet_best_line_facts,
    quiet_line_facts,
)
from tests.services.line_material_fixtures import D13_FIXTURE


def _d13_board() -> chess.Board:
    return chess.Board(D13_FIXTURE.pre_fen)


def test_d13_missed_gain_is_zero_under_the_quiet_rule() -> None:
    board = _d13_board()
    inputs = facepalm_material_inputs(
        board, D13_FIXTURE.played_uci, D13_FIXTURE.refutation_line, D13_FIXTURE.best_line
    )
    assert inputs.loss == pytest.approx(D13_FIXTURE.expected_loss)
    assert inputs.missed == 0.0

    played = quiet_line_facts(board, D13_FIXTURE.played_uci, D13_FIXTURE.refutation_line)
    best = quiet_best_line_facts(board, D13_FIXTURE.best_line)
    assert tuple(played.loss_at(d) for d in LINE_LOSS_DEPTHS) == (
        D13_FIXTURE.expected_quiet_played_loss
    )
    assert tuple(best.material_at(d) for d in LINE_LOSS_DEPTHS) == (
        D13_FIXTURE.expected_quiet_best_material
    )
    assert board.fen() == D13_FIXTURE.pre_fen  # never mutated


def _board_after(moves: str) -> chess.Board:
    board = chess.Board()
    for uci in moves.split():
        board.push_uci(uci)
    return board


def test_mating_best_move_with_one_token_line() -> None:
    """Pitfall 2: a best move that mates settles every depth, so missed is the mate value."""
    # Black to move after f3 e5 g4 and plays a6 instead of Qh4#; the stored best line is just Qh4.
    board = _board_after("f2f3 e7e5 g2g4")
    refutation = "a2a3 b7b6 b2b3 c7c6 c2c3 d7d6"
    assert quiet_best_line_facts(board, "d8h4").opponent_mate_ply == 0
    inputs = facepalm_material_inputs(board, "a7a6", refutation, "d8h4")
    assert inputs.loss == 0.0
    assert inputs.missed == float(FACEPALM_MISSED_MATE)


def test_blunderer_mated_within_line_depth_gives_mate_loss() -> None:
    # Fool's mate: g4 allows Qh4# at ply 1.
    board = _board_after("f2f3 e7e5")
    inputs = facepalm_material_inputs(board, "g2g4", "d8h4", "g1f3")
    assert inputs.loss == float(MATE_LOSS)


def test_null_pair_when_line_too_short() -> None:
    """256 D-03: an unsettled depth 3 leaves the row unscored, loss AND missed None."""
    board = _board_after("e2e4 e7e5")
    inputs = facepalm_material_inputs(board, "g1f3", "b8c6 f1c4", "d2d4 e5d4 d1d4")
    assert inputs.loss is None
    assert inputs.missed is None


@pytest.mark.parametrize(
    "best_pv", [None, "", "a1a8", "zz99"], ids=["none", "empty", "illegal", "bad"]
)
def test_unknown_best_line_gives_missed_zero(best_pv: str | None) -> None:
    """254 D-18: a known loss with an unknown best line contributes no missed gain."""
    board = _board_after("e2e4 e7e5")
    inputs = facepalm_material_inputs(board, "g1f3", "b8c6 f1c4 g8f6 e1g1", best_pv)
    assert inputs.loss == 0.0
    assert inputs.missed == 0.0


# Phase 262 D-01/D-02: a promotion is material, the caps stay where they were.
_PROMOTION_FEN = "6k1/8/8/8/8/8/2p5/1R4K1 w - - 0 1"


def test_opponent_queen_promotion_next_move_stores_the_cap() -> None:
    """262 D-01/D-02: the opponent queens on the next move, so every depth reads 8 and the stored
    loss is clipped to LOSS_CAP (5.0); before D-01 the promotion was invisible and loss was 0.0."""
    board = chess.Board(_PROMOTION_FEN)
    line = "c2c1q g1h2 g8f7 b3b7 f7e6 b7b6 e6d5 b6b5 d5c4 b5b8"
    played = quiet_line_facts(board, "b1b3", line)
    assert tuple(played.loss_at(d) for d in LINE_LOSS_DEPTHS) == (8, 8, 8, 8, 8)

    inputs = facepalm_material_inputs(board, "b1b3", line, None)
    assert inputs.loss == 5.0
    assert inputs.missed == 0.0
    assert board.fen() == _PROMOTION_FEN  # never mutated


@pytest.mark.parametrize(
    ("fen", "line", "expected_loss"),
    [
        # The opponent queens at ply 5 and the queen stays: depths 0, 0, 8, 8, 8 clip to 0, 0, 5, 5, 5.
        (
            _PROMOTION_FEN,
            "g8f7 h1g2 f7e6 b1b3 c2c1q b3b8 e6d5 b8b5 d5c4 b5b8",
            1.1290322580645162,
        ),
        # The queen is taken at once: the net is the lost pawn, floored at 0 (the CONTEXT 0.23
        # example is wrong under D-01, the per-depth values are 0, 0, -1, -1, -1).
        (_PROMOTION_FEN, "g8f7 h1g2 f7e6 b1a1 c2c1q a1c1 e6d5 c1c8 d5d4 c8c1", 0.0),
        # A line that is only the promotion is a settled loss now (net -1), no longer None.
        (_PROMOTION_FEN, "c2c1q", 0.0),
        # D-03: the freshly promoted piece is taken on its promotion square, the loss is 1 at every depth.
        (
            "1r4k1/P7/8/8/8/8/8/6K1 w - - 0 1",
            "g8f7 a7a8q b8a8 h1g1 f7e6 g1f2 e6d5 f2e3 d5c4 e3d2",
            1.0,
        ),
    ],
    ids=["queen_stays", "queen_taken_at_once", "promotion_only_line", "d03_promoted_piece_taken"],
)
def test_promotion_cap_examples_store_the_decaying_mean(
    fen: str, line: str, expected_loss: float
) -> None:
    """262 D-02: the caps are unchanged, so the stored loss is the decaying mean of the clipped
    per-depth values; the missed gain is 0.0 with no best line.

    The CONTEXT example "opponent queens at ply 5 and the queen is taken at once, 0.23" is wrong
    under D-01: the queen's 8 and the lost pawn net to -1, so the stored loss is 0.0.
    """
    board = chess.Board(fen)
    inputs = facepalm_material_inputs(board, "g1h1", line, None)
    assert inputs.loss == pytest.approx(expected_loss, rel=1e-9)
    assert inputs.missed == 0.0
