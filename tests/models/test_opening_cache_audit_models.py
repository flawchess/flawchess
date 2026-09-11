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
- TestMigrationMarking::test_migration_marking_matches_status : Phase 220
  release-2 migration (b7d4f5a60002) MARK_CONFIRMED_SQL, executed via its own
  exported constant (not a paraphrase), against a cache row seeded for each of
  the eight opening_cache_audit statuses -- confirms exactly the three
  post-repair statuses (screened_clean, confirmed_clean, repaired) and leaves
  every other status a candidate.
- TestMigrationMarking::test_new_columns_default_on_plain_insert : the seven
  CACHEFIX-08 columns' defaults on a plain OpeningPositionEval insert.
"""

from __future__ import annotations

import importlib.util
import pathlib
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.opening_cache_audit import (
    OpeningCacheAudit,
    OpeningCacheRepairGame,
    OpeningCacheRepairProgress,
    OpeningCacheRepairRow,
)
from app.models.opening_position_eval import OpeningPositionEval

# All eight opening_cache_audit statuses (ck_opening_cache_audit_status). Only
# the first three are the release-1 repair's post-repair "verified" statuses;
# the migration must mark exactly those confirmed=true.
_CONFIRMED_STATUSES = ("screened_clean", "confirmed_clean", "repaired")
_CANDIDATE_STATUSES = (
    "pending",
    "flagged",
    "confirmed_bad",
    "orphan",
    "hash_mismatch",
)
_ALL_STATUSES = _CONFIRMED_STATUSES + _CANDIDATE_STATUSES


def _load_migration_module():
    """Load the Phase 220 release-2 migration by path (not an importable package --
    alembic/versions filenames start with a digit, same pattern as
    tests/test_normalization.py::TestMigrationBackfillSqlMatchesPythonHelper).
    """
    migration_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "alembic"
        / "versions"
        / "20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("_phase_220_r2_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


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


class TestMigrationMarking:
    """Phase 220 release-2 migration (b7d4f5a60002): MARK_CONFIRMED_SQL, executed
    as the exact statement the migration runs, must mark confirmed=true only for
    the three post-repair audit statuses.
    """

    @pytest.mark.asyncio
    async def test_migration_marking_matches_status(self, db_session: AsyncSession) -> None:
        migration = _load_migration_module()

        # Seed one opening_position_eval + opening_cache_audit pair per status,
        # keyed by a distinct full_hash per status so the assertion below can
        # attribute each outcome unambiguously.
        hash_by_status = {status: -(1000 + i) for i, status in enumerate(_ALL_STATUSES)}
        for status, full_hash in hash_by_status.items():
            db_session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=10, best_move="e2e4"))
            db_session.add(OpeningCacheAudit(full_hash=full_hash, status=status))
        await db_session.flush()

        # Execute the migration's own exported statement -- not a paraphrase --
        # with a single unbounded pass (cursor=None, a generous batch size),
        # exactly as the migration's keyset walk executes it per-pass.
        await db_session.execute(
            text(migration.MARK_CONFIRMED_SQL),
            {"cursor": None, "batch_size": 1000},
        )

        rows = (
            await db_session.execute(
                select(
                    OpeningPositionEval.full_hash,
                    OpeningPositionEval.confirmed,
                    OpeningPositionEval.n_sources,
                    OpeningPositionEval.confirmed_at,
                ).where(OpeningPositionEval.full_hash.in_(hash_by_status.values()))
            )
        ).all()
        assert len(rows) == len(_ALL_STATUSES)

        by_hash = {
            full_hash: (confirmed, n_sources, confirmed_at)
            for full_hash, confirmed, n_sources, confirmed_at in rows
        }

        for status in _CONFIRMED_STATUSES:
            confirmed, n_sources, confirmed_at = by_hash[hash_by_status[status]]
            assert confirmed is True, f"status={status} should be marked confirmed"
            assert n_sources == 2, f"status={status} should have n_sources=2"
            assert confirmed_at is not None, f"status={status} should have confirmed_at set"

        for status in _CANDIDATE_STATUSES:
            confirmed, n_sources, confirmed_at = by_hash[hash_by_status[status]]
            assert confirmed is False, f"status={status} must stay a candidate"
            assert n_sources == 1, f"status={status} must stay n_sources=1"
            assert confirmed_at is None, f"status={status} must not have confirmed_at set"

    @pytest.mark.asyncio
    async def test_new_columns_default_on_plain_insert(self, db_session: AsyncSession) -> None:
        """The seven CACHEFIX-08 columns default correctly on a plain insert."""
        row = OpeningPositionEval(full_hash=-999999, eval_cp=5)
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)

        assert row.confirmed is False
        assert row.n_sources == 1
        assert row.disagreements == 0
        assert row.engine_version is None
        assert row.written_at is None
        assert row.confirmed_at is None
        assert row.source_game_id is None
