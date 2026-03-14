"""Stats service: aggregation logic for rating history and global stats."""

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repository import (
    query_rating_history,
    query_results_by_color,
    query_results_by_time_control,
)
from app.schemas.stats import (
    GlobalStatsResponse,
    RatingDataPoint,
    RatingHistoryResponse,
    WDLByCategory,
)
from app.services.analysis_service import derive_user_result, recency_cutoff

# Ordered time control buckets for consistent output ordering.
_TIME_CONTROL_ORDER = ["bullet", "blitz", "rapid", "classical"]

# Color ordering for consistent output.
_COLOR_ORDER = ["white", "black"]


async def get_rating_history(
    session: AsyncSession,
    user_id: int,
    recency: str | None,
) -> RatingHistoryResponse:
    """Return per-platform per-game rating data points.

    Calls recency_cutoff() to resolve the optional recency filter, queries
    both platforms in sequence, and maps rows to RatingDataPoint lists.
    """
    cutoff = recency_cutoff(recency)

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


def _aggregate_wdl(
    rows: list,
    label_fn,
    label_order: list[str],
) -> list[WDLByCategory]:
    """Aggregate (label_key, result, user_color) rows into WDLByCategory list.

    Args:
        rows: Iterable of (label_key, result, user_color) tuples.
        label_fn: Callable from label_key to display label string.
        label_order: Ordered list of label keys for output ordering.
    """
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "draws": 0, "losses": 0}
    )

    for label_key, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        counts[label_key][outcome + "s"] += 1

    categories = []
    for key in label_order:
        if key not in counts:
            continue
        c = counts[key]
        wins = c["wins"]
        draws = c["draws"]
        losses = c["losses"]
        total = wins + draws + losses
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
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Calls recency_cutoff() to resolve the optional recency filter, queries
    results by time control and by color, aggregates using derive_user_result(),
    and returns a GlobalStatsResponse.
    """
    cutoff = recency_cutoff(recency)

    tc_rows = await query_results_by_time_control(
        session, user_id=user_id, recency_cutoff=cutoff
    )
    color_rows = await query_results_by_color(
        session, user_id=user_id, recency_cutoff=cutoff
    )

    by_time_control = _aggregate_wdl(
        rows=tc_rows,
        label_fn=lambda key: key.title(),
        label_order=_TIME_CONTROL_ORDER,
    )

    # color_rows are (user_color, result) — map to (label_key, result, user_color)
    by_color = _aggregate_wdl(
        rows=[(user_color, result, user_color) for user_color, result in color_rows],
        label_fn=lambda key: key.title(),
        label_order=_COLOR_ORDER,
    )

    return GlobalStatsResponse(
        by_time_control=by_time_control,
        by_color=by_color,
    )
