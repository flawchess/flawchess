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
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

import chess
import chess.pgn
import httpx
import sentry_sdk
from sqlalchemy import case, select, update

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories import game_repository, import_job_repository
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
# so batch_size=28 means ~2,240 position rows per INSERT (split into 2 chunks
# of 1,700 and 540 by bulk_insert_positions). Increased from 10 to 28 for
# fewer DB commits per import (D-05). Memory: ~1.8MB per batch — safe for
# production 7.6GB + 2GB swap server.
_BATCH_SIZE = 28
IMPORT_TIMEOUT_SECONDS = 3 * 60 * 60  # 3 hours per D-24


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


async def cleanup_orphaned_jobs() -> None:
    """Mark any DB jobs stuck in pending/in_progress as failed.

    Called at startup — no in-memory tasks survive a restart, so any
    non-terminal DB jobs are orphaned.
    """
    async with async_session_maker() as session:
        count = await import_job_repository.fail_orphaned_jobs(session)
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
            async with async_session_maker() as session:
                # Determine since parameter for incremental sync (scoped to username)
                previous_job = await import_job_repository.get_latest_for_user_platform(
                    session, job.user_id, job.platform, job.username
                )

                # Create the DB record for this import job
                await import_job_repository.create_import_job(
                    session,
                    job_id=job_id,
                    user_id=job.user_id,
                    platform=job.platform,
                    username=job.username,
                )
                await session.commit()

                def _on_game_fetched() -> None:
                    job.games_fetched += 1

                async with httpx.AsyncClient(timeout=60.0) as client:
                    game_iter = _make_game_iterator(client, job, previous_job, _on_game_fetched)
                    batch: list[NormalizedGame] = []

                    async for game_dict in game_iter:
                        batch.append(game_dict)
                        if len(batch) >= _BATCH_SIZE:
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

                    # Flush any remaining games
                    if batch:
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

                # Mark job complete in DB — always advance last_synced_at so that
                # future syncs start from this point. A no-op sync (0 new games)
                # still confirms we're caught up — without this, the next sync
                # would re-fetch everything if the previous completed job had
                # last_synced_at=NULL (e.g. after a crash recovery re-sync).
                now = datetime.now(timezone.utc)
                completion_fields: dict[str, object] = {
                    "status": "completed",
                    "games_fetched": job.games_fetched,
                    "games_imported": job.games_imported,
                    "completed_at": now,
                    "last_synced_at": now,
                }

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

        try:
            async with async_session_maker() as session:
                await import_job_repository.update_import_job(
                    session,
                    job_id=job_id,
                    status="failed",
                    games_fetched=job.games_fetched,
                    games_imported=job.games_imported,
                    error_message=job.error,
                    completed_at=datetime.now(timezone.utc),
                )
                await session.commit()
        except Exception:
            logger.exception("Failed to record timeout for job %s", job_id)
            sentry_sdk.capture_exception()

    except Exception as exc:
        logger.exception("Import job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        sentry_sdk.set_context(
            "import", {"job_id": job_id, "user_id": job.user_id, "platform": job.platform}
        )
        sentry_sdk.capture_exception(exc)

        # Attempt to record failure in DB (best-effort)
        try:
            async with async_session_maker() as session:
                await import_job_repository.update_import_job(
                    session,
                    job_id=job_id,
                    status="failed",
                    games_fetched=job.games_fetched,
                    games_imported=job.games_imported,
                    error_message=str(exc),
                    completed_at=datetime.now(timezone.utc),
                )
                await session.commit()
        except Exception:
            logger.exception("Failed to record failure state for job %s", job_id)
            sentry_sdk.capture_exception()


async def _make_game_iterator(
    client: httpx.AsyncClient,
    job: JobState,
    previous_job: Any,
    on_game_fetched: Any,
):
    """Return the appropriate platform async iterator based on job.platform.

    Computes the incremental sync parameter from previous_job.last_synced_at.
    """
    if job.platform == "chess.com":
        since_timestamp = None
        if previous_job is not None and previous_job.last_synced_at is not None:
            since_timestamp = previous_job.last_synced_at

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
            since_ms = job.since_ms_override
        else:
            since_ms = None
            if previous_job is not None and previous_job.last_synced_at is not None:
                last_synced = previous_job.last_synced_at
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
    # 1. Build platform_game_id -> PGN lookup from batch (D-03: avoid SELECT Game.pgn)
    pgn_by_platform_id: dict[str, str] = {}
    for g in batch:
        if isinstance(g, NormalizedGame):
            pgn_by_platform_id[g.platform_game_id] = g.pgn
        else:
            pgn_by_platform_id[g.get("platform_game_id", "")] = g.get("pgn", "")  # type: ignore[union-attr] — dict fallback for test mocks

    # 2. Convert to dicts and bulk insert games
    game_dicts = [g.model_dump() if isinstance(g, NormalizedGame) else g for g in batch]  # type: ignore[union-attr] — dict fallback for test mocks
    new_game_ids = await game_repository.bulk_insert_games(session, game_dicts)

    if not new_game_ids:
        await session.commit()
        return 0

    # 3. Lightweight SELECT for (id, platform_game_id) only — no PGN transfer (D-03)
    result = await session.execute(
        select(Game.id, Game.platform_game_id).where(Game.id.in_(new_game_ids))
    )
    id_platform_pairs = result.fetchall()

    # 4. Process each game's PGN with unified function (D-01: single parse)
    position_rows: list[dict[str, Any]] = []
    move_counts: dict[int, int] = {}
    result_fens: dict[int, str | None] = {}
    # Phase 78 IMP-01: retain per-game data for the post-insert eval pass.
    # Each entry is (game_id, pgn_text, plies_list) — collected alongside position_rows.
    game_eval_data: list[tuple[int, str, list[PlyData]]] = []

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

        # Accumulate move_count and result_fen for bulk UPDATE (D-04)
        move_counts[game_id] = processing_result["move_count"]
        result_fens[game_id] = processing_result["result_fen"]

        # Retain plies for the eval pass — done here to avoid a second PGN parse loop.
        game_eval_data.append((game_id, pgn, list(processing_result["plies"])))

        # Build position rows from plies
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
            position_rows.append(row)

    # 5. Bulk insert positions (chunked at 1,700 rows)
    if position_rows:
        await game_repository.bulk_insert_positions(session, position_rows)

    # 5a. Phase 78 IMP-01 / Phase 79 PHASE-IMP-01: evaluate middlegame-entry and
    # per-class endgame span-entry rows where lichess %eval did NOT already
    # populate them. Runs AFTER bulk_insert_positions (rows exist in DB) and
    # BEFORE the final session.commit() so all eval UPDATEs land in the same
    # transaction.
    #
    # Two-phase to fan out engine work to the EnginePool:
    #   (a) collect all eval targets across the import batch (no engine, no DB),
    #   (b) await asyncio.gather(engine.evaluate(...) for each) — concurrency is
    #       bounded by the pool's internal queue (size = STOCKFISH_POOL_SIZE),
    #   (c) apply UPDATEs sequentially against the shared session (CLAUDE.md
    #       constraint: AsyncSession is not safe under asyncio.gather).
    # With pool size 1 this is equivalent to the previous serial loop. With
    # pool size N, up to N evaluations run in parallel.
    #
    # Each contiguous run of the same endgame_class within a game is its own
    # span: a class=1 → class=2 → class=1 sequence yields two class=1 entry
    # evals, not one. Spans of any length are evaluated; the repository's
    # ENDGAME_PLY_THRESHOLD is intentionally not enforced here so endgame
    # eval coverage stays uniform across short and long spans.
    eval_pass_start = time.perf_counter()
    eval_calls_made = 0
    eval_calls_failed = 0

    eval_targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        # Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.
        # At most one middlegame entry per game (later phase=1 stretches after an
        # endgame are NOT re-evaluated, mirroring lichess Divider's single
        # Division(midGame, endGame) return — D-79-08).
        midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
        if midgame_entries:
            mid_pd = min(midgame_entries, key=lambda p: p["ply"])
            # T-78-17 lichess preservation: skip if lichess %eval already populated the row.
            if mid_pd["eval_cp"] is None and mid_pd["eval_mate"] is None:
                mid_board = _board_at_ply(pgn_text, mid_pd["ply"])
                if mid_board is not None:
                    eval_targets.append(
                        _EvalTarget(
                            game_id=g_id,
                            ply=mid_pd["ply"],
                            eval_kind="middlegame_entry",
                            endgame_class=None,
                            board=mid_board,
                        )
                    )

        # Phase 78 per-class endgame span entry collection.
        # Group plies by endgame_class; only endgame plies have a non-None class.
        class_plies: dict[int, list[PlyData]] = defaultdict(list)
        for pd in plies_list:
            ec = pd["endgame_class"]
            if ec is not None:
                class_plies[ec].append(pd)

        for ec, pds in class_plies.items():
            # Split per-class plies into contiguous runs ("islands"). A new
            # island starts whenever the ply gap to the previous entry is > 1
            # — i.e. the class was interrupted by a non-class ply. plies_list
            # is already in ply order, so pds is too; sort defensively.
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

            for island in islands:
                span_pd = island[0]  # entry ply = first ply of the contiguous run

                if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None:
                    # Lichess %eval already populated this ply — do not overwrite (T-78-17).
                    continue

                span_board = _board_at_ply(pgn_text, span_pd["ply"])
                if span_board is None:
                    # PGN replay failed — skip row, no Sentry (parse error is unusual but not urgent).
                    continue

                eval_targets.append(
                    _EvalTarget(
                        game_id=g_id,
                        ply=span_pd["ply"],
                        eval_kind="endgame_span_entry",
                        endgame_class=ec,
                        board=span_board,
                    )
                )

    # Fan out engine evaluations across the EnginePool. The pool's internal
    # queue caps in-flight analyses at STOCKFISH_POOL_SIZE; remaining calls
    # await their slot. With pool size 1 this serializes (legacy behavior).
    if eval_targets:
        results = await asyncio.gather(*(engine_service.evaluate(t.board) for t in eval_targets))

        for target, (eval_cp, eval_mate) in zip(eval_targets, results, strict=True):
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
                sentry_sdk.capture_message(
                    "import-time engine returned None tuple", level="warning"
                )
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

    eval_pass_ms = (time.perf_counter() - eval_pass_start) * 1000
    logger.info(
        "import_eval_pass",
        extra={
            "games_in_batch": len(game_eval_data),
            "eval_calls_made": eval_calls_made,
            "eval_calls_failed": eval_calls_failed,
            "eval_pass_ms": round(eval_pass_ms, 1),
        },
    )

    # 6. Bulk UPDATE move_count and result_fen via CASE expressions (D-04)
    if move_counts:
        # Filter None result_fens — let NULL remain as default for those games
        fen_case_map = {gid: fen for gid, fen in result_fens.items() if fen is not None}
        values_dict: dict[str, Any] = {
            "move_count": case(move_counts, value=Game.id),
        }
        if fen_case_map:
            values_dict["result_fen"] = case(fen_case_map, value=Game.id, else_=None)
        await session.execute(
            update(Game).where(Game.id.in_(list(move_counts.keys()))).values(**values_dict)
        )

    await session.commit()
    return len(new_game_ids)
