"""Wave 0 queue tests — QUEUE-01/02/05/06/08 (Phase 117 Plan 02).

Tests cover:
- QUEUE-01 / tier_priority:  tier-1 job is picked before tier-3-eligible games
- QUEUE-02 / round_robin:    two users alternate claim (oldest-pending-first)
- QUEUE-02 / tc_ordering:    classical picked before bullet within the same user
- QUEUE-05 / tier3_derived:  game with no eval_jobs row is returned by claim_eval_job
- QUEUE-06 / lease_expiry:   expired lease requeued to pending, claimable again
- QUEUE-08 / guest_exclusion: guest game never claimed; enqueue_tier1_game no-ops

Session patching mirrors test_full_eval_drain.py: monkeypatch
app.services.eval_queue_service.async_session_maker to the test DB session maker.
No real Stockfish or engine calls are needed — these are DB-level queue tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ─── Module-level test constants ──────────────────────────────────────────────

# Unique user IDs for this module to avoid FK conflicts with other test files.
# Range 99201–99299 reserved for test_eval_queue.py.
_TEST_USER_A_ID: int = 99201
_TEST_USER_B_ID: int = 99202
_TEST_GUEST_USER_ID: int = 99203

# Minimal PGN for games (no real analysis needed — queue tests are DB-level only).
_SIMPLE_PGN: str = "1. e4 e5 *"


# ─── Session-scoped fixtures ──────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def queue_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker bound to the test engine for queue tests."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=False)
async def queue_test_users(
    queue_session_maker: async_sessionmaker[AsyncSession],
) -> dict[str, int]:
    """Ensure test users exist in the test DB. Returns mapping of role -> user_id."""
    from app.models.user import User

    users = [
        User(
            id=_TEST_USER_A_ID,
            email=f"queue-test-a-{_TEST_USER_A_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
        User(
            id=_TEST_USER_B_ID,
            email=f"queue-test-b-{_TEST_USER_B_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
        User(
            id=_TEST_GUEST_USER_ID,
            email=f"queue-test-guest-{_TEST_GUEST_USER_ID}@example.com",
            hashed_password="fakehash",
            is_guest=True,
        ),
    ]

    async with queue_session_maker() as session:
        for u in users:
            existing = await session.execute(select(User).where(User.id == u.id))
            if existing.unique().scalar_one_or_none() is None:
                session.add(u)
        await session.commit()

    return {
        "user_a": _TEST_USER_A_ID,
        "user_b": _TEST_USER_B_ID,
        "guest": _TEST_GUEST_USER_ID,
    }


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def _insert_game(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    *,
    time_control_bucket: str | None = "blitz",
    played_at: datetime | None = None,
    full_evals_completed_at: datetime | None = None,
    lichess_evals_at: datetime | None = None,
) -> int:
    """Insert a Game row and commit. Returns game_id."""
    from app.models.game import Game

    async with session_maker() as session:
        g = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=f"queue-test-{uuid.uuid4().hex}",
            pgn=_SIMPLE_PGN,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
            time_control_bucket=time_control_bucket,
            played_at=played_at,
            full_evals_completed_at=full_evals_completed_at,
            lichess_evals_at=lichess_evals_at,
        )
        session.add(g)
        await session.flush()
        game_id = g.id
        await session.commit()
    return game_id


async def _insert_eval_job(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    *,
    tier: int = 2,
    status: str = "pending",
    created_at: datetime | None = None,
    lease_expiry: datetime | None = None,
) -> int:
    """Insert an EvalJob row and commit. Returns job_id."""
    from app.models.eval_jobs import EvalJob

    async with session_maker() as session:
        job = EvalJob(
            tier=tier,
            user_id=user_id,
            game_id=game_id,
            status=status,
            lease_expiry=lease_expiry,
        )
        if created_at is not None:
            # Override server_default created_at via direct attribute assignment.
            job.created_at = created_at
        session.add(job)
        await session.flush()
        job_id = job.id
        await session.commit()
    return job_id


async def _delete_games(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
) -> None:
    """Delete games by ID (CASCADE deletes eval_jobs too)."""
    from app.models.game import Game

    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


async def _delete_eval_jobs(
    session_maker: async_sessionmaker[AsyncSession],
    job_ids: list[int],
) -> None:
    """Delete EvalJob rows by ID."""
    from app.models.eval_jobs import EvalJob

    if not job_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(EvalJob).where(EvalJob.id.in_(job_ids)))
        await session.commit()


# ─── QUEUE-01: tier priority ──────────────────────────────────────────────────


class TestTierPriority:
    """QUEUE-01: tier-1 job is claimed before tier-3-eligible games."""

    async def test_tier_priority(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With a pending tier-1 row and a tier-3-eligible game, claim returns tier-1."""
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = queue_test_users["user_a"]
        now = datetime.now(timezone.utc)

        # Tier-3 eligible game: full_evals_completed_at IS NULL, no eval_jobs row.
        t3_game_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)

        # Tier-1 explicit eval_jobs row for another game.
        t1_game_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)
        t1_job_id = await _insert_eval_job(
            queue_session_maker, user_a, t1_game_id, tier=1, created_at=now
        )

        try:
            claimed = await svc.claim_eval_job()

            assert claimed is not None, "Expected a claimed job; got None"
            assert claimed.game_id == t1_game_id, (
                f"Expected tier-1 game {t1_game_id} to be claimed before "
                f"tier-3 game {t3_game_id}; got game_id={claimed.game_id}"
            )
            assert claimed.tier == 1, f"Expected tier=1, got tier={claimed.tier}"
            assert claimed.job_id == t1_job_id, "Tier-1 claim must return the eval_jobs row id"
        finally:
            await _delete_games(queue_session_maker, [t1_game_id, t3_game_id])


# ─── QUEUE-02: round-robin ────────────────────────────────────────────────────


class TestRoundRobin:
    """QUEUE-02: two users alternate claims (oldest-pending-first round-robin)."""

    async def test_round_robin(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """User A has the oldest pending job; user B's job is newer.

        First claim → user A (oldest MIN created_at).
        After A's job is claimed/completed, second claim → user B.
        """
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = queue_test_users["user_a"]
        user_b = queue_test_users["user_b"]
        now = datetime.now(timezone.utc)

        # User A's job is older.
        game_a_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)
        job_a_id = await _insert_eval_job(
            queue_session_maker,
            user_a,
            game_a_id,
            tier=2,
            created_at=now - timedelta(minutes=5),
        )

        # User B's job is newer.
        game_b_id = await _insert_game(queue_session_maker, user_b, full_evals_completed_at=None)
        job_b_id = await _insert_eval_job(
            queue_session_maker,
            user_b,
            game_b_id,
            tier=2,
            created_at=now,
        )

        try:
            # First claim: should pick user A (oldest MIN created_at).
            first = await svc.claim_eval_job()
            assert first is not None, "First claim returned None; expected user A's job"
            assert first.game_id == game_a_id, (
                f"Expected user A's game {game_a_id} first (oldest pending); got {first.game_id}"
            )
            assert first.job_id == job_a_id

            # Mark A complete so the queue moves to B.
            if first.job_id is not None:
                await svc.report_job_complete(first.job_id)

            # Second claim: should pick user B.
            second = await svc.claim_eval_job()
            assert second is not None, "Second claim returned None; expected user B's job"
            assert second.game_id == game_b_id, (
                f"Expected user B's game {game_b_id} second; got {second.game_id}"
            )
            assert second.job_id == job_b_id
        finally:
            await _delete_games(queue_session_maker, [game_a_id, game_b_id])


# ─── QUEUE-02: TC ordering ────────────────────────────────────────────────────


class TestTcOrdering:
    """QUEUE-02: within a user, classical is picked before bullet (D-117-04)."""

    async def test_tc_ordering(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Same user has a bullet and a classical game in the queue.
        The classical game must be claimed first (CASE ordering weight 0 vs 3).
        """
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = queue_test_users["user_a"]
        now = datetime.now(timezone.utc)

        # Insert bullet game first (to verify TC ordering overrides insertion order).
        bullet_game_id = await _insert_game(
            queue_session_maker,
            user_a,
            time_control_bucket="bullet",
            played_at=now,
            full_evals_completed_at=None,
        )
        classical_game_id = await _insert_game(
            queue_session_maker,
            user_a,
            time_control_bucket="classical",
            played_at=now,
            full_evals_completed_at=None,
        )

        # Both tier-2 jobs with the same created_at (same user, so round-robin is N/A).
        await _insert_eval_job(queue_session_maker, user_a, bullet_game_id, tier=2, created_at=now)
        classical_job_id = await _insert_eval_job(
            queue_session_maker, user_a, classical_game_id, tier=2, created_at=now
        )

        try:
            claimed = await svc.claim_eval_job()
            assert claimed is not None, "Expected a claimed job; got None"
            assert claimed.game_id == classical_game_id, (
                f"Classical game {classical_game_id} must be claimed before "
                f"bullet game {bullet_game_id}; got game_id={claimed.game_id}"
            )
            assert claimed.job_id == classical_job_id
        finally:
            await _delete_games(queue_session_maker, [bullet_game_id, classical_game_id])


# ─── QUEUE-05: tier-3 derived pick ───────────────────────────────────────────


class TestTier3Derived:
    """QUEUE-05: tier-3 pick returns a game with no eval_jobs row."""

    async def test_tier3_derived(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A game with full_evals_completed_at IS NULL and NO eval_jobs row is
        returned by claim_eval_job with job_id=None and tier=3."""
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import TIER_IDLE_BACKLOG

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = queue_test_users["user_a"]

        # No eval_jobs row — pure tier-3 candidate.
        game_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)

        try:
            claimed = await svc.claim_eval_job()
            assert claimed is not None, "Expected a tier-3 derived pick; got None"
            assert claimed.game_id == game_id, (
                f"Expected game {game_id} to be picked; got {claimed.game_id}"
            )
            assert claimed.job_id is None, (
                f"Tier-3 derived pick must return job_id=None; got {claimed.job_id}"
            )
            assert claimed.tier == TIER_IDLE_BACKLOG, (
                f"Expected tier={TIER_IDLE_BACKLOG}, got {claimed.tier}"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id])


# ─── QUEUE-06: lease expiry / requeue ────────────────────────────────────────


class TestLeaseExpiry:
    """QUEUE-06: expired lease is requeued to pending and re-claimable."""

    async def test_lease_expiry(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Claim a job, set its lease_expiry into the past, call
        requeue_expired_leases (or next claim's sweep), and verify the job
        is back in 'pending' status and is re-claimable.
        """
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import EvalJob

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = queue_test_users["user_a"]

        game_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)
        job_id = await _insert_eval_job(queue_session_maker, user_a, game_id, tier=2)

        try:
            # Claim the job — status transitions to 'leased'.
            claimed = await svc.claim_eval_job()
            assert claimed is not None, "Initial claim returned None"
            assert claimed.job_id == job_id

            # Verify the job is now leased.
            async with queue_session_maker() as session:
                result = await session.execute(
                    select(EvalJob.status, EvalJob.lease_expiry).where(EvalJob.id == job_id)
                )
                row = result.one()
            assert row[0] == "leased", f"Expected status='leased', got {row[0]!r}"
            assert row[1] is not None, "lease_expiry must be set after claim"

            # Wind the lease_expiry back into the past to simulate expiry.
            past_expiry = datetime.now(timezone.utc) - timedelta(minutes=10)
            async with queue_session_maker() as session:
                await session.execute(
                    update(EvalJob.__table__)  # ty: ignore[invalid-argument-type]
                    .where(EvalJob.__table__.c.id == job_id)
                    .values(lease_expiry=past_expiry)
                )
                await session.commit()

            # Requeue via the standalone helper.
            requeued_count = await svc.requeue_expired_leases()
            assert requeued_count >= 1, f"Expected at least 1 row requeued; got {requeued_count}"

            # Verify status is back to 'pending'.
            async with queue_session_maker() as session:
                result = await session.execute(select(EvalJob.status).where(EvalJob.id == job_id))
                status_after = result.scalar_one()
            assert status_after == "pending", (
                f"Expected status='pending' after requeue; got {status_after!r}"
            )

            # Confirm the job is re-claimable.
            reclaimed = await svc.claim_eval_job()
            assert reclaimed is not None, "Job should be re-claimable after lease expiry"
            assert reclaimed.game_id == game_id
        finally:
            await _delete_games(queue_session_maker, [game_id])


# ─── QUEUE-08: guest exclusion ───────────────────────────────────────────────


class TestGuestExclusion:
    """QUEUE-08: guest games are never claimed; enqueue_tier1_game no-ops for guests."""

    async def test_guest_exclusion(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A guest user's game must never be claimed from tier-3 derived pick,
        and enqueue_tier1_game must return False for a guest game (QUEUE-08).
        """
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import EvalJob

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        guest_user_id = queue_test_users["guest"]

        # Guest game eligible for tier-3 (full_evals_completed_at IS NULL).
        guest_game_id = await _insert_game(
            queue_session_maker, guest_user_id, full_evals_completed_at=None
        )

        try:
            # Tier-3 derived pick must not return the guest's game.
            claimed = await svc.claim_eval_job()
            if claimed is not None:
                assert claimed.game_id != guest_game_id, (
                    f"Guest game {guest_game_id} must never be claimed via tier-3 pick; "
                    f"got game_id={claimed.game_id}"
                )

            # enqueue_tier1_game must return False for a guest game.
            inserted = await svc.enqueue_tier1_game(game_id=guest_game_id, user_id=guest_user_id)
            assert inserted is False, (
                "enqueue_tier1_game must return False for a guest user's game (QUEUE-08)"
            )

            # No eval_jobs row should exist for the guest game.
            async with queue_session_maker() as session:
                result = await session.execute(
                    select(EvalJob).where(EvalJob.game_id == guest_game_id)
                )
                jobs = result.scalars().all()
            assert len(jobs) == 0, (
                f"No eval_jobs rows should exist for guest game {guest_game_id}; found {len(jobs)}"
            )
        finally:
            await _delete_games(queue_session_maker, [guest_game_id])
