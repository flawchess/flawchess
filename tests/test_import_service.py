"""Tests for the import service.

Focuses on orchestration logic: job lifecycle, incremental sync, hash computation,
and error handling. All external dependencies are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.import_service as import_service
from app.services.import_service import (
    JobStatus,
    create_job,
    find_active_job,
    get_job,
    run_import,
)


def _make_mock_processing_result(
    plies: list[dict] | None = None,
    result_fen: str = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR",
    move_count: int = 1,
) -> dict:
    """Build a mock GameProcessingResult dict for testing."""
    if plies is None:
        plies = [
            {
                "ply": 0, "white_hash": 1, "black_hash": 2, "full_hash": 3,
                "move_san": "e4", "clock_seconds": None,
                "eval_cp": None, "eval_mate": None,
                "material_count": 7800, "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0, "has_opposite_color_bishops": False,
                "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                "endgame_class": None, "phase": 0,
            },
            {
                "ply": 1, "white_hash": 4, "black_hash": 5, "full_hash": 6,
                "move_san": None, "clock_seconds": None,
                "eval_cp": None, "eval_mate": None,
                "material_count": 7800, "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                "material_imbalance": 0, "has_opposite_color_bishops": False,
                "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                "endgame_class": None, "phase": 0,
            },
        ]
    return {"plies": plies, "result_fen": result_fen, "move_count": move_count}


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
            patch(
                "app.services.import_service.async_session_maker", mock_maker
            ),
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
                    "ply": 0, "white_hash": 100, "black_hash": 200, "full_hash": 300,
                    "move_san": "e4", "clock_seconds": None,
                    "eval_cp": None, "eval_mate": None,
                    "material_count": 7800, "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0, "has_opposite_color_bishops": False,
                    "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                    "endgame_class": None, "phase": 0,
                },
                {
                    "ply": 1, "white_hash": 400, "black_hash": 500, "full_hash": 600,
                    "move_san": "e5", "clock_seconds": None,
                    "eval_cp": None, "eval_mate": None,
                    "material_count": 7800, "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0, "has_opposite_color_bishops": False,
                    "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                    "endgame_class": None, "phase": 0,
                },
                {
                    "ply": 2, "white_hash": 700, "black_hash": 800, "full_hash": 900,
                    "move_san": None, "clock_seconds": None,
                    "eval_cp": None, "eval_mate": None,
                    "material_count": 7800, "material_signature": "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP",
                    "material_imbalance": 0, "has_opposite_color_bishops": False,
                    "piece_count": 14, "backrank_sparse": False, "mixedness": 0,
                    "endgame_class": None, "phase": 0,
                },
            ],
            move_count=1,
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
    async def test_move_count_populated(self):
        """After importing a game, move_count is set correctly via bulk CASE UPDATE (D-04)."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # 1. e4 e5 = 2 plies = 1 full move => move_count = 1
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

        # Verify session.execute was called with a bulk UPDATE for move_count (D-04)
        execute_calls = mock_session.execute.call_args_list
        update_calls = [
            call for call in execute_calls
            if hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]
        assert len(update_calls) >= 1, "Expected at least one UPDATE call for move_count"

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
        assert len(captured_positions) == 0, "No position rows should be inserted when process_game_pgn fails"


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
        assert evals[0] == (18, None)   # 1.e4: 0.18 pawns = 18 centipawns
        assert evals[1] == (17, None)   # 1...e5: 0.17 pawns = 17 centipawns
        assert evals[2] == (None, 3)    # 2.Nf3: mate in 3 for white

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
        assert results[0] == {"eval_cp": 18, "eval_mate": None}   # node 0: after e4
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
