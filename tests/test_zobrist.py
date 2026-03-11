"""Unit tests for Zobrist hash computation module.

Tests verify determinism, color-independence, BIGINT safety, PGN parsing, and
transposition equivalence for the three-hash scheme (white_hash, black_hash, full_hash).
"""
import chess
import chess.pgn
import io
import pytest

from app.services.zobrist import compute_hashes, hashes_for_game

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
    """PGN '1. e4 e5 2. Nf3 *' should yield 5 entries (ply 0 through 4)."""
    results = hashes_for_game(SIMPLE_PGN)
    assert len(results) == 5
    plies = [r[0] for r in results]
    assert plies == [0, 1, 2, 3, 4]


def test_hashes_for_game_ply_zero_is_starting_position():
    """Ply 0 entry matches compute_hashes on a fresh Board()."""
    results = hashes_for_game(SIMPLE_PGN)
    ply0_wh, ply0_bh, ply0_fh = results[0][1], results[0][2], results[0][3]
    expected_wh, expected_bh, expected_fh = compute_hashes(chess.Board())
    assert ply0_wh == expected_wh
    assert ply0_bh == expected_bh
    assert ply0_fh == expected_fh


def test_hashes_for_game_empty_pgn():
    """Empty string returns empty list."""
    assert hashes_for_game("") == []


def test_hashes_for_game_invalid_pgn():
    """Garbage string returns empty list."""
    assert hashes_for_game("not a pgn at all !!!") == []


def test_hashes_for_game_returns_int64_values():
    """All hash values in the returned list are within BIGINT range."""
    for _, wh, bh, fh in hashes_for_game(SIMPLE_PGN):
        assert INT64_MIN <= wh <= INT64_MAX
        assert INT64_MIN <= bh <= INT64_MAX
        assert INT64_MIN <= fh <= INT64_MAX


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
