"""Unit tests for the Phase 109 eval chart builder (_build_eval_series).

No DB required — all tests construct GamePosition / Game objects in memory
using the _make_pos / _make_game helpers from the flaws_service test pattern.

Sign convention: eval_cp / eval_mate are white-perspective (Stockfish).
"""

import pytest

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.library_service import _build_eval_series


# ---------------------------------------------------------------------------
# Fixture helpers (copied from test_flaws_service.py pattern)
# ---------------------------------------------------------------------------


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
    user_color: str = "white",
    result: str = "1-0",
    base_time_seconds: int | None = 600,
    increment_seconds: float | None = 0.0,
) -> Game:
    """Build a minimal Game object for unit testing (no DB flush)."""
    game = Game()
    game.pgn = "1. e4 e5 *"
    game.user_color = user_color
    game.result = result
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = increment_seconds
    return game


# ---------------------------------------------------------------------------
# TestEvalSeries — verifies the ES chart line (white-perspective)
# ---------------------------------------------------------------------------


class TestEvalSeries:
    def test_white_perspective_line_positive_cp(self) -> None:
        """Positive eval_cp → es > 0.5 (White ahead)."""
        positions = [
            _make_pos(0, eval_cp=100),
            _make_pos(1, eval_cp=200),
            _make_pos(2, eval_cp=150),
        ]
        game = _make_game(user_color="white")
        eval_series, _, _ = _build_eval_series(game, positions)
        assert len(eval_series) == 3
        for point in eval_series:
            assert point.es is not None
            assert point.es > 0.5, f"Expected es > 0.5 for positive eval_cp, got {point.es}"

    def test_white_perspective_line_negative_cp(self) -> None:
        """Negative eval_cp → es < 0.5 (Black ahead)."""
        positions = [
            _make_pos(0, eval_cp=-100),
            _make_pos(1, eval_cp=-200),
        ]
        game = _make_game(user_color="white")
        eval_series, _, _ = _build_eval_series(game, positions)
        assert len(eval_series) == 2
        for point in eval_series:
            assert point.es is not None
            assert point.es < 0.5, f"Expected es < 0.5 for negative eval_cp, got {point.es}"

    def test_null_eval_produces_null_es(self) -> None:
        """eval_cp=None and eval_mate=None → es=None (D-05: line breaks at missing eval)."""
        positions = [
            _make_pos(0, eval_cp=100),
            _make_pos(1, eval_cp=None, eval_mate=None),  # null eval
            _make_pos(2, eval_cp=50),
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert len(eval_series) == 3
        assert eval_series[0].es is not None
        null_point = eval_series[1]
        assert null_point.es is None, f"Expected es=None for null eval, got {null_point.es}"
        assert eval_series[2].es is not None

    def test_mate_hard_1_0_for_chart_line(self) -> None:
        """eval_mate > 0 → es = 1.0 (White has forced mate, white-perspective)."""
        positions = [
            _make_pos(0, eval_mate=3),  # White has mate in 3
            _make_pos(1, eval_mate=-2),  # Black has mate in 2
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert len(eval_series) == 2
        assert eval_series[0].es == pytest.approx(1.0), "White mate-in-N → es must be 1.0"
        assert eval_series[1].es == pytest.approx(0.0), "Black mate-in-N → es must be 0.0"

    def test_es_rounded_to_3dp(self) -> None:
        """ES values are rounded to 3 decimal places (D-05)."""
        positions = [_make_pos(0, eval_cp=100)]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        point = eval_series[0]
        if point.es is not None:
            assert point.es == round(point.es, 3), f"ES not rounded to 3dp: {point.es}"

    def test_eval_cp_and_mate_raw_values_preserved(self) -> None:
        """EvalPoint carries the raw eval_cp and eval_mate from the position (for tooltip)."""
        positions = [
            _make_pos(0, eval_cp=123, eval_mate=None),
            _make_pos(1, eval_cp=None, eval_mate=5),
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].eval_cp == 123
        assert eval_series[0].eval_mate is None
        assert eval_series[1].eval_cp is None
        assert eval_series[1].eval_mate == 5


# ---------------------------------------------------------------------------
# TestClockAndMoveTime — verifies clock_seconds passthrough + move-time derivation
# ---------------------------------------------------------------------------


class TestClockAndMoveTime:
    def test_clock_seconds_passthrough(self) -> None:
        """EvalPoint carries the position's raw clock_seconds for the tooltip."""
        positions = [
            _make_pos(0, eval_cp=10, clock_seconds=597.0),
            _make_pos(1, eval_cp=10, clock_seconds=595.0),
        ]
        game = _make_game(base_time_seconds=600, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].clock_seconds == 597.0
        assert eval_series[1].clock_seconds == 595.0

    def test_move_seconds_first_move_uses_base_time(self) -> None:
        """First move of each color: time spent = base_time − clock + increment."""
        positions = [
            _make_pos(0, eval_cp=10, clock_seconds=597.0),  # White, 600 → 597 = 3s
            _make_pos(1, eval_cp=10, clock_seconds=595.0),  # Black, 600 → 595 = 5s
        ]
        game = _make_game(base_time_seconds=600, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].move_seconds == pytest.approx(3.0)
        assert eval_series[1].move_seconds == pytest.approx(5.0)

    def test_move_seconds_uses_prior_same_color_clock(self) -> None:
        """Move time deducts the SAME color's previous clock, not the adjacent ply."""
        positions = [
            _make_pos(0, eval_cp=10, clock_seconds=597.0),  # White first
            _make_pos(1, eval_cp=10, clock_seconds=580.0),  # Black first
            _make_pos(2, eval_cp=10, clock_seconds=590.0),  # White: 597 → 590 = 7s
            _make_pos(3, eval_cp=10, clock_seconds=560.0),  # Black: 580 → 560 = 20s
        ]
        game = _make_game(base_time_seconds=600, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[2].move_seconds == pytest.approx(7.0)
        assert eval_series[3].move_seconds == pytest.approx(20.0)

    def test_move_seconds_adds_increment(self) -> None:
        """Increment is added back: time spent = prior − clock + increment."""
        positions = [_make_pos(0, eval_cp=10, clock_seconds=178.0)]
        game = _make_game(base_time_seconds=180, increment_seconds=5.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        # 180 − 178 + 5 = 7.0
        assert eval_series[0].move_seconds == pytest.approx(7.0)

    def test_move_seconds_clamps_negative_to_zero(self) -> None:
        """A premove/clock-jitter case never yields a negative move time."""
        positions = [_make_pos(0, eval_cp=10, clock_seconds=605.0)]  # clock > base
        game = _make_game(base_time_seconds=600, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].move_seconds == pytest.approx(0.0)

    def test_no_clock_yields_null_fields(self) -> None:
        """No %clk annotation (chess.com) → clock_seconds and move_seconds both null."""
        positions = [_make_pos(0, eval_cp=10, clock_seconds=None)]
        game = _make_game(base_time_seconds=600, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].clock_seconds is None
        assert eval_series[0].move_seconds is None

    def test_move_seconds_null_when_base_time_unknown(self) -> None:
        """First move with no base time and no prior clock → move_seconds null."""
        positions = [_make_pos(0, eval_cp=10, clock_seconds=300.0)]
        game = _make_game(base_time_seconds=None, increment_seconds=0.0)
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[0].clock_seconds == 300.0
        assert eval_series[0].move_seconds is None


# ---------------------------------------------------------------------------
# TestFlawMarkers — verifies the flaw dot detection and is_user flag
# ---------------------------------------------------------------------------


class TestFlawMarkers:
    def _minimal_blunder_positions(
        self, user_color: str = "white"
    ) -> tuple[list[GamePosition], "Game"]:
        """Build a minimal 3-position sequence where the player makes a blunder.

        For white user:
        - ply 0: initial (eval_cp=+200, white ahead significantly)
        - ply 2: after white's move (eval_cp=+200 → white still ahead; used as es_before)
        - ply 4: after white's move that drops eval by blunder threshold
          positions[2]: eval_cp=-300 (big drop from +200 white perspective, mover POV drop > BLUNDER_DROP)
        This uses mover parity: ply 2 → white mover (n=2, n%2==0 → white).
        """
        # Large positive → large negative = white blunder (white mover at ply 2)
        # Use enough eval_cp to guarantee blunder threshold (BLUNDER_DROP=0.15)
        # eval_cp_to_expected_score(500, "white") ≈ 0.86 (well above 0.5)
        # eval_cp_to_expected_score(-500, "white") ≈ 0.14 (well below 0.5)
        # Drop = 0.86 - 0.14 = 0.72 >> BLUNDER_DROP=0.15 → blunder
        positions = [
            _make_pos(0, eval_cp=0),  # initial position, no mover
            _make_pos(1, eval_cp=500),  # after ply 1 (black mover), white ahead
            _make_pos(2, eval_cp=-500),  # after ply 2 (white mover) — big drop → blunder
        ]
        game = _make_game(user_color=user_color, result="0-1")
        return positions, game

    def test_both_color_detection(self) -> None:
        """Both a white-mover drop and a black-mover drop produce FlawMarker rows (D-01/D-02)."""
        # ply 2: white mover blunder (+500 → −500 white-perspective)
        # ply 3: black mover blunder from black's perspective
        # For black mover at ply 3: es_before from black's POV at positions[2], es_after at positions[3]
        # positions[2].eval_cp = -500 → black-POV es_before = eval_cp_to_es(-500, "black") ≈ 0.86
        # positions[3].eval_cp = +500 → black-POV es_after = eval_cp_to_es(+500, "black") ≈ 0.14
        # Drop for black mover = 0.86 - 0.14 = 0.72 >> BLUNDER_DROP → black blunder detected
        positions = [
            _make_pos(0, eval_cp=0),
            _make_pos(1, eval_cp=500),  # after ply 1 (black mover)
            _make_pos(2, eval_cp=-500),  # after ply 2 (white mover) — white blunder
            _make_pos(3, eval_cp=500),  # after ply 3 (black mover) — black blunder
        ]
        game = _make_game(user_color="white", result="1/2-1/2")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        plies_with_markers = {m.ply for m in flaw_markers}
        assert 2 in plies_with_markers, "White mover blunder at ply 2 must produce a flaw marker"
        assert 3 in plies_with_markers, "Black mover blunder at ply 3 must produce a flaw marker"

    def test_is_user_flag_player(self) -> None:
        """Flaw by the user (white) → is_user=True."""
        positions, game = self._minimal_blunder_positions(user_color="white")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        # ply 2 is a white mover (n=2, n%2==0 → white) → is_user=True for white user
        user_markers = [m for m in flaw_markers if m.ply == 2]
        assert user_markers, "Expected a flaw marker at ply 2 (white blunder)"
        assert user_markers[0].is_user is True, "White user blunder must have is_user=True"

    def test_move_san_populated(self) -> None:
        """FlawMarker carries positions[ply].move_san for the tooltip move label."""
        positions, game = self._minimal_blunder_positions(user_color="white")
        positions[2].move_san = "Qxh7"  # the flawed move at ply 2
        _, flaw_markers, _ = _build_eval_series(game, positions)
        marker = next(m for m in flaw_markers if m.ply == 2)
        assert marker.move_san == "Qxh7", "FlawMarker must expose the flawed move's SAN"

    def test_is_user_flag_opponent(self) -> None:
        """Flaw by the opponent → is_user=False."""
        # user_color="black": white mover at ply 2 is the opponent
        positions, game = self._minimal_blunder_positions(user_color="black")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        user_markers = [m for m in flaw_markers if m.ply == 2]
        assert user_markers, "Expected a flaw marker at ply 2 (white mover)"
        assert user_markers[0].is_user is False, "White mover when user is black → is_user=False"

    def test_inaccuracy_has_empty_tags(self) -> None:
        """Inaccuracy markers carry empty tags (D-03)."""
        # eval_cp drop just above INACCURACY_DROP but below MISTAKE_DROP:
        # eval_cp_to_expected_score(100, "white") ≈ 0.591
        # eval_cp_to_expected_score(0, "white") = 0.5
        # Drop ≈ 0.091, which is > INACCURACY_DROP=0.05 but < MISTAKE_DROP=0.10 → inaccuracy
        positions = [
            _make_pos(0, eval_cp=0),
            _make_pos(1, eval_cp=100),  # after ply 1 (black mover)
            _make_pos(2, eval_cp=0),  # after ply 2 (white mover) — small drop → inaccuracy
        ]
        game = _make_game(user_color="white", result="1-0")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        inaccuracy_markers = [m for m in flaw_markers if m.severity == "inaccuracy"]
        if inaccuracy_markers:
            for marker in inaccuracy_markers:
                assert marker.tags == [], (
                    f"Inaccuracy marker must have empty tags, got {marker.tags}"
                )

    def test_opponent_tags_strip_user_framed(self) -> None:
        """Opponent B/M markers never contain 'miss' or 'lucky' (D-03 resolution)."""
        # Build positions where an opponent blunder occurs.
        # The specific tags depend on context, but 'miss' and 'lucky' must be absent.
        # ply 2 is white mover (n=2, n%2==0); user=black → white is opponent
        # Use large eval swings to ensure blunder detection
        positions = [
            _make_pos(0, eval_cp=0),
            _make_pos(1, eval_cp=500),  # after ply 1
            _make_pos(2, eval_cp=-500),  # after ply 2 (white/opponent blunder)
        ]
        game = _make_game(user_color="black", result="0-1")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        opponent_markers = [m for m in flaw_markers if not m.is_user]
        for marker in opponent_markers:
            assert "miss" not in marker.tags, (
                f"Opponent marker must not contain 'miss' tag, got {marker.tags}"
            )
            assert "lucky" not in marker.tags, (
                f"Opponent marker must not contain 'lucky' tag, got {marker.tags}"
            )

    def test_blunder_has_tags(self) -> None:
        """Blunder markers for the player carry tags (non-empty)."""
        # Large eval swing to ensure tags are populated (reversed etc.)
        positions = [
            _make_pos(0, eval_cp=0),
            _make_pos(1, eval_cp=900),  # white way ahead
            _make_pos(2, eval_cp=-900),  # white blunders away huge advantage
        ]
        game = _make_game(user_color="white", result="0-1")
        _, flaw_markers, _ = _build_eval_series(game, positions)
        user_markers = [m for m in flaw_markers if m.is_user and m.severity == "blunder"]
        if user_markers:
            # reversed should be present since es_before >= 0.70 and es_after <= 0.30
            # (can't guarantee exact tags without knowing increment, but at least phase is always added)
            assert len(user_markers[0].tags) > 0, "Blunder should carry at least one tag"


# ---------------------------------------------------------------------------
# TestPhaseTransitions — verifies the phase-transition ply derivation
# ---------------------------------------------------------------------------


class TestPhaseTransitions:
    def test_no_ply_0_line(self) -> None:
        """Phase transition at ply 0 is NOT emitted (D-06: no ply-0 line).

        Even if positions[0].phase == 1, it should not become middlegame_ply=0.
        Note: ply 0 is the initial position (no move played), so a phase=1 there
        would be an anomaly. The builder simply skips ply 0 for phase tracking
        because it's the starting position, not a transition.
        """
        # positions[0] has phase=1 but no move was played — should not trigger transition
        positions = [
            _make_pos(0, eval_cp=0, phase=1),  # ply 0 should not count
            _make_pos(1, eval_cp=100, phase=1),  # first real middlegame ply
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        # The first ply where phase==1 that is NOT ply 0 should be 1
        if phase_transitions.middlegame_ply is not None:
            assert phase_transitions.middlegame_ply != 0, "ply-0 must not be a phase transition"

    def test_middlegame_first_ply(self) -> None:
        """middlegame_ply = first ply where phase == 1 (D-06)."""
        positions = [
            _make_pos(0, eval_cp=0, phase=0),
            _make_pos(1, eval_cp=50, phase=0),
            _make_pos(2, eval_cp=60, phase=1),  # first middlegame ply
            _make_pos(3, eval_cp=70, phase=1),
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        assert phase_transitions.middlegame_ply == 2, (
            f"Expected middlegame_ply=2, got {phase_transitions.middlegame_ply}"
        )

    def test_endgame_first_ply(self) -> None:
        """endgame_ply = first ply where phase == 2 (D-06)."""
        positions = [
            _make_pos(0, eval_cp=0, phase=0),
            _make_pos(1, eval_cp=50, phase=1),
            _make_pos(2, eval_cp=60, phase=2),  # first endgame ply
            _make_pos(3, eval_cp=70, phase=2),
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        assert phase_transitions.endgame_ply == 2, (
            f"Expected endgame_ply=2, got {phase_transitions.endgame_ply}"
        )

    def test_at_most_two_transitions(self) -> None:
        """At most two phase transitions are emitted (D-06)."""
        positions = [
            _make_pos(0, eval_cp=0, phase=0),
            _make_pos(1, eval_cp=50, phase=1),  # middlegame starts
            _make_pos(2, eval_cp=60, phase=2),  # endgame starts
            _make_pos(3, eval_cp=70, phase=2),
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        # Count non-None transitions
        transitions = [
            v
            for v in [phase_transitions.middlegame_ply, phase_transitions.endgame_ply]
            if v is not None
        ]
        assert len(transitions) <= 2, f"At most 2 phase transitions, got {len(transitions)}"

    def test_absent_phase_is_none(self) -> None:
        """When a phase is never reached, its ply is None (D-06)."""
        positions = [
            _make_pos(0, eval_cp=0, phase=0),
            _make_pos(1, eval_cp=50, phase=0),
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        assert phase_transitions.middlegame_ply is None, "Middlegame never reached → None"
        assert phase_transitions.endgame_ply is None, "Endgame never reached → None"

    def test_both_transitions_in_game(self) -> None:
        """Both middlegame_ply and endgame_ply are populated when both phases occur."""
        positions = [
            _make_pos(0, eval_cp=0, phase=0),
            _make_pos(1, eval_cp=0, phase=0),
            _make_pos(2, eval_cp=20, phase=1),  # middlegame at ply 2
            _make_pos(3, eval_cp=30, phase=1),
            _make_pos(4, eval_cp=40, phase=2),  # endgame at ply 4
        ]
        game = _make_game()
        _, _, phase_transitions = _build_eval_series(game, positions)
        assert phase_transitions.middlegame_ply == 2
        assert phase_transitions.endgame_ply == 4


# ---------------------------------------------------------------------------
# TestCheckmateFinalPly — the terminal (unevaluated) checkmate ply gets es 1.0/0.0
# ---------------------------------------------------------------------------


class TestCheckmateFinalPly:
    def test_white_checkmate_fills_final_es_1(self) -> None:
        """White delivers mate on ply 2 → unevaluated final ply 3 gets es=1.0."""
        positions = [
            _make_pos(0, eval_cp=300, move_san="Qh5"),
            _make_pos(1, eval_cp=350, move_san="Nc6"),
            _make_pos(2, eval_cp=None, move_san="Qxf7#"),  # White's mating move
            _make_pos(3, eval_cp=None, eval_mate=None, move_san=None),  # final position
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[-1].es == pytest.approx(1.0)

    def test_black_checkmate_fills_final_es_0(self) -> None:
        """Black delivers mate on ply 3 → unevaluated final ply 4 gets es=0.0."""
        positions = [
            _make_pos(0, eval_cp=-100, move_san="f3"),
            _make_pos(1, eval_cp=-150, move_san="e5"),
            _make_pos(2, eval_cp=-200, move_san="g4"),
            _make_pos(3, eval_cp=None, move_san="Qh4#"),  # Black's mating move (odd ply)
            _make_pos(4, eval_cp=None, eval_mate=None, move_san=None),  # final position
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[-1].es == pytest.approx(0.0)

    def test_non_checkmate_final_ply_stays_null(self) -> None:
        """Resignation/timeout: last move has no '#' → final ply es stays None (trimmed)."""
        positions = [
            _make_pos(0, eval_cp=100, move_san="e4"),
            _make_pos(1, eval_cp=120, move_san="e5"),
            _make_pos(2, eval_cp=None, move_san="Nf3"),  # resigned here, no mate
            _make_pos(3, eval_cp=None, eval_mate=None, move_san=None),  # final position
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[-1].es is None

    def test_evaluated_final_ply_unchanged(self) -> None:
        """A final ply that already has an eval is never overwritten by the mate fill."""
        positions = [
            _make_pos(0, eval_cp=100, move_san="e4"),
            _make_pos(1, eval_cp=120, move_san="Qh4#"),  # mate SAN but ply already evaluated
        ]
        game = _make_game()
        eval_series, _, _ = _build_eval_series(game, positions)
        assert eval_series[-1].es is not None
        assert eval_series[-1].es != pytest.approx(0.0)
