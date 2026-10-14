"""Password policy shared by registration, password reset and guest promotion.

Deliberately permissive (security review 2026-10-14): FlawChess stores no
sensitive data, so usability wins. Length bounds only, no composition rules,
no expiry. The login failure limiter (app/core/login_rate_limiter.py) is what
makes short passwords impractical to brute-force.
"""

MIN_PASSWORD_LENGTH = 8
# Argon2 accepts any length; the cap stops megabyte inputs from costing hash time.
MAX_PASSWORD_LENGTH = 128


def password_policy_violation(password: str) -> str | None:
    """Return a user-facing reason the password is rejected, or None if it is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    return None
