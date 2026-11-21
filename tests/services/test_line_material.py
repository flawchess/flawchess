"""Tests for app/services/line_material.py (Phase 250 D-02, D-05).

Coverage:
- labels        : the ten D-02 label positions and the seven 1-ply mate lines reproduce the
                  reference capture_loss values at depths 1/3/5/7/9 and the mate ply
                  (tests/services/line_material_fixtures.py, no gitignored cache is read)
- synthetic     : depth + 1 recapture, short-line NULLs, en passant credit, illegal mid-line
                  token and mate rules, built by real replay from the start position
- null          : no line, empty line, malformed or illegal first token, illegal or malformed
                  played move give all-NULL facts and never raise
- purity        : the caller's board (FEN and move stack) is never mutated
- owner misses  : the two owner miss fixtures (games 817357 / 820181) give their depth-3 played
                  and best material through line_facts and best_line_facts (Phase 254 D-05, D-09)
- best line     : a best move that mates has opponent_mate_ply 0, an opponent mate settles the
                  line, a malformed or empty best line gives all-None facts
- nine slots    : material_array() is the negated loss for every 250 fixture (9 slots, even slots
                  are mid-exchange values), best-line arrays have 9 slots, material_at_depth reads
                  a stored array by depth (Phase 254 D-09, D-17)
- tracer pure   : label #176, a 1-ply line settled by the static-exchange recapture credit
- tracer storage: one real blunder's line facts round-trip through the new game_flaws columns
                  and the two new games stamps start NULL

Every seeded game is deleted in `finally` (leaked non-guest full-eval games poison the
global eval lottery and other modules' foreign-pick tests).
"""

from __future__ import annotations

import io

import chess
import pytest
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.repositories.game_flaws_repository import bulk_update_game_flaw_rows
from app.services.line_material import (
    LINE_LOSS_DEPTHS,
    LineFacts,
    LINE_MATERIAL_SLOTS,
    best_line_facts,
    line_facts,
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
from tests.blunder_check_seed import (
    SEED_PGN,
    SeedBlunder,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)

# Label #176 (game 483089, ply 67): black Re6-e7 hangs the rook to Rxe7, but Kxe7 wins it back.
_LABEL_176_PRE_FEN = "8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34"
_LABEL_176_PLAYED = "e6e7"
_LABEL_176_LINE = "h7e7"

_SEED_ROWS = 61  # positions of SEED_PGN (60 plies + the final position)
_SEED_BLUNDER_PLY = 40  # white user's blunder; 20 clean user moves precede it
_SEED_BLUNDER_DROP_CP = 600
_SEED_LINE_PLIES = 10  # next ten mainline moves after the blunder form the stored line

_NO_LOSS = (None,) * len(LINE_LOSS_DEPTHS)
_ZERO_LOSS = (0,) * len(LINE_LOSS_DEPTHS)


def test_label_176_recapture_credit_settles_one_ply_line() -> None:
    facts = line_facts(chess.Board(_LABEL_176_PRE_FEN), _LABEL_176_PLAYED, _LABEL_176_LINE)
    assert [facts.loss_at(depth) for depth in LINE_LOSS_DEPTHS] == [0] * len(LINE_LOSS_DEPTHS)
    assert facts.mate_ply is None


@pytest.mark.parametrize("fixture", OWNER_MISS_FIXTURES, ids=lambda f: f"g{f.game_id}p{f.ply}")
def test_best_line_owner_fixtures(fixture: OwnerMissFixture) -> None:
    pre_board = chess.Board(fixture.pre_fen)
    played = line_facts(pre_board, fixture.played_uci, fixture.refutation_line)
    best = best_line_facts(pre_board, fixture.best_line)
    assert played.material_at(3) == fixture.expected_played_3
    assert best.material_at(3) == fixture.expected_best_3


def test_best_line_mate_by_first_move() -> None:
    # Fool's mate: black to move, Qh4 mates at once, so the one-token best line is settled.
    facts = best_line_facts(_board_after("f2f3 e7e5 g2g4"), "d8h4")
    assert facts.opponent_mate_ply == 0
    assert facts.mate_ply is None
    assert facts.material_at(3) == 0


def test_best_line_opponent_mated_settles() -> None:
    # Scholar's-style: Bc4 (ply 0), ...Nf6 (ply 1), Qxf7# (ply 2) wins a pawn and mates.
    board = _board_after("e2e4 e7e5 d1h5 b8c6")
    facts = best_line_facts(board, "f1c4 g8f6 h5f7")
    assert facts.opponent_mate_ply == 2
    assert facts.material_at(3) == 1


@pytest.mark.parametrize(
    "best_pv",
    [None, "", "zz99", "a1a8", "zz99 e7e5", "e2e4"],
    ids=["none", "empty", "malformed", "illegal", "malformed_with_tail", "too_short"],
)
def test_best_line_bad_tokens_null(best_pv: str | None) -> None:
    facts = best_line_facts(chess.Board(), best_pv)
    assert facts.material_at(3) is None
    assert facts.mate_ply is None
    assert facts.opponent_mate_ply is None


@pytest.mark.parametrize("fixture", LINE_FIXTURES, ids=lambda f: f"n{f.label_n}")
def test_material_array_is_negated_loss_on_250_fixtures(fixture: LineFixture) -> None:
    facts = line_facts(chess.Board(fixture.pre_fen), fixture.played_uci, fixture.line)
    array = facts.material_array()
    assert len(array) == LINE_MATERIAL_SLOTS == 9
    for depth in range(1, LINE_MATERIAL_SLOTS + 1):
        loss = facts.loss_at(depth)
        assert array[depth - 1] == (None if loss is None else -loss)
    # The legacy odd depths still carry the 250 expected values.
    assert _losses(facts) == fixture.expected_loss


@pytest.mark.parametrize("fixture", OWNER_MISS_FIXTURES, ids=lambda f: f"g{f.game_id}p{f.ply}")
def test_best_line_material_array_nine_slots(fixture: OwnerMissFixture) -> None:
    array = best_line_facts(chess.Board(fixture.pre_fen), fixture.best_line).material_array()
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
    best_line_facts(board, "g1f3 b8c6 f1c4")
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
def test_label_fixture_matches_reference(fixture: LineFixture) -> None:
    facts = line_facts(chess.Board(fixture.pre_fen), fixture.played_uci, fixture.line)
    assert _losses(facts) == fixture.expected_loss
    assert facts.mate_ply == fixture.expected_mate_ply


# (id, moves before the blunder, blunder, stored line, expected loss per depth, expected mate ply)
_SYNTHETIC = [
    # d1 includes the blunderer's recapture at depth + 1; the four-ply line stops short of d5+.
    (
        "depth_plus_one_recapture",
        "e2e4",
        "d7d5",
        "e4d5 d8d5 b1c3 d5a5",
        (0, 0, None, None, None),
        None,
    ),
    ("line_too_short", "e2e4 e7e5", "g1f3", "b8c6 f1c4", (0, None, None, None, None), None),
    # An en passant capture is worth one pawn; the recapture credit settles the 1-ply line.
    ("en_passant_credit", "e2e4 g8f6 e4e5", "d7d5", "e5d6", _ZERO_LOSS, None),
    # b8c6 then a1a8 (blocked rook, illegal): the walk stops, so only depth 1 is settled.
    (
        "illegal_second_token",
        "e2e4 e7e5",
        "g1f3",
        "b8c6 a1a8 f1c4",
        (0, None, None, None, None),
        None,
    ),
    ("fools_mate", "f2f3 e7e5", "g2g4", "d8h4", _ZERO_LOSS, 1),
]


@pytest.mark.parametrize(
    ("moves", "blunder", "line", "expected_loss", "expected_mate"),
    [case[1:] for case in _SYNTHETIC],
    ids=[case[0] for case in _SYNTHETIC],
)
def test_synthetic_rules(
    moves: str,
    blunder: str,
    line: str,
    expected_loss: tuple[int | None, ...],
    expected_mate: int | None,
) -> None:
    facts = line_facts(_board_after(moves), blunder, line)
    assert _losses(facts) == expected_loss
    assert facts.mate_ply == expected_mate


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


def test_quiet_rule_differs_from_the_old_rule_on_a_blunderer_capture_ending() -> None:
    """The old walk keeps the blunderer's last capture; the quiet rule settles the recapture."""
    board = chess.Board(_LAST_CAPTURE_FEN)
    old = line_facts(board, "g1h1", _LAST_CAPTURE_LINE)
    assert old.loss_at(1) == -1
    assert quiet_line_facts(board, "g1h1", _LAST_CAPTURE_LINE).loss_at(1) == 0


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
def test_unusable_input_gives_null_facts(played: str, line: str | None) -> None:
    facts = line_facts(chess.Board(), played, line)
    assert _losses(facts) == _NO_LOSS
    assert facts.mate_ply is None
    assert facts.material_array() == [None] * LINE_MATERIAL_SLOTS


def test_caller_board_is_not_mutated() -> None:
    board = _board_after("e2e4 e7e5")
    fen_before, stack_before = board.fen(), len(board.move_stack)
    line_facts(board, "g1f3", "b8c6 f1c4 g8f6 e1g1")
    assert board.fen() == fen_before
    assert len(board.move_stack) == stack_before


def _replayed_mainline(pgn: str) -> tuple[list[chess.Board], list[chess.Move]]:
    """Boards BEFORE each ply (real move replay) and the played moves."""
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    assert parsed is not None
    board = parsed.board()
    boards: list[chess.Board] = []
    moves: list[chess.Move] = []
    for node in parsed.mainline():
        boards.append(board.copy())
        moves.append(node.move)
        board.push(node.move)
    return boards, moves


async def test_line_facts_round_trip_through_game_flaws_arrays(test_engine) -> None:
    user_id, _ = await register_user("line-material", beta=True, test_engine=test_engine)
    evals = with_user_blunder(flat_evals(_SEED_ROWS, 0), _SEED_BLUNDER_PLY, _SEED_BLUNDER_DROP_CP)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=_SEED_BLUNDER_PLY)],
    )
    try:
        boards, moves = _replayed_mainline(SEED_PGN)
        line = " ".join(
            move.uci()
            for move in moves[_SEED_BLUNDER_PLY + 1 : _SEED_BLUNDER_PLY + 1 + _SEED_LINE_PLIES]
        )
        facts = line_facts(boards[_SEED_BLUNDER_PLY], moves[_SEED_BLUNDER_PLY].uci(), line)
        columns = {
            "played_line_material": facts.material_array(),
            "line_mate_ply": facts.mate_ply,
        }
        # A ten-ply line reaches every odd stored depth, so none of those slots is NULL.
        assert all(facts.material_at(depth) is not None for depth in LINE_LOSS_DEPTHS)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            await bulk_update_game_flaw_rows(
                session,
                [{"user_id": user_id, "game_id": game_id, "ply": _SEED_BLUNDER_PLY, **columns}],
            )
            await session.commit()
        async with maker() as session:
            flaw = (
                await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id))
            ).scalar_one()
            game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one()
        stored = {
            "played_line_material": flaw.played_line_material,
            "line_mate_ply": flaw.line_mate_ply,
        }
        assert stored == columns
        assert flaw.played_line_material == facts.material_array()
        assert game.facepalm_spread_completed_at is None
        assert game.facepalm_line_completed_at is None
    finally:
        await delete_games(test_engine, [game_id])
