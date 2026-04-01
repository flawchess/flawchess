"""Stats service: aggregation logic for rating history and global stats."""

import datetime
from typing import Any, TypedDict

from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repository import (
    query_position_wdl_batch,
    query_rating_history,
    query_results_by_color,
    query_results_by_time_control,
    query_top_openings_sql_wdl,
)
from app.schemas.stats import (
    GlobalStatsResponse,
    MostPlayedOpeningsResponse,
    OpeningWDL,
    RatingDataPoint,
    RatingHistoryResponse,
    WDLByCategory,
)
from app.services.analysis_service import recency_cutoff

# Minimum number of games required for an opening to appear in top openings.
MIN_GAMES_FOR_OPENING = 1

# Maximum number of top openings to return per color.
TOP_OPENINGS_LIMIT = 10

# Minimum ply count for an opening to be included: white needs 1 ply, black needs 2.
MIN_PLY_WHITE = 1
MIN_PLY_BLACK = 2

# Ordered time control buckets for consistent output ordering.
_TIME_CONTROL_ORDER = ["bullet", "blitz", "rapid", "classical"]

# Color ordering for consistent output.
_COLOR_ORDER = ["white", "black"]


class FilterParams(TypedDict):
    """Typed filter parameters for position WDL batch queries.

    Created per D-02: TypedDicts for internal data structures.
    Matches keyword parameters of query_position_wdl_batch in stats_repository.py.
    """
    time_control: list[str] | None
    platform: list[str] | None
    rated: bool | None
    opponent_type: str
    recency_cutoff: datetime.datetime | None


async def get_rating_history(
    session: AsyncSession,
    user_id: int,
    recency: str | None,
    platform: str | None = None,
) -> RatingHistoryResponse:
    """Return per-platform per-game rating data points.

    Calls recency_cutoff() to resolve the optional recency filter, queries
    both platforms in sequence, and maps rows to RatingDataPoint lists.

    When platform is "chess.com", only chess.com data is queried; lichess is empty.
    When platform is "lichess", only lichess data is queried; chess.com is empty.
    When platform is None, both platforms are queried.
    """
    cutoff = recency_cutoff(recency)

    if platform == "chess.com":
        chesscom_rows = await query_rating_history(
            session, user_id=user_id, platform="chess.com", recency_cutoff=cutoff
        )
        lichess_rows: list = []
    elif platform == "lichess":
        chesscom_rows = []
        lichess_rows = await query_rating_history(
            session, user_id=user_id, platform="lichess", recency_cutoff=cutoff
        )
    else:
        chesscom_rows = await query_rating_history(
            session, user_id=user_id, platform="chess.com", recency_cutoff=cutoff
        )
        lichess_rows = await query_rating_history(
            session, user_id=user_id, platform="lichess", recency_cutoff=cutoff
        )

    def rows_to_points(rows: list) -> list[RatingDataPoint]:
        points = []
        for date_val, rating, tc_bucket in rows:
            # date_val is a date object from CAST(... AS DATE) — use isoformat directly
            date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
            points.append(
                RatingDataPoint(
                    date=date_str,
                    rating=rating,
                    time_control_bucket=tc_bucket or "unknown",
                )
            )
        return points

    return RatingHistoryResponse(
        chess_com=rows_to_points(chesscom_rows),
        lichess=rows_to_points(lichess_rows),
    )


def _rows_to_wdl_categories(
    rows: list[Row[Any]],
    label_fn,
    label_order: list[str],
) -> list[WDLByCategory]:
    """Convert SQL-aggregated (label_key, total, wins, draws, losses) rows to WDLByCategory list.

    Rows are already aggregated by the database — no Python-side counting needed.
    """
    row_map = {row[0]: row for row in rows}

    categories = []
    for key in label_order:
        if key not in row_map:
            continue
        _, total, wins, draws, losses = row_map[key]
        if total > 0:
            win_pct = round(wins / total * 100, 1)
            draw_pct = round(draws / total * 100, 1)
            loss_pct = round(losses / total * 100, 1)
        else:
            win_pct = draw_pct = loss_pct = 0.0

        categories.append(
            WDLByCategory(
                label=label_fn(key),
                wins=wins,
                draws=draws,
                losses=losses,
                total=total,
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
            )
        )

    return categories


async def get_global_stats(
    session: AsyncSession,
    user_id: int,
    recency: str | None,
    platform: str | None = None,
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Both queries return SQL-aggregated (label, total, wins, draws, losses) rows.
    """
    cutoff = recency_cutoff(recency)

    tc_rows = await query_results_by_time_control(
        session, user_id=user_id, recency_cutoff=cutoff, platform=platform
    )
    color_rows = await query_results_by_color(
        session, user_id=user_id, recency_cutoff=cutoff, platform=platform
    )

    by_time_control = _rows_to_wdl_categories(
        rows=tc_rows,
        label_fn=lambda key: key.title(),
        label_order=_TIME_CONTROL_ORDER,
    )

    by_color = _rows_to_wdl_categories(
        rows=color_rows,
        label_fn=lambda key: key.title(),
        label_order=_COLOR_ORDER,
    )

    return GlobalStatsResponse(
        by_time_control=by_time_control,
        by_color=by_color,
    )


async def get_most_played_openings(
    session: AsyncSession,
    user_id: int,
    recency: str | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
) -> MostPlayedOpeningsResponse:
    """Return top 10 most played openings per color with position-based game counts.

    Opening selection uses the games table (by opening_eco/name), but the
    displayed game count comes from game_positions (games passing through
    the position). This matches the count shown in "Results by Opening".
    """
    cutoff = recency_cutoff(recency)

    white_rows = await query_top_openings_sql_wdl(
        session,
        user_id=user_id,
        color="white",
        min_games=MIN_GAMES_FOR_OPENING,
        limit=TOP_OPENINGS_LIMIT,
        min_ply=MIN_PLY_WHITE,
        recency_cutoff=cutoff,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
    )
    black_rows = await query_top_openings_sql_wdl(
        session,
        user_id=user_id,
        color="black",
        min_games=MIN_GAMES_FOR_OPENING,
        limit=TOP_OPENINGS_LIMIT,
        min_ply=MIN_PLY_BLACK,
        recency_cutoff=cutoff,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
    )

    # Batch-query position-based WDL — games passing through each position,
    # which is typically higher than the opening-name count because many
    # openings share early moves. This matches "Results by Opening" counts.
    # FilterParams TypedDict per D-02. Passed explicitly (not via **) for ty compatibility.
    filter_params: FilterParams = FilterParams(
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
    )
    white_position_wdl = await query_position_wdl_batch(
        session, user_id,
        [row[4] for row in white_rows if row[4] is not None],
        color="white",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
    )
    black_position_wdl = await query_position_wdl_batch(
        session, user_id,
        [row[4] for row in black_rows if row[4] is not None],
        color="black",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
    )

    def rows_to_openings(
        rows: list[Row[Any]],
        position_wdl: dict,
    ) -> list[OpeningWDL]:
        openings = []
        for eco, name, pgn, fen, full_hash, total, wins, draws, losses in rows:
            # Use position-based WDL if available, falling back to
            # opening-name WDL for openings without a hash
            pos = position_wdl.get(full_hash) if full_hash else None
            if pos:
                total, wins, draws, losses = pos.total, pos.wins, pos.draws, pos.losses
            if total > 0:
                win_pct = round(wins / total * 100, 1)
                draw_pct = round(draws / total * 100, 1)
                loss_pct = round(losses / total * 100, 1)
            else:
                win_pct = draw_pct = loss_pct = 0.0
            openings.append(
                OpeningWDL(
                    opening_eco=eco,
                    opening_name=name,
                    label=f"{name} ({eco})",
                    pgn=pgn,
                    fen=fen,
                    full_hash=str(full_hash) if full_hash is not None else "",
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    total=total,
                    win_pct=win_pct,
                    draw_pct=draw_pct,
                    loss_pct=loss_pct,
                )
            )
        # Sort by position-based game count descending (may differ from
        # the opening-name-based order returned by the SQL query)
        openings.sort(key=lambda o: o.total, reverse=True)
        return openings

    return MostPlayedOpeningsResponse(
        white=rows_to_openings(white_rows, white_position_wdl),
        black=rows_to_openings(black_rows, black_position_wdl),
    )
