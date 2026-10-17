"""Library router: thin HTTP layer (validation, service call, response shaping).

Business logic lives in library_service, except tactic-lines, which reads
library_repository directly.
"""

import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import library_repository
from app.schemas.library import (
    FlawComparisonResponse,
    FlawStatsResponse,
    GameFlawCard,
    LibraryFlawsResponse,
    LibraryGamesResponse,
    TacticComparisonResponse,
    TacticLinesResponse,
)
from app.services import library_service
from app.users import current_active_user

router = APIRouter(prefix="/library", tags=["library"])

# The Games/Flaws filter offers only the mistake/blunder severity tiers
# (inaccuracies are count-only, never a filter; game_flaws stores M+B only).
# Constraining the Query type rejects anything else at the HTTP boundary.
SeverityFilter = Literal["mistake", "blunder"]

# Tag filter for GET /library/games and /library/flaws — the 7 classification
# tags plus the 3 phase tags. Phase tags are a first-class filter family
# (build_flaw_filter_clauses filters on game_flaws.phase). FastAPI 422-rejects
# any value outside this Literal.
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

# Orientation filter for GET /library/flaws. "either" is OR across both missed_* and
# allowed_* tactic columns; "missed"/"allowed" select a single orientation. Mirrors
# TacticOrientation in library_repository. FastAPI 422-rejects any value outside this
# Literal at the HTTP boundary.
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
    has_gem: bool | None = Query(default=None),
    has_great: bool | None = Query(default=None),
    include_pasted: bool = Query(default=False),
) -> LibraryGamesResponse:
    """Return a paginated, flaw-filterable game archive.

    When `severity` is supplied, only games with >=1 of the user's OWN plies at
    that severity (or worse) are returned. When `tag` is supplied, only games
    containing a SINGLE flaw satisfying ALL selected tag families are returned
    (OR within family, AND across families — single-flaw EXISTS semantics).
    When `tactic_family` is supplied, only games with >=1 flaw whose tactic motif (in the
    orientation's column, within the depth range) is in the selected families are returned —
    the same tactic EXISTS the Flaws tab uses. severity, tag and tactic_family combine. Each
    card carries per-game B/M/I counts and curated chips; chess.com / unanalyzed- lichess
    games carry analysis_state="no_engine_analysis" with severity_counts=null (never 0/0/0).
    When `color` is supplied ("white" or "black"), only games played as that color are
    returned. When `has_gem` / `has_great` is True, only games with >=1 of the user's OWN
    plies classifying as a gem/great best move are returned; both True is a union (gem OR
    great). `include_pasted` is the Library-only opt-in that reveals `platform='pgn'` games,
    off by default, additive to whatever population this tab already shows.
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
        has_gem=has_gem,
        has_great=has_great,
        include_pasted=include_pasted,
    )


@router.get("/games/{game_id}", response_model=GameFlawCard)
async def get_library_game(
    game_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> GameFlawCard:
    """Return a single GameFlawCard for any game, by id (analysis-page view).

    Intentionally NOT owner-scoped. Any authenticated user may
    inspect any game by url (e.g. /analysis?game_id=640125) for opponent scouting
    and game sharing. The current_active_user dependency enforces "logged in";
    the returned data is scoped to the game's owner in the service layer. Returns
    404 only when the game does not exist. game_id is typed int so FastAPI rejects
    non-integer values with 422.

    This endpoint accepts no severity/tactic filter params. It does no game
    selection, so such params would only drive per-slot tactic pruning; the card
    always shows every valid tactic + context tag regardless of the Games-tab
    filter.
    """
    card = await library_service.get_library_game(
        session,
        game_id=game_id,
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
    include_pasted: bool = Query(default=False),
) -> FlawStatsResponse:
    """Return the analyzed-game count and per-TC Flaws Timeline.

    trend_by_tc is one rolling-game trend series per time control (the client picks
    the selected TC's series); analyzed_n is the analyzed-game count of the filtered
    set. The severity counts, rates and tag distribution this
    endpoint used to return are gone: the tiles read /flaw-comparison. Same filter
    set as /games (no pagination). An empty analyzed set returns zeros, never an
    error. When `color` is supplied ("white" or "black"), stats are computed over
    only games played as that color. `include_pasted` is the Library-only
    opt-in that reveals `platform='pgn'` games, off by default, additive to
    whatever population this surface already shows.
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
        include_pasted=include_pasted,
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
    include_pasted: bool = Query(default=False),
) -> FlawComparisonResponse:
    """Return the per-TC you-vs-opponent comparison for the filtered analyzed set.

    tcs[] lists every time control the sidebar filter allows that has at least one
    analyzed game, each with 12 bullets; below-gate TCs keep their bullets
    The TC switch is client-side: no TC request parameter exists.

    user_id is taken exclusively from the authenticated user — never from a
    request parameter (IDOR prevention).
    `include_pasted` is the Library-only opt-in that reveals
    `platform='pgn'` games, off by default, additive to whatever population
    this surface already shows.
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
        include_pasted=include_pasted,
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
    include_pasted: bool = Query(default=False),
) -> TacticComparisonResponse:
    """Per-TC tactic motif you-vs-opponent comparison, per 100 games.

    Returns `tcs`, one entry per time control that the filters
    allow and that has at least one analyzed game (bullet..classical order). Each TC carries
    38 bullets (19 families x missed/allowed) in fixed FAMILY_TO_MOTIF_INTS order, missed
    before allowed, also when the TC is below the analyzed-game gate. Rates and gaps are per
    100 games. No ranking or top-N. No query parameter selects a TC (the switch is client-side).

    user_id taken exclusively from the authenticated user — never from a
    request parameter (IDOR prevention).
    tactic_families: optional multi-select to narrow to specific motif families
    (e.g. "fork", "skewer"); unknown/dropped keys are silently ignored.
    Backend is NOT beta-gated — frontend gating enforces beta rollout.
    `include_pasted` is the Library-only opt-in that reveals
    `platform='pgn'` games, off by default, additive to whatever population
    this surface already shows.
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
        include_pasted=include_pasted,
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
    include_pasted: bool = Query(default=False),
) -> LibraryFlawsResponse:
    """Return a paginated flat list of individual flawed positions.

    One row per flawed position from game_flaws, ordered recent-first
    (g.played_at DESC, f.ply ASC), with each row carrying the full
    miniboard display payload (fen, move_san from game_positions join, severity,
    tags, before/after eval from game_positions) and game metadata (opponent,
    ratings, date, result).

    Severity defaults to M+B when omitted; game_flaws stores M+B only. Phase tags
    (opening/middlegame/endgame) in `tag` filter on the game_flaws.phase column
    (OR within the phase family).

    user_id is taken exclusively from the authenticated user (never from a
    request parameter) to prevent IDOR. `include_pasted` is the Library-only
    opt-in that reveals `platform='pgn'` games, off by default, additive to
    whatever population this tab already shows — and computed from this
    surface's own default (chess.com/lichess), so it never newly admits
    flawchess bot games.
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
        include_pasted=include_pasted,
    )


@router.get("/flaws/{game_id}/{ply}/tactic-lines", response_model=TacticLinesResponse)
async def get_tactic_lines(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    game_id: int,
    ply: int,
) -> TacticLinesResponse:
    """PV walk for the TacticLineExplorer.

    Returns both orientations' SAN move lists, raw 0-based depths, motif strings,
    and the full decision-position FEN for chess.js board initialization.

    NOT owner-scoped — any authenticated user may expand the
    tactic lines of any game they inspect on the analysis page (mirrors
    get_library_game). The current_active_user dependency enforces "logged in".
    game_id uniquely identifies the game (and thus its owner), so the flaw/PV
    rows resolve to the owner's data without a requester filter. Returns 404 when
    no flaw exists at (game_id, ply).

    game_id and ply are typed int so FastAPI auto-422-rejects non-integer values
    before the handler runs.
    """
    result = await library_repository.fetch_tactic_lines(session, game_id=game_id, ply=ply)
    if result is None:
        raise HTTPException(status_code=404, detail="Flaw not found")
    return result
