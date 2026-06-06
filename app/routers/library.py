"""Library (Games-surface) router: HTTP endpoints for the Games subtab.

Endpoints (mounted under /api/library):
- GET /games: paginated game archive filterable by a boolean flaw severity,
  each card carrying per-game B/M/I counts + curated chips (LIBG-08).

Thin HTTP layer only — validation, service call, response shaping. All business
logic (kernel re-call, counts, chip curation) lives in library_service.
"""

import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.library import LibraryGamesResponse, FlawStatsResponse
from app.services import library_service
from app.users import current_active_user

router = APIRouter(prefix="/library", tags=["library"])

# The Games filter offers only the mistake/blunder severity tiers (inaccuracies
# are count-only, never a filter). Constraining the Query type rejects anything
# else at the HTTP boundary (T-106-02V).
SeverityFilter = Literal["mistake", "blunder"]


@router.get("/games", response_model=LibraryGamesResponse)
async def get_library_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: str | None = Query(default=None),
) -> LibraryGamesResponse:
    """Return a paginated, flaw-filterable game archive (LIBG-08).

    When `severity` is supplied, only games with >=1 of the user's OWN plies at
    that severity (or worse) are returned. Each card carries per-game B/M/I counts
    and curated chips; chess.com / unanalyzed-lichess games carry
    analysis_state="no_engine_analysis" with severity_counts=null (never 0/0/0).
    When `color` is supplied ("white" or "black"), only games played as that color
    are returned.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_library_games(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=list(severity) if severity else None,
        offset=offset,
        limit=limit,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )


@router.get("/flaw-stats", response_model=FlawStatsResponse)
async def get_flaw_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: str | None = Query(default=None),
) -> FlawStatsResponse:
    """Return the stats-panel aggregate over the filtered analyzed-only set (LIBG-09).

    Per-severity counts + rates (per game and per 100 user-moves), the full tag
    distribution (tempo split, result-changing rate, phase histogram), a rolling-
    game trend, and the explicit >=90%-coverage analyzed denominator (analyzed_pct
    / analyzed_n / total_n). Same filter set as /games (no pagination). An empty
    analyzed set returns zeros, never an error. When `color` is supplied ("white"
    or "black"), stats are computed over only games played as that color.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_flaw_stats(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=list(severity) if severity else None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )
