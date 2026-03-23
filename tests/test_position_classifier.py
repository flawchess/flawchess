"""Tests for the position_classifier module.

Covers:
- Game phase detection (opening/middlegame/endgame)
- Phase score boundary conditions
- Material signature computation (canonical form, stronger side first)
- Material imbalance computation
- Endgame class assignment (priority order)
- Tactical indicators (bishop pair, opposite-color bishops)
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
# Game Phase tests (PMETA-01, D-01)
# ---------------------------------------------------------------------------


class TestGamePhase:
    def test_starting_position_is_opening(self, starting_board: chess.Board) -> None:
        """Starting position has phase_score=62 (>=50), so classified as opening."""
        result = classify_position(starting_board)
        assert result.game_phase == "opening"

    def test_early_queen_trade_is_middlegame(self) -> None:
        """After both queens are traded, phase_score drops from 62 to 44 (25<=44<50 -> middlegame)."""
        # Both queens off the board: each side has 2N+2B+2R = 22, total = 44
        board = chess.Board()
        board.clear()
        # White: 2 rooks, 2 bishops, 2 knights, 8 pawns + king
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.H1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.B1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.G1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        for file in range(8):
            board.set_piece_at(chess.square(file, 1), chess.Piece(chess.PAWN, chess.WHITE))
        # Black: 2 rooks, 2 bishops, 2 knights, 8 pawns + king
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.H8, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.F8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.B8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.G8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        for file in range(8):
            board.set_piece_at(chess.square(file, 6), chess.Piece(chess.PAWN, chess.BLACK))
        result = classify_position(board)
        assert result.game_phase == "middlegame"

    def test_phase_score_exactly_25_is_middlegame(self) -> None:
        """Phase score exactly 25 is the boundary — must be middlegame (>=25), not endgame."""
        # One side: Q(9)+R(5)+B(3)+N(3)=20, other side: R(5) = total 25
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.B1, chess.Piece(chess.KNIGHT, chess.WHITE))
        # White total: 9+5+3+3 = 20
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        # Black total: 5
        # Combined: 25 -> middlegame
        result = classify_position(board)
        assert result.game_phase == "middlegame"

    def test_phase_score_24_is_endgame(self) -> None:
        """Phase score 24 is just below the threshold, must be endgame."""
        # One side: Q(9)+R(5)+B(3)+N(3)=20, other side: B(3)+N(3)=6... need 24 exactly.
        # White: Q(9)+R(5)+N(3) = 17, Black: R(5)+B(3)-1 -- let's do:
        # White: Q(9)+R(5) = 14, Black: R(5)+B(3)+N(3) = 11... total 25, not 24.
        # White: Q(9)+R(5) = 14, Black: R(5)+B(3) = 8 + N(2)? No, N=3.
        # Try: White: R(5)+B(3)+N(3)=11, Black: R(5)+B(3)+N(3)=11... that's 22. Not 24.
        # White: Q(9)+R(5)=14, Black: R(5)+B(3)+N(1)? No, N=3.
        # White: Q(9)+N(3)+B(3)=15, Black: R(5)+B(3)+N(1)?
        # Actually let's do White: Q(9)+R(5)=14, Black: R(5)+B(3)+N(3)...
        # That's 14+11=25. Need 24.
        # White: R(5)+B(3)+N(3)+B(3)=14, Black: R(5)+B(3)+N(3)-1? No.
        # White: Q(9)+R(5)+N(3)=17, Black: R(5)+B(3)-1? Can't have partial.
        # White: 2N(6)+2B(6)+R(5)=17, Black: R(5)+B(3)-1? Not valid.
        # Simplest: White=12, Black=12 -> 24.  e.g. White: 2R(10)+B(3)-1? no.
        # White: 2N(6)+2B(6)=12, Black: 2N(6)+2B(6)=12, total=24.
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.B1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.G1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        # White: N+N+B+B = 3+3+3+3 = 12
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.B8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.G8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.F8, chess.Piece(chess.BISHOP, chess.BLACK))
        # Black: N+N+B+B = 12
        # Total: 24 -> endgame
        result = classify_position(board)
        assert result.game_phase == "endgame"

    def test_pawns_and_kings_only_is_endgame(self) -> None:
        """All major pieces off, only pawns + kings -> phase_score=0 -> endgame."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.E7, chess.Piece(chess.PAWN, chess.BLACK))
        result = classify_position(board)
        assert result.game_phase == "endgame"

    def test_endgame_class_is_none_for_opening(self, starting_board: chess.Board) -> None:
        """endgame_class must be None for non-endgame positions."""
        result = classify_position(starting_board)
        assert result.endgame_class is None

    def test_endgame_class_is_none_for_middlegame(self) -> None:
        """endgame_class must be None for middlegame positions."""
        # early queen trade board — same as above, phase_score=44
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.H1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.B1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.G1, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A8, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.H8, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.F8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.B8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.G8, chess.Piece(chess.KNIGHT, chess.BLACK))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.endgame_class is None


# ---------------------------------------------------------------------------
# Material Signature tests (PMETA-02, D-02)
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
        # White: K + R + P (stronger: R=500+P=100=600)
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.PAWN, chess.WHITE))
        # Black: K + R (weaker: R=500)
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
        # Create KQ vs KQ position
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.D1, chess.Piece(chess.QUEEN, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        result = classify_position(board)
        # The signature should be canonical — same if we swap sides conceptually
        assert result.material_signature == "KQ_KQ"

    def test_asymmetric_black_stronger(self) -> None:
        """When black has more material, stronger side must still come first in signature."""
        board = chess.Board()
        board.clear()
        # White: K + R
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        # Black: K + Q (stronger: Q=900 > R=500)
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.D8, chess.Piece(chess.QUEEN, chess.BLACK))
        result = classify_position(board)
        # Black is stronger, so black side string should be first
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
# Material Imbalance tests (PMETA-03, D-03)
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
# Endgame Class tests (PMETA-04, D-04)
# ---------------------------------------------------------------------------


class TestEndgameClass:
    def _endgame_board_with_pieces(
        self,
        white_pieces: list[tuple[int, int]],
        black_pieces: list[tuple[int, int]],
    ) -> chess.Board:
        """Build a board with just kings and specified pieces (no queens/rooks unless specified).

        white_pieces / black_pieces: list of (piece_type, square) tuples.
        Kings at E1/E8 are always added automatically.
        """
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        for piece_type, square in white_pieces:
            board.set_piece_at(square, chess.Piece(piece_type, chess.WHITE))
        for piece_type, square in black_pieces:
            board.set_piece_at(square, chess.Piece(piece_type, chess.BLACK))
        return board

    def test_pawn_endgame_class(self) -> None:
        """K+P vs K -> priority 1: kings and pawns only -> 'pawn'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.PAWN, chess.A2)],
            black_pieces=[],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "pawn"

    def test_pawnless_endgame_class(self) -> None:
        """K+R vs K -> priority 2: no pawns, any pieces -> 'pawnless'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.ROOK, chess.A1)],
            black_pieces=[],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "pawnless"

    def test_rook_endgame_class(self) -> None:
        """K+R+P vs K+R -> priority 3: rooks + pawns, no queen/bishop/knight -> 'rook'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.ROOK, chess.A1), (chess.PAWN, chess.A2)],
            black_pieces=[(chess.ROOK, chess.A8)],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "rook"

    def test_minor_piece_endgame_class(self) -> None:
        """K+B+P vs K+N -> priority 4: minor pieces + pawns -> 'minor_piece'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.BISHOP, chess.C1), (chess.PAWN, chess.A2)],
            black_pieces=[(chess.KNIGHT, chess.B8)],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "minor_piece"

    def test_queen_endgame_class(self) -> None:
        """K+Q+P vs K -> priority 5: queens + pawns -> 'queen'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.QUEEN, chess.D1), (chess.PAWN, chess.A2)],
            black_pieces=[],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "queen"

    def test_mixed_endgame_class(self) -> None:
        """K+R+B+P vs K+Q -> priority 6: catch-all mixed -> 'mixed'."""
        board = self._endgame_board_with_pieces(
            white_pieces=[
                (chess.ROOK, chess.A1),
                (chess.BISHOP, chess.C1),
                (chess.PAWN, chess.A2),
            ],
            black_pieces=[(chess.QUEEN, chess.D8)],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "mixed"

    def test_pawnless_priority_over_minor_piece(self) -> None:
        """K+B+N vs K (no pawns) must be 'pawnless' (priority 2 before minor_piece priority 4)."""
        board = self._endgame_board_with_pieces(
            white_pieces=[(chess.BISHOP, chess.C1), (chess.KNIGHT, chess.B1)],
            black_pieces=[],
        )
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "pawnless"

    def test_endgame_class_assigned_in_endgame(self) -> None:
        """endgame_class must be a valid string when game_phase == 'endgame'."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.game_phase == "endgame"
        assert result.endgame_class == "pawnless"


# ---------------------------------------------------------------------------
# Tactical Indicator tests (D-05)
# ---------------------------------------------------------------------------


class TestTacticalIndicators:
    def test_white_bishop_pair(self) -> None:
        """White has 2 bishops -> has_bishop_pair_white=True."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.has_bishop_pair_white is True
        assert result.has_bishop_pair_black is False

    def test_white_single_bishop_no_pair(self) -> None:
        """White has 1 bishop -> has_bishop_pair_white=False."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.has_bishop_pair_white is False

    def test_black_bishop_pair(self) -> None:
        """Black has 2 bishops -> has_bishop_pair_black=True."""
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        board.set_piece_at(chess.F8, chess.Piece(chess.BISHOP, chess.BLACK))
        result = classify_position(board)
        assert result.has_bishop_pair_black is True
        assert result.has_bishop_pair_white is False

    def test_starting_position_bishop_pairs(self, starting_board: chess.Board) -> None:
        """Starting position: both sides have bishop pairs."""
        result = classify_position(starting_board)
        assert result.has_bishop_pair_white is True
        assert result.has_bishop_pair_black is True

    def test_opposite_color_bishops_true(self) -> None:
        """Each side has exactly 1 bishop on different colors -> has_opposite_color_bishops=True.

        C1 is a dark square and C8 is a light square in python-chess's BB_DARK_SQUARES convention.
        """
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        # White bishop on C1 (dark square per BB_DARK_SQUARES)
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        # Black bishop on C8 (light square — opposite color from C1)
        board.set_piece_at(chess.C8, chess.Piece(chess.BISHOP, chess.BLACK))
        result = classify_position(board)
        assert result.has_opposite_color_bishops is True

    def test_same_color_bishops_false(self) -> None:
        """Both bishops on same square color -> has_opposite_color_bishops=False.

        C1 and D8 are both dark squares in python-chess's BB_DARK_SQUARES convention.
        """
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        # White bishop on C1 (dark square)
        board.set_piece_at(chess.C1, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        # Black bishop on D8 (also a dark square — same color as C1)
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
        # Black has no bishop
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
        # White has 2, black has 1 -> not exactly 1 for white -> False
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
        """All 7 fields of PositionClassification must be present."""
        result = classify_position(starting_board)
        assert hasattr(result, "game_phase")
        assert hasattr(result, "material_signature")
        assert hasattr(result, "material_imbalance")
        assert hasattr(result, "endgame_class")
        assert hasattr(result, "has_bishop_pair_white")
        assert hasattr(result, "has_bishop_pair_black")
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
        # If it returned a coroutine, we'd need to await it — just verify no coroutine
        assert not inspect.iscoroutine(result)
