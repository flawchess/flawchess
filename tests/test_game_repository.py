"""Tests for game_repository and import_job_repository.

Uses real PostgreSQL with transaction rollback — each test is isolated.
"""

import datetime
import uuid



class TestBulkInsertGames:
    """Tests for bulk_insert_games with ON CONFLICT DO NOTHING."""

    def _make_game_row(self, platform_game_id: str, user_id: int = 1) -> dict:
        return {
            "user_id": user_id,
            "platform": "chess.com",
            "platform_game_id": platform_game_id,
            "platform_url": f"https://chess.com/game/{platform_game_id}",
            "pgn": '[Event "Test"]\n\n1. e4 *',
            "variant": "Standard",
            "result": "1-0",
            "user_color": "white",
            "time_control_str": "600+0",
            "time_control_bucket": "blitz",
            "time_control_seconds": 600,
            "rated": True,
            "opponent_username": "Opponent",
            "opponent_rating": 1500,
            "user_rating": 1600,
            "opening_name": None,
            "opening_eco": None,
            "played_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        }

    async def test_insert_three_games_returns_three_ids(self, db_session):
        from app.repositories.game_repository import bulk_insert_games
        rows = [
            self._make_game_row(f"game-{uuid.uuid4().hex}"),
            self._make_game_row(f"game-{uuid.uuid4().hex}"),
            self._make_game_row(f"game-{uuid.uuid4().hex}"),
        ]
        ids = await bulk_insert_games(db_session, rows)
        assert len(ids) == 3
        assert all(isinstance(i, int) for i in ids)

    async def test_duplicate_game_skipped(self, db_session):
        from app.repositories.game_repository import bulk_insert_games
        game_id = f"game-{uuid.uuid4().hex}"
        row = self._make_game_row(game_id)

        # First insert: should return 1 ID
        ids_first = await bulk_insert_games(db_session, [row])
        assert len(ids_first) == 1

        # Second insert of same game: should return 0 IDs (duplicate skipped)
        ids_second = await bulk_insert_games(db_session, [row])
        assert len(ids_second) == 0

    async def test_mixed_new_and_duplicate(self, db_session):
        from app.repositories.game_repository import bulk_insert_games
        existing_game_id = f"game-{uuid.uuid4().hex}"
        new_game_id = f"game-{uuid.uuid4().hex}"

        # Insert first game
        await bulk_insert_games(db_session, [self._make_game_row(existing_game_id)])

        # Insert 1 duplicate + 1 new game
        rows = [
            self._make_game_row(existing_game_id),
            self._make_game_row(new_game_id),
        ]
        ids = await bulk_insert_games(db_session, rows)
        # Only the new game should be returned
        assert len(ids) == 1

    async def test_empty_list_returns_empty(self, db_session):
        from app.repositories.game_repository import bulk_insert_games
        ids = await bulk_insert_games(db_session, [])
        assert ids == []

    async def test_returned_ids_are_valid_integers(self, db_session):
        from app.repositories.game_repository import bulk_insert_games
        row = self._make_game_row(f"game-{uuid.uuid4().hex}")
        ids = await bulk_insert_games(db_session, [row])
        assert len(ids) == 1
        assert ids[0] > 0


class TestBulkInsertPositions:
    """Tests for bulk_insert_positions."""

    def _make_game_row(self, platform_game_id: str) -> dict:
        return {
            "user_id": 1,
            "platform": "lichess",
            "platform_game_id": platform_game_id,
            "platform_url": f"https://lichess.org/{platform_game_id}",
            "pgn": '[Event "Test"]\n\n1. e4 e5 *',
            "variant": "Standard",
            "result": "1/2-1/2",
            "user_color": "white",
            "time_control_str": "600+0",
            "time_control_bucket": "blitz",
            "time_control_seconds": 600,
            "rated": True,
            "opponent_username": None,
            "opponent_rating": None,
            "user_rating": 1500,
            "opening_name": None,
            "opening_eco": None,
            "played_at": datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc),
        }

    async def test_insert_positions(self, db_session):
        from app.repositories.game_repository import bulk_insert_games, bulk_insert_positions
        # First insert a game to get a game_id
        row = self._make_game_row(f"lich-{uuid.uuid4().hex}")
        [game_id] = await bulk_insert_games(db_session, [row])

        # Now insert positions
        position_rows = [
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 0,
                "full_hash": 12345678,
                "white_hash": 9876543,
                "black_hash": 1111111,
            },
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 1,
                "full_hash": 22345678,
                "white_hash": 19876543,
                "black_hash": 11111111,
            },
        ]
        # Should not raise
        await bulk_insert_positions(db_session, position_rows)

    async def test_insert_empty_positions(self, db_session):
        from app.repositories.game_repository import bulk_insert_positions
        # Should not raise for empty list
        await bulk_insert_positions(db_session, [])


class TestImportJobRepository:
    """Tests for import job CRUD operations."""

    async def test_create_and_get_import_job(self, db_session):
        from app.repositories.import_job_repository import create_import_job, get_import_job
        job_id = str(uuid.uuid4())
        job = await create_import_job(
            db_session,
            job_id=job_id,
            user_id=1,
            platform="chess.com",
            username="testuser",
        )
        assert job is not None
        assert job.id == job_id
        assert job.status == "pending"
        assert job.games_fetched == 0
        assert job.games_imported == 0

        fetched = await get_import_job(db_session, job_id)
        assert fetched is not None
        assert fetched.id == job_id
        assert fetched.platform == "chess.com"
        assert fetched.username == "testuser"

    async def test_get_nonexistent_job_returns_none(self, db_session):
        from app.repositories.import_job_repository import get_import_job
        result = await get_import_job(db_session, "nonexistent-id")
        assert result is None

    async def test_update_import_job(self, db_session):
        from app.repositories.import_job_repository import (
            create_import_job,
            get_import_job,
            update_import_job,
        )
        job_id = str(uuid.uuid4())
        await create_import_job(db_session, job_id=job_id, user_id=1,
                                platform="lichess", username="testuser")

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        await update_import_job(
            db_session,
            job_id=job_id,
            status="completed",
            games_fetched=100,
            games_imported=95,
            completed_at=now,
            last_synced_at=now,
        )

        job = await get_import_job(db_session, job_id)
        assert job is not None
        assert job.status == "completed"
        assert job.games_fetched == 100
        assert job.games_imported == 95

    async def test_get_latest_for_user_platform(self, db_session):
        from app.repositories.import_job_repository import (
            create_import_job,
            get_latest_for_user_platform,
            update_import_job,
        )
        user_id = 42  # Use distinct user_id to avoid cross-test interference
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        # Create two completed jobs
        job_id_1 = str(uuid.uuid4())
        job_id_2 = str(uuid.uuid4())
        await create_import_job(db_session, job_id=job_id_1, user_id=user_id,
                                platform="lichess", username="myuser")
        await create_import_job(db_session, job_id=job_id_2, user_id=user_id,
                                platform="lichess", username="myuser")

        earlier = now - datetime.timedelta(hours=1)
        await update_import_job(db_session, job_id=job_id_1, status="completed",
                                 completed_at=earlier, last_synced_at=earlier)
        await update_import_job(db_session, job_id=job_id_2, status="completed",
                                 completed_at=now, last_synced_at=now)

        # Should return the most recent completed job
        latest = await get_latest_for_user_platform(db_session, user_id=user_id, platform="lichess")
        assert latest is not None
        assert latest.id == job_id_2

    async def test_get_latest_returns_none_if_no_jobs(self, db_session):
        from app.repositories.import_job_repository import get_latest_for_user_platform
        result = await get_latest_for_user_platform(db_session, user_id=99999, platform="chess.com")
        assert result is None

    async def test_get_latest_returns_none_for_different_platform(self, db_session):
        from app.repositories.import_job_repository import (
            create_import_job,
            get_latest_for_user_platform,
            update_import_job,
        )
        user_id = 55
        job_id = str(uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        await create_import_job(db_session, job_id=job_id, user_id=user_id,
                                platform="lichess", username="myuser")
        await update_import_job(db_session, job_id=job_id, status="completed",
                                 completed_at=now, last_synced_at=now)

        # Query for chess.com should return None (only lichess job exists)
        result = await get_latest_for_user_platform(db_session, user_id=user_id, platform="chess.com")
        assert result is None
