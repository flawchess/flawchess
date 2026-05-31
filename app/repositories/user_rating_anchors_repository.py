"""Repository for user_rating_anchors: UPSERT + per-user SELECT.

D-12 Reversal Amendment (2026-05-27) -- see CONTEXT.md §Amendment and
``.planning/notes/percentile-anchor-d12-reversal.md`` for the standalone
design-decision record.

Phase 94.4 Plan 09 (reshaped from Plan 02) -- implements the write/read path
for materialised per-(user, TC) game-weighted blended rating anchors used by
the peer-relative percentile chip lookup.

The blended anchor pools per-game converted chess.com ratings with native
Lichess ratings and takes the median of the pool (see module docstring of
``app/models/user_rating_anchors.py``). The original Lichess-precedence rule
(D-12) is superseded; this repository is now platform-agnostic -- it stores
counts + native medians for both platforms and the blended anchor.

V4 Information Disclosure mitigation: both ``upsert_anchor`` and
``fetch_anchors_for_user`` require ``user_id`` as a keyword argument. The
caller in Plan 10 (and downstream consumers) must pass ``current_user.id``
from the FastAPI-Users dependency. Never accept ``user_id`` as a query
parameter from the client. This pattern mirrors
``app/repositories/user_benchmark_percentiles_repository.py:134-136`` per
Phase 94.4 PATTERNS line 140 / 813.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_rating_anchors import (
    TimeControlBucket,
    UserRatingAnchor,
)


@dataclass(frozen=True)
class RatingAnchorRow:
    """Internal dataclass for a single user_rating_anchors row.

    Used by ``fetch_anchors_for_user`` to return structured data with
    attribute access. Frozen (immutable) per CLAUDE.md internal-structured-
    data rule.

    Fields:
      anchor_rating: Blended median rating (Lichess-equivalent). Always
        populated when a row exists.
      n_chesscom_games: Count of non-Daily chess.com games used. >= 0.
      n_lichess_games: Count of Lichess games used. >= 0.
      chesscom_median_native: Median of the user's RAW (pre-conversion)
        chess.com ratings in this TC. None when n_chesscom_games == 0.
        Tooltip-disclosure source (D-07 bullet 4, amendment-revised).
      lichess_median_native: Median of the user's native Lichess ratings
        in this TC. None when n_lichess_games == 0. Tooltip-disclosure source.

    Note: ``computed_at`` is intentionally NOT exposed here -- it is a
    server-side timestamp refreshed on every UPSERT and is only needed for
    tests that read raw ORM rows (see test_user_rating_anchors_repository.py
    Test 7).
    """

    anchor_rating: int
    n_chesscom_games: int
    n_lichess_games: int
    chesscom_median_native: int | None
    lichess_median_native: int | None


async def upsert_anchor(
    session: AsyncSession,
    *,
    user_id: int,
    time_control_bucket: TimeControlBucket,
    anchor_rating: int,
    n_chesscom_games: int,
    n_lichess_games: int,
    chesscom_median_native: int | None,
    lichess_median_native: int | None,
) -> None:
    """Insert or update one (user_id, time_control_bucket) row.

    Uses ``INSERT ... ON CONFLICT (user_id, time_control_bucket) DO UPDATE``
    so the operation is atomic and idempotent. The caller is responsible
    for committing the session after all writes in a unit of work are done.

    V4 mitigation: ``user_id`` is keyword-only. Callers MUST source it from
    the authenticated ``current_user.id`` FastAPI-Users dep; never accept it
    as a query/path parameter (Phase 94.4 PATTERNS line 813).

    Args:
        session: AsyncSession. Caller commits.
        user_id: Internal user PK (V4: from authenticated dep, never user input).
        time_control_bucket: One of bullet/blitz/rapid/classical.
        anchor_rating: Blended median (Lichess-equivalent) per the D-12 Reversal
            Amendment algorithm.
        n_chesscom_games: Count of non-Daily chess.com games used. >= 0.
        n_lichess_games: Count of Lichess games used. >= 0.
        chesscom_median_native: Pre-conversion chess.com median when
            n_chesscom_games > 0; None otherwise (D-07 bullet 4 tooltip).
        lichess_median_native: Native Lichess median when n_lichess_games > 0;
            None otherwise (D-07 bullet 4 tooltip).
    """
    stmt = pg_insert(UserRatingAnchor).values(
        user_id=user_id,
        time_control_bucket=time_control_bucket,
        anchor_rating=anchor_rating,
        n_chesscom_games=n_chesscom_games,
        n_lichess_games=n_lichess_games,
        chesscom_median_native=chesscom_median_native,
        lichess_median_native=lichess_median_native,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "time_control_bucket"],
        set_={
            "anchor_rating": stmt.excluded.anchor_rating,
            "n_chesscom_games": stmt.excluded.n_chesscom_games,
            "n_lichess_games": stmt.excluded.n_lichess_games,
            "chesscom_median_native": stmt.excluded.chesscom_median_native,
            "lichess_median_native": stmt.excluded.lichess_median_native,
            "computed_at": func.now(),  # server-side NOW() refresh on every update
        },
    )
    await session.execute(stmt)


async def fetch_anchors_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[TimeControlBucket, RatingAnchorRow]:
    """Return all rating-anchor rows for a user, keyed by time_control_bucket.

    V4 Information Disclosure mitigation: caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_user.id``); never accept
    ``user_id`` as a query parameter from the client (Phase 94.4 PATTERNS
    line 813).

    Returns only the TCs that have anchors -- missing TCs are absent from
    the dict, not represented as None placeholders. An absent entry means
    the user is below the per-TC inclusion floor for that TC (suppression
    semantics: no row => no anchor => chip suppresses naturally).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK.

    Returns:
        Dict keyed by TimeControlBucket, values are RatingAnchorRow dataclasses.
        Empty dict when the user has no anchor rows (e.g. newly imported user
        whose Stage A has not yet run, or below-floor on all TCs).
    """
    result = await session.execute(
        select(
            UserRatingAnchor.time_control_bucket,
            UserRatingAnchor.anchor_rating,
            UserRatingAnchor.n_chesscom_games,
            UserRatingAnchor.n_lichess_games,
            UserRatingAnchor.chesscom_median_native,
            UserRatingAnchor.lichess_median_native,
        ).where(UserRatingAnchor.user_id == user_id)
    )
    rows = result.fetchall()
    return {
        row.time_control_bucket: RatingAnchorRow(
            anchor_rating=row.anchor_rating,
            n_chesscom_games=row.n_chesscom_games,
            n_lichess_games=row.n_lichess_games,
            chesscom_median_native=row.chesscom_median_native,
            lichess_median_native=row.lichess_median_native,
        )
        for row in rows
    }


async def has_any_anchor(session: AsyncSession, *, user_id: int) -> bool:
    """Return True if at least one rating-anchor row exists for the user.

    A committed anchor row is proof that ``compute_stage_a`` ran to completion
    for this user: Stage A computes anchors AND the eval-independent
    ``score_gap`` percentiles in one transaction and commits them together, so
    an anchor row is only visible to other sessions once that whole transaction
    has committed.

    This is the "Stage A has run" signal for the ``GET /imports/readiness``
    settled-empty escape (bug fix endgame-percentiles-missing, prod user 146):
    a user who is above the 30-game anchor floor but below the per-metric
    endgame-population floor (e.g. 33 rating-eligible games but only 22 reach an
    endgame) gets an anchor row yet zero ``user_benchmark_percentiles`` rows, by
    design. ``has_any_rows`` stays False forever and the anchor-floor probe
    reports above-floor, so without this signal the endgames page locks
    permanently. ``anchor row exists AND no percentile rows`` means Stage A ran
    and the user is too sparse for any metric — unlock instead of spinning.

    V4 Information Disclosure mitigation: caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_active_user.id``); never accept
    ``user_id`` as a query parameter from the client.

    Uses a bounded-count query (``LIMIT 1``) so it exits after the first match.

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK. Keyword-only to match the
            V4 access-control convention used by ``fetch_anchors_for_user``.

    Returns:
        True if any anchor row exists for the user; False otherwise.
    """
    result = await session.execute(
        select(func.count(UserRatingAnchor.user_id))
        .where(UserRatingAnchor.user_id == user_id)
        .limit(1)
    )
    return (result.scalar() or 0) > 0


__all__ = [
    "RatingAnchorRow",
    "upsert_anchor",
    "fetch_anchors_for_user",
    "has_any_anchor",
]
