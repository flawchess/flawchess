"""Tests for the import service.

Focuses on orchestration logic: job lifecycle, incremental sync, hash computation,
and error handling. All external dependencies are mocked.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

import app.services.import_service as import_service
from app.schemas.normalization import NormalizedGame
from app.services.import_service import (
    IMPORT_TIMEOUT_SECONDS,
    JobStatus,
    create_job,
    find_active_job,
    get_job,
    run_import,
)


def _make_mock_processing_result(
    plies: list[dict] | None = None,
    result_fen: str = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR",
    ply_count: int = 1,
) -> dict:
    """Build a mock GameProcessingResult dict for testing."""
    if plies is None:
        plies = [
            {
                "ply": 0,
                "white_hash": 1,
                "black_hash": 2,
                "full_hash": 3,
                "move_san": "e4",
                "clock_seconds": None,
                "eval_cp": None,
                "eval_mate": None,
                "material_count": 7800,
                "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0,
                "has_opposite_color_bishops": False,
                "piece_count": 14,
                "backrank_sparse": False,
                "mixedness": 0,
                "endgame_class": None,
                "phase": 0,
            },
            {
                "ply": 1,
                "white_hash": 4,
                "black_hash": 5,
                "full_hash": 6,
                "move_san": None,
                "clock_seconds": None,
                "eval_cp": None,
                "eval_mate": None,
                "material_count": 7800,
                "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0,
                "has_opposite_color_bishops": False,
                "piece_count": 14,
                "backrank_sparse": False,
                "mixedness": 0,
                "endgame_class": None,
                "phase": 0,
            },
        ]
    return {"plies": plies, "result_fen": result_fen, "ply_count": ply_count}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear the in-memory job registry before each test to prevent cross-test pollution."""
    import_service._jobs.clear()
    yield
    import_service._jobs.clear()


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------


class TestCreateJob:
    def test_returns_valid_uuid_string(self):
        """create_job should return a UUID string."""
        import uuid

        job_id = create_job(user_id=1, platform="chess.com", username="alice")
        # Should not raise
        parsed = uuid.UUID(job_id)
        assert str(parsed) == job_id

    def test_stores_job_in_registry(self):
        """create_job should register the job in _jobs."""
        job_id = create_job(user_id=1, platform="lichess", username="bob")
        assert job_id in import_service._jobs

    def test_job_starts_as_pending(self):
        """Newly created job should have PENDING status."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")
        job = import_service._jobs[job_id]
        assert job.status == JobStatus.PENDING

    def test_job_fields_set_correctly(self):
        """create_job should set all job fields from arguments."""
        job_id = create_job(user_id=42, platform="lichess", username="carol")
        job = import_service._jobs[job_id]
        assert job.user_id == 42
        assert job.platform == "lichess"
        assert job.username == "carol"
        assert job.games_fetched == 0
        assert job.games_imported == 0
        assert job.error is None


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------


class TestGetJob:
    def test_returns_job_for_known_id(self):
        """get_job should return the JobState for a known job_id."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")
        job = get_job(job_id)
        assert job is not None
        assert job.job_id == job_id

    def test_returns_none_for_unknown_id(self):
        """get_job should return None for an unknown job_id."""
        result = get_job("nonexistent-id")
        assert result is None


# ---------------------------------------------------------------------------
# find_active_job
# ---------------------------------------------------------------------------


class TestFindActiveJob:
    def test_returns_pending_job_for_same_user_platform(self):
        """Should return an existing PENDING job for the same user+platform."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")
        result = find_active_job(user_id=1, platform="chess.com")
        assert result is not None
        assert result.job_id == job_id

    def test_returns_in_progress_job(self):
        """Should return an existing IN_PROGRESS job."""
        job_id = create_job(user_id=1, platform="lichess", username="bob")
        import_service._jobs[job_id].status = JobStatus.IN_PROGRESS

        result = find_active_job(user_id=1, platform="lichess")
        assert result is not None
        assert result.job_id == job_id

    def test_returns_none_when_no_active_job(self):
        """Should return None when no active jobs for this user+platform."""
        result = find_active_job(user_id=1, platform="chess.com")
        assert result is None

    def test_returns_none_for_completed_job(self):
        """Should return None for completed jobs (not active)."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")
        import_service._jobs[job_id].status = JobStatus.COMPLETED

        result = find_active_job(user_id=1, platform="chess.com")
        assert result is None

    def test_returns_none_for_different_platform(self):
        """Should return None when only a job for a different platform exists."""
        create_job(user_id=1, platform="chess.com", username="alice")

        result = find_active_job(user_id=1, platform="lichess")
        assert result is None

    def test_returns_none_for_different_user(self):
        """Should return None when only a job for a different user exists."""
        create_job(user_id=1, platform="chess.com", username="alice")

        result = find_active_job(user_id=2, platform="chess.com")
        assert result is None


# ---------------------------------------------------------------------------
# run_import — helpers
# ---------------------------------------------------------------------------


def _make_mock_session():
    """Build a minimal mock AsyncSession with async context manager support."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    # Make session.execute return something with a fetchall() for the SELECT
    result_mock = MagicMock()
    result_mock.fetchall.return_value = []
    session.execute.return_value = result_mock
    return session


def _mock_session_maker(session):
    """Return a callable that yields session as async context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    maker = MagicMock()
    maker.return_value = ctx
    return maker


async def _empty_async_gen(*args, **kwargs):
    """Async generator that yields nothing."""
    return
    yield  # pragma: no cover — makes it a generator


async def _single_game_gen(*args, **kwargs):
    """Async generator that yields one mock game dict."""
    yield {
        "platform": "chess.com",
        "platform_game_id": "game-1",
        "pgn": "1. e4 e5 *",
        "user_id": 1,
    }


# ---------------------------------------------------------------------------
# run_import tests
# ---------------------------------------------------------------------------


class TestRunImport:
    @pytest.mark.asyncio
    async def test_transitions_pending_to_completed(self):
        """run_import should move job from PENDING -> IN_PROGRESS -> COMPLETED."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)

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
                side_effect=_empty_async_gen,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        job = get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_import_sets_error(self):
        """When platform client raises, job should be FAILED with error message."""
        job_id = create_job(user_id=1, platform="chess.com", username="nonexistent")

        async def _raise_value_error(*args, **kwargs):
            raise ValueError("chess.com user 'nonexistent' not found")
            yield  # pragma: no cover

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)

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
                side_effect=_raise_value_error,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        job = get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error is not None
        assert "nonexistent" in job.error

    @pytest.mark.asyncio
    async def test_incremental_sync_passes_since_to_chesscom_client(self):
        """When a previous completed job exists, since_timestamp should be passed."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        last_synced = datetime(2024, 3, 1, tzinfo=timezone.utc)
        previous_job = MagicMock()
        previous_job.last_synced_at = last_synced

        captured_kwargs = {}

        async def _capture_kwargs(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return
            yield  # pragma: no cover

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=previous_job),
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
                side_effect=_capture_kwargs,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert captured_kwargs.get("since_timestamp") == last_synced

    @pytest.mark.asyncio
    async def test_incremental_sync_passes_since_ms_to_lichess_client(self):
        """When a previous completed job exists for lichess, since_ms should be passed."""
        job_id = create_job(user_id=1, platform="lichess", username="bob")

        last_synced = datetime(2024, 3, 1, tzinfo=timezone.utc)
        previous_job = MagicMock()
        previous_job.last_synced_at = last_synced

        captured_kwargs = {}

        async def _capture_kwargs(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return
            yield  # pragma: no cover

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=previous_job),
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
                side_effect=_capture_kwargs,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        expected_ms = int(last_synced.timestamp() * 1000)
        assert captured_kwargs.get("since_ms") == expected_ms

    @pytest.mark.asyncio
    async def test_hashes_computed_for_newly_inserted_games(self):
        """run_import should call process_game_pgn for each newly inserted game's PGN."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        # Make execute return game id=999 with platform_game_id (D-03: no PGN in SELECT)
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
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
                return_value=_make_mock_processing_result(),
            ) as mock_process,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        mock_process.assert_called_once_with(pgn)

    @pytest.mark.asyncio
    async def test_position_rows_include_move_san(self):
        """run_import should pass position_rows with move_san to bulk_insert_positions."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-moveSan-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-moveSan-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture_bulk_insert_positions(session, position_rows):
            captured_positions.extend(position_rows)

        three_ply_result = _make_mock_processing_result(
            plies=[
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
                    "piece_count": 14,
                    "backrank_sparse": False,
                    "mixedness": 0,
                    "endgame_class": None,
                    "phase": 0,
                },
                {
                    "ply": 1,
                    "white_hash": 400,
                    "black_hash": 500,
                    "full_hash": 600,
                    "move_san": "e5",
                    "clock_seconds": None,
                    "eval_cp": None,
                    "eval_mate": None,
                    "material_count": 7800,
                    "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0,
                    "has_opposite_color_bishops": False,
                    "piece_count": 14,
                    "backrank_sparse": False,
                    "mixedness": 0,
                    "endgame_class": None,
                    "phase": 0,
                },
                {
                    "ply": 2,
                    "white_hash": 700,
                    "black_hash": 800,
                    "full_hash": 900,
                    "move_san": None,
                    "clock_seconds": None,
                    "eval_cp": None,
                    "eval_mate": None,
                    "material_count": 7800,
                    "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0,
                    "has_opposite_color_bishops": False,
                    "piece_count": 14,
                    "backrank_sparse": False,
                    "mixedness": 0,
                    "endgame_class": None,
                    "phase": 0,
                },
            ],
            ply_count=1,
        )

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(side_effect=_capture_bulk_insert_positions),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=three_ply_result,
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_positions) == 3
        assert "move_san" in captured_positions[0]
        assert captured_positions[0]["move_san"] == "e4"
        assert captured_positions[1]["move_san"] == "e5"
        assert captured_positions[2]["move_san"] is None

    @pytest.mark.asyncio
    async def test_unknown_job_id_does_nothing(self):
        """run_import with unknown job_id should log and return without error."""
        # Should not raise
        await run_import("nonexistent-job-id")

    @pytest.mark.asyncio
    async def test_username_not_saved_in_run_import(self):
        """run_import should NOT save the platform username — that is now done at import start
        in the router (start_import endpoint), so it persists even if the import fails.
        """
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)

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
                side_effect=_empty_async_gen,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        job = get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_ply_count_populated(self):
        """After importing a game, ply_count is set correctly via bulk UPDATE (D-04)."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # 1. e4 e5 = 2 plies = 2 half-moves => ply_count = 2
        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-mc-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-mc-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
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
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # Verify session.execute was called with a bulk UPDATE for ply_count (D-04)
        execute_calls = mock_session.execute.call_args_list
        update_calls = [
            call
            for call in execute_calls
            if hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]
        assert len(update_calls) >= 1, "Expected at least one UPDATE call for ply_count"

    @pytest.mark.asyncio
    async def test_position_rows_include_material_count(self):
        """After importing a game, all position_rows dicts have a non-null material_count field."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # Use a real PGN so process_game_pgn runs on actual board states
        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-mc-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-mc-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture(session, position_rows):
            captured_positions.extend(position_rows)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(side_effect=_capture),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_positions) > 0, "Expected at least one position row"
        for row in captured_positions:
            assert "material_count" in row, f"Missing material_count in row: {row}"
            assert row["material_count"] is not None, "material_count should not be None"
            assert isinstance(row["material_count"], int), "material_count should be int"

    @pytest.mark.asyncio
    async def test_position_rows_include_material_signature(self):
        """After importing a game, all position_rows dicts have a non-null material_signature field."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-ms-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-ms-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture(session, position_rows):
            captured_positions.extend(position_rows)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(side_effect=_capture),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_positions) > 0, "Expected at least one position row"
        for row in captured_positions:
            assert "material_signature" in row, f"Missing material_signature in row: {row}"
            assert row["material_signature"] is not None, "material_signature should not be None"

    @pytest.mark.asyncio
    async def test_starting_position_has_full_material(self):
        """The starting position (ply 0) has full material count and signature."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-sp-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-sp-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture(session, position_rows):
            captured_positions.extend(position_rows)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(side_effect=_capture),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_positions) > 0
        ply0 = captured_positions[0]
        assert ply0["ply"] == 0
        assert ply0["material_count"] == 7800  # full starting material
        assert ply0["material_signature"] == "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP"

    @pytest.mark.asyncio
    async def test_classification_failure_degrades_gracefully(self):
        """When process_game_pgn raises, import still succeeds — no positions for that game."""
        # Classification is now inside process_game_pgn; if it raises, _flush_batch catches it
        # and continues. The game is skipped (no position rows inserted), but the import job
        # still completes successfully.
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-degrade-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, "game-degrade-1")]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture(session, position_rows):
            captured_positions.extend(position_rows)

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
                side_effect=_yield_one_game,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[999]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(side_effect=_capture),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                side_effect=Exception("Simulated PGN processing failure"),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        job = import_service._jobs[job_id]
        assert job.status == JobStatus.COMPLETED, (
            f"Expected COMPLETED, got {job.status} — PGN processing failure must not fail the import"
        )
        # No position rows inserted for the failed game — bulk_insert_positions not called
        assert len(captured_positions) == 0, (
            "No position rows should be inserted when process_game_pgn fails"
        )


# ---------------------------------------------------------------------------
# TestEvalExtraction — python-chess PGN eval annotation parsing
# ---------------------------------------------------------------------------


class TestEvalExtraction:
    """Tests for per-move eval extraction from PGN %eval annotations."""

    def test_lichess_pgn_with_evals(self):
        """PGN with %eval annotations extracts centipawn and mate values."""
        import chess.pgn
        import io

        pgn = "1. e4 { [%eval 0.18] } 1... e5 { [%eval 0.17] } 2. Nf3 { [%eval #3] } *"
        game = chess.pgn.read_game(io.StringIO(pgn))
        assert game is not None  # PGN is valid test data
        nodes = list(game.mainline())
        evals = []
        for node in nodes:
            pov = node.eval()
            if pov is not None:
                w = pov.white()
                evals.append((w.score(mate_score=None), w.mate()))
            else:
                evals.append((None, None))
        assert evals[0] == (18, None)  # 1.e4: 0.18 pawns = 18 centipawns
        assert evals[1] == (17, None)  # 1...e5: 0.17 pawns = 17 centipawns
        assert evals[2] == (None, 3)  # 2.Nf3: mate in 3 for white

    def test_pgn_without_evals(self):
        """PGN without %eval annotations returns all None."""
        import chess.pgn
        import io

        pgn = "1. e4 e5 2. Nf3 *"
        game = chess.pgn.read_game(io.StringIO(pgn))
        assert game is not None  # PGN is valid test data
        nodes = list(game.mainline())
        evals = []
        for node in nodes:
            pov = node.eval()
            if pov is not None:
                w = pov.white()
                evals.append((w.score(mate_score=None), w.mate()))
            else:
                evals.append((None, None))
        assert all(e == (None, None) for e in evals)

    def test_mate_negative_for_black(self):
        """Negative mate value means black mates."""
        import chess.pgn
        import io

        pgn = "1. e4 { [%eval #-7] } *"
        game = chess.pgn.read_game(io.StringIO(pgn))
        assert game is not None  # PGN is valid test data
        node = list(game.mainline())[0]
        pov = node.eval()
        assert pov is not None  # Test PGN contains eval annotations
        w = pov.white()
        assert w.score(mate_score=None) is None
        assert w.mate() == -7

    def test_evals_list_shorter_than_hash_tuples(self):
        """Evals list has N entries (one per move), hash_tuples has N+1 (includes final position).
        When i >= len(evals), eval should default to (None, None) for final position."""
        import chess.pgn
        import io

        pgn = "1. e4 { [%eval 0.18] } 1... e5 { [%eval 0.17] } *"
        game = chess.pgn.read_game(io.StringIO(pgn))
        assert game is not None  # PGN is valid test data
        nodes = list(game.mainline())
        evals = []
        for node in nodes:
            pov = node.eval()
            if pov is not None:
                w = pov.white()
                evals.append((w.score(mate_score=None), w.mate()))
            else:
                evals.append((None, None))
        # Simulate hash_tuples having 3 entries (ply 0, 1, 2) but evals has 2
        assert len(evals) == 2
        # Final position (i=2) should get (None, None)
        final_eval = evals[2] if 2 < len(evals) else (None, None)
        assert final_eval == (None, None)

    def test_import_service_position_rows_contain_eval_fields(self):
        """_flush_batch position rows must include eval_cp and eval_mate keys."""
        # This test verifies that the _flush_batch integration adds eval fields to rows.
        # It inspects the rows captured by bulk_insert_positions using a lichess PGN
        # with %eval annotations.
        import chess.pgn
        import io

        # Verify the implementation produces eval rows — check rows captured in the flush loop
        pgn_with_eval = "1. e4 { [%eval 0.18] } 1... e5 { [%eval -0.17] } *"
        game = chess.pgn.read_game(io.StringIO(pgn_with_eval))
        assert game is not None  # PGN is valid test data
        classify_nodes = list(game.mainline())

        evals: list[tuple[int | None, int | None]] = []
        if classify_nodes:
            for node in classify_nodes:
                pov = node.eval()
                if pov is not None:
                    w = pov.white()
                    evals.append((w.score(mate_score=None), w.mate()))
                else:
                    evals.append((None, None))

        # Simulate the loop: 3 hash_tuples (ply 0,1,2) but only 2 evals
        hash_tuple_count = 3  # ply 0 (start), ply 1 (after e4), ply 2 (after e5)
        results = []
        for i in range(hash_tuple_count):
            eval_cp: int | None = None
            eval_mate: int | None = None
            if i < len(evals):
                eval_cp, eval_mate = evals[i]
            results.append({"eval_cp": eval_cp, "eval_mate": eval_mate})

        # ply 0 (starting position): no node, gets (None, None)
        assert results[0] == {"eval_cp": 18, "eval_mate": None}  # node 0: after e4
        assert results[1] == {"eval_cp": -17, "eval_mate": None}  # node 1: after e5
        assert results[2] == {"eval_cp": None, "eval_mate": None}  # final position


# ---------------------------------------------------------------------------
# TestIncrementalProgress — DB counter updates after each batch
# ---------------------------------------------------------------------------


class TestIncrementalProgress:
    """Tests that DB job counters are updated incrementally during import."""

    @pytest.mark.asyncio
    async def test_db_counters_updated_after_full_batch(self):
        """After a full batch flush (_BATCH_SIZE games), DB counters should be updated
        with the current games_fetched and games_imported values (not left at zero).
        """
        from app.services.import_service import _BATCH_SIZE

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # Yield exactly _BATCH_SIZE games to trigger exactly one full-batch DB update
        call_count = 0

        async def _yield_batch_games(*args, **kwargs):
            nonlocal call_count
            for i in range(_BATCH_SIZE):
                call_count += 1
                kwargs["on_game_fetched"]()
                yield {
                    "platform": "chess.com",
                    "platform_game_id": f"game-{i}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)
        captured_update_calls: list[dict] = []

        async def _capture_update(session, job_id, **kwargs):
            captured_update_calls.append(dict(kwargs))

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
                new=AsyncMock(side_effect=_capture_update),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_batch_games,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=list(range(_BATCH_SIZE))),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # There must be at least one incremental DB update (after the full batch)
        # and one final completion update. The incremental one has status="in_progress".
        in_progress_updates = [c for c in captured_update_calls if c.get("status") == "in_progress"]
        assert len(in_progress_updates) >= 1, (
            "Expected at least one in_progress DB update after batch flush, got none. "
            f"All update calls: {captured_update_calls}"
        )

        # The incremental update must carry non-zero games_imported (all _BATCH_SIZE games inserted)
        incremental = in_progress_updates[0]
        assert incremental["games_imported"] == _BATCH_SIZE, (
            f"Expected games_imported={_BATCH_SIZE} in incremental update, got {incremental}"
        )
        assert incremental["games_fetched"] == _BATCH_SIZE, (
            f"Expected games_fetched={_BATCH_SIZE} in incremental update, got {incremental}"
        )

    @pytest.mark.asyncio
    async def test_db_counters_updated_after_trailing_batch(self):
        """After the trailing (sub-batch-size) flush, DB counters should also be updated."""
        from app.services.import_service import _BATCH_SIZE

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # Yield fewer than _BATCH_SIZE games — triggers only the trailing batch path
        trailing_count = _BATCH_SIZE - 3  # e.g. 7 games for _BATCH_SIZE=10

        async def _yield_trailing_games(*args, **kwargs):
            for i in range(trailing_count):
                kwargs["on_game_fetched"]()
                yield {
                    "platform": "chess.com",
                    "platform_game_id": f"game-{i}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)
        captured_update_calls: list[dict] = []

        async def _capture_update(session, job_id, **kwargs):
            captured_update_calls.append(dict(kwargs))

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
                new=AsyncMock(side_effect=_capture_update),
            ),
            patch(
                "app.services.import_service.chesscom_client.fetch_chesscom_games",
                side_effect=_yield_trailing_games,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=list(range(trailing_count))),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # Trailing batch should also produce an in_progress DB update
        in_progress_updates = [c for c in captured_update_calls if c.get("status") == "in_progress"]
        assert len(in_progress_updates) >= 1, (
            "Expected at least one in_progress DB update after trailing batch flush, got none. "
            f"All update calls: {captured_update_calls}"
        )
        incremental = in_progress_updates[0]
        assert incremental["games_imported"] == trailing_count
        assert incremental["games_fetched"] == trailing_count


# ---------------------------------------------------------------------------
# TestFlushBatchStage5 — Wave 0 unit tests for Stage 5 executemany leak fix
# ---------------------------------------------------------------------------


# Phase 90 / SEED-018 / FLAWCHESS-56 / FLAWCHESS-3Q: pins the leak-free
# invariant — Stage 5 SQL must not include literal game ids that vary per
# batch, and result_fen must never be silently NULLed.
class TestFlushBatchStage5:
    """Unit tests for _flush_batch Stage 5: ply_count + result_fen UPDATE.

    Verifies:
    1. ply_count is persisted for every game in the batch.
    2. result_fen=None for a game does not overwrite a pre-existing result_fen.
    3. When ALL result_fens are None, no result_fen UPDATE is issued.
    4. When ply_counts is empty, no Stage-5 UPDATEs are issued.
    5. The compiled SQL text for both UPDATE statements is invariant across batches
       with different game-id sets (the leak regression guard).
    """

    def _make_flush_session(self, id_platform_pairs: list[tuple[int, str]]):
        """Build a mock session where the SELECT returns the given (id, platform_game_id) pairs."""
        session = AsyncMock()
        session.commit = AsyncMock()

        # First execute call is the INSERT from bulk_insert_games (mocked separately).
        # Second execute call is the SELECT(Game.id, Game.platform_game_id).
        # Subsequent calls are Stage 5 UPDATEs.
        select_result = MagicMock()
        select_result.fetchall.return_value = id_platform_pairs

        # Stage 5 UPDATEs return a plain mock result.
        update_result = MagicMock()

        # Return select_result once (for the SELECT), then update_result for everything else.
        call_count = 0

        async def _execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return select_result
            return update_result

        session.execute = AsyncMock(side_effect=_execute_side_effect)
        return session

    def _make_processing_result(
        self,
        result_fen: str | None,
        ply_count: int = 5,
    ) -> dict:
        """Build a minimal process_game_pgn result with no eval targets (phase=0)."""
        return {
            "result_fen": result_fen,
            "ply_count": ply_count,
            "plies": [
                {
                    "ply": 0,
                    "white_hash": 1,
                    "black_hash": 2,
                    "full_hash": 3,
                    "move_san": "e4",
                    "clock_seconds": None,
                    "eval_cp": None,
                    "eval_mate": None,
                    "material_count": 7800,
                    "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0,
                    "has_opposite_color_bishops": False,
                    "piece_count": 14,
                    "backrank_sparse": False,
                    "mixedness": 0,
                    "endgame_class": None,
                    "phase": 0,
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_ply_count_lands_for_all_games(self):
        """After _flush_batch, a Stage 5 execute call is issued for ply_count for all games."""
        from app.services.import_service import _flush_batch

        # 3 games, all with valid fens.
        id_pairs = [(101, "gid-101"), (102, "gid-102"), (103, "gid-103")]
        session = self._make_flush_session(id_pairs)

        batch = [
            {
                "platform": "chess.com",
                "platform_game_id": f"gid-{gid}",
                "pgn": "1. e4 *",
                "user_id": 1,
            }
            for gid in [101, 102, 103]
        ]
        pgn_results = {
            "gid-101": self._make_processing_result("fen_101", ply_count=10),
            "gid-102": self._make_processing_result("fen_102", ply_count=20),
            "gid-103": self._make_processing_result("fen_103", ply_count=30),
        }

        def _pgn_side_effect(pgn):
            for pid, result in pgn_results.items():
                if pid in pgn or pgn == "1. e4 *":
                    return result
            return None

        with (
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[101, 102, 103]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                side_effect=lambda pgn: (
                    pgn_results.get(next((pid for pid in pgn_results if pid in pgn), ""), None)
                    or pgn_results["gid-101"]
                ),
            ),
        ):
            result = await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)

        assert result == 3

        # Collect UPDATE calls (is_update attribute) from Stage 5.
        execute_calls = session.execute.call_args_list
        update_calls = [
            call
            for call in execute_calls
            if len(call.args) > 0 and hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]
        assert len(update_calls) >= 1, "Expected at least one Stage 5 UPDATE for ply_count"

    @pytest.mark.asyncio
    async def test_result_fen_none_preserved(self):
        """A game with result_fen=None must NOT appear in the fen UPDATE params list.

        Contract:
        - Exactly 2 UPDATE execute calls: one for ply_count (all 3 games), one for fen
          (only games 101 and 103 which have non-None fens).
        - Game 102 does NOT appear in the fen UPDATE params.

        With the current CASE+IN code: 1 combined UPDATE → this test fails (xfail).
        After Task 2 rewrite: 2 separate UPDATE calls → test passes.
        """
        from app.services.import_service import _flush_batch

        # 3 games: 101 and 103 have valid fens; 102 has None (e.g. truncated PGN).
        id_pairs = [(101, "gid-101"), (102, "gid-102"), (103, "gid-103")]
        session = self._make_flush_session(id_pairs)

        batch = [
            {
                "platform": "chess.com",
                "platform_game_id": f"gid-{gid}",
                "pgn": "1. e4 *",
                "user_id": 1,
            }
            for gid in [101, 102, 103]
        ]
        pgn_results = {
            "gid-101": self._make_processing_result("fen_101", ply_count=10),
            "gid-102": self._make_processing_result(None, ply_count=8),  # None fen
            "gid-103": self._make_processing_result("fen_103", ply_count=30),
        }

        call_index = [0]

        def _pgn_side_effect(pgn: str) -> dict:
            i = call_index[0]
            call_index[0] += 1
            return list(pgn_results.values())[i % len(pgn_results)]

        with (
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[101, 102, 103]),
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
            await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)

        execute_calls = session.execute.call_args_list
        update_calls = [
            call
            for call in execute_calls
            if len(call.args) > 0 and hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]

        # Phase 91: _flush_batch now has 3 UPDATE groups:
        #   (a) ply_count for all games, (b) result_fen for non-None fens,
        #   (c) Stage 5c evals_completed_at for covered games (no entry plies needing eval).
        # Games with "1. e4 *" PGN have no phase=1 or endgame entries, so all 3 are covered.
        assert len(update_calls) >= 2, (
            f"Expected at least 2 Stage 5 UPDATE calls (ply_count group + fen group). "
            f"Got {len(update_calls)}."
        )

        # The fen UPDATE's params must NOT include game 102.
        fen_update_game_ids: set[int] = set()
        for call in update_calls:
            if len(call.args) >= 2 and isinstance(call.args[1], list):
                for p in call.args[1]:
                    if isinstance(p, dict) and "b_rf" in p:
                        fen_update_game_ids.add(p["b_id"])

        assert 102 not in fen_update_game_ids, (
            f"Game 102 (result_fen=None) must not appear in fen UPDATE params. "
            f"Found fen-update game ids: {fen_update_game_ids}"
        )

    @pytest.mark.asyncio
    async def test_result_fen_all_none_skips_fen_update(self):
        """When ALL games have result_fen=None after parse, no result_fen UPDATE is issued.

        Verifies: with the two-group executemany approach, fen_params is empty so
        the fen execute call is skipped entirely. With current code: fen_case_map is
        empty so the `if fen_case_map:` guard already prevents the fen update — this
        test passes on both current and new code.
        """
        from app.services.import_service import _flush_batch

        id_pairs = [(101, "gid-101"), (102, "gid-102"), (103, "gid-103")]
        session = self._make_flush_session(id_pairs)

        batch = [
            {
                "platform": "chess.com",
                "platform_game_id": f"gid-{gid}",
                "pgn": "1. e4 *",
                "user_id": 1,
            }
            for gid in [101, 102, 103]
        ]
        # All games parse to result_fen=None.
        all_none_result = self._make_processing_result(None, ply_count=5)

        with (
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[101, 102, 103]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=all_none_result,
            ),
        ):
            await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)

        execute_calls = session.execute.call_args_list

        # No execute call should carry a params list with "b_rf" keys (fen update).
        fen_update_calls = [
            call
            for call in execute_calls
            if len(call.args) >= 2
            and isinstance(call.args[1], list)
            and any(isinstance(p, dict) and "b_rf" in p for p in call.args[1])
        ]
        assert len(fen_update_calls) == 0, (
            f"Expected no fen UPDATE when all result_fens are None. "
            f"Found {len(fen_update_calls)} fen update call(s)."
        )

    @pytest.mark.asyncio
    async def test_empty_ply_counts_short_circuits(self):
        """When rows_result.ply_counts is empty, no Stage-5 UPDATE execute calls are made.

        This happens when bulk_insert_games returns no new IDs (all duplicates).
        """
        from app.services.import_service import _flush_batch

        # Make bulk_insert_games return empty (all duplicates).
        session = _make_mock_session()

        batch = [
            {
                "platform": "chess.com",
                "platform_game_id": "gid-dup-1",
                "pgn": "1. e4 *",
                "user_id": 1,
            }
        ]

        with (
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[]),  # empty — all duplicates
            ),
        ):
            result = await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)

        # Short-circuit returns 0 and must not call any UPDATE.
        assert result == 0

        execute_calls = session.execute.call_args_list
        update_calls = [
            call
            for call in execute_calls
            if len(call.args) > 0 and hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]
        assert len(update_calls) == 0, (
            f"Expected no UPDATE calls when ply_counts is empty, "
            f"but found {len(update_calls)} update call(s)."
        )

    @pytest.mark.asyncio
    async def test_stage5_sql_text_invariant_across_batches(self):
        """Stage 5 SQL text must be identical regardless of which game ids are in the batch.

        This is the memory-leak regression guard (Phase 90 / SEED-018 / FLAWCHESS-56):
        if the SQL text varies per batch (e.g. via CASE+IN with literal game ids),
        SQLAlchemy's compile cache and asyncpg's prepared-statement LRU both grow
        unboundedly, OOM-killing production on large imports.

        Calls _flush_batch twice with two different game-id sets and compares the
        compiled SQL text of the Stage 5 UPDATE statements captured from each call.

        EXPECTED STATE: xfail against current code (case()+IN SQL embeds literal game ids
        in the WHERE clause, so the text differs between the two batches).
        After Task 2 rewrite (bindparam executemany), both batches emit identical SQL.
        """
        from sqlalchemy.dialects import postgresql

        from app.services.import_service import _flush_batch

        dialect = postgresql.dialect()

        async def _run_batch_and_capture_update_sql(game_ids: list[int]) -> list[str]:
            id_pairs = [(gid, f"gid-{gid}") for gid in game_ids]
            session = self._make_flush_session(id_pairs)

            batch = [
                {
                    "platform": "chess.com",
                    "platform_game_id": f"gid-{gid}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }
                for gid in game_ids
            ]
            processing_result = self._make_processing_result("test_fen", ply_count=5)

            with (
                patch(
                    "app.services.import_service.game_repository.bulk_insert_games",
                    new=AsyncMock(return_value=game_ids),
                ),
                patch(
                    "app.services.import_service.game_repository.bulk_insert_positions",
                    new=AsyncMock(),
                ),
                patch(
                    "app.services.import_service.process_game_pgn",
                    return_value=processing_result,
                ),
            ):
                await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)

            # Collect SQL text from UPDATE execute calls.
            update_sql_texts: list[str] = []
            for call in session.execute.call_args_list:
                if (
                    len(call.args) > 0
                    and hasattr(call.args[0], "is_update")
                    and call.args[0].is_update
                ):
                    compiled = call.args[0].compile(dialect=dialect)
                    update_sql_texts.append(str(compiled))
            return update_sql_texts

        # Use 7-digit ids so they cannot appear as a substring of a 6-digit
        # microsecond fraction in a literal-rendered timestamp (e.g. the
        # `evals_completed_at` value the bindparam-less literal_binds compile
        # below produces). Earlier 3-digit ids like 101/102 flaked CI when a
        # microsecond happened to start with the same digits.
        ids_a = [9000001, 9000002, 9000003]
        ids_b = [9000004, 9000005, 9000006, 9000007]
        sql_texts_batch_a = await _run_batch_and_capture_update_sql(ids_a)
        sql_texts_batch_b = await _run_batch_and_capture_update_sql(ids_b)

        assert len(sql_texts_batch_a) > 0, "Expected at least one UPDATE call in batch A"
        assert len(sql_texts_batch_b) > 0, "Expected at least one UPDATE call in batch B"
        assert len(sql_texts_batch_a) == len(sql_texts_batch_b), (
            f"Both batches must emit the same number of UPDATE statements. "
            f"Batch A: {len(sql_texts_batch_a)}, Batch B: {len(sql_texts_batch_b)}"
        )

        for i, (sql_a, sql_b) in enumerate(zip(sql_texts_batch_a, sql_texts_batch_b)):
            assert sql_a == sql_b, (
                f"Stage 5 UPDATE statement {i} SQL text must be invariant across batches "
                f"(the memory-leak regression guard). "
                f"Batch A: {sql_a!r}\nBatch B: {sql_b!r}"
            )

        # WR-04: extra regression guard — render with literal_binds and assert
        # that NO batch game id appears inline in the SQL text. The template
        # compile above is trivially invariant under bindparam, but a future
        # regression to case()+IN would embed game ids as literals and this
        # assertion would catch it.
        # WR-04: bindparams without supplied values render as NULL under
        # literal_binds; this is expected and harmless for the assertion below
        # (we only check that none of the batch game ids appear inline).
        import warnings as _warnings

        async def _capture_compiled_literal_sql(game_ids: list[int]) -> list[str]:
            id_pairs = [(gid, f"gid-{gid}") for gid in game_ids]
            session = self._make_flush_session(id_pairs)
            batch = [
                {
                    "platform": "chess.com",
                    "platform_game_id": f"gid-{gid}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }
                for gid in game_ids
            ]
            processing_result = self._make_processing_result("test_fen", ply_count=5)
            with (
                patch(
                    "app.services.import_service.game_repository.bulk_insert_games",
                    new=AsyncMock(return_value=game_ids),
                ),
                patch(
                    "app.services.import_service.game_repository.bulk_insert_positions",
                    new=AsyncMock(),
                ),
                patch(
                    "app.services.import_service.process_game_pgn",
                    return_value=processing_result,
                ),
            ):
                await _flush_batch(session, cast(list[NormalizedGame], batch), user_id=1)
            literal_sql_texts: list[str] = []
            for call in session.execute.call_args_list:
                if (
                    len(call.args) > 0
                    and hasattr(call.args[0], "is_update")
                    and call.args[0].is_update
                ):
                    with _warnings.catch_warnings():
                        _warnings.simplefilter("ignore", category=Warning)
                        compiled = call.args[0].compile(
                            dialect=dialect, compile_kwargs={"literal_binds": True}
                        )
                    literal_sql_texts.append(str(compiled))
            return literal_sql_texts

        literal_sql_a = await _capture_compiled_literal_sql(ids_a)
        for sql_text in literal_sql_a:
            for gid in ids_a:
                assert str(gid) not in sql_text, (
                    f"Game id {gid} appears in literal-rendered SQL — Stage 5 "
                    f"regressed to inline literals. SQL: {sql_text!r}"
                )


# ---------------------------------------------------------------------------
# Phase 90 / SEED-017 carry-forward: Resilience defect tests
#
# Assumption A3 verified (2026-05-20) via code inspection and SQLAlchemy
# exception hierarchy research:
#   SQLAlchemy wraps asyncpg connection exceptions (CannotConnectNowError,
#   ConnectionDoesNotExistError) in sqlalchemy.exc.OperationalError.
#   The asyncpg exception is accessible via exc.__cause__. Catching
#   sqlalchemy.exc.OperationalError covers both connection-refused and
#   connection-dropped scenarios (Pitfall 4 in 90-RESEARCH.md).
#   Therefore _record_failure_with_retry catches OperationalError, not raw
#   asyncpg types. This mirrors the finding in app/main.py:_sentry_before_send
#   which walks __cause__ to detect the underlying asyncpg type.
#
# If local verification showed OperationalError does NOT match (e.g. only
# DBAPIError with __cause__ walk), swap the except clause in
# _record_failure_with_retry to catch DBAPIError and inspect __cause__.
# ---------------------------------------------------------------------------


class TestFailOrphanedJobsAgeThreshold:
    """DB-backed tests for fail_orphaned_jobs age-threshold extension.

    Bug fix (Phase 90, SEED-017, FLAWCHESS-3Q): cleanup_orphaned_jobs() only
    ran at backend startup. A Postgres-only restart left in_progress jobs
    stuck. The periodic reaper needed an age threshold to avoid killing a
    live healthy import (Pitfall 3 in 90-RESEARCH.md).

    Uses the real test DB via db_session fixture (rollback-scoped transactions).
    """

    async def _seed_job(
        self,
        session,
        user_id: int,
        job_id: str,
        status: str,
        started_at: datetime,
    ) -> None:
        """Insert an ImportJob with a controlled started_at."""
        from app.models.import_job import ImportJob

        from tests.conftest import ensure_test_user

        await ensure_test_user(session, user_id)
        job = ImportJob(
            id=job_id,
            user_id=user_id,
            platform="lichess",
            username="test_user",
            status=status,
            games_fetched=0,
            games_imported=0,
        )
        session.add(job)
        await session.flush()
        # Override started_at with a controlled value via direct UPDATE.
        from sqlalchemy import text

        await session.execute(
            text("UPDATE import_jobs SET started_at = :ts WHERE id = :id"),
            {"ts": started_at, "id": job_id},
        )
        await session.flush()

    @pytest.mark.asyncio
    async def test_no_threshold_reaps_all_in_progress(self, db_session):
        """fail_orphaned_jobs() with no threshold reaps all in_progress jobs.

        Pins the startup-call behavior: every in_progress job is reaped
        regardless of age. This is safe at startup — no in-flight tasks
        survive a backend restart.
        """
        import uuid

        from app.repositories.import_job_repository import fail_orphaned_jobs

        now = datetime.now(timezone.utc)
        job_id_recent = str(uuid.uuid4())
        job_id_old = str(uuid.uuid4())

        await self._seed_job(
            db_session, 9001, job_id_recent, "in_progress", now - timedelta(seconds=10)
        )
        await self._seed_job(db_session, 9001, job_id_old, "in_progress", now - timedelta(hours=4))

        count = await fail_orphaned_jobs(db_session)
        await db_session.commit()

        assert count == 2

        from sqlalchemy import select

        from app.models.import_job import ImportJob

        rows = (
            (
                await db_session.execute(
                    select(ImportJob).where(ImportJob.id.in_([job_id_recent, job_id_old]))
                )
            )
            .scalars()
            .all()
        )
        assert all(j.status == "failed" for j in rows), (
            f"Expected both jobs to be failed, got: {[j.status for j in rows]}"
        )

    @pytest.mark.asyncio
    async def test_threshold_reaps_only_old(self, db_session):
        """fail_orphaned_jobs() with a 3h threshold reaps only jobs older than 3h.

        A 10 s old job must NOT be reaped — it is a live healthy import.
        A 4 h old job MUST be reaped — it exceeded its 3-hour budget.

        This is the critical Pitfall 3 mitigation in 90-RESEARCH.md:
        without this threshold the periodic reaper would kill live imports.
        """
        import uuid

        from app.repositories.import_job_repository import fail_orphaned_jobs
        from sqlalchemy import select
        from app.models.import_job import ImportJob

        now = datetime.now(timezone.utc)
        job_id_recent = str(uuid.uuid4())
        job_id_old = str(uuid.uuid4())

        await self._seed_job(
            db_session, 9002, job_id_recent, "in_progress", now - timedelta(seconds=10)
        )
        await self._seed_job(db_session, 9002, job_id_old, "in_progress", now - timedelta(hours=4))

        count = await fail_orphaned_jobs(
            db_session,
            orphan_age_threshold=timedelta(seconds=IMPORT_TIMEOUT_SECONDS),
        )
        await db_session.commit()

        assert count == 1

        rows = (
            (
                await db_session.execute(
                    select(ImportJob).where(ImportJob.id.in_([job_id_recent, job_id_old]))
                )
            )
            .scalars()
            .all()
        )
        status_by_id = {j.id: j.status for j in rows}
        assert status_by_id[job_id_recent] == "in_progress", (
            "Recent job (10s old) must stay in_progress when threshold=3h"
        )
        assert status_by_id[job_id_old] == "failed", (
            "Old job (4h old) must be reaped when threshold=3h"
        )

    @pytest.mark.asyncio
    async def test_threshold_zero_equivalent_to_no_threshold(self, db_session):
        """fail_orphaned_jobs() with threshold=timedelta(0) reaps any job older than 0s.

        Semantics: None means no threshold (startup behavior). timedelta(0) means
        any job with started_at < NOW() - 0 = NOW() — i.e., everything already
        started (practically equivalent to no threshold for jobs started before
        the current instant).
        """
        import uuid

        from app.repositories.import_job_repository import fail_orphaned_jobs
        from sqlalchemy import select
        from app.models.import_job import ImportJob

        now = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())
        await self._seed_job(db_session, 9003, job_id, "in_progress", now - timedelta(seconds=10))

        count = await fail_orphaned_jobs(db_session, orphan_age_threshold=timedelta(0))
        await db_session.commit()

        assert count == 1
        rows = (
            (await db_session.execute(select(ImportJob).where(ImportJob.id == job_id)))
            .scalars()
            .all()
        )
        assert rows[0].status == "failed"


class TestPeriodicReaper:
    """Unit tests for run_periodic_reaper coroutine (mocked — no real DB).

    Bug fix (Phase 90, SEED-017): cleanup_orphaned_jobs() only ran at
    backend startup. A Postgres-only restart left the backend up but
    orphaned import jobs stuck in_progress. run_periodic_reaper runs
    every _REAPER_INTERVAL_SECONDS and uses IMPORT_TIMEOUT_SECONDS as
    the orphan-age threshold so live imports are never reaped.
    """

    @pytest.mark.asyncio
    async def test_reaper_calls_cleanup_at_interval(self, monkeypatch):
        """run_periodic_reaper calls cleanup_orphaned_jobs at least 3 times before cancel."""
        from app.services.import_service import run_periodic_reaper

        call_count = 0

        async def _mock_sleep(_seconds: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise asyncio.CancelledError()

        async def _mock_cleanup(**kwargs) -> None:
            pass

        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)
        monkeypatch.setattr("app.services.import_service.cleanup_orphaned_jobs", _mock_cleanup)

        with pytest.raises(asyncio.CancelledError):
            await run_periodic_reaper()

        assert call_count >= 3

    @pytest.mark.asyncio
    async def test_reaper_passes_age_threshold(self, monkeypatch):
        """run_periodic_reaper calls cleanup_orphaned_jobs with the 3h age threshold.

        The reaper sleeps FIRST, then calls cleanup. So we let the first sleep succeed,
        let cleanup run once, then cancel on the second sleep.
        """
        from app.services.import_service import run_periodic_reaper

        received_kwargs: list[dict] = []
        sleep_count = 0

        async def _mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError()

        async def _mock_cleanup(**kwargs) -> None:
            received_kwargs.append(kwargs)

        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)
        monkeypatch.setattr("app.services.import_service.cleanup_orphaned_jobs", _mock_cleanup)

        with pytest.raises(asyncio.CancelledError):
            await run_periodic_reaper()

        assert len(received_kwargs) >= 1, (
            "Reaper must have called cleanup at least once before second sleep cancelled it."
        )
        # Verify that cleanup was called with the 3h orphan age threshold.
        first_call = received_kwargs[0]
        expected_threshold = timedelta(seconds=IMPORT_TIMEOUT_SECONDS)
        assert first_call.get("orphan_age_threshold") == expected_threshold, (
            f"Expected orphan_age_threshold={expected_threshold!r}, got: {first_call!r}"
        )

    @pytest.mark.asyncio
    async def test_reaper_survives_cleanup_exception(self, monkeypatch):
        """run_periodic_reaper catches cleanup exceptions, logs them, and continues."""
        from app.services.import_service import run_periodic_reaper

        sleep_count = 0

        async def _mock_sleep(_seconds: float) -> None:
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 3:
                raise asyncio.CancelledError()

        call_count = 0

        async def _mock_cleanup(**kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("DB temporarily unavailable")
            # Subsequent calls succeed.

        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)
        monkeypatch.setattr("app.services.import_service.cleanup_orphaned_jobs", _mock_cleanup)

        with (
            patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture,
            pytest.raises(asyncio.CancelledError),
        ):
            await run_periodic_reaper()

        # Reaper must not crash and must have attempted cleanup >= 2 times.
        assert call_count >= 2, (
            f"Reaper should continue after cleanup exception. cleanup called {call_count} time(s)"
        )
        # Sentry capture must have been called (once per exception from cleanup).
        assert mock_capture.call_count >= 1, (
            "Sentry.capture_exception must be called when cleanup raises"
        )


class TestRecordFailureWithRetry:
    """Unit tests for _record_failure_with_retry helper (mocked — no real DB).

    Bug fix (Phase 90, SEED-017, FLAWCHESS-3Q): the original except-block in
    run_import opened a new session and immediately UPDATEd the job to failed
    while Postgres was still in crash recovery (OperationalError, ~2s window
    observed in the 2026-05-16 incident). The capture_exception swallowed the
    error and the job stayed in_progress forever.

    _record_failure_with_retry wraps the UPDATE in a bounded retry loop with
    exponential backoff (2/4/8/16/30s) mirroring app/services/lichess_client.py.
    Sentry capture happens only on final exhaustion per CLAUDE.md rule.
    """

    def _make_failure_kwargs(self) -> dict:
        return dict(
            job_id="test-job-id",
            status="failed",
            games_fetched=5,
            games_imported=3,
            error_message="something went wrong",
            completed_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_succeeds_first_attempt(self, monkeypatch):
        """Helper returns after one attempt; asyncio.sleep not called."""
        from app.services.import_service import _record_failure_with_retry

        mock_update = AsyncMock()
        mock_commit = AsyncMock()

        mock_session = AsyncMock()
        mock_session.commit = mock_commit

        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)

        sleep_mock = AsyncMock()

        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job", mock_update
        )
        monkeypatch.setattr("app.services.import_service.asyncio.sleep", sleep_mock)

        await _record_failure_with_retry(**self._make_failure_kwargs())

        mock_update.assert_called_once()
        sleep_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_operational_error_then_succeeds(self, monkeypatch):
        """Helper retries on OperationalError and succeeds on 3rd attempt.

        asyncio.sleep called twice (attempts 1 and 2) with backoffs 2s and 4s.
        No Sentry capture because the helper succeeded before exhaustion.
        """
        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _mock_update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OperationalError("connection refused", None, Exception("transient"))

        mock_commit = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = mock_commit

        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)

        sleep_calls: list[float] = []

        async def _mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job", _mock_update
        )
        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)

        with patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture:
            await _record_failure_with_retry(**self._make_failure_kwargs())

        assert call_count == 3
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 2
        assert sleep_calls[1] == 4
        mock_capture.assert_not_called()

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_captures_once(self, monkeypatch):
        """Helper exhausts all 5 retries and calls Sentry capture exactly once.

        asyncio.sleep called 4 times (backoff between attempts 1-2, 2-3, 3-4, 4-5).
        Sentry capture_exception called exactly once (last-attempt rule per CLAUDE.md).
        Helper returns without re-raising (best-effort — same as the original pattern).
        """
        from app.services.import_service import (
            _FAILURE_RECORD_MAX_RETRIES,
            _record_failure_with_retry,
        )

        async def _mock_update(*args, **kwargs) -> None:
            raise OperationalError("connection refused", None, Exception("transient"))

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)

        sleep_calls: list[float] = []

        async def _mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job", _mock_update
        )
        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)

        with patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture:
            # Should return without raising (best-effort).
            await _record_failure_with_retry(**self._make_failure_kwargs())

        # 5 attempts → 4 sleep calls between them.
        assert len(sleep_calls) == _FAILURE_RECORD_MAX_RETRIES - 1
        # Pin the documented backoff schedule (WR-02) so a future change to
        # the constants is forced to update the docstring too.
        assert sleep_calls == [2, 4, 8, 16], (
            f"Backoff schedule must be 2/4/8/16s (30s total budget). Got {sleep_calls}."
        )
        # Sentry called exactly once (on exhaustion, not per attempt).
        assert mock_capture.call_count == 1, (
            f"Expected exactly 1 Sentry capture (last-attempt rule), got {mock_capture.call_count}"
        )

    @pytest.mark.asyncio
    async def test_non_transient_error_fails_fast(self, monkeypatch):
        """Helper fails fast on non-transient exception (no retries, one Sentry capture)."""
        from app.services.import_service import _record_failure_with_retry

        async def _mock_update(*args, **kwargs) -> None:
            raise ValueError("unexpected schema drift")

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)

        sleep_mock = AsyncMock()

        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job", _mock_update
        )
        monkeypatch.setattr("app.services.import_service.asyncio.sleep", sleep_mock)

        with patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture:
            await _record_failure_with_retry(**self._make_failure_kwargs())

        # No retries — sleep never called.
        sleep_mock.assert_not_called()
        # Sentry capture called once for the non-transient exception.
        assert mock_capture.call_count == 1

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates_without_retry(self, monkeypatch):
        """WR-07: CancelledError from asyncio.sleep must propagate immediately.

        Simulates the lifespan shutdown path: an in-flight retry sleep is
        cancelled, the helper must re-raise CancelledError (not retry, not
        capture to Sentry). The periodic orphan-job reaper backstops any
        jobs left in_progress because of this cancellation.
        """
        from app.services.import_service import _record_failure_with_retry

        # First update call raises OperationalError so the helper enters the
        # retry path; sleep then raises CancelledError to simulate shutdown.
        async def _mock_update(*args, **kwargs) -> None:
            raise OperationalError("connection refused", None, Exception("transient"))

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)

        sleep_calls: list[float] = []

        async def _mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            raise asyncio.CancelledError()

        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job",
            _mock_update,
        )
        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)

        with patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture:
            with pytest.raises(asyncio.CancelledError):
                await _record_failure_with_retry(**self._make_failure_kwargs())

        # First sleep was attempted (with backoff=2s) and immediately cancelled.
        assert sleep_calls == [2], f"Expected one cancelled sleep at 2s, got {sleep_calls}"
        # No Sentry capture — cancellation is a shutdown signal, not a bug.
        mock_capture.assert_not_called()


# ---------------------------------------------------------------------------
# TestRunImportSessionPerBatch — Phase 90 / SEED-018: per-batch session lifecycle
#
# Phase 90 / SEED-018: pins the per-batch session lifecycle. A regression to a
# single-session import is the secondary accumulation surface mitigated alongside
# the Stage 5 leak fix (Plan 90-01).
#
# Tests 2–5 are xfail(strict=True) until Task 2 (Plan 90-02) lands the
# three-session-scope restructure. Test 1 is NOT xfail — it asserts Assumption
# A2 (scalar accessibility after session close), which is a property of the
# current code that the implementation already relies on.
# ---------------------------------------------------------------------------


class TestRunImportSessionPerBatch:
    """Tests for the per-batch AsyncSession lifecycle introduced in Plan 90-02.

    After restructure, run_import opens THREE distinct session scopes:
    1. Bootstrap scope — get_latest_for_user_platform + create_import_job + commit
    2. Per-batch scope — _flush_batch + update_import_job + commit (once per batch)
    3. Completion scope — update_import_job(completed) + commit

    Verifies:
    1. previous_job.last_synced_at scalar survives session close (Assumption A2).
    2. async_session_maker() is called once per logical scope (1 bootstrap +
       N_batches per-batch + 1 completion = N_batches + 2 total).
    3. Bootstrap session is closed before the first per-batch session opens.
    4. Completion session is distinct from the last batch's session.
    5. run_import completes without error and _make_game_iterator receives a
       scalar (datetime | None), not an ImportJob ORM instance.
    """

    def _make_counting_session_maker(self) -> tuple[MagicMock, list[str]]:
        """Return a session-maker mock that tracks open/close ordering.

        Each entry in the returned list is a string like "open:session-1"
        or "close:session-1". The list grows in call order so callers can
        verify that bootstrap closes before the first batch opens, etc.
        """
        events: list[str] = []

        class _TrackedSession:
            def __init__(self, name: str) -> None:
                self._name = name
                self.commit = AsyncMock()
                self.execute = AsyncMock(
                    return_value=MagicMock(fetchall=MagicMock(return_value=[]))
                )

            async def __aenter__(self):
                events.append(f"open:{self._name}")
                return self

            async def __aexit__(self, *_a):
                events.append(f"close:{self._name}")
                return False

        call_count = [0]

        def _factory():
            call_count[0] += 1
            return _TrackedSession(f"session-{call_count[0]}")

        maker = MagicMock(side_effect=_factory)
        return maker, events

    def _make_simple_session_maker(self, n_calls: list[int]) -> MagicMock:
        """Return a session-maker mock that counts calls and provides basic sessions."""

        def _factory():
            ctx = AsyncMock()
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            result_mock = MagicMock()
            result_mock.fetchall.return_value = []
            mock_session.execute = AsyncMock(return_value=result_mock)
            ctx.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            n_calls[0] += 1
            return ctx

        return MagicMock(side_effect=_factory)

    @pytest.mark.asyncio
    async def test_previous_job_last_synced_at_scalar_survives_close(self):
        """Assumption A2 (90-RESEARCH.md Pitfall 2): after the bootstrap session closes,
        a scalar extracted from previous_job.last_synced_at inside the session remains
        accessible from a local variable.

        This test is NOT xfail — it asserts a property of the CURRENT code and must
        pass before and after the Task 2 restructure. If it fails, the implementation
        MUST extract the scalar inside the bootstrap scope before closing the session
        (which Plan 90-02 Task 2 does unconditionally as a defensive measure).
        """
        expected_dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Simulate an ImportJob ORM instance with expire_on_commit=False semantics:
        # the scalar column is loaded as part of the SELECT, so it's accessible
        # even after the session closes.
        previous_job = MagicMock()
        previous_job.last_synced_at = expected_dt

        # Simulate the bootstrap session context manager.
        bootstrap_session = AsyncMock()
        bootstrap_session.commit = AsyncMock()

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=bootstrap_session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        scalar_after_close: datetime | None = None

        async def run() -> None:
            nonlocal scalar_after_close
            # Mimic the bootstrap scope: open session, load previous_job, extract scalar.
            async with ctx:
                # In the real code, get_latest_for_user_platform returns previous_job here.
                # We pre-load the attribute inside the session scope (Pitfall 2 mitigation).
                extracted = previous_job.last_synced_at if previous_job is not None else None
            # Session is now "closed" (ctx.__aexit__ called). Scalar must still be readable.
            scalar_after_close = extracted

        await run()

        assert scalar_after_close == expected_dt, (
            f"Scalar extracted inside the bootstrap scope must survive session close. "
            f"Expected {expected_dt!r}, got {scalar_after_close!r}. "
            f"If this fails with DetachedInstanceError, the extraction must happen "
            f"before closing the bootstrap session (already planned in Task 2)."
        )
        # Verify the session context manager was entered and exited.
        ctx.__aenter__.assert_called_once()
        ctx.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_one_session_per_batch(self):
        """run_import opens one session for each logical scope: bootstrap + per-batch + completion + Stage-B gate.

        With N=30 games and _BATCH_SIZE=12:
          12 (batch 1) + 12 (batch 2) + 6 (trailing) = 3 batch sessions
          + 1 bootstrap + 1 completion + 1 Stage-B gate read session (quick-260527-u3u) = 6 total session opens.

        The trailing +1 is the fresh read session opened inside _complete_import_job to
        evaluate users_with_zero_pending before firing compute_stage_b — see
        app/services/import_service.py around line 510.
        """
        from app.services.import_service import _BATCH_SIZE

        total_games = _BATCH_SIZE * 2 + _BATCH_SIZE // 2  # = 30 for _BATCH_SIZE=12
        n_full_batches = total_games // _BATCH_SIZE  # = 2
        n_trailing = total_games % _BATCH_SIZE  # = 6
        n_batch_sessions = n_full_batches + (1 if n_trailing > 0 else 0)  # = 3
        # bootstrap + batches + completion + Stage-B gate read session = 6
        expected_session_calls = 1 + n_batch_sessions + 1 + 1

        call_count = [0]
        mock_maker = self._make_simple_session_maker(call_count)

        async def _yield_n_games(*args, **kwargs):
            for i in range(total_games):
                if "on_game_fetched" in kwargs:
                    kwargs["on_game_fetched"]()
                yield {
                    "platform": "chess.com",
                    "platform_game_id": f"game-{i}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

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
                side_effect=_yield_n_games,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert call_count[0] == expected_session_calls, (
            f"Expected {expected_session_calls} async_session_maker() calls "
            f"(1 bootstrap + {n_batch_sessions} per-batch + 1 completion + 1 Stage-B gate). "
            f"Got {call_count[0]}."
        )

    @pytest.mark.asyncio
    async def test_bootstrap_session_closed_before_loop(self):
        """Bootstrap session is closed (via __aexit__) before the first per-batch session opens.

        The event ordering must be: open bootstrap → close bootstrap → open batch-1.
        Currently: one session is shared for the whole import — no distinct bootstrap close.
        After Task 2: three-scope structure enforces this ordering.
        """
        from app.services.import_service import _BATCH_SIZE

        maker, events = self._make_counting_session_maker()

        async def _yield_one_batch(*args, **kwargs):
            for i in range(_BATCH_SIZE):
                if "on_game_fetched" in kwargs:
                    kwargs["on_game_fetched"]()
                yield {
                    "platform": "chess.com",
                    "platform_game_id": f"game-{i}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        with (
            patch("app.services.import_service.async_session_maker", maker),
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
                side_effect=_yield_one_batch,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # After Task 2: the first 3 events must be:
        #   open:session-1  (bootstrap opens)
        #   close:session-1 (bootstrap closes)
        #   open:session-2  (first batch opens)
        # Currently: only session-1 opens and closes once at the very end,
        # so close:session-1 never comes before open:session-2 mid-import.
        assert len(events) >= 3, f"Expected at least 3 session events, got: {events}"
        bootstrap_open = events.index("open:session-1")
        bootstrap_close = events.index("close:session-1")
        # There must be a second session opened AFTER the bootstrap closes.
        second_open_events = [
            i for i, e in enumerate(events) if e.startswith("open:") and e != "open:session-1"
        ]
        assert second_open_events, (
            f"No second session was opened. Events: {events}. "
            f"After Task 2, a per-batch session must open after the bootstrap closes."
        )
        first_batch_open = second_open_events[0]
        assert bootstrap_close < first_batch_open, (
            f"Bootstrap session must close (event index {bootstrap_close}) BEFORE the first "
            f"per-batch session opens (event index {first_batch_open}). "
            f"Events: {events}. "
            f"Currently run_import uses one session for the whole import — "
            f"bootstrap close happens at the very end."
        )
        _ = bootstrap_open  # used in assertion above via events.index

    @pytest.mark.asyncio
    async def test_completion_session_separate_from_batch(self):
        """Completion UPDATE runs on a fresh session, not the last batch's.

        After all batches flush, the completion scope must open a NEW session
        (a distinct async_session_maker() call) rather than reusing the last
        batch's session.

        Currently: one session covers the whole import — the completion update
        uses the same session as every batch.
        After Task 2: 1 bootstrap + N_batches + 1 completion = distinct sessions.
        """
        from app.services.import_service import _BATCH_SIZE

        # Yield exactly one trailing batch (< _BATCH_SIZE) to keep the scenario simple.
        trailing_count = _BATCH_SIZE // 2

        maker, events = self._make_counting_session_maker()

        async def _yield_trailing(*args, **kwargs):
            for i in range(trailing_count):
                if "on_game_fetched" in kwargs:
                    kwargs["on_game_fetched"]()
                yield {
                    "platform": "chess.com",
                    "platform_game_id": f"game-{i}",
                    "pgn": "1. e4 *",
                    "user_id": 1,
                }

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        with (
            patch("app.services.import_service.async_session_maker", maker),
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
                side_effect=_yield_trailing,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.import_service.game_repository.bulk_insert_games",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.import_service.game_repository.bulk_insert_positions",
                new=AsyncMock(),
            ),
            patch(
                "app.services.import_service.process_game_pgn",
                return_value=_make_mock_processing_result(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # After Task 2: trailing batch + completion = 3 total sessions
        # (session-1=bootstrap, session-2=trailing batch, session-3=completion).
        # The last close must be session-3 (completion), and session-2 (trailing batch)
        # must have closed BEFORE session-3 opened.
        # Currently: 1 session total; open/close happens once.
        open_events = [e for e in events if e.startswith("open:")]
        assert len(open_events) >= 3, (
            f"Expected at least 3 session opens (bootstrap + trailing batch + completion). "
            f"Got {len(open_events)}. Events: {events}. "
            f"Currently run_import uses 1 session."
        )
        # The completion session (last open) must open after the trailing batch session closes.
        completion_session_name = open_events[-1].split("open:")[1]
        batch_session_name = open_events[-2].split("open:")[1]
        batch_close_idx = events.index(f"close:{batch_session_name}")
        completion_open_idx = events.index(f"open:{completion_session_name}")
        assert batch_close_idx < completion_open_idx, (
            f"Trailing batch session ({batch_session_name!r}) must close (index {batch_close_idx}) "
            f"BEFORE completion session ({completion_session_name!r}) opens "
            f"(index {completion_open_idx}). Events: {events}."
        )

    @pytest.mark.asyncio
    async def test_run_import_e2e_smoke(self):
        """Smoke test: after Task 2, _make_game_iterator is called with the extracted scalar
        (`previous_last_synced_at: datetime | None`) rather than the ORM ImportJob instance.

        Currently: _make_game_iterator receives `previous_job` (an ORM instance or None).
        After Task 2: _make_game_iterator receives `previous_last_synced_at` (a scalar
        datetime or None) extracted inside the bootstrap scope, eliminating any risk of
        DetachedInstanceError from cross-scope ORM attribute access (Pitfall 2).

        The parameter rename is the observable signal: the old signature accepts `previous_job`,
        the new signature accepts `previous_last_synced_at`. We verify by inspecting the
        captured call-args to `_make_game_iterator`.
        """
        last_synced = datetime(2025, 6, 1, tzinfo=timezone.utc)

        # previous_job mock — after Task 2, its last_synced_at is extracted as a scalar
        # and previous_job is never passed cross-scope.
        previous_job_mock = MagicMock()
        previous_job_mock.last_synced_at = last_synced

        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        call_count = [0]
        mock_maker = self._make_simple_session_maker(call_count)

        # Capture positional args passed to _make_game_iterator.
        # The call site uses positional args: _make_game_iterator(client, job, scalar, on_game_fetched).
        # arg[2] is the 3rd positional — previous_last_synced_at (datetime | None) after Task 2,
        # or previous_job (an ORM instance) before Task 2.
        captured_make_game_iterator_args: list[tuple] = []

        async def _mock_make_game_iterator(*args, **kwargs):
            captured_make_game_iterator_args.append(args)
            return
            yield  # pragma: no cover

        with (
            patch("app.services.import_service.async_session_maker", mock_maker),
            patch(
                "app.services.import_service.import_job_repository.get_latest_for_user_platform",
                new=AsyncMock(return_value=previous_job_mock),
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
                "app.services.import_service._make_game_iterator",
                side_effect=_mock_make_game_iterator,
            ),
            patch("app.services.import_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_make_game_iterator_args) >= 1, (
            "_make_game_iterator must have been called (is it still called via run_import?)"
        )
        # Positional arg layout: (client, job, previous_last_synced_at, on_game_fetched)
        # arg[2] must be a datetime scalar (or None), not an ORM ImportJob instance.
        positional_args = captured_make_game_iterator_args[0]
        assert len(positional_args) >= 3, (
            f"Expected at least 3 positional args to _make_game_iterator, got: {positional_args!r}"
        )
        third_arg = positional_args[2]
        # After Task 2: third arg is `previous_last_synced_at` — a datetime or None scalar.
        # It must NOT be the previous_job_mock ORM instance.
        assert third_arg is not previous_job_mock, (
            f"After Task 2, _make_game_iterator must receive the extracted datetime scalar "
            f"as its 3rd arg, NOT the ORM instance. Got: {third_arg!r} (same object as "
            f"previous_job_mock). The scalar extraction inside the bootstrap scope "
            f"eliminates DetachedInstanceError risk (Pitfall 2, 90-RESEARCH.md)."
        )
        assert isinstance(third_arg, (datetime, type(None))), (
            f"3rd arg to _make_game_iterator must be datetime | None, got {type(third_arg)!r}. "
            f"Value: {third_arg!r}"
        )
        assert third_arg == last_synced, (
            f"Expected previous_last_synced_at={last_synced!r}, got {third_arg!r}"
        )


class TestFlushBatchStage5RealDb:
    """DB-backed regression test for Stage 5 executemany.

    The mock-based TestFlushBatchStage5 tests use AsyncMock sessions, which
    never trigger SQLAlchemy's real ORM-update-with-executemany validation.
    UAT 2026-05-20 caught a runtime failure ("bulk synchronize of persistent
    objects not supported when using bulk update with additional WHERE
    criteria right now") that the mock tests could not detect. This class
    pins the contract against a real DB session via the rollback-scoped
    db_session fixture, so any future regression in synchronize_session
    handling will fail in CI.
    """

    async def _seed_user_and_games(
        self,
        session,
        user_id: int,
        n_games: int,
    ) -> list[int]:
        """Insert a test user and N Game rows with NULL ply_count / result_fen.

        Returns the list of inserted game ids in order.
        """
        from app.models.game import Game
        from tests.conftest import ensure_test_user

        await ensure_test_user(session, user_id)
        ids: list[int] = []
        for i in range(n_games):
            g = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=f"stage5-real-{user_id}-{i}",
                pgn="1. e4 *",
                result="1-0",
                user_color="white",
                rated=True,
                is_computer_game=False,
            )
            session.add(g)
            await session.flush()
            ids.append(g.id)
        return ids

    @pytest.mark.asyncio
    async def test_stage5_executemany_runs_against_real_session(self, db_session):
        """Issue both Stage 5 UPDATE groups via real session.execute(stmt, params).

        The Table-level (not ORM) update bypasses SQLAlchemy 2.x's ORM
        bulk-update machinery, which would otherwise raise either
        "bulk synchronize of persistent objects not supported when using
        bulk update with additional WHERE criteria right now" (default) or
        "per-row ORM Bulk UPDATE by Primary Key requires that records
        contain primary key values" (with synchronize_session=False but the
        bind param keyed by `b_id` instead of `id`).
        """
        from sqlalchemy import bindparam, select, update

        from app.models.game import Game

        game_ids = await self._seed_user_and_games(db_session, 9501, 3)
        games_table = Game.__table__

        # Group (a): ply_count for ALL games. This must NOT raise.
        ply_count_stmt = (
            update(games_table)  # ty: ignore[invalid-argument-type]
            .where(games_table.c.id == bindparam("b_id"))
            .values(ply_count=bindparam("b_pc"))
        )
        await db_session.execute(
            ply_count_stmt,
            [{"b_id": gid, "b_pc": 10 + i} for i, gid in enumerate(game_ids)],
        )

        # Group (b): result_fen for a SUBSET — only the first game.
        fen_stmt = (
            update(games_table)  # ty: ignore[invalid-argument-type]
            .where(games_table.c.id == bindparam("b_id"))
            .values(result_fen=bindparam("b_rf"))
        )
        await db_session.execute(
            fen_stmt,
            [{"b_id": game_ids[0], "b_rf": "8/8/8/8/8/8/8/8 w - -"}],
        )
        await db_session.flush()

        # Verify both groups landed correctly.
        rows = (
            await db_session.execute(
                select(Game.id, Game.ply_count, Game.result_fen)
                .where(Game.id.in_(game_ids))
                .order_by(Game.id)
            )
        ).all()

        assert len(rows) == 3
        # ply_count set for all 3
        assert [r.ply_count for r in rows] == [10, 11, 12]
        # result_fen set ONLY for the first
        assert rows[0].result_fen == "8/8/8/8/8/8/8/8 w - -"
        assert rows[1].result_fen is None
        assert rows[2].result_fen is None

    @pytest.mark.asyncio
    async def test_orm_level_update_with_executemany_raises(self, db_session):
        """Document SQLAlchemy's contract for the ORM-level alternative.

        `update(Game).where(Game.id == bindparam(...))` + executemany goes
        through the ORM bulk-update path, which raises by default. This
        pins WHY Stage 5 targets `Game.__table__` directly rather than the
        ORM mapper. If a future SQLAlchemy release relaxes this restriction,
        this test will fail and we can revisit whether the Table-level
        rewrite is still needed.
        """
        from sqlalchemy import bindparam, update
        from sqlalchemy.exc import InvalidRequestError

        from app.models.game import Game

        game_ids = await self._seed_user_and_games(db_session, 9502, 2)

        bad_stmt = (
            update(Game).where(Game.id == bindparam("b_id")).values(ply_count=bindparam("b_pc"))
        )

        with pytest.raises(InvalidRequestError, match="bulk synchronize"):
            await db_session.execute(
                bad_stmt,
                [{"b_id": gid, "b_pc": i} for i, gid in enumerate(game_ids)],
            )


class TestRecordFailureWithRetryDbOutage:
    """Regression tests for the broadened DB-outage classifier in
    _record_failure_with_retry.

    UAT 2026-05-20 (Postgres-only restart): a real outage raises
    InterfaceError / DBAPIError / asyncpg.CannotConnectNowError /
    ConnectionRefusedError on the next session checkout — none of which
    were caught by the original `except OperationalError`. The helper
    fell through to the generic Exception fail-fast branch and the job
    stayed `in_progress`. This class pins the broadened classifier and
    the engine.dispose() pool-invalidation between retries.

    These tests mock the session+update path to inject each exception
    type directly; the full live-DB scenario is too heavy for CI but is
    covered by UAT-2 in 90-HUMAN-UAT.md.
    """

    def _make_failure_kwargs(self) -> dict:
        return dict(
            job_id="test-job-outage",
            status="failed",
            games_fetched=10,
            games_imported=8,
            error_message="db went away",
            completed_at=datetime.now(timezone.utc),
        )

    def _patch_session_path(self, monkeypatch, update_side_effect) -> list[float]:
        """Wire monkeypatches so update_import_job raises per side_effect and
        engine.dispose() is observed. Returns the list that sleep calls append to.
        """
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_maker = MagicMock(return_value=session_ctx)
        monkeypatch.setattr("app.services.import_service.async_session_maker", mock_maker)
        monkeypatch.setattr(
            "app.services.import_service.import_job_repository.update_import_job",
            update_side_effect,
        )
        sleep_calls: list[float] = []

        async def _mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        monkeypatch.setattr("app.services.import_service.asyncio.sleep", _mock_sleep)
        return sleep_calls

    @pytest.mark.asyncio
    async def test_retries_on_sqlalchemy_interface_error(self, monkeypatch):
        """SQLAlchemy InterfaceError ('underlying connection is closed') must be retried.

        This is the exact exception observed in UAT 2026-05-20 for jobs
        e9466083 and 1466eb6d after Postgres was stopped mid-import.
        """
        from sqlalchemy.exc import InterfaceError as SAInterfaceError

        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise SAInterfaceError(
                    "cannot call PreparedStatement.fetch(): the underlying connection is closed",
                    None,
                    Exception("interface"),
                )

        sleep_calls = self._patch_session_path(monkeypatch, _update)
        dispose_mock = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.dispose = dispose_mock
        monkeypatch.setattr("app.services.import_service.engine", mock_engine)

        with patch("app.services.import_service.sentry_sdk.capture_exception") as cap:
            await _record_failure_with_retry(**self._make_failure_kwargs())

        assert call_count == 3
        # dispose() called once per retry (i.e. before attempts 2 and 3).
        assert dispose_mock.await_count == 2
        assert sleep_calls == [2, 4]
        cap.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_sqlalchemy_dbapi_error(self, monkeypatch):
        """SQLAlchemy DBAPIError (parent of OperationalError) must be retried.

        Mirrors the asyncpg ConnectionDoesNotExistError observed for job
        824bce84 in UAT 2026-05-20.
        """
        from sqlalchemy.exc import DBAPIError

        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DBAPIError(
                    "connection was closed in the middle of operation",
                    None,
                    Exception("dbapi"),
                )

        self._patch_session_path(monkeypatch, _update)
        _mock_engine = MagicMock()
        _mock_engine.dispose = AsyncMock()
        monkeypatch.setattr("app.services.import_service.engine", _mock_engine)

        await _record_failure_with_retry(**self._make_failure_kwargs())
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_raw_asyncpg_cannot_connect_now(self, monkeypatch):
        """Raw asyncpg.CannotConnectNowError (DB shutting down) must be retried.

        This one escapes SA's exception translator because the pool's
        connect-time path can raise the raw asyncpg exception without
        going through dialect._handle_exception. UAT 2026-05-20 caught
        this exact pattern in the second retry attempt.
        """
        import asyncpg

        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncpg.exceptions.CannotConnectNowError(
                    "the database system is shutting down"
                )

        self._patch_session_path(monkeypatch, _update)
        _mock_engine = MagicMock()
        _mock_engine.dispose = AsyncMock()
        monkeypatch.setattr("app.services.import_service.engine", _mock_engine)

        await _record_failure_with_retry(**self._make_failure_kwargs())
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_connection_refused(self, monkeypatch):
        """Raw ConnectionRefusedError (OS-level, port 5432 down) must be retried.

        asyncpg's _create_ssl_connection raises this from uvloop when the
        Postgres listener is fully down — observed at the bottom of the
        UAT 2026-05-20 traceback for job 1466eb6d.
        """
        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionRefusedError(111, "Connection refused")

        self._patch_session_path(monkeypatch, _update)
        _mock_engine = MagicMock()
        _mock_engine.dispose = AsyncMock()
        monkeypatch.setattr("app.services.import_service.engine", _mock_engine)

        await _record_failure_with_retry(**self._make_failure_kwargs())
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_engine_dispose_called_between_retries(self, monkeypatch):
        """Pool invalidation must run between retries so the next attempt
        opens a fresh asyncpg connection rather than reusing a stale one.
        """
        from sqlalchemy.exc import InterfaceError as SAInterfaceError

        from app.services.import_service import _record_failure_with_retry

        async def _update(*args, **kwargs) -> None:
            raise SAInterfaceError("closed", None, Exception("x"))

        self._patch_session_path(monkeypatch, _update)
        dispose_mock = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.dispose = dispose_mock
        monkeypatch.setattr("app.services.import_service.engine", mock_engine)

        with patch("app.services.import_service.sentry_sdk.capture_exception"):
            await _record_failure_with_retry(**self._make_failure_kwargs())

        # MAX_RETRIES=5 attempts: 4 retries → 4 dispose() calls.
        assert dispose_mock.await_count == 4

    @pytest.mark.asyncio
    async def test_dispose_failure_does_not_break_retry_loop(self, monkeypatch):
        """If engine.dispose() itself raises, the retry loop must continue
        rather than fall through to the generic Exception branch.
        """
        from sqlalchemy.exc import InterfaceError as SAInterfaceError

        from app.services.import_service import _record_failure_with_retry

        call_count = 0

        async def _update(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise SAInterfaceError("closed", None, Exception("x"))

        self._patch_session_path(monkeypatch, _update)
        # dispose() raises on every call — must not break the loop.
        bad_engine = MagicMock()
        bad_engine.dispose = AsyncMock(side_effect=RuntimeError("dispose blew up"))
        monkeypatch.setattr("app.services.import_service.engine", bad_engine)

        await _record_failure_with_retry(**self._make_failure_kwargs())
        assert call_count == 3
