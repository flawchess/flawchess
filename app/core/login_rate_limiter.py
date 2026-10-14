"""Per-email sliding window limiter on failed password logins.

Counts FAILED attempts only, keyed by the lowercased submitted email whether or
not an account exists, so a 429 never reveals which emails are registered. Once
the limit is hit, every login for that email (even with the right password) is
refused until the window slides. Someone can therefore lock a known email out of
password login for one window; Google sign-in and password reset still work.

In-process limiter, resets on restart. Acceptable for the single-process Uvicorn
deployment (mirrors reset_password_limiter's posture).
"""

from app.core.ip_rate_limiter import _SlidingWindowRateLimiter

_LOGIN_FAILURE_MAX_ATTEMPTS = 10
_LOGIN_FAILURE_WINDOW_SECONDS = 900  # 15 minutes

login_failure_limiter = _SlidingWindowRateLimiter(
    _LOGIN_FAILURE_MAX_ATTEMPTS,
    _LOGIN_FAILURE_WINDOW_SECONDS,
)
