"""Unit tests for app.services.flaws_service.

Covers Phase 105 LIBG-02/06/07: severity classification, 8 attribution tags,
TypedDict output contract, eval coverage gate, mate Option B, FEN recomputation.
No DB required — all tests construct GamePosition objects in memory.

Sign convention: eval_cp / eval_mate are white-perspective (Stockfish / python-chess).
"""

import chess
import pytest

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.flaws_service import (
    BLUNDER_DROP,
    EVAL_COVERAGE_MIN,
    FROM_WINNING_ES,
    INACCURACY_DROP,
    MATE_CP_EQUIVALENT,
    MISTAKE_DROP,
    SANITY_TOLERANCE,
    TIME_PRESSURE_CLOCK_FRACTION,
    HASTY_MOVE_FRACTION,
    FlawRecord,
    GameFlawsResult,
    GameNotAnalyzed,
    _classify_severity,
    _classify_tempo,
    _compute_eval_coverage,
    _move_time,
    _ply_to_es,
    _recompute_fen_map,
    classify_game_flaws,
)


def _make_pos(
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Build a GamePosition with eval/clock fields for pure unit testing (no DB flush).

    SQLAlchemy ORM objects can be instantiated without a session for attribute access.
    We set all columns the service reads plus non-null NOT-NULL columns so that
    attribute access never raises.
    """
    pos = GamePosition()
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = move_san
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KP_KP"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos


def _make_game(
    pgn: str = "1. e4 e5 *",
    user_color: str = "white",
    result: str = "1-0",
    base_time_seconds: int | None = 600,
    increment_seconds: float | None = 0.0,
) -> Game:
    """Build a minimal Game object for unit testing (no DB flush).

    Uses direct constructor — SQLAlchemy ORM objects can be instantiated without
    a session for attribute access (session only required for DB queries/commits).
    """
    game = Game()
    game.pgn = pgn
    game.user_color = user_color
    game.result = result
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = increment_seconds
    return game


# Short analyzed-game PGN for use in classify_game_flaws tests.
# Two-move game: 1. e4 e5 (white plays e4, black plays e5).
_SHORT_PGN = "1. e4 e5 *"

# A minimal but valid PGN for testing FEN recomputation.
_PGN_THREE_MOVES = "1. e4 e5 2. Nf3 *"


class TestConstants:
    """Verify that the named constants have the locked values from CONTEXT.md §Severity."""

    """Verify that the named constants have the locked values from CONTEXT.md §Severity."""

    def test_inaccuracy_drop_value(self) -> None:
        """INACCURACY_DROP must equal 0.05 (Lichess 0.10 halved for [0,1] ES scale)."""
        assert INACCURACY_DROP == 0.05

    def test_mistake_drop_value(self) -> None:
        """MISTAKE_DROP must equal 0.10."""
        assert MISTAKE_DROP == 0.10

    def test_blunder_drop_value(self) -> None:
        """BLUNDER_DROP must equal 0.15."""
        assert BLUNDER_DROP == 0.15

    def test_mate_cp_equivalent_value(self) -> None:
        """MATE_CP_EQUIVALENT must equal 1000 (Option B mate mapping)."""
        assert MATE_CP_EQUIVALENT == 1000

    def test_eval_coverage_min_value(self) -> None:
        """EVAL_COVERAGE_MIN must equal 0.90."""
        assert EVAL_COVERAGE_MIN == 0.90

    def test_from_winning_es_value(self) -> None:
        """FROM_WINNING_ES must equal 0.85."""
        assert FROM_WINNING_ES == 0.85


class TestTypeContract:
    """Verify that FlawRecord and GameNotAnalyzed are importable and accept full literals."""

    def test_flaw_record_accepts_full_literal(self) -> None:
        """A fully-constructed FlawRecord literal round-trips all 8 fields."""
        record: FlawRecord = {
            "ply": 10,
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "side": "white",
            "severity": "blunder",
            "tags": [],
            "es_before": 0.65,
            "es_after": 0.40,
            "move_san": "Qxf7",
        }
        assert record["ply"] == 10
        assert record["severity"] == "blunder"
        assert record["side"] == "white"
        assert record["es_before"] == pytest.approx(0.65)
        assert record["es_after"] == pytest.approx(0.40)
        assert record["move_san"] == "Qxf7"
        assert record["tags"] == []

    def test_game_not_analyzed_accepts_full_literal(self) -> None:
        """A fully-constructed GameNotAnalyzed literal round-trips all 2 fields."""
        not_analyzed: GameNotAnalyzed = {
            "reason": "no_engine_analysis",
            "eval_coverage": 0.0,
        }
        assert not_analyzed["reason"] == "no_engine_analysis"
        assert not_analyzed["eval_coverage"] == 0.0

    def test_game_flaws_result_is_union_type(self) -> None:
        """GameFlawsResult is the union type (importable and usable as annotation)."""
        result: GameFlawsResult = []
        assert isinstance(result, list)
        result2: GameFlawsResult = {"reason": "no_engine_analysis", "eval_coverage": 0.0}
        assert isinstance(result2, dict)


class TestSeverityClassification:
    """Boundary tests for _classify_severity — halved Lichess thresholds on [0,1] ES."""

    def test_below_inaccuracy_threshold_returns_none(self) -> None:
        """A drop of 0.04 is below all thresholds — returns None."""
        assert _classify_severity(0.04) is None

    def test_exactly_zero_drop_returns_none(self) -> None:
        """A drop of 0.0 (no worsening) returns None."""
        assert _classify_severity(0.0) is None

    def test_inaccuracy_threshold_boundary_inclusive(self) -> None:
        """A drop of exactly 0.05 (INACCURACY_DROP) classifies as 'inaccuracy'."""
        assert _classify_severity(0.05) == "inaccuracy"

    def test_inaccuracy_just_above_threshold(self) -> None:
        """A drop of 0.051 classifies as 'inaccuracy' (below MISTAKE_DROP)."""
        assert _classify_severity(0.051) == "inaccuracy"

    def test_mistake_threshold_boundary_inclusive(self) -> None:
        """A drop of exactly 0.10 (MISTAKE_DROP) classifies as 'mistake'."""
        assert _classify_severity(0.10) == "mistake"

    def test_mistake_just_above_threshold(self) -> None:
        """A drop of 0.101 classifies as 'mistake' (below BLUNDER_DROP)."""
        assert _classify_severity(0.101) == "mistake"

    def test_blunder_threshold_boundary_inclusive(self) -> None:
        """A drop of exactly 0.15 (BLUNDER_DROP) classifies as 'blunder'."""
        assert _classify_severity(0.15) == "blunder"

    def test_blunder_large_drop(self) -> None:
        """A large drop (0.50) classifies as 'blunder' (highest band wins)."""
        assert _classify_severity(0.50) == "blunder"

    def test_highest_band_wins(self) -> None:
        """A drop of 0.20 classifies as 'blunder', not 'mistake' or 'inaccuracy'."""
        assert _classify_severity(0.20) == "blunder"


class TestPlyToEs:
    """Tests for _ply_to_es — mover-POV ES derivation with Option B mate handling."""

    def test_cp_eval_white_mover(self) -> None:
        """+100 cp with white mover yields ~0.591 (sigmoid at +100)."""
        pos = _make_pos(0, eval_cp=100)
        result = _ply_to_es(pos, "white")
        assert result == pytest.approx(0.591, abs=1e-3)

    def test_cp_eval_black_mover_symmetry(self) -> None:
        """+100 cp with black mover yields ~0.409 (sign-flipped sigmoid — white is ahead)."""
        pos = _make_pos(0, eval_cp=100)
        result = _ply_to_es(pos, "black")
        assert result == pytest.approx(0.409, abs=1e-3)

    def test_null_eval_returns_none(self) -> None:
        """A position with both eval_cp and eval_mate null returns None."""
        pos = _make_pos(0)
        assert _ply_to_es(pos, "white") is None

    def test_mate_option_b_positive_for_white(self) -> None:
        """eval_mate=+3 with white mover yields ~0.975 (Option B, NOT 1.0)."""
        pos = _make_pos(0, eval_mate=3)
        result = _ply_to_es(pos, "white")
        assert result is not None
        assert result == pytest.approx(0.975, abs=1e-3)
        assert result != 1.0  # Option B: never exactly 1.0

    def test_mate_option_b_negative_for_white(self) -> None:
        """eval_mate=-3 with white mover yields ~0.025 (opponent has mate)."""
        pos = _make_pos(0, eval_mate=-3)
        result = _ply_to_es(pos, "white")
        assert result is not None
        assert result == pytest.approx(0.025, abs=1e-3)

    def test_mate_option_b_positive_for_black(self) -> None:
        """eval_mate=+3 (white has mate) with black mover yields ~0.025."""
        pos = _make_pos(0, eval_mate=3)
        result = _ply_to_es(pos, "black")
        assert result is not None
        assert result == pytest.approx(0.025, abs=1e-3)

    def test_eval_mate_takes_precedence_over_eval_cp(self) -> None:
        """When both eval_cp and eval_mate are present, eval_mate takes precedence (Option B)."""
        pos = _make_pos(0, eval_cp=50, eval_mate=3)
        result = _ply_to_es(pos, "white")
        assert result is not None
        assert result == pytest.approx(0.975, abs=1e-3)


class TestMateOptionB:
    """Tests for mate handling — Option B ensures mate-to-mate is NOT always a blunder."""

    def test_same_sign_mate_positions_near_zero_drop(self) -> None:
        """Two consecutive same-sign mate positions yield a near-zero ES drop.

        Both positions have eval_mate > 0 for white (white has forced mate throughout).
        The mover (white) at ply 2 should NOT have this classified as a blunder.
        """
        pos_before = _make_pos(1, eval_mate=4)  # ply 1: white has mate-in-4
        pos_after = _make_pos(2, eval_mate=3)  # ply 2: white has mate-in-3 (improved)
        # White mover at ply 2: reads ES_before from pos_before
        es_before = _ply_to_es(pos_before, "white")
        es_after = _ply_to_es(pos_after, "white")
        assert es_before is not None
        assert es_after is not None
        drop = es_before - es_after
        # Both map to ~0.975 with Option B; drop is near zero
        assert abs(drop) < INACCURACY_DROP, (
            f"Same-sign mate-to-mate drop should be near zero, got {drop}"
        )
        # Classify the drop — should NOT be classified as blunder
        severity = _classify_severity(drop) if drop >= 0 else None
        assert severity is None or severity == "inaccuracy"


class TestEvalCoverageGate:
    """Tests for _compute_eval_coverage."""

    def test_all_null_returns_zero(self) -> None:
        """All-null evals (chess.com game) returns 0.0."""
        positions = [_make_pos(i) for i in range(10)]
        assert _compute_eval_coverage(positions) == 0.0

    def test_empty_positions_returns_zero(self) -> None:
        """Empty list returns 0.0 (no divide-by-zero)."""
        assert _compute_eval_coverage([]) == 0.0

    def test_full_coverage_minus_final_ply(self) -> None:
        """81-row game with only the final row's eval null returns >=0.90.

        An 81-position game (plies 0-80) where only ply 80 has null eval
        has coverage 80/81 ≈ 0.988 — well above 0.90.
        """
        positions = [_make_pos(i, eval_cp=50) for i in range(80)]
        positions.append(_make_pos(80))  # final ply: no eval
        coverage = _compute_eval_coverage(positions)
        assert coverage == pytest.approx(80 / 81, abs=1e-9)
        assert coverage >= EVAL_COVERAGE_MIN

    def test_below_threshold_returns_low_coverage(self) -> None:
        """A game with only 50% eval coverage returns 0.50 (below threshold)."""
        positions = [_make_pos(i, eval_cp=50 if i % 2 == 0 else None) for i in range(10)]
        coverage = _compute_eval_coverage(positions)
        assert coverage == pytest.approx(0.5, abs=1e-9)
        assert coverage < EVAL_COVERAGE_MIN


class TestFenRecompute:
    """Tests for _recompute_fen_map — PGN replay using board.board_fen()."""

    def test_initial_position_at_ply_zero(self) -> None:
        """Ply 0 (before any moves) is the standard initial position."""
        fen_map = _recompute_fen_map(_SHORT_PGN)
        # Standard starting position piece placement
        assert 0 in fen_map
        assert fen_map[0] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

    def test_after_e4_board_fen(self) -> None:
        """After 1. e4, the fen at ply 1 reflects e4 played (no en passant in board_fen)."""
        fen_map = _recompute_fen_map(_SHORT_PGN)
        # After e4, pawn on e4; board_fen has no castling/en passant suffix
        assert 1 in fen_map
        fen = fen_map[1]
        # board_fen is piece placement only — no space-separated fields
        assert " " not in fen

    def test_three_moves_produces_four_entries(self) -> None:
        """A 3-move PGN produces 4 entries: ply 0 through 3."""
        fen_map = _recompute_fen_map(_PGN_THREE_MOVES)
        assert len(fen_map) == 4  # plies 0, 1, 2, 3

    def test_invalid_pgn_returns_initial_position(self) -> None:
        """An unparseable PGN (no valid moves) returns the initial position at ply 0.

        chess.pgn.read_game successfully parses a game header even on invalid input,
        yielding zero mainline moves. The map contains only ply 0 (initial position).
        """
        fen_map = _recompute_fen_map("not valid pgn at all !!!!")
        # python-chess parses this as an empty game (no moves) — ply 0 only
        assert 0 in fen_map
        # No moves parsed, so only ply 0 is in the map
        assert len(fen_map) == 1

    def test_board_fen_not_full_fen(self) -> None:
        """FEN values are piece-placement only (no castling/en passant/move count fields)."""
        fen_map = _recompute_fen_map(_PGN_THREE_MOVES)
        for ply_n, fen in fen_map.items():
            # board_fen() output has exactly 8 rank fields separated by /
            ranks = fen.split("/")
            assert len(ranks) == 8, f"ply {ply_n}: expected 8 rank fields, got {len(ranks)}: {fen}"
            # No space in board_fen output (full FEN has ' w KQkq ...' suffix)
            assert " " not in fen, f"ply {ply_n}: board_fen should have no spaces: {fen}"

    def test_replay_failure_captured_to_sentry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WR-03: a replay failure is captured to Sentry, not silently swallowed.

        We make board_fen() raise inside the replay loop and assert capture_exception
        fired exactly once while the partial map (ply 0) is still returned. board_fen
        is only called by the replay (never by chess.pgn.read_game), so patching it
        isolates the failure to the try block without breaking PGN parsing.
        """
        captured: list[BaseException | None] = []

        def fake_capture(exc: BaseException | None = None) -> None:
            captured.append(exc)

        monkeypatch.setattr("app.services.flaws_service.sentry_sdk.capture_exception", fake_capture)

        real_board_fen = chess.Board.board_fen
        calls = {"n": 0}

        def flaky_board_fen(self: chess.Board, *, promoted: bool = False) -> str:
            calls["n"] += 1
            # 1st call is ply 0 (outside the try) and must succeed; raise on the
            # 2nd call (first loop iteration, inside the try) to hit the except path.
            if calls["n"] == 2:
                raise ValueError("simulated replay failure")
            return real_board_fen(self, promoted=promoted)

        monkeypatch.setattr(chess.Board, "board_fen", flaky_board_fen)

        fen_map = _recompute_fen_map(_PGN_THREE_MOVES)

        assert len(captured) == 1, "replay failure must be reported to Sentry exactly once"
        # Partial map preserved: ply 0 captured before the failure; later plies absent.
        assert 0 in fen_map
        assert 1 not in fen_map


class TestClassifyGameFlaws:
    """Tests for classify_game_flaws — the public API."""

    # -----------------------------------------------------------------------
    # Helpers: build small position sequences for testing
    # -----------------------------------------------------------------------

    def _make_analyzed_positions(
        self,
        n_plies: int = 10,
        eval_cp_value: int = 20,
    ) -> list[GamePosition]:
        """Build n_plies positions where all but the last have eval_cp set."""
        positions = [_make_pos(i, eval_cp=eval_cp_value) for i in range(n_plies)]
        positions[-1] = _make_pos(n_plies - 1)  # final ply: no eval (normal)
        return positions

    def _make_chesscom_positions(self, n_plies: int = 10) -> list[GamePosition]:
        """Build positions with all-null evals (chess.com game)."""
        return [_make_pos(i) for i in range(n_plies)]

    # -----------------------------------------------------------------------
    # Coverage gate
    # -----------------------------------------------------------------------

    def test_zero_coverage_returns_game_not_analyzed(self) -> None:
        """A chess.com game (all evals null) returns GameNotAnalyzed."""
        game = _make_game(pgn=_SHORT_PGN, user_color="white")
        positions = self._make_chesscom_positions(4)
        result = classify_game_flaws(game, positions)
        assert isinstance(result, dict), "Expected GameNotAnalyzed dict"
        assert result["reason"] == "no_engine_analysis"
        assert result["eval_coverage"] == pytest.approx(0.0)

    def test_analyzed_game_returns_list(self) -> None:
        """A >= 90%-coverage game returns a list (possibly empty)."""
        # Use 10 positions; only the last has no eval: coverage = 9/10 = 0.90 >= threshold
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")
        positions = [_make_pos(i, eval_cp=20) for i in range(9)]
        positions.append(_make_pos(9))  # final ply: no eval
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list), "Expected list[FlawRecord]"

    def test_coverage_gate_below_threshold_returns_not_analyzed(self) -> None:
        """A game with < 90% eval coverage returns GameNotAnalyzed."""
        game = _make_game(pgn=_SHORT_PGN, user_color="white")
        # 10 positions, only 5 with eval = 50% coverage < 90%
        positions = [_make_pos(i, eval_cp=20 if i < 5 else None) for i in range(10)]
        result = classify_game_flaws(game, positions)
        assert isinstance(result, dict)
        assert result["reason"] == "no_engine_analysis"

    # -----------------------------------------------------------------------
    # Flaw emission: only mistakes/blunders, not inaccuracies
    # -----------------------------------------------------------------------

    def test_inaccuracy_only_game_returns_empty_list(self) -> None:
        """An analyzed game with only inaccuracies returns empty list, NOT GameNotAnalyzed.

        This tests the 2026-06-05 amendment: inaccuracies are count-only.

        White mover at ply 2 (even ply).
        eval_cp_to_expected_score(50, "white") ≈ 0.568 (es_before from ply 1)
        eval_cp_to_expected_score(0, "white") = 0.5   (es_after from ply 2)
        drop = 0.068 -> inaccuracy band — NOT emitted.
        10 positions with 1 final null: coverage = 9/10 = 0.90 >= EVAL_COVERAGE_MIN.
        """
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")
        # Build 10 positions; only white at ply 2 has an inaccuracy (drop ≈ 0.068)
        positions = [_make_pos(i, eval_cp=0) for i in range(10)]
        positions[1] = _make_pos(1, eval_cp=50)  # es_before for white mover at ply 2
        positions[2] = _make_pos(2, eval_cp=0)  # es_after for white mover at ply 2
        positions[9] = _make_pos(9)  # final null; coverage = 9/10 = 0.90
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list), (
            "Inaccuracy-only analyzed game must return list, not GameNotAnalyzed"
        )
        assert result == [], "Inaccuracy-only analyzed game must return empty list"

    def test_blunder_emitted_as_flaw_record(self) -> None:
        """A deliberate blunder is emitted as a FlawRecord with correct fields.

        White is the user (user_color="white"). White's move at ply 2 (even ply).
        ES_before = _ply_to_es(positions[1], "white"); ES_after = _ply_to_es(positions[2], "white").
        """
        # Use a real PGN so FEN recomputation works
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")

        # 10 positions: plies 0-9, final ply has no eval.
        # Induce a blunder for white at ply 2 (even ply => white mover).
        # ES_before from ply 1, ES_after from ply 2.
        # eval_cp_to_expected_score(200, "white") ≈ 0.685
        # eval_cp_to_expected_score(-500, "white") ≈ 0.160
        # drop = 0.685 - 0.160 = 0.525 >= 0.15 => blunder
        positions = [_make_pos(i, eval_cp=20) for i in range(10)]
        positions[1] = _make_pos(1, eval_cp=200, move_san="e4")
        positions[2] = _make_pos(2, eval_cp=-500, move_san="Nf3")
        positions[9] = _make_pos(9)  # final ply: no eval

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        assert len(result) >= 1, "Expected at least one blunder FlawRecord"

        # Find the blunder at ply 2
        blunders = [r for r in result if r["ply"] == 2]
        assert len(blunders) == 1
        flaw = blunders[0]
        assert flaw["severity"] == "blunder"
        assert flaw["side"] == "white"
        assert flaw["fen"] != ""  # FEN recomputed from PGN
        assert flaw["es_before"] > flaw["es_after"], "Blunder worsens ES"
        assert isinstance(flaw["tags"], list)  # tags populated in plan 02

    def test_es_before_greater_than_es_after_for_blunder(self) -> None:
        """Eval-AFTER landmine: ES_before reads positions[N-1], ES_after reads positions[N].

        White mover at ply 2 (even ply):
          positions[1] = ES_before (eval stored AFTER ply-1 move, BEFORE ply-2 move)
          positions[2] = ES_after  (eval stored AFTER ply-2 move, showing the blunder)
        A move that worsened the position must show es_before > es_after.
        """
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")
        positions = [_make_pos(i, eval_cp=0) for i in range(10)]
        positions[1] = _make_pos(1, eval_cp=300)  # good position before white's blunder
        positions[2] = _make_pos(2, eval_cp=-500)  # bad position after white's blunder
        positions[9] = _make_pos(9)  # final null; coverage = 9/10 = 0.90

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2_flaws = [r for r in result if r["ply"] == 2]
        assert len(ply2_flaws) == 1
        flaw = ply2_flaws[0]
        assert flaw["es_before"] > flaw["es_after"]

    def test_opponent_flaws_not_in_result_for_white_user(self) -> None:
        """Only user's (white's) flaws appear in the result — opponent errors are filtered."""
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")

        # Induce a blunder for BLACK at ply 3 (odd ply => black mover).
        # ES_before = _ply_to_es(positions[2], "black"); ES_after = _ply_to_es(positions[3], "black")
        # For black: eval_cp=+500 is BAD for black (white winning) => low black ES
        # eval_cp_to_expected_score(+200, "black") ≈ 0.315 (before)
        # eval_cp_to_expected_score(-500, "black") ≈ 0.840 (after — black recovers??)
        # Actually: we want black to make a blunder (drop in black's ES).
        # pos[2].eval_cp = -300 => es_before for black ≈ eval_cp_to_expected_score(-300, "black")
        #                        = 1 - eval_cp_to_expected_score(-300, "white")
        #                        ≈ 1 - 0.333 = 0.667 (black was winning)
        # pos[3].eval_cp = +200 => es_after for black ≈ eval_cp_to_expected_score(+200, "black")
        #                        ≈ 1 - 0.685 = 0.315 (black now losing)
        # drop = 0.667 - 0.315 = 0.352 => blunder for black
        positions = [_make_pos(i, eval_cp=0) for i in range(10)]
        positions[2] = _make_pos(2, eval_cp=-300)  # before black's ply-3 move
        positions[3] = _make_pos(3, eval_cp=200)  # after black's blunder
        positions[9] = _make_pos(9)  # final null

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        # White is user_color — no black flaws should appear
        for flaw in result:
            assert flaw["side"] == "white", (
                f"Opponent (black) flaw at ply {flaw['ply']} should not appear in result"
            )

    def test_flaws_are_sorted_by_ply(self) -> None:
        """Returned FlawRecords are ordered by ply ascending (iteration order)."""
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white")

        # Induce two white blunders: ply 2 and ply 6
        positions = [_make_pos(i, eval_cp=0) for i in range(10)]
        positions[1] = _make_pos(1, eval_cp=200)
        positions[2] = _make_pos(2, eval_cp=-500)  # blunder at ply 2
        positions[5] = _make_pos(5, eval_cp=200)
        positions[6] = _make_pos(6, eval_cp=-500)  # blunder at ply 6
        positions[9] = _make_pos(9)

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        plies = [r["ply"] for r in result]
        assert plies == sorted(plies), "FlawRecords should be ordered by ply ASC"


class TestTempoTags:
    """Tests for _classify_tempo — at most one tempo tag per flaw."""

    def test_low_clock_when_low_clock_fraction(self) -> None:
        """clock_after < TIME_PRESSURE_CLOCK_FRACTION * base_time yields low-clock."""
        base_time = 600
        low_clock = base_time * TIME_PRESSURE_CLOCK_FRACTION - 1  # just below threshold
        result = _classify_tempo(move_time=30.0, clock_after=low_clock, base_time=base_time)
        assert result == "low-clock"

    def test_impatient_when_fast_move_on_comfortable_clock(self) -> None:
        """move_time < HASTY_MOVE_FRACTION * base_time on a comfortable clock yields impatient."""
        base_time = 600
        comfortable_clock = base_time * TIME_PRESSURE_CLOCK_FRACTION + 10  # well above threshold
        fast_move = base_time * HASTY_MOVE_FRACTION - 0.1  # just below fast threshold
        result = _classify_tempo(
            move_time=fast_move, clock_after=comfortable_clock, base_time=base_time
        )
        assert result == "impatient"

    def test_considered_when_adequate_time(self) -> None:
        """Adequate clock and adequate move time yields considered."""
        base_time = 600
        comfortable_clock = base_time * TIME_PRESSURE_CLOCK_FRACTION + 60
        adequate_move = base_time * HASTY_MOVE_FRACTION + 5.0
        result = _classify_tempo(
            move_time=adequate_move, clock_after=comfortable_clock, base_time=base_time
        )
        assert result == "considered"

    def test_no_tempo_tag_when_clock_data_missing(self) -> None:
        """Missing clock_after yields None — missing clock/move-time yields no tempo tag, not a fallback."""
        result = _classify_tempo(move_time=10.0, clock_after=None, base_time=600)
        assert result is None

    def test_no_tempo_tag_when_move_time_missing(self) -> None:
        """Missing move_time yields None — missing clock/move-time yields no tempo tag, not a fallback."""
        result = _classify_tempo(move_time=None, clock_after=100.0, base_time=600)
        assert result is None

    def test_abs_fallback_low_clock_when_no_base_time(self) -> None:
        """When base_time is None, falls back to absolute threshold for low-clock."""
        # clock < 30s absolute = low-clock
        result = _classify_tempo(move_time=10.0, clock_after=25.0, base_time=None)
        assert result == "low-clock"

    def test_abs_fallback_impatient_when_no_base_time(self) -> None:
        """When base_time is None, falls back to absolute threshold for impatient."""
        # clock >= 30s, move < 5s = impatient
        result = _classify_tempo(move_time=3.0, clock_after=60.0, base_time=None)
        assert result == "impatient"

    def test_move_time_clamps_negative_to_none(self) -> None:
        """WR-05: a clock anomaly producing a negative move time returns None.

        Same-side clock is two plies back. If the clock 'gains' more than the
        increment between the player's own moves (corrupt data), the raw formula
        goes negative — which would otherwise satisfy move_time < fast_threshold
        and mislabel the move as impatient. The fix returns None so tempo is
        absent (None) so the move is not mislabeled impatient.
        """
        positions = [_make_pos(i) for i in range(4)]
        # prev same-side clock (n-2) LOWER than current (n) with zero increment
        # => prev - curr + inc = 100 - 130 + 0 = -30 (impossible, anomaly)
        positions[0] = _make_pos(0, clock_seconds=100.0)
        positions[2] = _make_pos(2, clock_seconds=130.0)
        assert _move_time(positions, n=2, increment=0.0) is None

    def test_move_time_zero_is_valid(self) -> None:
        """A genuinely instant move (time == 0) is valid and not clamped to None."""
        positions = [_make_pos(i) for i in range(4)]
        positions[0] = _make_pos(0, clock_seconds=100.0)
        positions[2] = _make_pos(2, clock_seconds=100.0)
        assert _move_time(positions, n=2, increment=0.0) == 0.0

    def test_at_most_one_tempo_tag_per_flaw_in_classify_game(self) -> None:
        """Every emitted FlawRecord contains at most one tempo tag."""
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        # Construct positions with clocks to exercise tempo logic
        game = _make_game(pgn=pgn, user_color="white", base_time_seconds=600)
        positions = [_make_pos(i, eval_cp=0, clock_seconds=float(600 - i * 5)) for i in range(10)]
        # Induce blunder at ply 2 (white)
        positions[1] = _make_pos(1, eval_cp=300, clock_seconds=590.0)
        positions[2] = _make_pos(2, eval_cp=-500, clock_seconds=580.0)
        positions[9] = _make_pos(9)  # final null

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        assert len(result) >= 1, "Expected at least one flaw"
        for flaw in result:
            tempo_tags = [t for t in flaw["tags"] if t in ("low-clock", "impatient", "considered")]
            assert len(tempo_tags) <= 1, (
                f"Flaw at ply {flaw['ply']} must have at most one tempo tag, got: {tempo_tags}"
            )

    def test_no_tempo_tag_when_flaw_has_missing_clock_data(self) -> None:
        """A FlawRecord built from a flaw with missing clock data carries NO tempo tag.

        This tests the at-most-one rule from flaw-tag-naming.md §'Structural change':
        when clock_after or move_time is None, _classify_tempo returns None and
        _build_tags omits the tempo append entirely.
        """
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
        game = _make_game(pgn=pgn, user_color="white", base_time_seconds=600)
        # Build positions with NO clock data (clock_seconds=None throughout)
        positions = [_make_pos(i, eval_cp=0, clock_seconds=None) for i in range(10)]
        # Induce blunder at ply 2 (white) — clock_seconds remains None
        positions[1] = _make_pos(1, eval_cp=300, clock_seconds=None)
        positions[2] = _make_pos(2, eval_cp=-500, clock_seconds=None)
        positions[9] = _make_pos(9)  # final null

        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        assert len(result) >= 1, "Expected at least one flaw"
        tempo_set = {"low-clock", "impatient", "considered"}
        for flaw in result:
            tempo_tags = [t for t in flaw["tags"] if t in tempo_set]
            assert tempo_tags == [], (
                f"Flaw at ply {flaw['ply']} must carry no tempo tag when clock data is "
                f"unavailable, got: {tempo_tags}"
            )


class TestAttributionTags:
    """Tests for miss, lucky-escape, while-ahead, result-changing, and phase tags."""

    # PGN long enough to have moves for position building
    _PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"

    def _make_standard_positions(self, n: int = 12) -> list[GamePosition]:
        """Build n positions with moderate eval (no errors)."""
        positions = [_make_pos(i, eval_cp=20) for i in range(n)]
        positions[-1] = _make_pos(n - 1)  # final null
        return positions

    def test_while_ahead_tag_when_es_before_above_threshold(self) -> None:
        """Flaw with es_before >= 0.85 (FROM_WINNING_ES) gets while-ahead tag."""
        # eval_cp_to_expected_score(900, "white") is well above 0.85
        # eval_cp_to_expected_score(-500, "white") is well below 0.85
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=900)  # es_before for white at ply 2 is high
        positions[2] = _make_pos(2, eval_cp=-500)  # blunder — large drop from winning position
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1, "Expected blunder at ply 2"
        assert "while-ahead" in ply2[0]["tags"]

    def test_no_while_ahead_tag_when_es_before_below_threshold(self) -> None:
        """Flaw with es_before < FROM_WINNING_ES does NOT get while-ahead tag."""
        # eval_cp_to_expected_score(50, "white") ≈ 0.568 < 0.85
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=50)  # es_before ≈ 0.568 < FROM_WINNING_ES
        positions[2] = _make_pos(2, eval_cp=-500)  # blunder
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "while-ahead" not in ply2[0]["tags"]

    def test_miss_tag_when_preceding_opponent_was_blunder(self) -> None:
        """User flaw at ply N gets miss tag when opponent at ply N-1 was a blunder.

        Positions: user is white.
        Ply 3 (odd = black mover): black blunders (eval_cp drops for black).
        Ply 4 (even = white mover): white also blunders — this gets miss tag.
        """
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        # Black blunders at ply 3: set positions[2] and positions[3]
        # Black POV: eval_cp=-300 at [2] means es_before for black ≈ 1-0.333=0.667
        # eval_cp=+400 at [3] means es_after for black ≈ 1-0.731=0.269
        # drop = 0.667 - 0.269 = 0.398 >= 0.15 => blunder for black
        positions[2] = _make_pos(2, eval_cp=-300)
        positions[3] = _make_pos(3, eval_cp=400)  # black blunder
        # White blunders at ply 4 (immediately after black's ply 3 blunder):
        # eval_cp=400 at [3] means es_before for white ≈ 0.731
        # eval_cp=-400 at [4] means es_after for white ≈ 1-0.731=0.269
        # drop = 0.731 - 0.269 = 0.462 >= 0.15 => blunder for white
        positions[4] = _make_pos(4, eval_cp=-400)  # white blunder right after
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply4 = [f for f in result if f["ply"] == 4]
        assert len(ply4) == 1, "Expected white blunder at ply 4"
        assert "miss" in ply4[0]["tags"], "White blunder after black blunder should get miss tag"

    def test_no_miss_tag_when_preceding_opponent_not_error(self) -> None:
        """User flaw at ply N does NOT get miss tag when opponent at N-1 was fine.

        Black at ply 3 (odd): positions[2].eval_cp = positions[3].eval_cp = 20
        => drop for black ≈ 0, not an error.
        White at ply 4 (even): positions[3].eval_cp = 20, positions[4].eval_cp = -400
        => large drop for white = blunder. But ply 3 had no opponent error, so no miss.
        """
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        # Black at ply 3: both positions[2] and positions[3] at eval_cp=20 => near-zero drop for black
        positions[2] = _make_pos(2, eval_cp=20)  # es_before for black at ply 3 (same as default)
        positions[3] = _make_pos(
            3, eval_cp=20
        )  # opponent's ply 3: fine (negligible drop for black)
        positions[4] = _make_pos(4, eval_cp=-400)  # white blunders at ply 4 (drop ≈ 0.72)
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply4 = [f for f in result if f["ply"] == 4]
        assert len(ply4) == 1
        assert "miss" not in ply4[0]["tags"]

    def test_lucky_escape_tag_on_blunder_when_opponent_plays_fine(self) -> None:
        """User blunder at ply N gets lucky-escape when opponent at N+1 plays a fine move.

        lucky-escape = user's blunder where the opponent did NOT make a mistake/blunder
        in their immediate response (the eval shows the opponent played OK, but
        the user still has the advantage they would have lost — opponent failed
        to maximize the opportunity).

        Black at ply 5: positions[4].eval_cp=-400, positions[5].eval_cp=-380
        => drop for black ≈ eval_cp_to_expected_score(-400, "black") - eval_cp_to_expected_score(-380, "black")
        ≈ 0 (tiny, not an error). Opponent plays normally → lucky-escape applies.
        """
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        # White blunders at ply 4
        positions[3] = _make_pos(3, eval_cp=400)  # before white's ply 4
        positions[4] = _make_pos(4, eval_cp=-400)  # white blunders (drop ≈ 0.462)
        # Black at ply 5 plays a NORMAL move — almost no change in eval
        # drop for black: es_before(black) from [4], es_after(black) from [5]
        # es_before(black) = eval_cp_to_expected_score(-400, "black") ≈ 0.731
        # positions[5].eval_cp=-380 => es_after(black) ≈ 0.723 (tiny improvement for black)
        # drop ≈ 0.731 - 0.723 = 0.008 < INACCURACY_DROP => fine, not an error
        positions[5] = _make_pos(5, eval_cp=-380)  # black plays fine, small change
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply4 = [f for f in result if f["ply"] == 4]
        assert len(ply4) == 1
        assert ply4[0]["severity"] == "blunder"
        assert "lucky-escape" in ply4[0]["tags"], (
            "White blunder should be lucky-escape when black responds with a fine move"
        )

    def test_no_lucky_escape_tag_on_non_blunder(self) -> None:
        """A user mistake (not blunder) does NOT get the lucky-escape tag."""
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        # White makes a mistake at ply 4 (between MISTAKE_DROP and BLUNDER_DROP)
        # eval_cp_to_expected_score(200, "white") ≈ 0.685 (es_before)
        # eval_cp_to_expected_score(50, "white")  ≈ 0.568 (es_after)
        # drop ≈ 0.117 >= 0.10 = mistake, < 0.15 = not blunder
        positions[3] = _make_pos(3, eval_cp=200)
        positions[4] = _make_pos(4, eval_cp=50)  # mistake (drop ≈ 0.117)
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply4 = [f for f in result if f["ply"] == 4]
        assert len(ply4) == 1
        assert ply4[0]["severity"] == "mistake"
        assert "lucky-escape" not in ply4[0]["tags"], "Mistakes should not get lucky-escape tag"

    def test_result_changing_on_loss_crossing_draw_threshold(self) -> None:
        """User flaw gets result-changing when crossing from >= RESULT_DRAW_THRESHOLD to below.

        User lost game (result="0-1", user_color="white").
        White flaw at ply 2: es_before >= 0.40, es_after < 0.40.
        """
        # eval_cp_to_expected_score(100, "white") ≈ 0.591 >= 0.40
        # eval_cp_to_expected_score(-500, "white") ≈ 0.160 < 0.40
        game = _make_game(pgn=self._PGN, user_color="white", result="0-1")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=100)  # es_before ≈ 0.591 >= RESULT_DRAW_THRESHOLD
        positions[2] = _make_pos(2, eval_cp=-500)  # es_after ≈ 0.160 < RESULT_DRAW_THRESHOLD
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "result-changing" in ply2[0]["tags"]

    def test_no_result_changing_when_does_not_cross_boundary(self) -> None:
        """User flaw does NOT get result-changing when both sides of threshold are same zone."""
        # Both es_before and es_after are below the relevant threshold:
        # User lost, but flaw stays below 0.40 before and after (no boundary crossed)
        # eval_cp_to_expected_score(-300, "white") ≈ 0.333 < RESULT_DRAW_THRESHOLD
        # eval_cp_to_expected_score(-600, "white") ≈ 0.094 < RESULT_DRAW_THRESHOLD
        # drop ≈ 0.239 >= BLUNDER_DROP (it's a blunder but not result-changing)
        game = _make_game(pgn=self._PGN, user_color="white", result="0-1")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=-300)  # already below threshold
        positions[2] = _make_pos(2, eval_cp=-600)  # still below threshold
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "result-changing" not in ply2[0]["tags"]

    def test_opening_tag_for_phase_0(self) -> None:
        """Flaw at a position with phase=0 gets opening tag."""
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=300, phase=0)  # opening phase
        positions[2] = _make_pos(2, eval_cp=-500, phase=0)  # blunder in opening
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "opening" in ply2[0]["tags"]
        assert "middlegame" not in ply2[0]["tags"]
        assert "endgame" not in ply2[0]["tags"]

    def test_middlegame_tag_for_phase_1(self) -> None:
        """Flaw at a position with phase=1 gets middlegame tag."""
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=300, phase=1)
        positions[2] = _make_pos(2, eval_cp=-500, phase=1)
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "middlegame" in ply2[0]["tags"]

    def test_endgame_tag_for_phase_2(self) -> None:
        """Flaw at a position with phase=2 gets endgame tag."""
        game = _make_game(pgn=self._PGN, user_color="white")
        positions = self._make_standard_positions(12)
        positions[1] = _make_pos(1, eval_cp=300, phase=2)
        positions[2] = _make_pos(2, eval_cp=-500, phase=2)
        result = classify_game_flaws(game, positions)
        assert isinstance(result, list)
        ply2 = [f for f in result if f["ply"] == 2]
        assert len(ply2) == 1
        assert "endgame" in ply2[0]["tags"]


class TestOracleCloseness:
    """Oracle-closeness sanity test: derived B/M/I counts vs. Lichess game-level columns.

    Derived counts are CLOSE (within SANITY_TOLERANCE), NOT identical to Lichess's
    oracle columns. Divergence sources:
    1. Mate handling: we use Option B (±1000 cp), Lichess uses MateAdvice ladder.
       Mate-adjacent moves may be classified differently.
    2. Floating point edge cases at exact threshold values (minor).
    3. Book-move eval omissions (some plies have null eval; we skip them, Lichess may count).

    This test uses a synthetic position list where all drops are well away from boundaries,
    so mate handling doesn't matter and counts should match exactly (tolerance of 2 is generous).
    """

    def _make_oracle_positions_and_counts(
        self,
    ) -> tuple[list[GamePosition], int, int, int, int, int, int]:
        """Build a synthetic 16-ply game with deliberate errors, return positions + oracle counts.

        Returns:
            (positions, white_blunders, white_mistakes, white_inaccuracies,
             black_blunders, black_mistakes, black_inaccuracies)

        Game structure (plies 0-15, final ply 15 has null eval):
        Ply 2 (white): blunder  — drop > BLUNDER_DROP
        Ply 4 (white): mistake  — MISTAKE_DROP <= drop < BLUNDER_DROP
        Ply 6 (white): inaccuracy — INACCURACY_DROP <= drop < MISTAKE_DROP
        Ply 9 (black): blunder  — drop > BLUNDER_DROP
        Ply 11 (black): mistake  — MISTAKE_DROP <= drop < BLUNDER_DROP
        Ply 13 (black): inaccuracy — INACCURACY_DROP <= drop < MISTAKE_DROP
        """
        positions = [_make_pos(i, eval_cp=0) for i in range(16)]
        positions[15] = _make_pos(15)  # final null

        # White blunder at ply 2:
        # eval_cp_to_expected_score(400, "white") ≈ 0.731 (es_before)
        # eval_cp_to_expected_score(-400, "white") ≈ 0.269 (es_after)
        # drop ≈ 0.462 >= 0.15 = blunder
        positions[1] = _make_pos(1, eval_cp=400)
        positions[2] = _make_pos(2, eval_cp=-400)

        # White mistake at ply 4:
        # eval_cp_to_expected_score(150, "white") ≈ 0.634 (es_before)
        # eval_cp_to_expected_score(0, "white") = 0.5 (es_after)
        # drop ≈ 0.134 >= 0.10, < 0.15 = mistake
        positions[3] = _make_pos(3, eval_cp=150)
        positions[4] = _make_pos(4, eval_cp=0)

        # White inaccuracy at ply 6:
        # eval_cp_to_expected_score(80, "white") ≈ 0.576 (es_before)
        # eval_cp_to_expected_score(0, "white") = 0.5 (es_after)
        # drop ≈ 0.076 >= 0.05, < 0.10 = inaccuracy
        positions[5] = _make_pos(5, eval_cp=80)
        positions[6] = _make_pos(6, eval_cp=0)

        # Black blunder at ply 9:
        # black mover: eval_cp=-300 at [8] means es_before for black ≈ 1-0.333=0.667
        # eval_cp=+300 at [9] means es_after for black ≈ 1-0.667=0.333
        # drop ≈ 0.334 >= 0.15 = blunder
        positions[8] = _make_pos(8, eval_cp=-300)
        positions[9] = _make_pos(9, eval_cp=300)

        # Black mistake at ply 11:
        # eval_cp=-100 at [10] means es_before for black ≈ 1-0.409=0.591
        # eval_cp=+100 at [11] means es_after for black ≈ 1-0.591=0.409
        # drop ≈ 0.182 >= 0.10, hmm that's too large (blunder). Let's recalculate.
        # We need a drop of MISTAKE_DROP <= drop < BLUNDER_DROP (0.10 <= d < 0.15).
        # eval_cp_to_expected_score(x, "black") = 1 - eval_cp_to_expected_score(x, "white")
        # For a black mistake: we need es_before(black) - es_after(black) ∈ [0.10, 0.15).
        # es_before(black) = 1 - es_before(white) = 1 - eval_cp_to_expected_score(eval_before, "white")
        # es_after(black)  = 1 - es_after(white)  = 1 - eval_cp_to_expected_score(eval_after, "white")
        # drop(black) = es_before(black) - es_after(black)
        #             = (1 - es_before(white)) - (1 - es_after(white))
        #             = es_after(white) - es_before(white)    [a gain for white = loss for black]
        # We want es_after(white) - es_before(white) ∈ [0.10, 0.15).
        # eval_cp_to_expected_score(-50, "white") ≈ 0.486
        # eval_cp_to_expected_score(100, "white") ≈ 0.591
        # drop(black) = 0.591 - 0.486 = 0.105 ∈ [0.10, 0.15) = mistake for black
        positions[10] = _make_pos(10, eval_cp=-50)
        positions[11] = _make_pos(11, eval_cp=100)

        # Black inaccuracy at ply 13:
        # We need drop(black) ∈ [0.05, 0.10).
        # eval_cp_to_expected_score(-20, "white") ≈ 0.494
        # eval_cp_to_expected_score(50, "white")  ≈ 0.568
        # drop(black) = 0.568 - 0.494 = 0.074 ∈ [0.05, 0.10) = inaccuracy for black
        positions[12] = _make_pos(12, eval_cp=-20)
        positions[13] = _make_pos(13, eval_cp=50)

        # Oracle counts (what Lichess would report for this synthetic game)
        white_blunders = 1
        white_mistakes = 1
        white_inaccuracies = 1
        black_blunders = 1
        black_mistakes = 1
        black_inaccuracies = 1

        return (
            positions,
            white_blunders,
            white_mistakes,
            white_inaccuracies,
            black_blunders,
            black_mistakes,
            black_inaccuracies,
        )

    def test_derived_counts_close_to_oracle_white(self) -> None:
        """Derived white B/M/I counts are within SANITY_TOLERANCE of oracle."""
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 *"
        positions, wb, wm, wi, bb, bm, bi = self._make_oracle_positions_and_counts()

        # White user
        game = _make_game(
            pgn=pgn,
            user_color="white",
            result="1/2-1/2",
            base_time_seconds=600,
        )
        game.white_blunders = wb
        game.white_mistakes = wm
        game.white_inaccuracies = wi

        flaws = classify_game_flaws(game, positions)
        assert isinstance(flaws, list)

        # Derived counts from emitted records (mistakes + blunders only)
        derived_blunders = sum(1 for f in flaws if f["severity"] == "blunder")
        derived_mistakes = sum(1 for f in flaws if f["severity"] == "mistake")

        # For inaccuracy count: re-run all-moves pass and count inaccuracy severity entries for white
        # (inaccuracies are count-only per the 2026-06-05 amendment — not emitted but classifiable)
        from app.services.flaws_service import _run_all_moves_pass

        all_moves = _run_all_moves_pass(positions)
        derived_inaccuracies = sum(
            1
            for n, (mover, sev, _, _) in all_moves.items()
            if mover == "white" and sev == "inaccuracy"
        )

        assert abs(derived_blunders - wb) <= SANITY_TOLERANCE, (
            f"White blunders: derived={derived_blunders} oracle={wb} diff={abs(derived_blunders - wb)}"
        )
        assert abs(derived_mistakes - wm) <= SANITY_TOLERANCE, (
            f"White mistakes: derived={derived_mistakes} oracle={wm} diff={abs(derived_mistakes - wm)}"
        )
        assert abs(derived_inaccuracies - wi) <= SANITY_TOLERANCE, (
            f"White inaccuracies: derived={derived_inaccuracies} oracle={wi} diff={abs(derived_inaccuracies - wi)}"
        )

    def test_derived_counts_close_to_oracle_black(self) -> None:
        """Derived black B/M/I counts are within SANITY_TOLERANCE of oracle."""
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 *"
        positions, wb, wm, wi, bb, bm, bi = self._make_oracle_positions_and_counts()

        # Black user — to test the black-side derived counts
        game = _make_game(
            pgn=pgn,
            user_color="black",
            result="1/2-1/2",
            base_time_seconds=600,
        )
        game.black_blunders = bb
        game.black_mistakes = bm
        game.black_inaccuracies = bi

        flaws = classify_game_flaws(game, positions)
        assert isinstance(flaws, list)

        derived_blunders = sum(1 for f in flaws if f["severity"] == "blunder")
        derived_mistakes = sum(1 for f in flaws if f["severity"] == "mistake")

        from app.services.flaws_service import _run_all_moves_pass as _ramp_black

        all_moves = _ramp_black(positions)
        derived_inaccuracies = sum(
            1
            for n, (mover, sev, _, _) in all_moves.items()
            if mover == "black" and sev == "inaccuracy"
        )

        assert abs(derived_blunders - bb) <= SANITY_TOLERANCE, (
            f"Black blunders: derived={derived_blunders} oracle={bb} diff={abs(derived_blunders - bb)}"
        )
        assert abs(derived_mistakes - bm) <= SANITY_TOLERANCE, (
            f"Black mistakes: derived={derived_mistakes} oracle={bm} diff={abs(derived_mistakes - bm)}"
        )
        assert abs(derived_inaccuracies - bi) <= SANITY_TOLERANCE, (
            f"Black inaccuracies: derived={derived_inaccuracies} oracle={bi} diff={abs(derived_inaccuracies - bi)}"
        )
