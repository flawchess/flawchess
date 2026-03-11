"""Analysis service: W/D/L derivation, stats computation, and orchestration."""

import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analysis_repository import (
    HASH_COLUMN_MAP,
    query_all_results,
    query_matching_games,
)
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    GameRecord,
    WDLStats,
)

# Maps recency filter strings to timedelta offsets.
RECENCY_DELTAS: dict[str, datetime.timedelta] = {
    "week": datetime.timedelta(days=7),
    "month": datetime.timedelta(days=30),
    "3months": datetime.timedelta(days=90),
    "6months": datetime.timedelta(days=180),
    "year": datetime.timedelta(days=365),
}


def derive_user_result(
    result: str, user_color: str
) -> Literal["win", "draw", "loss"]:
    """Derive win/draw/loss from the raw PGN result and the user's color.

    Args:
        result: One of "1-0", "0-1", "1/2-1/2".
        user_color: One of "white", "black".

    Returns:
        "draw" for draws, "win" when the user's side won, "loss" otherwise.
    """
    if result == "1/2-1/2":
        return "draw"
    if (result == "1-0" and user_color == "white") or (
        result == "0-1" and user_color == "black"
    ):
        return "win"
    return "loss"


def recency_cutoff(recency: str | None) -> datetime.datetime | None:
    """Return a UTC datetime cutoff for the given recency filter, or None.

    Returns None for None or "all" (no recency restriction).
    """
    if recency is None or recency == "all":
        return None
    delta = RECENCY_DELTAS[recency]
    return datetime.datetime.now(tz=datetime.timezone.utc) - delta


async def analyze(
    session: AsyncSession,
    user_id: int,
    request: AnalysisRequest,
) -> AnalysisResponse:
    """Orchestrate a position analysis query and return W/D/L stats + games.

    Steps:
    1. Resolve hash column from match_side.
    2. Compute optional recency cutoff datetime.
    3. Fetch all (result, user_color) rows for aggregate stats.
    4. Compute W/D/L counts and percentages.
    5. Fetch paginated Game objects.
    6. Build GameRecord list and return AnalysisResponse.
    """
    hash_column = HASH_COLUMN_MAP[request.match_side]
    cutoff = recency_cutoff(request.recency)

    # --- Stats (full result set, no pagination) ---
    all_rows = await query_all_results(
        session=session,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=request.target_hash,
        time_control=request.time_control,
        rated=request.rated,
        recency_cutoff=cutoff,
        color=request.color,
    )

    wins = draws = losses = 0
    for result, user_color in all_rows:
        outcome = derive_user_result(result, user_color)
        if outcome == "win":
            wins += 1
        elif outcome == "draw":
            draws += 1
        else:
            losses += 1

    total = wins + draws + losses
    if total > 0:
        win_pct = round(wins / total * 100, 1)
        draw_pct = round(draws / total * 100, 1)
        loss_pct = round(losses / total * 100, 1)
    else:
        win_pct = draw_pct = loss_pct = 0.0

    stats = WDLStats(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
    )

    # --- Paginated game list ---
    games, matched_count = await query_matching_games(
        session=session,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=request.target_hash,
        time_control=request.time_control,
        rated=request.rated,
        recency_cutoff=cutoff,
        color=request.color,
        offset=request.offset,
        limit=request.limit,
    )

    game_records = [
        GameRecord(
            game_id=g.id,
            opponent_username=g.opponent_username,
            user_result=derive_user_result(g.result, g.user_color),
            played_at=g.played_at,
            time_control_bucket=g.time_control_bucket,
            platform=g.platform,
            platform_url=g.platform_url,
        )
        for g in games
    ]

    return AnalysisResponse(
        stats=stats,
        games=game_records,
        matched_count=matched_count,
        offset=request.offset,
        limit=request.limit,
    )
