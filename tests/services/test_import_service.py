"""Regression tests for the Phase 91 hot-lane refactor in import_service.py.

Two test classes cover:
1. TestHotLaneNoEvalCalls: proves engine.evaluate is never called from _flush_batch
   (T-91-12 CI regression guard — structural invariant).
2. TestHotLaneCoveredGate: integration + unit tests for Stage 5c covered-game gate
   (_collect_covered_game_ids + evals_completed_at marking).

Phase 91 / SEED-023:
    The Stockfish eval pass was removed from the hot import lane and moved to
    the cold-drain coroutine (run_eval_drain in eval_drain.py).  _flush_batch
    must NEVER call engine.evaluate, regardless of the game content.
    Stage 5c sets evals_completed_at = NOW() for games whose entry plies are
    already covered (lichess %eval) or absent (very short games) so they are
    never re-picked by the cold drain.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.normalization import NormalizedGame

# Module-level test constants (CLAUDE.md: no magic numbers)
BATCH_SIZE_FOR_HOT_LANE_TEST: int = 2

# Minimal valid PGN for _board_at_ply replay.
# Short enough that process_game_pgn returns only opening plies (phase=0):
# piece count stays at 16 (no trades), backrank is always occupied, mixedness~0.
_SHORT_PGN_COVERED: str = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O *"

# Lichess PGN with %eval annotations — all entry plies pre-covered.
_LICHESS_PGN_WITH_EVAL: str = (
    "1. e4 { [%eval 0.15] } e5 { [%eval 0.12] } "
    "2. Nf3 { [%eval 0.10] } Nc6 { [%eval 0.08] } "
    "3. Bc4 { [%eval 0.05] } Bc5 { [%eval 0.02] } "
    "4. O-O { [%eval 0.00] } d6 { [%eval -0.03] } *"
)


# ---------------------------------------------------------------------------
# Mock session helpers (mirrors test_import_service_eval.py)
# ---------------------------------------------------------------------------


def _make_mock_session() -> MagicMock:
    """Build a minimal mock AsyncSession with async context manager support."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchall.return_value = []
    session.execute.return_value = result_mock
    return session


def _mock_session_maker(session: MagicMock) -> MagicMock:
    """Return a callable that yields session as async context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    maker = MagicMock()
    maker.return_value = ctx
    return maker


def _make_opening_only_processing_result() -> dict[str, Any]:
    """Return a processing result with only phase=0 (opening) plies — no entry plies needing eval.

    Simulates a short game that never enters the middlegame or endgame phase.
    Both _collect_midgame_eval_targets and _collect_endgame_span_eval_targets
    return empty for this data, making the game "covered" by Stage 5c.
    """
    plies: list[dict[str, Any]] = [
        {
            "ply": i,
            "white_hash": i + 100,
            "black_hash": i + 200,
            "full_hash": i + 300,
            "move_san": f"move{i}",
            "clock_seconds": None,
            "eval_cp": None,
            "eval_mate": None,
            "material_count": 7800,
            "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 16,
            "backrank_sparse": False,
            "mixedness": 0,
            "endgame_class": None,
            "phase": 0,  # opening only — no entry plies
        }
        for i in range(4)
    ]
    return {"plies": plies, "result_fen": None, "move_count": 2}


def _make_midgame_needs_eval_processing_result() -> dict[str, Any]:
    """Return a processing result with phase=1 plies with no %eval — requires Stockfish.

    Simulates a game that entered the middlegame phase. The MIN(ply) where phase==1
    has eval_cp=None and eval_mate=None, so _collect_midgame_eval_targets would
    return a non-empty list. Stage 5c must NOT mark this game as covered.
    """
    plies: list[dict[str, Any]] = [
        # Opening ply (phase=0)
        {
            "ply": 0,
            "white_hash": 100,
            "black_hash": 200,
            "full_hash": 300,
            "move_san": "e4",
            "clock_seconds": None,
            "eval_cp": None,
            "eval_mate": None,
            "material_count": 7800,
            "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 16,
            "backrank_sparse": False,
            "mixedness": 0,
            "endgame_class": None,
            "phase": 0,
        },
        # Middlegame entry ply (phase=1, no eval — needs Stockfish)
        {
            "ply": 1,
            "white_hash": 101,
            "black_hash": 201,
            "full_hash": 301,
            "move_san": "Nc3",
            "clock_seconds": None,
            "eval_cp": None,   # no lichess %eval — needs engine evaluation
            "eval_mate": None,
            "material_count": 5000,
            "material_signature": "KQRBN_KQRBN",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 10,
            "backrank_sparse": True,
            "mixedness": 200,
            "endgame_class": None,
            "phase": 1,  # middlegame entry — needs eval
        },
    ]
    return {"plies": plies, "result_fen": None, "move_count": 1}


# ---------------------------------------------------------------------------
# Class 1: TestHotLaneNoEvalCalls
# ---------------------------------------------------------------------------


class TestHotLaneNoEvalCalls:
    """T-91-12: engine.evaluate must NEVER be called from the hot import lane.

    This is a CI regression guard — if a future edit re-introduces engine.evaluate
    calls inside _flush_batch (or any function it calls), this test fails.
    """

    @pytest.mark.asyncio
    async def test_flush_batch_no_engine_calls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Drive _flush_batch with a 2-game batch; assert engine.evaluate is never invoked.

        Monkeypatches engine_service.evaluate in both the module where the engine
        lives and the eval_drain module to raise AssertionError if ever called.
        The hot lane (_flush_batch) must complete without triggering either patch.
        """
        import app.services.engine as engine_module
        import app.services.eval_drain as drain_module

        # Patch evaluate in the engine module and the drain (which the hot lane
        # no longer imports, but we patch defensively to catch any regression).
        engine_calls_made: list[str] = []

        async def _assert_not_called(*args: Any, **kwargs: Any) -> tuple[int | None, int | None]:
            engine_calls_made.append("engine.evaluate called from hot lane!")
            raise AssertionError("engine.evaluate must not be called from hot lane")

        monkeypatch.setattr(engine_module, "evaluate", _assert_not_called)
        monkeypatch.setattr(drain_module, "engine_service", engine_module)

        from app.services.import_service import _flush_batch

        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [
            (1001, "pgn-game-A"),
            (1002, "pgn-game-B"),
        ]
        mock_session.execute.return_value = select_result

        batch: list[Any] = [
            {
                "platform": "chess.com",
                "platform_game_id": "pgn-game-A",
                "pgn": _SHORT_PGN_COVERED,
                "user_id": 1,
            },
            {
                "platform": "chess.com",
                "platform_game_id": "pgn-game-B",
                "pgn": _SHORT_PGN_COVERED,
                "user_id": 1,
            },
        ]

        with (
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[1001, 1002]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_opening_only_processing_result(),
            ),
        ):
            # Must complete without raising — if engine.evaluate is called,
            # the monkeypatched function raises AssertionError.
            await _flush_batch(mock_session, cast(list[NormalizedGame], batch), user_id=1)

        # Belt-and-suspenders: call count must be zero.
        assert engine_calls_made == [], (
            f"engine.evaluate was called from the hot lane: {engine_calls_made}. "
            "Phase 91 / SEED-023 requires eval work to run ONLY in eval_drain.py."
        )


# ---------------------------------------------------------------------------
# Class 2: TestHotLaneCoveredGate
# ---------------------------------------------------------------------------


class TestHotLaneCoveredGate:
    """Stage 5c: _collect_covered_game_ids and evals_completed_at hot-lane gate."""

    # -- Pure unit tests (no DB) -------------------------------------------

    def test_collect_covered_game_ids_empty_input(self) -> None:
        """_collect_covered_game_ids([]) returns [] (empty batch is covered)."""
        from app.services.import_service import _collect_covered_game_ids

        result = _collect_covered_game_ids([])
        assert result == [], f"Expected [] for empty input, got {result}"

    def test_collect_covered_game_ids_filters_correctly(self) -> None:
        """Pure unit: game with phase=1 no-eval not covered; opening-only game is covered.

        Three game_eval_data entries:
          - Game 1001: one phase=1 ply with eval_cp=None → needs eval → NOT covered
          - Game 1002: only phase=0 plies → no entry plies → covered
          - Game 1003: one phase=1 ply but eval_cp already set (lichess) → covered
        """
        from app.services.import_service import _collect_covered_game_ids

        # Build phase=1 ply without eval (needs Stockfish)
        midgame_ply_no_eval: dict[str, Any] = {
            "ply": 1,
            "white_hash": 1,
            "black_hash": 2,
            "full_hash": 3,
            "move_san": "Nc3",
            "clock_seconds": None,
            "eval_cp": None,    # no eval — needs Stockfish
            "eval_mate": None,
            "material_count": 5000,
            "material_signature": "KQ_KQ",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 10,
            "backrank_sparse": True,
            "mixedness": 200,
            "endgame_class": None,
            "phase": 1,
        }
        # Opening-only ply (phase=0, no entry plies)
        opening_ply: dict[str, Any] = {
            "ply": 0,
            "white_hash": 10,
            "black_hash": 20,
            "full_hash": 30,
            "move_san": "e4",
            "clock_seconds": None,
            "eval_cp": None,
            "eval_mate": None,
            "material_count": 7800,
            "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 16,
            "backrank_sparse": False,
            "mixedness": 0,
            "endgame_class": None,
            "phase": 0,
        }
        # Phase=1 ply WITH eval_cp already set (lichess %eval covered)
        midgame_ply_with_eval: dict[str, Any] = {**midgame_ply_no_eval, "eval_cp": 15}

        game_eval_data: list[tuple[int, str, list[Any]]] = [
            (1001, _SHORT_PGN_COVERED, [midgame_ply_no_eval]),  # needs eval
            (1002, _SHORT_PGN_COVERED, [opening_ply]),           # opening only — covered
            (1003, _SHORT_PGN_COVERED, [midgame_ply_with_eval]), # lichess covered
        ]

        covered = _collect_covered_game_ids(game_eval_data)
        covered_set = set(covered)

        assert 1001 not in covered_set, (
            "Game 1001 has phase=1 ply with no eval — must NOT be marked covered."
        )
        assert 1002 in covered_set, (
            "Game 1002 has only opening plies — no entry plies, must be marked covered."
        )
        assert 1003 in covered_set, (
            "Game 1003 has all lichess-covered entry plies — must be marked covered."
        )

    # -- Integration test (real DB) ----------------------------------------

    @pytest.mark.asyncio
    async def test_stage5c_marks_covered_games(self, db_session: Any) -> None:
        """Stage 5c marks only fully-covered games; pending games stay NULL.

        Setup:
          - Game A: phase=1 ply with eval_cp=None (needs Stockfish) → evals_completed_at NULL
          - Game B: opening-only plies (no entry plies) → evals_completed_at = NOW()

        Games are pre-inserted, then _flush_batch is driven with mocked
        bulk_insert_games (returns the pre-inserted IDs) and mocked process_game_pgn
        (returns specific ply profiles). After flush, we SELECT evals_completed_at
        for both games and assert the Stage 5c gate behavior.
        """
        from sqlalchemy import select

        from app.models.game import Game
        from app.services.import_service import _flush_batch
        from tests.conftest import ensure_test_user

        test_user_id = 92300  # unique ID for this test module
        await ensure_test_user(db_session, test_user_id)

        platform_id_a = "stage5c-test-game-A"
        platform_id_b = "stage5c-test-game-B"

        # Pre-insert the two games so they exist in DB for the SELECT in _collect_position_rows
        game_a = Game(
            user_id=test_user_id,
            platform="chess.com",
            platform_game_id=platform_id_a,
            pgn=_SHORT_PGN_COVERED,
            result="1/2-1/2",
            user_color="white",
            rated=True,
            is_computer_game=False,
        )
        game_b = Game(
            user_id=test_user_id,
            platform="chess.com",
            platform_game_id=platform_id_b,
            pgn=_SHORT_PGN_COVERED,
            result="1-0",
            user_color="black",
            rated=True,
            is_computer_game=False,
        )
        db_session.add(game_a)
        db_session.add(game_b)
        await db_session.flush()
        game_a_id: int = game_a.id
        game_b_id: int = game_b.id

        # Track call index to assign correct processing result per game
        call_index: list[int] = [0]
        # Order matches the batch order (A first, B second)
        processing_results = [
            _make_midgame_needs_eval_processing_result(),  # Game A: needs eval
            _make_opening_only_processing_result(),         # Game B: covered (opening only)
        ]

        def _pgn_side_effect(pgn: str) -> dict[str, Any]:
            idx = call_index[0] % len(processing_results)
            call_index[0] += 1
            return processing_results[idx]

        # Build minimal batch dicts matching _collect_position_rows dict-fallback path
        batch: list[Any] = [
            {"platform_game_id": platform_id_a, "pgn": _SHORT_PGN_COVERED},
            {"platform_game_id": platform_id_b, "pgn": _SHORT_PGN_COVERED},
        ]

        with (
            # Return pre-inserted IDs so _collect_position_rows does the SELECT
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[game_a_id, game_b_id]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                side_effect=_pgn_side_effect,
            ),
        ):
            await _flush_batch(db_session, cast(list[NormalizedGame], batch), user_id=test_user_id)
            await db_session.flush()

        # Retrieve evals_completed_at for both games
        result = await db_session.execute(
            select(Game.platform_game_id, Game.evals_completed_at)
            .where(Game.user_id == test_user_id)
            .where(Game.platform_game_id.in_([platform_id_a, platform_id_b]))
        )
        rows = {row[0]: row[1] for row in result.all()}

        # Game A: needs eval — evals_completed_at must be NULL
        assert platform_id_a in rows, "Game A was not found in the DB"
        assert rows[platform_id_a] is None, (
            f"Game A has a phase=1 ply with no %eval and must remain pending "
            f"(evals_completed_at = NULL). Got: {rows[platform_id_a]}"
        )

        # Game B: opening-only — evals_completed_at must be set by Stage 5c
        assert platform_id_b in rows, "Game B was not found in the DB"
        assert rows[platform_id_b] is not None, (
            "Game B has only opening plies (no entry plies needing eval) and must be "
            f"marked covered by Stage 5c (evals_completed_at != NULL). Got: {rows[platform_id_b]}"
        )
