"""Unit tests for Zobrist hash computation module.

Tests verify determinism, color-independence, BIGINT safety, PGN parsing, and
transposition equivalence for the three-hash scheme (white_hash, black_hash, full_hash).
"""

import chess
import chess.pgn
import pytest

from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD
from app.services.position_classifier import classify_position
from app.services.zobrist import (
    compute_hashes,
    hashes_for_game,
    process_game_pgn,
)

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_after_e4():
    b = chess.Board()
    b.push_san("e4")
    return b


@pytest.fixture
def board_after_e4_e5():
    b = chess.Board()
    b.push_san("e4")
    b.push_san("e5")
    return b


@pytest.fixture
def board_after_e4_d5():
    b = chess.Board()
    b.push_san("e4")
    b.push_san("d5")
    return b


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_starting_position_is_deterministic(starting_board):
    """Same board position yields identical hashes on repeated calls."""
    wh1, bh1, fh1 = compute_hashes(starting_board)
    wh2, bh2, fh2 = compute_hashes(starting_board)
    assert wh1 == wh2
    assert bh1 == bh2
    assert fh1 == fh2


def test_two_fresh_boards_produce_equal_hashes():
    """Two independently created starting boards yield the same hashes."""
    board_a = chess.Board()
    board_b = chess.Board()
    assert compute_hashes(board_a) == compute_hashes(board_b)


# ---------------------------------------------------------------------------
# Different positions produce different full_hash
# ---------------------------------------------------------------------------


def test_different_positions_different_full_hash(starting_board, board_after_e4):
    """Starting position and position after 1.e4 have different full_hash values."""
    _, _, fh_start = compute_hashes(starting_board)
    _, _, fh_e4 = compute_hashes(board_after_e4)
    assert fh_start != fh_e4


# ---------------------------------------------------------------------------
# Color independence
# ---------------------------------------------------------------------------


def test_white_hash_ignores_black_moves(board_after_e4_e5, board_after_e4_d5):
    """After 1.e4 e5 vs 1.e4 d5, white_hash is identical (white pawn on e4 in both)."""
    wh_e5, _, _ = compute_hashes(board_after_e4_e5)
    wh_d5, _, _ = compute_hashes(board_after_e4_d5)
    assert wh_e5 == wh_d5


def test_black_hash_ignores_white_moves():
    """After 1.e4 e5 vs 1.d4 e5, black_hash is identical (black pawn on e5 in both)."""
    b1 = chess.Board()
    b1.push_san("e4")
    b1.push_san("e5")

    b2 = chess.Board()
    b2.push_san("d4")
    b2.push_san("e5")

    _, bh1, _ = compute_hashes(b1)
    _, bh2, _ = compute_hashes(b2)
    assert bh1 == bh2


def test_white_hash_changes_when_white_moves(starting_board, board_after_e4):
    """White pawn moved to e4 means white_hash differs from starting position."""
    wh_start, _, _ = compute_hashes(starting_board)
    wh_e4, _, _ = compute_hashes(board_after_e4)
    assert wh_start != wh_e4


def test_black_hash_changes_when_black_moves(board_after_e4, board_after_e4_e5):
    """Black pawn moved to e5 means black_hash differs from position after 1.e4."""
    _, bh_e4, _ = compute_hashes(board_after_e4)
    _, bh_e4_e5, _ = compute_hashes(board_after_e4_e5)
    assert bh_e4 != bh_e4_e5


# ---------------------------------------------------------------------------
# BIGINT safety
# ---------------------------------------------------------------------------


def test_hashes_are_signed_int64(starting_board):
    """All three hash values must fit in PostgreSQL BIGINT range."""
    for h in compute_hashes(starting_board):
        assert INT64_MIN <= h <= INT64_MAX


def test_hashes_are_signed_int64_after_moves(board_after_e4_e5):
    """Hash values remain within BIGINT range after moves."""
    for h in compute_hashes(board_after_e4_e5):
        assert INT64_MIN <= h <= INT64_MAX


# ---------------------------------------------------------------------------
# Empty board
# ---------------------------------------------------------------------------


def test_empty_board_hashes(empty_board):
    """Cleared board: white_hash and black_hash are 0; full_hash need not be 0."""
    wh, bh, fh = compute_hashes(empty_board)
    assert wh == 0, f"Expected white_hash=0 on empty board, got {wh}"
    assert bh == 0, f"Expected black_hash=0 on empty board, got {bh}"
    # full_hash is from the library — just check it's a valid int64
    assert INT64_MIN <= fh <= INT64_MAX


# ---------------------------------------------------------------------------
# hashes_for_game — PGN parsing
# ---------------------------------------------------------------------------

SIMPLE_PGN = "1. e4 e5 2. Nf3 *"


def test_hashes_for_game_includes_ply_zero():
    """PGN '1. e4 e5 2. Nf3 *' has 3 half-moves, so 4 entries (ply 0 through 3)."""
    results, _ = hashes_for_game(SIMPLE_PGN)
    assert len(results) == 4
    plies = [r[0] for r in results]
    assert plies == [0, 1, 2, 3]


def test_hashes_for_game_ply_zero_is_starting_position():
    """Ply 0 entry matches compute_hashes on a fresh Board()."""
    results, _ = hashes_for_game(SIMPLE_PGN)
    ply0_wh, ply0_bh, ply0_fh = results[0][1], results[0][2], results[0][3]
    expected_wh, expected_bh, expected_fh = compute_hashes(chess.Board())
    assert ply0_wh == expected_wh
    assert ply0_bh == expected_bh
    assert ply0_fh == expected_fh


def test_hashes_for_game_empty_pgn():
    """Empty string returns ([], None)."""
    result, fen = hashes_for_game("")
    assert result == []
    assert fen is None


def test_hashes_for_game_invalid_pgn():
    """Garbage string returns ([], None)."""
    result, fen = hashes_for_game("not a pgn at all !!!")
    assert result == []
    assert fen is None


def test_hashes_for_game_returns_int64_values():
    """All hash values in the returned list are within BIGINT range."""
    tuples, _ = hashes_for_game(SIMPLE_PGN)
    for _, wh, bh, fh, _, _ in tuples:
        assert INT64_MIN <= wh <= INT64_MAX
        assert INT64_MIN <= bh <= INT64_MAX
        assert INT64_MIN <= fh <= INT64_MAX


def test_hashes_for_game_returns_move_san():
    """For PGN '1. e4 e5 2. Nf3 *', result has 4 entries with correct move_san values."""
    results, _ = hashes_for_game(SIMPLE_PGN)
    assert len(results) == 4
    # Each entry is a 6-tuple
    assert all(len(r) == 6 for r in results)
    # move_san values: e4, e5, Nf3, None (final position)
    assert results[0][4] == "e4"
    assert results[1][4] == "e5"
    assert results[2][4] == "Nf3"
    assert results[3][4] is None


def test_hashes_for_game_move_san_null_on_final_ply():
    """For PGN '1. e4 *', result has 2 entries; final position has move_san=None."""
    results, _ = hashes_for_game("1. e4 *")
    assert len(results) == 2
    assert results[1][4] is None


def test_hashes_for_game_move_san_ply_zero():
    """For PGN '1. e4 e5 *', ply-0 has move_san='e4' (first move SAN, not None)."""
    results, _ = hashes_for_game("1. e4 e5 *")
    assert results[0][4] == "e4"


def test_hashes_for_game_preserves_hash_values():
    """Ply-0 hashes match compute_hashes(chess.Board()); ply-1 hashes match board after e4."""
    results, _ = hashes_for_game(SIMPLE_PGN)
    # ply-0 hashes = starting position
    expected_wh, expected_bh, expected_fh = compute_hashes(chess.Board())
    assert results[0][1] == expected_wh
    assert results[0][2] == expected_bh
    assert results[0][3] == expected_fh
    # ply-1 hashes = board after e4
    board_after_e4 = chess.Board()
    board_after_e4.push_san("e4")
    exp_wh, exp_bh, exp_fh = compute_hashes(board_after_e4)
    assert results[1][1] == exp_wh
    assert results[1][2] == exp_bh
    assert results[1][3] == exp_fh


def test_hashes_for_game_returns_result_fen():
    """hashes_for_game returns a non-None result_fen for a valid PGN."""
    pgn = "1. e4 e5 2. Nf3 *"
    tuples, result_fen = hashes_for_game(pgn)
    assert result_fen is not None
    # After 1. e4 e5 2. Nf3, the board FEN should have the knight on f3
    assert "N" in result_fen  # White knight present
    assert "/" in result_fen  # Valid FEN format with rank separators


def test_hashes_for_game_empty_returns_none_fen():
    """Empty PGN returns ([], None) — result_fen is None."""
    tuples, result_fen = hashes_for_game("")
    assert tuples == []
    assert result_fen is None


# ---------------------------------------------------------------------------
# Transposition equivalence
# ---------------------------------------------------------------------------


def test_transposition_produces_same_hashes():
    """Same final position reached via different move orders has identical hash tuples."""
    # Italian game can be reached as 1.e4 e5 2.Nf3 Nc6 3.Bc4
    # or via 1.e4 Nc6 2.Nf3 e5 3.Bc4 (order of black's first two moves swapped)
    b1 = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4"]:
        b1.push_san(san)

    b2 = chess.Board()
    for san in ["e4", "Nc6", "Nf3", "e5", "Bc4"]:
        b2.push_san(san)

    assert compute_hashes(b1) == compute_hashes(b2)


# ---------------------------------------------------------------------------
# hashes_for_game — clock extraction
# ---------------------------------------------------------------------------

PGN_WITH_CLK = '[Event "?"]\n\n1. e4 {[%clk 0:09:58.3]} e5 {[%clk 0:09:56.1]} *'
PGN_WITHOUT_CLK = "1. e4 e5 2. Nf3 *"


def test_hashes_for_game_with_clk_returns_6_tuples():
    """PGN with %clk annotations returns 6-tuples."""
    results, _ = hashes_for_game(PGN_WITH_CLK)
    assert all(len(r) == 6 for r in results)


def test_hashes_for_game_with_clk_clock_seconds_are_floats():
    """PGN with %clk: clock_seconds for non-final positions are floats."""
    results, _ = hashes_for_game(PGN_WITH_CLK)
    # 3 entries: ply 0 (before e4), ply 1 (before e5), ply 2 (final)
    # ply 0 clock = 9*60 + 58.3 = 598.3
    assert results[0][5] == pytest.approx(598.3, abs=0.01)
    # ply 1 clock = 9*60 + 56.1 = 596.1
    assert results[1][5] == pytest.approx(596.1, abs=0.01)


def test_hashes_for_game_with_clk_final_position_clock_is_none():
    """PGN with %clk: final position row always has clock_seconds=None."""
    results, _ = hashes_for_game(PGN_WITH_CLK)
    # Last entry is final position
    assert results[-1][5] is None


def test_hashes_for_game_without_clk_returns_6_tuples():
    """PGN without %clk still returns 6-tuples."""
    results, _ = hashes_for_game(PGN_WITHOUT_CLK)
    assert all(len(r) == 6 for r in results)


def test_hashes_for_game_without_clk_clock_seconds_are_none():
    """PGN without %clk: all clock_seconds are None."""
    results, _ = hashes_for_game(PGN_WITHOUT_CLK)
    for r in results:
        assert r[5] is None


# ---------------------------------------------------------------------------
# process_game_pgn — unified function tests
# ---------------------------------------------------------------------------

SIMPLE_PGN_3_MOVES = "1. e4 e5 2. Nf3 *"
PGN_WITH_EVAL = '[Event "?"]\n\n1. e4 {[%eval 0.3]} e5 {[%eval 0.2]} *'


def test_process_game_pgn_returns_correct_ply_count():
    """PGN '1. e4 e5 2. Nf3 *' has 3 half-moves, so 4 plies (ply 0 through 3)."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    assert len(result["plies"]) == 4
    plies = [p["ply"] for p in result["plies"]]
    assert plies == [0, 1, 2, 3]


def test_process_game_pgn_empty_pgn_returns_none():
    """Empty string returns None."""
    assert process_game_pgn("") is None


def test_process_game_pgn_invalid_pgn_returns_none():
    """Garbage string returns None."""
    assert process_game_pgn("not valid pgn!!!") is None


def test_process_game_pgn_hashes_match_compute_hashes():
    """Ply 0 hashes match compute_hashes(chess.Board()) — starting position."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    ply0 = result["plies"][0]
    expected_wh, expected_bh, expected_fh = compute_hashes(chess.Board())
    assert ply0["white_hash"] == expected_wh
    assert ply0["black_hash"] == expected_bh
    assert ply0["full_hash"] == expected_fh


def test_process_game_pgn_move_san_correct():
    """Ply 0 has move_san='e4' (first move); final ply has move_san=None."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    assert result["plies"][0]["move_san"] == "e4"
    assert result["plies"][-1]["move_san"] is None


def test_process_game_pgn_move_count():
    """PGN '1. e4 e5 2. Nf3 *' has move_count=2 (2 full moves)."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    assert result["move_count"] == 2


def test_process_game_pgn_result_fen():
    """result_fen is not None and contains 'N' (knight on f3)."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    assert result["result_fen"] is not None
    assert "N" in result["result_fen"]  # White knight present after 2. Nf3


def test_process_game_pgn_classification_matches_classify_position():
    """Ply 0 classification fields match classify_position(chess.Board())."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    ply0 = result["plies"][0]
    expected = classify_position(chess.Board())
    assert ply0["material_count"] == expected.material_count
    assert ply0["material_signature"] == expected.material_signature
    assert ply0["material_imbalance"] == expected.material_imbalance
    assert ply0["has_opposite_color_bishops"] == expected.has_opposite_color_bishops
    assert ply0["piece_count"] == expected.piece_count
    assert ply0["backrank_sparse"] == expected.backrank_sparse
    assert ply0["mixedness"] == expected.mixedness


def test_process_game_pgn_eval_extraction():
    """PGN with %eval annotations returns non-None eval_cp values."""
    result = process_game_pgn(PGN_WITH_EVAL)
    assert result is not None
    # ply 0 has eval from %eval 0.3 on the e4 move node (30 centipawns from white's POV)
    assert result["plies"][0]["eval_cp"] == 30
    assert result["plies"][0]["eval_mate"] is None
    # ply 1 has eval from %eval 0.2 on the e5 move node (20 centipawns from white's POV)
    assert result["plies"][1]["eval_cp"] == 20
    # final ply has no eval annotation
    assert result["plies"][-1]["eval_cp"] is None


def test_process_game_pgn_clock_extraction():
    """PGN with %clk annotations returns correct clock_seconds values."""
    result = process_game_pgn(PGN_WITH_CLK)
    assert result is not None
    # ply 0 clock = 9*60 + 58.3 = 598.3
    assert result["plies"][0]["clock_seconds"] == pytest.approx(598.3, abs=0.01)
    # ply 1 clock = 9*60 + 56.1 = 596.1
    assert result["plies"][1]["clock_seconds"] == pytest.approx(596.1, abs=0.01)
    # final ply has no clock annotation
    assert result["plies"][-1]["clock_seconds"] is None


def test_process_game_pgn_endgame_class_none_for_opening():
    """Ply 0 of a standard game has endgame_class=None (piece_count > threshold)."""
    result = process_game_pgn(SIMPLE_PGN_3_MOVES)
    assert result is not None
    ply0 = result["plies"][0]
    # Starting position has piece_count=14 which is > ENDGAME_PIECE_COUNT_THRESHOLD (6)
    assert ply0["piece_count"] > ENDGAME_PIECE_COUNT_THRESHOLD
    assert ply0["endgame_class"] is None


def test_hashes_for_game_wrapper_matches_process_game_pgn():
    """hashes_for_game and process_game_pgn return identical hash/move_san/clock values."""
    pgn = SIMPLE_PGN_3_MOVES
    hash_tuples, fen1 = hashes_for_game(pgn)
    result = process_game_pgn(pgn)
    assert result is not None
    assert fen1 == result["result_fen"]
    assert len(hash_tuples) == len(result["plies"])
    for (ply, wh, bh, fh, move_san, clock), ply_data in zip(hash_tuples, result["plies"]):
        assert ply == ply_data["ply"]
        assert wh == ply_data["white_hash"]
        assert bh == ply_data["black_hash"]
        assert fh == ply_data["full_hash"]
        assert move_san == ply_data["move_san"]
        assert clock == ply_data["clock_seconds"]
