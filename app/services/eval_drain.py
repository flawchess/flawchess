"""Cold-lane eval drain coroutine for Phase 91 / SEED-023.

This module owns the in-process background coroutine that evaluates entry plies
for games whose `evals_completed_at IS NULL`. It is the structural fix for the
OOM-kill failure mode described in SEED-022/023 — by moving Stockfish work out
of the hot import lane (which caused 20-40 s held transactions) into this
dedicated background loop with short, well-bounded transactions.

Key architectural invariant:
    asyncio.gather() over engine_service.evaluate() MUST run OUTSIDE any open
    AsyncSession scope. Per CLAUDE.md hard rule: AsyncSession is not safe for
    concurrent use from multiple coroutines, and holding a session open during
    multi-position fan-out is the structural OOM driver.

Session discipline per tick:
    1. _pick_pending_game_ids: short read tx, then CLOSE.
    2. _load_pgns_for_games: short read tx, then CLOSE.
    3. asyncio.gather (no session open).
    4. Write session: open LATE, UPDATEs + commit, CLOSE.

Phase 91 / SEED-023 locks:
    D-09: engine (None, None) marks game complete — no permanent retry loop.
    D-11: LIFO id-DESC pick, batch size 10.
    D-12: no per-user fairness at current scale.
    D-13: idle sleep 5s when queue empty.

Quick 260521-d6o follow-up:
    Target collection is single-walk per game — one chess.pgn.read_game + one
    mainline traversal yields board snapshots at every target ply, instead of
    one parse-and-walk per target ply. Public wrappers
    (_collect_midgame_eval_targets, _collect_endgame_span_eval_targets) keep
    their original signatures for the hot-lane Stage 5c covered-game gate in
    import_service.py:_collect_covered_game_ids.
"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import asyncpg
import sentry_sdk
import sqlalchemy as sa
from sqlalchemy import TextClause, select, text, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker
from app.models.eval_jobs import TIER_BESTMOVE_BACKFILL
from app.models.game import Game
from app.models.game_position import DEDUP_MAX_PLY, GamePosition
from app.models.import_job import ImportJob
from app.models.opening_position_eval import OpeningPositionEval
from app.repositories.game_repository import users_with_zero_pending
from app.schemas.eval_remote import MAX_SUBMIT_EVALS
from app.services import engine as engine_service
from app.services import maia_engine
from app.services import percentile_compute_registry

# Phase 150 R7: the shared write-path primitives physically moved to eval_apply.py.
# Several are re-imported here purely for backward compatibility with existing
# `from app.services.eval_drain import <symbol>` references in tests/scripts (they
# are re-bound names, not re-definitions — the implementation lives in eval_apply.py
# only) — noqa: F401 marks the ones this module's own code does not call directly.
from app.services.eval_apply import (
    MAX_EVAL_ATTEMPTS,  # noqa: F401 — backward-compat re-export (tests)
    _FullPlyEvalTarget,
    _apply_full_eval_results,  # noqa: F401 — backward-compat re-export (tests/scripts)
    _assemble_flaw_blobs_from_submit,  # noqa: F401 — backward-compat re-export (tests)
    _assemble_one_line_blob,  # noqa: F401 — backward-compat re-export (tests)
    _build_best_move_candidates,
    _build_bestmove_lease_positions,
    _build_flaw_blob_lease_positions,  # noqa: F401 — backward-compat re-export (tests/scripts)
    _build_flaw_multipv2_blobs,
    _build_line_blobs,  # noqa: F401 — backward-compat re-export (tests)
    _classify_with_overlay,
    _collect_full_ply_targets,
    _eval_of_position_map,
    _fetch_dedup_evals,
    _mark_best_moves_completed,
    _reconstruct_pos_eval,
    _signal_flaw_completion,
    _stamp_best_moves_completed_directly,
    _upsert_best_move_rows,
    _walk_pv_boards,  # noqa: F401 — backward-compat re-export (scripts)
    apply_full_eval,
)

# Phase 150 R7 Task 2: entry-ply (import-time, no-shift) collection/write/classify
# primitives physically moved to eval_entry.py (none of them open their own session
# -- see eval_entry.py's module docstring). run_eval_drain (below) still needs them;
# _EvalTarget/ENTRY_LEASE_* symbols and several others are re-imported purely for
# backward compatibility with existing `from app.services.eval_drain import <symbol>`
# references in tests/import_service.py.
from app.services.eval_entry import (
    _EvalTarget,  # noqa: F401 — backward-compat re-export (tests/eval_remote.py)
    _apply_eval_results,
    _claim_entry_eval_games,
    _classify_and_insert_flaws,
    _collect_endgame_span_eval_targets,  # noqa: F401 — backward-compat re-export (import_service.py/tests)
    _collect_eval_targets_from_db,
    _collect_midgame_eval_targets,  # noqa: F401 — backward-compat re-export (import_service.py/tests)
    _mark_evals_completed,
)
from app.services.eval_queue_service import WORKER_ID_SERVER_POOL, claim_eval_job
from app.services.eval_utils import (
    derive_is_lichess_eval_game,
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.user_benchmark_percentiles_service import compute_stage_b

logger = logging.getLogger(__name__)

# UAT 2026-05-20 — same broad exception tuple as import_service.py to catch
# all connection-class errors raised by the asyncpg dialect during a
# Postgres restart. Copied verbatim (modulo module context).
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

_DRAIN_BATCH_SIZE = 10  # D-11 (LIFO id-DESC pick size)
_DRAIN_IDLE_SLEEP_SECONDS = 5  # D-13 (poll interval when queue empty)

# Phase 119 WR-04: chunk the resweep_holed_games re-arm UPDATE so the documented
# unbounded "sweep all" prod path can't re-arm the entire holed backlog (~558k
# games) in one IN(...) statement/transaction — that would materialize the full
# id list as bind params (risking the parameter limit) and flip every game back
# into the tier-3 candidate pool simultaneously. Each chunk commits independently;
# the small-N path (count <= this size) is a single statement + single commit,
# behaviorally identical to the pre-batching code.
_RESWEEP_UPDATE_CHUNK_SIZE = 1000

# SEED-139 item 5: the app now runs resweep_holed_games itself once a day (below),
# instead of relying on an operator remembering to run scripts/resweep_holed_games.py.
# 24 hours, expressed the same way as the guest-cleanup analog
# (_GUEST_CLEANUP_INTERVAL_SECONDS, app/services/guest_cleanup_service.py).
_RESWEEP_INTERVAL_SECONDS = 24 * 60 * 60

# D-07: a burst guard on the drain and the volunteer fleet, NOT a correctness
# device — the daily cadence above picks up any remainder next tick. Chosen well
# above _RESWEEP_UPDATE_CHUNK_SIZE so a single day's sweep is rarely chunked.
_RESWEEP_TICK_LIMIT = 5000

# MAX_EVAL_ATTEMPTS moved to eval_apply.py (Phase 150 R7) — apply_completion_decision
# is defined there now. Imported below (re-exported for backward compatibility with
# existing `from app.services.eval_drain import MAX_EVAL_ATTEMPTS` test/script imports).

# Phase 116 EVAL-03 / D-116-02: dedup only in the opening region.
# WR-08: aliased from the model constant (single source of truth) so this
# boundary can never drift from the ply <= N predicate of the
# ix_gp_full_hash_opening partial index — drifting above it would silently
# stop dedup lookups from using the index.
_DEDUP_MAX_PLY: int = DEDUP_MAX_PLY

# SEED-049: under post-move storage, the game-ending move row (ply = max_ply - 1) stores
# the eval of the terminal game-over position, which is legitimately unevaluable. This
# offset defines "the game-ending move sits 1 ply before the maximum stored ply", used
# in the resweep predicate to exclude it from the hole definition (ply < max_ply - 1).
_GAME_ENDING_PLY_OFFSET: int = 1

# ─── Phase 123.1 SEED-053: opening eval cache population gate (single source of truth) ───

# OPENING_CACHE_BACKFILL_SQL is the canonical INSERT…SELECT that populates
# opening_position_eval from our-engine game_positions evals.  It is the single
# source of the cache-population gate, shared by:
#   - scripts/backfill_opening_eval_cache.py  (one-time idempotent backfill), and
#   - tests/services/test_full_eval_drain.py  (gate-equivalence tests for
#     _fetch_dedup_evals — run this SQL before calling _fetch_dedup_evals so the
#     gate is exercised at its actual enforcement site).
#
# Gate predicates:
#   full_evals_completed_at IS NOT NULL — our-engine evals only (D-123.1-03)
#   lichess_evals_at IS NULL            — exclude lichess %eval sources (WR-02 / D-117-07)
#   eval_cp IS NOT NULL OR eval_mate IS NOT NULL — donor row must have an eval
#   nxt.ply <= :dedup_max_ply           — opening region only (D-116-02 / EVAL-03)
# Idempotent: ON CONFLICT (full_hash) DO NOTHING.
#
# SEED-164 diagnosis 3 (Phase 220 CACHEFIX-12): `SELECT DISTINCT ON` with no ORDER
# BY picks an ARBITRARY donor row per position — Postgres is free to return
# whichever candidate its scan happens to visit first. The 2026-06-17 backfill ran
# this SQL unordered and enshrined whatever donor the planner visited first per
# position, some of them stale/wrong-position legacy evals. `ORDER BY
# nxt.full_hash, g.full_evals_completed_at DESC, cur.pv IS NULL` makes the choice
# deterministic: newest-evaluated donor wins, and at equal timestamps a
# pv-bearing donor wins over a pv-less one (`false` sorts before `true`). Do not
# simplify this ordering away — it is the fix, not incidental tidiness.
#
# Phase 220 CACHEFIX-08: the INSERT gains an explicit `confirmed = false` — any
# backfilled row is a candidate (one source: this backfill's own donor row), never
# confirmed. Only the release-2 migration's status-derived marking or a genuine
# second independent game can confirm a row; the backfill itself is exactly the
# kind of single-source write that started the poisoning this phase fixes.
OPENING_CACHE_BACKFILL_SQL: TextClause = text(
    """
    INSERT INTO opening_position_eval (full_hash, eval_cp, eval_mate, best_move, confirmed)
    SELECT DISTINCT ON (nxt.full_hash)
           nxt.full_hash,
           cur.eval_cp,
           cur.eval_mate,
           nxt.best_move,
           false
    FROM   game_positions cur
    JOIN   game_positions nxt
           ON  nxt.game_id = cur.game_id
           AND nxt.ply     = cur.ply + 1
    JOIN   games g
           ON  g.id = cur.game_id
    WHERE  nxt.ply <= :dedup_max_ply
      AND  g.full_evals_completed_at IS NOT NULL
      AND  g.lichess_evals_at IS NULL
      AND  (cur.eval_cp IS NOT NULL OR cur.eval_mate IS NOT NULL)
    ORDER BY nxt.full_hash, g.full_evals_completed_at DESC, cur.pv IS NULL
    ON CONFLICT (full_hash) DO NOTHING
    """
)

# ─── Phase 220 CACHEFIX-08 (D-11/D-12/D-13): two-source confirmation constants ───

# D-11: two-source agreement tolerance in EXPECTED-SCORE units, never a fixed
# centipawn cut — a fixed cp cut is wrong twice over (100cp at +600 changes
# nothing while 55cp at equality is an inaccuracy boundary), the same argument
# SEED-164 makes for the repair's own thresholds. Comparisons always go
# through eval_cp_to_expected_score / eval_mate_to_expected_score
# (app/services/eval_utils.py), never centipawns directly.
#
# Value is the PROD-MEASURED confirm_floor from the Phase 220 repair's
# calibrate stage (p99 of the 1M-node delta against a known-clean stored
# value), rounded UP to a readable precision:
#   confirm_floor = 0.029419322, calibration_n = 500,
#   calibrated 2026-09-10 11:47:37Z, Stockfish 18 (220-06-SUMMARY.md).
# Must be a module constant, never a runtime lookup into
# opening_cache_repair_progress — the app cannot depend on that row existing
# (the benchmark DB, dev, and the test DB all lack it; D-11).
OPENING_CACHE_AGREE_MAX_SCORE_DELTA: float = 0.03

# D-12: how many times a candidate must disagree with a second source before
# Sentry fires — 2, not 1. A p99 floor means roughly 1% of honest second
# sources look like disagreements; over 2.6M positions a per-event signal
# would be ~26k Sentry events for nothing. Two CONSECUTIVE misses on the same
# position is the misalignment signature.
_DISAGREEMENT_SENTRY_THRESHOLD: int = 2

# Phase 220 CACHEFIX-08: process-local memo for the Stockfish version string.
# get_stockfish_version() (app/services/engine.py) opens and quits its own UCI
# connection — calling it on every opening-region cache write (every tick,
# every atomic submit) would open a fresh subprocess connection per write.
# Memoized once per worker process; a mid-process Stockfish upgrade is not
# picked up until restart, which is acceptable (the engine process already
# restarts on every deploy).
_cached_engine_version: str | None = None


async def _get_cached_engine_version() -> str | None:
    """Resolve and memoize the Stockfish version string for this process."""
    global _cached_engine_version
    if _cached_engine_version is None:
        _cached_engine_version = await engine_service.get_stockfish_version()
    return _cached_engine_version


# ─── Phase 123 SEED-051: entry-ply remote-fan-out lease constants (D-03/D-04/D-05) ───

# D-04: short TTL — entry-ply batches are only seconds of work (50 games × 2-3 plies
# × ~90ms ÷ N cores). Must be well under the 120s full-ply LEASE_TTL_SECONDS.
# RESEARCH Pitfall 3 recommends 15–30s; 20s is the midpoint with comfortable margin.
ENTRY_LEASE_TTL_SECONDS: int = 20

# D-5 starting knob: how many games to hand to one remote worker per batch.
# Tune once the worker is live and throughput is measured.
ENTRY_LEASE_BATCH_SIZE: int = 50

# D-5 starting knob: minimum backlog depth before /entry-lease invites remote workers.
# The existence probe uses OFFSET = THRESHOLD - 1 (Pitfall 6: 0-indexed OFFSET).
# Below this depth the server pool handles the tail solo (D-02).
ENTRY_LEASE_BACKLOG_THRESHOLD: int = 300


async def _any_active_import_or_entry_ply_pending(session: AsyncSession) -> bool:
    """True if the full drain should yield to higher-priority work (D-116-11).

    Returns True when:
    (a) any import_job with status IN ('pending', 'in_progress') exists, OR
    (b) any game with evals_completed_at IS NULL exists (entry-ply drain backlog).
    Both checks use existing partial indexes and are sub-millisecond.
    """
    active_import = await session.scalar(
        select(sa.func.count())
        .select_from(ImportJob)
        .where(ImportJob.status.in_(["pending", "in_progress"]))
    )
    if active_import:
        return True
    entry_ply_pending = await session.scalar(
        select(sa.func.count()).select_from(Game).where(Game.evals_completed_at.is_(None)).limit(1)
    )
    return bool(entry_ply_pending)


# ---------------------------------------------------------------------------
# Phase 123 SEED-051: entry-ply lease claim. Physically stays here (Phase 150
# R7 Task 2) rather than moving to eval_entry.py -- it opens its own internal
# session via async_session_maker, and this is the ONLY caller of that binding
# in the entry-ply cold-drain lane; keeping it local avoids adding a second
# module (eval_entry.py) whose own async_session_maker binding every existing
# test/script session-patch would need to learn about, for zero behavioral
# benefit (both _pick_pending_game_ids and _load_pgns_for_games are consumed
# exclusively by run_eval_drain, which also stays in this module).
# ---------------------------------------------------------------------------


async def _pick_pending_game_ids(limit: int) -> list[int]:
    """Open a short read-then-commit session, claim up to *limit* pending game IDs,
    stamp their entry-eval lease, and close.

    D-01 (Phase 123 SEED-051): now a lease claim via _claim_entry_eval_games so the
    server pool and remote workers strictly partition the same import (no double-eval).
    D-11: LIFO by id DESC (newest import first) — unchanged.

    The lease is committed before drain work begins so it is durable before the engine
    gather runs (mirror of claim_eval_job's commit-then-release discipline in
    eval_queue_service.py). The lease ends naturally when _mark_evals_completed stamps
    evals_completed_at; a crash is reclaimed by ENTRY_LEASE_TTL_SECONDS expiry.

    Note: UPDATE … RETURNING does not guarantee row order, so we sort DESC to preserve
    the D-11 LIFO contract for callers (the set of claimed games is correct by SKIP LOCKED;
    only the list ordering needs an explicit sort here).
    """
    async with async_session_maker() as session:
        game_ids = await _claim_entry_eval_games(
            session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS
        )
        await session.commit()
    return sorted(game_ids, reverse=True)


async def _load_pgns_for_games(game_ids: Sequence[int]) -> list[tuple[int, str]]:
    """Open a short session, load (id, pgn) rows for the given game IDs, close."""
    async with async_session_maker() as session:
        result = await session.execute(select(Game.id, Game.pgn).where(Game.id.in_(game_ids)))
        return [(row[0], row[1]) for row in result.all()]


# ---------------------------------------------------------------------------
# Cold-drain coroutine + DB-backed target collection
# ---------------------------------------------------------------------------


async def _eval_drain_tick() -> None:
    """One tick of the cold-lane entry-ply drain.

    Split out of run_eval_drain (SEED-138) to mirror _full_drain_tick, so the
    loop stays thin enough to carry a per-tick Sentry isolation scope and so
    the body stops nesting past CLAUDE.md's hard limit of 4.
    """
    # Step 1: pick batch (short read tx, then close session).
    # D-11: LIFO id-DESC, batch size = _DRAIN_BATCH_SIZE.
    game_ids = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)
    if not game_ids:
        await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        return

    # Step 2: load PGNs (short read tx, then close session).
    game_pgn_rows = await _load_pgns_for_games(game_ids)
    pgn_map = {gid: pgn for gid, pgn in game_pgn_rows}

    # Step 3: load GamePosition metadata and derive eval targets
    # (separate short read session, then close).
    async with async_session_maker() as read_session:
        eval_targets = await _collect_eval_targets_from_db(read_session, game_ids, pgn_map)

    # Step 4: fan out engine evaluations.
    # CLAUDE.md hard rule: asyncio.gather must NEVER run inside an AsyncSession scope
    if eval_targets:
        eval_results: Sequence[tuple[int | None, int | None]] = await asyncio.gather(
            *(engine_service.evaluate(t.board) for t in eval_targets)
        )
    else:
        eval_results = []

    # WR-05 mirror (Phase 148 item 2): when EVERY engine call in a
    # non-empty batch failed, the cause is overwhelmingly a dead
    # engine pool (all workers permanently failed after restart
    # attempts — see the corrected EnginePool docstring in engine.py),
    # not a position problem. Stamping evals_completed_at here would
    # silently convert a transient pool outage into permanent
    # complete-but-unevaluated games. Gate on `eval_targets` non-empty
    # (not `game_ids`) so the legitimate D-09 zero-eval-target case
    # (test_engine_none_marks_complete) still stamps complete — see
    # Pitfall 2 in 148-RESEARCH.md. Leave the lease to expire via its
    # ENTRY_LEASE_TTL_SECONDS TTL (the same reclaim mechanism
    # test_idempotent_on_simulated_crash already relies on) rather
    # than an explicit UPDATE.
    if eval_targets and all(cp is None and mt is None for cp, mt in eval_results):
        sentry_sdk.set_context(
            "eval", {"game_id_count": len(game_ids), "failed_ply_count": len(eval_targets)}
        )
        sentry_sdk.set_tag("source", "eval_drain")
        sentry_sdk.capture_message(
            "entry-drain: all engine evals failed for batch — leaving pending",
            level="warning",
        )
        await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        return

    # Step 5: open session LATE, write all UPDATEs in one short tx.
    # Session opens only AFTER gather completes — write window is <100 ms.
    async with async_session_maker() as session:
        if eval_targets:
            await _apply_eval_results(session, eval_targets, list(eval_results))
        # Phase 108-02 D-10: classify + bulk-insert game_flaws for all
        # just-evaluated games. Runs AFTER _apply_eval_results so eval_cp
        # is available for classification, and BEFORE _mark_evals_completed
        # so flaw rows commit atomically with the eval results (Pitfall 2).
        # Sequential, no asyncio.gather (CLAUDE.md hard rule).
        await _classify_and_insert_flaws(session, game_ids)
        # Mark all picked games done regardless of eval success/failure.
        # engine.evaluate() returning (None, None) is treated as
        # "evaluated — engine failed for this position, leave row NULL"
        # per D-09 / R-02 — no permanent retry loop.
        await _mark_evals_completed(session, game_ids)
        await session.commit()

    # Phase 94.1 D-01 / Pitfall 1: Stage B fires for users whose pending-eval
    # count just transitioned to zero. Group just-drained game_ids by user_id,
    # then in ONE aggregated query (WR-01 fix, 94.1-12) filter to users whose
    # pending-eval count is now zero AND no active import_job exists (Plan 13
    # Stage B gate). Without the active-import guard, Stage B fires multiple
    # times as eval batches drain mid-import, producing transient intermediate
    # values on the chip (user 28 case — see 94.1-13-PLAN.md gap_source).
    # Fresh read session: never share the eval-write session across coroutines.
    async with async_session_maker() as read_session:
        user_id_rows = await read_session.execute(
            select(Game.user_id).distinct().where(Game.id.in_(game_ids))
        )
        affected_user_ids = [row[0] for row in user_id_rows.all()]
        if affected_user_ids:
            zero_pending = await users_with_zero_pending(read_session, affected_user_ids)
            for uid in zero_pending:
                # Quick 260529-015: mark BEFORE scheduling so the 3s
                # readiness poll can't observe pending==0 and unlock Tier 2
                # in the window before compute_stage_b starts writing rows.
                percentile_compute_registry.mark(uid)
                asyncio.create_task(compute_stage_b(uid))


async def run_eval_drain() -> None:
    """Continuously evaluate entry plies for games with evals_completed_at IS NULL.

    Phase 91 / SEED-023: cold-lane drain coroutine.

    Picks _DRAIN_BATCH_SIZE game IDs (LIFO by id DESC, D-11), loads PGNs from DB,
    derives entry-ply targets via GamePosition metadata, fans out asyncio.gather
    OUTSIDE any session scope (CLAUDE.md: AsyncSession not safe for concurrent use),
    then opens a short write-window session for the combined UPDATEs.

    Crash-safe: if the process dies before commit, all picked games remain
    evals_completed_at IS NULL and are re-picked on the next tick. At most a
    few seconds of eval CPU is repeated (idempotent).

    Exception handling (three-tier):
    - asyncio.CancelledError: propagates (lifespan shutdown contract, WR-07).
    - _RETRIABLE_DB_OUTAGE_ERRORS: sleep + continue (Postgres restart mid-tick).
    - Exception: log + capture + continue.

    Wired in app/main.py lifespan alongside run_periodic_reaper.
    """
    while True:
        # SEED-138: per-tick isolation scope -- a background loop must never
        # write to the shared lifespan scope (AsyncioIntegration is not
        # enabled; see app/main.py's create_task comment for why). Encloses
        # the whole try/except: the except clauses below also call
        # set_tag/capture_exception and would otherwise keep leaking.
        with sentry_sdk.isolation_scope():
            try:
                await _eval_drain_tick()
            except asyncio.CancelledError:
                # Lifespan shutdown — propagate without retry (cancellation contract
                # mirrors WR-07 in import_service.py: CancelledError is BaseException,
                # neither except clause below catches it).
                raise
            except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
                # Postgres restart mid-tick: log + short sleep, then re-poll.
                # Games remain evals_completed_at IS NULL and will be re-picked.
                logger.warning("eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS)
                sentry_sdk.set_tag("source", "eval_drain")
                sentry_sdk.capture_exception(exc)
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
            except Exception:
                logger.exception("eval_drain: unexpected error — continuing")
                sentry_sdk.set_tag("source", "eval_drain")
                sentry_sdk.capture_exception()
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)


@dataclass(slots=True)
class _ExistingCacheRow:
    """One opening_position_eval row as read before this batch's writes (Phase 220
    CACHEFIX-08, D-11/D-12/D-13) — the snapshot both the partition decision and the
    optimistic-concurrency WHERE guard in the write helpers are built from."""

    eval_cp: int | None
    eval_mate: int | None
    pv: str | None
    confirmed: bool
    source_game_id: int | None


@dataclass(slots=True)
class _InsertWrite:
    full_hash: int
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None
    pv: str | None


@dataclass(slots=True)
class _PromoteWrite:
    full_hash: int
    pv: str | None
    expected_source: int | None


@dataclass(slots=True)
class _ReplaceWrite:
    full_hash: int
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None
    pv: str | None
    expected_source: int | None
    old_eval_cp: int | None
    old_eval_mate: int | None


@dataclass(slots=True)
class _CacheWriteBuckets:
    """A batch of freshly-computed opening evals, partitioned by what write each one
    needs (Phase 220 CACHEFIX-08). See `_partition_cache_writes`'s docstring for the
    four buckets' meaning."""

    insert: list[_InsertWrite] = field(default_factory=list)
    skip_pv_heal: list[tuple[int, str]] = field(default_factory=list)
    promote: list[_PromoteWrite] = field(default_factory=list)
    replace: list[_ReplaceWrite] = field(default_factory=list)


def _cache_values_agree(
    existing_cp: int | None,
    existing_mate: int | None,
    new_cp: int | None,
    new_mate: int | None,
) -> bool:
    """D-11: two sources agree iff mate/non-mate status matches AND the
    expected-score delta is at or below OPENING_CACHE_AGREE_MAX_SCORE_DELTA — the
    comparison is `<=`, so a delta exactly at the constant promotes (agree_boundary).

    Always measured in expected-score units via eval_cp_to_expected_score /
    eval_mate_to_expected_score with user_color="white" on both sides: the cache is
    keyed by position, not by any user, so "white" is a fixed, arbitrary-but-consistent
    perspective — the delta between two white-perspective scores is identical no
    matter which perspective both sides use, as long as both use the SAME one.
    """
    if (existing_mate is not None) != (new_mate is not None):
        return False
    if existing_mate is not None and new_mate is not None:
        existing_score = eval_mate_to_expected_score(existing_mate, "white")
        new_score = eval_mate_to_expected_score(new_mate, "white")
        return abs(new_score - existing_score) <= OPENING_CACHE_AGREE_MAX_SCORE_DELTA
    if existing_cp is None or new_cp is None:
        return False
    existing_score = eval_cp_to_expected_score(existing_cp, "white")
    new_score = eval_cp_to_expected_score(new_cp, "white")
    return abs(new_score - existing_score) <= OPENING_CACHE_AGREE_MAX_SCORE_DELTA


def _partition_cache_writes(
    cache_rows: list[tuple[int, int | None, int | None, str | None, str | None]],
    existing_by_hash: dict[int, _ExistingCacheRow],
    source_game_id: int,
) -> _CacheWriteBuckets:
    """Partition a batch of freshly-computed opening evals into write buckets
    (Phase 220 CACHEFIX-08, D-11/D-13). Pure — no I/O — split out of
    _upsert_opening_cache so both halves stay under CLAUDE.md's nesting-depth/LOC
    limits.

    insert: no existing row for this full_hash yet — a brand-new candidate.
    skip_pv_heal: existing row is confirmed, OR its source_game_id equals this
        batch's source_game_id (D-13's self-promotion guard — a re-drained or
        resubmitted game is the same source, not a second one). The one permitted
        mutation in either case is filling a NULL pv from this write.
    promote: unconfirmed, a genuinely different source, and the two values agree
        within OPENING_CACHE_AGREE_MAX_SCORE_DELTA — becomes confirmed.
    replace: unconfirmed, a genuinely different source, and the two values disagree
        — the candidate's value is replaced wholesale and disagreements increments.
    """
    buckets = _CacheWriteBuckets()
    for full_hash, cp, mate, bm, pv in cache_rows:
        existing = existing_by_hash.get(full_hash)
        if existing is None:
            buckets.insert.append(_InsertWrite(full_hash, cp, mate, bm, pv))
            continue
        same_source = existing.source_game_id == source_game_id
        if existing.confirmed or same_source:
            if existing.pv is None and pv is not None:
                buckets.skip_pv_heal.append((full_hash, pv))
            continue
        if _cache_values_agree(existing.eval_cp, existing.eval_mate, cp, mate):
            kept_pv = (
                pv
                if existing.pv is None or (pv is not None and len(pv) > len(existing.pv))
                else existing.pv
            )
            buckets.promote.append(_PromoteWrite(full_hash, kept_pv, existing.source_game_id))
        else:
            buckets.replace.append(
                _ReplaceWrite(
                    full_hash,
                    cp,
                    mate,
                    bm,
                    pv,
                    existing.source_game_id,
                    existing.eval_cp,
                    existing.eval_mate,
                )
            )
    return buckets


def _capture_opening_cache_disagreement(
    *,
    full_hash: int,
    old_eval_cp: int | None,
    old_eval_mate: int | None,
    new_eval_cp: int | None,
    new_eval_mate: int | None,
    disagreements: int,
    new_game_id: int,
    previous_game_id: int | None,
) -> None:
    """D-12: fires exactly once per position, on the write that takes
    `disagreements` from 1 to 2 — two CONSECUTIVE misses on the same position, the
    misalignment signature, not the expected ~1% p99-floor rate of a single honest
    disagreement. Fixed message string for Sentry grouping (CLAUDE.md: never embed
    variables in the message); all variable data goes in set_context.
    """
    sentry_sdk.set_context(
        "opening_cache",
        {
            "full_hash": full_hash,
            "old_eval_cp": old_eval_cp,
            "old_eval_mate": old_eval_mate,
            "new_eval_cp": new_eval_cp,
            "new_eval_mate": new_eval_mate,
            "disagreements": disagreements,
            "new_game_id": new_game_id,
            "previous_game_id": previous_game_id,
        },
    )
    sentry_sdk.set_tag("source", "opening-cache")
    sentry_sdk.capture_message(
        "opening-cache: two consecutive evaluations disagreed with the cached value",
        level="warning",
    )


async def _insert_cache_candidates(
    session: AsyncSession,
    rows: list[_InsertWrite],
    source_game_id: int,
) -> None:
    """Batched INSERT ... ON CONFLICT DO NOTHING for brand-new candidate rows
    (Phase 220 CACHEFIX-08 algorithm step 3). DO NOTHING, not a merge: a
    concurrent insert from another game simply wins the race, and this result
    becomes the second source next time this position is reached.

    Uses CAST() instead of :: cast syntax for asyncpg compatibility (same reason
    as _batch_update_eval_rows).
    """
    engine_version = await _get_cached_engine_version()
    params: dict[str, int | str | None] = {
        "engine_version": engine_version,
        "source_game_id": source_game_id,
    }
    values_parts: list[str] = []
    for i, row in enumerate(rows):
        params[f"fh_{i}"] = row.full_hash
        params[f"cp_{i}"] = row.eval_cp
        params[f"mt_{i}"] = row.eval_mate
        params[f"bm_{i}"] = row.best_move
        params[f"pv_{i}"] = row.pv
        values_parts.append(
            f"(CAST(:fh_{i} AS bigint),"
            f" CAST(:cp_{i} AS smallint),"
            f" CAST(:mt_{i} AS smallint),"
            f" CAST(:bm_{i} AS varchar),"
            f" CAST(:pv_{i} AS text),"
            " false, 1, 0,"
            " CAST(:engine_version AS text),"
            " now(),"
            " CAST(:source_game_id AS bigint))"
        )
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        "INSERT INTO opening_position_eval"
        " (full_hash, eval_cp, eval_mate, best_move, pv, confirmed, n_sources,"  # noqa: S608
        "  disagreements, engine_version, written_at, source_game_id)"
        f" VALUES {values_sql}"
        " ON CONFLICT (full_hash) DO NOTHING"
    )
    await session.execute(sql, params)


async def _heal_cache_pv(session: AsyncSession, rows: list[tuple[int, str]]) -> None:
    """Batched pv self-heal: fill a NULL pv from a later write. The one permitted
    mutation of a confirmed (or same-source) row — pre-existing SEED-076 behavior,
    unchanged by CACHEFIX-08's write-path rewrite."""
    params: dict[str, int | str] = {}
    values_parts: list[str] = []
    for i, (fh, pv) in enumerate(rows):
        params[f"fh_{i}"] = fh
        params[f"pv_{i}"] = pv
        values_parts.append(f"(CAST(:fh_{i} AS bigint), CAST(:pv_{i} AS text))")
    values_sql = ", ".join(values_parts)
    await session.execute(
        sa.text(
            "UPDATE opening_position_eval AS o SET pv = v.pv"  # noqa: S608
            f" FROM (VALUES {values_sql}) AS v(full_hash, pv)"
            " WHERE o.full_hash = v.full_hash AND o.pv IS NULL"
        ),
        params,
    )


async def _promote_cache_rows(session: AsyncSession, rows: list[_PromoteWrite]) -> None:
    """Optimistic promote (Phase 220 CACHEFIX-08 algorithm step 4): a candidate
    becomes confirmed only if it is still exactly the row this batch read
    (confirmed = false AND source_game_id IS NOT DISTINCT FROM the snapshot). If
    another lane changed the row in between, the WHERE matches nothing and this
    result is simply not counted. The eval itself is NOT changed on promotion —
    the candidate's own value is the confirmed one."""
    for row in rows:
        await session.execute(
            sa.text(
                "UPDATE opening_position_eval SET confirmed = true, n_sources = 2,"
                " confirmed_at = now(), pv = CAST(:pv AS text)"
                " WHERE full_hash = CAST(:fh AS bigint) AND confirmed = false"
                " AND source_game_id IS NOT DISTINCT FROM CAST(:expected_source AS bigint)"
            ),
            {"pv": row.pv, "fh": row.full_hash, "expected_source": row.expected_source},
        )


async def _replace_cache_rows(
    session: AsyncSession,
    rows: list[_ReplaceWrite],
    source_game_id: int,
) -> None:
    """Optimistic replace (Phase 220 CACHEFIX-08 algorithm step 5): a disagreeing
    candidate's value is replaced wholesale and disagreements incremented, guarded
    the same way as promote. D-12: Sentry fires exactly once, on the write that
    takes disagreements from 1 to 2."""
    engine_version = await _get_cached_engine_version()
    for row in rows:
        result = await session.execute(
            sa.text(
                "UPDATE opening_position_eval SET eval_cp = CAST(:cp AS smallint),"
                " eval_mate = CAST(:mate AS smallint), best_move = CAST(:bm AS varchar),"
                " pv = CAST(:pv AS text), source_game_id = CAST(:gid AS bigint),"
                " written_at = now(), engine_version = CAST(:ver AS text),"
                " disagreements = disagreements + 1"
                " WHERE full_hash = CAST(:fh AS bigint) AND confirmed = false"
                " AND source_game_id IS NOT DISTINCT FROM CAST(:expected_source AS bigint)"
                " RETURNING full_hash, disagreements"
            ),
            {
                "cp": row.eval_cp,
                "mate": row.eval_mate,
                "bm": row.best_move,
                "pv": row.pv,
                "gid": source_game_id,
                "ver": engine_version,
                "fh": row.full_hash,
                "expected_source": row.expected_source,
            },
        )
        written = result.one_or_none()
        if written is not None and written[1] == _DISAGREEMENT_SENTRY_THRESHOLD:
            _capture_opening_cache_disagreement(
                full_hash=written[0],
                old_eval_cp=row.old_eval_cp,
                old_eval_mate=row.old_eval_mate,
                new_eval_cp=row.eval_cp,
                new_eval_mate=row.eval_mate,
                disagreements=written[1],
                new_game_id=source_game_id,
                previous_game_id=row.expected_source,
            )


async def _apply_cache_writes(
    session: AsyncSession,
    buckets: _CacheWriteBuckets,
    source_game_id: int,
) -> None:
    """Execute the partitioned batch's write-bucket statements (Phase 220
    CACHEFIX-08). Split out of _upsert_opening_cache so the caller stays under
    CLAUDE.md's nesting-depth/LOC limits. All statements run inside the caller's
    write transaction — same contract as the pre-CACHEFIX-08 upsert."""
    if buckets.insert:
        await _insert_cache_candidates(session, buckets.insert, source_game_id)
    if buckets.skip_pv_heal:
        await _heal_cache_pv(session, buckets.skip_pv_heal)
    if buckets.promote:
        await _promote_cache_rows(session, buckets.promote)
    if buckets.replace:
        await _replace_cache_rows(session, buckets.replace, source_game_id)


async def _fetch_existing_cache_rows(
    session: AsyncSession, hashes: list[int]
) -> dict[int, _ExistingCacheRow]:
    """Read the current state of every cache row this batch's hashes touch, before
    any write — the snapshot _partition_cache_writes decides against and the write
    helpers' optimistic-concurrency guards are built from."""
    result = await session.execute(
        select(
            OpeningPositionEval.full_hash,
            OpeningPositionEval.eval_cp,
            OpeningPositionEval.eval_mate,
            OpeningPositionEval.pv,
            OpeningPositionEval.confirmed,
            OpeningPositionEval.source_game_id,
        ).where(OpeningPositionEval.full_hash.in_(hashes))
    )
    return {
        row[0]: _ExistingCacheRow(
            eval_cp=row[1],
            eval_mate=row[2],
            pv=row[3],
            confirmed=row[4],
            source_game_id=row[5],
        )
        for row in result.all()
    }


async def _upsert_opening_cache(
    session: AsyncSession,
    engine_targets: list[_FullPlyEvalTarget],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    source_game_id: int,
) -> None:
    """Write freshly-computed opening-region engine evals through the two-source
    confirmation write path (Phase 220 CACHEFIX-08, replacing the former
    first-write-wins upsert — D-01/D-11/D-12/D-13).

    Restricted to the opening region (ply <= _DEDUP_MAX_PLY), non-terminal
    targets, and rows that have a real eval (at least one of eval_cp/eval_mate is
    non-NULL). Excludes dedup transplants (already in the cache; only
    engine_targets are passed in), terminal donors (is_terminal=True; no
    game_positions row, eval is post-move only), and null-eval holes (engine
    failure — nothing to cache).

    A first write for an unseen hash inserts a candidate (confirmed=false,
    n_sources=1). A second, agreeing result from a DIFFERENT game promotes it
    (confirmed=true, n_sources=2). A second, disagreeing result from a different
    game replaces its value and bumps disagreements. A result whose game_id
    equals the candidate's own source_game_id (D-13) neither promotes nor counts
    as a disagreement — the caller passes `source_game_id` for exactly this
    guard. A confirmed row is never overwritten by this path; its only permitted
    mutation is the pre-existing pv self-heal.

    source_game_id: the game this batch's engine results came from — either
    _full_drain_tick's own game_id, or apply_full_eval's game_id parameter for
    the atomic-submit lane (one function, two call sites, threaded through
    apply_full_eval's upsert_opening_cache_fn call — CACHEFIX-12).

    Runs inside the caller's write transaction. If it fails the whole txn rolls
    back and the game is re-picked next tick — acceptable, as the eval writes
    have not committed either. No outer try/except is added (we do not swallow
    cache errors).

    Guard: an empty target list is a no-op — no SQL emitted, not even the
    existing-rows SELECT.
    """
    cache_rows = [
        (t.full_hash, cp, mate, bm, pv)
        for t in engine_targets
        if t.ply <= _DEDUP_MAX_PLY and not t.is_terminal
        for cp, mate, bm, pv in (engine_result_map.get(t.ply, (None, None, None, None)),)
        if cp is not None or mate is not None
    ]
    if not cache_rows:
        return
    # A single game can reach the same position at two different plies (a
    # transposition or repetition), so cache_rows may hold multiple entries with the
    # same full_hash. Postgres rejects INSERT ... ON CONFLICT when two proposed rows
    # share the conflict key ("ON CONFLICT DO UPDATE command cannot affect row a
    # second time" — FLAWCHESS-8E), so collapse duplicates by full_hash here. The
    # eval is identical for a given position; prefer a pv-bearing row so the pv
    # backfill still fires.
    deduped: dict[int, tuple[int, int | None, int | None, str | None, str | None]] = {}
    for row in cache_rows:
        existing = deduped.get(row[0])
        if existing is None or (existing[4] is None and row[4] is not None):
            deduped[row[0]] = row
    cache_rows = list(deduped.values())

    existing_by_hash = await _fetch_existing_cache_rows(session, [row[0] for row in cache_rows])
    buckets = _partition_cache_writes(cache_rows, existing_by_hash, source_game_id)
    await _apply_cache_writes(session, buckets, source_game_id)


async def _missing_flaw_pv_targets(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> list[_FullPlyEvalTarget]:
    """SEED-056: find engine-game flaw plies that took a pv-less opening dedup transplant.

    Lichess-eval games never seed or draw from the opening dedup cache (Phase 174-06 /
    SEED-109: dedup_map is always empty for them), so this gap is engine-games-only —
    the prior lichess pre-classification path (`_flaw_engine_plies`, D-117-13) that used
    to exempt {flaw_ply, flaw_ply + 1} from a NOW-RETIRED targets filter is gone; lichess
    games get every ply engine-evaluated directly instead. Fresh engine games can't
    pre-classify like that anyway — they have no evals until AFTER the gather — so an
    opening-region flaw ply whose full_hash matched a dedup donor gets an eval-only
    transplant with NO pv. The flaw is registered but un-taggable (no refutation line for
    the SEED-039 motif classifier), and the better-alternative PV at flaw_ply is lost too.

    Fix: once the gather is done we DO know every ply's eval (engine_result_map for
    engine plies, dedup_map for transplanted ones). Reconstruct the post-move evals
    in-memory, classify, and return the dedup-transplanted {flaw_ply, flaw_ply + 1}
    targets that still lack a pv. The caller runs a tiny second engine gather on these
    boards and merges the results back into engine_result_map before the write session,
    so classify + the PV write pick the pv up exactly as for any engine-evaluated ply.

    Returns [] when the game has no flaws, no eval coverage, or no pv-less opening flaw
    plies — the common case (the prod gap is ~0.3% of opening-region engine-game flaws).
    """
    # R4: overlay=True — reconstructed post-move evals fill the NULL evals still in
    # the DB at this point (engine games have no eval written until the write
    # session runs).
    pos_eval = _reconstruct_pos_eval(targets, dedup_map, engine_result_map)
    async with async_session_maker() as session:
        flaw_result = await _classify_with_overlay(
            game_id, session, overlay=True, pos_eval=pos_eval
        )
    if flaw_result is None:
        return []

    targets_by_ply = {t.ply: t for t in targets}
    need: dict[int, _FullPlyEvalTarget] = {}
    for flaw in flaw_result:
        flaw_ply_val: int = flaw["ply"]
        for cand_ply in (flaw_ply_val, flaw_ply_val + 1):
            if cand_ply in need:
                continue
            engine_entry = engine_result_map.get(cand_ply)
            if engine_entry is not None and engine_entry[3] is not None:
                continue  # already engine-evaluated with a pv
            target = targets_by_ply.get(cand_ply)
            if target is None or target.is_terminal:
                continue
            # Only the opening dedup region is in scope: a transplanted ply has its eval
            # but no pv. Engine-region flaw plies always get a real pass already, and an
            # engine HOLE (eval failed) would just fail the re-pass too — out of scope.
            if cand_ply <= _DEDUP_MAX_PLY and target.full_hash in dedup_map:
                need[cand_ply] = target
    return list(need.values())


async def _fill_engine_game_flaw_pvs(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    """SEED-056: targeted second engine pass for pv-less opening flaw plies (engine games).

    Engine games can't pre-know their flaws (no evals until after the gather), so an
    opening-region flaw ply that matched a dedup donor took an eval-only transplant with
    NO pv — registered but un-taggable. This classifies from the in-memory gather results,
    finds those pv-less flaw plies, runs ONE more gather over just their boards, and merges
    the pv back into engine_result_map (mutated in place) so the write-session classify
    (tactic tagging) and the pv write pick it up like any engine-evaluated ply.

    No-op for lichess games (Phase 174-06: they get every ply engine-evaluated directly —
    dedup_map is always empty for them, so there is never a dedup transplant to recover a
    pv from) and when there were no opening dedup hits (no possible gap). MUST be called
    with NO session open — it runs asyncio.gather (CLAUDE.md hard rule).
    """
    if is_lichess_eval_game:
        return
    has_opening_dedup = any(
        not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map for t in targets
    )
    if not has_opening_dedup:
        return
    pv_gap_targets = await _missing_flaw_pv_targets(game_id, targets, dedup_map, engine_result_map)
    if not pv_gap_targets:
        return
    # Phase 142: switch to evaluate_nodes_multipv2 so the PV-recovery pass also returns
    # multipv=2 data. Slice to 4-tuple before writing to engine_result_map (which is keyed
    # as dict[int, tuple[...*4]] to avoid blast radius on _apply_full_eval_results).
    pv_gap_results: Sequence[
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]
    ] = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in pv_gap_targets)
    )
    for t, res in zip(pv_gap_targets, pv_gap_results, strict=True):
        # Only merge a real pv — a failed re-pass (pv None) leaves the status quo (eval
        # still served from the dedup transplant; pv stays NULL).
        if res[3] is not None:
            engine_result_map[t.ply] = (res[0], res[1], res[2], res[3])


async def _fill_engine_game_flaw_second_best(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    second_best_map: dict[int, tuple[int | None, int | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    """D-05 / Phase 142 MPV-02: recover node-0 second-best for flaw plies that used
    the opening dedup cache (no engine second-best in second_best_map for those plies).

    Mirrors _fill_engine_game_flaw_pvs (SEED-056): no-op for lichess games and when
    there is no opening dedup. Reuses _missing_flaw_pv_targets to find the same
    dedup-transplanted flaw plies. Mutates second_best_map in place. MUST be called
    with NO session open — runs asyncio.gather (CLAUDE.md hard rule).
    """
    if is_lichess_eval_game:
        return
    has_opening_dedup = any(
        not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map for t in targets
    )
    if not has_opening_dedup:
        return
    # Find flaw-ply targets in the dedup region — the same set as pv-less gap targets.
    gap_targets = await _missing_flaw_pv_targets(game_id, targets, dedup_map, engine_result_map)
    if not gap_targets:
        return
    # Only recover plies still absent from second_best_map (avoid redundant engine calls).
    missing = [t for t in gap_targets if t.ply not in second_best_map]
    if not missing:
        return
    gap_results: Sequence[
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]
    ] = await asyncio.gather(*(engine_service.evaluate_nodes_multipv2(t.board) for t in missing))
    for t, res in zip(missing, gap_results, strict=True):
        second_cp, second_mate, second_uci = res[4], res[5], res[6]
        # Include valid second-best data only (not engine failure). second_uci is str
        # when the engine ran: "" = single-legal-move sentinel, non-empty = real second move.
        if second_cp is not None or second_uci is not None:
            second_best_map[t.ply] = (second_cp, second_mate, second_uci)


def _log_path_c_capacity_reached(
    game_id: int, failed_ply_count: int, new_attempts: int, source: str
) -> None:
    """Path-C reporting for the in-process drain tick (R1).

    Deliberately logger.warning, not a Sentry event: an earlier per-tick Sentry
    capture on this expected cap-path outcome burned the error quota for no
    signal (FLAWCHESS-5V). `source` is accepted for signature parity with the
    router's callback but not embedded in the log message here.
    """
    _ = source
    logger.warning(
        "full_eval_drain: stamping complete after MAX_EVAL_ATTEMPTS with residual "
        "holes (game_id=%s hole_count=%s attempts=%s)",
        game_id,
        failed_ply_count,
        new_attempts,
    )


async def _tier4b_minimal_drain_tick(game_id: int, user_id: int) -> bool:
    """Phase 177 D-05: minimal candidate-only drain path for a TIER_BESTMOVE_BACKFILL
    claim — fixes the documented `_ = tier` no-op (177-RESEARCH.md Pitfall 3).

    `claim_eval_job` has already selected `game_id` via `_claim_tier4_bestmove`
    (`_full_drain_tick`'s Step 1); this function does the rest of the tier-4b work
    in-process, reusing the SAME reconstruction + candidate/writer primitives the
    dedicated `POST /bestmove-lease` + `POST /bestmove-submit` endpoint pair uses
    (Plan 02) — never the full every-ply MultiPV-2 gather + `apply_full_eval`
    reclassify below (that would re-evaluate and re-classify an already-analyzed
    game from scratch for zero benefit).

    Flow (mirrors bestmove_lease + bestmove_submit, minus the HTTP round-trip):
    1. `_build_bestmove_lease_positions` — server-recomputed candidate-ply FENs
       (out-of-book, played == stored `game_positions.best_move`), no engine
       calls (mirrors `/bestmove-lease` Step 3).
    2. Zero candidates OR over `MAX_SUBMIT_EVALS`: stamp `best_moves_completed_at`
       directly (Pitfall 2 forward-progress) and return True — the game IS
       processed (claimed + terminated), never re-drawn by the ES lottery
       (mirrors `/bestmove-lease` Step 4).
    3. Otherwise rebuild `targets` + the inverse-shift `engine_result_map`
       (Pitfall 1) via the SAME primitives `_apply_bestmove_submit` uses (D-03:
       lease and submit — and this local variant — reconstruct from the
       identical stored source of truth, so candidate sets structurally agree),
       then run the targeted MultiPV-2 runner-up search for EXACTLY the leased
       candidate plies — ONE `asyncio.gather`, NO session open (CLAUDE.md hard
       rule). This is the N-search work a worker would do between
       `/bestmove-lease` and `/bestmove-submit`, executed here in-process on
       the server pool instead.
    4. Delegate to `_build_best_move_candidates` (reused verbatim — the margin
       gate + pinned-ELO Maia scoring are NOT re-derived here) with
       `source='drain-local'` (D-06) so a residual Pitfall-1 fallback here is
       Sentry-distinguishable from the worker-submit-path regression signal.
    5. Write session (opened LATE): UPSERT `game_best_moves` rows + stamp
       `best_moves_completed_at` IFF `maia_engine.is_maia_available()`
       (Phase 176 D-01 guardrail — a Maia-absent backend must never stamp,
       since `_build_best_move_candidates` returns `[]` for BOTH "Maia ran,
       zero candidates" and "Maia absent"; row count alone cannot
       distinguish them) + commit. Nothing else — no `apply_full_eval`, no
       reclassify; `game_flaws` is never read or written (S-06/D-02
       isolation, T-177-10).

    `user_id` is accepted for signature parity with the caller's already-claimed
    `(game_id, user_id)` pair; `game_best_moves` rows are keyed on
    `(game_id, ply)` only, so it is otherwise unused here.
    """
    _ = user_id

    positions = await _build_bestmove_lease_positions(game_id)
    if not positions or len(positions) > MAX_SUBMIT_EVALS:
        await _stamp_best_moves_completed_directly(game_id)
        return True

    # Rebuild the SAME targets + inverse-shift engine_result_map
    # _apply_bestmove_submit builds (Pitfall 1) — short read session, CLOSED
    # before any engine work.
    async with async_session_maker() as read_session:
        game = await read_session.scalar(select(Game).where(Game.id == game_id))
        if game is None:
            # Game deleted between claim and this read — nothing to do.
            return False
        pgn_text: str = game.pgn
        # Quick 260719-fsz: needed for the divergence-guard-parity override below.
        # Phase 212 D-03: routed through the single derivation point so
        # BENCHMARK_HOMOGENIZE_EVAL_SOURCE can force this False everywhere.
        is_lichess_eval_game = derive_is_lichess_eval_game(game.lichess_evals_at)
        gp_result = await read_session.execute(
            select(
                GamePosition.ply,
                GamePosition.best_move,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(
                GamePosition.game_id == game_id,
                GamePosition.user_id == game.user_id,
            )
        )
        gp_rows = gp_result.all()
    # read_session closed.

    stored_best_move_by_ply: dict[int, str | None] = {r.ply: r.best_move for r in gp_rows}
    eval_of_position = _eval_of_position_map([(r.ply, r.eval_cp, r.eval_mate) for r in gp_rows])
    gp_full_rows: list[tuple[int, int, int | None, int | None]] = [
        (r.ply, 0, r.eval_cp, r.eval_mate) for r in gp_rows
    ]
    targets = _collect_full_ply_targets(
        game_id=game_id,
        pgn_text=pgn_text,
        game_positions_rows=gp_full_rows,
        include_terminal=False,
        stored_best_move_by_ply=stored_best_move_by_ply,
    )
    if not targets:
        return False

    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {
        t.ply: (
            *eval_of_position.get(t.ply, (None, None)),
            stored_best_move_by_ply.get(t.ply),
            None,
        )
        for t in targets
    }

    # Targeted MultiPV-2 runner-up search for EXACTLY the leased candidate
    # plies — ONE asyncio.gather, NO session open (CLAUDE.md hard rule).
    targets_by_ply = {t.ply: t for t in targets}
    search_targets = [targets_by_ply[p.ply] for p in positions if p.ply in targets_by_ply]
    if not search_targets:
        await _stamp_best_moves_completed_directly(game_id)
        return True

    search_results: Sequence[
        tuple[
            int | None,
            int | None,
            str | None,
            str | None,
            int | None,
            int | None,
            str | None,
        ]
    ] = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in search_targets)
    )
    # Mirrors the main tick's second_best_map population (line ~816 below): only a
    # real runner-up result is recorded, so a fully-failed search leaves the ply
    # absent and lets _build_best_move_candidates's own Pitfall-1 fallback recover
    # it (tagged source='drain-local' below, D-06).
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {}
    for t, res in zip(search_targets, search_results, strict=True):
        second_cp, second_mate, second_uci = res[4], res[5], res[6]
        if second_cp is not None or second_uci is not None:
            second_best_map[t.ply] = (second_cp, second_mate, second_uci)

    # Quick 260719-fsz — divergence-guard parity. For a lichess-eval game the
    # engine_result_map best_cp/best_mate came from game_positions.eval_cp, which
    # holds LICHESS %eval (the full_pv pass preserves it, eval_apply.py:607-629),
    # NOT our Stockfish. The query-time gem/great divergence guard
    # (library_service.py:246-261) compares that stored best_cp against
    # post_move_cp = game_positions.eval_cp — both lichess → the guard would never
    # fire (over-badging) and would mix units in the C2 margin. Override best_cp/
    # best_mate from the fresh white-perspective MultiPV-2 search (res[0]/res[1],
    # same convention as second_cp = res[4]/res[5] above), matching the
    # atomic-submit path (eval_remote.py:1158). Keep the stored best_move (index 2)
    # as the identity key so _build_best_move_candidates's played==best test is
    # unchanged. Engine games are left untouched (their stored eval IS our
    # Stockfish). Residual edge: a candidate ply absent from search_targets keeps
    # its lichess best_cp via the builder's own Pitfall-1 fallback
    # (source='drain-local'); lease candidates ⊇ builder candidates by
    # construction, so this is not expected to fire.
    if is_lichess_eval_game:
        for t, res in zip(search_targets, search_results, strict=True):
            engine_result_map[t.ply] = (
                res[0],
                res[1],
                stored_best_move_by_ply.get(t.ply),
                None,
            )

    # Candidate/writer path — reused verbatim (D-05); source='drain-local' tags
    # a residual Pitfall-1 fallback so it is queryable apart from the
    # worker-submit-fallback regression signal (D-06).
    best_move_rows = await _build_best_move_candidates(
        game_id, targets, engine_result_map, second_best_map, source="drain-local"
    )

    # Phase 176 D-01 guardrail (apply_completion_decision's maia_available param):
    # best_moves_completed_at is stamped ONLY when a Maia session was actually
    # loaded — never inferred from best_move_rows being empty/non-empty, since
    # _build_best_move_candidates returns [] for BOTH "Maia ran, zero
    # candidates" and "Maia absent" (row count alone cannot distinguish them).
    # A Maia-absent backend must never stamp, or the game would be permanently
    # excluded from the tier-4b lottery with zero best-move rows.
    maia_available = maia_engine.is_maia_available()

    # Write session — open LATE, UPSERT rows + stamp (iff Maia was available) +
    # commit. Nothing else.
    async with async_session_maker() as write_session:
        await _upsert_best_move_rows(write_session, best_move_rows)
        if maia_available:
            await _mark_best_moves_completed(write_session, game_id)
        await write_session.commit()

    return True


async def _full_drain_tick() -> bool:
    """Run ONE full-drain tick: yield gate, queue claim, collect, dedup, gather, write.

    Returns True when a game was processed and marked complete; False when the
    tick did nothing (yield gate active, or no pending non-guest game) or the
    all-fail circuit breaker tripped (WR-05 — game stays pending for retry).

    Extracted from run_full_eval_drain (WR-07) so tests can drive exactly one
    tick deterministically — no wall-clock sleeps, no loop cancellation.

    Session discipline (CLAUDE.md hard rule: AsyncSession not safe for concurrent use):
      Step 0: yield gate — short read tx, close.
      Step 1: claim_eval_job — tier-1 > tier-3 derived (queue service owns sessions).
      Step 2: load PGN + game_positions rows — short read tx, close.
      Step 3: asyncio.gather(evaluate_nodes_multipv2) with NO session open.
      Step 4: write session (open LATE): UPDATEs + classify + oracle + markers + commit, close.
      Step 5: _signal_flaw_completion — lightweight hook (no session, Phase 117 stub).
    """
    # Step 0: yield gate (D-116-11).
    # Short read session to check active import or entry-ply backlog.
    async with async_session_maker() as gate_session:
        should_yield = await _any_active_import_or_entry_ply_pending(gate_session)
    if should_yield:
        return False

    # Step 1: claim ONE game via the tiered priority queue (Phase 117 QUEUE-01/02/05).
    # Replaces the LIFO id-DESC interim pick (D-116-09). claim_eval_job owns its
    # sessions internally and commits before returning — the SKIP LOCKED lease is
    # released on that commit (Pitfall 1 in RESEARCH §Common Pitfalls).
    claimed = await claim_eval_job(worker_id=WORKER_ID_SERVER_POOL)
    if claimed is None:
        return False

    game_id: int = claimed.game_id
    user_id: int = claimed.user_id
    tier: int = claimed.tier
    is_lichess_eval_game: bool = claimed.is_lichess_eval_game
    job_id: int | None = claimed.job_id

    # Phase 177 D-05: a TIER_BESTMOVE_BACKFILL claim takes the minimal
    # candidate-only path — never the full every-ply gather + apply_full_eval
    # reclassify below (fixes the documented `_ = tier` no-op, Pitfall 3).
    if tier == TIER_BESTMOVE_BACKFILL:
        return await _tier4b_minimal_drain_tick(game_id, user_id)

    # Step 2: load PGN + game_positions rows for this game.
    # Build targets via _collect_full_ply_targets; partition dedup candidates.
    # Also load full_eval_attempts (SEED-045: threaded here to avoid an extra
    # round-trip inside the write session).
    # Short read session, then close.
    async with async_session_maker() as load_session:
        pgn_result = await load_session.execute(
            select(Game.pgn, Game.full_eval_attempts).where(Game.id == game_id)
        )
        pgn_row = pgn_result.one_or_none()
        if pgn_row is None:
            # Game deleted between claim and load — nothing to do.
            return False
        pgn_text: str = pgn_row[0]
        current_attempts: int = pgn_row[1]

        pos_result = await load_session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(GamePosition.game_id == game_id)
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]

        # Collect one target per ply (EVAL-01). Engine games also get a terminal
        # eval-donor (SEED-044): under post-move storage the last move's stored
        # eval is the eval of the post-game position. Lichess games preserve their
        # %evals (never shifted), so they need no terminal donor.
        targets = _collect_full_ply_targets(
            game_id, pgn_text, gp_rows, include_terminal=not is_lichess_eval_game
        )

        # Phase 174-06 (SEED-109 Option C): the former is_lichess_eval_game targets
        # filter (WR-01/D-117-13) is RETIRED. Lichess-eval games now get the SAME
        # full-ply MultiPV-2 pass as any engine game — every non-terminal ply is
        # engine-evaluated, not just eval-holes + flaw-adjacent plies. That is what
        # lets _build_best_move_candidates nominate every out-of-book played==best
        # ply (174-VERIFICATION Truth 2), not just the flaw-adjacent subset the old
        # filter left visible. The write path still preserves the stored lichess
        # %evals unchanged (is_lichess_eval_game=True stays the apply_full_eval
        # argument below) — only best_move/PV are now written for every ply the
        # engine covers.
        #
        # Partition opening-region hashes for dedup (EVAL-03). Lichess-eval games
        # NEVER seed or draw from the opening dedup cache (their %evals are the DB's
        # permanent, authoritative provenance — never an engine value, and never
        # donated to the cache either — SEED-109 item 4): dedup_hashes is empty for
        # them, so every ply below falls through to a real engine pass instead of a
        # pv-less dedup transplant.
        dedup_hashes = (
            []
            if is_lichess_eval_game
            else [t.full_hash for t in targets if t.ply <= _DEDUP_MAX_PLY and not t.is_terminal]
        )
        dedup_map = await _fetch_dedup_evals(load_session, dedup_hashes)
    # load_session is now closed.

    # Step 3: asyncio.gather — NO session open.
    # CLAUDE.md hard rule: gather must never run inside an AsyncSession scope.
    # Targets with a dedup hit skip the engine call (EVAL-03).
    # Phase 117 EVAL-04 / Phase 142 D-01: use evaluate_nodes_multipv2 so the
    # whole-game per-ply pass becomes multipv=2 (capturing second-best per ply).
    # Tier-1 (QUEUE-03): fan ALL of one game's plies across the pool simultaneously.
    # Tiers 2/3: same gather — the distinction is how the game was claimed, not how it's analyzed.
    # The terminal eval-donor (SEED-044) is always engine-evaluated: it has no
    # full_hash in the dedup map and supplies the last move's after-eval.
    # Phase 174-06: dedup_map is always empty for lichess-eval games (above), so
    # every one of their non-terminal plies falls through to a real engine call
    # here too — the full-ply MultiPV-2 pass SEED-109 requires.
    engine_targets = [
        t
        for t in targets
        if t.is_terminal or t.ply > _DEDUP_MAX_PLY or t.full_hash not in dedup_map
    ]
    if engine_targets:
        engine_results_raw: Sequence[
            tuple[
                int | None,
                int | None,
                str | None,
                str | None,
                int | None,
                int | None,
                str | None,
            ]
        ] = await asyncio.gather(
            *(engine_service.evaluate_nodes_multipv2(t.board) for t in engine_targets)
        )
    else:
        engine_results_raw = []

    # WR-05 circuit breaker: when EVERY engine call for the game failed, the
    # cause is overwhelmingly an engine-pool problem (e.g. all workers
    # permanently dead after failed restarts), not a position problem. Marking
    # the game complete would convert a transient outage into permanent,
    # silent loss of full-eval coverage across the whole backlog at maximum
    # loop speed. Leave the game pending (re-picked next tick) and report ONE
    # Sentry event. Per-position holes remain mark-and-continue per D-116-07.
    if engine_targets and all(
        cp is None and mt is None for cp, mt, _bm, _pv, _scp, _smt, _suci in engine_results_raw
    ):
        sentry_sdk.set_context(
            "eval", {"game_id": game_id, "failed_ply_count": len(engine_targets)}
        )
        sentry_sdk.set_tag("source", "full_eval_drain")
        sentry_sdk.capture_message(
            "full-drain: all engine evals failed for game — leaving pending", level="warning"
        )
        return False

    # Build engine_result_map (4-tuple, unchanged downstream signature) and a parallel
    # second_best_map from the 7-tuple gather results. engine_result_map keeps its existing
    # 4-tuple shape so _apply_full_eval_results / _classify_and_fill_oracle are UNCHANGED
    # (minimal blast radius, Open Question #2 resolution). second_best_map carries the
    # second-best data and is passed only to _build_flaw_multipv2_blobs.
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {}
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {}
    for t, res in zip(engine_targets, engine_results_raw, strict=True):
        engine_result_map[t.ply] = (res[0], res[1], res[2], res[3])
        second_cp, second_mate, second_uci = res[4], res[5], res[6]
        # Include valid second-best data only (not engine failure). second_uci is str
        # when the engine ran: "" = single-legal-move sentinel (Pitfall 3), non-empty = second move.
        if second_cp is not None or second_uci is not None:
            second_best_map[t.ply] = (second_cp, second_mate, second_uci)

    # Step 3b (SEED-056): recover pv for engine-game opening flaw plies that took a
    # pv-less dedup transplant. Runs another gather internally — still NO session open
    # (CLAUDE.md hard rule). Mutates engine_result_map in place; no-op for lichess games.
    await _fill_engine_game_flaw_pvs(
        game_id, targets, dedup_map, engine_result_map, is_lichess_eval_game
    )

    # Step 3c (D-05 / Phase 142 MPV-02): recover node-0 second-best for flaw plies that
    # used the opening dedup cache (their evals came from the dedup transplant and thus
    # have no entry in second_best_map). Mutates second_best_map in place. Still NO
    # session open (CLAUDE.md hard rule).
    await _fill_engine_game_flaw_second_best(
        game_id, targets, dedup_map, engine_result_map, second_best_map, is_lichess_eval_game
    )

    # Step 3d (Phase 142 MPV-02): build PvNode blobs for each flaw's allowed/missed lines.
    # Opens its own read session (closes before gather), then runs ONE asyncio.gather for
    # all continuation nodes — all before the write session opens (CLAUDE.md hard rule).
    flaw_pv_blobs = await _build_flaw_multipv2_blobs(
        game_id, targets, dedup_map, engine_result_map, second_best_map
    )

    # Step 3e (Phase 174 GEMS-03): build best-move candidate rows. The local lane
    # already has per-ply second-best in second_best_map (whole-game MultiPV-2 pass),
    # so the Pitfall-1 fallback rarely fires here. Opens its own short read session
    # for rating metadata and closes it before Maia inference — still NO write
    # session open (CLAUDE.md hard rule). Rows are UPSERTed inside apply_full_eval's
    # write session so they commit atomically with the eval.
    best_move_rows = await _build_best_move_candidates(
        game_id, targets, engine_result_map, second_best_map
    )

    # Step 4: write session — open LATE, after gather completes.
    # All UPDATEs, classify hook, oracle counts, markers, and job report in one transaction.
    #
    # Phase 119 SEED-045 hole-aware completion logic:
    #   failed_ply_count from _apply_full_eval_results = count of non-terminal engine-game
    #   plies where BOTH eval_cp IS NULL AND eval_mate IS NULL after the tick (holes).
    #   Mate-scored plies (eval_mate IS NOT NULL) and terminal donors are NOT counted.
    #
    # Phase 150 R7: the write-session body (evals -> classify/oracle/diff-upsert ->
    # opening-cache fill -> Path A/B/C completion decision) is now the single shared
    # eval_apply.apply_full_eval(...), also called by the router's atomic-submit
    # wrapper (eval_remote.py). This function still owns session lifecycle (mirrors
    # apply_completion_decision's pre-existing convention) so async_session_maker
    # test monkeypatches on THIS module continue to route correctly.
    async with async_session_maker() as write_session:
        failed_ply_count, stamp_complete, _flaws_written = await apply_full_eval(
            write_session,
            game_id=game_id,
            job_id=job_id,
            targets=targets,
            dedup_map=dedup_map,
            engine_result_map=engine_result_map,
            is_lichess_eval_game=is_lichess_eval_game,
            flaw_pv_blobs=flaw_pv_blobs,
            current_attempts=current_attempts,
            source="full_eval_drain",
            on_path_c_capacity_reached=_log_path_c_capacity_reached,
            # SEED-075: blobs_pending=True mirrors the atomic go-forward path
            # (eval_remote.py atomic-submit). Without it the local drain defaulted to
            # False and re-minted raw ungated cp-based tactic tags for any flaw whose
            # continuation blob was NOT assembled into flaw_pv_blobs this pass
            # (flaw_ply absent from the dict, pre_flaw_eval_cp present) — the exact
            # Phase 147 strict-zero violation. It has ZERO effect on flaws that DID
            # get a blob (the gate runs on pv_blob directly) and on the D-06
            # []-sentinel / mate-adjacent FINAL cases.
            blobs_pending=True,
            # SEED-053 / D-123.1-04: fill the opening-eval cache with freshly-computed
            # misses. Phase 220 CACHEFIX-12: the atomic-submit lane (eval_remote.py)
            # now populates the cache too, through this SAME _upsert_opening_cache
            # (one function, two call sites).
            #
            # Phase 220 (SEED-164 / this phase): guarded on `not is_lichess_eval_game`.
            # Before this fix, dedup_hashes is always [] for a lichess-eval game (see
            # the partition comment above), so EVERY one of its non-terminal opening
            # plies lands in engine_targets and was being donated to the cache — which
            # contradicts the invariant that same partition comment already states
            # (SEED-109 item 4: lichess games neither seed nor draw from the cache).
            # The donated values were genuine engine results on hash-asserted boards
            # (not misaligned/poisoned), so this was a provenance-rule violation, not
            # a poison source — counted in the CACHEFIX-07 report.
            update_opening_cache=not is_lichess_eval_game,
            upsert_opening_cache_fn=_upsert_opening_cache,
            engine_targets_for_cache=[] if is_lichess_eval_game else engine_targets,
            best_move_rows=best_move_rows,
        )

        await write_session.commit()

    if not stamp_complete:
        # Path B: game is left pending — not a processed game by the WR-07 contract.
        return False

    # Step 5: per-user cache-completion signal (D-117-11 — no-op stub in Phase 117).
    # Runs AFTER commit so the signal never fires for a partially-committed game.
    _signal_flaw_completion(user_id)

    return True


async def run_full_eval_drain() -> None:
    """Continuously evaluate all non-terminal plies for games with full_evals_completed_at IS NULL.

    Phase 116 EVAL-01/EVAL-02/EVAL-03/EVAL-05 / D-116-08.

    Thin loop over _full_drain_tick (WR-07): sleeps _DRAIN_IDLE_SLEEP_SECONDS
    whenever the tick processed nothing (yield gate active or queue empty),
    loops immediately after a processed game.

    D-116-09: LIFO id-DESC interim pick (replaced by queue in Phase 117).
    D-116-10: guest filter — WHERE NOT users.is_guest.
    D-116-11: yield gate — sleep if active import OR entry-ply drain has backlog.

    Exception handling (three-tier mirrors run_eval_drain):
    - asyncio.CancelledError: propagates (lifespan shutdown contract).
    - _RETRIABLE_DB_OUTAGE_ERRORS: sleep + continue (Postgres restart mid-tick).
    - Exception: log + capture + continue.

    Wired in app/main.py lifespan as full-eval-drain alongside the entry-ply drain.
    """
    while True:
        # SEED-138: per-tick isolation scope -- a background loop must never
        # write to the shared lifespan scope (AsyncioIntegration is not
        # enabled; see app/main.py's create_task comment for why). Encloses
        # the whole try/except: the except clauses below also call
        # set_tag/capture_exception and would otherwise keep leaking.
        with sentry_sdk.isolation_scope():
            try:
                processed = await _full_drain_tick()
                if not processed:
                    await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)

            except asyncio.CancelledError:
                raise
            except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
                logger.warning(
                    "full_eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS
                )
                sentry_sdk.set_tag("source", "full_eval_drain")
                sentry_sdk.capture_exception(exc)
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
            except Exception:
                logger.exception("full_eval_drain: unexpected error — continuing")
                sentry_sdk.set_tag("source", "full_eval_drain")
                sentry_sdk.capture_exception()
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)


async def resweep_holed_games(
    limit: int | None = None,
    dry_run: bool = False,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Re-arm already-stamped engine games that still carry non-terminal holes (SEED-045).

    Permanent re-arm tool for Path-C mid-game holes — NOT pre-Phase-119 legacy.
    `apply_completion_decision` (`eval_apply.py`, Path C) deliberately stamps a game's
    completion markers when `current_attempts + 1 >= MAX_EVAL_ATTEMPTS`, even though
    `failed_ply_count > 0` — this is the EXPECTED terminal state of the bounded-retry
    drain, not a bug (see that function's own docstring). A weak or slow remote worker
    that repeatedly fails the same plies recreates this holed-stamped population
    go-forward — there is no population-exhaustion date. This sweep clears the
    completion markers for such games so the drain re-picks them with a fresh
    MAX_EVAL_ATTEMPTS budget. (Historical note: before Phase 119 introduced the
    bounded-retry Path A/B/C decision tree, the drain stamped unconditionally with no
    retry budget at all — D-116-07 — so this tool's original 2026 motivation was
    cleaning up that one-time backlog. The tool has remained load-bearing ever since
    as the only way to re-arm Path-C-stamped holes.)

    SEED-139 item 5: no longer manual-only. `run_periodic_holed_game_resweep` (below)
    now also calls this function once a day, in-process, so a game that still ends up
    holed is repaired without an operator remembering to run the script. The
    prod-tunnel entry point (`scripts/resweep_holed_games.py`) stays the ad-hoc,
    cross-database (dev/benchmark/prod) way to run it by hand.

    A "hole" is a non-terminal, non-game-ending-move, non-mate ply:
        eval_cp IS NULL AND eval_mate IS NULL AND ply < MAX(ply) - 1 for that game.
    The MAX(ply) exclusion skips the terminal game-over ply (which has no DB row of its
    own in most games but may appear as the last row in some PGNs). The additional
    `- 1` (SEED-049) further excludes the game-ending move ply (ply = max_ply - 1):
    under post-move storage, that row stores the eval of the game-over terminal
    position, which is legitimately unevaluable (no legal moves; the engine skips it in
    _collect_full_ply_targets). Resignation/timeout endings whose last move has a real
    eval are unaffected — their last move is not NULL. Only the genuinely unevaluable
    terminal-move NULLs (checkmate, stalemate, insufficient material) are excluded.
    The 2 genuine mid-game holes observed in prod are at ply < max_ply - 1, so this
    exclusion is precise and safe.

    Scope: engine games only (lichess_evals_at IS NULL). Lichess %eval games are already
    excluded from the full-drain and need no re-arming.

    Args:
        limit: cap the candidate scan at this many games (None = all).
        dry_run: count candidates without performing the UPDATE. Useful for prod inspection
            before running for real.
        session_maker: optional sessionmaker override (e.g. a prod-tunnel-bound maker from
            scripts/resweep_holed_games.py --db prod). Defaults to the app's
            async_session_maker (bound to DATABASE_URL — the dev DB locally).

    Returns:
        Count of games swept (cleared) or that would be swept (dry_run=True).

    Prod usage (via the SSH tunnel from bin/prod_db_tunnel.sh):
        uv run python scripts/resweep_holed_games.py --db prod --dry-run   # count only
        uv run python scripts/resweep_holed_games.py --db prod             # sweep
    """
    from app.models.game_position import GamePosition

    maker = session_maker or async_session_maker
    games_table = Game.__table__
    gp_table = GamePosition.__table__

    # Sub-query: find game_ids of engine games whose full_evals_completed_at IS NOT NULL
    # AND that have at least one genuine (non-terminal, non-game-ending-move, non-mate) hole.
    # "Non-terminal" = ply < MAX(ply) for that game (excludes the last game-over ply).
    # "Non-game-ending-move" = ply < MAX(ply) - _GAME_ENDING_PLY_OFFSET (SEED-049:
    #     excludes the move that ended the game; under post-move storage its after-eval is
    #     the unevaluable terminal position — legitimately NULL, not a transient hole).
    # "Non-mate" = eval_mate IS NULL (mate-scored plies are not holes).
    max_ply_per_game = (
        sa.select(GamePosition.game_id, sa.func.max(GamePosition.ply).label("max_ply"))
        .group_by(GamePosition.game_id)
        .subquery("max_ply_per_game")
    )

    holed_game_ids_q = (
        sa.select(gp_table.c.game_id)
        .distinct()
        .join(
            games_table,
            sa.and_(
                gp_table.c.game_id == games_table.c.id,
                games_table.c.full_evals_completed_at.isnot(None),
                games_table.c.lichess_evals_at.is_(None),  # engine games only
            ),
        )
        .join(
            max_ply_per_game,
            gp_table.c.game_id == max_ply_per_game.c.game_id,
        )
        .where(
            gp_table.c.eval_cp.is_(None),
            gp_table.c.eval_mate.is_(None),
            # SEED-049: ply < max_ply - 1 excludes both the terminal ply AND the
            # game-ending move ply (whose NULL after-eval is legitimately unevaluable).
            gp_table.c.ply < max_ply_per_game.c.max_ply - _GAME_ENDING_PLY_OFFSET,
        )
    )
    if limit is not None:
        holed_game_ids_q = holed_game_ids_q.limit(limit)

    async with maker() as session:
        # Initialize before the try so the except handler can report game_count
        # without a fragile `dir()` scope probe (WR-03). If session.execute raises
        # before the assignment below, game_count is correctly 0.
        game_ids: list[int] = []
        try:
            result = await session.execute(holed_game_ids_q)
            game_ids = [row[0] for row in result.all()]
            count = len(game_ids)

            if dry_run or count == 0:
                logger.info(
                    "resweep_holed_games: %s=%d games%s",
                    "would sweep" if dry_run else "swept",
                    count,
                    " (dry run)" if dry_run else "",
                )
                return count

            # Clear the completion markers and reset the attempt counter.
            # Clearing full_evals_completed_at makes the game match the
            # "needs engine" predicate again (full_evals_completed_at IS NULL
            # AND lichess_evals_at IS NULL) → tier-3 re-picks it. The
            # ix_games_needs_engine_full_evals partial index (SEED-046,
            # migration 20260614150000) covers this predicate.
            #
            # WR-04: chunk the UPDATE in _RESWEEP_UPDATE_CHUNK_SIZE batches so the
            # unbounded prod path can't re-arm the whole holed backlog in one
            # statement/transaction (bind-param blowup + simultaneous re-queue).
            # For count <= chunk size this is one statement + one commit, identical
            # to the pre-batching behavior.
            for chunk_start in range(0, count, _RESWEEP_UPDATE_CHUNK_SIZE):
                chunk_ids = game_ids[chunk_start : chunk_start + _RESWEEP_UPDATE_CHUNK_SIZE]
                await session.execute(
                    update(games_table)  # ty: ignore[invalid-argument-type]
                    .where(games_table.c.id.in_(chunk_ids))
                    .values(
                        full_evals_completed_at=None,
                        full_pv_completed_at=None,
                        full_eval_attempts=0,
                    )
                )
                await session.commit()
            logger.info("resweep_holed_games: swept %d games", count)
            return count

        except Exception as exc:
            sentry_sdk.set_context("resweep", {"game_count": len(game_ids)})
            sentry_sdk.set_tag("source", "resweep_holed_games")
            sentry_sdk.capture_exception(exc)
            raise


# SEED-139 D-07: daily in-process automation, following the exact
# run_periodic_guest_cleanup pattern (app/services/guest_cleanup_service.py) —
# sleep-first, per-tick sentry_sdk.isolation_scope(), Exception-only catch so
# CancelledError propagates on lifespan shutdown.
async def run_periodic_holed_game_resweep() -> None:
    """Automates resweep_holed_games: re-arm holed games once a day, in-process.

    This is the automation of what was a manual chore (`scripts/resweep_holed_
    games.py`, still available for an ad-hoc or cross-database run — see that
    module and resweep_holed_games' own docstring). Every tick calls
    `resweep_holed_games(limit=_RESWEEP_TICK_LIMIT, dry_run=False)` — NEVER a
    dry run; `_RESWEEP_TICK_LIMIT` is a burst guard on the drain and the
    volunteer fleet (D-07), not a correctness device, since the next day's tick
    picks up any remainder.

    D-07 accepted trade-off: the sweep resets `full_eval_attempts` to 0, so a
    genuinely unevaluable game is re-armed every cycle and burns its budget
    again. This is accepted for now on current prod evidence — every swept game
    has gotten fixed, and a dry run against prod returns 0 candidates. If that
    stops being true, the fix is a bounded `resweep_count` column (so a game
    that has been swept N times without ever clearing stops being re-armed),
    NOT dropping this automation.

    Called as `resweep_holed_games` (module global, not imported into a local
    name) so a test can monkeypatch this module's attribute directly.

    Wired in app/main.py lifespan — started on startup, cancelled+awaited on
    shutdown, alongside the other five background tasks (reaper, eval-drain,
    full-eval-drain, guest-cleanup, train-reminders). No ordering dependency
    with stop_engine/stop_maia — this loop never touches the engine.
    """
    while True:
        await asyncio.sleep(_RESWEEP_INTERVAL_SECONDS)
        # SEED-138: per-tick isolation scope -- a background loop must never
        # write to the shared lifespan scope (AsyncioIntegration is not
        # enabled; see app/main.py's create_task comment for why).
        with sentry_sdk.isolation_scope():
            try:
                swept = await resweep_holed_games(limit=_RESWEEP_TICK_LIMIT, dry_run=False)
                logger.info("holed_game_resweep: re-armed %d games", swept)
            except Exception:
                logger.exception("Periodic holed-game resweep failed")
                sentry_sdk.set_tag("source", "holed_game_resweep")
                sentry_sdk.capture_exception()
