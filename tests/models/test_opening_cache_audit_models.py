"""Round-trip tests for the Phase 220 opening cache repair audit models (CACHEFIX-01).

Coverage:
- test_opening_cache_audit_round_trip : insert + read back OpeningCacheAudit
  with every column populated, including the D-06 hash_mismatch_attempts
  counter and its server_default of 0.
- test_opening_cache_repair_row_round_trip : insert + read back
  OpeningCacheRepairRow with its composite (game_id, ply) PK.
- test_opening_cache_repair_game_round_trip : insert + read back
  OpeningCacheRepairGame with its FK to both games and users.
- test_opening_cache_repair_progress_round_trip : insert + read back the
  singleton OpeningCacheRepairProgress row (id=1) with a per-stage
  started_at/finished_at pair populated.
- test_opening_cache_audit_status_check_rejects_ninth_value : the status
  CHECK accepts only the eight literals; a ninth raises IntegrityError.
- test_opening_cache_repair_progress_rejects_second_row : the id=1 CHECK
  makes the table a true singleton; a second row (id=2) raises IntegrityError.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.opening_cache_audit import (
    OpeningCacheAudit,
    OpeningCacheRepairGame,
    OpeningCacheRepairProgress,
    OpeningCacheRepairRow,
)

_TEST_USER_ID = 77801


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    """Ensure the FK-target test user exists (FK constraint on repair_games.user_id)."""
    from tests.conftest import ensure_test_user

    await ensure_test_user(db_session, _TEST_USER_ID)


async def _seed_game(session: AsyncSession, *, user_id: int = _TEST_USER_ID) -> Game:
    """Insert a minimal Game row and flush to obtain an ID."""
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game


class TestOpeningCacheAuditRoundTrip:
    @pytest.mark.asyncio
    async def test_opening_cache_audit_round_trip(self, db_session: AsyncSession) -> None:
        """OpeningCacheAudit round-trips every column, including the D-06 retry counter."""
        game = await _seed_game(db_session)
        now = datetime.now(timezone.utc)
        row = OpeningCacheAudit(
            full_hash=-3185735734450884963,
            status="flagged",
            old_cp=42,
            old_mate=None,
            old_best_move="e2e4",
            old_pv="e2e4 e7e5",
            sample_game_id=game.id,
            sample_ply=5,
            screen_cp=190,
            screen_mate=None,
            screened_at=now,
            full_cp=None,
            full_mate=None,
            delta_score=0.12,
            delta_cp=148,
            engine_version="Stockfish 18",
            hash_mismatch_attempts=1,
        )
        db_session.add(row)
        await db_session.flush()

        fetched = (
            await db_session.execute(
                select(OpeningCacheAudit).where(OpeningCacheAudit.full_hash == -3185735734450884963)
            )
        ).scalar_one()
        assert fetched.status == "flagged"
        assert fetched.old_cp == 42
        assert fetched.old_best_move == "e2e4"
        assert fetched.sample_game_id == game.id
        assert fetched.sample_ply == 5
        assert fetched.screen_cp == 190
        assert fetched.delta_score == pytest.approx(0.12)
        assert fetched.delta_cp == 148
        assert fetched.engine_version == "Stockfish 18"
        assert fetched.hash_mismatch_attempts == 1
        assert fetched.repaired_at is None

    @pytest.mark.asyncio
    async def test_opening_cache_audit_hash_mismatch_attempts_defaults_zero(
        self, db_session: AsyncSession
    ) -> None:
        """hash_mismatch_attempts has a server_default of 0 when omitted."""
        row = OpeningCacheAudit(full_hash=123456789, status="pending")
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)
        assert row.hash_mismatch_attempts == 0

    @pytest.mark.asyncio
    async def test_opening_cache_audit_status_check_rejects_ninth_value(
        self, db_session: AsyncSession
    ) -> None:
        """The status CHECK accepts only the eight literals; a ninth raises IntegrityError."""
        row = OpeningCacheAudit(full_hash=987654321, status="not_a_real_status")
        db_session.add(row)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestOpeningCacheRepairRowRoundTrip:
    @pytest.mark.asyncio
    async def test_opening_cache_repair_row_round_trip(self, db_session: AsyncSession) -> None:
        """OpeningCacheRepairRow round-trips with its composite (game_id, ply) PK."""
        game = await _seed_game(db_session)
        row = OpeningCacheRepairRow(
            game_id=game.id,
            ply=7,
            full_hash=555,
            old_cp=200,
            old_mate=None,
            new_cp=40,
            new_mate=None,
            best_move_replaced=True,
            pv_replaced=False,
        )
        db_session.add(row)
        await db_session.flush()

        fetched = (
            await db_session.execute(
                select(OpeningCacheRepairRow).where(
                    OpeningCacheRepairRow.game_id == game.id,
                    OpeningCacheRepairRow.ply == 7,
                )
            )
        ).scalar_one()
        assert fetched.full_hash == 555
        assert fetched.old_cp == 200
        assert fetched.new_cp == 40
        assert fetched.best_move_replaced is True
        assert fetched.pv_replaced is False
        assert fetched.repaired_at is not None


class TestOpeningCacheRepairGameRoundTrip:
    @pytest.mark.asyncio
    async def test_opening_cache_repair_game_round_trip(self, db_session: AsyncSession) -> None:
        """OpeningCacheRepairGame round-trips with FKs to both games and users."""
        game = await _seed_game(db_session)
        row = OpeningCacheRepairGame(
            game_id=game.id,
            user_id=_TEST_USER_ID,
            status="reclassified",
            rows_repaired=3,
            flaws_before_blund=2,
            flaws_after_blund=1,
            flaws_removed=1,
            white_accuracy_before=88.5,
            white_accuracy_after=91.2,
            white_acpl_before=35,
            white_acpl_after=28,
        )
        db_session.add(row)
        await db_session.flush()

        fetched = (
            await db_session.execute(
                select(OpeningCacheRepairGame).where(OpeningCacheRepairGame.game_id == game.id)
            )
        ).scalar_one()
        assert fetched.user_id == _TEST_USER_ID
        assert fetched.status == "reclassified"
        assert fetched.rows_repaired == 3
        assert fetched.flaws_removed == 1
        assert fetched.white_accuracy_before == pytest.approx(88.5)
        assert fetched.white_acpl_after == 28
        # server_default counters not explicitly set stay at 0.
        assert fetched.flaws_added == 0
        assert fetched.herrings_touched == 0


class TestOpeningCacheRepairProgressRoundTrip:
    @pytest.mark.asyncio
    async def test_opening_cache_repair_progress_round_trip(self, db_session: AsyncSession) -> None:
        """The singleton progress row (id=1) round-trips a per-stage timestamp pair."""
        now = datetime.now(timezone.utc)
        row = OpeningCacheRepairProgress(
            id=1,
            last_game_id_walked=42,
            screen_floor=0.08,
            confirm_floor=0.05,
            calibration_n=500,
            calibrated_at=now,
            engine_version="Stockfish 18",
            seed_started_at=now,
            seed_finished_at=now,
        )
        db_session.add(row)
        await db_session.flush()

        fetched = (
            await db_session.execute(
                select(OpeningCacheRepairProgress).where(OpeningCacheRepairProgress.id == 1)
            )
        ).scalar_one()
        assert fetched.last_game_id_walked == 42
        assert fetched.screen_floor == pytest.approx(0.08)
        assert fetched.confirm_floor == pytest.approx(0.05)
        assert fetched.calibration_n == 500
        assert fetched.seed_finished_at is not None
        assert fetched.calibrate_finished_at is None

    @pytest.mark.asyncio
    async def test_opening_cache_repair_progress_rejects_second_row(
        self, db_session: AsyncSession
    ) -> None:
        """The id=1 CHECK makes the table a true singleton; a second row raises IntegrityError."""
        row = OpeningCacheRepairProgress(id=2)
        db_session.add(row)
        with pytest.raises(IntegrityError):
            await db_session.flush()
