"""Stats service: aggregation logic for rating history and global stats."""

import datetime
from typing import Any, Literal, TypedDict

from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repository import (
    OpeningPhaseEntryMetrics,
    PositionWDL,
    query_opening_phase_entry_metrics_batch,
    query_position_wdl_batch,
    query_rating_history,
    query_results_by_color,
    query_results_by_time_control,
    query_top_openings_sql_wdl,
)
from app.schemas.stats import (
    BookmarkPhaseEntryItem,
    BookmarkPhaseEntryQuery,
    BookmarkPhaseEntryResponse,
    GlobalStatsResponse,
    MostPlayedOpeningsResponse,
    OpeningWDL,
    RatingDataPoint,
    RatingHistoryResponse,
    WDLByCategory,
)
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.openings_service import recency_cutoff

# Minimum number of games required for an opening to appear in top openings.
MIN_GAMES_FOR_OPENING = 1

# Maximum number of top openings to return per color.
TOP_OPENINGS_LIMIT = 10

# Minimum ply count for a named opening position to be considered: ply 3 keeps
# named gambits/systems like Blackmar-Diemer (1.d4 d5 2.e4) but cuts trivial
# trunks like "Queen's Pawn Game" (1.d4) and "King's Pawn Game" (1.e4) which
# would otherwise dominate position-based ranking — every d4/e4 game would
# count toward them.
MIN_PLY_WHITE = 3
MIN_PLY_BLACK = 3

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
    opponent_gap_min: int | None
    opponent_gap_max: int | None


async def get_rating_history(
    session: AsyncSession,
    user_id: int,
    recency: str | None,
    platform: str | None = None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
            session,
            user_id=user_id,
            platform="chess.com",
            recency_cutoff=cutoff,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
        lichess_rows: list = []
    elif platform == "lichess":
        chesscom_rows = []
        lichess_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="lichess",
            recency_cutoff=cutoff,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
    else:
        chesscom_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="chess.com",
            recency_cutoff=cutoff,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
        lichess_rows = await query_rating_history(
            session,
            user_id=user_id,
            platform="lichess",
            recency_cutoff=cutoff,
            opponent_type=opponent_type,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
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
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Both queries return SQL-aggregated (label, total, wins, draws, losses) rows.
    """
    cutoff = recency_cutoff(recency)

    tc_rows = await query_results_by_time_control(
        session,
        user_id=user_id,
        recency_cutoff=cutoff,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    color_rows = await query_results_by_color(
        session,
        user_id=user_id,
        recency_cutoff=cutoff,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> MostPlayedOpeningsResponse:
    """Return top 10 most played openings per color with position-based game counts.

    Opening selection uses the games table (by opening_eco/name), but the
    displayed game count comes from game_positions (games passing through
    the position). This matches the count shown in "Results by Opening".

    Phase 80: also populates MG-entry eval + clock-diff + EG-entry eval fields
    via query_opening_phase_entry_metrics_batch (D-01, D-04, D-05, D-08, D-09).
    Sequential awaits within the same session (CLAUDE.md: AsyncSession not safe for concurrent use).
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    # Row tuple shape: (eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)
    # full_hash sits at index 5 after the display_name column was added (PRE-01).
    white_position_wdl = await query_position_wdl_batch(
        session,
        user_id,
        [row[5] for row in white_rows if row[5] is not None],
        color="white",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )
    # Phase 80: batch-query phase-entry metrics (MG + EG eval + clock-diff).
    # Sequential await — same session, AsyncSession not safe for concurrent use (CLAUDE.md).
    white_phase_entry_metrics = await query_opening_phase_entry_metrics_batch(
        session,
        user_id,
        [row[5] for row in white_rows if row[5] is not None],
        color="white",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )
    black_position_wdl = await query_position_wdl_batch(
        session,
        user_id,
        [row[5] for row in black_rows if row[5] is not None],
        color="black",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )
    # Sequential await — same session, AsyncSession not safe for concurrent use.
    black_phase_entry_metrics = await query_opening_phase_entry_metrics_batch(
        session,
        user_id,
        [row[5] for row in black_rows if row[5] is not None],
        color="black",
        time_control=filter_params["time_control"],
        platform=filter_params["platform"],
        rated=filter_params["rated"],
        opponent_type=filter_params["opponent_type"],
        recency_cutoff=filter_params["recency_cutoff"],
        opponent_gap_min=filter_params["opponent_gap_min"],
        opponent_gap_max=filter_params["opponent_gap_max"],
    )

    def rows_to_openings(
        rows: list[Row[Any]],
        position_wdl: dict[int, PositionWDL],
        phase_entry_metrics: dict[int, OpeningPhaseEntryMetrics],
    ) -> list[OpeningWDL]:
        openings = []
        for eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses in rows:
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

            # Phase 80: phase-entry eval finalizer (D-01, D-04, D-08).
            pe = phase_entry_metrics.get(full_hash) if full_hash else None

            # MG-entry pillar (D-01, D-04, D-08)
            avg_eval_pawns: float | None = None
            eval_ci_low_pawns: float | None = None
            eval_ci_high_pawns: float | None = None
            eval_n = 0
            eval_p_value: float | None = None
            eval_confidence: Literal["low", "medium", "high"] = "low"

            if pe is not None and pe.eval_n_mg > 0:
                confidence_mg, p_value_mg, mean_cp_mg, ci_half_mg = compute_eval_confidence_bucket(
                    pe.eval_sum_mg, pe.eval_sumsq_mg, pe.eval_n_mg
                )
                avg_eval_pawns = mean_cp_mg / 100.0  # cp -> pawns
                if pe.eval_n_mg >= 2:
                    eval_ci_low_pawns = (mean_cp_mg - ci_half_mg) / 100.0
                    eval_ci_high_pawns = (mean_cp_mg + ci_half_mg) / 100.0
                eval_n = pe.eval_n_mg
                eval_p_value = p_value_mg
                eval_confidence = confidence_mg

            openings.append(
                OpeningWDL(
                    opening_eco=eco,
                    opening_name=name,
                    display_name=display_name,
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
                    # Phase 80 MG-entry eval fields
                    avg_eval_pawns=avg_eval_pawns,
                    eval_ci_low_pawns=eval_ci_low_pawns,
                    eval_ci_high_pawns=eval_ci_high_pawns,
                    eval_n=eval_n,
                    eval_p_value=eval_p_value,
                    eval_confidence=eval_confidence,
                )
            )
        # Sort by position-based game count descending (may differ from
        # the opening-name-based order returned by the SQL query)
        openings.sort(key=lambda o: o.total, reverse=True)
        return openings

    return MostPlayedOpeningsResponse(
        white=rows_to_openings(white_rows, white_position_wdl, white_phase_entry_metrics),
        black=rows_to_openings(black_rows, black_position_wdl, black_phase_entry_metrics),
    )


def _phase80_item_from_metrics(
    target_hash: str,
    pe: OpeningPhaseEntryMetrics | None,
) -> BookmarkPhaseEntryItem:
    """Compute the Phase 80 display fields for a single hash.

    Mirrors the inline finalizer in get_most_played_openings.rows_to_openings
    (D-01, D-04, D-05, D-08). Kept as a separate helper so the bookmark endpoint
    can reuse the same numerical logic without depending on the OpeningWDL row shape.
    """
    item = BookmarkPhaseEntryItem(target_hash=target_hash)
    if pe is None:
        return item

    if pe.eval_n_mg > 0:
        confidence_mg, p_value_mg, mean_cp_mg, ci_half_mg = compute_eval_confidence_bucket(
            pe.eval_sum_mg, pe.eval_sumsq_mg, pe.eval_n_mg
        )
        item.avg_eval_pawns = mean_cp_mg / 100.0
        if pe.eval_n_mg >= 2:
            item.eval_ci_low_pawns = (mean_cp_mg - ci_half_mg) / 100.0
            item.eval_ci_high_pawns = (mean_cp_mg + ci_half_mg) / 100.0
        item.eval_n = pe.eval_n_mg
        item.eval_p_value = p_value_mg
        item.eval_confidence = confidence_mg

    return item


async def get_bookmark_phase_entry_metrics(
    session: AsyncSession,
    user_id: int,
    bookmarks: list[BookmarkPhaseEntryQuery],
    *,
    recency: str | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> BookmarkPhaseEntryResponse:
    """Phase 80 fields for arbitrary bookmark target_hashes.

    Groups bookmarks by (match_side, color) — each group is one batched DB call to
    query_opening_phase_entry_metrics_batch with the matching hash_column. Sequential
    awaits within the same session (CLAUDE.md: AsyncSession not safe for concurrent use).
    """
    if not bookmarks:
        return BookmarkPhaseEntryResponse(items=[])

    cutoff = recency_cutoff(recency)

    # Group by (match_side, color). Bookmarks with the same group share one DB call.
    grouped: dict[tuple[Literal["white", "black", "full"], Literal["white", "black"] | None], list[int]] = {}
    for b in bookmarks:
        key = (b.match_side, b.color)
        grouped.setdefault(key, []).append(int(b.target_hash))

    # Result map: target_hash (signed int) -> OpeningPhaseEntryMetrics
    metrics_by_hash: dict[int, OpeningPhaseEntryMetrics] = {}
    for (match_side, color), hashes in grouped.items():
        # Sequential await — same session.
        group_metrics = await query_opening_phase_entry_metrics_batch(
            session,
            user_id,
            hashes,
            color=color,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            recency_cutoff=cutoff,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
            hash_column=match_side,
        )
        metrics_by_hash.update(group_metrics)

    items = [
        _phase80_item_from_metrics(b.target_hash, metrics_by_hash.get(int(b.target_hash)))
        for b in bookmarks
    ]
    return BookmarkPhaseEntryResponse(items=items)
