"""Wave 0 queue tests — QUEUE-01/02/05/06/08 (Phase 117 Plan 02).

Tests cover:
- QUEUE-01 / tier_priority:  tier-1 job is picked before tier-3-eligible games
- QUEUE-02 / round_robin:    two users alternate claim (oldest-pending-first)
- QUEUE-02 / tc_ordering:    classical picked before bullet within the same user
- QUEUE-05 / tier3_derived:  game with no eval_jobs row is returned by claim_eval_job
- QUEUE-06 / lease_expiry:   expired lease requeued to pending, claimable again
- QUEUE-08 / guest_exclusion: guest tier-1 enqueue allowed + worker drain; tier-3 still excluded

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
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ─── Module-level test constants ──────────────────────────────────────────────

# Unique user IDs for this module to avoid FK conflicts with other test files.
# Range 99201–99299 reserved for test_eval_queue.py.
_TEST_USER_A_ID: int = 99201
_TEST_USER_B_ID: int = 99202
_TEST_GUEST_USER_ID: int = 99203

# Minimal PGN for games (no real analysis needed — queue tests are DB-level only).
_SIMPLE_PGN: str = "1. e4 e5 *"


# ─── Auto-drain flag ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _enable_auto_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default EVAL_AUTO_DRAIN_ENABLED=True for every test in this module so the
    positive-path enqueue/claim tests are independent of the ambient .env (dev sets
    it False, which would make those tests hit the early-return — phase-117 commit
    5f36f85e added the gate without re-pinning the positive paths). Negative-path
    tests override it back to False inside their own body, which runs after this
    fixture, so this default does not mask them.
    """
    import app.services.eval_queue_service as svc

    monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", True)


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

    async def test_tier3_disabled_returns_none(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With EVAL_AUTO_DRAIN_ENABLED=False, the same tier-3 candidate that
        would otherwise be picked yields None — the idle backlog drain is off."""
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)
        monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", False)

        user_a = queue_test_users["user_a"]

        # Identical setup to test_tier3_derived: a pure tier-3 candidate.
        game_id = await _insert_game(queue_session_maker, user_a, full_evals_completed_at=None)

        try:
            claimed = await svc.claim_eval_job()
            assert claimed is None, f"Tier-3 drain disabled must return None; got {claimed!r}"
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
    """QUEUE-08: tier-1 explicit guest enqueue is allowed; tier-3 bulk stays guest-excluded.

    A guest may enqueue their own game for on-demand tier-1 analysis via
    enqueue_tier1_game, and the worker can drain that job via _claim_queued_job
    (OR ej.tier = 1). Automatic tier-3 bulk/idle analysis remains gated to
    authenticated users — both _claim_tier3_derived filters are unchanged.
    """

    async def test_guest_exclusion(
        self,
        queue_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """(a) Tier-3 derived pick must never return a guest's game (unchanged).
        (b) enqueue_tier1_game must return True for a guest's own game (QUEUE-08 opened).
        (c) The resulting tier-1 job must be claimable by the worker via _claim_queued_job.
        """
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import EvalJob
        from app.services.eval_queue_service import (
            LEASE_TTL_SECONDS,
            WORKER_ID_SERVER_POOL,
            _claim_queued_job,
        )

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        guest_user_id = queue_test_users["guest"]

        # Guest game eligible for tier-3 (full_evals_completed_at IS NULL).
        guest_game_id = await _insert_game(
            queue_session_maker, guest_user_id, full_evals_completed_at=None
        )

        try:
            # (a) Tier-3 derived pick must not return the guest's game.
            claimed = await svc.claim_eval_job()
            if claimed is not None:
                assert claimed.game_id != guest_game_id, (
                    f"Guest game {guest_game_id} must never be claimed via tier-3 pick; "
                    f"got game_id={claimed.game_id}"
                )

            # (b) Tier-1 explicit enqueue must succeed for a guest's own game.
            inserted = await svc.enqueue_tier1_game(game_id=guest_game_id, user_id=guest_user_id)
            assert inserted is True, (
                "enqueue_tier1_game must return True for a guest's own game (QUEUE-08 opened)"
            )

            # A tier-1 eval_jobs row must now exist for the guest game.
            async with queue_session_maker() as session:
                result = await session.execute(
                    select(EvalJob).where(EvalJob.game_id == guest_game_id)
                )
                jobs = result.scalars().all()
            assert len(jobs) == 1, (
                f"Exactly one tier-1 eval_jobs row must exist for guest game "
                f"{guest_game_id}; found {len(jobs)}"
            )
            assert jobs[0].tier == 1, f"Enqueued job must have tier=1; got tier={jobs[0].tier}"

            # (c) The worker must be able to drain the guest's explicit tier-1 job.
            async with queue_session_maker() as session:
                claimed_row = await _claim_queued_job(
                    session, WORKER_ID_SERVER_POOL, LEASE_TTL_SECONDS
                )
            assert claimed_row is not None, (
                "Worker must be able to claim the guest's tier-1 eval job "
                "via _claim_queued_job (OR ej.tier = 1 path)"
            )
            _job_id, claimed_game_id, _user_id, _tier, _is_lichess = claimed_row
            assert claimed_game_id == guest_game_id, (
                f"Worker must claim guest game {guest_game_id}; got game_id={claimed_game_id}"
            )
        finally:
            await _delete_games(queue_session_maker, [guest_game_id])


# ─── D-118-04: tier-3 ordering test fixtures ─────────────────────────────────

# Unique user IDs for queue-ordering tests — range 99210–99219 reserved.
_TEST_USER_TIER2_ID: int = 99210
_TEST_GUEST_TIER2_ID: int = 99211
_TEST_USER_TIER3_A_ID: int = 99212
_TEST_USER_TIER3_B_ID: int = 99213


@pytest_asyncio.fixture(scope="session", autouse=False)
async def tier2_test_users(
    queue_session_maker: async_sessionmaker[AsyncSession],
) -> dict[str, int]:
    """Ensure tier-2/tier-3 ordering test users exist. Returns mapping role -> user_id."""
    from app.models.user import User

    users = [
        User(
            id=_TEST_USER_TIER2_ID,
            email=f"tier2-test-{_TEST_USER_TIER2_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
        User(
            id=_TEST_GUEST_TIER2_ID,
            email=f"tier2-guest-{_TEST_GUEST_TIER2_ID}@example.com",
            hashed_password="fakehash",
            is_guest=True,
        ),
        User(
            id=_TEST_USER_TIER3_A_ID,
            email=f"tier3-a-{_TEST_USER_TIER3_A_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
        User(
            id=_TEST_USER_TIER3_B_ID,
            email=f"tier3-b-{_TEST_USER_TIER3_B_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
    ]

    async with queue_session_maker() as session:
        for u in users:
            existing = await session.execute(select(User).where(User.id == u.id))
            if existing.unique().scalar_one_or_none() is None:
                session.add(u)
        await session.commit()

    return {
        "user": _TEST_USER_TIER2_ID,
        "guest": _TEST_GUEST_TIER2_ID,
        "tier3_a": _TEST_USER_TIER3_A_ID,
        "tier3_b": _TEST_USER_TIER3_B_ID,
    }


class TestTier3Lottery:
    """SEED-046: _claim_tier3_derived recency-weighted ES lottery.

    Replaces the old D-118-04 deterministic 'active user first' ordering with a
    probabilistic weighted lottery. Tests assert distribution properties, not
    strict ordering.
    """

    async def test_tier3_recency_weighting(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A recently-active user wins the lottery in a strong majority of draws.

        user_a: last_activity = now (weight ≈ 1.0)
        user_b: last_activity = now - 30d (weight ≈ floor, ~0.005)
        Over N=400 draws, user_a must win >65% (strong majority with >floor dominance).
        The lottery is probabilistic — assert a distribution, not strict ordering.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = tier2_test_users["tier3_a"]
        user_b = tier2_test_users["tier3_b"]

        now = datetime.now(timezone.utc)
        # user_a is very recently active; user_b is 30d stale (≈floor weight)
        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_a).values(last_activity=now)
            )
            await session.execute(
                sa_update(User)
                .where(User.id == user_b)
                .values(last_activity=now - timedelta(days=30))
            )
            await session.commit()

        game_a = await _insert_game(
            queue_session_maker, user_a, full_evals_completed_at=None, lichess_evals_at=None
        )
        game_b = await _insert_game(
            queue_session_maker, user_b, full_evals_completed_at=None, lichess_evals_at=None
        )

        # Ensure no other non-guest users with engine-backlog games bleed into this test.
        # We monkeypatch _claim_tier3_derived directly to count per-user selection.
        # But first isolate: use the raw function under test directly.
        from app.services.eval_queue_service import _claim_tier3_derived

        n_draws = 400
        count_a = 0
        count_b = 0
        try:
            async with queue_session_maker() as session:
                for _ in range(n_draws):
                    result = await _claim_tier3_derived(session)
                    if result is not None:
                        picked_game_id = result[0]
                        if picked_game_id == game_a:
                            count_a += 1
                        elif picked_game_id == game_b:
                            count_b += 1

            total = count_a + count_b
            assert total > 0, "Expected at least some draws to return a game"
            share_a = count_a / total
            assert share_a > 0.65, (
                f"Recently-active user_a should win >65% of draws; "
                f"got {share_a:.1%} ({count_a}/{total})"
            )
        finally:
            await _delete_games(queue_session_maker, [game_a, game_b])

    async def test_tier3_near_uniform_when_stale(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When both users are equally stale (floor-dominated), neither is starved.

        Both users with last_activity=now-60d have near-floor weight → floor-dominated
        → near-uniform distribution. Over N=400 draws, neither user should have <20%
        share (with 2 users, uniform = 50%; 20% is a generous tolerance for floor noise).
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_a = tier2_test_users["tier3_a"]
        user_b = tier2_test_users["tier3_b"]

        now = datetime.now(timezone.utc)
        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User)
                .where(User.id == user_a)
                .values(last_activity=now - timedelta(days=60))
            )
            await session.execute(
                sa_update(User)
                .where(User.id == user_b)
                .values(last_activity=now - timedelta(days=60))
            )
            await session.commit()

        game_a = await _insert_game(
            queue_session_maker, user_a, full_evals_completed_at=None, lichess_evals_at=None
        )
        game_b = await _insert_game(
            queue_session_maker, user_b, full_evals_completed_at=None, lichess_evals_at=None
        )

        from app.services.eval_queue_service import _claim_tier3_derived

        n_draws = 400
        count_a = 0
        count_b = 0
        try:
            async with queue_session_maker() as session:
                for _ in range(n_draws):
                    result = await _claim_tier3_derived(session)
                    if result is not None:
                        picked_game_id = result[0]
                        if picked_game_id == game_a:
                            count_a += 1
                        elif picked_game_id == game_b:
                            count_b += 1

            total = count_a + count_b
            assert total > 0, "Expected some draws"
            share_a = count_a / total
            share_b = count_b / total
            assert share_a > 0.20, (
                f"user_a should not be starved when both stale; got {share_a:.1%}"
            )
            assert share_b > 0.20, (
                f"user_b should not be starved when both stale; got {share_b:.1%}"
            )
        finally:
            await _delete_games(queue_session_maker, [game_a, game_b])

    async def test_tier3_never_picks_lichess_while_engine_candidate_exists(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The leak fix: with a needs-engine game and a lichess-eval game for the same
        user (both full_evals_completed_at IS NULL), the primary lottery NEVER picks the
        lichess-eval game while the needs-engine game exists.

        Replaces the old test_tier3_pv_ordering single-pick assertion with a
        'never picks lichess while engine candidate exists' assertion.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]
        now = datetime.now(timezone.utc)

        # Set user as recently active to ensure they participate in the lottery.
        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_id).values(last_activity=now)
            )
            await session.commit()

        # needs-engine game: lichess_evals_at IS NULL → should be the primary candidate
        needs_engine_game = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=None,
            lichess_evals_at=None,
            played_at=now,
        )
        # lichess-eval game: lichess_evals_at IS NOT NULL → excluded from primary lottery
        lichess_game = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=None,
            lichess_evals_at=now,
            played_at=now,
        )

        from app.services.eval_queue_service import _claim_tier3_derived

        try:
            async with queue_session_maker() as session:
                for i in range(20):
                    result = await _claim_tier3_derived(session)
                    assert result is not None, f"Draw {i}: expected a result, got None"
                    picked_game_id = result[0]
                    assert picked_game_id == needs_engine_game, (
                        f"Draw {i}: primary lottery must NEVER pick the lichess-eval "
                        f"game {lichess_game} while needs-engine game {needs_engine_game} "
                        f"exists; got {picked_game_id}"
                    )
        finally:
            await _delete_games(queue_session_maker, [needs_engine_game, lichess_game])

    async def test_tier3_residual_fallback(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Residual fallback: when NO needs-engine game exists, the residual tier
        returns a PV-backfill-only lichess game (lichess_evals_at IS NOT NULL).

        is_lichess_eval_game must be True for such a residual pick.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]
        now = datetime.now(timezone.utc)

        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_id).values(last_activity=now)
            )
            await session.commit()

        # Only a PV-backfill-only game — no needs-engine candidate anywhere.
        pv_only_game = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=None,
            lichess_evals_at=now,
            played_at=now,
        )

        from app.services.eval_queue_service import _claim_tier3_derived

        try:
            async with queue_session_maker() as session:
                result = await _claim_tier3_derived(session)
            assert result is not None, "Residual fallback must return the PV-only game"
            picked_game_id, picked_user_id, is_lichess_eval_game = result
            assert picked_game_id == pv_only_game, (
                f"Residual fallback must return pv_only_game {pv_only_game}; got {picked_game_id}"
            )
            assert is_lichess_eval_game is True, (
                "Residual pick of a lichess-eval game must set is_lichess_eval_game=True"
            )
        finally:
            await _delete_games(queue_session_maker, [pv_only_game])

    async def test_tier3_guest_excluded_from_lottery(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A guest user with a backlog is never selected by the lottery (QUEUE-08)."""
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        guest_id = tier2_test_users["guest"]
        now = datetime.now(timezone.utc)

        # Set guest as recently active (so they would win if the guest check is absent).
        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == guest_id).values(last_activity=now)
            )
            await session.commit()

        guest_game = await _insert_game(
            queue_session_maker,
            guest_id,
            full_evals_completed_at=None,
            lichess_evals_at=None,
        )

        from app.services.eval_queue_service import _claim_tier3_derived

        try:
            async with queue_session_maker() as session:
                for i in range(10):
                    result = await _claim_tier3_derived(session)
                    if result is not None:
                        assert result[0] != guest_game, (
                            f"Draw {i}: guest game {guest_game} must never be picked by lottery"
                        )
        finally:
            await _delete_games(queue_session_maker, [guest_game])

    async def test_tier3_claimed_job_has_is_lichess_eval_game(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ClaimedJob from a primary lottery pick has is_lichess_eval_game=False.
        The field was renamed from is_analyzed (opportunistic D cleanup).
        """
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=None,
            lichess_evals_at=None,
        )

        try:
            claimed = await svc.claim_eval_job()
            assert claimed is not None, "Expected a tier-3 pick"
            # The renamed field must exist and be False for a needs-engine game.
            assert hasattr(claimed, "is_lichess_eval_game"), (
                "ClaimedJob must have is_lichess_eval_game field (renamed from is_analyzed)"
            )
            assert claimed.is_lichess_eval_game is False, (
                "Primary lottery pick of needs-engine game must have is_lichess_eval_game=False"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id])


# ─── D-7: weighted-random within-user game pick spread tests ──────────────────


class TestTier3GamePickSpread:
    """D-7 (SEED-048): _claim_tier3_derived Step-2 uses ES weighted-random game pick.

    Verifies that the within-user game pick is no longer deterministic: multiple
    workers landing on the same user will usually get different games, cutting
    avoidable wasted eval cycles without changing the priority intent (classical
    > rapid > blitz > bullet > other, more-recent game preferred).

    All tests use tier2_test_users fixtures (tier3_a user) and insert/delete
    games per-test to avoid pollution of other tests.
    """

    async def test_game_pick_spread(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Step-2 game pick spreads across multiple games for a multi-game user.

        Seed ~10 needs-engine games for one user. Over ~300 draws the returned
        game_id must cover >= 3 distinct seeded games. The old deterministic
        implementation would return exactly 1 distinct game_id every draw, so
        this assertion can only pass with the weighted-random change.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]
        now = datetime.now(timezone.utc)

        # Set user as recently active so Step 1 reliably picks them.
        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_id).values(last_activity=now)
            )
            await session.commit()

        # Seed 10 games with varied TC and played_at to give spread a fair chance.
        # Use valid enum values (bullet/blitz/rapid/classical) plus None for the
        # "other/unknown" bucket (time_control_bucket is nullable in the Game model).
        tc_buckets: list[str | None] = [
            "classical",
            "rapid",
            "blitz",
            "bullet",
            None,
            "classical",
            "rapid",
            "blitz",
            "bullet",
            None,
        ]
        game_ids: list[int] = []
        try:
            for i, tc in enumerate(tc_buckets):
                gid = await _insert_game(
                    queue_session_maker,
                    user_id,
                    time_control_bucket=tc,
                    played_at=now - timedelta(days=i * 7),
                    full_evals_completed_at=None,
                    lichess_evals_at=None,
                )
                game_ids.append(gid)

            seeded_set = set(game_ids)
            from app.services.eval_queue_service import _claim_tier3_derived

            n_draws = 300
            seen_ids: set[int] = set()
            async with queue_session_maker() as session:
                for _ in range(n_draws):
                    result = await _claim_tier3_derived(session)
                    if result is not None and result[0] in seeded_set:
                        seen_ids.add(result[0])

            assert len(seen_ids) >= 3, (
                f"Step-2 weighted-random game pick must spread across >= 3 of 10 seeded "
                f"games over {n_draws} draws; got only {len(seen_ids)} distinct game(s). "
                f"This assertion cannot pass with a deterministic LIMIT 1 pick."
            )
        finally:
            await _delete_games(queue_session_maker, game_ids)

    async def test_weighting_bias_preserved(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Priority intent (classical + recent > other/bullet + oldest) survives the spread.

        Seed exactly two games: one top-priority (classical, played recently) and
        one bottom-priority (other, played long ago). Over ~400 draws the top-priority
        game must be picked strictly more often than the bottom-priority game, proving
        that the ES spread did not flatten the weighting signal.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]
        now = datetime.now(timezone.utc)

        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_id).values(last_activity=now)
            )
            await session.commit()

        try:
            # Top priority: classical + most recent
            top_game = await _insert_game(
                queue_session_maker,
                user_id,
                time_control_bucket="classical",
                played_at=now - timedelta(hours=1),
                full_evals_completed_at=None,
                lichess_evals_at=None,
            )
            # Bottom priority: NULL TC (ELSE branch = tc_other weight) + very old.
            # time_control_bucket=None maps to the ELSE clause in the CASE expression,
            # which uses CAST(:tc_other AS float8) — the lowest weight multiplier.
            bottom_game = await _insert_game(
                queue_session_maker,
                user_id,
                time_control_bucket=None,
                played_at=now - timedelta(days=365),
                full_evals_completed_at=None,
                lichess_evals_at=None,
            )

            from app.services.eval_queue_service import _claim_tier3_derived

            n_draws = 400
            count_top = 0
            count_bottom = 0
            async with queue_session_maker() as session:
                for _ in range(n_draws):
                    result = await _claim_tier3_derived(session)
                    if result is not None:
                        if result[0] == top_game:
                            count_top += 1
                        elif result[0] == bottom_game:
                            count_bottom += 1

            total = count_top + count_bottom
            assert total > 0, "Expected some draws to return one of the seeded games"
            assert count_top > count_bottom, (
                f"Top-priority game (classical, recent) must be picked more often than "
                f"bottom-priority game (other, oldest); "
                f"top={count_top}, bottom={count_bottom} of {total} relevant picks. "
                f"Weighting bias must survive the ES spread."
            )
        finally:
            await _delete_games(queue_session_maker, [top_game, bottom_game])

    async def test_single_game_regression(
        self,
        tier2_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A user with exactly one needs-engine game always gets that game back.

        The ES formula -ln(random()) / game_weight is undefined for weight=0, but
        GAME_WEIGHT_FLOOR guarantees weight > 0. For a single-game user there is
        only one candidate, so the ORDER BY picks it every draw regardless of the
        random component — regression safety for this degenerate case.
        """
        import app.services.eval_queue_service as svc
        from app.models.user import User

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        user_id = tier2_test_users["tier3_a"]
        now = datetime.now(timezone.utc)

        async with queue_session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == user_id).values(last_activity=now)
            )
            await session.commit()

        sole_game = await _insert_game(
            queue_session_maker,
            user_id,
            time_control_bucket="blitz",
            played_at=now - timedelta(days=1),
            full_evals_completed_at=None,
            lichess_evals_at=None,
        )

        from app.services.eval_queue_service import _claim_tier3_derived

        try:
            async with queue_session_maker() as session:
                for i in range(50):
                    result = await _claim_tier3_derived(session)
                    if result is not None and result[1] == user_id:
                        assert result[0] == sole_game, (
                            f"Draw {i}: single-game user must always return sole_game "
                            f"{sole_game}; got {result[0]}"
                        )
        finally:
            await _delete_games(queue_session_maker, [sole_game])


# ─── Tier-4 blob-backfill lottery ─────────────────────────────────────────────

# Unique user IDs for tier-4 blob tests — range 99220–99229 reserved.
_TEST_USER_TIER4_ID: int = 99220
_TEST_GUEST_TIER4_ID: int = 99221


@pytest_asyncio.fixture(scope="session", autouse=False)
async def tier4_test_users(
    queue_session_maker: async_sessionmaker[AsyncSession],
) -> dict[str, int]:
    """Ensure tier-4 blob-backfill test users exist. Returns mapping role -> user_id."""
    from app.models.user import User

    users = [
        User(
            id=_TEST_USER_TIER4_ID,
            email=f"tier4-test-{_TEST_USER_TIER4_ID}@example.com",
            hashed_password="fakehash",
            is_guest=False,
        ),
        User(
            id=_TEST_GUEST_TIER4_ID,
            email=f"tier4-guest-{_TEST_GUEST_TIER4_ID}@example.com",
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
        "user": _TEST_USER_TIER4_ID,
        "guest": _TEST_GUEST_TIER4_ID,
    }


async def _insert_game_flaw(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    *,
    ply: int = 2,
    allowed_pv_lines: list[dict[str, object]] | None = None,
) -> None:
    """Insert a GameFlaw row and commit via the ORM.

    allowed_pv_lines=None  → column NOT set → PostgreSQL stores SQL NULL → IS NULL matches.
    allowed_pv_lines=[...] → JSONB blob via asyncpg codec → IS NULL does NOT match.

    IMPORTANT: do NOT do `flaw.allowed_pv_lines = None` — asyncpg's JSONB codec serializes
    Python None as JSON null ('null'::jsonb), not as SQL NULL. The _claim_tier4_blob predicate
    `gf.allowed_pv_lines IS NULL` only matches SQL NULL (which is what production rows have
    after the ALTER TABLE ADD COLUMN migration sets all existing rows to NULL by default).
    Omitting the attribute entirely lets PostgreSQL insert SQL NULL via the column default.
    """
    from app.models.game_flaw import GameFlaw

    async with session_maker() as session:
        flaw = GameFlaw(
            user_id=user_id,
            game_id=game_id,
            ply=ply,
            severity=2,
            phase=0,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
        )
        # Only explicitly set when non-NULL — asyncpg sends Python None through the JSONB
        # codec, which stores the JSONB null atom, not SQL NULL (see comment above).
        if allowed_pv_lines is not None:
            flaw.allowed_pv_lines = allowed_pv_lines
        session.add(flaw)
        await session.commit()


class TestTier4BlobBackfill:
    """Phase 145 Plan 02: tier-4 spare-capacity flaw-blob backfill lottery.

    Tests cover:
    - tier4_null_blob_picked: _claim_tier4_blob returns analyzed non-guest game with NULL blob
    - tier4_returns_none_empty_queue: returns None when no matching game exists
    - tier4_excludes_guests: guest-owned games are never returned (QUEUE-08)
    - tier4_excludes_unanalyzed: games without full_evals_completed_at are excluded
    - tier4_blobbed_game_excluded: fully-blobbed game stops matching predicate (idempotency)
    - tier4_dispatch_via_claim: claim_eval_job dispatches tier-4 after tier-1/2/3 fall through
    - tier4_dispatch_disabled: tier-4 is suppressed when EVAL_AUTO_DRAIN_ENABLED=False
    - tier4_claimed_job_fields: ClaimedJob has tier=TIER_BLOB_BACKFILL and job_id=None
    """

    async def test_tier4_null_blob_picked(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """_claim_tier4_blob returns the analyzed non-guest game that has a NULL-blob flaw."""
        from app.services.eval_queue_service import _claim_tier4_blob

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id)

        try:
            async with queue_session_maker() as session:
                result = await _claim_tier4_blob(session)

            assert result is not None, "Expected _claim_tier4_blob to return a game; got None"
            picked_game_id, picked_user_id = result
            assert picked_game_id == game_id, (
                f"Expected game {game_id} with NULL-blob flaw; got {picked_game_id}"
            )
            assert picked_user_id == user_id, f"Expected user_id={user_id}; got {picked_user_id}"
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_returns_none_empty_queue(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """_claim_tier4_blob returns None when no analyzed non-guest game has a NULL-blob flaw."""
        from app.services.eval_queue_service import _claim_tier4_blob

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        # Game with all blobs already written (non-NULL allowed_pv_lines) — no NULL rows.
        written_blob: list[dict[str, object]] = [
            {"b": 10, "bm": None, "s": 5, "sm": None, "su": "e2e4"}
        ]
        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(
            queue_session_maker, user_id, game_id, allowed_pv_lines=written_blob
        )

        try:
            async with queue_session_maker() as session:
                result = await _claim_tier4_blob(session)

            # If other test games happen to have NULL blobs, result might not be None.
            # Assert our specific game is NOT picked (it has a written blob).
            if result is not None:
                assert result[0] != game_id, (
                    f"Game {game_id} with written blob must not be returned by _claim_tier4_blob"
                )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_excludes_guests(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Guest-owned games with NULL-blob flaws are never returned (QUEUE-08)."""
        from app.services.eval_queue_service import _claim_tier4_blob

        guest_id = tier4_test_users["guest"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            guest_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, guest_id, game_id)

        try:
            async with queue_session_maker() as session:
                for i in range(10):
                    result = await _claim_tier4_blob(session)
                    if result is not None:
                        assert result[0] != game_id, (
                            f"Draw {i}: guest game {game_id} must never be returned "
                            f"by _claim_tier4_blob (QUEUE-08)"
                        )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_excludes_unanalyzed(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Games with full_evals_completed_at IS NULL are excluded — tier-4 is for analyzed games only."""
        from app.services.eval_queue_service import _claim_tier4_blob

        user_id = tier4_test_users["user"]

        # full_evals_completed_at=None → NOT analyzed → must be excluded from tier-4.
        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=None,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id)

        try:
            async with queue_session_maker() as session:
                for i in range(10):
                    result = await _claim_tier4_blob(session)
                    if result is not None:
                        assert result[0] != game_id, (
                            f"Draw {i}: unanalyzed game {game_id} must never be returned "
                            f"by _claim_tier4_blob"
                        )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_blobbed_game_excluded(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A game whose flaw blobs are all written stops being selected (idempotency by predicate).

        Simulates the full blob-write lifecycle: insert game + flaw with NULL blob,
        verify it is picked, then set allowed_pv_lines to a non-NULL value and
        verify the game is no longer returned.
        """
        from sqlalchemy import update as sa_update2

        from app.models.game_flaw import GameFlaw
        from app.services.eval_queue_service import _claim_tier4_blob

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id, ply=4)

        try:
            # Phase 1: flaw has NULL blob — game must be picked.
            async with queue_session_maker() as session:
                result = await _claim_tier4_blob(session)
            assert result is not None, "Before blob write, game with NULL flaw must be returned"
            assert result[0] == game_id, f"Expected game {game_id}; got {result[0]}"

            # Phase 2: write the blob (simulate Plan-03 handler completing the write).
            written_blob: list[dict[str, object]] = [
                {"b": 50, "bm": None, "s": 20, "sm": None, "su": "d2d4"}
            ]
            async with queue_session_maker() as session:
                await session.execute(
                    sa_update2(GameFlaw)
                    .where(GameFlaw.game_id == game_id, GameFlaw.ply == 4)
                    .values(allowed_pv_lines=written_blob)
                )
                await session.commit()

            # Phase 3: all flaw blobs written — game must no longer be returned.
            async with queue_session_maker() as session:
                for i in range(10):
                    result_after = await _claim_tier4_blob(session)
                    if result_after is not None:
                        assert result_after[0] != game_id, (
                            f"Draw {i}: fully-blobbed game {game_id} must not be re-selected "
                            f"(idempotency by predicate)"
                        )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_dispatch_via_claim(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """claim_eval_job dispatches tier-4 after tier-1/2/3 all fall through.

        Strategy: mock _claim_tier3_derived to return None so tier-3 is bypassed,
        then insert an analyzed game with a NULL-blob flaw for the tier-4 path.
        """
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import TIER_BLOB_BACKFILL

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        # Force tier-3 to return None so tier-4 is reached.
        async def _mock_tier3(session: object) -> None:
            return None

        monkeypatch.setattr(svc, "_claim_tier3_derived", _mock_tier3)

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id, ply=6)

        try:
            claimed = await svc.claim_eval_job()

            assert claimed is not None, (
                "claim_eval_job must return tier-4 when tier-3 is exhausted and a "
                "NULL-blob analyzed game exists"
            )
            assert claimed.game_id == game_id, (
                f"Expected tier-4 game {game_id}; got {claimed.game_id}"
            )
            assert claimed.tier == TIER_BLOB_BACKFILL, (
                f"Expected tier={TIER_BLOB_BACKFILL}; got {claimed.tier}"
            )
            assert claimed.job_id is None, (
                f"Tier-4 table-less lottery must return job_id=None; got {claimed.job_id}"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_dispatch_disabled(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tier-4 is NOT dispatched when EVAL_AUTO_DRAIN_ENABLED=False.

        The same EVAL_AUTO_DRAIN_ENABLED gate that guards tier-3 also prevents
        tier-4 from running — spare-capacity backfill is off when auto-drain is off.
        """
        import app.services.eval_queue_service as svc

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)
        monkeypatch.setattr(svc.settings, "EVAL_AUTO_DRAIN_ENABLED", False)

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id, ply=8)

        try:
            claimed = await svc.claim_eval_job()
            assert claimed is None, (
                f"With EVAL_AUTO_DRAIN_ENABLED=False, claim_eval_job must return None "
                f"even when a tier-4 candidate exists; got {claimed!r}"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_tier4_claimed_job_fields(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ClaimedJob returned for tier-4 has tier=TIER_BLOB_BACKFILL and job_id=None."""
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import TIER_BLOB_BACKFILL

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        # Force tier-3 to return None so we reach tier-4.
        async def _mock_tier3(session: object) -> None:
            return None

        monkeypatch.setattr(svc, "_claim_tier3_derived", _mock_tier3)

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id, ply=10)

        try:
            claimed = await svc.claim_eval_job()

            assert claimed is not None, "Expected tier-4 ClaimedJob; got None"
            assert claimed.tier == TIER_BLOB_BACKFILL, (
                f"Expected tier={TIER_BLOB_BACKFILL}; got {claimed.tier}"
            )
            assert claimed.job_id is None, (
                f"Tier-4 must have job_id=None (table-less lottery); got {claimed.job_id}"
            )
            assert claimed.is_lichess_eval_game is False, (
                "is_lichess_eval_game must be False at claim time (resolved in Plan-03 handler)"
            )
            assert isinstance(claimed.game_id, int), "game_id must be an int"
            assert isinstance(claimed.user_id, int), "user_id must be an int"
        finally:
            await _delete_games(queue_session_maker, [game_id])

    async def test_idle_scope_returns_none_when_tier3_empty(
        self,
        tier4_test_users: dict[str, int],
        queue_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SEED-072: scope="idle" must NOT fall through to tier-4.

        With tier-3 mocked empty and a tier-4-eligible NULL-blob game present,
        claim_eval_job(scope="idle") returns None (→ HTTP 204) so the remote worker
        drains tier-4 via the dedicated /flaw-blob-lease rung instead of re-evaluating
        the already-complete game through the full-ply /lease path. The bundled
        scope=None path (in-process server pool) still dispatches tier-4 — asserted by
        test_tier4_dispatch_via_claim.
        """
        import app.services.eval_queue_service as svc
        from app.models.eval_jobs import TIER_BLOB_BACKFILL

        monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)

        # Force tier-3 to return None so tier-4 would be reached under the old behavior.
        async def _mock_tier3(session: object) -> None:
            return None

        monkeypatch.setattr(svc, "_claim_tier3_derived", _mock_tier3)

        user_id = tier4_test_users["user"]
        now = datetime.now(timezone.utc)

        game_id = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id, ply=12)

        try:
            claimed = await svc.claim_eval_job(scope="idle")
            assert claimed is None, (
                "scope='idle' must return None once tier-3 is empty (SEED-072); "
                f"tier-4 must NOT be served via /lease. Got {claimed!r}"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id])

        # Sanity: the same NULL-blob game is still a valid tier-4 candidate — proving
        # the None above is the routing change, not an empty backlog. (Re-insert since
        # the game was deleted in the finally; a fresh row keeps the assertion honest.)
        game_id2 = await _insert_game(
            queue_session_maker,
            user_id,
            full_evals_completed_at=now,
        )
        await _insert_game_flaw(queue_session_maker, user_id, game_id2, ply=12)
        try:
            from app.services.eval_queue_service import _claim_tier4_blob

            async with queue_session_maker() as session:
                tier4_pick = await _claim_tier4_blob(session)
            assert tier4_pick is not None and tier4_pick[0] == game_id2, (
                f"Expected tier-4 to still see game {game_id2}; got {tier4_pick!r}. "
                f"(TIER_BLOB_BACKFILL={TIER_BLOB_BACKFILL})"
            )
        finally:
            await _delete_games(queue_session_maker, [game_id2])
