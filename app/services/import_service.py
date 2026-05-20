"""Import service: in-memory job registry and background import orchestrator.

Manages import jobs from chess.com and lichess, including:
- Job creation and state management (in-memory registry)
- Duplicate import prevention (active job detection)
- Background async orchestration via asyncio.create_task
- Incremental sync via last_synced_at from previous completed jobs
- Zobrist hash computation and bulk DB persistence
"""

import asyncio
import io
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

import chess
import chess.pgn
import httpx
import sentry_sdk
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories import game_repository, import_job_repository
from app.repositories.import_job_repository import ImportJobNotFound
from app.schemas.normalization import NormalizedGame
from app.services import chesscom_client, engine as engine_service, lichess_client
from app.services.zobrist import PlyData, process_game_pgn

logger = logging.getLogger(__name__)


def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to the board state at *target_ply* (0-indexed, pre-push).

    Phase 78 IMP-01: used by the import-time eval pass to reconstruct the board
    at a span-entry ply without retaining chess.Board objects in memory during
    the main PGN walk. Mirrors the backfill script approach (Option A, RESEARCH.md).

    Returns None if the PGN is unparseable or the game ends before target_ply.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i == target_ply:
            return board
        board.push(node.move)
    return None


# Number of games per DB insert batch. Each game produces ~80 position rows,
# so batch_size=12 means ~960 position rows per INSERT.
#
# Bug fix (2026-05-16, FLAWCHESS-56 / FLAWCHESS-3Q): reduced from 28 back to 12.
# The old comment claimed "~1.8MB per batch — safe" but that only counted the
# position rows; it ignored the per-batch Stockfish eval pass added in Phase
# 41.1, which runs STOCKFISH_POOL_SIZE engines concurrently over the batch.
# At batch_size=28 with prod's 4-engine pool this drove a Postgres OOM-kill
# mid-import. Keep this low until the orphan-reaper / atomic-import-guard
# follow-up phase lands. The dominant memory cost is the engine pass, not the
# INSERT, so batch size is the cheapest lever.
_BATCH_SIZE = 12
IMPORT_TIMEOUT_SECONDS = 3 * 60 * 60  # 3 hours per D-24

# Phase 90 / SEED-017 resilience constants — no magic numbers (CLAUDE.md).
_REAPER_INTERVAL_SECONDS = 5 * 60  # 5 minutes between periodic reaper ticks
_FAILURE_RECORD_MAX_RETRIES = 5  # max attempts in failure-state retry loop
_FAILURE_RECORD_BACKOFF_BASE_SECONDS = 2  # base for exponential backoff (2/4/8/16/30s)
_FAILURE_RECORD_BACKOFF_CAP_SECONDS = 30  # per-sleep cap (~60s total budget)


@dataclass(slots=True)
class _EvalTarget:
    """One row scheduled for engine evaluation in the import-time eval pass.

    Collected up-front across all games in an import batch so the per-eval
    asyncio.gather() can fan out to every Stockfish worker in the module-level
    pool. Without batching the gather, a multi-worker pool would still serve
    only one in-flight evaluation at a time.
    """

    game_id: int
    ply: int
    eval_kind: Literal["middlegame_entry", "endgame_span_entry"]
    endgame_class: int | None  # None for middlegame; int for endgame span entry
    board: chess.Board


@dataclass(slots=True)
class _PositionRowsResult:
    """Aggregate output of `_collect_position_rows`.

    Carries the position rows ready for bulk insert plus the per-game
    metadata needed by downstream stages (move_count / result_fen bulk
    UPDATE, and the post-insert engine eval pass).
    """

    new_game_ids: Sequence[int]
    position_rows: list[dict[str, Any]] = field(default_factory=list)
    move_counts: dict[int, int] = field(default_factory=dict)
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
# stayed in_progress forever. Retry across a ~60s recovery window
# (2/4/8/16/30s backoff) before giving up. Mirrors the in-tree retry
# pattern from app/services/lichess_client.py.
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

    Backoff schedule: 2/4/8/16/30s (~60s total budget). The 2026-05-16
    Postgres crash-recovery window was ~2s, so this is generous.

    Args:
        job_id: The import job UUID to update.
        status: Always "failed" — typed as Literal to enforce CLAUDE.md no-bare-str rule.
        games_fetched: Counters to persist alongside the failed status.
        games_imported: Counters to persist alongside the failed status.
        error_message: Human-readable failure reason (the import's own error, not
            a retry-loop error — variables go via set_context, not inline).
        completed_at: Timestamp to record as the job's completion time.
    """
    last_exc: OperationalError | None = None
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
        except OperationalError as exc:
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
            # Bug fix (Phase 90, SEED-018, FLAWCHESS-56 / FLAWCHESS-3Q): three session
            # scopes (bootstrap / per-batch / completion) instead of one. The old
            # single-session-for-whole-import pattern was the secondary accumulation
            # surface alongside the Stage 5 unique-SQL leak fixed in Plan 90-01.
            # `expire_on_commit=False` keeps loaded scalars accessible after commit,
            # but we extract `previous_last_synced_at` as a local scalar inside the
            # bootstrap scope to avoid any risk of DetachedInstanceError from
            # cross-scope ORM attribute access (Pitfall 2, 90-RESEARCH.md).

            # Bootstrap scope: previous-job lookup + job-record creation.
            async with async_session_maker() as bootstrap_session:
                previous_job = await import_job_repository.get_latest_for_user_platform(
                    bootstrap_session, job.user_id, job.platform, job.username
                )
                # Extract scalar INSIDE the bootstrap scope (Pitfall 2 mitigation,
                # Assumption A2). After the scope closes, bootstrap_session is no
                # longer valid; only the plain scalar crosses the boundary.
                previous_last_synced_at: datetime | None = (
                    previous_job.last_synced_at if previous_job is not None else None
                )
                # Create the DB record for this import job.
                await import_job_repository.create_import_job(
                    bootstrap_session,
                    job_id=job_id,
                    user_id=job.user_id,
                    platform=job.platform,
                    username=job.username,
                )
                await bootstrap_session.commit()
            # bootstrap_session is now closed — only `previous_last_synced_at`
            # (a plain scalar) carries state into the batch loop.

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
                        # Per-batch scope: flush + progress update, then release session.
                        async with async_session_maker() as session:
                            imported = await _flush_batch(session, batch, job.user_id)
                            job.games_imported += imported
                            # Persist incremental counters to DB after each batch so that
                            # orphaned-job cleanup and post-restart status reads reflect
                            # accurate progress (not zero) if the server crashes mid-import.
                            await import_job_repository.update_import_job(
                                session,
                                job_id=job_id,
                                status="in_progress",
                                games_fetched=job.games_fetched,
                                games_imported=job.games_imported,
                            )
                            await session.commit()
                        batch = []

                # Flush any remaining games (trailing batch < _BATCH_SIZE).
                if batch:
                    async with async_session_maker() as session:
                        imported = await _flush_batch(session, batch, job.user_id)
                        job.games_imported += imported
                        # Persist incremental counters for the trailing batch as well.
                        await import_job_repository.update_import_job(
                            session,
                            job_id=job_id,
                            status="in_progress",
                            games_fetched=job.games_fetched,
                            games_imported=job.games_imported,
                        )
                        await session.commit()

            # Completion scope: mark job complete — always advance last_synced_at so
            # that future syncs start from this point. A no-op sync (0 new games)
            # still confirms we're caught up — without this, the next sync would
            # re-fetch everything if the previous completed job had
            # last_synced_at=NULL (e.g. after a crash recovery re-sync).
            now = datetime.now(timezone.utc)
            completion_fields: dict[str, object] = {
                "status": "completed",
                "games_fetched": job.games_fetched,
                "games_imported": job.games_imported,
                "completed_at": now,
                "last_synced_at": now,
            }
            async with async_session_maker() as session:
                await import_job_repository.update_import_job(
                    session,
                    job_id=job_id,
                    **completion_fields,
                )
                await session.commit()

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
    on_game_fetched: Any,
):
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
    and bulk CASE UPDATE for move_count/result_fen (D-04).

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
        await session.commit()
        return 0

    # Stage 2: bulk insert positions (chunked at 1,700 rows by repository).
    if rows_result.position_rows:
        await game_repository.bulk_insert_positions(session, rows_result.position_rows)

    # Stage 3 / 3a: collect engine eval targets (middlegame entries + per-class
    # endgame span entries). Phase 78 IMP-01 / Phase 79 PHASE-IMP-01 — runs
    # AFTER bulk_insert_positions (rows exist in DB) and BEFORE the final
    # session.commit() so all eval UPDATEs land in the same transaction.
    #
    # Two-phase to fan out engine work to the EnginePool:
    #   (a) collect all eval targets across the import batch (no engine, no DB),
    #   (b) await asyncio.gather(engine.evaluate(...) for each) — concurrency is
    #       bounded by the pool's internal queue (size = STOCKFISH_POOL_SIZE),
    #   (c) apply UPDATEs sequentially against the shared session (CLAUDE.md
    #       constraint: AsyncSession is not safe under asyncio.gather).
    # With pool size 1 this is equivalent to the previous serial loop. With
    # pool size N, up to N evaluations run in parallel.
    eval_pass_start = time.perf_counter()
    eval_targets: list[_EvalTarget] = []
    eval_targets.extend(_collect_midgame_eval_targets(rows_result.game_eval_data))
    eval_targets.extend(_collect_endgame_span_eval_targets(rows_result.game_eval_data))

    # Stage 4: fan out engine evaluations and apply UPDATEs sequentially.
    # The engine call site stays here in the orchestrator so the asyncio.gather
    # is colocated with the AsyncSession ownership boundary (CLAUDE.md hard rule).
    eval_calls_made = 0
    eval_calls_failed = 0
    if eval_targets:
        eval_results = await asyncio.gather(
            *(engine_service.evaluate(t.board) for t in eval_targets)
        )
        eval_calls_made, eval_calls_failed = await _apply_eval_results(
            session, eval_targets, eval_results
        )

    eval_pass_ms = (time.perf_counter() - eval_pass_start) * 1000
    logger.info(
        "import_eval_pass",
        extra={
            "games_in_batch": len(rows_result.game_eval_data),
            "eval_calls_made": eval_calls_made,
            "eval_calls_failed": eval_calls_failed,
            "eval_pass_ms": round(eval_pass_ms, 1),
        },
    )

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

    # Stage 5: bulk UPDATE move_count and result_fen via two executemany groups.
    if rows_result.move_counts:
        # Group (a): move_count for ALL games in the batch.
        move_count_stmt = (
            update(Game)
            .where(Game.id == bindparam("b_id"))
            .values(move_count=bindparam("b_mc"))
        )
        move_count_params: list[dict[str, Any]] = [
            {"b_id": gid, "b_mc": mc}
            for gid, mc in rows_result.move_counts.items()
        ]
        await session.execute(move_count_stmt, move_count_params)

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
                update(Game)
                .where(Game.id == bindparam("b_id"))
                .values(result_fen=bindparam("b_rf"))
            )
            await session.execute(fen_stmt, fen_params)

    await session.commit()
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

        # Accumulate move_count and result_fen for bulk UPDATE (D-04).
        out.move_counts[game_id] = processing_result["move_count"]
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


def _collect_midgame_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.

    At most one middlegame entry per game (later phase=1 stretches after an
    endgame are NOT re-evaluated, mirroring lichess Divider's single
    Division(midGame, endGame) return — D-79-08). Skips plies where lichess
    %eval already populated the row (T-78-17).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
        if not midgame_entries:
            continue
        mid_pd = min(midgame_entries, key=lambda p: p["ply"])
        # T-78-17 lichess preservation: skip if lichess %eval already populated the row.
        if mid_pd["eval_cp"] is not None or mid_pd["eval_mate"] is not None:
            continue
        mid_board = _board_at_ply(pgn_text, mid_pd["ply"])
        if mid_board is None:
            continue
        targets.append(
            _EvalTarget(
                game_id=g_id,
                ply=mid_pd["ply"],
                eval_kind="middlegame_entry",
                endgame_class=None,
                board=mid_board,
            )
        )
    return targets


def _collect_endgame_span_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 78 per-class endgame span entry collection.

    Each contiguous run of the same endgame_class within a game is its own
    span: a class=1 → class=2 → class=1 sequence yields two class=1 entry
    evals, not one. Spans of any length are evaluated; the repository's
    ENDGAME_PLY_THRESHOLD is intentionally not enforced here so endgame
    eval coverage stays uniform across short and long spans. Skips plies
    where lichess %eval already populated the row (T-78-17).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        # Group plies by endgame_class; only endgame plies have a non-None class.
        class_plies: dict[int, list[PlyData]] = defaultdict(list)
        for pd in plies_list:
            ec = pd["endgame_class"]
            if ec is not None:
                class_plies[ec].append(pd)

        for ec, pds in class_plies.items():
            islands = _split_into_contiguous_islands(pds)
            targets.extend(_island_eval_targets(g_id, pgn_text, ec, islands))
    return targets


def _split_into_contiguous_islands(pds: Sequence[PlyData]) -> list[list[PlyData]]:
    """Split per-class plies into contiguous runs ("islands").

    A new island starts whenever the ply gap to the previous entry is > 1
    — i.e. the class was interrupted by a non-class ply. plies_list is
    already in ply order, so pds is too; sort defensively.
    """
    pds_sorted = sorted(pds, key=lambda p: p["ply"])
    islands: list[list[PlyData]] = []
    current: list[PlyData] = []
    for pd in pds_sorted:
        if current and pd["ply"] != current[-1]["ply"] + 1:
            islands.append(current)
            current = []
        current.append(pd)
    if current:
        islands.append(current)
    return islands


def _island_eval_targets(
    g_id: int,
    pgn_text: str,
    ec: int,
    islands: Sequence[Sequence[PlyData]],
) -> list[_EvalTarget]:
    """Build _EvalTarget rows for each island's entry ply.

    Skips islands where lichess %eval already populated the entry ply
    (T-78-17) or where _board_at_ply replay fails (rare, no Sentry —
    parse error is unusual but not urgent).
    """
    targets: list[_EvalTarget] = []
    for island in islands:
        span_pd = island[0]  # entry ply = first ply of the contiguous run
        if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None:
            # Lichess %eval already populated this ply — do not overwrite (T-78-17).
            continue
        span_board = _board_at_ply(pgn_text, span_pd["ply"])
        if span_board is None:
            continue
        targets.append(
            _EvalTarget(
                game_id=g_id,
                ply=span_pd["ply"],
                eval_kind="endgame_span_entry",
                endgame_class=ec,
                board=span_board,
            )
        )
    return targets


async def _apply_eval_results(
    session: AsyncSession,
    eval_targets: Sequence[_EvalTarget],
    eval_results: Sequence[tuple[int | None, int | None]],
) -> tuple[int, int]:
    """Apply engine eval results to GamePosition rows via per-row UPDATE.

    UPDATEs run sequentially against the shared session (CLAUDE.md hard
    rule: AsyncSession is not safe under asyncio.gather). The session is
    owned by the caller and the UPDATEs land in its transaction.

    Returns (eval_calls_made, eval_calls_failed).
    """
    eval_calls_made = 0
    eval_calls_failed = 0
    for target, (eval_cp, eval_mate) in zip(eval_targets, eval_results, strict=True):
        eval_calls_made += 1
        if eval_cp is None and eval_mate is None:
            # D-11: engine error / timeout — skip row, capture to Sentry, continue import.
            eval_calls_failed += 1
            # Bounded Sentry context (D-79-04, T-78-18: no PGN/FEN/user_id).
            ctx: dict[str, Any] = {"game_id": target.game_id, "ply": target.ply}
            if target.endgame_class is not None:
                ctx["endgame_class"] = target.endgame_class
            sentry_sdk.set_context("eval", ctx)
            sentry_sdk.set_tag("source", "import")
            sentry_sdk.set_tag("eval_kind", target.eval_kind)
            sentry_sdk.capture_message("import-time engine returned None tuple", level="warning")
            continue

        # Build the WHERE clause for this eval kind. Endgame span entries
        # filter by endgame_class to disambiguate when the same ply could
        # in principle belong to multiple class spans (defensive — current
        # schema has at most one row per (game_id, ply)).
        stmt = update(GamePosition).where(
            GamePosition.game_id == target.game_id,
            GamePosition.ply == target.ply,
        )
        if target.endgame_class is not None:
            stmt = stmt.where(GamePosition.endgame_class == target.endgame_class)
        await session.execute(stmt.values(eval_cp=eval_cp, eval_mate=eval_mate))
    return eval_calls_made, eval_calls_failed
