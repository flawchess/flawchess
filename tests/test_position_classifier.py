"""Tests for the position_classifier module.

Covers:
- Material count computation (total centipawns both sides)
- Material signature computation (canonical form, stronger side first)
- Material imbalance computation
- Tactical indicators (opposite-color bishops)
"""

import chess

from app.services.position_classifier import PositionClassification, classify_position


# ---------------------------------------------------------------------------
# Helpers for constructing test boards
# ---------------------------------------------------------------------------


def board_from_fen(fen: str) -> chess.Board:
    """Return a chess.Board from a FEN string."""
    return chess.Board(fen)


# ---------------------------------------------------------------------------
# Material Count tests
# ---------------------------------------------------------------------------

# Starting material per side: 8P(800) + 2N(600) + 2B(600) + 2R(1000) + Q(900) = 3900
# Both sides starting total: 7800
_STARTING_MATERIAL_COUNT = 7800


class TestMaterialCount:
    def test_starting_position_material_count(self, starting_board: chess.Board) -> None:
        """Starting position has full material: 7800 centipawns total."""
        result = classify_position(starting_board)
        assert result.material_count == _STARTING_MATERIAL_COUNT

    def test_bare_kings_zero_material(self) -> None:
        """K vs K: zero material (kings are not counted)."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.material_count == 0

    def test_single_pawn_each_side(self) -> None:
        """K+P vs K+P: 200 centipawns total."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.E7, chess.Piece(chess.PAWN, chess.BLACK))
        result = classify_position(board)
        assert result.material_count == 200

    def test_asymmetric_material(self) -> None:
        """K+Q vs K+R: 900 + 500 = 1400 centipawns total."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.material_count == 1400

    def test_material_decreases_with_captures(self) -> None:
        """Removing a pawn should decrease material_count by 100."""
        board = chess.Board()
        full = classify_position(board)
        # Remove one white pawn
        board.remove_piece_at(chess.A2)
        after = classify_position(board)
        assert after.material_count == full.material_count - 100


# ---------------------------------------------------------------------------
# Material Signature tests
# ---------------------------------------------------------------------------


class TestMaterialSignature:
    def test_starting_position_signature(self, starting_board: chess.Board) -> None:
        """Starting position produces the full symmetric signature (33 chars)."""
        result = classify_position(starting_board)
        assert result.material_signature == "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP"

    def test_starting_position_signature_length(self, starting_board: chess.Board) -> None:
        """Starting position signature must be 33 chars (fits in String(40))."""
        result = classify_position(starting_board)
        assert len(result.material_signature) == 33

    def test_asymmetric_stronger_side_first(self) -> None:
        """KRP vs KR: asymmetric position, stronger side (with pawn) must be first."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "KRP_KR"

    def test_bare_kings_signature(self) -> None:
        """K vs K: bare kings only."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "K_K"

    def test_symmetric_qr_signature(self) -> None:
        """KQR vs KQR: symmetric position should produce KQR_KQR (lexicographic tie-break)."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "KQR_KQR"

    def test_symmetric_signature_deterministic_regardless_of_color(self) -> None:
        """Symmetric positions must produce identical signatures regardless of which side we view from."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "KQ_KQ"

    def test_asymmetric_black_stronger(self) -> None:
        """When black has more material, stronger side must still come first in signature."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "KQ_KR"

    def test_pawn_endgame_signature(self) -> None:
        """KPP vs KP: correct pawn count with stronger side first."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.B2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A7, chess.Piece(chess.PAWN, chess.BLACK))
        result = classify_position(board)
        assert result.material_signature == "KPP_KP"


# ---------------------------------------------------------------------------
# Material Imbalance tests
# ---------------------------------------------------------------------------


class TestMaterialImbalance:
    def test_starting_position_is_equal(self, starting_board: chess.Board) -> None:
        """Starting position is perfectly equal -> imbalance=0."""
        result = classify_position(starting_board)
        assert result.material_imbalance == 0

    def test_white_up_a_pawn(self) -> None:
        """White up one pawn -> +100 centipawns."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.material_imbalance == 100

    def test_black_up_a_queen(self) -> None:
        """Black up a queen -> -900 centipawns."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        result = classify_position(board)
        assert result.material_imbalance == -900

    def test_equal_material_non_zero_pieces(self) -> None:
        """KR vs KR: equal material -> imbalance=0."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.material_imbalance == 0

    def test_complex_imbalance(self) -> None:
        """White has Q+P (1000), black has 2R (1000) -> imbalance=0."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.H8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.material_imbalance == 0  # 900+100 vs 500+500


# ---------------------------------------------------------------------------
# Tactical Indicator tests
# ---------------------------------------------------------------------------


class TestTacticalIndicators:
    def test_opposite_color_bishops_true(self) -> None:
        """Each side has exactly 1 bishop on different colors -> has_opposite_color_bishops=True."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is True

    def test_same_color_bishops_false(self) -> None:
        """Both bishops on same square color -> has_opposite_color_bishops=False."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.BISHOP, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is False

    def test_no_bishops_no_opposite_color(self) -> None:
        """No bishops at all -> has_opposite_color_bishops=False."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is False

    def test_one_side_no_bishop_no_opposite_color(self) -> None:
        """One side has 0 bishops -> has_opposite_color_bishops=False."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is False

    def test_two_bishops_same_side_no_opposite_color(self) -> None:
        """One side has 2 bishops -> has_opposite_color_bishops=False (not exactly 1)."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is False


# ---------------------------------------------------------------------------
# Return type / dataclass tests
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_position_classification_dataclass(self, starting_board: chess.Board) -> None:
        """classify_position must return a PositionClassification instance."""
        result = classify_position(starting_board)
        assert isinstance(result, PositionClassification)

    def test_all_fields_present(self, starting_board: chess.Board) -> None:
        """All 4 fields of PositionClassification must be present."""
        result = classify_position(starting_board)
        assert hasattr(result, "material_count")
        assert hasattr(result, "material_signature")
        assert hasattr(result, "material_imbalance")
        assert hasattr(result, "has_opposite_color_bishops")

    def test_pure_function_no_side_effects(self, starting_board: chess.Board) -> None:
        """classify_position must not modify the board state."""
        fen_before = starting_board.fen()
        classify_position(starting_board)
        assert starting_board.fen() == fen_before

    def test_classify_position_is_synchronous(self, starting_board: chess.Board) -> None:
        """classify_position must be a regular synchronous function (not a coroutine)."""
        import inspect

        result = classify_position(starting_board)
        assert not inspect.iscoroutine(result)
