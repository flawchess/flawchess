"""In-process sliding window rate limiter (shared class) and the per-IP guest-creation limiter.

In-process limiter — resets on server restart. Acceptable for single-process
Uvicorn deployment. For multi-process or distributed deployments, replace with
a Redis-backed solution.
"""

import time
from collections import defaultdict

_GUEST_CREATE_MAX_REQUESTS = 5
_GUEST_CREATE_WINDOW_SECONDS = 3600  # 1 hour


class _SlidingWindowRateLimiter:
    """Sliding window rate limiter keyed by an arbitrary string (IP, user id or email, per instance).

    Stores timestamps of allowed requests in memory. On each call to
    `is_allowed`, evicts timestamps outside the window, then checks if the
    count is below the maximum.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        # Keyed by the limiter key; values are sorted lists of monotonic timestamps
        self._timestamps: defaultdict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str) -> list[float]:
        """Evict timestamps outside the window and return the live ones for `key`."""
        cutoff = time.monotonic() - self._window_seconds
        live = [t for t in self._timestamps.get(key, ()) if t > cutoff]

        # Bug fix: a pruned-to-empty entry was never removed
        # from the dict, so every IP that ever hit this limiter stayed in
        # memory for the process lifetime. Only non-empty lists are stored.
        if live:
            self._timestamps[key] = live
        else:
            self._timestamps.pop(key, None)
        return live

    def is_allowed(self, key: str) -> bool:
        """Return True if the request from `key` is within the rate limit, else False.

        Counts the request when allowed (check-and-record in one call).
        """
        if len(self._prune(key)) >= self._max_requests:
            return False
        self._timestamps[key].append(time.monotonic())
        return True

    def is_blocked(self, key: str) -> bool:
        """Return True if `key` has used up the window, without counting this call."""
        return len(self._prune(key)) >= self._max_requests

    def record(self, key: str) -> None:
        """Count one event for `key` (for limiters that count only some outcomes)."""
        self._prune(key)
        self._timestamps[key].append(time.monotonic())


# Module-level singleton used by the guest creation endpoint
guest_create_limiter = _SlidingWindowRateLimiter(
    _GUEST_CREATE_MAX_REQUESTS,
    _GUEST_CREATE_WINDOW_SECONDS,
)
