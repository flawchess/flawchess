"""Library (Games-surface) router: HTTP endpoints for the Games subtab.

Endpoints (mounted under /api/library):
- GET /games: paginated game archive filterable by a boolean flaw severity,
  each card carrying per-game B/M/I counts + curated chips (LIBG-08).
- GET /flaws: paginated flat list of individual flawed positions, one row per
  flaw, ordered recent-first, with game metadata for the row header (Plan
  108-05, D-05/D-07/D-08).

Thin HTTP layer only — validation, service call, response shaping. All business
logic (kernel re-call, counts, chip curation) lives in library_service.
"""

import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.library import (
    FlawComparisonResponse,
    FlawStatsResponse,
    GameFlawCard,
    LibraryFlawsResponse,
    LibraryGamesResponse,
    TacticComparisonResponse,
)
from app.services import library_service
from app.users import current_active_user

router = APIRouter(prefix="/library", tags=["library"])

# The Games/Flaws filter offers only the mistake/blunder severity tiers
# (inaccuracies are count-only, never a filter; game_flaws stores M+B only
# per D-03). Constraining the Query type rejects anything else at the HTTP
# boundary (T-106-02V, T-108-11).
SeverityFilter = Literal["mistake", "blunder"]

# Tag filter for GET /library/games and /library/flaws — the 7 classification
# tags plus the 3 phase tags. Phase tags became a first-class filter family in
# Quick 260612-fow (build_flaw_filter_clauses filters on game_flaws.phase),
# superseding the earlier display-only decision. FastAPI 422-rejects any value
# outside this Literal (T-108-11 mitigation).
FlawTagFilter = Literal[
    "miss",
    "lucky",
    "reversed",
    "squandered",
    "low-clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame",
]

# Orientation filter for GET /library/flaws (Phase 129, TACUI-06/D-07). "either"
# is OR across both missed_* and allowed_* tactic columns; "missed"/"allowed"
# select a single orientation. Mirrors TacticOrientation in library_repository.
# FastAPI 422-rejects any value outside this Literal at the HTTP boundary.
TacticOrientationFilter = Literal["either", "missed", "allowed"]


@router.get("/games", response_model=LibraryGamesResponse)
async def get_library_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    tag: list[FlawTagFilter] | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    tactic_family: list[str] | None = Query(default=None),
    tactic_orientation: TacticOrientationFilter = Query(default="either"),
    min_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    max_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: str | None = Query(default=None),
) -> LibraryGamesResponse:
    """Return a paginated, flaw-filterable game archive (LIBG-08).

    When `severity` is supplied, only games with >=1 of the user's OWN plies at
    that severity (or worse) are returned. When `tag` is supplied, only games
    containing a SINGLE flaw satisfying ALL selected tag families are returned
    (OR within family, AND across families — single-flaw EXISTS semantics,
    SEED-038). When `tactic_family` is supplied (Quick 260620-pza), only games
    with >=1 flaw whose tactic motif (in the orientation's column, within the
    depth range) is in the selected families are returned — the same tactic
    EXISTS the Flaws tab uses. severity, tag and tactic_family combine. Each card
    carries per-game B/M/I counts and curated chips; chess.com / unanalyzed-
    lichess games carry analysis_state="no_engine_analysis" with
    severity_counts=null (never 0/0/0). When `color` is supplied ("white" or
    "black"), only games played as that color are returned.
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
        flaw_tags=list(tag) if tag else None,
        tactic_families=list(tactic_family) if tactic_family else None,
        tactic_orientation=tactic_orientation,
        min_tactic_depth=min_tactic_depth,
        max_tactic_depth=max_tactic_depth,
        offset=offset,
        limit=limit,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )


@router.get("/games/{game_id}", response_model=GameFlawCard)
async def get_library_game(
    game_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    tactic_family: list[str] | None = Query(default=None),
    tactic_orientation: TacticOrientationFilter = Query(default="either"),
    min_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    max_tactic_depth: int | None = Query(default=None, ge=0, le=11),
) -> GameFlawCard:
    """Return a single GameFlawCard for the authenticated user's game (SC-7).

    IDOR guard (T-112-01): returns 404 when the game does not exist OR when
    the game belongs to a different user. Returns 404 (not 403) to avoid
    confirming whether the id exists for the requester. game_id is typed int
    so FastAPI rejects non-integer values with 422 (T-112-05).

    Quick 260621-sm8: accepts the same tactic filter params as /games so the
    "View game" modal (opened from a flaw card with an active filter) nulls
    non-matching tactic slots per-slot, matching the list. Without these params
    the modal showed every tactic regardless of the depth/orientation/family
    filter the user had set (the bug being fixed). Defaults (no family, either,
    no depth bounds) leave both slots populated, so direct opens are unchanged.
    """
    card = await library_service.get_library_game(
        session,
        user_id=user.id,
        game_id=game_id,
        tactic_families=list(tactic_family) if tactic_family else None,
        tactic_orientation=tactic_orientation,
        min_tactic_depth=min_tactic_depth,
        max_tactic_depth=max_tactic_depth,
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return card


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
    distribution (tempo split, reversed/squandered rates, phase histogram), a
    rolling-game trend, and the explicit >=90%-coverage analyzed denominator
    (analyzed_pct / analyzed_n / total_n). Same filter set as /games (no
    pagination). An empty analyzed set returns zeros, never an error. When
    `color` is supplied ("white" or "black"), stats are computed over only games
    played as that color.
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


@router.get("/flaw-comparison", response_model=FlawComparisonResponse)
async def get_flaw_comparison(
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
) -> FlawComparisonResponse:
    """Return the 15-bullet you-vs-opponent comparison for the filtered analyzed set (Phase 115).

    user_id is taken exclusively from the authenticated user — never from a
    request parameter (IDOR prevention, T-115-01 / T-108-10 pattern).
    Returns below_gate=True with empty bullets when analyzed_n < 20 (FLAWCMP-05, D-09).
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_flaw_comparison(
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


@router.get("/tactic-comparison", response_model=TacticComparisonResponse)
async def get_tactic_comparison(
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
    tactic_families: list[str] | None = Query(default=None),
) -> TacticComparisonResponse:
    """Per-family tactic motif you-vs-opponent comparison (Phase 126/129).

    Phase 129 (D-13/D-14, taxonomy redesign): returns up to 20 orientation-tagged bullets
    (10 families x 2 orientations); top-6 families by Missed you_rate appear first, then overflow.
    No orientation query param — grid always shows both orientations (D-09).

    user_id taken exclusively from the authenticated user — never from a
    request parameter (IDOR prevention, T-126-01).
    Returns below_gate=True with empty bullets when analyzed_n < TACTIC_COMPARISON_GATE.
    tactic_families: optional multi-select to narrow to specific motif families
    (e.g. "fork", "skewer"); unknown/dropped keys are silently ignored (T-126-02).
    Backend is NOT beta-gated per D-01a — frontend gating enforces beta rollout.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_tactic_comparison(
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
        tactic_families=tactic_families,
    )


@router.get("/flaws", response_model=LibraryFlawsResponse)
async def get_library_flaws(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    tag: list[FlawTagFilter] | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    color: str | None = Query(default=None),
    tactic_family: list[str] | None = Query(default=None),
    tactic_orientation: TacticOrientationFilter = Query(default="either"),
    min_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    max_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> LibraryFlawsResponse:
    """Return a paginated flat list of individual flawed positions (Plan 108-05).

    One row per flawed position from game_flaws, ordered recent-first
    (g.played_at DESC, f.ply ASC — D-07), with each row carrying the full
    miniboard display payload (fen, move_san from game_positions join, severity,
    tags, before/after eval from game_positions) and game metadata (opponent,
    ratings, date, result). Phase 112 (D-05/D-07/D-08): es_before/es_after dropped;
    raw eval + ratings added.

    Severity defaults to M+B when omitted (D-08); game_flaws stores M+B only
    (D-03). Phase tags (opening/middlegame/endgame) in `tag` filter on the
    game_flaws.phase column (OR within the phase family, Quick 260612-fow).

    user_id is taken exclusively from the authenticated user (never from a
    request parameter) to prevent IDOR (T-108-10).
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_library_flaws(
        session,
        user_id=user.id,
        severity=list(severity) if severity else [],
        tags=list(tag) if tag else [],
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        color=color,
        tactic_families=list(tactic_family) if tactic_family else None,
        tactic_orientation=tactic_orientation,
        min_tactic_depth=min_tactic_depth,
        max_tactic_depth=max_tactic_depth,
        offset=offset,
        limit=limit,
    )
