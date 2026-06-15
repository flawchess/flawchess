"""Per-user sliding window rate limiter for feedback submissions.

Reuses the in-process _SlidingWindowRateLimiter from ip_rate_limiter.
Keyed by user_id (str), not IP address. In-process limiter resets on restart —
acceptable for single-process Uvicorn deployment (D-07 / A5).
"""

from app.core.ip_rate_limiter import _SlidingWindowRateLimiter

_FEEDBACK_MAX_REQUESTS = 5
_FEEDBACK_WINDOW_SECONDS = 3600  # 1 hour

# Module-level singleton keyed by str(user.id)
feedback_limiter = _SlidingWindowRateLimiter(
    _FEEDBACK_MAX_REQUESTS,
    _FEEDBACK_WINDOW_SECONDS,
)
