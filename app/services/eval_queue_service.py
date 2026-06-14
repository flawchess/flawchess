"""Priority queue service for the full-ply eval drain (QUEUE-01/02/05/06/08).

Three-tier pick:
  Tier 1 (TIER_EXPLICIT)      — explicit user request
  Tier 2 (TIER_AUTO_WINDOW)   — automatic recency window (no active enqueue source
                                as of Phase 118 — see note below; lane retained)
  Tier 3 (TIER_IDLE_BACKLOG)  — idle backlog (derived pick, no eval_jobs row)

Tier-1 and tier-2 use SELECT FOR UPDATE OF … SKIP LOCKED against the eval_jobs
table for a lock-safe, serialized claim contract (QUEUE-06 / SEED-012 D-8).

Phase 118 removed the tier-2 auto-enqueue (`enqueue_tier2_window`): the tier-3 idle
drain already prioritizes recently-active users (last_activity DESC) and covers the
whole backlog, so an explicit auto-window added no scheduling value. The tier-2 lane
(constant, generic claim handling, eval_jobs.tier column) is intentionally retained
for a future per-user "analyze my games" vs "help drain for everybody" mode.

Tier-3 is a *derived* pick directly over games WHERE full_evals_completed_at IS
NULL AND NOT guest — no rows are pre-populated in eval_jobs for the backlog.
This keeps the queue table lean (~558k backlog games are never pre-inserted).

Lease TTL:
  LEASE_TTL_SECONDS = 120
  Derivation: tier-1 fan-out ≈ 10s (all plies via pool, spike-003); tier-2/3
  per-worker worst case ≈ 60 plies × 0.98 s/ply ≈ 59s. 2× the slow case → 120s.

Security (RESEARCH §Security V5):
  All worker_id / TTL values are bound as :params — never interpolated into
  the sa.text CTE string. No f-string is used inside sa.text calls.

QUEUE-08 (guest exclusion):
  Every claim path JOINs the users table and filters NOT users.is_guest.
  enqueue_tier1_game also refuses to enqueue a guest's game (no-op).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import sqlalchemy as sa
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.eval_jobs import EvalJob, TIER_EXPLICIT, TIER_AUTO_WINDOW, TIER_IDLE_BACKLOG  # noqa: F401 — re-export constants for callers
from app.models.game import Game
from app.models.user import User

# ─── Module-level constants (no magic numbers) ────────────────────────────────

# 2× the slowest tier-2/3 per-worker game: ~60 plies × 0.98 s/ply ≈ 59s.
# Tier-1 fan-out across the full pool: ~60 plies / 6 workers × 0.98 s ≈ 10s.
# 120s covers both tiers with a comfortable safety margin.
LEASE_TTL_SECONDS: int = 120

# Default worker identity for the server-side engine pool.
# Future browser workers will supply their own identity (SEED-012 D-8).
WORKER_ID_SERVER_POOL: str = "server-pool"

# Status literals (Literal type keeps ty + mypy happy; DB stores varchar(20))
EvalJobStatus = Literal["pending", "leased", "completed", "failed"]


# ─── Return type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClaimedJob:
    """Returned by claim_eval_job when a job was successfully claimed.

    job_id is None for tier-3 derived picks (no eval_jobs row exists for the
    backlog; the drain marks full_evals_completed_at directly).

    is_analyzed is derived from Game.lichess_evals_at IS NOT NULL (D-117-07):
    True means the game already has lichess %evals → preserve them; the drain
    should skip plies with existing evals (D-116-04 repointed by D-117-07).
    """

    game_id: int
    user_id: int
    tier: int
    is_analyzed: bool
    job_id: int | None  # None for tier-3 derived pick


# ─── Private helpers ──────────────────────────────────────────────────────────


async def _sweep_expired_leases(session: AsyncSession) -> int:
    """Reset expired leased rows to 'pending'.

    Called at the top of each claim to ensure stale leases are cleaned up
    before the SKIP LOCKED pick runs, so they re-enter the queue immediately.

    Returns the number of rows requeued.
    """
    jobs_table = EvalJob.__table__
    now_ts = datetime.now(timezone.utc)
    stmt = (
        update(jobs_table)  # ty: ignore[invalid-argument-type]
        .where(
            jobs_table.c.status == "leased",
            jobs_table.c.lease_expiry < now_ts,
        )
        .values(status="pending", leased_by=None, lease_expiry=None)
    )
    result = await session.execute(stmt)
    return result.rowcount  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount


async def _claim_queued_job(
    session: AsyncSession,
    worker_id: str,
    lease_ttl_seconds: int,
) -> tuple[int, int, int, int, bool] | None:
    """Claim one pending tier-1 or tier-2 job via SELECT FOR UPDATE OF SKIP LOCKED.

    Returns (job_id, game_id, user_id, tier, is_analyzed) or None when empty.

    The SKIP LOCKED CTE is the canonical PostgreSQL job-queue primitive (RESEARCH §3).
    All bound values (:worker_id, :ttl) are parameterized — no string interpolation.

    Within a tier:
      - Oldest-pending user first (round-robin approximation via MIN(created_at), QUEUE-02)
      - Within a user: classical > rapid > blitz > bullet > other (D-117-04)
      - Within a TC bucket: most-recent game first (played_at DESC)

    Guest exclusion: JOIN users + NOT is_guest filter (QUEUE-08).
    """
    result = await session.execute(
        sa.text("""
            WITH candidate AS (
                SELECT ej.id, ej.game_id, ej.user_id, ej.tier
                FROM eval_jobs ej
                JOIN games g ON g.id = ej.game_id
                JOIN users u ON u.id = ej.user_id
                WHERE ej.status = 'pending'
                  AND u.is_guest = false
                ORDER BY
                    ej.tier ASC,
                    (SELECT MIN(j2.created_at) FROM eval_jobs j2
                     WHERE j2.user_id = ej.user_id AND j2.status = 'pending') ASC,
                    CASE g.time_control_bucket
                        WHEN 'classical' THEN 0
                        WHEN 'rapid'     THEN 1
                        WHEN 'blitz'     THEN 2
                        WHEN 'bullet'    THEN 3
                        ELSE 4
                    END ASC,
                    g.played_at DESC NULLS LAST
                LIMIT 1
                FOR UPDATE OF ej SKIP LOCKED
            )
            UPDATE eval_jobs ej
            SET status = 'leased',
                leased_by = :worker_id,
                lease_expiry = now() + (:ttl || ' seconds')::interval
            FROM candidate
            WHERE ej.id = candidate.id
            RETURNING ej.id, ej.game_id, ej.user_id, candidate.tier
        """),
        {"worker_id": worker_id, "ttl": str(lease_ttl_seconds)},
    )
    row = result.one_or_none()
    if row is None:
        return None

    job_id: int = row[0]
    game_id: int = row[1]
    user_id: int = row[2]
    tier: int = row[3]

    # Resolve is_analyzed (D-117-07): lichess_evals_at IS NOT NULL
    game_result = await session.execute(select(Game.lichess_evals_at).where(Game.id == game_id))
    lichess_evals_at = game_result.scalar_one_or_none()
    is_analyzed = lichess_evals_at is not None

    return job_id, game_id, user_id, tier, is_analyzed


async def _claim_tier3_derived(
    session: AsyncSession,
) -> tuple[int, int, bool] | None:
    """Derive a tier-3 pick from games with full_evals_completed_at IS NULL.

    No eval_jobs row is pre-populated for the idle backlog. The drain marks
    full_evals_completed_at directly; there is nothing to report back.

    Ordering mirrors D-117-04: classical > rapid > blitz > bullet, then most-recent.
    Round-robin across users is best-effort (ordered by played_at globally).
    Guest games are excluded (QUEUE-08) via JOIN users + NOT is_guest.

    Returns (game_id, user_id, is_analyzed) or None when no pending games exist.
    """
    # Phase 118: this plain SELECT has no locking. Two concurrent workers can pick
    # the same game (double-claim). Duplicate work is idempotent (ON CONFLICT DO NOTHING
    # for flaws, idempotent oracle UPDATE) but wastes engine calls. At the single-worker
    # Phase 117 scale the risk is negligible; add FOR UPDATE SKIP LOCKED here (backed by
    # a transient eval_jobs row for the claim window) when multi-worker is introduced.
    result = await session.execute(
        select(
            Game.id,
            Game.user_id,
            Game.lichess_evals_at.isnot(None).label("is_analyzed"),
        )
        .join(User, Game.user_id == User.id)
        .where(
            Game.full_evals_completed_at.is_(None),
            User.is_guest == False,  # noqa: E712 — SQLAlchemy requires == not is
        )
        .order_by(
            # D-118-04: active users first (users.last_activity DESC NULLS LAST).
            # User join already present at line above — no new join needed.
            User.last_activity.desc().nullslast(),
            sa.case(
                (Game.time_control_bucket == "classical", 0),
                (Game.time_control_bucket == "rapid", 1),
                (Game.time_control_bucket == "blitz", 2),
                (Game.time_control_bucket == "bullet", 3),
                else_=4,
            ).asc(),
            Game.played_at.desc().nullslast(),
            # D-118-04: games needing full eval (lichess_evals_at IS NULL) before
            # PV-backfill-only games (lichess_evals_at IS NOT NULL). False < True
            # in ascending order, so NULL-games (False) come first.
            Game.lichess_evals_at.isnot(None).asc(),
        )
        .limit(1)
    )
    row = result.one_or_none()
    if row is None:
        return None

    game_id: int = row[0]
    user_id: int = row[1]
    is_analyzed: bool = row[2]
    return game_id, user_id, is_analyzed


# ─── Public API ───────────────────────────────────────────────────────────────


async def claim_eval_job(
    worker_id: str = WORKER_ID_SERVER_POOL,
) -> ClaimedJob | None:
    """Claim the next eval job — tier-1 > tier-2 > tier-3 (derived).

    Session discipline: opens its own short session, commits, closes.
    The SKIP LOCKED lock is released immediately on commit — never held
    across the engine gather (Pitfall 1 in RESEARCH §Common Pitfalls).

    Returns ClaimedJob or None when there is nothing to process.
    """
    async with async_session_maker() as session:
        # Sweep expired leases first so they re-enter the queue.
        await _sweep_expired_leases(session)
        await session.commit()

    # Attempt tier-1 / tier-2 pick in a fresh short transaction.
    async with async_session_maker() as session:
        queued = await _claim_queued_job(session, worker_id, LEASE_TTL_SECONDS)
        await session.commit()

    if queued is not None:
        job_id, game_id, user_id, tier, is_analyzed = queued
        return ClaimedJob(
            game_id=game_id,
            user_id=user_id,
            tier=tier,
            is_analyzed=is_analyzed,
            job_id=job_id,
        )

    # No tier-1/2 row — fall through to tier-3 derived pick (idle backlog),
    # unless automatic eval is disabled via EVAL_AUTO_DRAIN_ENABLED (e.g. dev, to
    # avoid pinning every local core on the hundreds-of-thousands-game backlog).
    # Tier-1 explicit jobs above are never gated; tier-2 has no enqueue source
    # (Phase 118) so only the tier-3 idle drain below is gated by this flag.
    if not settings.EVAL_AUTO_DRAIN_ENABLED:
        return None

    async with async_session_maker() as session:
        derived = await _claim_tier3_derived(session)
        # No write needed for tier-3; session auto-closes.

    if derived is None:
        return None

    game_id3, user_id3, is_analyzed3 = derived
    return ClaimedJob(
        game_id=game_id3,
        user_id=user_id3,
        tier=TIER_IDLE_BACKLOG,
        is_analyzed=is_analyzed3,
        job_id=None,  # no eval_jobs row for tier-3
    )


async def report_job_complete(job_id: int) -> None:
    """Mark a leased eval_job as completed.

    Short session; idempotent (re-completing an already-completed job is a no-op
    because the WHERE matches only 'leased' rows).
    """
    async with async_session_maker() as session:
        jobs_table = EvalJob.__table__
        now_ts = datetime.now(timezone.utc)
        stmt = (
            update(jobs_table)  # ty: ignore[invalid-argument-type]
            .where(
                jobs_table.c.id == job_id,
                jobs_table.c.status == "leased",
            )
            .values(status="completed", completed_at=now_ts)
        )
        await session.execute(stmt)
        await session.commit()


async def requeue_expired_leases() -> int:
    """Reset expired leased rows to 'pending'. Returns count requeued.

    Standalone entry point for external callers (e.g. maintenance scripts).
    The claim_eval_job function also calls this inline at the top of each tick.
    """
    async with async_session_maker() as session:
        count = await _sweep_expired_leases(session)
        await session.commit()
    return count


async def enqueue_tier1_game(game_id: int, user_id: int) -> bool:
    """Insert a tier-1 eval_job for one game. Returns True if a row was inserted.

    Idempotent: ON CONFLICT DO NOTHING on the active-job partial unique index
    (uq_eval_jobs_game_active, status IN ('pending','leased')). A game already
    in any active status is silently skipped.

    QUEUE-08: refuses to enqueue a guest's game (no-op, no Sentry — guests
    simply never enter the queue; not a bug, just a classification).

    Returns False for a guest game or when the game is already queued.
    """
    async with async_session_maker() as session:
        # Guest guard (QUEUE-08): look up the user's is_guest flag.
        user_result = await session.execute(select(User.is_guest).where(User.id == user_id))
        is_guest = user_result.scalar_one_or_none()
        # Bug fix: scalar_one_or_none() returns None when the user row is missing
        # (deleted between game load and this lookup). `if is_guest:` evaluates
        # `if None:` → False, letting execution reach the FK insert and raising
        # an unhandled IntegrityError / 500.  Treat missing user as non-enqueue.
        if is_guest is None or is_guest:
            return False

        stmt = (
            pg_insert(EvalJob)
            .values(
                tier=TIER_EXPLICIT,
                user_id=user_id,
                game_id=game_id,
                status="pending",
            )
            # uq_eval_jobs_game_active is a partial unique index on game_id
            # WHERE status IN ('pending', 'leased'). The index_where must match
            # the partial index predicate so PostgreSQL resolves the conflict target.
            # Completed/failed jobs DO allow re-enqueue (not covered by the partial
            # index). See RESEARCH Pitfall 6 / eval_jobs.py model comments.
            .on_conflict_do_nothing(
                index_elements=["game_id"],
                index_where=sa.text("status IN ('pending', 'leased')"),
            )
        )
        result = await session.execute(stmt)
        await session.commit()

    # rowcount is 1 when a row was inserted, 0 on conflict.
    return (result.rowcount or 0) > 0  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
