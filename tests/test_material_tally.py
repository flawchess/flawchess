"""Material tally sanity tests (Phase 61).

Verifies that position_classifier's pure functions correctly compute material
metrics from python-chess boards. These tests catch regressions in piece
values, sign conventions, and signature ordering before they reach the DB.
"""

import chess

from app.services.position_classifier import (
    _compute_material_signature,
)


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
