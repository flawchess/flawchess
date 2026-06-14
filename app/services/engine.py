"""Stockfish engine wrapper (Phase 78 ENG-02 / ENG-03).

Single source of UCI option configuration. The module-level API is backed by
an internal `EnginePool` of size `STOCKFISH_POOL_SIZE` (env var, default 1).
Sign convention is white-perspective and matches app/services/zobrist.py:183-197
byte-for-byte.

On Linux, every Stockfish subprocess is spawned under SCHED_IDLE (see
`_sched_idle_preexec`), so the kernel preempts it instantly whenever any other
runnable task wants CPU. This makes pool sizes equal to the host's vCPU count
safe without starving Uvicorn or Postgres. macOS / Windows fall back to default
scheduling (the relevant `os.sched_setscheduler` API is Linux-only).

Two APIs:
    Module-level (live FastAPI traffic, prod imports):
        start_engine()              -- call from FastAPI lifespan startup.
        stop_engine()               -- call from lifespan shutdown.
        evaluate(board)             -- async; returns (eval_cp, eval_mate); depth-15.
        evaluate_nodes(board)       -- async; returns (eval_cp, eval_mate); 1M nodes (EVAL-02).
        evaluate_nodes_with_pv(board) -- async; returns (eval_cp, eval_mate, best_move, pv_string);
                                        zero extra search cost (EVAL-04, Phase 117).

        With STOCKFISH_POOL_SIZE=1 (the dev/CI default) this behaves exactly
        like the original singleton. Set STOCKFISH_POOL_SIZE=2+ on prod to get
        N independent UCI processes. Callers gain parallelism only when they
        fan out evaluate() via asyncio.gather — a single sequential awaiter
        sees no speedup regardless of pool size.

    EnginePool (batch jobs that benefit from parallelism, e.g. backfill):
        pool = EnginePool(size=N)
        await pool.start(); ...; await pool.evaluate(board); ...; await pool.stop()

        Use directly when you need a different size than the module-level
        pool (e.g. scripts/backfill_eval.py running on a beefy host).

On engine timeout / crash, evaluate() restarts the affected worker and
returns (None, None). The caller decides whether to log to Sentry
(import path: D-11; backfill script: log).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from typing import Any

import chess
import chess.engine

from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

# D-06: STOCKFISH_PATH env var wins when set (prod Docker sets it, CI sets it).
# When unset we probe well-known locations so local dev needs no env var: the
# prod Docker path, then bin/install_stockfish.sh's dev install location, then
# anything named `stockfish` on PATH (e.g. Homebrew / apt). Falls back to the
# Docker path so a missing-binary error still points somewhere sane.
_DOCKER_STOCKFISH_PATH: str = "/usr/local/bin/stockfish"
_DEV_STOCKFISH_PATH: str = os.path.expanduser("~/.local/stockfish/sf")


def _resolve_stockfish_path() -> str:
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        return env_path
    for candidate in (_DOCKER_STOCKFISH_PATH, _DEV_STOCKFISH_PATH):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    on_path = shutil.which("stockfish")
    if on_path:
        return on_path
    return _DOCKER_STOCKFISH_PATH


_STOCKFISH_PATH: str = _resolve_stockfish_path()
# D-03: UCI options live ONLY in this module (ENG-03 grep gate)
# Bug fix (2026-05-16, FLAWCHESS-56 / FLAWCHESS-3Q): reduced 64 -> 32. With
# the hotfix-era STOCKFISH_POOL_SIZE=4 the pool reserved 4 * 64 = 256MB of
# hash tables alone, a material contributor to the import-time Postgres
# OOM-kill. At depth 15 over import-time evals the smaller hash has negligible
# quality impact (per-position search, not long analysis). Prod has since been
# raised to STOCKFISH_POOL_SIZE=6 stably for several weeks (see pool comment).
_HASH_MB: int = 32
_THREADS: int = 1
# SPEC constraint: depth 15 fixed, no per-call tuning
_DEPTH: int = 15
# D-05: defensive per-eval timeout
_TIMEOUT_S: float = 2.0
# Phase 116 EVAL-02: node-budget constants for full-game analysis drain.
# _NODES_TIMEOUT_S is distinct from _TIMEOUT_S: depth-15 mean ~0.09s; 1M-node
# mean ~0.98s (prod spike 002 p90 = 1.277s). _TIMEOUT_S = 2.0 would time out ~50%
# of node-budget calls on prod. 5.0s = ~4x prod p90 (spike 002).
_NODES_BUDGET: int = 1_000_000  # EVAL-02: Lichess fishnet parity (D-6 SEED-012)
_NODES_TIMEOUT_S: float = 5.0  # 4x prod p90 (1.277s, spike 002)
# Phase 117 EVAL-04 / D-117-02: PV cap for flaw refutation lines.
# SEED-039 motif-line depth: tier-1/2 need 1-2 plies; tier-3 needs ~3 plies.
# Cap at 12 for margin. At 12 moves: max 12×5 + 11 = 71 chars — fits Text easily.
PV_CAP_PLIES: int = 12
#
# NOTE (2026-05-29): eval_cp is NOT reproducible across machines/runs, and the
# eval-derived percentiles (achievable_score_gap, score_gap_conv/parity/recovery)
# therefore differ slightly between independently-backfilled DBs (e.g. dev vs prod)
# even for identical imports. Two causes: (1) this wall-clock timeout is
# machine-speed-dependent -- a slower/busier host times out more depth-15 searches,
# leaving eval_cp=NULL, which classify_span() routes to "parity"; (2) the TT
# persists across positions within a pool worker (python-chess only clears on a
# `game=` change, which we don't pass) so depth-15 evals are mildly order-/
# scheduling-dependent. Stockfish has no RNG seed -- its search isn't randomized --
# so there's nothing to seed; determinism would require a node limit + per-position
# hash clear + pinned binary/net. Decided NOT worth fixing: differences are
# sub-percentile and at the +-100cp classification boundary. If dev/prod must match
# exactly, copy eval_cp/eval_mate between DBs rather than re-backfilling each.
#
# QUEUE-07 / D-116-12: Memory accounting for the pool-size decision (Phase 116).
#
# Measured per-worker RSS at 1M-node budget on the dev box (2026-06-12):
#   1 worker:  277 MB    (includes full NNUE net load)
#   4 workers: 1056 MB   (264 MB/worker -- sub-linear: NNUE net is OS page-cache-shared)
#   6 workers: 1586 MB   (264 MB/worker)
#   8 workers: 2083 MB   (260 MB/worker)
# The sub-linear scaling (8x277 would be 2216 MB; actual 2083 MB) confirms the
# 125 MiB NNUE net is shared across workers from the same binary via page cache (A3).
#
# Conservative prod estimate (Phase 91 stress test measured ~368 MB/worker at
# depth-15 with concurrent imports; 1M-node calls are similar in working-set):
#   8 workers x 368 MB = ~2.94 GB Stockfish
#   FastAPI/Uvicorn ~0.3 GB
#   Total estimate:   ~3.24 GB
#   4g mem_limit headroom: ~0.76 GB  (sufficient; import-era OOM needed ~3.7+ GB)
#
# Deploy decision (D-116-13): ship at STOCKFISH_POOL_SIZE=6 first, monitor prod
# API p50/p90 and container RSS for ~24 h, then raise to 8 only if (a) the
# accounting fits 4g with headroom AND (b) API latency is clean. All Phase 116
# throughput targets (5.83 pos/s, 8.4k games/day) were benchmarked at 6 workers.
#
# Module-level pool size. Default 1 = dev/CI singleton behavior. Prod sets
# STOCKFISH_POOL_SIZE via .env (currently 6; 8 is the Phase 116 target,
# contingent on the QUEUE-07 accounting check -- see comment above). Workers
# run under Linux SCHED_IDLE (see _sched_idle_preexec) so they only consume
# idle CPU and never preempt Uvicorn or Postgres. Read at start_engine() time.
_POOL_SIZE_ENV: str = "STOCKFISH_POOL_SIZE"
_DEFAULT_POOL_SIZE: int = 1

# Module-level pool. None until start_engine() is called.
_pool: EnginePool | None = None


def _sched_idle_preexec() -> None:
    """preexec_fn: switch the just-forked child to SCHED_IDLE before exec.

    Linux SCHED_IDLE makes the process consume only idle CPU. The kernel
    preempts it instantly whenever any other runnable task (Uvicorn worker,
    Postgres, system daemons) wants the core. This lets us safely run as many
    Stockfish workers as we have vCPUs without harming API latency.

    Unprivileged SCHED_IDLE does NOT require CAP_SYS_NICE on Linux 2.6.23+.
    Errors are swallowed: if the kernel rejects the call (containerised host
    with seccomp filter, exotic distro), we'd rather have Stockfish run at
    normal priority than crash the worker spawn.
    """
    try:
        os.sched_setscheduler(0, os.SCHED_IDLE, os.sched_param(0))
    except OSError:
        pass


def _engine_popen_kwargs() -> dict[str, Any]:
    """Return popen kwargs for Stockfish subprocesses.

    On Linux, request SCHED_IDLE scheduling for the child. On macOS / Windows
    the os.sched_setscheduler API doesn't exist, so we spawn with default
    scheduling. Dev-on-Mac behaves exactly as before this change.

    Return type is `dict[str, Any]` (not `dict[str, object]`) because
    `chess.engine.popen_uci` declares a typed `setpgrp: bool` keyword in
    addition to `**popen_args: Any`; ty resolves splatted kwargs against the
    typed param first and rejects `object`.
    """
    if sys.platform == "linux":
        return {"preexec_fn": _sched_idle_preexec}
    return {}


def _read_pool_size() -> int:
    raw = os.environ.get(_POOL_SIZE_ENV)
    if raw is None or raw == "":
        return _DEFAULT_POOL_SIZE
    try:
        size = int(raw)
    except ValueError:
        return _DEFAULT_POOL_SIZE
    return max(1, size)


async def start_engine() -> None:
    """Start the module-level engine pool. Idempotent: a second call is a no-op."""
    global _pool
    if _pool is not None:
        return
    pool = EnginePool(size=_read_pool_size())
    await pool.start()
    _pool = pool


async def stop_engine() -> None:
    """Stop the module-level engine pool. Safe to call without start (no-op)."""
    global _pool
    if _pool is None:
        return
    try:
        await _pool.stop()
    finally:
        _pool = None


async def evaluate(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at depth 15. Returns (eval_cp, eval_mate) in white perspective.

    Returns (None, None) if the engine is not started, or on timeout / crash
    (the affected worker is restarted before returning so the next caller
    sees a clean state).

    Sign convention matches app/services/zobrist.py:183-197 byte-for-byte:
        eval_cp  -- centipawn score from white's perspective; None for mate positions
        eval_mate -- moves to forced mate; positive = white mates, negative = black mates
    """
    if _pool is None:
        return None, None
    return await _pool.evaluate(board)


async def evaluate_nodes(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at 1M nodes. Returns (eval_cp, eval_mate) in white perspective.

    EVAL-02: Lichess-parity budget for full-game analysis drain.
    Returns (None, None) on engine failure — same contract as evaluate().
    Single PV only (Phase 116). PV capture is EVAL-04 / Phase 117.
    Scalar InfoDict returned directly, handled by existing _score_to_cp_mate().
    """
    if _pool is None:
        return None, None
    return await _pool.evaluate_nodes(board)


async def evaluate_nodes_with_pv(
    board: chess.Board,
) -> tuple[int | None, int | None, str | None, str | None]:
    """Evaluate position at 1M nodes, returning eval + PV data.

    EVAL-04 / Phase 117: PV capture at zero extra engine cost — the PV falls
    out of the same 1M-node search as evaluate_nodes (info=Info.ALL default).

    Returns (eval_cp, eval_mate, best_move_uci, pv_uci_string):
        eval_cp / eval_mate: same sign convention as evaluate_nodes (white perspective).
        best_move_uci: info["pv"][0].uci() when PV present, else None (D-117-01).
        pv_uci_string: space-joined UCI, capped at PV_CAP_PLIES (D-117-02); None when
            PV absent.

    Returns (None, None, None, None) on engine failure — D-09 semantics preserved.
    """
    if _pool is None:
        return None, None, None, None
    return await _pool.evaluate_nodes_with_pv(board)


def _pv_to_best_move(info: chess.engine.InfoDict) -> str | None:
    """Extract the best move UCI string from an InfoDict (EVAL-04 / D-117-01).

    Returns info["pv"][0].uci() when the PV is present and non-empty, else None.
    Mirrors the _score_to_cp_mate info.get(...) guard style.
    """
    pv = info.get("pv")
    if not pv:
        return None
    return pv[0].uci()


def _pv_to_uci_string(info: chess.engine.InfoDict, cap: int = PV_CAP_PLIES) -> str | None:
    """Build a space-joined UCI PV string from an InfoDict (EVAL-04 / D-117-02).

    Caps at `cap` plies (default PV_CAP_PLIES=12 for the flaw refutation line).
    Returns None when the PV is absent or empty.
    """
    pv = info.get("pv")
    if not pv:
        return None
    return " ".join(m.uci() for m in pv[:cap])


def _score_to_cp_mate(
    info: chess.engine.InfoDict,
) -> tuple[int | None, int | None]:
    """Extract (eval_cp, eval_mate) from an analyse() result.

    Sign convention and clamping match zobrist.py:183-197 byte-for-byte.
    """
    pov_score = info.get("score")
    if pov_score is None:
        return None, None
    white_score = pov_score.white()
    eval_cp: int | None = white_score.score(mate_score=None)
    eval_mate: int | None = white_score.mate()
    if eval_cp is not None:
        eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
    if eval_mate is not None:
        eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))
    return eval_cp, eval_mate


async def get_stockfish_version() -> str:
    """Read Stockfish version string via UCI handshake.

    Returns e.g. 'Stockfish 18'. Called once by the remote worker CLI at
    startup to populate sf_version in SubmitRequest (Phase 120 D-5).
    Opens and immediately quits a single UCI connection; does not use EnginePool.
    """
    transport, protocol = await chess.engine.popen_uci(_STOCKFISH_PATH, **_engine_popen_kwargs())
    version = str(protocol.id.get("name", "unknown"))
    await protocol.quit()
    return version


class EnginePool:
    """Parallel Stockfish workers for batch evaluation jobs.

    Owns N independent UCI subprocesses, each with its own protocol. evaluate()
    grabs an idle worker from an asyncio.Queue, runs analyse() against its
    process, and releases it back to the queue. With N callers awaiting
    evaluate() concurrently (e.g. via asyncio.gather), up to N positions
    analyse in parallel.

    On per-worker timeout / crash, that worker restarts in place; siblings
    keep going. If restart fails the worker is permanently disabled and its
    slot is dropped from the queue — remaining workers continue to serve.

    The module-level start_engine() / evaluate() use a pool of size
    STOCKFISH_POOL_SIZE (default 1). Use this class directly when you need
    a different size — e.g. scripts/backfill_eval.py on a beefy host.
    """

    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError(f"EnginePool size must be >= 1, got {size}")
        self._size = size
        self._transports: list[asyncio.SubprocessTransport | None] = []
        self._protocols: list[chess.engine.UciProtocol | None] = []
        self._available: asyncio.Queue[int] = asyncio.Queue()
        self._started = False

    @property
    def size(self) -> int:
        return self._size

    async def start(self) -> None:
        """Spawn `size` UCI processes. Idempotent: a second call is a no-op."""
        if self._started:
            return
        for _ in range(self._size):
            transport, protocol = await chess.engine.popen_uci(
                _STOCKFISH_PATH, **_engine_popen_kwargs()
            )
            await protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})
            idx = len(self._transports)
            self._transports.append(transport)
            self._protocols.append(protocol)
            self._available.put_nowait(idx)
        self._started = True

    async def stop(self) -> None:
        """Quit all UCI processes. Safe to call without start (no-op)."""
        for protocol in self._protocols:
            if protocol is None:
                continue
            try:
                await protocol.quit()
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError, RuntimeError):
                # RuntimeError: quit() on an already-dead engine writes to a closed
                # uvloop transport ("the handler is closed") — FLAWCHESS-59.
                pass
        self._transports.clear()
        self._protocols.clear()
        while not self._available.empty():
            self._available.get_nowait()
        self._started = False

    async def _restart_worker(self, idx: int) -> bool:
        """Restart worker at index `idx` after timeout / crash. Returns True on success."""
        old_protocol = self._protocols[idx]
        if old_protocol is not None:
            try:
                await old_protocol.quit()
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError, RuntimeError):
                # RuntimeError: when the engine process died (e.g. SIGINT from dev
                # reload), quit() writes to a closed uvloop transport and raises
                # "the handler is closed" — not an EngineError subclass. Letting it
                # escape aborted the restart and left the dead protocol in the slot,
                # causing a raise-loop on every subsequent pickup (FLAWCHESS-59).
                pass
        try:
            transport, protocol = await chess.engine.popen_uci(
                _STOCKFISH_PATH, **_engine_popen_kwargs()
            )
            await protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})
        except Exception:
            self._transports[idx] = None
            self._protocols[idx] = None
            return False
        self._transports[idx] = transport
        self._protocols[idx] = protocol
        return True

    async def _analyse(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        timeout: float,
    ) -> tuple[int | None, int | None]:
        """Shared worker-acquisition / analyse / failure-restart path (WR-06).

        Single implementation behind evaluate() and evaluate_nodes() — the
        acquisition, exception tuple, restart-on-failure, and slot-release
        logic must never diverge between the two public methods.
        """
        if not self._started:
            return None, None
        idx = await self._available.get()
        try:
            protocol = self._protocols[idx]
            if protocol is None:
                return None, None
            try:
                info = await asyncio.wait_for(
                    protocol.analyse(board, limit),
                    timeout=timeout,
                )
            except (
                asyncio.TimeoutError,
                chess.engine.EngineError,
                chess.engine.EngineTerminatedError,
            ):
                # Restart the failed worker; its slot returns to the queue regardless
                # of restart success — a permanently-failed worker returns (None, None)
                # on its next pickup but does not block sibling workers.
                await self._restart_worker(idx)
                return None, None
            return _score_to_cp_mate(info)
        finally:
            self._available.put_nowait(idx)

    async def evaluate(self, board: chess.Board) -> tuple[int | None, int | None]:
        """Evaluate a position at depth 15 on the next idle worker."""
        return await self._analyse(board, chess.engine.Limit(depth=_DEPTH), _TIMEOUT_S)

    async def evaluate_nodes(self, board: chess.Board) -> tuple[int | None, int | None]:
        """Evaluate at 1M nodes on the next idle worker. EVAL-02.

        Same contract as evaluate() but uses Limit(nodes=_NODES_BUDGET) and
        _NODES_TIMEOUT_S. Single PV only (Phase 116); PV capture is EVAL-04 / Phase 117.
        Scalar InfoDict returned directly, handled by _score_to_cp_mate() unchanged.
        """
        return await self._analyse(board, chess.engine.Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S)

    async def _analyse_with_pv(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        timeout: float,
    ) -> chess.engine.InfoDict | None:
        """Shared worker-acquisition / analyse / failure-restart path returning raw InfoDict.

        Parallel to _analyse but returns the InfoDict instead of applying _score_to_cp_mate,
        so callers can extract both eval and PV from a single search (EVAL-04).
        Returns None on timeout / crash / missing protocol (mirrors _analyse failure path).
        """
        if not self._started:
            return None
        idx = await self._available.get()
        try:
            protocol = self._protocols[idx]
            if protocol is None:
                return None
            try:
                info = await asyncio.wait_for(
                    protocol.analyse(board, limit),
                    timeout=timeout,
                )
            except (
                asyncio.TimeoutError,
                chess.engine.EngineError,
                chess.engine.EngineTerminatedError,
            ):
                await self._restart_worker(idx)
                return None
            return info
        finally:
            self._available.put_nowait(idx)

    async def evaluate_nodes_with_pv(
        self,
        board: chess.Board,
    ) -> tuple[int | None, int | None, str | None, str | None]:
        """Evaluate at 1M nodes, returning (eval_cp, eval_mate, best_move_uci, pv_uci_string).

        EVAL-04 / Phase 117: PV falls out of the SAME 1M-node search as evaluate_nodes —
        zero extra engine compute. Reuses _NODES_BUDGET and _NODES_TIMEOUT_S.

        best_move_uci: info["pv"][0].uci() when PV present, else None (D-117-01).
        pv_uci_string: space-joined UCI capped at PV_CAP_PLIES (D-117-02).
        Returns (None, None, None, None) on engine failure (D-09 failure semantics).
        """
        info = await self._analyse_with_pv(
            board, chess.engine.Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S
        )
        if info is None:
            return None, None, None, None
        eval_cp, eval_mate = _score_to_cp_mate(info)
        best_move = _pv_to_best_move(info)
        pv_string = _pv_to_uci_string(info)
        return eval_cp, eval_mate, best_move, pv_string
