"""Stats service: aggregation logic for rating history and global stats."""

import chess as chess_lib
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repository import (
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
from app.services.zobrist import compute_hashes

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
    rows: list[tuple],
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
    """Return top 10 most played openings per color with SQL-side WDL stats.

    JOINs to openings_dedup for pgn/fen. Filters by recency, time_control,
    platform, rated, and opponent_type. Excludes openings below ply threshold.
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

    def rows_to_openings(rows: list[tuple]) -> list[OpeningWDL]:
        openings = []
        for eco, name, pgn, fen, total, wins, draws, losses in rows:
            if total > 0:
                win_pct = round(wins / total * 100, 1)
                draw_pct = round(draws / total * 100, 1)
                loss_pct = round(losses / total * 100, 1)
            else:
                win_pct = draw_pct = loss_pct = 0.0
            board = chess_lib.Board(fen)
            _, _, full_hash = compute_hashes(board)
            openings.append(
                OpeningWDL(
                    opening_eco=eco,
                    opening_name=name,
                    label=f"{name} ({eco})",
                    pgn=pgn,
                    fen=fen,
                    full_hash=str(full_hash),
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    total=total,
                    win_pct=win_pct,
                    draw_pct=draw_pct,
                    loss_pct=loss_pct,
                )
            )
        return openings

    return MostPlayedOpeningsResponse(
        white=rows_to_openings(white_rows),
        black=rows_to_openings(black_rows),
    )
