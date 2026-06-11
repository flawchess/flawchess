"""Import service: in-memory job registry and background import orchestrator.

Manages import jobs from chess.com and lichess, including:
- Job creation and state management (in-memory registry)
- Duplicate import prevention (active job detection)
- Background async orchestration via asyncio.create_task
- Incremental sync via last_synced_at from previous completed jobs
- Zobrist hash computation and bulk DB persistence
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

import httpx
import sentry_sdk
import asyncpg
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, engine
from app.models.game import Game
from app.repositories import game_repository, import_job_repository
from app.repositories.import_job_repository import ImportJobNotFound
from app.schemas.normalization import NormalizedGame
from app.services import chesscom_client, lichess_client, percentile_compute_registry
from app.services.eval_drain import (
    _classify_and_insert_flaws,
    _collect_midgame_eval_targets,
    _collect_endgame_span_eval_targets,
)  # Phase 91: cross-module use of eval_drain internals is intentional — see SEED-023.
from app.services.user_benchmark_percentiles_service import compute_stage_a, compute_stage_b
from app.services.zobrist import PlyData, process_game_pgn

logger = logging.getLogger(__name__)

# UAT 2026-05-20 — a real Postgres-restart outage raises any of these on the
# next write/connect, and the original `except OperationalError` was too
# narrow. SQLAlchemy translates query-time asyncpg errors via the dialect's
# _handle_exception, but the pool's connect-time path can propagate the raw
# asyncpg exception (e.g. CannotConnectNowError, ConnectionDoesNotExistError)
# AND the OS-level ConnectionRefusedError without translation. The retry
# classifier must catch all of them or the helper falls through to the
# generic `except Exception` fail-fast branch and the job stays in_progress.
_RETRIABLE_DB_OUTAGE_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    DBAPIError,
    asyncpg.exceptions.CannotConnectNowError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.InterfaceError,
    asyncpg.exceptions.PostgresConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    OSError,
)


# Number of games per DB insert batch. Each game produces ~80 position rows,
# so batch_size=30 means ~2400 position rows per COPY.
#
# History: temporarily dropped to 12 on 2026-05-16 (FLAWCHESS-56 / FLAWCHESS-3Q)
# because Phase 41.1's per-batch Stockfish eval pass — STOCKFISH_POOL_SIZE engines
# run concurrently over the batch — drove a Postgres OOM-kill at batch_size=28.
# That eval pass no longer runs in this hot lane: it was moved to the decoupled
# run_eval_drain() cold lane (see _flush_batch below), so the OOM driver is gone.
# Position writes now use asyncpg binary COPY (game_repository.bulk_insert_positions),
# which is lighter than the old ORM INSERT and has no VALUES parameter ceiling.
# The 2026-05-27 dual-platform 20k-each prod stress test ran at 12 with the import
# phase nowhere near memory-bound (backend 36% / DB 27% of caps, zero swap); the
# bottleneck is the Stockfish eval drain, which batch size does not affect. Raised
# 12 -> 30 for fewer transactions during fetch+import with comfortable headroom.
_BATCH_SIZE = 30
IMPORT_TIMEOUT_SECONDS = 3 * 60 * 60  # 3 hours per D-24

# Phase 90 / SEED-017 resilience constants — no magic numbers (CLAUDE.md).
_REAPER_INTERVAL_SECONDS = 5 * 60  # 5 minutes between periodic reaper ticks
_FAILURE_RECORD_MAX_RETRIES = 5  # max attempts in failure-state retry loop
# With MAX_RETRIES=5 the loop runs attempts 0..4 with sleeps before attempts
# 1..4, giving the schedule 2/4/8/16s = 30s total. The cap (30s) never binds
# because 2*2^3 = 16 < 30; it's a safety guard for any future tuning.
_FAILURE_RECORD_BACKOFF_BASE_SECONDS = 2  # base for exponential backoff
_FAILURE_RECORD_BACKOFF_CAP_SECONDS = 30  # per-sleep cap (defensive, currently never hit)


@dataclass(slots=True)
class _PositionRowsResult:
    """Aggregate output of `_collect_position_rows`.

    Carries the position rows ready for bulk insert plus the per-game
    metadata needed by downstream stages (ply_count / result_fen bulk
    UPDATE, and the post-insert engine eval pass).
    """

    new_game_ids: Sequence[int]
    position_rows: list[dict[str, Any]] = field(default_factory=list)
    ply_counts: dict[int, int] = field(default_factory=dict)
    result_fens: dict[int, str | None] = field(default_factory=dict)
    # Each entry is (game_id, pgn_text, plies_list) — used by the eval pass
    # to avoid a second PGN parse loop and to call _board_at_ply on demand.
    game_eval_data: list[tuple[int, str, list[PlyData]]] = field(default_factory=list)


class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobState:
    job_id: str
    user_id: int
    platform: str
    username: str
    status: JobStatus = JobStatus.PENDING
    games_fetched: int = 0
    games_imported: int = 0
    error: str | None = None
    # Benchmark ingest hooks (None for user-facing imports — behavior unchanged).
    # since_ms_override: bypass get_latest_for_user_platform and fetch from this
    #   millisecond timestamp directly. Lets the same lichess username be imported
    #   once per perf_type without the second run inheriting the first run's
    #   last_synced_at cursor.
    # max_games / perf_type: passed through to the lichess client (max=, perfType=).
    since_ms_override: int | None = None
    max_games: int | None = None
    perf_type: str | None = None


# Module-level in-memory job registry
_jobs: dict[str, JobState] = {}


async def cleanup_orphaned_jobs(
    orphan_age_threshold: timedelta | None = None,
) -> None:
    """Mark any DB jobs stuck in pending/in_progress as failed.

    Called at startup (no threshold) and periodically (with IMPORT_TIMEOUT_SECONDS
    threshold) via run_periodic_reaper (Phase 90 / SEED-017).

    Args:
        orphan_age_threshold: Passed through to fail_orphaned_jobs. None means
            reap all non-terminal jobs (startup behavior). A timedelta reaps
            only jobs older than the threshold (periodic reaper behavior to
            avoid killing live healthy imports, per Pitfall 3 in 90-RESEARCH.md).
    """
    async with async_session_maker() as session:
        count = await import_job_repository.fail_orphaned_jobs(
            session,
            orphan_age_threshold=orphan_age_threshold,
        )
        await session.commit()
        if count:
            logger.info("Marked %d orphaned import job(s) as failed", count)


def create_job(
    user_id: int,
    platform: str,
    username: str,
    *,
    since_ms_override: int | None = None,
    max_games: int | None = None,
    perf_type: str | None = None,
) -> str:
    """Create a new import job and register it in memory.

    Args:
        user_id: Internal database user ID.
        platform: 'chess.com' or 'lichess'.
        username: Platform username to import from.
        since_ms_override: Optional benchmark-only override; when set, run_import
            uses this Unix-millisecond timestamp instead of consulting the most
            recent completed import_job for ``last_synced_at``.
        max_games: Optional benchmark-only cap on lichess ``max`` parameter.
        perf_type: Optional benchmark-only lichess ``perfType`` filter.

    Returns:
        The generated UUID string for the new job.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobState(
        job_id=job_id,
        user_id=user_id,
        platform=platform,
        username=username,
        since_ms_override=since_ms_override,
        max_games=max_games,
        perf_type=perf_type,
    )
    return job_id


def get_job(job_id: str) -> JobState | None:
    """Return the JobState for the given job_id, or None if not found.

    Args:
        job_id: UUID string of the job.
    """
    return _jobs.get(job_id)


def find_active_job(user_id: int, platform: str) -> JobState | None:
    """Return an existing PENDING or IN_PROGRESS job for this user+platform.

    Used to prevent duplicate concurrent imports for the same user and platform.

    Args:
        user_id: Internal database user ID.
        platform: 'chess.com' or 'lichess'.

    Returns:
        A JobState if an active job exists, otherwise None.
    """
    for job in _jobs.values():
        if (
            job.user_id == user_id
            and job.platform == platform
            and job.status in (JobStatus.PENDING, JobStatus.IN_PROGRESS)
        ):
            return job
    return None


def find_active_jobs_for_user(user_id: int) -> list[JobState]:
    """Return all PENDING or IN_PROGRESS jobs for the given user.

    Used to restore active job visibility after page refresh or re-login.

    Args:
        user_id: Internal database user ID.

    Returns:
        List of active JobState entries (may be empty).
    """
    return [
        job
        for job in _jobs.values()
        if job.user_id == user_id and job.status in (JobStatus.PENDING, JobStatus.IN_PROGRESS)
    ]


def count_active_platform_jobs(platform: str, exclude_user_id: int) -> int:
    """Return count of active import jobs for a platform from other users.

    Used to show "X other users are importing" (D-23). Excludes the
    requesting user's own jobs so the count reflects OTHER importers only.

    Args:
        platform: 'chess.com' or 'lichess'.
        exclude_user_id: User ID to exclude from the count (the requesting user).
    """
    return sum(
        1
        for job in _jobs.values()
        if job.platform == platform
        and job.status in (JobStatus.PENDING, JobStatus.IN_PROGRESS)
        and job.user_id != exclude_user_id
    )


# Bug fix (Phase 90, SEED-017): cleanup_orphaned_jobs() only ran at backend
# startup. A Postgres-only restart (or any DB recovery window the backend
# survives) left in_progress jobs stuck forever. This coroutine runs
# every _REAPER_INTERVAL_SECONDS and uses an orphan-age threshold of
# IMPORT_TIMEOUT_SECONDS (3h) so a live healthy import is never reaped
# (Pitfall 3 in 90-RESEARCH.md).
async def run_periodic_reaper() -> None:
    """Periodically mark stuck import jobs as failed.

    Companion to cleanup_orphaned_jobs (which only runs at backend startup).
    A Postgres-only restart leaves the backend up, so without this loop
    orphaned in_progress jobs would stay stuck until the next backend deploy.

    Sleeps BEFORE the first cleanup call so the startup-time cleanup_orphaned_jobs()
    handles T=0 and this reaper handles T+5min, T+10min, etc.

    Wired in app/main.py lifespan — started on startup, cancelled+awaited on shutdown.
    """
    while True:
        await asyncio.sleep(_REAPER_INTERVAL_SECONDS)
        try:
            await cleanup_orphaned_jobs(
                orphan_age_threshold=timedelta(seconds=IMPORT_TIMEOUT_SECONDS)
            )
        except Exception:
            logger.exception("Periodic orphan-job reaper failed")
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.capture_exception()


# Bug fix (Phase 90, SEED-017, FLAWCHESS-3Q): the original except-block
# opened a session + UPDATE'd while Postgres was still in crash recovery
# (OperationalError). The capture_exception swallowed it and the job
# stayed in_progress forever. Retry across a ~30s recovery window
# (2/4/8/16s backoff = 30s total) before giving up. Mirrors the in-tree
# retry pattern from app/services/lichess_client.py.
async def _record_failure_with_retry(
    *,
    job_id: str,
    status: Literal["failed"],
    games_fetched: int,
    games_imported: int,
    error_message: str,
    completed_at: datetime,
) -> None:
    """Persist a job's failure state with bounded retry against DB recovery.

    Retries on sqlalchemy.exc.OperationalError (the SQLAlchemy wrapper for
    asyncpg connection errors like CannotConnectNowError — Assumption A3,
    verified per Pitfall 4 in 90-RESEARCH.md). Non-transient exceptions
    fail fast. Sentry capture happens only on final exhaustion (CLAUDE.md rule).

    Backoff schedule with MAX_RETRIES=5: sleeps 2/4/8/16s between attempts
    (30s total). The 30s cap never binds at current settings; it's a
    defensive guard for future tuning. The 2026-05-16 Postgres crash-
    recovery window was ~2s, so 30s is generous.

    Cancellation contract (WR-07): this helper is cancellation-aware. A
    CancelledError raised during asyncio.sleep (e.g. lifespan shutdown
    cancelling an in-flight run_import) propagates without retry — it is
    a BaseException, not Exception, so neither except OperationalError nor
    except Exception catches it. The periodic orphan-job reaper is the
    backstop: jobs left in_progress because the failure-state UPDATE was
    cancelled mid-retry will be reaped on the next reaper tick.

    Args:
        job_id: The import job UUID to update.
        status: Always "failed" — typed as Literal to enforce CLAUDE.md no-bare-str rule.
        games_fetched: Counters to persist alongside the failed status.
        games_imported: Counters to persist alongside the failed status.
        error_message: Human-readable failure reason (the import's own error, not
            a retry-loop error — variables go via set_context, not inline).
        completed_at: Timestamp to record as the job's completion time.
    """
    last_exc: BaseException | None = None
    for attempt in range(_FAILURE_RECORD_MAX_RETRIES):
        if attempt > 0:
            backoff = min(
                _FAILURE_RECORD_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                _FAILURE_RECORD_BACKOFF_CAP_SECONDS,
            )
            logger.warning(
                "Retrying failure-state UPDATE for job %s (attempt %d/%d) in %ds",
                job_id,
                attempt + 1,
                _FAILURE_RECORD_MAX_RETRIES,
                backoff,
            )
            await asyncio.sleep(backoff)
            # UAT 2026-05-20 fix: invalidate the pool between retries. After a
            # Postgres restart, the existing asyncpg connections in SA's pool
            # are stale — the very next checkout raises InterfaceError ("the
            # underlying connection is closed"). engine.dispose() drops the
            # entire pool so the next session opens a brand-new connection.
            try:
                await engine.dispose()
            except Exception:
                logger.warning(
                    "engine.dispose() during failure-record retry raised — continuing",
                    exc_info=True,
                )
        try:
            async with async_session_maker() as session:
                await import_job_repository.update_import_job(
                    session,
                    job_id=job_id,
                    must_exist=True,
                    status=status,
                    games_fetched=games_fetched,
                    games_imported=games_imported,
                    error_message=error_message,
                    completed_at=completed_at,
                )
                await session.commit()
                return
        except asyncio.CancelledError:
            # WR-07: cancellation contract — propagate, do not retry. The
            # periodic reaper picks up the stuck job on its next tick.
            raise
        except ImportJobNotFound:
            # CR-01: bootstrap scope never committed, so no DB row exists. Retrying
            # cannot help — the row truly is missing. Log + capture once, then
            # stop. The in-memory JobState still reflects FAILED for the caller.
            logger.error(
                "Cannot persist failure state for job %s: no DB row exists "
                "(bootstrap session never committed)",
                job_id,
            )
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.set_context("import", {"job_id": job_id})
            sentry_sdk.capture_message(
                "Failure-state UPDATE skipped: import job row missing",
                level="error",
            )
            return
        except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
            # UAT 2026-05-20 — broadened from `except OperationalError` to the
            # full tuple above. The original narrow catch let real Postgres-
            # restart outages fall through to the generic Exception branch and
            # leave jobs stranded in_progress. See _RETRIABLE_DB_OUTAGE_ERRORS
            # comment for the rationale.
            last_exc = exc
            continue
        except Exception as exc:
            # Non-transient error — fail fast, no point retrying.
            logger.exception("Non-transient error recording failure state for job %s", job_id)
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.capture_exception(exc)
            return

    # All retries exhausted — capture once per CLAUDE.md (last-attempt rule).
    logger.error(
        "Failed to record failure state for job %s after %d retries",
        job_id,
        _FAILURE_RECORD_MAX_RETRIES,
    )
    if last_exc is not None:
        sentry_sdk.set_tag("source", "import")
        sentry_sdk.capture_exception(last_exc)


async def _bootstrap_import_job(job: JobState, job_id: str) -> datetime | None:
    """Bootstrap scope: previous-job lookup + job-record creation.

    Extracted from run_import (WR-01: nesting-depth reduction). Owns its own
    AsyncSession so the bootstrap row is committed and the session is closed
    before the batch loop begins. Only the plain scalar `previous_last_synced_at`
    crosses the boundary, avoiding any DetachedInstanceError risk on cross-scope
    ORM attribute access (Pitfall 2, 90-RESEARCH.md).
    """
    async with async_session_maker() as bootstrap_session:
        previous_job = await import_job_repository.get_latest_for_user_platform(
            bootstrap_session, job.user_id, job.platform, job.username
        )
        # Extract scalar INSIDE the bootstrap scope (Pitfall 2 mitigation, Assumption A2).
        previous_last_synced_at: datetime | None = (
            previous_job.last_synced_at if previous_job is not None else None
        )
        await import_job_repository.create_import_job(
            bootstrap_session,
            job_id=job_id,
            user_id=job.user_id,
            platform=job.platform,
            username=job.username,
        )
        await bootstrap_session.commit()
    return previous_last_synced_at


async def _flush_batch_with_progress(
    batch: list[NormalizedGame], job: JobState, job_id: str
) -> None:
    """Per-batch scope: flush rows + bump progress counter in one session.

    Extracted from run_import (WR-01: nesting-depth reduction). Each call
    opens, commits, and releases a single AsyncSession so per-batch session
    lifetime is bounded (Phase 90 / SEED-018).
    """
    async with async_session_maker() as session:
        imported = await _flush_batch(session, batch, job.user_id)
        job.games_imported += imported
        # Persist incremental counters so orphaned-job cleanup and post-restart
        # status reads reflect accurate progress (not zero) if the server
        # crashes mid-import.
        await import_job_repository.update_import_job(
            session,
            job_id=job_id,
            status="in_progress",
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
        )
        await session.commit()


async def _complete_import_job(job: JobState, job_id: str) -> None:
    """Completion scope: mark job complete and advance last_synced_at.

    Extracted from run_import (WR-01: nesting-depth reduction). Always
    advances last_synced_at so a no-op sync (0 new games) still confirms
    we're caught up; without this, the next sync would re-fetch everything
    if the previous completed job had last_synced_at=NULL.
    """
    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        await import_job_repository.update_import_job(
            session,
            job_id=job_id,
            status="completed",
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
            completed_at=now,
            last_synced_at=now,
        )
        await session.commit()
    # Phase 94.1 D-03 / ROADMAP SC 3: Stage A fires AFTER commit, NOT inside the
    # import transaction. Fire-and-forget — errors are captured to Sentry inside
    # compute_stage_a; never propagated.
    asyncio.create_task(compute_stage_a(job.user_id))

    # Quick fix 260527-u3u: Stage B re-fires here for the all-Stage-5c-covered case
    # where eval_drain never ticks for this user — keeps the cold-drain trigger at
    # eval_drain.py:566-568 in place; both sites are idempotent (Stage A/B write
    # disjoint rows; compute_stage_b is upsert-safe). Gated on the same
    # users_with_zero_pending check the cold drain uses, which excludes users with
    # an active import (Plan 13 Stage B gate). A fresh read session is used (never
    # the import-write session) to mirror the eval_drain pattern.
    try:
        async with async_session_maker() as read_session:
            zero_pending = await game_repository.users_with_zero_pending(
                read_session, [job.user_id]
            )
            if zero_pending:
                # Quick 260529-015: mark BEFORE scheduling so the 3s readiness
                # poll can't observe pending==0 and unlock Tier 2 in the window
                # before compute_stage_b starts writing rows.
                percentile_compute_registry.mark(job.user_id)
                asyncio.create_task(compute_stage_b(job.user_id))
    except asyncio.CancelledError:
        # Lifespan shutdown — propagate (mirrors WR-07 cancellation contract).
        raise
    except Exception as exc:
        sentry_sdk.set_context(
            "percentile_compute",
            {"user_id": job.user_id, "stage": "B", "trigger": "import_complete"},
        )
        sentry_sdk.capture_exception(exc)


async def run_import(job_id: str) -> None:
    """Background import orchestrator — launched via asyncio.create_task.

    Orchestrates the full import pipeline:
    1. Checks for previous completed job to determine incremental sync boundary.
    2. Fetches games from the platform client (chess.com or lichess).
    3. Batches games, bulk inserts to DB, computes Zobrist hashes, stores positions.
    4. Updates job to COMPLETED or FAILED with final counts.

    This function never re-raises exceptions — failures are captured in the job state.

    Args:
        job_id: UUID of the job to run (must already be registered in _jobs).
    """
    job = _jobs.get(job_id)
    if job is None:
        logger.error("run_import called with unknown job_id: %s", job_id)
        return

    job.status = JobStatus.IN_PROGRESS

    try:
        async with asyncio.timeout(IMPORT_TIMEOUT_SECONDS):
            # Phase 90 / SEED-018 / WR-01: pipeline reads as a list of stages.
            # Each helper owns its own AsyncSession scope (bootstrap / per-batch /
            # completion) so session lifetime is bounded — the old single-session
            # pattern was the secondary accumulation surface alongside the Stage 5
            # unique-SQL leak fixed in Plan 90-01.
            previous_last_synced_at = await _bootstrap_import_job(job, job_id)

            def _on_game_fetched() -> None:
                job.games_fetched += 1

            async with httpx.AsyncClient(timeout=60.0) as client:
                game_iter = _make_game_iterator(
                    client, job, previous_last_synced_at, _on_game_fetched
                )
                batch: list[NormalizedGame] = []
                async for game_dict in game_iter:
                    batch.append(game_dict)
                    if len(batch) >= _BATCH_SIZE:
                        await _flush_batch_with_progress(batch, job, job_id)
                        batch = []
                if batch:
                    # Trailing batch < _BATCH_SIZE.
                    await _flush_batch_with_progress(batch, job, job_id)

            await _complete_import_job(job, job_id)
            job.status = JobStatus.COMPLETED

    except TimeoutError:
        # 3-hour timeout exceeded (D-24). Partial results already persisted
        # via incremental batch commits — re-sync picks up where it left off.
        logger.warning("Import job %s timed out after %d seconds", job_id, IMPORT_TIMEOUT_SECONDS)
        job.status = JobStatus.FAILED
        job.error = "Import timed out — re-sync to continue where it left off"
        sentry_sdk.set_context(
            "import", {"job_id": job_id, "user_id": job.user_id, "platform": job.platform}
        )
        sentry_sdk.capture_exception()

        # Bug fix (Phase 90, SEED-017, FLAWCHESS-3Q): use bounded-retry helper so
        # a Postgres crash-recovery window does not swallow this failed transition.
        await _record_failure_with_retry(
            job_id=job_id,
            status="failed",
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
            error_message=job.error or "Import timed out — re-sync to continue where it left off",
            completed_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        logger.exception("Import job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        sentry_sdk.set_context(
            "import", {"job_id": job_id, "user_id": job.user_id, "platform": job.platform}
        )
        sentry_sdk.capture_exception(exc)

        # Bug fix (Phase 90, SEED-017, FLAWCHESS-3Q): use bounded-retry helper so
        # a Postgres crash-recovery window does not swallow this failed transition.
        await _record_failure_with_retry(
            job_id=job_id,
            status="failed",
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
            error_message=str(exc),
            completed_at=datetime.now(timezone.utc),
        )


async def _make_game_iterator(
    client: httpx.AsyncClient,
    job: JobState,
    previous_last_synced_at: datetime | None,
    on_game_fetched: Callable[[], None],
) -> AsyncIterator[NormalizedGame]:
    """Return the appropriate platform async iterator based on job.platform.

    Bug fix (Phase 90, SEED-018, Pitfall 2): accepts `previous_last_synced_at`
    as a plain scalar (datetime | None) instead of a `previous_job` ORM instance.
    The scalar is extracted inside the bootstrap session scope in `run_import`,
    so no ORM instance crosses the bootstrap-to-batch-loop boundary (eliminating
    any risk of DetachedInstanceError from cross-scope ORM attribute access).
    """
    if job.platform == "chess.com":
        since_timestamp: datetime | None = previous_last_synced_at

        async for game in chesscom_client.fetch_chesscom_games(
            client,
            username=job.username,
            user_id=job.user_id,
            since_timestamp=since_timestamp,
            on_game_fetched=on_game_fetched,
        ):
            yield game

    elif job.platform == "lichess":
        if job.since_ms_override is not None:
            # Benchmark ingest path: skip get_latest_for_user_platform entirely.
            # The same lichess user can be imported once per perf_type, and the
            # second run must not inherit the first run's last_synced_at cursor.
            since_ms: int | None = job.since_ms_override
        else:
            since_ms = None
            if previous_last_synced_at is not None:
                last_synced = previous_last_synced_at
                if last_synced.tzinfo is None:
                    last_synced = last_synced.replace(tzinfo=timezone.utc)
                since_ms = int(last_synced.timestamp() * 1000)

        async for game in lichess_client.fetch_lichess_games(
            client,
            username=job.username,
            user_id=job.user_id,
            since_ms=since_ms,
            max_games=job.max_games,
            perf_type=job.perf_type,
            on_game_fetched=on_game_fetched,
        ):
            yield game

    else:
        raise ValueError(f"Unknown platform: {job.platform!r}")


async def _flush_batch(
    session: Any,
    batch: list[NormalizedGame],
    user_id: int,
) -> int:
    """Insert a batch of NormalizedGame objects, compute hashes, insert positions.

    Uses process_game_pgn for a single PGN parse per game (D-01),
    platform_game_id lookup to avoid redundant SELECT Game.pgn (D-03),
    and bulk UPDATE for ply_count/result_fen (D-04).

    WR-05: this function does NOT commit. The caller owns the transaction
    boundary so the row inserts and the per-batch progress-counter UPDATE
    can land in a single atomic transaction. See _flush_batch_with_progress.

    Args:
        session: AsyncSession to use.
        batch: List of NormalizedGame objects from platform client.
        user_id: Denormalized user ID for position rows.

    Returns:
        Number of newly inserted games (duplicates excluded).
    """
    # Stage 1: bulk-insert games + reparse PGNs into position rows + per-game
    # eval data. Helper handles the early-empty-batch case via empty result.
    rows_result = await _collect_position_rows(session, batch, user_id)
    if not rows_result.new_game_ids:
        return 0

    # Stage 2: bulk insert positions (chunked at 1,700 rows by repository).
    if rows_result.position_rows:
        await game_repository.bulk_insert_positions(session, rows_result.position_rows)

    # Phase 91 / SEED-023: Stages 3a (target collection) and 4 (asyncio.gather +
    # _apply_eval_results) have been removed from the hot lane. The eval pass now
    # runs in the cold-lane coroutine run_eval_drain() (app/services/eval_drain.py).
    # This eliminates the 20-40 s held-transaction OOM driver identified in the
    # 2026-05-20 stress test (FLAWCHESS-3Q / SEED-023).

    # Bug fix (Phase 90, SEED-018, FLAWCHESS-56 / FLAWCHESS-3Q):
    # Old code used case(...)+IN whose SQL text varied per batch (game-id set
    # differs every batch). That grew SQLAlchemy's compile cache and asyncpg's
    # prepared-statement LRU unboundedly, OOM-killing prod on 2026-03-22 and
    # 2026-05-16. The two bound-param executemany groups below emit invariant
    # SQL text — compiled once, prepared once, reused forever.
    #
    # Two groups (not one COALESCE) because result_fen must be preserved for
    # games whose PGN parses to result_fen=None: only update result_fen for
    # ids where we actually parsed a value. The COALESCE alternative is
    # fragile (SQLAlchemy issue #9075 drops the expression in some executemany
    # contexts). See 90-RESEARCH.md Pitfall 1.

    # Stage 5: bulk UPDATE ply_count and result_fen via two executemany groups.
    #
    # We target the underlying Table (`Game.__table__`) rather than the ORM
    # `Game` mapper. SQLAlchemy 2.x routes `update(Game).where(...)` with
    # executemany through the ORM bulk-update machinery, which (a) refuses to
    # run without an explicit `synchronize_session=False` and (b) even then,
    # expects parameter keys named after the PK column (`id`) to use the ORM
    # Bulk UPDATE by Primary Key path. Going Table-level emits plain Core SQL,
    # bypasses both restrictions, and yields exactly the invariant prepared
    # statement we want for the leak fix. The identity map is irrelevant here
    # — we never read these rows back inside the same session; the very next
    # batch opens a fresh session (Plan 90-02).
    #
    # Caught in UAT 2026-05-20: the original ORM-level statement raised
    # "bulk synchronize of persistent objects not supported when using bulk
    #  update with additional WHERE criteria right now" against a real DB.
    # Unit tests using AsyncMock sessions never exercised this path. Pinned
    # by TestFlushBatchStage5RealDb against the rollback-scoped db_session.
    if rows_result.ply_counts:
        # ty: __table__ is typed as FromClause on declarative base, but is a
        # Table at runtime. Cast at module level not needed — the Table API
        # is what we use here.
        games_table = Game.__table__
        # Group (a): ply_count for ALL games in the batch.
        ply_count_stmt = (
            update(games_table)  # ty: ignore[invalid-argument-type]
            .where(games_table.c.id == bindparam("b_id"))
            .values(ply_count=bindparam("b_pc"))
        )
        ply_count_params: list[dict[str, Any]] = [
            {"b_id": gid, "b_pc": pc} for gid, pc in rows_result.ply_counts.items()
        ]
        await session.execute(ply_count_stmt, ply_count_params)

        # Group (b): result_fen ONLY for games where result_fen is not None.
        # Games without a parsed result_fen keep their prior column value (or
        # stay NULL if never set) — they are NOT actively overwritten to NULL.
        fen_params: list[dict[str, Any]] = [
            {"b_id": gid, "b_rf": fen}
            for gid, fen in rows_result.result_fens.items()
            if fen is not None
        ]
        if fen_params:
            fen_stmt = (
                update(games_table)  # ty: ignore[invalid-argument-type]
                .where(games_table.c.id == bindparam("b_id"))
                .values(result_fen=bindparam("b_rf"))
            )
            await session.execute(fen_stmt, fen_params)

    # Stage 5c: mark games whose entry plies are already fully covered (D-08 hot-lane gate).
    # CONTEXT.md D-08 / SEED-023: A game is "covered" if both _collect_midgame_eval_targets
    # and _collect_endgame_span_eval_targets return empty for its game_eval_data entry
    # (all entry plies already have lichess %eval, or the game has no entry plies at all).
    # These games are set evals_completed_at = NOW() immediately; the cold drain skips them.
    # Games with pending entry plies keep evals_completed_at = NULL (cold drain will handle them).
    covered_ids = _collect_covered_game_ids(rows_result.game_eval_data)
    if covered_ids:
        now_ts = datetime.now(timezone.utc)
        stage5c_games_table = Game.__table__
        covered_stmt = (
            update(stage5c_games_table)  # ty: ignore[invalid-argument-type]
            .where(stage5c_games_table.c.id == bindparam("b_id"))
            .values(evals_completed_at=now_ts)
        )
        await session.execute(covered_stmt, [{"b_id": gid} for gid in covered_ids])
        # Bug fix (quick 260611): covered games never reach the cold drain (the
        # drain only picks evals_completed_at IS NULL), so the drain's
        # _classify_and_insert_flaws never ran for them — games imported WITH
        # full lichess %eval got eval_cp on positions but zero game_flaws rows
        # (badges showed 0 while the live eval chart showed flaws). Classify
        # here, in the same transaction as the position inserts, so flaw rows
        # commit atomically with the batch.
        await _classify_and_insert_flaws(session, covered_ids)

    # WR-05: caller owns the commit (single transaction per batch).
    return len(rows_result.new_game_ids)


async def _collect_position_rows(
    session: AsyncSession,
    batch: Sequence[NormalizedGame],
    user_id: int,
) -> _PositionRowsResult:
    """Bulk-insert games + reparse PGNs into position rows + per-game eval data.

    Returns an aggregate result with `new_game_ids` empty if no games were
    inserted (caller should short-circuit). The session is owned by the caller
    and the bulk_insert_games + select queries execute within its transaction.
    """
    # Build platform_game_id -> PGN lookup from batch (D-03: avoid SELECT Game.pgn).
    pgn_by_platform_id: dict[str, str] = {}
    for g in batch:
        if isinstance(g, NormalizedGame):
            pgn_by_platform_id[g.platform_game_id] = g.pgn
        else:
            pgn_by_platform_id[g.get("platform_game_id", "")] = g.get("pgn", "")  # type: ignore[union-attr] — dict fallback for test mocks

    # Convert to dicts and bulk insert games.
    game_dicts = [g.model_dump() if isinstance(g, NormalizedGame) else g for g in batch]  # type: ignore[union-attr] — dict fallback for test mocks
    new_game_ids = await game_repository.bulk_insert_games(session, game_dicts)

    if not new_game_ids:
        return _PositionRowsResult(new_game_ids=[])

    # Lightweight SELECT for (id, platform_game_id) only — no PGN transfer (D-03).
    result = await session.execute(
        select(Game.id, Game.platform_game_id).where(Game.id.in_(new_game_ids))
    )
    id_platform_pairs = result.fetchall()

    out = _PositionRowsResult(new_game_ids=new_game_ids)

    # Process each game's PGN with unified function (D-01: single parse).
    for game_id, platform_game_id in id_platform_pairs:
        pgn = pgn_by_platform_id.get(platform_game_id, "")
        if not pgn:
            continue
        try:
            processing_result = process_game_pgn(pgn)
        except Exception:
            logger.warning("Failed to process PGN for game_id=%s", game_id)
            sentry_sdk.set_context("import", {"game_id": game_id})
            sentry_sdk.capture_exception()
            continue

        if processing_result is None:
            continue

        # Accumulate ply_count and result_fen for bulk UPDATE (D-04).
        out.ply_counts[game_id] = processing_result["ply_count"]
        out.result_fens[game_id] = processing_result["result_fen"]

        # Retain plies for the eval pass — done here to avoid a second PGN parse loop.
        out.game_eval_data.append((game_id, pgn, list(processing_result["plies"])))

        # Build position rows from plies.
        for ply_data in processing_result["plies"]:
            row: dict[str, Any] = {
                "game_id": game_id,
                "user_id": user_id,
                "ply": ply_data["ply"],
                "white_hash": ply_data["white_hash"],
                "black_hash": ply_data["black_hash"],
                "full_hash": ply_data["full_hash"],
                "move_san": ply_data["move_san"],
                "clock_seconds": ply_data["clock_seconds"],
                "eval_cp": ply_data["eval_cp"],
                "eval_mate": ply_data["eval_mate"],
                "material_count": ply_data["material_count"],
                "material_signature": ply_data["material_signature"],
                "material_imbalance": ply_data["material_imbalance"],
                "has_opposite_color_bishops": ply_data["has_opposite_color_bishops"],
                "piece_count": ply_data["piece_count"],
                "backrank_sparse": ply_data["backrank_sparse"],
                "mixedness": ply_data["mixedness"],
                "endgame_class": ply_data["endgame_class"],
                "phase": ply_data["phase"],
            }
            out.position_rows.append(row)

    return out


def _collect_covered_game_ids(
    game_eval_data: list[tuple[int, str, list[PlyData]]],
) -> list[int]:
    """Return IDs of games whose entry plies need no further Stockfish evaluation.

    CONTEXT.md D-08 / SEED-023 Stage 5c: a game is "covered" when both
    _collect_midgame_eval_targets and _collect_endgame_span_eval_targets return
    empty lists for its game_eval_data entry. This means either:
      - All entry plies already have lichess %eval populated (T-78-17), or
      - The game has no midgame or endgame entry plies at all (very short game).

    These games are marked evals_completed_at = NOW() by the hot-lane Stage 5c
    UPDATE. Games with pending entry plies are left with evals_completed_at = NULL
    so the cold-drain coroutine run_eval_drain() can pick them up asynchronously.

    Pure function: no session, no engine calls. Delegates to the same helpers
    used by the cold drain (_collect_midgame_eval_targets,
    _collect_endgame_span_eval_targets from app.services.eval_drain) so a game
    marked covered here is by definition one the drain would also find empty
    targets for — false positives are structurally impossible (T-91-10).

    Args:
        game_eval_data: List of (game_id, pgn_text, plies_list) tuples as
            produced by _collect_position_rows into _PositionRowsResult.game_eval_data.

    Returns:
        List of game IDs for which both target collectors return empty.
    """
    covered: list[int] = []
    for game_id, pgn_text, plies_list in game_eval_data:
        single_game_data: list[tuple[int, str, list[PlyData]]] = [(game_id, pgn_text, plies_list)]
        midgame_targets = _collect_midgame_eval_targets(single_game_data)
        endgame_targets = _collect_endgame_span_eval_targets(single_game_data)
        if not midgame_targets and not endgame_targets:
            covered.append(game_id)
    return covered
