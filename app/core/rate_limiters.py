"""Shared per-platform rate limiters for import jobs.

Module-level asyncio.Semaphore instances that throttle outbound API calls
across ALL concurrent import jobs. Lazy-initialized to avoid creating
Semaphores before the event loop starts (Python 3.10+ requirement).
"""

import asyncio

# chess.com: community-reported 3-4 concurrent triggers 429s. Conservative limit.
CHESSCOM_SEMAPHORE_LIMIT = 2
# lichess: more permissive, but each connection is a long-lived stream
LICHESS_SEMAPHORE_LIMIT = 3

_chesscom_semaphore: asyncio.Semaphore | None = None
_lichess_semaphore: asyncio.Semaphore | None = None


def get_chesscom_semaphore() -> asyncio.Semaphore:
    """Return the shared chess.com rate-limiting semaphore (lazy init)."""
    global _chesscom_semaphore
    if _chesscom_semaphore is None:
        _chesscom_semaphore = asyncio.Semaphore(CHESSCOM_SEMAPHORE_LIMIT)
    return _chesscom_semaphore


def get_lichess_semaphore() -> asyncio.Semaphore:
    """Return the shared lichess rate-limiting semaphore (lazy init)."""
    global _lichess_semaphore
    if _lichess_semaphore is None:
        _lichess_semaphore = asyncio.Semaphore(LICHESS_SEMAPHORE_LIMIT)
    return _lichess_semaphore
