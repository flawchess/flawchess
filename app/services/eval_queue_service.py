"""Priority queue service for the full-ply eval drain (QUEUE-01/02/05/06/08).

Three-tier pick:
  Tier 1 (TIER_EXPLICIT)      — explicit user request
  Tier 2 (TIER_AUTO_WINDOW)   — automatic recency window (no active enqueue source
                                as of Phase 118 — see note below; lane retained)
  Tier 3 (TIER_IDLE_BACKLOG)  — idle backlog (derived pick, no eval_jobs row)

Tier-1 and tier-2 use SELECT FOR UPDATE OF … SKIP LOCKED against the eval_jobs
table for a lock-safe, serialized claim contract (QUEUE-06 / SEED-012 D-8).

Phase 118 removed the tier-2 auto-enqueue (`enqueue_tier2_window`): the tier-3 idle
drain already prioritizes recently-active users and covers the whole backlog, so an
explicit auto-window added no scheduling value. The tier-2 lane (constant, generic
claim handling, eval_jobs.tier column) is intentionally retained for a future per-user
"analyze my games" vs "help drain for everybody" mode.

Tier-3 is a *derived* pick via an Efraimidis–Spirakis recency-weighted lottery over
candidate users (games WHERE needs_engine_full_evals = full_evals_completed_at IS NULL
AND lichess_evals_at IS NULL AND is_guest=false). No rows are pre-populated in
eval_jobs for the backlog. This keeps the queue table lean (~558k backlog games never
pre-inserted) while providing fast catch-up for returning users (SEED-046).

When the primary lottery finds no candidate (no needs-engine games), a residual
fallback picks a PV-backfill-only game (lichess_evals_at IS NOT NULL).

Lease TTL:
  LEASE_TTL_SECONDS = 120
  Derivation: tier-1 fan-out ≈ 10s (all plies via pool, spike-003); tier-2/3
  per-worker worst case ≈ 60 plies × 0.98 s/ply ≈ 59s. 2× the slow case → 120s.

Security (RESEARCH §Security V5):
  All worker_id / TTL / τ / floor values are bound as :params — never interpolated
  into the sa.text CTE string. No f-string is used inside sa.text calls.

QUEUE-08 (guest exclusion):
  Every claim path JOINs the users table and filters NOT users.is_guest.
  enqueue_tier1_game also refuses to enqueue a guest's game (no-op).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import math

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

# ─── SEED-046: recency-weighted tier-3 lottery constants ─────────────────────

# Recency half-life for the ES user lottery. τ½ = 1d → a returning user
# (last_activity ≈ now, weight ≈ 1.0) wins ~30–40% of draws even against
# 1–2 currently-recent users; badge ticks roughly every ~25s at the ~10s
# tier-3 claim cadence. PROD TUNING: raise to 2–3d for broader idle sharing at
# the cost of less immediate return-burst responsiveness. (SEED-046 / RESEARCH-NOTES)
RECENCY_HALF_LIFE_DAYS: float = 1.0

# Anti-starvation floor for the ES key weight. The weight formula is
# exp(-Δt/τ) + WEIGHT_FLOOR so weight is always > 0 (guards against div-by-zero
# in -ln(random())/weight). At floor=0.005 with ~59 non-guest users the total
# floor mass ≈ 0.30, so a lone returner keeps ~65–70% share. Keep ≤ 0.01.
# PROD TUNING: do NOT raise above 0.01 — larger floor swamps the recency signal.
# (SEED-046 / RESEARCH-NOTES τ/floor recommendation)
WEIGHT_FLOOR: float = 0.005


# ─── Return type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClaimedJob:
    """Returned by claim_eval_job when a job was successfully claimed.

    job_id is None for tier-3 derived picks (no eval_jobs row exists for the
    backlog; the drain marks full_evals_completed_at directly).

    is_lichess_eval_game is derived from Game.lichess_evals_at IS NOT NULL
    (D-117-07): True means the game already has lichess %evals → preserve them;
    the drain should skip plies with existing evals (D-116-04 repointed by
    D-117-07). This field name makes the lichess-gate explicit and avoids
    confusion with the source-agnostic flaw-coverage property on Game
    (see RESEARCH-NOTES §Opportunistic cleanup).
    """

    game_id: int
    user_id: int
    tier: int
    is_lichess_eval_game: bool
    job_id: int | None  # None for tier-3 derived pick


# ─── Private helpers ─────────────────────────────────────────────────────────


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

    Returns (job_id, game_id, user_id, tier, is_lichess_eval_game) or None when empty.

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

    # Resolve is_lichess_eval_game (D-117-07): lichess_evals_at IS NOT NULL.
    game_result = await session.execute(select(Game.lichess_evals_at).where(Game.id == game_id))
    lichess_evals_at = game_result.scalar_one_or_none()
    is_lichess_eval_game = lichess_evals_at is not None

    return job_id, game_id, user_id, tier, is_lichess_eval_game


async def _claim_tier3_derived(
    session: AsyncSession,
) -> tuple[int, int, bool] | None:
    """Derive a tier-3 pick using a recency-weighted Efraimidis–Spirakis user lottery.

    Two steps in a single session (no locking — see Phase 118 note below):

    Step 1 — WEIGHTED USER PICK (SEED-046):
      Candidate users = non-guest users with at least one needs-engine game
      (full_evals_completed_at IS NULL AND lichess_evals_at IS NULL). This
      predicate matches Game.needs_engine_full_evals exactly and is backed by
      ix_games_needs_engine_full_evals partial index (added by migration 119-01).
      For each candidate compute:
        weight = exp(-Δt/τ) + WEIGHT_FLOOR
      where Δt = seconds since last_activity (NULL → coalesced to a very old
      timestamp so the exp term ≈ 0 and weight ≈ floor), τ = RECENCY_HALF_LIFE_DAYS
      / ln(2) converted to seconds. weight is always > 0 (guards div-by-zero in the
      ES key). Pick user ORDER BY -ln(random()) / weight LIMIT 1.

    Step 2 — BEST GAME FOR PICKED USER:
      Within the chosen user, pick the best needs-engine game by TC bucket
      (classical > rapid > blitz > bullet > other) then played_at DESC NULLS LAST.

    RESIDUAL FALLBACK (when no needs-engine candidate exists anywhere):
      Pick a PV-backfill-only game (full_evals_completed_at IS NULL AND
      lichess_evals_at IS NOT NULL AND is_guest=false) by TC then played_at.
      Returns is_lichess_eval_game=True for this path only.

    This replaces the old D-118-04 last_activity DESC winner-take-all ordering and
    drops the dead lichess_evals_at tiebreaker (live prod bug: it was the LAST ORDER
    key and played_at broke ties first, so lichess games were picked at full engine
    cost despite needs_engine_full_evals saying to skip them — ~70% throughput waste
    on user 28; see RESEARCH-NOTES §Live prod bug).

    Guest games are excluded (QUEUE-08) via JOIN users + is_guest filter.

    Returns (game_id, user_id, is_lichess_eval_game) or None when nothing to process.

    Note: plain SELECT with no locking — two concurrent workers can pick the same game
    (double-claim). Duplicate work is idempotent (ON CONFLICT DO NOTHING for flaws,
    idempotent oracle UPDATE) but wastes engine calls. Add FOR UPDATE SKIP LOCKED
    (backed by a transient eval_jobs row) when multi-worker is introduced.

    Security: τ_seconds, floor_val bound as :params — no f-string inside sa.text.
    """
    # Convert half-life (days) to the decay constant τ in seconds.
    # τ = τ½ / ln2; weight = exp(-Δt_seconds / τ_seconds) + floor
    tau_seconds: float = RECENCY_HALF_LIFE_DAYS / math.log(2) * 86400.0
    floor_val: float = WEIGHT_FLOOR

    # Step 1: ES weighted user pick over needs-engine games.
    # ix_games_needs_engine_full_evals (119-01 migration) covers
    # WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL.
    # COALESCE last_activity to epoch-0 so NULL → exp term ≈ 0 (floor weight).
    # -ln(random()) / weight is the Efraimidis–Spirakis key: LIMIT 1 = winner.
    # All variable values bound as :tau_s, :floor — never f-string-interpolated.
    user_pick_result = await session.execute(
        sa.text("""
            SELECT u.id
            FROM users u
            WHERE u.is_guest = false
              AND EXISTS (
                SELECT 1 FROM games g
                WHERE g.user_id = u.id
                  AND g.full_evals_completed_at IS NULL
                  AND g.lichess_evals_at IS NULL
              )
            ORDER BY
                -ln(random()) / (
                    exp(
                        -EXTRACT(EPOCH FROM (now() - COALESCE(u.last_activity, '1970-01-01'::timestamptz)))
                        / :tau_s
                    ) + :floor
                )
            LIMIT 1
        """),
        {"tau_s": tau_seconds, "floor": floor_val},
    )
    user_row = user_pick_result.one_or_none()

    if user_row is not None:
        picked_user_id: int = user_row[0]
        # Step 2: best needs-engine game for the picked user (TC → played_at order).
        game_result = await session.execute(
            select(Game.id)
            .where(
                Game.user_id == picked_user_id,
                Game.full_evals_completed_at.is_(None),
                Game.lichess_evals_at.is_(None),
            )
            .order_by(
                sa.case(
                    (Game.time_control_bucket == "classical", 0),
                    (Game.time_control_bucket == "rapid", 1),
                    (Game.time_control_bucket == "blitz", 2),
                    (Game.time_control_bucket == "bullet", 3),
                    else_=4,
                ).asc(),
                Game.played_at.desc().nullslast(),
            )
            .limit(1)
        )
        game_row = game_result.scalar_one_or_none()
        if game_row is not None:
            # Needs-engine game → is_lichess_eval_game=False by construction.
            return game_row, picked_user_id, False

    # Residual fallback: no needs-engine candidate → try PV-backfill-only games.
    # Only path that returns is_lichess_eval_game=True.
    fallback_result = await session.execute(
        select(Game.id, Game.user_id)
        .join(User, Game.user_id == User.id)
        .where(
            Game.full_evals_completed_at.is_(None),
            Game.lichess_evals_at.isnot(None),
            User.is_guest == False,  # noqa: E712 — SQLAlchemy requires == not is
        )
        .order_by(
            sa.case(
                (Game.time_control_bucket == "classical", 0),
                (Game.time_control_bucket == "rapid", 1),
                (Game.time_control_bucket == "blitz", 2),
                (Game.time_control_bucket == "bullet", 3),
                else_=4,
            ).asc(),
            Game.played_at.desc().nullslast(),
        )
        .limit(1)
    )
    fallback_row = fallback_result.one_or_none()
    if fallback_row is None:
        return None

    fallback_game_id: int = fallback_row[0]
    fallback_user_id: int = fallback_row[1]
    return fallback_game_id, fallback_user_id, True


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
        job_id, game_id, user_id, tier, is_lichess_eval_game = queued
        return ClaimedJob(
            game_id=game_id,
            user_id=user_id,
            tier=tier,
            is_lichess_eval_game=is_lichess_eval_game,
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

    game_id3, user_id3, is_lichess_eval_game3 = derived
    return ClaimedJob(
        game_id=game_id3,
        user_id=user_id3,
        tier=TIER_IDLE_BACKLOG,
        is_lichess_eval_game=is_lichess_eval_game3,
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
