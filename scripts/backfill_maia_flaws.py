"""Backfill Maia per-flaw stats (game_flaws.maia_*) for games that predate go-forward scoring.

Phase 247 (D-06, D-10, D-11, D-13, D-16). Scores every flaw of every UNSTAMPED game that has
flaws, from boards replayed out of games.pgn (never from game_flaws.fen), through the same
shared scorer the live lanes use (app/services/maia_flaw_scoring.py), and stamps each game in
the same transaction as its eight-column write.

The stamp games.maia_flaws_completed_at IS the checkpoint: a crash, a SIGTERM, or a D-09
unstamp (a reclassification that clears stamps) is caught by simply re-running. A second run
over the same scope selects zero games and writes nothing. Zero-flaw games are never selected
(the go-forward scorer stamps them), so there is no scan of all games.

Parallelism: the games are split into --workers shards by HASH RESIDUE of the game id, never by
rank windows (the table grows during a run, so rank-window shards silently double-scan and skip,
see scripts/engine_disagreement_study/seed153_scan_sample.py). Each shard is its own spawned
process with its own single-threaded ORT session (one thread measured faster per position than
the ORT default; throughput scales by processes) and a one-connection pool.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

The URL for each target comes from the DATABASE_URL_{DEV,BENCHMARK,PROD} env vars (.env),
resolved via app.core.config.db_url_for_target. It is never printed.

Usage:
    uv run python scripts/backfill_maia_flaws.py --db dev --workers 1 --user-id 28 --limit 200
    uv run python scripts/backfill_maia_flaws.py --db benchmark --workers 1 --limit 50 --dry-run
    PYTHONUNBUFFERED=1 uv run python scripts/backfill_maia_flaws.py --db prod --workers 9
    uv run python scripts/backfill_maia_flaws.py --db prod --status
    uv run python scripts/backfill_maia_flaws.py --db dev --shard 2 --num-shards 9
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import signal
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target, settings  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.services import maia_engine  # noqa: E402
from app.services.maia_flaw_scoring import (  # noqa: E402
    MAX_GAMES_PER_WRITE_TXN,
    GameMaiaScore,
    MaiaInferenceUnavailableError,
    load_game_maia_inputs,
    score_game,
    write_game_maia_scores,
)

# No magic numbers (CLAUDE.md rule).
DEFAULT_WORKERS: int = 9
# One write transaction holds one advisory lock per game; MAX_GAMES_PER_WRITE_TXN is the cap.
DEFAULT_BATCH_GAMES: int = MAX_GAMES_PER_WRITE_TXN
# One ORT thread per process measured faster per position than ORT's default (plan 01).
MAIA_THREADS_PER_PROCESS: int = 1
# A batch with a per-game write failure counts as failed; this many in a row end the shard.
MAX_CONSECUTIVE_BATCH_FAILURES: int = 5
EXIT_OK: int = 0
EXIT_MAIA_UNAVAILABLE: int = 3
EXIT_SHARD_FAILED: int = 4
DEFAULT_REPORT_DIR: Path = _REPO_ROOT / "reports" / "maia-flaws-backfill"
RUN_STAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"
MS_PER_SECOND: int = 1000

BackfillDb = Literal["dev", "benchmark", "prod"]
BACKFILL_DB_CHOICES: tuple[str, ...] = ("dev", "benchmark", "prod")
AbortReason = Literal["maia_unavailable", "too_many_batch_failures"]

# Top 8 hex digits of md5(game id) as an unsigned 32-bit integer. Unseeded and pure, so a
# game's shard is stable across processes, runs and table growth.
SHARD_RESIDUE_SQL: str = "('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint"

# Priority: most recently active users first, then their newest games (deterministic).
_SELECT_SHARD_SQL: str = f"""
SELECT g.id
FROM games g
JOIN users u ON u.id = g.user_id
WHERE g.maia_flaws_completed_at IS NULL
  AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id)
  AND {SHARD_RESIDUE_SQL} % CAST(:num_shards AS bigint) = CAST(:shard AS bigint)
  {{user_clause}}
ORDER BY u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC
{{limit_clause}}
"""

# Set by the SIGTERM/SIGINT handler; run_shard stops after the current batch.
_stop_requested: bool = False


def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


async def select_shard_game_ids(
    session: AsyncSession,
    *,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
) -> list[int]:
    """Ids of this shard's unstamped games that have flaws, in priority order.

    One snapshot at shard start; batches iterate it. Bound parameters only.
    """
    params: dict[str, Any] = {"shard": shard, "num_shards": num_shards}
    user_clause = ""
    if user_id is not None:
        user_clause = "AND g.user_id = :user_id"
        params["user_id"] = user_id
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit
    sql = _SELECT_SHARD_SQL.format(user_clause=user_clause, limit_clause=limit_clause)
    result = await session.execute(text(sql), params)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class ShardReport:
    db: str
    shard: int
    num_shards: int
    run_stamp: str
    dry_run: bool
    games_selected: int = 0
    games_scored: int = 0
    games_stamped: int = 0
    games_already_stamped: int = 0
    games_fingerprint_changed: int = 0
    games_missing: int = 0
    games_write_failed: int = 0
    games_score_failed: int = 0
    # Flaw rows that received Maia values / that were written all-NULL (reason in `reasons`).
    flaws_scored: int = 0
    flaws_null: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    aborted_reason: str | None = None
    elapsed_s: float = 0.0
    flaws_per_s: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _write_report(report: ShardReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{report.db}-{report.run_stamp}-shard{report.shard}.json"
    path.write_text(report.to_json() + "\n")
    return path


# ---------------------------------------------------------------------------
# Shard run
# ---------------------------------------------------------------------------


def _install_signal_handlers() -> None:
    """Cooperative SIGINT/SIGTERM: finish the current batch, write the report, exit."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        _log(f"signal {signum} received, stopping after this batch")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def _tally_stamped(report: ShardReport, score: GameMaiaScore) -> None:
    """Count one scored game's flaws and reasons (stamped, or would-be in a dry run)."""
    scored = sum(1 for row in score.rows if row["maia_played_prob"] is not None)
    report.flaws_scored += scored
    report.flaws_null += len(score.rows) - scored
    for reason, n in score.reasons.items():
        report.reasons[reason] = report.reasons.get(reason, 0) + n


def _score_batch(
    inputs_by_game: dict[int, Any], batch_ids: list[int], report: ShardReport
) -> list[GameMaiaScore]:
    """Score each loaded game from a PGN replay (D-06). MaiaInferenceUnavailableError aborts."""
    scores: list[GameMaiaScore] = []
    for game_id in batch_ids:
        inputs = inputs_by_game.get(game_id)
        if inputs is None:
            report.games_missing += 1
            continue
        try:
            scores.append(score_game(inputs, None))
        except MaiaInferenceUnavailableError:
            raise
        except Exception:
            # One unscorable game must not kill the shard; it stays unstamped for the next run.
            sentry_sdk.set_context("maia_flaws_backfill", {"game_id": game_id})
            sentry_sdk.capture_exception()
            report.games_score_failed += 1
    return scores


def _tally_outcomes(
    report: ShardReport, scores: list[GameMaiaScore], outcomes: dict[int, str]
) -> None:
    by_game = {s.game_id: s for s in scores}
    for game_id, outcome in outcomes.items():
        if outcome == "stamped":
            report.games_stamped += 1
            _tally_stamped(report, by_game[game_id])
        elif outcome == "already_stamped":
            report.games_already_stamped += 1
        elif outcome == "fingerprint_changed":
            report.games_fingerprint_changed += 1
        elif outcome == "game_missing":
            report.games_missing += 1


async def _write_scores(
    session_maker: async_sessionmaker[AsyncSession], scores: list[GameMaiaScore]
) -> dict[int, str]:
    async with session_maker() as session:
        outcomes = await write_game_maia_scores(session, scores, require_unstamped=True)
        await session.commit()
    return dict(outcomes)


async def _write_one_by_one(
    session_maker: async_sessionmaker[AsyncSession],
    scores: list[GameMaiaScore],
    report: ShardReport,
    shard: int,
) -> dict[int, str]:
    """Retry a failed batch game by game so one poison game cannot sink the other 49."""
    outcomes: dict[int, str] = {}
    for score in scores:
        try:
            outcomes.update(await _write_scores(session_maker, [score]))
        except Exception:
            sentry_sdk.set_context(
                "maia_flaws_backfill", {"game_id": score.game_id, "shard": shard}
            )
            sentry_sdk.capture_exception()
            report.games_write_failed += 1
    return outcomes


async def _write_batch(
    session_maker: async_sessionmaker[AsyncSession],
    scores: list[GameMaiaScore],
    report: ShardReport,
    shard: int,
) -> dict[int, str]:
    try:
        return await _write_scores(session_maker, scores)
    except Exception:
        # The failed transaction rolled back with its session; nothing of it is stamped.
        return await _write_one_by_one(session_maker, scores, report, shard)


async def _process_batch(
    session_maker: async_sessionmaker[AsyncSession],
    batch_ids: list[int],
    report: ShardReport,
    *,
    shard: int,
    dry_run: bool,
) -> None:
    async with session_maker() as read_session:
        inputs_by_game = await load_game_maia_inputs(read_session, batch_ids)
    scores = _score_batch(inputs_by_game, batch_ids, report)
    report.games_scored += len(scores)
    if dry_run:
        for score in scores:
            _tally_stamped(report, score)
        return
    if not scores:
        return
    outcomes = await _write_batch(session_maker, scores, report, shard)
    _tally_outcomes(report, scores, outcomes)


def _finish_report(report: ShardReport, started: float) -> None:
    report.elapsed_s = round(time.monotonic() - started, 2)
    report.flaws_per_s = (
        round(report.flaws_scored / report.elapsed_s, 2) if report.elapsed_s else 0.0
    )


def _progress_line(report: ShardReport, done: int, started: float) -> str:
    elapsed = max(time.monotonic() - started, 1e-9)
    return (
        f"shard {report.shard}/{report.num_shards}: {done}/{report.games_selected} games, "
        f"stamped={report.games_stamped} flaws_scored={report.flaws_scored} "
        f"({report.flaws_scored / elapsed:.1f} flaws/s)"
    )


async def _run_batches(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
    report: ShardReport,
    *,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    started: float,
) -> None:
    consecutive_failures = 0
    for start in range(0, len(game_ids), batch_games):
        if _stop_requested:
            _log(f"shard {report.shard}: stop requested, ending before batch at {start}")
            return
        write_failed_before = report.games_write_failed
        try:
            await _process_batch(
                session_maker,
                game_ids[start : start + batch_games],
                report,
                shard=report.shard,
                dry_run=dry_run,
            )
        except MaiaInferenceUnavailableError:
            report.aborted_reason = "maia_unavailable"
            return
        except Exception:
            # Read-side failure (DB unreachable): counts as a failed batch.
            sentry_sdk.set_context("maia_flaws_backfill", {"shard": report.shard})
            sentry_sdk.capture_exception()
            report.games_write_failed += batch_games
        failed = report.games_write_failed > write_failed_before
        consecutive_failures = consecutive_failures + 1 if failed else 0
        if consecutive_failures >= MAX_CONSECUTIVE_BATCH_FAILURES:
            report.aborted_reason = "too_many_batch_failures"
            return
        _log(_progress_line(report, min(start + batch_games, len(game_ids)), started))
        if throttle_ms > 0:
            await asyncio.sleep(throttle_ms / MS_PER_SECOND)


async def run_shard(
    *,
    db: BackfillDb,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    report_dir: Path,
    run_stamp: str,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> ShardReport:
    """Select, score and stamp one shard's games. Always writes the shard report."""
    engine = None
    if session_maker is None:
        engine = create_async_engine(
            db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
    report = ShardReport(
        db=db, shard=shard, num_shards=num_shards, run_stamp=run_stamp, dry_run=dry_run
    )
    started = time.monotonic()
    try:
        async with session_maker() as session:
            game_ids = await select_shard_game_ids(
                session, shard=shard, num_shards=num_shards, user_id=user_id, limit=limit
            )
        report.games_selected = len(game_ids)
        _log(f"shard {shard}/{num_shards}: {len(game_ids)} games selected (dry_run={dry_run})")
        await _run_batches(
            session_maker,
            game_ids,
            report,
            batch_games=batch_games,
            dry_run=dry_run,
            throttle_ms=throttle_ms,
            started=started,
        )
    finally:
        _finish_report(report, started)
        path = _write_report(report, report_dir)
        _log(f"shard {shard}: report written to {path}")
        if engine is not None:
            await engine.dispose()
    return report


# ---------------------------------------------------------------------------
# Process entry, CLI
# ---------------------------------------------------------------------------


async def _start_maia_and_run(**shard_kwargs: Any) -> int:
    await maia_engine.start_maia(intra_op_num_threads=MAIA_THREADS_PER_PROCESS)
    if not maia_engine.is_maia_available():
        _log("Maia is unavailable in this process (onnxruntime or model missing); nothing done")
        return EXIT_MAIA_UNAVAILABLE
    report = await run_shard(**shard_kwargs)
    if report.aborted_reason == "maia_unavailable":
        return EXIT_MAIA_UNAVAILABLE
    return EXIT_SHARD_FAILED if report.aborted_reason is not None else EXIT_OK


def _shard_process_entry(
    *,
    db: BackfillDb,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    report_dir: str,
    run_stamp: str,
) -> int:
    """One shard process: own Sentry, own single-threaded Maia session, own DB engine."""
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _install_signal_handlers()
    return asyncio.run(
        _start_maia_and_run(
            db=db,
            shard=shard,
            num_shards=num_shards,
            user_id=user_id,
            limit=limit,
            batch_games=batch_games,
            dry_run=dry_run,
            throttle_ms=throttle_ms,
            report_dir=Path(report_dir),
            run_stamp=run_stamp,
        )
    )


def _shard_process_target(**kwargs: Any) -> None:
    """mp.Process target: the child's exit code is the shard's exit code."""
    raise SystemExit(_shard_process_entry(**kwargs))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sharded, resumable Maia flaw-stats backfill (stamp = checkpoint)"
    )
    parser.add_argument(
        "--db",
        choices=list(BACKFILL_DB_CHOICES),
        required=True,
        help="DB target: dev (5432), benchmark (5433), prod (via bin/prod_db_tunnel.sh).",
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS, help="Shard processes to spawn."
    )
    parser.add_argument(
        "--num-shards",
        type=int,
        default=None,
        dest="num_shards",
        help="Total shards (default: --workers). Must equal --workers unless --shard is given.",
    )
    parser.add_argument(
        "--shard",
        type=int,
        default=None,
        help="Run exactly this one shard in-process (no spawn).",
    )
    parser.add_argument("--user-id", type=int, default=None, dest="user_id")
    parser.add_argument("--limit", type=int, default=None, help="Max games per shard.")
    parser.add_argument(
        "--batch-games",
        type=int,
        default=DEFAULT_BATCH_GAMES,
        dest="batch_games",
        help=f"Games per write transaction (max {MAX_GAMES_PER_WRITE_TXN}).",
    )
    parser.add_argument(
        "--throttle-ms", type=int, default=0, dest="throttle_ms", help="Sleep between batches."
    )
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, dest="report_dir")
    parser.add_argument(
        "--status", action="store_true", help="Print progress counts (SELECT only) and exit."
    )
    args = parser.parse_args(argv)
    if args.num_shards is None:
        args.num_shards = args.workers
    if not 1 <= args.batch_games <= MAX_GAMES_PER_WRITE_TXN:
        parser.error(f"--batch-games must be between 1 and {MAX_GAMES_PER_WRITE_TXN}")
    if args.workers < 1 or args.num_shards < 1:
        parser.error("--workers and --num-shards must be at least 1")
    if args.shard is not None and not 0 <= args.shard < args.num_shards:
        parser.error("--shard must be in [0, --num-shards)")
    if args.shard is None and args.num_shards != args.workers and not args.status:
        parser.error("--num-shards must equal --workers unless --shard is given")
    return args


async def _print_banner(db: BackfillDb) -> None:
    """Show which database this run targets, never its URL."""
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT current_database(), inet_server_addr(), inet_server_port()")
                )
            ).one()
    finally:
        await engine.dispose()
    _log(f"target: --db {db} -> database={row[0]} server={row[1]}:{row[2]}")


_STATUS_QUERIES: dict[str, str] = {
    "stamped_games": "SELECT count(*) FROM games g WHERE g.maia_flaws_completed_at IS NOT NULL{u}",
    "unstamped_games_with_flaws": (
        "SELECT count(*) FROM games g WHERE g.maia_flaws_completed_at IS NULL"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
    "flaws_with_maia": (
        "SELECT count(*) FROM game_flaws g WHERE g.maia_played_prob IS NOT NULL{u}"
    ),
    "flaws_total": "SELECT count(*) FROM game_flaws g WHERE true{u}",
}


async def fetch_status(
    session_maker: async_sessionmaker[AsyncSession], user_id: int | None
) -> dict[str, int]:
    """The four progress counts, SELECT-only, optionally for one user."""
    user_clause = " AND g.user_id = :user_id" if user_id is not None else ""
    params: dict[str, Any] = {"user_id": user_id} if user_id is not None else {}
    counts: dict[str, int] = {}
    async with session_maker() as session:
        for key, sql in _STATUS_QUERIES.items():
            result = await session.execute(text(sql.format(u=user_clause)), params)
            counts[key] = int(result.scalar_one())
    return counts


async def _print_status(db: BackfillDb, user_id: int | None) -> None:
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0)
    try:
        counts = await fetch_status(async_sessionmaker(engine, expire_on_commit=False), user_id)
    finally:
        await engine.dispose()
    print(" ".join(f"{k}={v}" for k, v in counts.items()), flush=True)


def _shard_kwargs(args: argparse.Namespace, run_stamp: str, shard: int) -> dict[str, Any]:
    return {
        "db": args.db,
        "shard": shard,
        "num_shards": args.num_shards,
        "user_id": args.user_id,
        "limit": args.limit,
        "batch_games": args.batch_games,
        "dry_run": args.dry_run,
        "throttle_ms": args.throttle_ms,
        "report_dir": str(args.report_dir),
        "run_stamp": run_stamp,
    }


def _combined_total_line(reports: list[dict[str, Any]]) -> str:
    keys = (
        "games_selected",
        "games_scored",
        "games_stamped",
        "games_already_stamped",
        "games_fingerprint_changed",
        "games_missing",
        "games_write_failed",
        "games_score_failed",
        "flaws_scored",
        "flaws_null",
    )
    totals = {k: sum(int(r.get(k, 0)) for r in reports) for k in keys}
    reasons: Counter[str] = Counter()
    for r in reports:
        reasons.update(r.get("reasons", {}))
    pairs = [f"{k}={v}" for k, v in totals.items()]
    pairs += [f"reason_{name}={n}" for name, n in sorted(reasons.items()) if n]
    return "total: " + " ".join(pairs)


def _run_spawned_shards(args: argparse.Namespace, run_stamp: str) -> int:
    ctx = mp.get_context("spawn")
    procs = [
        ctx.Process(target=_shard_process_target, kwargs=_shard_kwargs(args, run_stamp, shard))
        for shard in range(args.num_shards)
    ]
    forwarded = False

    def _on_signal(signum: int, _frame: object) -> None:
        # Forward to the children (they finish their batch and write their report) and
        # keep joining: the parent must outlive them to print the combined line.
        nonlocal forwarded
        if not forwarded:
            forwarded = True
            _log(f"signal {signum} received, asking shards to stop after their batch")
            for p in procs:
                if p.is_alive():
                    p.terminate()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    reports = _read_reports(args, run_stamp, range(args.num_shards))
    print(_combined_total_line(reports), flush=True)
    return max((p.exitcode or 0) for p in procs)


def _read_reports(
    args: argparse.Namespace, run_stamp: str, shards: Sequence[int]
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for shard in shards:
        path = args.report_dir / f"{args.db}-{run_stamp}-shard{shard}.json"
        if path.exists():
            reports.append(json.loads(path.read_text()))
        else:
            _log(f"shard {shard}: no report found at {path}")
    return reports


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    asyncio.run(_print_banner(args.db))
    if args.status:
        asyncio.run(_print_status(args.db, args.user_id))
        return EXIT_OK
    run_stamp = datetime.now(timezone.utc).strftime(RUN_STAMP_FORMAT)
    if args.shard is not None:
        code = _shard_process_entry(**_shard_kwargs(args, run_stamp, args.shard))
        reports = _read_reports(args, run_stamp, [args.shard])
        print(_combined_total_line(reports), flush=True)
        return code
    return _run_spawned_shards(args, run_stamp)


if __name__ == "__main__":
    raise SystemExit(main())
