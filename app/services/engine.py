"""Stockfish engine wrapper (Phase 78 ENG-02 / ENG-03).

Single source of UCI option configuration. Long-lived UCI process per Python
process (D-01). Async-friendly via asyncio.Lock serialization. Sign convention
is white-perspective and matches app/services/zobrist.py:183-197 byte-for-byte.

Two APIs:
    Singleton (live FastAPI traffic, prod imports):
        start_engine()       -- call from FastAPI lifespan startup.
        stop_engine()        -- call from lifespan shutdown.
        evaluate(board)      -- async; returns (eval_cp, eval_mate).

    EnginePool (batch jobs that benefit from parallelism, e.g. backfill):
        pool = EnginePool(size=N)
        await pool.start(); ...; await pool.evaluate(board); ...; await pool.stop()

The singleton holds one UCI process. The pool holds N independent processes,
each with its own protocol, dispatched via an asyncio.Queue. Live traffic
must keep using the singleton — running N engines in a 4 vCPU / 8 GB prod
container would starve the API and Postgres. The pool is opt-in for
short-lived batch scripts running on hosts with the resources to spare.

On engine timeout / crash, evaluate() restarts the affected engine and
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

# Long-lived process state. Module-level globals per D-01 (single shared engine).
_transport: asyncio.SubprocessTransport | None = None
_protocol: chess.engine.UciProtocol | None = None
_lock: asyncio.Lock = asyncio.Lock()


async def start_engine() -> None:
    """Start the long-lived UCI process. Idempotent: a second call is a no-op."""
    global _transport, _protocol
    if _protocol is not None:
        return
    _transport, _protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
    await _protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})


async def stop_engine() -> None:
    """Stop the UCI process. Safe to call without start (no-op if not started)."""
    global _transport, _protocol
    if _protocol is not None:
        try:
            await _protocol.quit()
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
            pass
    _transport = None
    _protocol = None


async def _restart_engine() -> None:
    """Restart after timeout / crash. Internal -- callers do not invoke directly."""
    await stop_engine()
    try:
        await start_engine()
    except Exception:
        # If restart also fails, _protocol stays None so next evaluate() returns (None, None).
        pass


async def evaluate(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at depth 15. Returns (eval_cp, eval_mate) in white perspective.

    Returns (None, None) if the engine is not started, or on timeout / crash
    (engine is restarted before returning so the next caller sees a clean state).

    Sign convention matches app/services/zobrist.py:183-197 byte-for-byte:
        eval_cp  -- centipawn score from white's perspective; None for mate positions
        eval_mate -- moves to forced mate; positive = white mates, negative = black mates
    """
    async with _lock:
        if _protocol is None:
            return None, None
        try:
            info = await asyncio.wait_for(
                _protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
                timeout=_TIMEOUT_S,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await _restart_engine()
            return None, None

    return _score_to_cp_mate(info)


def _score_to_cp_mate(
    info: chess.engine.InfoDict,
) -> tuple[int | None, int | None]:
    """Extract (eval_cp, eval_mate) from an analyse() result.

    Shared by the singleton and EnginePool paths. Sign convention and clamping
    match zobrist.py:183-197 byte-for-byte.
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
    evaluate() concurrently, up to N positions analyse in parallel.

    On per-worker timeout / crash, that worker restarts in place; siblings
    keep going. If restart fails the worker is permanently disabled and its
    slot is dropped from the queue — remaining workers continue to serve.

    Use only for batch jobs (e.g. scripts/backfill_eval.py). Live FastAPI
    traffic uses the module-level singleton because the prod container has
    4 vCPU / 8 GB RAM — a multi-engine pool there would starve the API.
    """

    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError(f"EnginePool size must be >= 1, got {size}")
        self._size = size
        self._transports: list[asyncio.SubprocessTransport | None] = []
        self._protocols: list[chess.engine.UciProtocol | None] = []
        self._available: asyncio.Queue[int] = asyncio.Queue()
        self._started = False

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
