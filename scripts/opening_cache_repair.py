"""Phase 220 opening eval cache repair pipeline operator surface (SEED-164, CACHEFIX-01..07).

`opening_position_eval` (the position-keyed dedup cache, 2.57M rows on prod) is
poisoned by the 2026-06-17 `DISTINCT ON` backfill and the first days of the
full-game drain — first-write-wins means a bad early value can never
self-heal. This script drives a resumable, DB-state-driven repair pipeline:

    seed -> calibrate -> screen -> orphans -> confirm -> propagate -> rederive -> report

plus `legacy-sample` (D-07), which runs after `report`, gated on `calibrate`.

Every stage refuses to run until its predecessor's `{stage}_finished_at` is
set in the `opening_cache_repair_progress` singleton row (D-05: strict
gating, never pipelined) — this is also what makes a killed run resumable:
ALL progress lives in that row and in `opening_cache_audit`'s per-position
`status` column, never in a local file or in-memory position.

The --db target is REQUIRED so this never silently runs against the wrong
database. dev=localhost:5432, benchmark=localhost:5433, prod=localhost:15432
(via bin/prod_db_tunnel.sh).

Usage:
    uv run python scripts/opening_cache_repair.py seed --db dev
    uv run python scripts/opening_cache_repair.py seed --db prod --dry-run
    uv run python scripts/opening_cache_repair.py screen --db dev --limit 100
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import asyncio
import math
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess  # noqa: E402
import sentry_sdk  # noqa: E402
from sqlalchemy import delete, func, select, text, update  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import db_url_for_target, settings  # noqa: E402

# Import every ORM model so the SQLAlchemy registry fully configures. The
# screen walk uses ORM entities (Game/GamePosition), which forces a global
# mapper-configure pass; User.oauth_accounts -> OAuthAccount must be
# registered or that pass fails. The app registers these via FastAPI-Users
# setup at startup; a bare script must do it here (resweep_holed_games.py
# precedent).
import app.models.oauth_account  # noqa: E402, F401
import app.models.user  # noqa: E402, F401
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import DEDUP_MAX_PLY, GamePosition  # noqa: E402
from app.models.opening_cache_audit import (  # noqa: E402
    OpeningCacheAudit,
    OpeningCacheRepairGame,
    OpeningCacheRepairProgress,
    OpeningCacheRepairRow,
)
from app.models.opening_position_eval import OpeningPositionEval  # noqa: E402
from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: E402
from app.services.engine import EnginePool, get_stockfish_version, read_pool_size  # noqa: E402
from app.services.eval_apply import (  # noqa: E402
    _classify_and_fill_oracle,
    _FullPlyEvalTarget,
    _collect_full_ply_targets,
    _game_write_lock_key,
    _load_game_and_positions,
)
from app.services.eval_utils import (  # noqa: E402
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.flaws_service import classify_game_flaws  # noqa: E402
from app.services.zobrist import EVAL_CP_MAX_ABS, compute_hashes  # noqa: E402

# ─── Named constants (each cites the decision or measurement it comes from) ──

# D-06: a pasted game with an odd initial_fen must not by itself condemn a
# popular position -- try up to this many distinct carrier games before
# marking a hash `hash_mismatch`.
MAX_CARRIERS_PER_HASH: int = 3

# ROADMAP cross-cutting constraint: commit at most this many audit-row writes
# per transaction, so a kill mid-run never loses more than one batch of work.
REPAIR_BATCH_ROWS: int = 500

# `screen`'s per-batch engine-game walk page size (seed diagnosis step 2).
SCREEN_GAMES_PER_BATCH: int = 200

# `calibrate`'s default sample size (seed §Thresholds).
CALIBRATION_DEFAULT_N: int = 500

# Seed diagnosis 5: rows carrying a full-eval completion at/after this date
# are "clean" (the write path agreed with a fresh evaluation 18/18 times
# measured) and are eligible as calibrate's known-clean sample.
CALIBRATION_CLEAN_AFTER: datetime = datetime(2026, 8, 20, tzinfo=timezone.utc)

# Keyset sentinel for "past the last real game.id" -- games.id is INTEGER
# (app/models/game.py), so the INTEGER max, not a BIGINT sentinel (asyncpg
# rejects a BIGINT value out of int4 range for an INTEGER-typed column).
_KEYSET_MAX_GAME_ID: int = (1 << 31) - 1  # INTEGER max

# Single-source expected-score convention (RESEARCH §Expected-Score
# Utilities): a mixed user_color convention on the two sides of a delta
# silently halves or doubles the measured floor.
_DELTA_USER_COLOR: Literal["white", "black"] = "white"

Stage = Literal[
    "seed",
    "calibrate",
    "screen",
    "orphans",
    "confirm",
    "propagate",
    "rederive",
    "report",
    "legacy_sample",
]

# Predecessor order for _stage_gate. `orphans` has no {stage}_started_at/
# finished_at columns of its own (it is a one-shot action, not a progress-
# tracked stage) -- it is a member purely so `confirm`'s predecessor lookup
# has a position to skip PAST; _stage_gate walks backward past any stage
# lacking those columns to find "the nearest tracked predecessor", so
# `orphans` itself gates on `screen_finished_at` and `confirm` still gates on
# `screen_finished_at` too (unaffected by orphans having run or not).
_STAGE_ORDER: tuple[Stage, ...] = (
    "seed",
    "calibrate",
    "screen",
    "orphans",
    "confirm",
    "propagate",
    "rederive",
    "report",
    "legacy_sample",
)


class StageOrderError(RuntimeError):
    """Raised when a stage is invoked before its nearest tracked predecessor finished."""


class CalibrationRequiredError(RuntimeError):
    """Raised when `screen` is invoked while screen_floor/confirm_floor is still NULL."""


class CalibrationSampleEmptyError(RuntimeError):
    """Raised when `calibrate` finds zero eligible known-clean rows to sample."""


# Cooperative SIGINT/SIGTERM flag (scripts/import_stress_monitor.py precedent):
# checked BETWEEN batch commits, never inside one, so a `kill -TERM` finishes
# the current batch, commits it, and exits cleanly instead of losing work.
_stop_requested: bool = False


def _install_signal_handlers() -> None:
    """Install cooperative SIGINT/SIGTERM handlers. Idempotent -- safe to call
    at the top of every batched stage runner."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        print(f"opening_cache_repair: signal {signum} received, stopping after this batch.")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


async def _ensure_progress_row(session: AsyncSession) -> OpeningCacheRepairProgress:
    """Return the singleton progress row (id=1), inserting it on first use."""
    row = await session.get(OpeningCacheRepairProgress, 1)
    if row is None:
        row = OpeningCacheRepairProgress(id=1)
        session.add(row)
        await session.flush()
    return row


async def _stage_gate(session: AsyncSession, stage: Stage) -> OpeningCacheRepairProgress:
    """Refuse to run `stage` unless its nearest tracked predecessor has finished.

    Reads `{prev}_finished_at IS NOT NULL` -- never a `>` timestamp comparison
    between two stages, so two stages finishing in the same clock tick still
    gate correctly (CACHEFIX-02 edge probe). `seed` is first in _STAGE_ORDER
    and has no predecessor, so it always passes. Returns the progress row so
    callers don't have to fetch it twice.
    """
    row = await _ensure_progress_row(session)
    idx = _STAGE_ORDER.index(stage)
    for prev in reversed(_STAGE_ORDER[:idx]):
        finished_col = f"{prev}_finished_at"
        if not hasattr(row, finished_col):
            continue  # untracked stage between `stage` and its real predecessor
        if getattr(row, finished_col) is None:
            raise StageOrderError(
                f"{stage!r} refuses to run: its predecessor {prev!r} has not finished "
                f"yet ({finished_col} IS NULL)."
            )
        break  # nearest tracked predecessor has finished; gate passes
    return row


def _clamp_smallint_cp(value: int | None) -> int | None:
    """Clamp a signed cp delta into the SMALLINT display range (delta_cp is display-only)."""
    if value is None:
        return None
    return max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, value))


def _pool_from_env(pool_size: int | None = None) -> EnginePool:
    """Build the stage's own EnginePool: `--pool-size` if given, else STOCKFISH_POOL_SIZE.

    Phase 220 dev smoke (2026-09-10): every stage used to hardcode
    ``EnginePool(1)``, so ``export STOCKFISH_POOL_SIZE=4`` on the operator box
    had no effect and ``screen`` ran a single engine (~430 rows/min on dev,
    ~4x slower than CONTEXT.md assumes for the prod run). Size it from the
    same env var the server's ``start_engine`` reads.
    """
    if pool_size is not None:
        size = max(1, pool_size)
        print(f"engine pool: {size} worker(s) (--pool-size)", flush=True)
    else:
        size = read_pool_size()
        print(f"engine pool: {size} worker(s) (STOCKFISH_POOL_SIZE)", flush=True)
    return EnginePool(size)


def _carrier_targets(
    game_id: int,
    pgn: str,
    gp_rows: Sequence[tuple[int, int, int | None, int | None]],
) -> list[_FullPlyEvalTarget]:
    """Replay a carrier game's opening plies for the hash-asserted stages.

    Same walk as the drain (`_collect_full_ply_targets`) but INCLUDING the
    terminal position of a game that ended within `DEDUP_MAX_PLY` plies, with
    that target's `full_hash` taken from its stored `game_positions` row so
    every caller keeps the single stored-vs-replayed assertion.

    Phase 220 dev smoke (2026-09-10): 94 dev cache rows (0.09%) were carried
    ONLY as the final position of a short game (resignation/timeout/abandoned
    inside 20 plies). `include_terminal=False` never yields that board, so
    `screen` skipped them, `orphans` correctly refused to delete them ("WITH a
    carrier") and they stayed `pending` forever. A game-over terminal
    (checkmate/stalemate) is still excluded by the drain helper itself.
    """
    stored_hash_by_ply = {ply: fh for ply, fh, _cp, _mate in gp_rows}
    targets: list[_FullPlyEvalTarget] = []
    for target in _collect_full_ply_targets(game_id, pgn, gp_rows, include_terminal=True):
        if target.is_terminal:
            stored = stored_hash_by_ply.get(target.ply)
            if target.ply > DEDUP_MAX_PLY or stored is None:
                continue
            target.full_hash = stored
        targets.append(target)
    return targets


def _resolve_session_maker(
    db: str, session_maker: async_sessionmaker[AsyncSession] | None
) -> tuple[async_sessionmaker[AsyncSession], AsyncEngine | None, bool]:
    """Build a session_maker from db_url_for_target(db) when none is injected.

    Never binds to the app's module-global session maker (it points at dev
    locally, so `--db prod` would silently hit dev). Prints the resolved
    target banner before any work when a real engine is constructed.

    Returns (session_maker, engine_or_None, owns_engine) -- callers dispose
    the engine themselves only when owns_engine is True.
    """
    if session_maker is not None:
        return session_maker, None, False
    engine = create_async_engine(db_url_for_target(db), pool_pre_ping=True)
    print(f"Target: {engine.url.host}:{engine.url.port}/{engine.url.database} ({db})")
    return async_sessionmaker(engine, expire_on_commit=False), engine, True


def _expected_score(cp: int | None, mate: int | None) -> float | None:
    """Position-keyed expected score, always user_color="white" on both sides of a delta
    (RESEARCH §Expected-Score Utilities) -- a mixed convention silently halves/doubles
    the measured floor. Returns None when neither cp nor mate is available."""
    if mate is not None:
        return eval_mate_to_expected_score(mate, _DELTA_USER_COLOR)
    if cp is not None:
        return eval_cp_to_expected_score(cp, _DELTA_USER_COLOR)
    return None


# ─── `seed` ──────────────────────────────────────────────────────────────────

_SEED_INSERT_SQL_ALL = text(
    "INSERT INTO opening_cache_audit "
    "(full_hash, status, old_cp, old_mate, old_best_move, old_pv) "
    "SELECT full_hash, 'pending', eval_cp, eval_mate, best_move, pv "
    "FROM opening_position_eval "
    "ON CONFLICT (full_hash) DO NOTHING"
)

_SEED_INSERT_SQL_LIMITED = text(
    "INSERT INTO opening_cache_audit "
    "(full_hash, status, old_cp, old_mate, old_best_move, old_pv) "
    "SELECT full_hash, 'pending', eval_cp, eval_mate, best_move, pv "
    "FROM opening_position_eval "
    "ORDER BY full_hash "
    "LIMIT :limit "
    "ON CONFLICT (full_hash) DO NOTHING"
)


async def run_seed(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Seed `opening_cache_audit` with one `pending` row per `opening_position_eval` row.

    Idempotent (`ON CONFLICT (full_hash) DO NOTHING`) -- a re-run inserts only
    the rows a prior run had not yet seeded. `--dry-run` runs the matching
    `SELECT count(*)` and writes nothing. `--limit 0` returns before stamping
    `seed_started_at`.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, count candidates without writing.
        limit: Cap the number of rows seeded this run, or None for all.
        session_maker: Injectable session factory for testing. When None, a
            real engine is created from db_url_for_target(db).
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("seed: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            await _stage_gate(session, "seed")

            total = (
                await session.execute(text("SELECT count(*) FROM opening_position_eval"))
            ).scalar_one()

            if dry_run:
                existing = (
                    await session.execute(text("SELECT count(*) FROM opening_cache_audit"))
                ).scalar_one()
                would_insert = max(0, total - existing)
                print(
                    f"seed: would insert {would_insert} row(s) out of {total} total "
                    "(--dry-run, nothing written)."
                )
                return

            progress = await _ensure_progress_row(session)
            progress.seed_started_at = datetime.now(timezone.utc)
            await session.flush()

            if limit is not None:
                result = await session.execute(_SEED_INSERT_SQL_LIMITED, {"limit": limit})
            else:
                result = await session.execute(_SEED_INSERT_SQL_ALL)
            inserted = result.rowcount or 0  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
            skipped = total - inserted

            progress.seed_finished_at = datetime.now(timezone.utc)
            await session.commit()
            print(f"seed: inserted {inserted} row(s), skipped {skipped} already-seeded row(s).")
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `calibrate` ─────────────────────────────────────────────────────────────


def _nearest_rank_p99(deltas: list[float]) -> float:
    """Plain nearest-rank p99 over sorted deltas -- documented here so the
    report can restate the exact rule: ceil(0.99 * n) - 1 index into the
    ascending sort, clamped to the last index for a tiny sample."""
    if not deltas:
        raise ValueError("cannot compute p99 of an empty sample")
    ordered = sorted(deltas)
    idx = min(len(ordered) - 1, max(0, math.ceil(0.99 * len(ordered)) - 1))
    return ordered[idx]


async def _load_calibration_sample(
    session: AsyncSession, n: int
) -> list[tuple[int, int, chess.Board, int | None, int | None]]:
    """Up to `n` audit rows whose cache row is carried by a known-clean game
    (`full_evals_completed_at >= CALIBRATION_CLEAN_AFTER AND lichess_evals_at
    IS NULL` -- the "analyzed by us" definition, seed diagnosis 5). Returns
    (full_hash, game_id, board, old_cp, old_mate) tuples, hash-asserted."""
    stmt = (
        select(
            OpeningCacheAudit.full_hash,
            OpeningCacheAudit.old_cp,
            OpeningCacheAudit.old_mate,
            GamePosition.game_id,
        )
        .join(GamePosition, GamePosition.full_hash == OpeningCacheAudit.full_hash)
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.ply.between(1, 20),
            Game.full_evals_completed_at.is_not(None),
            Game.full_evals_completed_at >= CALIBRATION_CLEAN_AFTER,
            Game.lichess_evals_at.is_(None),
        )
        .distinct(OpeningCacheAudit.full_hash)
        .order_by(OpeningCacheAudit.full_hash, GamePosition.game_id.asc())
        .limit(n)
    )
    rows = (await session.execute(stmt)).all()

    sample: list[tuple[int, int, chess.Board, int | None, int | None]] = []
    for full_hash, old_cp, old_mate, game_id in rows:
        game = await session.get(Game, game_id)
        if game is None:
            continue
        pos_result = await session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(GamePosition.game_id == game_id, GamePosition.ply.between(1, 20))
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]
        targets = _carrier_targets(game_id, game.pgn, gp_rows)
        target = next((t for t in targets if t.full_hash == full_hash), None)
        if target is None or compute_hashes(target.board)[2] != full_hash:
            continue  # a non-clean/mismatched carrier must never poison the floor
        sample.append((full_hash, game_id, target.board, old_cp, old_mate))
    return sample


async def _measure_calibration_deltas(
    pool: EnginePool,
    sample: list[tuple[int, int, chess.Board, int | None, int | None]],
) -> tuple[list[float], list[float]]:
    """Depth-15 and 1M-node expected-score deltas against each sample's stored
    value. No session open during this loop (Pitfall 8)."""
    depth15_deltas: list[float] = []
    full_deltas: list[float] = []
    for _full_hash, _game_id, board, old_cp, old_mate in sample:
        depth_cp, depth_mate = await pool.evaluate(board)
        full_cp, full_mate, _best_move, _pv = await pool.evaluate_nodes_with_pv(board)
        old_es = _expected_score(old_cp, old_mate)
        depth_es = _expected_score(depth_cp, depth_mate)
        full_es = _expected_score(full_cp, full_mate)
        if old_es is not None and depth_es is not None:
            depth15_deltas.append(abs(depth_es - old_es))
        if old_es is not None and full_es is not None:
            full_deltas.append(abs(full_es - old_es))
    return depth15_deltas, full_deltas


async def run_calibrate(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    n: int = CALIBRATION_DEFAULT_N,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: EnginePool | None = None,
    pool_size: int | None = None,
) -> None:
    """Measure screen_floor (p99 depth-15 delta) and confirm_floor (p99 1M-node
    delta) against a known-clean sample, and write both into the singleton
    progress row along with calibration_n/calibrated_at/engine_version.

    With zero eligible rows, both floors are left NULL and this raises
    CalibrationSampleEmptyError. `--dry-run` computes and prints the floors
    without writing them. `--limit 0` returns before stamping
    `calibrate_started_at`; `--limit N` overrides `n` (sample size cap).

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, compute and print the floors without writing them.
        limit: Overrides `n` when given (cap the sample size); 0 is a no-op.
        n: Target sample size (default CALIBRATION_DEFAULT_N).
        session_maker: Injectable session factory for testing.
        pool: Injectable EnginePool for testing.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)
    sample_size = limit if limit is not None else n

    try:
        if limit == 0:
            print("calibrate: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            await _stage_gate(session, "calibrate")
            sample = await _load_calibration_sample(session, sample_size)

        if not sample:
            raise CalibrationSampleEmptyError(
                "calibrate: zero eligible known-clean rows to sample -- both floors left NULL."
            )

        if dry_run:
            print(f"calibrate: would sample {len(sample)} row(s) (--dry-run, floors not written).")
            return

        owns_pool = pool is None
        if pool is None:
            pool = _pool_from_env(pool_size)
            await pool.start()
        try:
            depth15_deltas, full_deltas = await _measure_calibration_deltas(pool, sample)
            engine_version = await get_stockfish_version()
        finally:
            if owns_pool:
                await pool.stop()

        screen_floor = _nearest_rank_p99(depth15_deltas)
        confirm_floor = _nearest_rank_p99(full_deltas)
        now = datetime.now(timezone.utc)

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            progress.calibrate_started_at = now
            progress.screen_floor = screen_floor
            progress.confirm_floor = confirm_floor
            progress.calibration_n = len(sample)
            progress.calibrated_at = now
            progress.engine_version = engine_version
            progress.calibrate_finished_at = datetime.now(timezone.utc)
            await session.commit()
        print(
            f"calibrate: sampled {len(sample)} row(s), "
            f"screen_floor={screen_floor:.4f}, confirm_floor={confirm_floor:.4f}."
        )
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `screen` ────────────────────────────────────────────────────────────────


def _apply_screen_fields(
    audit: OpeningCacheAudit,
    *,
    eval_cp: int | None,
    eval_mate: int | None,
    sample_game_id: int,
    sample_ply: int,
    engine_version: str,
    screen_floor: float,
) -> None:
    """Set one audit row's screen result fields (pure mutation, no I/O):
    screened_clean when the delta is within screen_floor AND mate/non-mate
    agree, else flagged."""
    old_es = _expected_score(audit.old_cp, audit.old_mate)
    new_es = _expected_score(eval_cp, eval_mate)
    delta_score = abs(new_es - old_es) if old_es is not None and new_es is not None else None
    mates_agree = (audit.old_mate is None) == (eval_mate is None)
    is_clean = delta_score is not None and delta_score <= screen_floor and mates_agree

    audit.screen_cp = eval_cp
    audit.screen_mate = eval_mate
    audit.screened_at = datetime.now(timezone.utc)
    audit.sample_game_id = sample_game_id
    audit.sample_ply = sample_ply
    audit.engine_version = engine_version
    audit.delta_score = delta_score
    audit.delta_cp = _clamp_smallint_cp(
        eval_cp - audit.old_cp if eval_cp is not None and audit.old_cp is not None else None
    )
    audit.status = "screened_clean" if is_clean else "flagged"


# One screenable candidate: (full_hash, game_id, ply, board) -- hash already
# asserted against target.full_hash before being added to the list.
_ScreenCandidate = tuple[int, int, int, chess.Board]

# One batch's read-phase result: resolved candidates, plus per-hash mismatch
# attempt counts (D-06) and the most recent mismatched carrier's game_id, for
# hashes that had at least one bad carrier in this batch and were not (yet)
# resolved by a later, matching carrier in the same batch.
_ScreenReadResult = tuple[list[_ScreenCandidate], dict[int, int], dict[int, int]]


async def _collect_screen_candidates(
    session_maker: async_sessionmaker[AsyncSession], game_ids: list[int]
) -> _ScreenReadResult:
    """Read phase for one batch of games: load each game's pgn + ply-1..20 rows
    once, keep the targets whose full_hash still has a `pending` audit row.
    D-06: a mismatched replay does not condemn the hash on the spot -- it is
    recorded as an attempt (count + last-tried game_id) so the caller can
    increment `hash_mismatch_attempts` and let a LATER carrier (same batch or
    a future one) still resolve it; only once a hash resolves successfully is
    it excluded from further attempts in this batch (`seen_hashes`). No engine
    call happens in this function; the caller gathers with the session
    already closed (Pitfall 8).
    """
    candidates: list[_ScreenCandidate] = []
    mismatch_attempts: dict[int, int] = {}
    mismatch_last_game_id: dict[int, int] = {}
    seen_hashes: set[int] = set()
    async with session_maker() as session:
        pending_hashes = set(
            (
                await session.execute(
                    select(OpeningCacheAudit.full_hash).where(OpeningCacheAudit.status == "pending")
                )
            )
            .scalars()
            .all()
        )
        if not pending_hashes:
            return [], {}, {}
        for game_id in game_ids:
            game = await session.get(Game, game_id)
            if game is None:
                continue
            pos_result = await session.execute(
                select(
                    GamePosition.ply,
                    GamePosition.full_hash,
                    GamePosition.eval_cp,
                    GamePosition.eval_mate,
                ).where(GamePosition.game_id == game_id, GamePosition.ply.between(1, 20))
            )
            gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]
            if not gp_rows:
                continue
            targets = _carrier_targets(game_id, game.pgn, gp_rows)
            for target in targets:
                if target.full_hash not in pending_hashes or target.full_hash in seen_hashes:
                    continue
                if compute_hashes(target.board)[2] != target.full_hash:
                    mismatch_attempts[target.full_hash] = (
                        mismatch_attempts.get(target.full_hash, 0) + 1
                    )
                    mismatch_last_game_id[target.full_hash] = game_id
                    continue
                seen_hashes.add(target.full_hash)
                candidates.append((target.full_hash, game_id, target.ply, target.board))
    return candidates, mismatch_attempts, mismatch_last_game_id


def _apply_mismatch_attempts(
    audit: OpeningCacheAudit, *, attempts: int, attempted_game_id: int
) -> None:
    """Record `attempts` more failed carrier replays for one audit row (D-06):
    the hash-mismatch attempt budget lives in a column so it survives a kill.
    Transitions to `hash_mismatch` only once the running total reaches
    MAX_CARRIERS_PER_HASH; the row's cache entry (opening_position_eval) is
    never touched by a mismatch."""
    audit.hash_mismatch_attempts += attempts
    audit.sample_game_id = attempted_game_id
    if audit.hash_mismatch_attempts >= MAX_CARRIERS_PER_HASH:
        audit.status = "hash_mismatch"


async def _run_screen_batch(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
    *,
    pool: EnginePool,
    screen_floor: float,
    engine_version: str,
) -> int:
    """Process one page of the id-ASC game walk: gather every pending-hash
    candidate's depth-15 eval with no session open, then write every result
    (including hash-mismatch attempt counters) AND advance
    `last_game_id_walked` in the SAME write transaction -- an exception raised
    during the gather (a kill, a CancelledError) means this function never
    reaches the write session, so the batch's audit rows keep their prior
    status and the cursor stays unchanged (resumable). Returns the number of
    hashes screened (evaluated) this batch.
    """
    candidates, mismatch_attempts, mismatch_last_game_id = await _collect_screen_candidates(
        session_maker, game_ids
    )
    resolved_hashes = {c[0] for c in candidates}

    eval_results = (
        await asyncio.gather(*(pool.evaluate(c[3]) for c in candidates)) if candidates else []
    )

    async with session_maker() as write_session:
        for (full_hash, sample_game_id, sample_ply, _board), (eval_cp, eval_mate) in zip(
            candidates, eval_results, strict=True
        ):
            audit = await write_session.get(OpeningCacheAudit, full_hash)
            if audit is None:
                continue  # cache row's audit entry vanished between read and write
            _apply_screen_fields(
                audit,
                eval_cp=eval_cp,
                eval_mate=eval_mate,
                sample_game_id=sample_game_id,
                sample_ply=sample_ply,
                engine_version=engine_version,
                screen_floor=screen_floor,
            )
        for full_hash, attempts in mismatch_attempts.items():
            if full_hash in resolved_hashes:
                continue  # a later carrier in this same batch resolved it -- not a mismatch
            audit = await write_session.get(OpeningCacheAudit, full_hash)
            if audit is None:
                continue
            _apply_mismatch_attempts(
                audit, attempts=attempts, attempted_game_id=mismatch_last_game_id[full_hash]
            )
        progress = await _ensure_progress_row(write_session)
        progress.last_game_id_walked = game_ids[-1]
        await write_session.commit()
    return len(candidates)


async def _walk_screen(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    cursor: int,
    limit: int | None,
    pool: EnginePool,
    screen_floor: float,
    engine_version: str,
) -> tuple[int, int]:
    """Page through games.id ASC from `cursor`, processing one batch per page
    until the walk exhausts, `limit` units have been processed, or a signal
    arrives. Stamps `screen_finished_at` ONLY on true exhaustion (never on a
    --limit truncation or a signal) -- that is the only condition under which
    the NEXT stage's gate should open. Returns (processed_total, final_cursor).
    """
    processed_total = 0
    while not _stop_requested:
        if limit is not None and processed_total >= limit:
            break
        async with session_maker() as session:
            game_ids = (
                (
                    await session.execute(
                        select(Game.id)
                        .where(Game.id > cursor)
                        .order_by(Game.id.asc())
                        .limit(SCREEN_GAMES_PER_BATCH)
                    )
                )
                .scalars()
                .all()
            )
        if not game_ids:
            async with session_maker() as fin_session:
                fin_progress = await _ensure_progress_row(fin_session)
                fin_progress.screen_finished_at = datetime.now(timezone.utc)
                await fin_session.commit()
            break
        batch_count = await _run_screen_batch(
            session_maker,
            list(game_ids),
            pool=pool,
            screen_floor=screen_floor,
            engine_version=engine_version,
        )
        processed_total += batch_count
        cursor = game_ids[-1]
    return processed_total, cursor


async def run_screen(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: EnginePool | None = None,
    pool_size: int | None = None,
) -> None:
    """Walk carrier games by `games.id` ASC from the resumable
    `last_game_id_walked` cursor, depth-15 screening every `pending` audit row
    whose carrier board's replayed hash matches (D-06's carrier-retry counter
    and the `hash_mismatch` transition arrive in a later task of this same
    plan). Refuses to start while `screen_floor`/`confirm_floor` is NULL.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, report how many rows are still pending and write
            nothing.
        limit: Cap the number of hashes screened this run, or None for all
            (walks until the game table is exhausted or a signal arrives).
        session_maker: Injectable session factory for testing.
        pool: Injectable EnginePool for testing. When None, a real pool of
            size 1 is started and stopped by this function.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("screen: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            progress = await _stage_gate(session, "screen")
            screen_floor = progress.screen_floor
            confirm_floor = progress.confirm_floor
            cursor = progress.last_game_id_walked

        if screen_floor is None or confirm_floor is None:
            raise CalibrationRequiredError(
                "screen refuses to run: screen_floor/confirm_floor is NULL (run calibrate first)."
            )

        if not dry_run:
            async with session_maker() as session:
                progress = await _ensure_progress_row(session)
                if progress.screen_started_at is None:
                    progress.screen_started_at = datetime.now(timezone.utc)
                    await session.commit()

        if dry_run:
            async with session_maker() as session:
                pending_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheAudit)
                        .where(OpeningCacheAudit.status == "pending")
                    )
                ).scalar_one()
            print(f"screen: {pending_count} pending row(s) remain (--dry-run, nothing written).")
            return

        owns_pool = pool is None
        if pool is None:
            pool = _pool_from_env(pool_size)
            await pool.start()
        try:
            engine_version = await get_stockfish_version()
            _install_signal_handlers()
            processed_total, cursor = await _walk_screen(
                session_maker,
                cursor=cursor,
                limit=limit,
                pool=pool,
                screen_floor=screen_floor,
                engine_version=engine_version,
            )
            print(f"screen: processed {processed_total} row(s); cursor at game_id {cursor}.")
        finally:
            if owns_pool:
                await pool.stop()
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `orphans` ───────────────────────────────────────────────────────────────

# Pitfall 6 report sample size: enough to eyeball the shape of what got
# deleted without dumping the whole orphan set to stdout.
_ORPHAN_SAMPLE_SIZE: int = 20


async def run_orphans(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Mark still-`pending` audit rows with NO `game_positions` carrier at ply
    1..20 in ANY game as `orphan`, and delete their `opening_position_eval`
    cache rows -- but only when `--dry-run` is absent. A separate, explicit,
    dry-runnable stage (Pitfall 6 refinement), NOT an implicit tail of
    `screen`: a `pending` row that DOES have a carrier is left untouched and
    reported separately as "unscreened with a carrier" (the walk was cut
    short -- a `--limit`, a PGN parse failure, or a kill -- not an orphan).
    Carrier existence is checked across ALL games, including lichess games,
    whose boards are legitimate even though their evals are never read
    (Pitfall 6).

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, report the counts and a sample without deleting
            anything.
        limit: Cap the number of pending rows considered this run, or None.
        session_maker: Injectable session factory for testing.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("orphans: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            await _stage_gate(session, "orphans")

            pending_hashes = (
                (
                    await session.execute(
                        select(OpeningCacheAudit.full_hash)
                        .where(OpeningCacheAudit.status == "pending")
                        .order_by(OpeningCacheAudit.full_hash)
                    )
                )
                .scalars()
                .all()
            )
            if limit is not None:
                pending_hashes = pending_hashes[:limit]
            if not pending_hashes:
                print("orphans: no pending row(s) to consider.")
                return

            carrier_hashes = set(
                (
                    await session.execute(
                        select(GamePosition.full_hash)
                        .where(
                            GamePosition.full_hash.in_(pending_hashes),
                            GamePosition.ply.between(1, 20),
                        )
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
            orphan_hashes = [h for h in pending_hashes if h not in carrier_hashes]
            unscreened_with_carrier = len(pending_hashes) - len(orphan_hashes)
            print(
                f"orphans: {len(orphan_hashes)} orphan row(s) (no carrier anywhere), "
                f"{unscreened_with_carrier} still-pending row(s) WITH a carrier "
                "(walk cut short -- not an orphan)."
            )

            if orphan_hashes:
                sample = orphan_hashes[:_ORPHAN_SAMPLE_SIZE]
                sample_rows = (
                    await session.execute(
                        select(OpeningCacheAudit.full_hash, OpeningCacheAudit.old_cp).where(
                            OpeningCacheAudit.full_hash.in_(sample)
                        )
                    )
                ).all()
                for full_hash, old_cp in sample_rows:
                    print(f"  orphan full_hash={full_hash} old_cp={old_cp}")

            if dry_run or not orphan_hashes:
                print("orphans: --dry-run, nothing deleted." if dry_run else "orphans: done.")
                return

            await session.execute(
                update(OpeningCacheAudit)
                .where(OpeningCacheAudit.full_hash.in_(orphan_hashes))
                .values(status="orphan")
            )
            await session.execute(
                delete(OpeningPositionEval).where(OpeningPositionEval.full_hash.in_(orphan_hashes))
            )
            await session.commit()
            print(f"orphans: deleted {len(orphan_hashes)} orphaned cache row(s).")
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `confirm` (CACHEFIX-04) ─────────────────────────────────────────────────

# One confirm candidate: (full_hash, board) -- hash already re-asserted before
# being added to the list (a game's PGN could have changed since screen ran).
_ConfirmCandidate = tuple[int, chess.Board]


async def _collect_confirm_candidates(
    session_maker: async_sessionmaker[AsyncSession], batch_size: int
) -> tuple[list[_ConfirmCandidate], list[int]]:
    """Read phase for one confirm batch: load up to `batch_size` `flagged` audit
    rows in `full_hash` ASC order, rebuild each carrier board from its recorded
    `sample_game_id`/`sample_ply` (the same helper `screen` uses), and re-assert
    the Zobrist hash -- the assertion runs again here because a game's PGN could
    have changed between stages, and no eval may ever be written for an
    unasserted board. Returns (candidates, hash_mismatch_hashes): a row whose
    re-assertion fails is reported separately so the caller can transition it to
    `hash_mismatch` without ever sending it to the engine. No engine call
    happens in this function; the caller gathers with the session already
    closed (Pitfall 8).
    """
    candidates: list[_ConfirmCandidate] = []
    hash_mismatches: list[int] = []
    async with session_maker() as session:
        rows = (
            (
                await session.execute(
                    select(OpeningCacheAudit)
                    .where(OpeningCacheAudit.status == "flagged")
                    .order_by(OpeningCacheAudit.full_hash)
                    .limit(batch_size)
                )
            )
            .scalars()
            .all()
        )
        for audit in rows:
            if audit.sample_game_id is None or audit.sample_ply is None:
                hash_mismatches.append(audit.full_hash)
                continue
            game = await session.get(Game, audit.sample_game_id)
            if game is None:
                hash_mismatches.append(audit.full_hash)
                continue
            pos_result = await session.execute(
                select(
                    GamePosition.ply,
                    GamePosition.full_hash,
                    GamePosition.eval_cp,
                    GamePosition.eval_mate,
                ).where(GamePosition.game_id == game.id, GamePosition.ply.between(1, 20))
            )
            gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]
            targets = _carrier_targets(game.id, game.pgn, gp_rows)
            target = next((t for t in targets if t.ply == audit.sample_ply), None)
            if target is None or compute_hashes(target.board)[2] != audit.full_hash:
                hash_mismatches.append(audit.full_hash)
                continue
            candidates.append((audit.full_hash, target.board))
    return candidates, hash_mismatches


def _apply_confirm_fields(
    audit: OpeningCacheAudit,
    *,
    full_cp: int | None,
    full_mate: int | None,
    full_best_move: str | None,
    full_pv: str | None,
    confirm_floor: float,
) -> bool:
    """Set one audit row's confirm result fields (pure mutation, no I/O).
    Returns True iff the row is `confirmed_bad` -- the caller uses this to
    decide whether to overwrite the cache row. `confirmed_bad` when the delta
    exceeds `confirm_floor` OR the mate/non-mate status differs from the old
    cached value, whatever the delta (CACHEFIX-04); otherwise `confirmed_clean`
    and the cache row stays byte-identical."""
    old_es = _expected_score(audit.old_cp, audit.old_mate)
    new_es = _expected_score(full_cp, full_mate)
    delta_score = abs(new_es - old_es) if old_es is not None and new_es is not None else None
    mates_agree = (audit.old_mate is None) == (full_mate is None)
    is_bad = delta_score is None or delta_score > confirm_floor or not mates_agree

    audit.full_cp = full_cp
    audit.full_mate = full_mate
    audit.full_best_move = full_best_move
    audit.full_pv = full_pv
    audit.confirmed_at = datetime.now(timezone.utc)
    audit.delta_score = delta_score
    audit.delta_cp = _clamp_smallint_cp(
        full_cp - audit.old_cp if full_cp is not None and audit.old_cp is not None else None
    )
    audit.status = "confirmed_bad" if is_bad else "confirmed_clean"
    return is_bad


_CONFIRM_CACHE_OVERWRITE_SQL = text(
    "UPDATE opening_position_eval SET"
    " eval_cp = CAST(:cp AS smallint),"
    " eval_mate = CAST(:mate AS smallint),"
    " best_move = CAST(:bm AS varchar),"
    " pv = CAST(:pv AS text)"
    " WHERE full_hash = CAST(:h AS bigint)"
)


async def _run_confirm_batch(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    pool: EnginePool,
    confirm_floor: float,
) -> int:
    """Process one page of `flagged` audit rows: gather every candidate's
    1M-node re-evaluation with no session open, then write every result
    (status transition + cache overwrite for `confirmed_bad` rows, and
    `hash_mismatch` for rows whose carrier no longer replays) in the SAME
    write transaction -- an exception during the gather never reaches the
    write session, so the batch's rows keep their prior `flagged` status and
    a re-run re-selects exactly the same still-`flagged` rows (resumable).
    Returns the number of rows processed (evaluated + hash-mismatched) this
    batch, or 0 when there is nothing left to confirm (the walk's exhaustion
    signal).
    """
    candidates, hash_mismatches = await _collect_confirm_candidates(
        session_maker, REPAIR_BATCH_ROWS
    )
    if not candidates and not hash_mismatches:
        return 0

    eval_results = (
        await asyncio.gather(*(pool.evaluate_nodes_with_pv(board) for _fh, board in candidates))
        if candidates
        else []
    )

    async with session_maker() as write_session:
        for (full_hash, _board), (full_cp, full_mate, full_bm, full_pv) in zip(
            candidates, eval_results, strict=True
        ):
            audit = await write_session.get(OpeningCacheAudit, full_hash)
            if audit is None:
                continue  # cache row's audit entry vanished between read and write
            is_bad = _apply_confirm_fields(
                audit,
                full_cp=full_cp,
                full_mate=full_mate,
                full_best_move=full_bm,
                full_pv=full_pv,
                confirm_floor=confirm_floor,
            )
            if is_bad:
                # CACHEFIX-04: only the confirmed_bad branch writes -- the old
                # values already live in the audit row's old_* snapshot.
                await write_session.execute(
                    _CONFIRM_CACHE_OVERWRITE_SQL,
                    {
                        "cp": full_cp,
                        "mate": full_mate,
                        "bm": full_bm,
                        "pv": full_pv,
                        "h": full_hash,
                    },
                )
        for full_hash in hash_mismatches:
            audit = await write_session.get(OpeningCacheAudit, full_hash)
            if audit is not None:
                audit.status = "hash_mismatch"
        await write_session.commit()
    return len(candidates) + len(hash_mismatches)


async def _walk_confirm(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    limit: int | None,
    pool: EnginePool,
    confirm_floor: float,
) -> int:
    """Page through `flagged` audit rows until none remain, `limit` units have
    been processed, or a signal arrives. Stamps `confirm_finished_at` ONLY on
    true exhaustion (mirrors `_walk_screen`'s exhaustion rule) -- never on a
    `--limit` truncation or a signal. Returns the total rows processed."""
    processed_total = 0
    while not _stop_requested:
        if limit is not None and processed_total >= limit:
            break
        batch_count = await _run_confirm_batch(
            session_maker, pool=pool, confirm_floor=confirm_floor
        )
        if batch_count == 0:
            async with session_maker() as fin_session:
                fin_progress = await _ensure_progress_row(fin_session)
                fin_progress.confirm_finished_at = datetime.now(timezone.utc)
                await fin_session.commit()
            break
        processed_total += batch_count
    return processed_total


async def run_confirm(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: EnginePool | None = None,
    pool_size: int | None = None,
) -> None:
    """Re-evaluate every `flagged` audit row at the drain's own 1M-node budget
    (`evaluate_nodes_with_pv`), overwriting the cache row only when the delta
    exceeds `confirm_floor` or the mate/non-mate status differs (CACHEFIX-04).
    Gated (via `_stage_gate`) on `screen`/`orphans` having finished and on a
    non-NULL `confirm_floor`.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, report how many rows are still flagged and write
            nothing.
        limit: Cap the number of rows confirmed this run, or None for all.
        session_maker: Injectable session factory for testing.
        pool: Injectable EnginePool for testing. When None, a real pool of
            size 1 is started and stopped by this function.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("confirm: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            progress = await _stage_gate(session, "confirm")
            confirm_floor = progress.confirm_floor

        if confirm_floor is None:
            raise CalibrationRequiredError(
                "confirm refuses to run: confirm_floor is NULL (run calibrate first)."
            )

        if dry_run:
            async with session_maker() as session:
                flagged_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheAudit)
                        .where(OpeningCacheAudit.status == "flagged")
                    )
                ).scalar_one()
            print(f"confirm: {flagged_count} flagged row(s) remain (--dry-run, nothing written).")
            return

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            if progress.confirm_started_at is None:
                progress.confirm_started_at = datetime.now(timezone.utc)
                await session.commit()

        owns_pool = pool is None
        if pool is None:
            pool = _pool_from_env(pool_size)
            await pool.start()
        try:
            _install_signal_handlers()
            processed_total = await _walk_confirm(
                session_maker, limit=limit, pool=pool, confirm_floor=confirm_floor
            )
            print(f"confirm: processed {processed_total} row(s).")
        finally:
            if owns_pool:
                await pool.stop()
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `propagate` (CACHEFIX-05) ───────────────────────────────────────────────

# CACHEFIX-05: the eval rewrite lands on the CARRIER row (p.ply = n.ply - 1,
# the post-move shift); best_move/pv rewrites land on row `n` itself and are
# handled by separate statements below (Pitfall 5: best_move is NOT shifted,
# pv is written only at flaw-adjacent plies). Every bind uses CAST(x AS t),
# never `x::t` -- asyncpg cannot infer the parameter type of a NULL bind on an
# `IS NOT DISTINCT FROM` comparison otherwise (Pitfall 1).
_PROPAGATE_EVAL_SQL = text(
    "UPDATE game_positions p"
    " SET eval_cp = CAST(:new_cp AS smallint), eval_mate = CAST(:new_mate AS smallint)"
    " FROM game_positions n"
    " WHERE n.full_hash = CAST(:full_hash AS bigint)"
    "   AND n.ply BETWEEN 1 AND 20"
    "   AND p.game_id = n.game_id"
    "   AND p.user_id = n.user_id"
    "   AND p.ply = n.ply - 1"
    "   AND p.eval_cp IS NOT DISTINCT FROM CAST(:old_cp AS smallint)"
    "   AND p.eval_mate IS NOT DISTINCT FROM CAST(:old_mate AS smallint)"
    " RETURNING p.game_id, p.user_id, p.ply, n.ply AS hash_ply"
)

_PROPAGATE_BEST_MOVE_SQL = text(
    "UPDATE game_positions n"
    " SET best_move = CAST(:new_bm AS varchar)"
    " WHERE n.full_hash = CAST(:full_hash AS bigint)"
    "   AND n.ply BETWEEN 1 AND 20"
    "   AND n.best_move IS NOT DISTINCT FROM CAST(:old_bm AS varchar)"
    " RETURNING n.game_id, n.user_id, n.ply"
)

_PROPAGATE_PV_SQL = text(
    "UPDATE game_positions n"
    " SET pv = CAST(:new_pv AS text)"
    " WHERE n.full_hash = CAST(:full_hash AS bigint)"
    "   AND n.ply BETWEEN 1 AND 20"
    "   AND n.pv IS NOT DISTINCT FROM CAST(:old_pv AS text)"
    " RETURNING n.game_id, n.user_id, n.ply"
)

_REPAIR_GAME_UPSERT_SQL = text(
    "INSERT INTO opening_cache_repair_games (game_id, user_id, status, rows_repaired)"
    " VALUES (CAST(:game_id AS bigint), CAST(:user_id AS integer), 'pending', CAST(:rows AS integer))"
    " ON CONFLICT (game_id) DO UPDATE SET"
    " status = 'pending',"
    " rows_repaired = opening_cache_repair_games.rows_repaired + EXCLUDED.rows_repaired"
)


async def _propagate_one_hash(session: AsyncSession, audit: OpeningCacheAudit) -> None:
    """Propagate one `confirmed_bad` audit row's new value into every carrier
    `game_positions` row that still holds the OLD cached value, on the correct
    side of the post-move shift (CACHEFIX-05). Runs three statements against
    THIS hash only: the eval rewrite (carrier row p, RETURNING drives the
    per-cell repair-row trail), and independent best_move/pv rewrites against
    row `n` itself (each gated on its OWN old-value match -- Pitfall 5: a row
    can have its best_move transplanted without its pv, or vice versa). Writes
    one `opening_cache_repair_rows` per rewritten eval-cell (best_move_replaced/
    pv_replaced tell whether the SAME hash's row-`n` companion also matched),
    upserts `opening_cache_repair_games` `pending` for every game touched by
    ANY of the three statements, and always stamps `repaired_at` -- even when
    zero rows matched (idempotent: a hash whose carriers were already
    rewritten, or that never had one, still gets step 5).
    """
    params = {
        "full_hash": audit.full_hash,
        "new_cp": audit.full_cp,
        "new_mate": audit.full_mate,
        "old_cp": audit.old_cp,
        "old_mate": audit.old_mate,
        "new_bm": audit.full_best_move,
        "old_bm": audit.old_best_move,
        "new_pv": audit.full_pv,
        "old_pv": audit.old_pv,
    }
    eval_rows = (await session.execute(_PROPAGATE_EVAL_SQL, params)).all()
    bm_rows = (await session.execute(_PROPAGATE_BEST_MOVE_SQL, params)).all()
    pv_rows = (await session.execute(_PROPAGATE_PV_SQL, params)).all()

    bm_touched = {(r.game_id, r.ply) for r in bm_rows}
    pv_touched = {(r.game_id, r.ply) for r in pv_rows}

    repair_rows: list[dict[str, Any]] = []
    games_touched: dict[int, int] = {}  # game_id -> user_id
    for row in eval_rows:
        repair_rows.append(
            {
                "game_id": row.game_id,
                "ply": row.ply,
                "full_hash": audit.full_hash,
                "old_cp": audit.old_cp,
                "old_mate": audit.old_mate,
                "new_cp": audit.full_cp,
                "new_mate": audit.full_mate,
                "best_move_replaced": (row.game_id, row.hash_ply) in bm_touched,
                "pv_replaced": (row.game_id, row.hash_ply) in pv_touched,
            }
        )
        games_touched[row.game_id] = row.user_id
    for row in bm_rows:
        games_touched.setdefault(row.game_id, row.user_id)
    for row in pv_rows:
        games_touched.setdefault(row.game_id, row.user_id)

    if repair_rows:
        values_parts: list[str] = []
        insert_params: dict[str, Any] = {}
        for i, r in enumerate(repair_rows):
            insert_params[f"gid_{i}"] = r["game_id"]
            insert_params[f"ply_{i}"] = r["ply"]
            insert_params[f"fh_{i}"] = r["full_hash"]
            insert_params[f"ocp_{i}"] = r["old_cp"]
            insert_params[f"omt_{i}"] = r["old_mate"]
            insert_params[f"ncp_{i}"] = r["new_cp"]
            insert_params[f"nmt_{i}"] = r["new_mate"]
            insert_params[f"bmr_{i}"] = r["best_move_replaced"]
            insert_params[f"pvr_{i}"] = r["pv_replaced"]
            values_parts.append(
                f"(CAST(:gid_{i} AS bigint), CAST(:ply_{i} AS smallint),"
                f" CAST(:fh_{i} AS bigint), CAST(:ocp_{i} AS smallint),"
                f" CAST(:omt_{i} AS smallint), CAST(:ncp_{i} AS smallint),"
                f" CAST(:nmt_{i} AS smallint), CAST(:bmr_{i} AS boolean),"
                f" CAST(:pvr_{i} AS boolean))"
            )
        values_sql = ", ".join(values_parts)
        await session.execute(
            text(
                "INSERT INTO opening_cache_repair_rows"
                " (game_id, ply, full_hash, old_cp, old_mate, new_cp, new_mate,"
                "  best_move_replaced, pv_replaced)"
                f" VALUES {values_sql}"
                " ON CONFLICT (game_id, ply) DO NOTHING"
            ),
            insert_params,
        )

    for game_id, user_id in games_touched.items():
        rows_for_game = sum(1 for r in repair_rows if r["game_id"] == game_id)
        await session.execute(
            _REPAIR_GAME_UPSERT_SQL,
            {"game_id": game_id, "user_id": user_id, "rows": rows_for_game},
        )

    # Phase 220 dev smoke (2026-09-10): the status transition `confirmed_bad ->
    # repaired` (model docstring, plan 01 truth "pending -> flagged -> confirmed_bad
    # -> repaired") was never written -- only `repaired_at` was stamped. Release 2's
    # migration (CACHEFIX-08) trusts `screened_clean`/`confirmed_clean`/`repaired`
    # only, so every repaired prod row would have become an untrusted candidate.
    audit.status = "repaired"
    audit.repaired_at = datetime.now(timezone.utc)


async def _run_propagate_batch(
    session_maker: async_sessionmaker[AsyncSession], batch_size: int
) -> int:
    """Process one page of `confirmed_bad`, unpropagated audit rows: propagate
    each hash's new value in the SAME transaction as the batch commit (no
    engine calls in this stage, so no read/gather/write split is needed).
    Returns the number of hashes processed this batch, or 0 when none remain."""
    async with session_maker() as session:
        audits = (
            (
                await session.execute(
                    select(OpeningCacheAudit)
                    .where(
                        OpeningCacheAudit.status == "confirmed_bad",
                        OpeningCacheAudit.repaired_at.is_(None),
                    )
                    .order_by(OpeningCacheAudit.full_hash)
                    .limit(batch_size)
                )
            )
            .scalars()
            .all()
        )
        if not audits:
            return 0
        for audit in audits:
            await _propagate_one_hash(session, audit)
        await session.commit()
    return len(audits)


async def run_propagate(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Rewrite every carrier `game_positions` row that still holds a
    `confirmed_bad` audit row's OLD cached value with the new one, on the
    correct side of the post-move shift, and record one `opening_cache_repair_
    rows` row per rewritten eval-cell (CACHEFIX-05). Gated on `confirm_
    finished_at`.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, report how many rows remain unpropagated and write
            nothing.
        limit: Cap the number of hashes propagated this run, or None for all.
        session_maker: Injectable session factory for testing.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("propagate: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            await _stage_gate(session, "propagate")

        if dry_run:
            async with session_maker() as session:
                count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheAudit)
                        .where(
                            OpeningCacheAudit.status == "confirmed_bad",
                            OpeningCacheAudit.repaired_at.is_(None),
                        )
                    )
                ).scalar_one()
            print(
                f"propagate: {count} confirmed_bad row(s) remain unpropagated "
                "(--dry-run, nothing written)."
            )
            return

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            if progress.propagate_started_at is None:
                progress.propagate_started_at = datetime.now(timezone.utc)
                await session.commit()

        _install_signal_handlers()
        processed_total = 0
        while not _stop_requested:
            if limit is not None and processed_total >= limit:
                break
            batch_count = await _run_propagate_batch(session_maker, REPAIR_BATCH_ROWS)
            if batch_count == 0:
                async with session_maker() as fin_session:
                    fin_progress = await _ensure_progress_row(fin_session)
                    fin_progress.propagate_finished_at = datetime.now(timezone.utc)
                    await fin_session.commit()
                break
            processed_total += batch_count
        print(f"propagate: processed {processed_total} row(s).")
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `rederive` (CACHEFIX-06) ────────────────────────────────────────────────


async def _snapshot_rederive_state(
    session: AsyncSession, game_id: int, user_id: int
) -> dict[str, Any]:
    """One (user_id, game_id)'s `game_flaws` ply set + counts grouped by
    severity, plus the four accuracy/ACPL columns from `games` -- used for
    both the before- and after-rederive snapshot (the diff/upsert commits
    between the two calls). `game_flaws.severity` only ever stores mistake(1)/
    blunder(2) rows (inaccuracies are never materialized -- D-03 in
    game_flaws_repository.py), so the inaccuracy counter is always 0 here;
    this mirrors the plan's literal snapshot source, not a bug.
    """
    rows = (
        await session.execute(
            select(GameFlaw.ply, GameFlaw.severity).where(
                GameFlaw.user_id == user_id, GameFlaw.game_id == game_id
            )
        )
    ).all()
    plies = {r.ply for r in rows}
    mist = sum(1 for r in rows if r.severity == _SEVERITY_INT["mistake"])
    blund = sum(1 for r in rows if r.severity == _SEVERITY_INT["blunder"])
    game_row = (
        await session.execute(
            text(
                "SELECT white_accuracy, black_accuracy, white_acpl, black_acpl"
                " FROM games WHERE id = :gid"
            ),
            {"gid": game_id},
        )
    ).one()
    return {
        "plies": plies,
        "mist": mist,
        "blund": blund,
        "white_accuracy": game_row.white_accuracy,
        "black_accuracy": game_row.black_accuracy,
        "white_acpl": game_row.white_acpl,
        "black_acpl": game_row.black_acpl,
    }


async def _prune_orphaned_drills(session: AsyncSession, game_id: int, user_id: int) -> int:
    """Delete `drill_items` whose `(user_id, game_id, ply)` no longer has a
    surviving `game_flaws` row (D-09). Returns the number of rows deleted.
    `drill_solves` are never touched (kept as history, D-09)."""
    result = await session.execute(
        text(
            "DELETE FROM drill_items di"
            " WHERE di.user_id = :uid AND di.game_id = :gid"
            " AND NOT EXISTS ("
            "   SELECT 1 FROM game_flaws gf"
            "   WHERE gf.user_id = di.user_id AND gf.game_id = di.game_id"
            "     AND gf.ply = di.ply"
            " )"
        ),
        {"uid": user_id, "gid": game_id},
    )
    return result.rowcount or 0  # ty: ignore[unresolved-attribute]  # DML result carries rowcount


async def _count_touched_herrings(session: AsyncSession, game_id: int) -> int:
    """Count `herring_pool` rows whose `(game_id, ply)` appears in `opening_
    cache_repair_rows` for this game (D-08: count only, never delete or
    regenerate -- a pool row is self-sufficient and serves mostly other
    users' Train sessions)."""
    return (
        await session.execute(
            text(
                "SELECT count(*) FROM herring_pool hp"
                " JOIN opening_cache_repair_rows r"
                "   ON r.game_id = hp.game_id AND r.ply = hp.ply"
                " WHERE hp.game_id = :gid"
            ),
            {"gid": game_id},
        )
    ).scalar_one()


def _apply_rederive_result(
    repair_game: OpeningCacheRepairGame,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    drill_items_pruned: int,
    herrings_touched: int,
) -> None:
    """Write one game's before/after rederive snapshot onto its `opening_cache_
    repair_games` row (pure mutation, no I/O). `flaws_added`/`flaws_removed`
    are the symmetric-difference sizes of the before/after ply sets -- running
    rederive twice over an unchanged game yields empty differences on the
    second run (must_haves: identical before/after counters)."""
    repair_game.flaws_before_inacc = 0
    repair_game.flaws_before_mist = before["mist"]
    repair_game.flaws_before_blund = before["blund"]
    repair_game.flaws_after_inacc = 0
    repair_game.flaws_after_mist = after["mist"]
    repair_game.flaws_after_blund = after["blund"]
    repair_game.flaws_added = len(after["plies"] - before["plies"])
    repair_game.flaws_removed = len(before["plies"] - after["plies"])
    repair_game.drill_items_pruned = drill_items_pruned
    repair_game.herrings_touched = herrings_touched
    repair_game.white_accuracy_before = before["white_accuracy"]
    repair_game.white_accuracy_after = after["white_accuracy"]
    repair_game.black_accuracy_before = before["black_accuracy"]
    repair_game.black_accuracy_after = after["black_accuracy"]
    repair_game.white_acpl_before = before["white_acpl"]
    repair_game.white_acpl_after = after["white_acpl"]
    repair_game.black_acpl_before = before["black_acpl"]
    repair_game.black_acpl_after = after["black_acpl"]
    repair_game.reclassified_at = datetime.now(timezone.utc)
    repair_game.status = "reclassified"


async def _write_rederive_failure(
    session_maker: async_sessionmaker[AsyncSession], game_id: int, *, error: str
) -> None:
    """Write `status='failed'` + `error` for one game in a FRESH short session
    -- the original session may already be closed/aborted (an exception
    unwinds `async with session_maker() as session:` without committing, which
    rolls back that transaction)."""
    async with session_maker() as session:
        repair_game = await session.get(OpeningCacheRepairGame, game_id)
        if repair_game is not None:
            repair_game.status = "failed"
            repair_game.error = error[:2000]
        await session.commit()


async def _rederive_reclassify_game(
    session: AsyncSession, game_id: int, user_id: int
) -> tuple[dict[str, Any], dict[str, Any], int, int] | None:
    """Steps 2-5 of one game's rederive, inside the caller's locked
    transaction. Returns None (and leaves the repair-games row untouched) when
    `classify_game_flaws` reports insufficient eval coverage (`GameNotAnalyzed`
    -- an expected condition, not an error); otherwise (before, after,
    drill_items_pruned, herrings_touched)."""
    loaded = await _load_game_and_positions(session, game_id)
    if loaded is None:
        raise ValueError("rederive: game not found")
    game, positions = loaded

    reason_check = classify_game_flaws(game, positions)
    if "reason" in reason_check:
        return None

    before = await _snapshot_rederive_state(session, game_id, user_id)
    await _classify_and_fill_oracle(session, game_id, {}, flaw_pv_blobs=None, blobs_pending=True)
    drill_items_pruned = await _prune_orphaned_drills(session, game_id, user_id)
    herrings_touched = await _count_touched_herrings(session, game_id)
    after = await _snapshot_rederive_state(session, game_id, user_id)
    return before, after, drill_items_pruned, herrings_touched


async def _rederive_one_game(
    session_maker: async_sessionmaker[AsyncSession], game_id: int, user_id: int
) -> None:
    """Reclassify one game's flaws/oracle counts under the per-game advisory
    lock (D-04), through `_classify_and_fill_oracle` -- the drain's own
    diff/upsert classifier, never the blob-destructive delete-then-insert
    shape. Runs in ITS OWN transaction (never shared across games), so one
    game's failure cannot roll back a neighbour. `GameNotAnalyzed` is an
    expected condition (marked `failed` with that reason, no Sentry capture);
    every other exception is captured to Sentry with no variables in the
    message string and the game is marked `failed` with the exception repr.
    """
    try:
        async with session_maker() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _game_write_lock_key(game_id)},
            )
            result = await _rederive_reclassify_game(session, game_id, user_id)
            if result is None:
                await _write_rederive_failure(
                    session_maker, game_id, error="GameNotAnalyzed: insufficient eval coverage"
                )
                return
            before, after, drill_items_pruned, herrings_touched = result
            repair_game = await session.get(OpeningCacheRepairGame, game_id)
            if repair_game is not None:
                _apply_rederive_result(
                    repair_game,
                    before=before,
                    after=after,
                    drill_items_pruned=drill_items_pruned,
                    herrings_touched=herrings_touched,
                )
            await session.commit()
    except Exception as exc:
        sentry_sdk.set_context("opening_cache_rederive", {"game_id": game_id, "user_id": user_id})
        sentry_sdk.set_tag("source", "opening-cache-repair")
        sentry_sdk.capture_exception(exc)
        await _write_rederive_failure(session_maker, game_id, error=repr(exc))


async def run_rederive(
    *,
    db: str,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Reclassify every `pending` `opening_cache_repair_games` row under the
    per-game advisory lock, through the drain's own diff/upsert classifier
    (CACHEFIX-06). Gated on `propagate_finished_at`.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        dry_run: If True, report how many games are still pending and write
            nothing.
        limit: Cap the number of games rederived this run, or None for all.
        session_maker: Injectable session factory for testing. Exposed as a
            module-level coroutine so `backfill_flaws.py --from-repair-table`
            (a thin delegating wrapper, CACHEFIX-06) can call it directly.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)

    try:
        if limit == 0:
            print("rederive: --limit 0, nothing to do.")
            return

        async with session_maker() as session:
            await _stage_gate(session, "rederive")

        if dry_run:
            async with session_maker() as session:
                count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheRepairGame)
                        .where(OpeningCacheRepairGame.status == "pending")
                    )
                ).scalar_one()
            print(f"rederive: {count} pending game(s) remain (--dry-run, nothing written).")
            return

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            if progress.rederive_started_at is None:
                progress.rederive_started_at = datetime.now(timezone.utc)
                await session.commit()

        _install_signal_handlers()
        processed_total = await _walk_rederive(session_maker, limit=limit)
        print(f"rederive: processed {processed_total} game(s).")
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


async def _walk_rederive(
    session_maker: async_sessionmaker[AsyncSession], *, limit: int | None
) -> int:
    """Page through `pending` `opening_cache_repair_games` rows (game_id ASC)
    until none remain, `limit` units have been processed, or a signal
    arrives. Stamps `rederive_finished_at` ONLY on true exhaustion. Returns
    the total games processed."""
    processed_total = 0
    while not _stop_requested:
        if limit is not None and processed_total >= limit:
            break
        async with session_maker() as session:
            pending_rows = (
                await session.execute(
                    select(OpeningCacheRepairGame.game_id, OpeningCacheRepairGame.user_id)
                    .where(OpeningCacheRepairGame.status == "pending")
                    .order_by(OpeningCacheRepairGame.game_id)
                    .limit(REPAIR_BATCH_ROWS)
                )
            ).all()
        if not pending_rows:
            async with session_maker() as fin_session:
                fin_progress = await _ensure_progress_row(fin_session)
                fin_progress.rederive_finished_at = datetime.now(timezone.utc)
                await fin_session.commit()
            break
        for game_id, user_id in pending_rows:
            if _stop_requested:
                break
            if limit is not None and processed_total >= limit:
                break
            await _rederive_one_game(session_maker, game_id, user_id)
            processed_total += 1
    return processed_total


# ─── `report` (CACHEFIX-07) ──────────────────────────────────────────────────

# scripts/benchmark_lane.py:100-101 precedent -- reports/{topic}/{topic}-YYYY-MM-DD.md,
# committed to git (RESEARCH Pitfall 10: reports/ is not gitignored except for
# four unrelated subpaths).
REPAIR_REPORTS_DIR: Path = (
    Path(__file__).resolve().parent.parent / "reports" / "opening-cache-repair"
)

# Report semantics: a `confirmed_bad` row becomes `repaired` once propagate has
# rewritten its carriers, so every "confirmed bad" report section counts both.
_CONFIRMED_BAD_STATUSES: tuple[str, ...] = ("confirmed_bad", "repaired")

# SEED-164 §Blast radius band boundaries -- shared by the confirmed_bad
# delta_cp histogram (section 1) and the lichess-median-vs-lichess-internal-IQR
# histogram (section 7, the PRIMARY acceptance signal). Matches PostgreSQL's
# width_bucket(x, ARRAY[...]) semantics: bucket 0 is x < bands[0], bucket i
# (1<=i<len(bands)) is bands[i-1] <= x < bands[i], the last bucket is
# x >= bands[-1].
_HISTOGRAM_BANDS_CP: tuple[int, ...] = (25, 50, 75, 100, 150, 250, 400)

# Rows-repaired-per-game distribution bucket boundaries (report section 4).
_ROWS_REPAIRED_BUCKET_BOUNDS: tuple[int, ...] = (1, 2, 5, 10, 20)

# Top-N users table size (report section 4).
_GAMES_TOP_USERS_LIMIT: int = 20

# 2026-09-09 prod baselines the verification block restates every observed
# value against (seed §Blast radius / §Step 6 report).
_LICHESS_CROSSCHECK_BASELINE_N_CHECKED: int = 25_444
_LICHESS_CROSSCHECK_BASELINE_N_BAD: int = 87
_HISTOGRAM_BASELINE_CACHE: tuple[int, ...] = (21_987, 3_064, 203, 52, 49, 50, 35, 4)
_HISTOGRAM_BASELINE_CTRL: tuple[int, ...] = (24_000, 1_132, 183, 66, 37, 20, 6, 0)
_BOUNCE_BASELINE_BENCHMARK: tuple[float, float] = (0.618, 0.235)
_BOUNCE_BASELINE_LEGACY: tuple[float, float] = (0.798, 0.298)
_BOUNCE_BASELINE_MID: tuple[float, float] = (0.625, 0.243)
_BOUNCE_BASELINE_RECENT: tuple[float, float] = (0.844, 0.271)

# Acceptance fixture (SEED-164 §Acceptance check): the game this repair was
# discovered in, and the 9 named cache hashes the diagnosis names for
# verification -- the report and the phase verification both assert them.
_ACCEPTANCE_GAME_ID: int = 2356581
_ACCEPTANCE_HASHES: tuple[int, ...] = (
    3250950765068847520,
    -1357424544074167494,
    3912952322572315143,
    -4495720059219567338,
    -3692655065124884866,
    6991966663941067682,
    -4230257548248121256,
    -7106566961782875842,
    -3185735734450884963,
)

# Canonical stage order for the timings section (D-05, seed §Step 6) --
# `orphans` is deliberately excluded: it has no {stage}_started_at/finished_at
# columns of its own (see _STAGE_ORDER's docstring), so it is reported
# separately as "not tracked" rather than crashing on a missing attribute.
_TIMING_STAGE_ORDER: tuple[str, ...] = (
    "seed",
    "calibrate",
    "screen",
    "orphans",
    "confirm",
    "propagate",
    "rederive",
)

_LICHESS_CROSSCHECK_SQL = text(
    """
    WITH l AS (
      SELECT gp.full_hash,
             percentile_cont(0.5) WITHIN GROUP (ORDER BY prev.eval_cp) AS med, count(*) AS n
      FROM games g
      JOIN game_positions gp   ON gp.game_id = g.id AND gp.ply BETWEEN 1 AND 12
      JOIN game_positions prev ON prev.game_id = g.id AND prev.ply = gp.ply - 1
      WHERE g.lichess_evals_at IS NOT NULL AND prev.eval_cp IS NOT NULL AND prev.eval_mate IS NULL
      GROUP BY gp.full_hash HAVING count(*) >= 3)
    SELECT count(*) AS n_checked,
           count(*) FILTER (WHERE abs(o.eval_cp - l.med) > 150) AS n_bad
    FROM l JOIN opening_position_eval o ON o.full_hash = l.full_hash
    WHERE o.eval_mate IS NULL
    """
)

_HISTOGRAM_VS_CONTROL_SQL = text(
    """
    WITH l AS (
      SELECT gp.full_hash,
             percentile_cont(0.5) WITHIN GROUP (ORDER BY prev.eval_cp) AS med,
             percentile_cont(0.75) WITHIN GROUP (ORDER BY prev.eval_cp)
               - percentile_cont(0.25) WITHIN GROUP (ORDER BY prev.eval_cp) AS iqr
      FROM games g
      JOIN game_positions gp   ON gp.game_id = g.id AND gp.ply BETWEEN 1 AND 12
      JOIN game_positions prev ON prev.game_id = g.id AND prev.ply = gp.ply - 1
      WHERE g.lichess_evals_at IS NOT NULL AND prev.eval_cp IS NOT NULL AND prev.eval_mate IS NULL
      GROUP BY gp.full_hash HAVING count(*) >= 3),
    d AS (SELECT abs(o.eval_cp - l.med) AS delta, l.iqr
          FROM l JOIN opening_position_eval o ON o.full_hash = l.full_hash
          WHERE o.eval_mate IS NULL),
    h AS (SELECT width_bucket(delta, ARRAY[25,50,75,100,150,250,400]) AS b, count(*) AS n_cache
          FROM d GROUP BY 1),
    c AS (SELECT width_bucket(iqr,   ARRAY[25,50,75,100,150,250,400]) AS b, count(*) AS n_ctrl
          FROM d GROUP BY 1)
    SELECT coalesce(h.b, c.b) AS bucket, n_cache, n_ctrl FROM h FULL JOIN c ON c.b = h.b ORDER BY 1
    """
)

_OPENING_BOUNCE_RATE_SQL = text(
    """
    WITH b AS (
      SELECT abs(p.eval_cp - prev.eval_cp) AS drop_cp,
             abs(nxt.eval_cp - prev.eval_cp) AS bounce_cp
      FROM game_positions p
      JOIN game_positions prev ON prev.game_id = p.game_id AND prev.ply = p.ply - 1
      JOIN game_positions nxt  ON nxt.game_id  = p.game_id AND nxt.ply  = p.ply + 1
      JOIN games g ON g.id = p.game_id
      WHERE p.ply BETWEEN 2 AND 19
        AND g.full_evals_completed_at IS NOT NULL
        AND g.lichess_evals_at IS NULL
        AND p.eval_mate IS NULL AND prev.eval_mate IS NULL AND nxt.eval_mate IS NULL
        AND p.eval_cp IS NOT NULL AND prev.eval_cp IS NOT NULL AND nxt.eval_cp IS NOT NULL
    )
    SELECT
      count(*) AS n_checked,
      count(*) FILTER (WHERE drop_cp >= 200 AND bounce_cp <= 60) AS n_bounce_any,
      count(*) FILTER (WHERE drop_cp BETWEEN 250 AND 360) AS n_band,
      count(*) FILTER (WHERE drop_cp BETWEEN 250 AND 360 AND bounce_cp <= 60) AS n_bounce_band
    FROM b
    """
)


def _bucket_by_bands(values: list[float], bands: tuple[int, ...]) -> list[int]:
    """Bucket `values` into len(bands)+1 bins using PostgreSQL's own
    width_bucket semantics (see _HISTOGRAM_BANDS_CP's docstring) -- shared by
    every histogram this report renders in Python rather than SQL."""
    counts = [0] * (len(bands) + 1)
    for v in values:
        idx = 0
        for b in bands:
            if v >= b:
                idx += 1
            else:
                break
        counts[idx] += 1
    return counts


def _band_labels(bands: tuple[int, ...]) -> list[str]:
    labels = [f"< {bands[0]}"]
    labels += [f"{bands[i]}-{bands[i + 1]}" for i in range(len(bands) - 1)]
    labels.append(f"> {bands[-1]}")
    return labels


def _format_pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def _mean_paired_delta(pairs: list[tuple[float | None, float | None]]) -> float | None:
    deltas = [after - before for before, after in pairs if before is not None and after is not None]
    return sum(deltas) / len(deltas) if deltas else None


async def _report_section_status_breakdown(session: AsyncSession) -> list[str]:
    """Section 1: cache status breakdown (all 8 statuses, `pending` split into
    "no carrier" (orphan candidate) vs "has a carrier" (walk cut short) so the
    accounting cannot read complete when it is not), plus the confirmed_bad
    delta_cp histogram."""
    status_count_rows = (
        await session.execute(
            select(OpeningCacheAudit.status, func.count()).group_by(OpeningCacheAudit.status)
        )
    ).all()
    counts = {status: n for status, n in status_count_rows}

    pending_hashes = (
        (
            await session.execute(
                select(OpeningCacheAudit.full_hash).where(OpeningCacheAudit.status == "pending")
            )
        )
        .scalars()
        .all()
    )
    carrier_hashes: set[int] = set()
    if pending_hashes:
        carrier_hashes = set(
            (
                await session.execute(
                    select(GamePosition.full_hash)
                    .where(
                        GamePosition.full_hash.in_(pending_hashes),
                        GamePosition.ply.between(1, 20),
                    )
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
    pending_no_carrier = sum(1 for h in pending_hashes if h not in carrier_hashes)
    pending_has_carrier = len(pending_hashes) - pending_no_carrier

    lines = ["## 1. Cache status breakdown", "", "| Status | Count |", "|---|---|"]
    for status in (
        "screened_clean",
        "flagged",
        "confirmed_bad",
        "confirmed_clean",
        "orphan",
        "hash_mismatch",
        "repaired",
    ):
        lines.append(f"| `{status}` | {counts.get(status, 0):,} |")
    lines.append(f"| `pending`, no carrier (orphan candidate) | {pending_no_carrier:,} |")
    lines.append(f"| `pending`, has a carrier (walk cut short) | {pending_has_carrier:,} |")
    lines.append("")

    delta_cp_rows = (
        (
            await session.execute(
                select(OpeningCacheAudit.delta_cp).where(
                    OpeningCacheAudit.status.in_(_CONFIRMED_BAD_STATUSES),
                    OpeningCacheAudit.delta_cp.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    delta_cps = [float(d) for d in delta_cp_rows if d is not None]
    bucket_counts = _bucket_by_bands([abs(d) for d in delta_cps], _HISTOGRAM_BANDS_CP)
    labels = _band_labels(_HISTOGRAM_BANDS_CP)
    lines += [
        "`confirmed_bad` `delta_cp` histogram (old vs new, absolute value):",
        "",
        "| abs(delta_cp) band | count |",
        "|---|---|",
    ]
    for label, n in zip(labels, bucket_counts, strict=True):
        lines.append(f"| {label} | {n:,} |")
    lines.append("")
    return lines


async def _reconstruct_san(session: AsyncSession, game_id: int, ply: int) -> str | None:
    """Reconstruct the SAN of the move played FROM the position at `ply` in
    `game_id`, via the same helper `screen`/`confirm` use -- no re-derivation
    of the PGN walk."""
    game = await session.get(Game, game_id)
    if game is None:
        return None
    pos_result = await session.execute(
        select(
            GamePosition.ply,
            GamePosition.full_hash,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
        ).where(GamePosition.game_id == game_id, GamePosition.ply.between(1, 20))
    )
    gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]
    targets = _carrier_targets(game_id, game.pgn, gp_rows)
    target = next((t for t in targets if t.ply == ply), None)
    return target.move_san if target is not None else None


async def _report_section_top30(session: AsyncSession) -> list[str]:
    """Section 2: top-30 `confirmed_bad` positions by carrier count, ordered
    carrier count DESC then full_hash ASC -- a TOTAL order, so the table is
    reproducible across runs regardless of the DB's own scan order."""
    audit_rows = (
        (
            await session.execute(
                select(OpeningCacheAudit).where(
                    OpeningCacheAudit.status.in_(_CONFIRMED_BAD_STATUSES)
                )
            )
        )
        .scalars()
        .all()
    )
    lines = ["## 2. Top-30 `confirmed_bad` positions by carrier count", ""]
    if not audit_rows:
        lines += ["No `confirmed_bad` rows.", ""]
        return lines

    hashes = [a.full_hash for a in audit_rows]
    carrier_rows = (
        await session.execute(
            select(GamePosition.full_hash, func.count())
            .where(GamePosition.full_hash.in_(hashes), GamePosition.ply.between(1, 20))
            .group_by(GamePosition.full_hash)
        )
    ).all()
    carrier_count = {full_hash: n for full_hash, n in carrier_rows}

    ranked = sorted(audit_rows, key=lambda a: (-carrier_count.get(a.full_hash, 0), a.full_hash))[
        :30
    ]

    lines += [
        "| full_hash | carriers | old_cp | full_cp | delta_cp | SAN |",
        "|---|---|---|---|---|---|",
    ]
    for audit in ranked:
        san = None
        if audit.sample_game_id is not None and audit.sample_ply is not None:
            san = await _reconstruct_san(session, audit.sample_game_id, audit.sample_ply)
        lines.append(
            f"| {audit.full_hash} | {carrier_count.get(audit.full_hash, 0):,} |"
            f" {audit.old_cp} | {audit.full_cp} | {audit.delta_cp} | {san or '?'} |"
        )
    lines.append("")
    return lines


async def _report_section_positions_rewritten(session: AsyncSession) -> list[str]:
    """Section 3: `opening_cache_repair_rows` totals, best_move/pv replacement
    counted SEPARATELY (Pitfall 5: pv is written only at flaw-adjacent plies,
    so a zero pv_replaced count is expected, not a bug), and a by-ply
    distribution."""
    total = (
        await session.execute(select(func.count()).select_from(OpeningCacheRepairRow))
    ).scalar_one()
    bm_replaced = (
        await session.execute(
            select(func.count())
            .select_from(OpeningCacheRepairRow)
            .where(OpeningCacheRepairRow.best_move_replaced.is_(True))
        )
    ).scalar_one()
    pv_replaced = (
        await session.execute(
            select(func.count())
            .select_from(OpeningCacheRepairRow)
            .where(OpeningCacheRepairRow.pv_replaced.is_(True))
        )
    ).scalar_one()
    by_ply = (
        await session.execute(
            select(OpeningCacheRepairRow.ply, func.count())
            .group_by(OpeningCacheRepairRow.ply)
            .order_by(OpeningCacheRepairRow.ply)
        )
    ).all()

    lines = [
        "## 3. Positions rewritten",
        "",
        f"- Total `game_positions` cells rewritten: {total:,}",
        f"- Also had `best_move` replaced: {bm_replaced:,}",
        f"- Also had `pv` replaced (expected near-zero -- see Pitfall 5): {pv_replaced:,}",
        "",
        "| ply | rows repaired |",
        "|---|---|",
    ]
    for ply, n in by_ply:
        lines.append(f"| {ply} | {n:,} |")
    lines.append("")
    return lines


async def _report_section_games_affected(session: AsyncSession) -> list[str]:
    """Section 4: games affected by platform and by user id (numeric ids only
    -- no join to any user-identifying column), plus the per-game
    rows-repaired distribution."""
    by_platform = (
        await session.execute(
            select(Game.platform, func.count())
            .select_from(OpeningCacheRepairGame)
            .join(Game, Game.id == OpeningCacheRepairGame.game_id)
            .group_by(Game.platform)
        )
    ).all()
    by_user = (
        await session.execute(
            select(OpeningCacheRepairGame.user_id, func.count())
            .group_by(OpeningCacheRepairGame.user_id)
            .order_by(func.count().desc(), OpeningCacheRepairGame.user_id)
            .limit(_GAMES_TOP_USERS_LIMIT)
        )
    ).all()
    distinct_users = (
        await session.execute(select(func.count(func.distinct(OpeningCacheRepairGame.user_id))))
    ).scalar_one()
    rows_repaired = (
        (await session.execute(select(OpeningCacheRepairGame.rows_repaired))).scalars().all()
    )

    lines = [
        "## 4. Games affected",
        "",
        "By platform:",
        "",
        "| platform | games |",
        "|---|---|",
    ]
    for platform, n in by_platform:
        lines.append(f"| {platform} | {n:,} |")
    lines += [
        "",
        f"By user id (top {_GAMES_TOP_USERS_LIMIT}, numeric only):",
        "",
        "| user_id | games |",
        "|---|---|",
    ]
    for user_id, n in by_user:
        lines.append(f"| {user_id} | {n:,} |")
    lines += [
        "",
        f"Distinct users with at least one affected game: {distinct_users:,}",
        "",
        "Per-game rows-repaired distribution:",
        "",
        "| rows repaired | games |",
        "|---|---|",
    ]
    bucket_counts = _bucket_by_bands(
        [float(r) for r in rows_repaired], _ROWS_REPAIRED_BUCKET_BOUNDS
    )
    labels = _band_labels(_ROWS_REPAIRED_BUCKET_BOUNDS)
    for label, n in zip(labels, bucket_counts, strict=True):
        lines.append(f"| {label} | {n:,} |")
    lines.append("")
    return lines


async def _report_section_flaws(session: AsyncSession) -> list[str]:
    """Section 5: before/after flaw totals by severity, spurious flaws
    removed, flaws added, games whose blunder count changed,
    drill_items_pruned, herrings_touched, and mean accuracy/ACPL shift --
    summed/averaged across every `reclassified` repair-game row."""
    rows = (
        (
            await session.execute(
                select(OpeningCacheRepairGame).where(
                    OpeningCacheRepairGame.status == "reclassified"
                )
            )
        )
        .scalars()
        .all()
    )

    before_mist = sum(r.flaws_before_mist for r in rows)
    before_blund = sum(r.flaws_before_blund for r in rows)
    after_mist = sum(r.flaws_after_mist for r in rows)
    after_blund = sum(r.flaws_after_blund for r in rows)
    removed = sum(r.flaws_removed for r in rows)
    added = sum(r.flaws_added for r in rows)
    blund_changed = sum(1 for r in rows if r.flaws_before_blund != r.flaws_after_blund)
    drill_pruned = sum(r.drill_items_pruned for r in rows)
    herrings = sum(r.herrings_touched for r in rows)

    acc_pairs = [(r.white_accuracy_before, r.white_accuracy_after) for r in rows]
    acc_pairs += [(r.black_accuracy_before, r.black_accuracy_after) for r in rows]
    acpl_pairs: list[tuple[float | None, float | None]] = [
        (float(r.white_acpl_before), float(r.white_acpl_after))
        for r in rows
        if r.white_acpl_before is not None and r.white_acpl_after is not None
    ]
    acpl_pairs += [
        (float(r.black_acpl_before), float(r.black_acpl_after))
        for r in rows
        if r.black_acpl_before is not None and r.black_acpl_after is not None
    ]
    mean_acc_shift = _mean_paired_delta(acc_pairs)
    mean_acpl_shift = _mean_paired_delta(acpl_pairs)

    lines = [
        "## 5. Flaws",
        "",
        f"- Mistakes: {before_mist:,} -> {after_mist:,}",
        f"- Blunders: {before_blund:,} -> {after_blund:,}",
        f"- Spurious flaws removed: {removed:,}",
        f"- Flaws added: {added:,}",
        f"- Games whose blunder count changed: {blund_changed:,}",
        f"- `drill_items` pruned: {drill_pruned:,}",
        f"- `herring_pool` rows touched (counter only, never deleted): {herrings:,}",
        (
            f"- Mean accuracy shift (after - before, both colors): {mean_acc_shift:+.3f}"
            if mean_acc_shift is not None
            else "- Mean accuracy shift (after - before, both colors): n/a"
        ),
        (
            f"- Mean ACPL shift (after - before, both colors): {mean_acpl_shift:+.2f}"
            if mean_acpl_shift is not None
            else "- Mean ACPL shift (after - before, both colors): n/a"
        ),
        "",
    ]
    return lines


def _report_section_provenance_leaks_closed() -> list[str]:
    """Section 6: static note -- plan 220-02 closed the two write-path leaks
    diagnosed as part of why the cache was poisoned."""
    return [
        "## 6. Provenance leaks closed",
        "",
        "Plan 220-02 stopped the full-eval drain tick from donating a"
        " lichess-eval game's opening plies to the cache, and gave the"
        " `OPENING_CACHE_BACKFILL_SQL` backfill a deterministic donor order"
        " (newest `full_evals_completed_at`, pv-bearing tiebreak) -- both were"
        " part of why the cache was poisoned in the first place.",
        "",
    ]


async def _report_section_acceptance_fixture(session: AsyncSession) -> list[str]:
    """The game-2356581 before/after fixture and the 9 named hashes' observed
    audit status (SEED-164 §Acceptance check)."""
    lines = ["### Acceptance fixture: game 2356581 and the 9 named hashes", ""]

    game = await session.get(Game, _ACCEPTANCE_GAME_ID)
    if game is None:
        lines += [f"Game {_ACCEPTANCE_GAME_ID} not present in this database.", ""]
    else:
        pos_rows = (
            await session.execute(
                select(GamePosition.ply, GamePosition.eval_cp)
                .where(
                    GamePosition.game_id == _ACCEPTANCE_GAME_ID,
                    GamePosition.ply.in_([4, 5, 6]),
                )
                .order_by(GamePosition.ply)
            )
        ).all()
        flaw_rows = (
            await session.execute(
                select(GameFlaw.ply, GameFlaw.severity)
                .where(GameFlaw.game_id == _ACCEPTANCE_GAME_ID, GameFlaw.ply.in_([5, 6]))
                .order_by(GameFlaw.ply)
            )
        ).all()
        eval_str = ", ".join(f"ply {ply}={eval_cp}" for ply, eval_cp in pos_rows) or "none"
        flaw_str = ", ".join(f"ply {ply} severity={sev}" for ply, sev in flaw_rows) or "none"
        lines += [
            f"- `game_positions.eval_cp` at plies 4/5/6: {eval_str}",
            f"- `game_flaws` rows at plies 5/6: {flaw_str}",
            f"- `white_blunders`={game.white_blunders}, `black_blunders`={game.black_blunders}",
            "",
        ]

    acceptance_hash_rows = (
        await session.execute(
            select(OpeningCacheAudit.full_hash, OpeningCacheAudit.status).where(
                OpeningCacheAudit.full_hash.in_(_ACCEPTANCE_HASHES)
            )
        )
    ).all()
    status_by_hash = {full_hash: status for full_hash, status in acceptance_hash_rows}
    lines += ["| full_hash | observed status |", "|---|---|"]
    for h in _ACCEPTANCE_HASHES:
        lines.append(f"| {h} | {status_by_hash.get(h, 'not seeded')} |")
    lines.append("")
    return lines


async def _report_section_verification(
    session: AsyncSession, progress: OpeningCacheRepairProgress
) -> list[str]:
    """Section 7: restate every observed value next to its recorded
    2026-09-09 baseline. The histogram-vs-control table is labelled the
    PRIMARY acceptance signal -- a count at one cp cut only sizes the blast
    radius; the bounce rate is explicitly a coarse sanity check that cannot
    pass/fail the repair on its own."""
    lines = ["## 7. Verification block", ""]

    n_checked, n_bad = (await session.execute(_LICHESS_CROSSCHECK_SQL)).one()
    lines += [
        "### Lichess cross-check",
        "",
        f"- Observed: n_checked={n_checked:,}, n_bad={n_bad:,}",
        f"- 2026-09-09 baseline: n_checked={_LICHESS_CROSSCHECK_BASELINE_N_CHECKED:,},"
        f" n_bad={_LICHESS_CROSSCHECK_BASELINE_N_BAD:,}",
        "",
    ]

    hist_rows = (await session.execute(_HISTOGRAM_VS_CONTROL_SQL)).all()
    hist_by_bucket = {int(b): (n_cache or 0, n_ctrl or 0) for b, n_cache, n_ctrl in hist_rows}
    labels = _band_labels(_HISTOGRAM_BANDS_CP)
    lines += [
        "### Delta histogram vs lichess-internal IQR control"
        " (**PRIMARY ACCEPTANCE SIGNAL** -- every band above the noise floor"
        " must match the control after repair)",
        "",
        "| abs(delta) band | observed n_cache | observed n_ctrl |"
        " baseline n_cache | baseline n_ctrl |",
        "|---|---|---|---|---|",
    ]
    for i, label in enumerate(labels):
        n_cache, n_ctrl = hist_by_bucket.get(i, (0, 0))
        lines.append(
            f"| {label} | {n_cache:,} | {n_ctrl:,} |"
            f" {_HISTOGRAM_BASELINE_CACHE[i]:,} | {_HISTOGRAM_BASELINE_CTRL[i]:,} |"
        )
    lines.append("")

    n_checked_b, n_bounce_any, n_band, n_bounce_band = (
        await session.execute(_OPENING_BOUNCE_RATE_SQL)
    ).one()
    lines += [
        "### Opening bounce rate (coarse sanity check only -- cannot"
        " pass/fail the repair on its own)",
        "",
        f"- Observed: {_format_pct(n_bounce_any, n_checked_b)} any bounce"
        f" ({n_bounce_any:,}/{n_checked_b:,}),"
        f" {_format_pct(n_bounce_band, n_band)} in the 250-360cp band"
        f" ({n_bounce_band:,}/{n_band:,})",
        f"- Baseline: benchmark DB (cache-free) {_BOUNCE_BASELINE_BENCHMARK[0]}%"
        f" / {_BOUNCE_BASELINE_BENCHMARK[1]}%; prod legacy"
        f" {_BOUNCE_BASELINE_LEGACY[0]}% / {_BOUNCE_BASELINE_LEGACY[1]}%; mid"
        f" {_BOUNCE_BASELINE_MID[0]}% / {_BOUNCE_BASELINE_MID[1]}%; recent"
        f" {_BOUNCE_BASELINE_RECENT[0]}% / {_BOUNCE_BASELINE_RECENT[1]}%",
        "",
        "### Calibration",
        "",
        f"- screen_floor={progress.screen_floor}, confirm_floor={progress.confirm_floor},"
        f" calibration_n={progress.calibration_n}, calibrated_at={progress.calibrated_at},"
        f" engine_version={progress.engine_version}",
        "",
    ]

    lines += await _report_section_acceptance_fixture(session)
    return lines


def _report_section_timings(progress: OpeningCacheRepairProgress) -> list[str]:
    """Section 8: per-stage timings in the canonical stage order (never
    row-insertion order)."""
    lines = [
        "## 8. Per-stage timings",
        "",
        "| stage | started | finished | elapsed |",
        "|---|---|---|---|",
    ]
    for stage in _TIMING_STAGE_ORDER:
        started_col = f"{stage}_started_at"
        finished_col = f"{stage}_finished_at"
        if not hasattr(progress, started_col):
            lines.append(f"| {stage} | (not tracked -- one-shot action) | | |")
            continue
        started = getattr(progress, started_col)
        finished = getattr(progress, finished_col)
        elapsed = (finished - started) if started is not None and finished is not None else None
        lines.append(
            f"| {stage} | {started or '-'} | {finished or '-'} | {elapsed if elapsed is not None else '-'} |"
        )
    lines.append("")
    return lines


def _git_short_sha() -> str | None:
    try:
        result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no user input
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _report_section_final_provenance(
    *, db: str, now: datetime, engine_version: str | None
) -> list[str]:
    """Section 9: `--db` target, generation timestamp, script revision, engine
    version -- restated at the tail of every report, partial or full."""
    return [
        "## Provenance",
        "",
        f"- DB target: `{db}`",
        f"- Report generated: {now.isoformat()}",
        f"- Script revision: {_git_short_sha() or 'unknown'}",
        f"- engine_version: {engine_version or 'unknown'}",
        "",
    ]


async def write_repair_report(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    now: datetime,
    out_dir: Path = REPAIR_REPORTS_DIR,
    db: str = "unknown",
) -> Path:
    """Read-only: renders every audit table into one committed markdown trail.

    Takes `now`/`out_dir` as parameters (never calling `datetime.now()`
    internally) so a test can pin both the filename and the target directory
    (`scripts/benchmark_lane.py::write_record_report` precedent). Opens a
    single session and issues SELECT-only queries -- no DML, no commit --
    against `opening_position_eval`, `game_positions`, `game_flaws`,
    `opening_cache_audit`, `opening_cache_repair_rows` and
    `opening_cache_repair_games`; `test_report_read_only` asserts all six
    tables' row counts are identical before and after a run.

    Args:
        session_maker: Injectable session factory for testing.
        now: Report timestamp, also used to name the file (never
            `datetime.now()` internally).
        out_dir: Target directory for the report file.
        db: DB target string, for the Provenance section only.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")
    report_path = out_dir / f"opening-cache-repair-{date_str}.md"

    async with session_maker() as session:
        progress = await _ensure_progress_row(session)
        lines: list[str] = [f"# Opening Cache Repair Report -- {date_str}", ""]
        lines += await _report_section_status_breakdown(session)
        lines += await _report_section_top30(session)
        lines += await _report_section_positions_rewritten(session)
        lines += await _report_section_games_affected(session)
        lines += await _report_section_flaws(session)
        lines += _report_section_provenance_leaks_closed()
        lines += await _report_section_verification(session, progress)
        lines += _report_section_timings(progress)
        lines += _report_section_final_provenance(
            db=db, now=now, engine_version=progress.engine_version
        )
        # Read-only: session is discarded here with no DML ever issued.

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


async def run_report(
    *,
    db: str,
    partial: bool,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    out_dir: Path = REPAIR_REPORTS_DIR,
    now: datetime | None = None,
) -> Path:
    """Read-only `report` stage (CACHEFIX-07). Gated on `rederive_finished_at`
    unless `--partial` is given, which skips the gate and prints a banner --
    a partial snapshot is legitimate at any time, but a full (non-partial)
    report implicitly claims the whole pipeline finished.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        partial: Skip the stage gate and print a partial-snapshot banner.
        session_maker: Injectable session factory for testing.
        out_dir: Target directory for the report file.
        now: Report timestamp override for testing.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)
    report_now = now or datetime.now(timezone.utc)

    try:
        if partial:
            print("report: --partial, skipping the rederive_finished_at gate.")
        else:
            async with session_maker() as session:
                await _stage_gate(session, "report")

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            if progress.report_started_at is None:
                progress.report_started_at = report_now
                await session.commit()

        report_path = await write_repair_report(
            session_maker, now=report_now, out_dir=out_dir, db=db
        )

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            progress.report_finished_at = datetime.now(timezone.utc)
            await session.commit()

        print(f"report: wrote {report_path}")
        return report_path
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── `legacy-sample` (CACHEFIX-10, D-07) ─────────────────────────────────────

# D-07: 200 pre-2026-06-18 fully-evaluated games across ALL plies at depth 15,
# plus a like-for-like 50-game post-2026-08-20 control on the same walk.
LEGACY_SAMPLE_GAMES: int = 200
LEGACY_CONTROL_GAMES: int = 50
LEGACY_CUTOFF: datetime = datetime(2026, 6, 18, tzinfo=timezone.utc)

# D-07 build rule: build screen --legacy-cohort only when BOTH hold.
LEGACY_BUILD_RATIO: float = 2.0
LEGACY_BUILD_MIN_EXCESS_PP: float = 1.0

_LEGACY_DECISION_BUILD: str = "LEGACY-COHORT-DECISION: BUILD screen --legacy-cohort"
_LEGACY_DECISION_NO_BUILD: str = "LEGACY-COHORT-DECISION: NO BUILD"

# One legacy-sample row after hash assertion: (ply, board, prev_cp, prev_mate)
# -- prev_cp/prev_mate is the STORED eval for this ply's position, which under
# the post-move shift sits on game_positions row ply-1.
_LegacySampleRow = tuple[int, chess.Board, int | None, int | None]


@dataclass(slots=True)
class _LegacySampleCohortResult:
    """One cohort's walk result, split at ply 20 (D-07)."""

    n_games: int
    rows_le20: int
    rows_gt20: int
    disagree_le20: int
    disagree_gt20: int


async def _collect_legacy_sample_games(
    session: AsyncSession,
    *,
    before: datetime | None,
    after: datetime | None,
    n: int,
) -> list[int]:
    """Up to `n` engine-game ids (`lichess_evals_at IS NULL`,
    `full_evals_completed_at IS NOT NULL`) meeting the cutoff, sampled
    deterministically via `ORDER BY md5(id::text)` -- a pure function of
    `id`, so a re-run against unchanged data selects the identical set, and
    the sample spreads across the whole eligible population rather than only
    its earliest ids."""
    stmt = select(Game.id).where(
        Game.lichess_evals_at.is_(None), Game.full_evals_completed_at.is_not(None)
    )
    if before is not None:
        stmt = stmt.where(Game.full_evals_completed_at < before)
    if after is not None:
        stmt = stmt.where(Game.full_evals_completed_at >= after)
    stmt = stmt.order_by(text("md5(games.id::text)")).limit(n)
    return list((await session.execute(stmt)).scalars().all())


async def _walk_legacy_sample_game(session: AsyncSession, game_id: int) -> list[_LegacySampleRow]:
    """Read phase for one legacy-sample game: ALL plies (not just the opening
    region), hash-asserted. Ply 0 is skipped -- it has no "prev" row under the
    post-move convention (there is no ply -1). No engine call happens here
    (Pitfall 8)."""
    game = await session.get(Game, game_id)
    if game is None:
        return []
    pos_result = await session.execute(
        select(
            GamePosition.ply,
            GamePosition.full_hash,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
        ).where(GamePosition.game_id == game_id)
    )
    gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]
    eval_by_ply = {r[0]: (r[2], r[3]) for r in gp_rows}
    targets = _collect_full_ply_targets(game_id, game.pgn, gp_rows, include_terminal=False)

    out: list[_LegacySampleRow] = []
    for target in targets:
        if target.ply == 0:
            continue
        if compute_hashes(target.board)[2] != target.full_hash:
            continue  # hash mismatch -- skip, never send to the engine
        prev_cp, prev_mate = eval_by_ply.get(target.ply - 1, (None, None))
        out.append((target.ply, target.board, prev_cp, prev_mate))
    return out


def _classify_legacy_sample_row(
    *,
    prev_cp: int | None,
    prev_mate: int | None,
    depth_cp: int | None,
    depth_mate: int | None,
    screen_floor: float,
) -> bool:
    """True iff this row disagrees: expected-score delta beyond `screen_floor`
    (screen's own inclusive `<=` boundary -- a delta exactly equal to
    screen_floor agrees) or a mate/non-mate status mismatch."""
    prev_es = _expected_score(prev_cp, prev_mate)
    depth_es = _expected_score(depth_cp, depth_mate)
    mates_agree = (prev_mate is None) == (depth_mate is None)
    if prev_es is None or depth_es is None:
        return True
    return abs(depth_es - prev_es) > screen_floor or not mates_agree


async def _run_legacy_sample_cohort(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    pool: EnginePool,
    game_ids: list[int],
    screen_floor: float,
) -> _LegacySampleCohortResult:
    """Walk every game in `game_ids` through the same per-row disagreement
    test `screen` uses, splitting counts at ply 20. One session per game for
    the read phase (closed before the gather), matching Pitfall 8."""
    rows_le20 = rows_gt20 = disagree_le20 = disagree_gt20 = 0
    for game_id in game_ids:
        async with session_maker() as session:
            rows = await _walk_legacy_sample_game(session, game_id)
        if not rows:
            continue
        eval_results = await asyncio.gather(
            *(pool.evaluate(board) for _ply, board, _cp, _mt in rows)
        )
        for (ply, _board, prev_cp, prev_mate), (depth_cp, depth_mate) in zip(
            rows, eval_results, strict=True
        ):
            disagrees = _classify_legacy_sample_row(
                prev_cp=prev_cp,
                prev_mate=prev_mate,
                depth_cp=depth_cp,
                depth_mate=depth_mate,
                screen_floor=screen_floor,
            )
            if ply <= 20:
                rows_le20 += 1
                disagree_le20 += 1 if disagrees else 0
            else:
                rows_gt20 += 1
                disagree_gt20 += 1 if disagrees else 0
    return _LegacySampleCohortResult(
        n_games=len(game_ids),
        rows_le20=rows_le20,
        rows_gt20=rows_gt20,
        disagree_le20=disagree_le20,
        disagree_gt20=disagree_gt20,
    )


def _legacy_sample_rate(disagree: int, rows: int) -> float:
    return (100.0 * disagree / rows) if rows > 0 else 0.0


def _legacy_sample_decision(
    legacy: _LegacySampleCohortResult, control: _LegacySampleCohortResult
) -> tuple[float, float, bool]:
    """D-07 decision rule, restated verbatim in the printed decision block:
    build only when `legacy_rate_ply_gt_20 > LEGACY_BUILD_RATIO *
    control_rate_ply_gt_20` AND `(legacy_rate - control_rate) >=
    LEGACY_BUILD_MIN_EXCESS_PP`. Returns (legacy_rate, control_rate, build)."""
    legacy_rate = _legacy_sample_rate(legacy.disagree_gt20, legacy.rows_gt20)
    control_rate = _legacy_sample_rate(control.disagree_gt20, control.rows_gt20)
    build = (
        legacy_rate > LEGACY_BUILD_RATIO * control_rate
        and (legacy_rate - control_rate) >= LEGACY_BUILD_MIN_EXCESS_PP
    )
    return legacy_rate, control_rate, build


def _format_legacy_sample_decision(
    legacy: _LegacySampleCohortResult,
    control: _LegacySampleCohortResult,
    legacy_rate: float,
    control_rate: float,
    build: bool,
) -> list[str]:
    verdict = _LEGACY_DECISION_BUILD if build else _LEGACY_DECISION_NO_BUILD
    return [
        "legacy-sample: D-07 decision",
        f"- legacy cohort: {legacy.n_games} games,"
        f" {legacy.rows_le20} rows ply<=20 ({legacy.disagree_le20} disagree),"
        f" {legacy.rows_gt20} rows ply>20 ({legacy.disagree_gt20} disagree, {legacy_rate:.2f}%)",
        f"- control cohort: {control.n_games} games,"
        f" {control.rows_le20} rows ply<=20 ({control.disagree_le20} disagree),"
        f" {control.rows_gt20} rows ply>20 ({control.disagree_gt20} disagree, {control_rate:.2f}%)",
        "- rule: build only when legacy_rate_ply_gt_20 > LEGACY_BUILD_RATIO *"
        " control_rate_ply_gt_20 AND (legacy_rate - control_rate) >="
        " LEGACY_BUILD_MIN_EXCESS_PP",
        verdict,
    ]


async def run_legacy_sample(
    *,
    db: str,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: EnginePool | None = None,
    pool_size: int | None = None,
    append_report: bool = False,
    out_dir: Path = REPAIR_REPORTS_DIR,
    now: datetime | None = None,
) -> None:
    """D-07: measure whether the pre-2026-06-18 legacy cohort also carries
    wrong-position evals beyond ply 20, against a like-for-like
    post-2026-08-20 control, through the SAME per-row disagreement test
    `screen` uses. Gated on `calibrate_finished_at`/`screen_floor` ONLY --
    deliberately NOT via the generic `_stage_gate`/`_STAGE_ORDER` walk, which
    would incorrectly require `report_finished_at` (this stage runs after
    `report` in practice, but its real dependency is the floor, D-07). Writes
    nothing but its own progress timestamps.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        session_maker: Injectable session factory for testing.
        pool: Injectable EnginePool for testing.
        append_report: Also append the decision block to the dated report
            file, if one already exists for `now`'s date.
        out_dir: Report directory (for --append-report).
        now: Timestamp override for testing.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    session_maker, engine, owns_engine = _resolve_session_maker(db, session_maker)
    sample_now = now or datetime.now(timezone.utc)

    try:
        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            if progress.calibrate_finished_at is None or progress.screen_floor is None:
                raise CalibrationRequiredError(
                    "legacy-sample refuses to run: calibrate has not finished / "
                    "screen_floor is NULL."
                )
            screen_floor = progress.screen_floor

        async with session_maker() as session:
            legacy_ids = await _collect_legacy_sample_games(
                session, before=LEGACY_CUTOFF, after=None, n=LEGACY_SAMPLE_GAMES
            )
            control_ids = await _collect_legacy_sample_games(
                session, before=None, after=CALIBRATION_CLEAN_AFTER, n=LEGACY_CONTROL_GAMES
            )

        if not legacy_ids or not control_ids:
            raise CalibrationSampleEmptyError(
                "legacy-sample: zero eligible games in the legacy or control cohort -- no verdict."
            )

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            progress.legacy_sample_started_at = sample_now
            await session.commit()

        owns_pool = pool is None
        if pool is None:
            pool = _pool_from_env(pool_size)
            await pool.start()
        try:
            legacy = await _run_legacy_sample_cohort(
                session_maker, pool=pool, game_ids=legacy_ids, screen_floor=screen_floor
            )
            control = await _run_legacy_sample_cohort(
                session_maker, pool=pool, game_ids=control_ids, screen_floor=screen_floor
            )
        finally:
            if owns_pool:
                await pool.stop()

        legacy_rate, control_rate, build = _legacy_sample_decision(legacy, control)
        decision_lines = _format_legacy_sample_decision(
            legacy, control, legacy_rate, control_rate, build
        )
        for line in decision_lines:
            print(line)

        async with session_maker() as session:
            progress = await _ensure_progress_row(session)
            progress.legacy_sample_finished_at = datetime.now(timezone.utc)
            await session.commit()

        if append_report:
            report_path = out_dir / f"opening-cache-repair-{sample_now.strftime('%Y-%m-%d')}.md"
            if report_path.exists():
                with report_path.open("a", encoding="utf-8") as f:
                    f.write("\n" + "\n".join(decision_lines) + "\n")
            else:
                print(f"legacy-sample: --append-report given but {report_path} does not exist.")
    finally:
        if owns_engine and engine is not None:
            await engine.dispose()


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _add_common_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )
    sub.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Report what would happen without writing (default: False).",
    )
    sub.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the number of units processed this run (default: all).",
    )


def _add_pool_size_arg(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--pool-size",
        type=int,
        default=None,
        dest="pool_size",
        metavar="N",
        help=(
            "Stockfish engines to run in parallel for this stage "
            "(default: STOCKFISH_POOL_SIZE env var, else 1)."
        ),
    )


def _add_seed_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "seed", help="Seed opening_cache_audit with one pending row per cache row."
    )
    _add_common_args(sub)


def _add_calibrate_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "calibrate",
        help="Measure screen_floor/confirm_floor from a known-clean sample.",
    )
    _add_pool_size_arg(sub)
    _add_common_args(sub)
    sub.add_argument(
        "--n",
        type=int,
        default=CALIBRATION_DEFAULT_N,
        metavar="N",
        help=f"Target sample size (default: {CALIBRATION_DEFAULT_N}).",
    )


def _add_screen_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "screen",
        help="Depth-15 screen pending audit rows against a hash-asserted carrier board.",
    )
    _add_pool_size_arg(sub)
    _add_common_args(sub)


def _add_orphans_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "orphans",
        help="Mark+delete pending audit rows with no game_positions carrier anywhere.",
    )
    _add_common_args(sub)


def _add_confirm_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "confirm",
        help="1M-node re-evaluate flagged audit rows; overwrite the cache only when confirmed_bad.",
    )
    _add_pool_size_arg(sub)
    _add_common_args(sub)


def _add_propagate_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "propagate",
        help="Rewrite carrier game_positions rows that still hold a confirmed_bad old value.",
    )
    _add_common_args(sub)


def _add_rederive_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "rederive",
        help="Reclassify every pending repaired game through the drain's own classifier.",
    )
    _add_common_args(sub)


def _add_db_arg(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )


def _add_report_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "report",
        help="Read-only: render opening_cache_audit into a committed markdown report.",
    )
    _add_db_arg(sub)
    sub.add_argument(
        "--partial",
        action="store_true",
        default=False,
        help="Skip the rederive_finished_at gate and print a partial-snapshot banner.",
    )


def _add_legacy_sample_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sub = subparsers.add_parser(
        "legacy-sample",
        help="D-07: measure the pre-2026-06-18 legacy cohort's disagreement rate beyond ply 20.",
    )
    _add_pool_size_arg(sub)
    _add_db_arg(sub)
    sub.add_argument(
        "--append-report",
        action="store_true",
        default=False,
        dest="append_report",
        help="Also append the decision block to the dated report file, if one exists.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 220 opening eval cache repair pipeline operator surface."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_seed_subparser(subparsers)
    _add_calibrate_subparser(subparsers)
    _add_screen_subparser(subparsers)
    _add_orphans_subparser(subparsers)
    _add_confirm_subparser(subparsers)
    _add_propagate_subparser(subparsers)
    _add_rederive_subparser(subparsers)
    _add_report_subparser(subparsers)
    _add_legacy_sample_subparser(subparsers)
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


async def _dispatch(args: argparse.Namespace) -> None:
    if args.command == "seed":
        await run_seed(db=args.db, dry_run=args.dry_run, limit=args.limit)
    elif args.command == "calibrate":
        await run_calibrate(
            db=args.db, dry_run=args.dry_run, limit=args.limit, n=args.n, pool_size=args.pool_size
        )
    elif args.command == "screen":
        await run_screen(
            db=args.db, dry_run=args.dry_run, limit=args.limit, pool_size=args.pool_size
        )
    elif args.command == "orphans":
        await run_orphans(db=args.db, dry_run=args.dry_run, limit=args.limit)
    elif args.command == "confirm":
        await run_confirm(
            db=args.db, dry_run=args.dry_run, limit=args.limit, pool_size=args.pool_size
        )
    elif args.command == "propagate":
        await run_propagate(db=args.db, dry_run=args.dry_run, limit=args.limit)
    elif args.command == "rederive":
        await run_rederive(db=args.db, dry_run=args.dry_run, limit=args.limit)
    elif args.command == "report":
        await run_report(db=args.db, partial=args.partial)
    elif args.command == "legacy-sample":
        await run_legacy_sample(
            db=args.db, append_report=args.append_report, pool_size=args.pool_size
        )
    else:  # pragma: no cover — unreachable while argparse enforces a known command set
        raise ValueError(f"Unknown command: {args.command!r}")


def main() -> None:
    args = parse_args()
    asyncio.run(_dispatch(args))


if __name__ == "__main__":
    main()
