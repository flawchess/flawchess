"""Repository for user_rating_anchors: UPSERT + per-user SELECT.

Phase 94.4 Plan 02 — implements the write/read path for materialised
per-(user, TC) median rating anchors used by the peer-relative percentile
chip lookup (D-04).

V4 Information Disclosure mitigation: both ``upsert_anchor`` and
``fetch_anchors_for_user`` require ``user_id`` as a keyword argument. The
caller in Plan 05 (and downstream consumers) must pass ``current_user.id``
from the FastAPI-Users dependency. Never accept ``user_id`` as a query
parameter from the client. This pattern mirrors
``app/repositories/user_benchmark_percentiles_repository.py:102-126`` per
Phase 94.4 PATTERNS line 140 / 813.

Lichess-precedence (D-12) is implemented in the Python wrapper that calls
``upsert_anchor`` (Plan 05) — this repository is platform-agnostic and
takes ``source_platform`` + ``chesscom_raw_rating`` as direct arguments.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.user_rating_anchors import (
    AnchorSource,
    TimeControlBucket,
    UserRatingAnchor,
)


@dataclass(frozen=True)
class RatingAnchorRow:
    """Internal dataclass for a single user_rating_anchors row.

    Used by ``fetch_anchors_for_user`` to return structured data with
    attribute access. Frozen (immutable) per CLAUDE.md internal-structured-
    data rule.

    ``chesscom_raw_rating`` is None when ``source_platform == 'lichess'``;
    populated with the user's pre-conversion chess.com rating when
    ``source_platform == 'chesscom'`` (D-07 bullet 4 tooltip disclosure).
    """

    anchor_rating: int
    source_platform: AnchorSource
    chesscom_raw_rating: int | None
    n_games: int


async def upsert_anchor(
    session: AsyncSession,
    *,
    user_id: int,
    time_control_bucket: TimeControlBucket,
    anchor_rating: int,
    source_platform: AnchorSource,
    chesscom_raw_rating: int | None,
    n_games: int,
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
        anchor_rating: Median rating over the user's recent pool. For
            ``source_platform='chesscom'`` this is the POST-conversion
            (Lichess-equivalent) rating per D-12.
        source_platform: 'lichess' wins per D-12 precedence; 'chesscom'
            only when the user has < MEDIAN_ANCHOR_MIN_GAMES on Lichess.
        chesscom_raw_rating: pre-conversion chess.com rating when
            source_platform='chesscom'; None when source_platform='lichess'
            (D-07 bullet 4 tooltip provenance).
        n_games: Count of games used to compute the median anchor (must be
            >= MEDIAN_ANCHOR_MIN_GAMES per D-04).
    """
    stmt = pg_insert(UserRatingAnchor).values(
        user_id=user_id,
        time_control_bucket=time_control_bucket,
        anchor_rating=anchor_rating,
        source_platform=source_platform,
        chesscom_raw_rating=chesscom_raw_rating,
        n_games=n_games,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "time_control_bucket"],
        set_={
            "anchor_rating": stmt.excluded.anchor_rating,
            "source_platform": stmt.excluded.source_platform,
            "chesscom_raw_rating": stmt.excluded.chesscom_raw_rating,
            "n_games": stmt.excluded.n_games,
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

    Returns only the TCs that have anchors — missing TCs are absent from
    the dict, not represented as None placeholders. An absent entry means
    the user is below the per-TC inclusion floor for that TC (D-04
    suppression semantics: no row → no anchor → chip suppresses).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK.

    Returns:
        Dict keyed by TimeControlBucket, values are RatingAnchorRow dataclasses.
    """
    result = await session.execute(
        select(
            UserRatingAnchor.time_control_bucket,
            UserRatingAnchor.anchor_rating,
            UserRatingAnchor.source_platform,
            UserRatingAnchor.chesscom_raw_rating,
            UserRatingAnchor.n_games,
        ).where(UserRatingAnchor.user_id == user_id)
    )
    rows = result.fetchall()
    return {
        row.time_control_bucket: RatingAnchorRow(
            anchor_rating=row.anchor_rating,
            source_platform=row.source_platform,
            chesscom_raw_rating=row.chesscom_raw_rating,
            n_games=row.n_games,
        )
        for row in rows
    }


__all__ = ["RatingAnchorRow", "upsert_anchor", "fetch_anchors_for_user"]
