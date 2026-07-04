"""Tests for game_repository and import_job_repository.

Uses real PostgreSQL with transaction rollback — each test is isolated.
"""

import datetime
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [1, 2, 42, 55]:
        await ensure_test_user(db_session, uid)


class TestBulkInsertGames:
    """Tests for bulk_insert_games with ON CONFLICT DO NOTHING."""

    def _make_game_row(self, platform_game_id: str, user_id: int = 1) -> dict:
        return {
            "user_id": user_id,
            "platform": "chess.com",
            "platform_game_id": platform_game_id,
            "platform_url": f"https://chess.com/game/{platform_game_id}",
            "pgn": '[Event "Test"]\n\n1. e4 *',
            "result": "1-0",
            "user_color": "white",
            "time_control_str": "600+0",
            "time_control_bucket": "blitz",
            "time_control_seconds": 600,
            "rated": True,
            "white_username": "testuser",
            "black_username": "Opponent",
            "white_rating": 1600,
            "black_rating": 1500,
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

    async def test_different_users_can_import_same_game(self, db_session):
        from app.repositories.game_repository import bulk_insert_games

        platform_game_id = "shared-game-123"

        # User 1 inserts the game
        ids_user1 = await bulk_insert_games(
            db_session, [self._make_game_row(platform_game_id, user_id=1)]
        )
        assert len(ids_user1) == 1, "User 1 should have their game inserted"

        # User 2 inserts the same platform_game_id — should NOT be blocked by user 1's row
        ids_user2 = await bulk_insert_games(
            db_session, [self._make_game_row(platform_game_id, user_id=2)]
        )
        assert len(ids_user2) == 1, "User 2 should also get their own copy of the game"

        # Both IDs should be distinct
        assert ids_user1[0] != ids_user2[0]

    async def test_same_user_duplicate_still_skipped(self, db_session):
        from app.repositories.game_repository import bulk_insert_games

        platform_game_id = "dup-game-456"

        # First insert for user 1
        ids_first = await bulk_insert_games(
            db_session, [self._make_game_row(platform_game_id, user_id=1)]
        )
        assert len(ids_first) == 1

        # Second insert of the same game for the same user — should be skipped
        ids_second = await bulk_insert_games(
            db_session, [self._make_game_row(platform_game_id, user_id=1)]
        )
        assert len(ids_second) == 0, "Same user importing same game twice should be deduplicated"


class TestBulkInsertPositions:
    """Tests for bulk_insert_positions."""

    def _make_game_row(self, platform_game_id: str) -> dict:
        return {
            "user_id": 1,
            "platform": "lichess",
            "platform_game_id": platform_game_id,
            "platform_url": f"https://lichess.org/{platform_game_id}",
            "pgn": '[Event "Test"]\n\n1. e4 e5 *',
            "result": "1/2-1/2",
            "user_color": "white",
            "time_control_str": "600+0",
            "time_control_bucket": "blitz",
            "time_control_seconds": 600,
            "rated": True,
            "white_username": "testuser",
            "black_username": None,
            "white_rating": 1500,
            "black_rating": None,
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
                "move_san": "e4",
            },
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 1,
                "full_hash": 22345678,
                "white_hash": 19876543,
                "black_hash": 11111111,
                "move_san": None,
            },
        ]
        # Should not raise
        await bulk_insert_positions(db_session, position_rows)

    async def test_insert_positions_with_move_san(self, db_session):
        from sqlalchemy import select
        from app.models.game_position import GamePosition
        from app.repositories.game_repository import bulk_insert_games, bulk_insert_positions

        row = self._make_game_row(f"lich-{__import__('uuid').uuid4().hex}")
        [game_id] = await bulk_insert_games(db_session, [row])

        position_rows = [
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 0,
                "full_hash": 11111111,
                "white_hash": 22222222,
                "black_hash": 33333333,
                "move_san": "e4",
            },
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 1,
                "full_hash": 44444444,
                "white_hash": 55555555,
                "black_hash": 66666666,
                "move_san": "e5",
            },
            {
                "game_id": game_id,
                "user_id": 1,
                "ply": 2,
                "full_hash": 77777777,
                "white_hash": 88888888,
                "black_hash": 99999999,
                "move_san": None,
            },
        ]
        await bulk_insert_positions(db_session, position_rows)

        result = await db_session.execute(
            select(GamePosition).where(GamePosition.game_id == game_id).order_by(GamePosition.ply)
        )
        rows = result.scalars().all()
        assert len(rows) == 3
        assert rows[0].move_san == "e4"
        assert rows[1].move_san == "e5"
        assert rows[2].move_san is None

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
        await create_import_job(
            db_session, job_id=job_id, user_id=1, platform="lichess", username="testuser"
        )

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

        # Create two completed jobs. Each is transitioned to "completed"
        # before the next is created (Phase 149 PRUNE-05: only one active
        # pending/in_progress row per user+platform is allowed by
        # uq_import_jobs_user_platform_active — two simultaneously-pending
        # rows for the same user+platform would raise IntegrityError).
        job_id_1 = str(uuid.uuid4())
        await create_import_job(
            db_session, job_id=job_id_1, user_id=user_id, platform="lichess", username="myuser"
        )
        earlier = now - datetime.timedelta(hours=1)
        await update_import_job(
            db_session,
            job_id=job_id_1,
            status="completed",
            completed_at=earlier,
            last_synced_at=earlier,
        )

        job_id_2 = str(uuid.uuid4())
        await create_import_job(
            db_session, job_id=job_id_2, user_id=user_id, platform="lichess", username="myuser"
        )
        await update_import_job(
            db_session, job_id=job_id_2, status="completed", completed_at=now, last_synced_at=now
        )

        # Should return the most recent completed job
        latest = await get_latest_for_user_platform(
            db_session, user_id=user_id, platform="lichess", username="myuser"
        )
        assert latest is not None
        assert latest.id == job_id_2

    async def test_get_latest_returns_none_if_no_jobs(self, db_session):
        from app.repositories.import_job_repository import get_latest_for_user_platform

        result = await get_latest_for_user_platform(
            db_session, user_id=99999, platform="chess.com", username="nobody"
        )
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
        await create_import_job(
            db_session, job_id=job_id, user_id=user_id, platform="lichess", username="myuser"
        )
        await update_import_job(
            db_session, job_id=job_id, status="completed", completed_at=now, last_synced_at=now
        )

        # Query for chess.com should return None (only lichess job exists)
        result = await get_latest_for_user_platform(
            db_session, user_id=user_id, platform="chess.com", username="myuser"
        )
        assert result is None


# ─── D-118: coverage / in-flight count functions ─────────────────────────────


class TestCountFullyAnalyzedGames:
    """count_fully_analyzed_games uses full_evals_completed_at IS NOT NULL.

    This is the badge numerator and matches the per-game Library card definition
    of "analyzed". It deliberately does NOT use white_blunders (is_analyzed):
    a lichess game imported with bundled analysis has white_blunders set at import
    but full_evals_completed_at NULL, so it must NOT count here (its card still
    shows "Analyze" until FlawChess's own drain runs).
    """

    def _make_game_row(
        self,
        platform_game_id: str,
        user_id: int = 55,
    ) -> dict:
        return {
            "user_id": user_id,
            "platform": "chess.com",
            "platform_game_id": platform_game_id,
            "platform_url": f"https://chess.com/game/{platform_game_id}",
            "pgn": '[Event "Test"]\n\n1. e4 *',
            "result": "1-0",
            "user_color": "white",
            "time_control_str": "600+0",
            "time_control_bucket": "blitz",
            "time_control_seconds": 600,
            "rated": True,
            "white_username": "testuser",
            "black_username": "Opponent",
            "white_rating": 1600,
            "black_rating": 1500,
            "opening_name": None,
            "opening_eco": None,
            "played_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        }

    async def test_fully_analyzed_count(self, db_session) -> None:
        """count_fully_analyzed_games counts full_evals_completed_at IS NOT NULL only.

        - id1: full_evals_completed_at SET (FlawChess analyzed) → counts.
        - id2: full_evals_completed_at SET but white_blunders NULL (degenerate /
          coverage-capped) → still counts (matches its card: no Analyze button).
        - id3: white_blunders SET but full_evals_completed_at NULL (lichess bundled
          analysis at import) → must NOT count.
        - id4: plain unanalyzed → must NOT count.
        """
        import uuid
        import sqlalchemy as sa
        from sqlalchemy import select
        from app.repositories.game_repository import bulk_insert_games, count_fully_analyzed_games
        from app.models.game import Game

        # User 55 is created by the autouse _create_test_users fixture; db_session is
        # rollback-scoped, so we assert the delta to tolerate any template rows.
        user_id = 55
        uid = uuid.uuid4().hex
        before = await count_fully_analyzed_games(db_session, user_id)

        rows = [self._make_game_row(f"fa-{uid}-{i}", user_id=user_id) for i in range(4)]
        ids = await bulk_insert_games(db_session, rows)
        assert len(ids) == 4, f"Expected 4 game IDs; got {len(ids)}"
        id1, id2, id3, id4 = ids

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        await db_session.execute(
            sa.update(Game)
            .where(Game.id == id1)
            .values(full_evals_completed_at=now, white_blunders=2, black_blunders=1)
        )
        # Degenerate: full-eval drain done, no flaw counts — still counts.
        await db_session.execute(
            sa.update(Game).where(Game.id == id2).values(full_evals_completed_at=now)
        )
        # Lichess bundled analysis: white_blunders at import, no full-eval drain yet.
        await db_session.execute(
            sa.update(Game).where(Game.id == id3).values(white_blunders=1, black_blunders=0)
        )
        await db_session.commit()

        count = await count_fully_analyzed_games(db_session, user_id)
        assert count - before == 2, (
            f"Expected exactly 2 newly fully-analyzed games (id1, id2); got delta "
            f"{count - before}. id3 (lichess bundled analysis) and id4 (unanalyzed) "
            "must not count."
        )

        # Direct verification: id3/id4 have full_evals_completed_at NULL.
        not_analyzed = await db_session.execute(
            select(Game.id).where(
                Game.id.in_([id3, id4]),
                Game.full_evals_completed_at.isnot(None),
            )
        )
        assert not_analyzed.fetchall() == [], (
            "id3 (white_blunders set, full_evals NULL) and id4 (unanalyzed) must "
            "have full_evals_completed_at NULL"
        )
