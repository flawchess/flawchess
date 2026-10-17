"""Per-email sliding window rate limiter for password-reset requests.

Reuses the in-process _SlidingWindowRateLimiter from ip_rate_limiter. Keyed by
lowercased email address (not user_id — this call site is inside
UserManager.on_after_forgot_password, where a User is available, but keying
by email keeps this limiter meaningful even if the call site ever moves).
In-process limiter resets on restart — acceptable for single-process Uvicorn
deployment (mirrors feedback_limiter's posture).

Unlike the rejecting limiters (guest_create_limiter, feedback_limiter,
login_failure_limiter), which answer a rejection with an HTTP 429, this
instance's call site deliberately does NOT raise: a rejected request must return
the router's identical 202 with zero enumeration signal, so the caller silently
skips the send. The call site in app/users.py points here for why it deviates
from the other limiter call sites.
"""

from app.core.ip_rate_limiter import _SlidingWindowRateLimiter

_RESET_PASSWORD_MAX_REQUESTS = 5
_RESET_PASSWORD_WINDOW_SECONDS = (
    3600  # 1 hour — matches guest_create_limiter/feedback_limiter precedent
)

# Module-level singleton keyed by lowercased email
reset_password_limiter = _SlidingWindowRateLimiter(
    _RESET_PASSWORD_MAX_REQUESTS,
    _RESET_PASSWORD_WINDOW_SECONDS,
)
