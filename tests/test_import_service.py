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
                return_value=([(0, 1, 2, 3, "e4", None), (1, 4, 5, 6, None, None)], "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR"),
            ) as mock_hashes,
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        mock_hashes.assert_called_once_with(pgn)

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
        result_mock.fetchall.return_value = [(999, pgn)]
        mock_session.execute.return_value = result_mock

        mock_maker = _mock_session_maker(mock_session)
        captured_positions: list[dict] = []

        async def _capture_bulk_insert_positions(session, position_rows):
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
                new=AsyncMock(side_effect=_capture_bulk_insert_positions),
            ),
            patch(
                "app.services.import_service.hashes_for_game",
                return_value=([(0, 100, 200, 300, "e4", None), (1, 400, 500, 600, "e5", None), (2, 700, 800, 900, None, None)], "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR"),
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
    async def test_username_saved_after_import(self):
        """After a successful chess.com import, the user's chess_com_username is saved."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        mock_session = _make_mock_session()
        mock_maker = _mock_session_maker(mock_session)
        mock_update_username = AsyncMock()

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
            patch(
                "app.services.import_service.user_repository.update_platform_username",
                mock_update_username,
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        job = get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        mock_update_username.assert_called_once_with(mock_session, 1, "chess.com", "alice")

    @pytest.mark.asyncio
    async def test_move_count_populated(self):
        """After importing a game, move_count is set correctly from PGN (1.e4 e5 = 1 full move)."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # 1. e4 e5 = 2 plies = 1 full move => move_count = (2+1)//2 = 1
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
                return_value=([(0, 1, 2, 3, "e4", None), (1, 4, 5, 6, None, None)], "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR"),
            ),
            patch(
                "app.services.import_service.user_repository.update_platform_username",
                new=AsyncMock(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # Verify session.execute was called with an update that sets move_count
        # The mock session's execute is called multiple times; we look for the UPDATE call
        execute_calls = mock_session.execute.call_args_list
        update_calls = [
            call for call in execute_calls
            if hasattr(call.args[0], "is_update") and call.args[0].is_update
        ]
        assert len(update_calls) >= 1, "Expected at least one UPDATE call for move_count"

    @pytest.mark.asyncio
    async def test_position_rows_include_game_phase(self):
        """After importing a game, all position_rows dicts have a non-null game_phase field."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # Use a real PGN with moves so classify_position can run on actual board states
        pgn = "1. e4 e5 *"

        async def _yield_one_game(*args, **kwargs):
            yield {
                "platform": "chess.com",
                "platform_game_id": "game-gp-1",
                "pgn": pgn,
                "user_id": 1,
            }

        mock_session = _make_mock_session()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(999, pgn)]
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
                "app.services.import_service.user_repository.update_platform_username",
                new=AsyncMock(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        # Verify that all position rows have a non-null game_phase
        assert len(captured_positions) > 0, "Expected at least one position row"
        for row in captured_positions:
            assert "game_phase" in row, f"Missing game_phase in row: {row}"
            assert row["game_phase"] is not None, "game_phase should not be None"
            assert row["game_phase"] in ("opening", "middlegame", "endgame"), (
                f"Unexpected game_phase: {row['game_phase']}"
            )

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
        result_mock.fetchall.return_value = [(999, pgn)]
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
                "app.services.import_service.user_repository.update_platform_username",
                new=AsyncMock(),
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
    async def test_starting_position_classified_as_opening(self):
        """The starting position (ply 0) of a valid game is classified as 'opening' with full material."""
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
        result_mock.fetchall.return_value = [(999, pgn)]
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
                "app.services.import_service.user_repository.update_platform_username",
                new=AsyncMock(),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            await run_import(job_id)

        assert len(captured_positions) > 0
        # ply 0 is the starting position
        ply0 = captured_positions[0]
        assert ply0["ply"] == 0
        assert ply0["game_phase"] == "opening"
        # Starting position has full material on both sides
        assert ply0["material_signature"] == "KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP"

    @pytest.mark.asyncio
    async def test_classification_failure_degrades_gracefully(self):
        """When classify_position fails, import still succeeds with NULL metadata columns."""
        job_id = create_job(user_id=1, platform="chess.com", username="alice")

        # Use a PGN that hashes_for_game can process normally
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
        result_mock.fetchall.return_value = [(999, pgn)]
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
                "app.services.import_service.user_repository.update_platform_username",
                new=AsyncMock(),
            ),
            # Simulate classify PGN parse failure by making read_game return None for classify path
            # We do this by patching classify_position to raise, to simulate unexpected failure
            patch(
                "app.services.import_service.classify_position",
                side_effect=Exception("Simulated classification failure"),
            ),
        ):
            mock_http_ctx = AsyncMock()
            mock_http_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_http_ctx

            # Import should still complete successfully (no exception raised)
            await run_import(job_id)

        job = import_service._jobs[job_id]
        assert job.status == JobStatus.COMPLETED, (
            f"Expected COMPLETED, got {job.status} — classification failure must not fail the import"
        )
        # Positions should still be inserted, just without metadata
        assert len(captured_positions) > 0, "Position rows should still be inserted despite classify failure"
        for row in captured_positions:
            # When classify fails, metadata keys should not be present (or be None)
            assert "game_phase" not in row or row["game_phase"] is None
