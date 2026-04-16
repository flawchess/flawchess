"""Material tally sanity tests (Phase 61).

Verifies that position_classifier's pure functions correctly compute material
metrics from python-chess boards. These tests catch regressions in piece
values, sign conventions, and signature ordering before they reach the DB.
"""

import chess

from app.services.position_classifier import (
    _compute_material_count,
    _compute_material_imbalance,
    _compute_material_signature,
)


class TestMaterialCount:
    """_compute_material_count returns total centipawns for both sides combined."""

    def test_starting_position_is_7800(self) -> None:
        """Starting material = 2 × (Q + 2R + 2B + 2N + 8P) = 2 × 3900 = 7800 cp."""
        assert _compute_material_count(chess.Board()) == 7800

    def test_empty_board_is_zero(self) -> None:
        board = chess.Board()
        board.clear()
        assert _compute_material_count(board) == 0

    def test_after_white_captures_pawn(self) -> None:
        """1. e4 d5 2. exd5 — white captures a black pawn; total drops 100 cp."""
        board = chess.Board()
        for move in ("e4", "d5", "exd5"):
            board.push_san(move)
        assert _compute_material_count(board) == 7700


class TestMaterialImbalance:
    """_compute_material_imbalance returns signed (white − black) centipawns."""

    def test_starting_is_zero(self) -> None:
        assert _compute_material_imbalance(chess.Board()) == 0

    def test_white_up_a_pawn(self) -> None:
        """After 1. e4 d5 2. exd5, white is up one pawn = +100 cp."""
        board = chess.Board()
        for move in ("e4", "d5", "exd5"):
            board.push_san(move)
        assert _compute_material_imbalance(board) == 100

    def test_black_up_a_rook(self) -> None:
        """FEN with white's a1 rook removed → black is up 500 cp = -500 imbalance."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w Kkq - 0 1")
        assert _compute_material_imbalance(board) == -500

    def test_both_sides_missing_queen_is_zero_imbalance(self) -> None:
        """FEN with no queens on either side → imbalance == 0 (equal material)."""
        board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        assert _compute_material_imbalance(board) == 0


class TestMaterialSignature:
    """_compute_material_signature returns canonical 'white_black' piece strings."""

    def test_starting_signature(self) -> None:
        sig = _compute_material_signature(chess.Board())
        assert sig == "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP"

    def test_white_before_black(self) -> None:
        """Starting position is symmetric — both sides have identical piece strings."""
        sig = _compute_material_signature(chess.Board())
        assert "_" in sig
        white, black = sig.split("_")
        assert white == black
        assert white.startswith("K")

    def test_missing_white_queen(self) -> None:
        """Remove white queen via FEN; signature's white half must not contain Q."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        sig = _compute_material_signature(board)
        white, _black = sig.split("_")
        assert "Q" not in white
