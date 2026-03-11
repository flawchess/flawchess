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
        """run_import should call hashes_for_game for each newly inserted game's PGN."""
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
        # Make execute return game id=999 with the pgn
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, pgn)]
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
                "app.services.import_service.hashes_for_game",
                return_value=[(0, 1, 2, 3), (1, 4, 5, 6)],
            ) as mock_hashes,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        mock_hashes.assert_called_once_with(pgn)

    @pytest.mark.asyncio
    async def test_unknown_job_id_does_nothing(self):
        """run_import with unknown job_id should log and return without error."""
        # Should not raise
        await run_import("nonexistent-job-id")
