"""Feedback service: ELO bucket derivation and Sentry push signal.

Separates Sentry tagging + cohort derivation logic from the thin HTTP router,
keeping the router HTTP-only per project convention.
"""

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_rating_anchors_repository import fetch_anchors_for_user
from app.schemas.feedback import FeedbackCreate

# Descending threshold → bucket mapping mirroring elo_bucket_expr in canonical_slice_sql.py.
# < 800 → None; <1200 → 800; <1600 → 1200; <2000 → 1600; <2400 → 2000; else 2400
_ELO_ANCHORS: tuple[tuple[int, int], ...] = (
    (2400, 2400),
    (2000, 2000),
    (1600, 1600),
    (1200, 1200),
    (800, 800),
)
_ELO_FLOOR = 800


def elo_bucket(rating: int) -> int | None:
    """Map an integer rating to the nearest ELO bucket anchor.

    Mirrors the SQL CASE WHEN expression in canonical_slice_sql.elo_bucket_expr:
    < 800 → None (sub-floor); <1200 → 800; <1600 → 1200; <2000 → 1600;
    <2400 → 2000; >= 2400 → 2400.
    """
    if rating < _ELO_FLOOR:
        return None
    for threshold, bucket in _ELO_ANCHORS:
        if rating >= threshold:
            return bucket
    return None


async def push_sentry_signal(session: AsyncSession, user: User, data: FeedbackCreate) -> None:
    """Derive cohort context from the authenticated user and emit a Sentry push signal.

    Uses capture_message (non-exception, D-05) with a static message string.
    Variable data goes in tags (filterable: source/platform/elo_bucket) and
    set_context (structured: user_id/page_url/rating). Never embed variables
    in the message string — that would fragment Sentry grouping (CLAUDE.md rule,
    Pitfall 2 from RESEARCH.md).

    ELO bucket: highest anchor_rating across all TCs (ASSUMED A1 from RESEARCH.md).
    Platform: derived from user.chess_com_username / user.lichess_username.
    """
    # Derive ELO bucket from the user's highest anchor across all time controls (A1)
    anchors = await fetch_anchors_for_user(session, user_id=user.id)
    max_rating = max((a.anchor_rating for a in anchors.values()), default=None)
    bucket = elo_bucket(max_rating) if max_rating is not None else None

    # Derive platform from usernames on the injected User object (no extra query)
    if user.chess_com_username:
        platform = "chess.com"
    elif user.lichess_username:
        platform = "lichess"
    else:
        platform = "none"

    # Set tags (filterable dimensions for Sentry cohort filtering per D-05)
    sentry_sdk.set_tag("source", "feedback")
    sentry_sdk.set_tag("platform", platform)
    sentry_sdk.set_tag("elo_bucket", str(bucket) if bucket is not None else "unknown")

    # Set context (structured data — user_id/page_url/rating; NOT raw email/text)
    sentry_sdk.set_context(
        "feedback",
        {
            "user_id": user.id,
            "page_url": data.page_url,
            "rating": data.rating,
        },
    )

    # Static message string — NEVER an f-string with variable data (CLAUDE.md)
    sentry_sdk.capture_message("feedback submitted", level="info")
