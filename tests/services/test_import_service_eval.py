"""Import-time engine eval integration tests (IMP-01). Phase 78 Wave 0.

Tests verify that:
- chess.com games (no lichess %eval) get span-entry rows evaluated by Stockfish (T-78-17, IMP-01)
- lichess games with %eval at span-entry ply: existing eval is preserved, engine NOT called (T-78-17)
- engine error (None, None) return: row eval stays NULL, Sentry context is set with bounded fields (T-78-18, D-11)
- short games with no endgame: engine is NOT called (zero-call short-circuit)
- multi-class span entries: engine is called once per class (not once per ply)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# PGN test fixtures
# ---------------------------------------------------------------------------

# A minimal valid PGN for _board_at_ply replay in import_service.
# process_game_pgn is mocked in tests, so this PGN is only used by _board_at_ply
# to reconstruct the board at the span-entry ply. It just needs to be parseable
# with at least one legal move so _board_at_ply can return the board at ply 0.
_CHESS_COM_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Be7 4. O-O d6 5. d3 Nf6 1/2-1/2"

# A lichess PGN with %eval annotations at ply 0 — used to test that the eval pass
# skips span-entry plies that already have eval_cp populated from lichess.
_LICHESS_PGN_WITH_EVAL = (
    "1. e4 { [%eval 0.15] } e5 { [%eval 0.12] } "
    "2. Nf3 { [%eval 0.10] } Nc6 { [%eval 0.08] } "
    "3. Bc4 { [%eval 0.05] } Be7 { [%eval 0.02] } 1/2-1/2"
)

# ENDGAME_PLY_THRESHOLD = 6 (from endgame_repository constant)
_ENDGAME_PLY_THRESHOLD = 6

# Endgame class int values matching endgame_service._CLASS_TO_INT
_EC_ROOK = 1
_EC_PAWN = 3


# ---------------------------------------------------------------------------
# PlyData mock builders
# ---------------------------------------------------------------------------


def _make_endgame_plies(
    count: int = 8,
    endgame_class: int = _EC_ROOK,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    start_ply: int = 0,
) -> list[dict[str, Any]]:
    """Return *count* ply dicts all in *endgame_class*.

    eval_cp / eval_mate default to None (chess.com: no lichess eval).
    """
    plies: list[dict[str, Any]] = []
    for i in range(count):
        plies.append({
            "ply": start_ply + i,
            "white_hash": start_ply + i + 100,
            "black_hash": start_ply + i + 200,
            "full_hash": start_ply + i + 300,
            "move_san": "Rh1" if i % 2 == 0 else None,
            "clock_seconds": None,
            "eval_cp": eval_cp,
            "eval_mate": eval_mate,
            "material_count": 1000,
            "material_signature": "KR_KR",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 2,
            "backrank_sparse": True,
            "mixedness": 0,
            "endgame_class": endgame_class,
        })
    return plies


def _make_two_class_plies() -> list[dict[str, Any]]:
    """Return 8 rook-endgame plies (ply 0-7) + 8 pawn-endgame plies (ply 8-15).

    Two distinct endgame classes, each >= ENDGAME_PLY_THRESHOLD, eval_cp=None throughout.
    """
    rook_plies = _make_endgame_plies(count=8, endgame_class=_EC_ROOK, eval_cp=None, start_ply=0)
    pawn_plies: list[dict[str, Any]] = []
    for i in range(8):
        pawn_plies.append({
            "ply": 8 + i,
            "white_hash": 8 + i + 100,
            "black_hash": 8 + i + 200,
            "full_hash": 8 + i + 300,
            "move_san": "a4" if i % 2 == 0 else None,
            "clock_seconds": None,
            "eval_cp": None,
            "eval_mate": None,
            "material_count": 500,
            "material_signature": "KP_KP",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
            "piece_count": 0,
            "backrank_sparse": True,
            "mixedness": 0,
            "endgame_class": _EC_PAWN,
        })
    return rook_plies + pawn_plies


def _make_processing_result(
    plies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Wrap plies in a GameProcessingResult-shaped dict."""
    move_count = max((p["ply"] for p in plies), default=0) // 2 + 1 if plies else 0
    return {
        "plies": plies,
        "result_fen": "8/8/4k3/8/8/3K4/8/R7",
        "move_count": move_count,
    }


# ---------------------------------------------------------------------------
# Mock session/maker helpers (mirrors test_import_service.py)
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


def _mock_http_ctx() -> AsyncMock:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Test 1: chess.com path — eval populated on span-entry row
# ---------------------------------------------------------------------------


class TestImportEvalChessCom:
    async def test_chess_com_import_populates_span_entry_eval(self) -> None:
        """chess.com game with endgame plies: engine is called, span-entry gets eval_cp=150."""
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="chess.com", username="alice")

        mock_evaluate = AsyncMock(return_value=(150, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-eval-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        endgame_plies = _make_endgame_plies(count=8, endgame_class=_EC_ROOK, eval_cp=None)
        processing_result = _make_processing_result(endgame_plies)

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-eval-1",
                "pgn": _CHESS_COM_PGN,
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
        ):
            await import_service.run_import(job_id)

        # Engine called at least once (once per span-entry class, IMP-01)
        assert mock_evaluate.call_count >= 1, (
            f"Expected engine.evaluate >= 1 calls for chess.com endgame game, "
            f"got {mock_evaluate.call_count}"
        )

        # At least one UPDATE call (session.execute with UPDATE stmt for eval_cp)
        execute_calls = mock_session.execute.call_args_list
        update_calls = [
            c for c in execute_calls
            if hasattr(c.args[0], "is_update") and c.args[0].is_update
        ]
        assert len(update_calls) >= 1, (
            "Expected at least one UPDATE call for eval_cp after engine.evaluate"
        )

        import_service._jobs.clear()


# ---------------------------------------------------------------------------
# Test 2: lichess preservation — engine NOT called for span entry with eval
# ---------------------------------------------------------------------------


class TestImportEvalLichessPreservation:
    async def test_lichess_eval_at_span_entry_skips_engine(self) -> None:
        """Lichess span-entry ply already has eval_cp=15: engine must NOT be called (T-78-17)."""
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="lichess", username="alice")

        # engine returns 999 — if engine IS called, test will fail (wrong value)
        mock_evaluate = AsyncMock(return_value=(999, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-lichess-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        # Span-entry ply (ply=0) already has eval_cp=15 from lichess %eval
        lichess_plies = _make_endgame_plies(count=8, endgame_class=_EC_ROOK, eval_cp=15)
        processing_result = _make_processing_result(lichess_plies)

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "lichess",
                "platform_game_id": "game-lichess-1",
                "pgn": _LICHESS_PGN_WITH_EVAL,
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.lichess_client.fetch_lichess_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
        ):
            await import_service.run_import(job_id)

        # Span-entry ply has eval_cp=15 (lichess populated) — engine MUST NOT be called
        assert mock_evaluate.call_count == 0, (
            f"Engine should NOT be called when lichess %eval already populated span entry. "
            f"Got {mock_evaluate.call_count} calls (T-78-17: lichess values must be preserved)."
        )

        import_service._jobs.clear()


# ---------------------------------------------------------------------------
# Test 3: engine error — row stays NULL, Sentry context has bounded fields
# ---------------------------------------------------------------------------


class TestImportEvalEngineError:
    async def test_engine_error_skips_row_and_captures_to_sentry(self) -> None:
        """Engine returns (None, None): row stays NULL, Sentry context has bounded fields only.

        Information-disclosure mitigation (T-78-18): context MUST NOT contain pgn, user_id, fen.
        """
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="chess.com", username="alice")

        mock_evaluate = AsyncMock(return_value=(None, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-error-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        endgame_plies = _make_endgame_plies(count=8, endgame_class=_EC_ROOK, eval_cp=None)
        processing_result = _make_processing_result(endgame_plies)

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-error-1",
                "pgn": _CHESS_COM_PGN,
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
            patch("app.services.import_service.sentry_sdk.set_context") as mock_set_ctx,
            patch("app.services.import_service.sentry_sdk.set_tag"),
            patch("app.services.import_service.sentry_sdk.capture_message"),
        ):
            await import_service.run_import(job_id)

        # Sentry context must be set (D-11 pattern)
        assert mock_set_ctx.call_count >= 1, (
            "Expected sentry_sdk.set_context to be called when engine returns (None, None)"
        )

        # Find the 'eval' context call
        eval_ctx_calls = [
            c for c in mock_set_ctx.call_args_list
            if c.args and c.args[0] == "eval"
        ]
        assert len(eval_ctx_calls) >= 1, (
            "Expected sentry_sdk.set_context('eval', {...}) call"
        )

        ctx_payload = eval_ctx_calls[0].args[1]

        # Required bounded fields (game_id, ply, endgame_class)
        assert "game_id" in ctx_payload, "Sentry context must contain game_id"
        assert "ply" in ctx_payload, "Sentry context must contain ply"
        assert "endgame_class" in ctx_payload, "Sentry context must contain endgame_class"

        # Information-disclosure mitigation (T-78-18): no PGN, no user_id, no fen
        assert "pgn" not in ctx_payload, (
            "SECURITY: Sentry context must NOT contain pgn (T-78-18)"
        )
        assert "user_id" not in ctx_payload, (
            "SECURITY: Sentry context must NOT contain user_id (T-78-18)"
        )
        assert "fen" not in ctx_payload, (
            "SECURITY: Sentry context must NOT contain fen (T-78-18)"
        )

        # No eval UPDATE should be issued for the row (D-11: skip, leave NULL)
        execute_calls = mock_session.execute.call_args_list
        for call in execute_calls:
            if hasattr(call.args[0], "is_update") and call.args[0].is_update:
                stmt_str = str(call.args[0])
                assert "eval_cp" not in stmt_str, (
                    "No eval_cp UPDATE should be issued when engine returns (None, None). "
                    f"Found: {stmt_str}"
                )

        import_service._jobs.clear()


# ---------------------------------------------------------------------------
# Test 4: no endgame — engine NOT called
# ---------------------------------------------------------------------------


class TestImportEvalNoEndgame:
    async def test_short_game_zero_engine_calls(self) -> None:
        """Game with 2 non-endgame plies (endgame_class=None): engine.evaluate never called."""
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="chess.com", username="alice")

        mock_evaluate = AsyncMock(return_value=(0, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-short-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        non_endgame_plies: list[dict[str, Any]] = [
            {
                "ply": 0, "white_hash": 1, "black_hash": 2, "full_hash": 3,
                "move_san": "e4", "clock_seconds": None,
                "eval_cp": None, "eval_mate": None,
                "material_count": 7800,
                "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0, "has_opposite_color_bishops": False,
                "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                "endgame_class": None,
            },
            {
                "ply": 1, "white_hash": 4, "black_hash": 5, "full_hash": 6,
                "move_san": None, "clock_seconds": None,
                "eval_cp": None, "eval_mate": None,
                "material_count": 7800,
                "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0, "has_opposite_color_bishops": False,
                "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                "endgame_class": None,
            },
        ]
        processing_result: dict[str, Any] = {
            "plies": non_endgame_plies,
            "result_fen": None,
            "move_count": 1,
        }

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-short-1",
                "pgn": "1. e4 e5 1/2-1/2",
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
        ):
            await import_service.run_import(job_id)

        assert mock_evaluate.call_count == 0, (
            f"Engine should NOT be called for a non-endgame game. "
            f"Got {mock_evaluate.call_count} calls."
        )

        import_service._jobs.clear()

    async def test_below_threshold_endgame_plies_no_engine_call(self) -> None:
        """Game has 3 endgame plies < ENDGAME_PLY_THRESHOLD=6: engine NOT called."""
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="chess.com", username="alice")

        mock_evaluate = AsyncMock(return_value=(0, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-few-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        # 3 endgame plies < threshold (6) — no span entry created
        few_plies = _make_endgame_plies(count=3, endgame_class=_EC_ROOK, eval_cp=None)
        processing_result = _make_processing_result(few_plies)

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-few-1",
                "pgn": _CHESS_COM_PGN,
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
        ):
            await import_service.run_import(job_id)

        assert mock_evaluate.call_count == 0, (
            f"Engine should NOT be called when endgame ply count ({3}) < "
            f"ENDGAME_PLY_THRESHOLD ({_ENDGAME_PLY_THRESHOLD}). "
            f"Got {mock_evaluate.call_count} calls."
        )

        import_service._jobs.clear()


# ---------------------------------------------------------------------------
# Test 5: multi-class span entries — engine called once per class
# ---------------------------------------------------------------------------


class TestImportEvalMultiClass:
    async def test_two_class_span_entries_two_evaluations(self) -> None:
        """Game with two endgame classes (each >= threshold): engine called exactly once per class."""
        import app.services.import_service as import_service

        import_service._jobs.clear()
        job_id = import_service.create_job(user_id=1, platform="chess.com", username="alice")

        mock_evaluate = AsyncMock(return_value=(200, None))
        mock_session = _make_mock_session()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(999, "game-multi-1")]
        mock_session.execute.return_value = select_result
        mock_maker = _mock_session_maker(mock_session)

        # 8 rook plies + 8 pawn plies = two distinct endgame classes, each >= threshold
        two_class_plies = _make_two_class_plies()
        processing_result = _make_processing_result(two_class_plies)

        async def _yield_one(*args: Any, **kwargs: Any) -> Any:
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-multi-1",
                "pgn": _CHESS_COM_PGN,
                "user_id": 1,
            }

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.import_service.import_job_repository.create_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.import_job_repository.update_import_job",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_one,
            ),
            patch(
                "app.services.import_service.httpx.AsyncClient",
                return_value=_mock_http_ctx(),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=processing_result,
            ),
            patch(
                "app.services.import_service.engine_service.evaluate",
                new=mock_evaluate,
            ),
        ):
            await import_service.run_import(job_id)

        # Two distinct endgame classes → exactly 2 engine calls (one per span entry)
        assert mock_evaluate.call_count == 2, (
            f"Expected exactly 2 engine.evaluate calls for two distinct endgame classes, "
            f"got {mock_evaluate.call_count}"
        )

        import_service._jobs.clear()
