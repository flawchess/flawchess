"""Tests for app/services/line_material.py, the quiet-point rule (Phase 259 D-02).

Coverage:
- labels        : the committed label fixtures reproduce the spike's quiet loss values at depths
                  1/3/5/7/9 and the mate ply (tests/services/line_material_fixtures.py, no
                  gitignored cache is read)
- synthetic     : equal exchanges, static-exchange settlement, desperado exclusion, short-line
                  NULLs and mate rules, built by real replay from a given position
- null          : no line, empty line, malformed or illegal first token, illegal or malformed
                  played move give all-NULL facts and never raise
- purity        : the caller's board (FEN and move stack) is never mutated
- owner misses  : the two owner miss fixtures (games 817357 / 820181) give their depth-3 played
                  and best material through quiet_line_facts and quiet_best_line_facts
- best line     : a best move that mates has opponent_mate_ply 0, an opponent mate settles the
                  line, a malformed or empty best line gives all-None facts
- nine slots    : material_array() is the negated loss for every fixture (9 slots, even slots
                  None), best-line arrays have 9 slots, material_at_depth reads a stored array by
                  depth
"""

from __future__ import annotations

import chess
import pytest

from app.services.line_material import (
    LINE_LOSS_DEPTHS,
    LINE_MATERIAL_SLOTS,
    LineFacts,
    material_at_depth,
    quiet_best_line_facts,
    quiet_line_facts,
)
from tests.services.line_material_fixtures import (
    LINE_FIXTURES,
    OWNER_MISS_FIXTURES,
    LineFixture,
    OwnerMissFixture,
)

# Label #176 (game 483089, ply 67): black Re6-e7 hangs the rook to Rxe7, but Kxe7 wins it back.
_LABEL_176_PRE_FEN = "8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34"
_LABEL_176_PLAYED = "e6e7"
_LABEL_176_LINE = "h7e7"

_NO_LOSS = (None,) * len(LINE_LOSS_DEPTHS)
_ZERO_LOSS = (0,) * len(LINE_LOSS_DEPTHS)


@pytest.mark.parametrize("fixture", OWNER_MISS_FIXTURES, ids=lambda f: f"g{f.game_id}p{f.ply}")
def test_best_line_owner_fixtures(fixture: OwnerMissFixture) -> None:
    pre_board = chess.Board(fixture.pre_fen)
    played = quiet_line_facts(pre_board, fixture.played_uci, fixture.refutation_line)
    best = quiet_best_line_facts(pre_board, fixture.best_line)
    assert played.material_at(3) == fixture.expected_played_3
    assert best.material_at(3) == fixture.expected_best_3


def test_best_line_mate_by_first_move() -> None:
    # Fool's mate: black to move, Qh4 mates at once, so the one-token best line is settled.
    facts = quiet_best_line_facts(_board_after("f2f3 e7e5 g2g4"), "d8h4")
    assert facts.opponent_mate_ply == 0
    assert facts.mate_ply is None
    assert facts.material_at(3) == 0


def test_best_line_opponent_mated_settles() -> None:
    # Scholar's-style: Bc4 (ply 0), ...Nf6 (ply 1), Qxf7# (ply 2) wins a pawn and mates.
    board = _board_after("e2e4 e7e5 d1h5 b8c6")
    facts = quiet_best_line_facts(board, "f1c4 g8f6 h5f7")
    assert facts.opponent_mate_ply == 2
    assert facts.material_at(3) == 1


@pytest.mark.parametrize(
    "best_pv",
    [None, "", "zz99", "a1a8", "zz99 e7e5", "e2e4"],
    ids=["none", "empty", "malformed", "illegal", "malformed_with_tail", "too_short"],
)
def test_best_line_bad_tokens_null(best_pv: str | None) -> None:
    facts = quiet_best_line_facts(chess.Board(), best_pv)
    assert facts.material_at(3) is None
    assert facts.mate_ply is None
    assert facts.opponent_mate_ply is None


@pytest.mark.parametrize("fixture", LINE_FIXTURES, ids=lambda f: f"n{f.label_n}")
def test_material_array_is_negated_loss_on_label_fixtures(fixture: LineFixture) -> None:
    facts = quiet_line_facts(chess.Board(fixture.pre_fen), fixture.played_uci, fixture.line)
    array = facts.material_array()
    assert len(array) == LINE_MATERIAL_SLOTS == 9
    for depth in range(1, LINE_MATERIAL_SLOTS + 1):
        loss = facts.loss_at(depth)
        assert array[depth - 1] == (None if loss is None else -loss)
    # The odd depths carry the fixture's expected values.
    assert _losses(facts) == fixture.expected_quiet_loss


@pytest.mark.parametrize("fixture", OWNER_MISS_FIXTURES, ids=lambda f: f"g{f.game_id}p{f.ply}")
def test_best_line_nine_slot_material_values(fixture: OwnerMissFixture) -> None:
    array = quiet_best_line_facts(chess.Board(fixture.pre_fen), fixture.best_line).material_array()
    assert len(array) == LINE_MATERIAL_SLOTS
    assert array[3 - 1] == fixture.expected_best_3


def test_material_at_depth_reads_stored_arrays() -> None:
    stored = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    assert material_at_depth(stored, 3) == 30
    assert material_at_depth(stored, 9) == 90
    assert material_at_depth(None, 3) is None
    assert material_at_depth([], 3) is None
    assert material_at_depth([1, 2], 3) is None
    assert material_at_depth([1, 2, None], 3) is None


def test_best_line_does_not_mutate_board() -> None:
    board = _board_after("e2e4 e7e5")
    fen_before, stack_before = board.fen(), len(board.move_stack)
    quiet_best_line_facts(board, "g1f3 b8c6 f1c4")
    assert board.fen() == fen_before
    assert len(board.move_stack) == stack_before


def _losses(facts: LineFacts) -> tuple[int | None, ...]:
    return tuple(facts.loss_at(depth) for depth in LINE_LOSS_DEPTHS)


def _board_after(moves: str) -> chess.Board:
    """The start position with the space-separated UCI moves pushed (real replay)."""
    board = chess.Board()
    for uci in moves.split():
        board.push_uci(uci)
    return board


@pytest.mark.parametrize("fixture", LINE_FIXTURES, ids=lambda f: f"n{f.label_n}")
def test_label_fixture_quiet_rule(fixture: LineFixture) -> None:
    """259 D-02: the quiet walk on every committed fixture (13 unchanged, 4 read past depth 7/9)."""
    facts = quiet_line_facts(chess.Board(fixture.pre_fen), fixture.played_uci, fixture.line)
    assert _losses(facts) == fixture.expected_quiet_loss
    assert facts.mate_ply == fixture.expected_mate_ply


# Even depths are never filled by the quiet rule (D-03: only the odd depths are stored).
_EVEN_DEPTHS = (2, 4, 6, 8)

# A four-capture even trade on d5 (Nxd5 Rxd5 Rxd5 Rxd5) right after the blunderer's quiet first move.
_TRADE_FEN = "6k1/3r4/5n2/3N4/8/8/3R4/3R2K1 w - - 0 1"
_TRADE_LINE = "f6d5 d2d5 d7d5 d1d5 g8g7 h1g1 g7f6 g1f1 f6g7 f1g1"

# The blunderer's own last move is a capture that the opponent can recapture: the old rule keeps
# the +1, the quiet rule settles it (pawn for pawn).
_LAST_CAPTURE_FEN = "3q2k1/p7/8/3p4/4P3/8/8/6K1 w - - 0 1"
_LAST_CAPTURE_LINE = "a7a6 e4d5"

# The opponent's last capture cannot be recaptured: the full rook is lost.
_UNRECAPTURED_FEN = "4k3/8/8/8/8/8/r7/R5K1 w - - 0 1"

# Desperado: the blunderer's rook steps to a2 (no capture) and the opponent takes it there. That
# capture is the engine's spite move, not material the blunder cost, so it is not counted.
_DESPERADO_FEN = "4k3/8/8/8/8/8/1r6/R5K1 w - - 0 1"

# (id, fen, blunder, stored line, expected quiet loss per odd depth, expected mate ply)
_QUIET_SYNTHETIC = [
    ("even_four_capture_trade", _TRADE_FEN, "g1h1", _TRADE_LINE, _ZERO_LOSS, None),
    # Last line move is the blunderer's capture of a protected pawn: settled in the opponent's favour.
    (
        "line_ends_on_blunderer_capture",
        _LAST_CAPTURE_FEN,
        "g1h1",
        _LAST_CAPTURE_LINE,
        _ZERO_LOSS,
        None,
    ),
    # Last line move is the opponent's rook capture and the blunderer recaptures it (label 176).
    (
        "line_ends_on_opponent_capture_recaptured",
        _LABEL_176_PRE_FEN,
        _LABEL_176_PLAYED,
        _LABEL_176_LINE,
        _ZERO_LOSS,
        None,
    ),
    (
        "line_ends_on_opponent_capture_unrecaptured",
        _UNRECAPTURED_FEN,
        "g1h1",
        "a2a1",
        (5, 5, 5, 5, 5),
        None,
    ),
    (
        "desperado_capture_is_not_counted",
        _DESPERADO_FEN,
        "g1h1",
        "e8e7 a1a2 b2a2",
        _ZERO_LOSS,
        None,
    ),
    # No capture and a two-ply line: depth 1 is settled, the rest is too short to tell (D-05).
    (
        "quiet_line_too_short",
        "4k3/8/8/8/8/8/8/R3K3 w - - 0 1",
        "a1a2",
        "e8e7 e1d1",
        (0,) + (None,) * 4,
        None,
    ),
]


@pytest.mark.parametrize(
    ("fen", "blunder", "line", "expected_loss", "expected_mate"),
    [case[1:] for case in _QUIET_SYNTHETIC],
    ids=[case[0] for case in _QUIET_SYNTHETIC],
)
def test_quiet_synthetic_rules(
    fen: str,
    blunder: str,
    line: str,
    expected_loss: tuple[int | None, ...],
    expected_mate: int | None,
) -> None:
    facts = quiet_line_facts(chess.Board(fen), blunder, line)
    assert _losses(facts) == expected_loss
    assert facts.mate_ply == expected_mate
    assert all(facts.loss_at(depth) is None for depth in _EVEN_DEPTHS)


def test_quiet_mate_settles_short_line() -> None:
    # Fool's mate: the blunderer is mated at ply 1, which settles every odd depth.
    facts = quiet_line_facts(_board_after("f2f3 e7e5"), "g2g4", "d8h4")
    assert facts.mate_ply == 1
    assert _losses(facts) == _ZERO_LOSS


def test_quiet_best_line_mate_by_first_move() -> None:
    facts = quiet_best_line_facts(_board_after("f2f3 e7e5 g2g4"), "d8h4")
    assert facts.opponent_mate_ply == 0
    assert facts.mate_ply is None
    assert facts.material_at(3) == 0


@pytest.mark.parametrize(
    ("played", "line"),
    [
        ("e2e4", None),
        ("e2e4", ""),
        ("e2e4", "zz99"),
        ("e2e4", "a1a8"),
        ("e2e5", "e7e5"),
        ("zz99", "e7e5"),
        ("e2e4", "zz99 e7e5"),
    ],
    ids=[
        "no_line",
        "empty_line",
        "malformed_first_token",
        "illegal_first_token",
        "illegal_played_move",
        "malformed_played_move",
        "malformed_first_token_with_tail",
    ],
)
def test_quiet_unusable_input_gives_null_facts(played: str, line: str | None) -> None:
    facts = quiet_line_facts(chess.Board(), played, line)
    assert _losses(facts) == _NO_LOSS
    assert facts.mate_ply is None
    assert facts.material_array() == [None] * LINE_MATERIAL_SLOTS


@pytest.mark.parametrize(
    "best_pv",
    [None, "", "zz99", "a1a8", "zz99 e7e5", "e2e4"],
    ids=["none", "empty", "malformed", "illegal", "malformed_with_tail", "too_short"],
)
def test_quiet_best_line_bad_tokens_null(best_pv: str | None) -> None:
    facts = quiet_best_line_facts(chess.Board(), best_pv)
    assert facts.material_at(3) is None
    assert facts.mate_ply is None
    assert facts.opponent_mate_ply is None


def test_quiet_caller_board_is_not_mutated() -> None:
    board = _board_after("e2e4 e7e5")
    fen_before, stack_before = board.fen(), len(board.move_stack)
    quiet_line_facts(board, "g1f3", "b8c6 f1c4 g8f6 e1g1")
    quiet_best_line_facts(board, "g1f3 b8c6 f1c4")
    assert board.fen() == fen_before
    assert len(board.move_stack) == stack_before
