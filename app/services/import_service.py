"""Import service: in-memory job registry and background import orchestrator.

Manages import jobs from chess.com and lichess, including:
- Job creation and state management (in-memory registry)
- Duplicate import prevention (active job detection)
- Background async orchestration via asyncio.create_task
- Incremental sync via last_synced_at from previous completed jobs
- Zobrist hash computation and bulk DB persistence
"""

import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import chess.pgn
import httpx

from app.core.database import async_session_maker
from app.repositories import game_repository, import_job_repository, user_repository
from app.services import chesscom_client, lichess_client
from app.services.zobrist import hashes_for_game

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50


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


# Module-level in-memory job registry
_jobs: dict[str, JobState] = {}


def create_job(user_id: int, platform: str, username: str) -> str:
    """Create a new import job and register it in memory.

    Args:
        user_id: Internal database user ID.
        platform: 'chess.com' or 'lichess'.
        username: Platform username to import from.

    Returns:
        The generated UUID string for the new job.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobState(
        job_id=job_id,
        user_id=user_id,
        platform=platform,
        username=username,
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
        if job.user_id == user_id
        and job.status in (JobStatus.PENDING, JobStatus.IN_PROGRESS)
    ]


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

            async with httpx.AsyncClient() as client:
                game_iter = _make_game_iterator(
                    client, job, previous_job, _on_game_fetched
                )
                batch: list[dict[str, Any]] = []

                async for game_dict in game_iter:
                    batch.append(game_dict)
                    if len(batch) >= _BATCH_SIZE:
                        imported = await _flush_batch(session, batch, job.user_id)
                        job.games_imported += imported
                        batch = []

                # Flush any remaining games
                if batch:
                    imported = await _flush_batch(session, batch, job.user_id)
                    job.games_imported += imported

            # Mark job complete in DB
            await import_job_repository.update_import_job(
                session,
                job_id=job_id,
                status="completed",
                games_fetched=job.games_fetched,
                games_imported=job.games_imported,
                last_synced_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()

            # Best-effort: auto-save platform username to user profile
            try:
                await user_repository.update_platform_username(
                    session, job.user_id, job.platform, job.username
                )
                await session.commit()
            except Exception:
                logger.warning("Failed to save platform username for job %s", job_id)

        job.status = JobStatus.COMPLETED

    except Exception as exc:
        logger.exception("Import job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error = str(exc)

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
            on_game_fetched=on_game_fetched,
        ):
            yield game

    else:
        raise ValueError(f"Unknown platform: {job.platform!r}")


async def _flush_batch(
    session: Any,
    batch: list[dict[str, Any]],
    user_id: int,
) -> int:
    """Insert a batch of game dicts, compute hashes, insert positions.

    Args:
        session: AsyncSession to use.
        batch: List of normalized game dicts from platform client.
        user_id: Denormalized user ID for position rows.

    Returns:
        Number of newly inserted games (duplicates excluded).
    """
    new_game_ids = await game_repository.bulk_insert_games(session, batch)

    if not new_game_ids:
        await session.commit()
        return 0

    # Map platform_game_id -> pgn so we can look up PGN for new games
    pgn_by_idx: dict[int, str] = {}
    for i, game_dict in enumerate(batch):
        pgn_by_idx[i] = game_dict.get("pgn", "")

    # Build a map from game row index to new game ID by matching order of returned IDs.
    # bulk_insert_games returns IDs in insertion order for newly inserted rows.
    # We need to match new_game_ids to their PGNs. Since the batch may have duplicates
    # (which are skipped), we track which games were new by building position rows.
    position_rows: list[dict[str, Any]] = []

    # We need to know which games in the batch were new. We correlate by relying on
    # the fact that bulk_insert_games returns IDs in the same order as the inserted
    # rows. We identify new games by attempting a secondary lookup approach:
    # Since we can't know which specific batch indices were inserted vs skipped,
    # we fetch the just-inserted game rows and match by game_id.
    # However, for efficiency, we use pgn from batch items. The batch items contain
    # all game dicts, and new_game_ids are the IDs of newly created rows.
    # We need to get PGNs for those IDs.
    #
    # Simpler approach: query the session for games with these IDs.
    from sqlalchemy import select
    from app.models.game import Game

    result = await session.execute(
        select(Game.id, Game.pgn).where(Game.id.in_(new_game_ids))
    )
    id_pgn_pairs = result.fetchall()

    for game_id, pgn in id_pgn_pairs:
        if not pgn:
            continue
        try:
            hash_tuples, result_fen = hashes_for_game(pgn)
        except Exception:
            logger.warning("Failed to compute hashes for game_id=%s", game_id)
            continue

        for ply, white_hash, black_hash, full_hash, move_san, clock_seconds in hash_tuples:
            position_rows.append(
                {
                    "game_id": game_id,
                    "user_id": user_id,
                    "ply": ply,
                    "white_hash": white_hash,
                    "black_hash": black_hash,
                    "full_hash": full_hash,
                    "move_san": move_san,
                    "clock_seconds": clock_seconds,
                }
            )

        # Compute and persist move_count and result_fen for this new game
        try:
            from sqlalchemy import update as sa_update
            game_obj = chess.pgn.read_game(io.StringIO(pgn))
            if game_obj is not None:
                ply_count = len(list(game_obj.mainline_moves()))
                move_count = (ply_count + 1) // 2
                await session.execute(
                    sa_update(Game).where(Game.id == game_id).values(
                        move_count=move_count,
                        result_fen=result_fen,
                    )
                )
        except Exception:
            logger.warning("Failed to compute move_count for game_id=%s", game_id)

    if position_rows:
        await game_repository.bulk_insert_positions(session, position_rows)

    await session.commit()
    return len(new_game_ids)
