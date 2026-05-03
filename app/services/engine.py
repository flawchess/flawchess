"""Stockfish engine wrapper (Phase 78 ENG-02 / ENG-03).

Single source of UCI option configuration. The module-level API is backed by
an internal `EnginePool` of size `STOCKFISH_POOL_SIZE` (env var, default 1).
Sign convention is white-perspective and matches app/services/zobrist.py:183-197
byte-for-byte.

Two APIs:
    Module-level (live FastAPI traffic, prod imports):
        start_engine()       -- call from FastAPI lifespan startup.
        stop_engine()        -- call from lifespan shutdown.
        evaluate(board)      -- async; returns (eval_cp, eval_mate).

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

import chess
import chess.engine

from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

# D-06: env var with sensible default; Docker image sets STOCKFISH_PATH=/usr/local/bin/stockfish
_STOCKFISH_PATH: str = os.environ.get("STOCKFISH_PATH", "/usr/local/bin/stockfish")
# D-03: UCI options live ONLY in this module (ENG-03 grep gate)
_HASH_MB: int = 64
_THREADS: int = 1
# SPEC constraint: depth 15 fixed, no per-call tuning
_DEPTH: int = 15
# D-05: defensive per-eval timeout
_TIMEOUT_S: float = 2.0
# Module-level pool size. Default 1 = legacy singleton behavior. Prod sets
# STOCKFISH_POOL_SIZE=2 to use 2 of 4 vCPUs for parallel import-time evals
# while leaving headroom for Postgres + uvicorn. Read at start_engine() time.
_POOL_SIZE_ENV: str = "STOCKFISH_POOL_SIZE"
_DEFAULT_POOL_SIZE: int = 1

# Module-level pool. None until start_engine() is called.
_pool: EnginePool | None = None


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
            transport, protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
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
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
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
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
                pass
        try:
            transport, protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
            await protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})
        except Exception:
            self._transports[idx] = None
            self._protocols[idx] = None
            return False
        self._transports[idx] = transport
        self._protocols[idx] = protocol
        return True

    async def evaluate(self, board: chess.Board) -> tuple[int | None, int | None]:
        """Evaluate a position on the next idle worker. Same contract as evaluate()."""
        if not self._started:
            return None, None
        idx = await self._available.get()
        try:
            protocol = self._protocols[idx]
            if protocol is None:
                return None, None
            try:
                info = await asyncio.wait_for(
                    protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
                    timeout=_TIMEOUT_S,
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
