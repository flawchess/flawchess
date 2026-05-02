"""Stockfish engine wrapper (Phase 78 ENG-02 / ENG-03).

Single source of UCI option configuration. Long-lived UCI process per Python
process (D-01). Async-friendly via asyncio.Lock serialization. Sign convention
is white-perspective and matches app/services/zobrist.py:183-197 byte-for-byte.

Lifecycle:
    start_engine()       -- call from FastAPI lifespan startup (or script main()).
    stop_engine()        -- call from lifespan shutdown / script teardown.
    evaluate(board)      -- async; returns (eval_cp, eval_mate) in white perspective.

On engine timeout / crash, evaluate() restarts the engine and returns (None, None).
The caller decides whether to log to Sentry (import path: D-11; backfill script: log).
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

    pov_score = info.get("score")
    if pov_score is None:
        return None, None

    # White-perspective regardless of board.turn -- matches zobrist.py:183-197
    white_score = pov_score.white()
    eval_cp: int | None = white_score.score(mate_score=None)  # None for mate
    eval_mate: int | None = white_score.mate()  # None for non-mate

    # Clamp to SMALLINT-safe bounds (mirrors zobrist.py:194-197)
    if eval_cp is not None:
        eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
    if eval_mate is not None:
        eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))

    return eval_cp, eval_mate
