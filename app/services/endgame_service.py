"""Endgame service: classification, aggregation, and orchestration for endgame analytics.

Exposes:
- classify_endgame_class: pure function mapping material_signature to category name
- EndgameClassInt: IntEnum encoding for endgame_class SmallInteger column (Per D-06)
- _INT_TO_CLASS / _CLASS_TO_INT: bidirectional mappings for integer <-> string conversion
- _aggregate_endgame_stats: aggregates raw per-game rows into EndgameCategoryStats list
- get_endgame_stats: orchestrator for GET /api/endgames/stats
- get_endgame_games: orchestrator for GET /api/endgames/games
- get_endgame_performance: orchestrator for GET /api/endgames/performance
- get_endgame_timeline: orchestrator for GET /api/endgames/timeline
"""

import asyncio
from collections import defaultdict
from enum import IntEnum
from typing import Any, Literal

from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    count_filtered_games,
    query_conv_recov_timeline_rows,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
    query_endgame_performance_rows,
    query_endgame_timeline_rows,
)
from app.schemas.analysis import GameRecord
from app.schemas.endgames import (
    ConvRecovTimelinePoint,
    ConvRecovTimelineResponse,
    ConversionRecoveryStats,
    EndgameClass,
    EndgameCategoryStats,
    EndgameGamesResponse,
    EndgameLabel,
    EndgameOverallPoint,
    EndgamePerformanceResponse,
    EndgameStatsResponse,
    EndgameTimelinePoint,
    EndgameTimelineResponse,
    EndgameWDLSummary,
)
from app.services.analysis_service import derive_user_result, recency_cutoff

class EndgameClassInt(IntEnum):
    """Integer encoding for endgame_class column (SmallInteger, 2 bytes per row).
    Maps 1:1 to EndgameClass Literal strings. Per D-06."""

    ROOK = 1
    MINOR_PIECE = 2
    PAWN = 3
    QUEEN = 4
    MIXED = 5
    PAWNLESS = 6


_INT_TO_CLASS: dict[int, EndgameClass] = {
    1: "rook",
    2: "minor_piece",
    3: "pawn",
    4: "queen",
    5: "mixed",
    6: "pawnless",
}

_CLASS_TO_INT: dict[EndgameClass, int] = {v: k for k, v in _INT_TO_CLASS.items()}


# Display labels for each endgame category (D-07).
_ENDGAME_CATEGORY_LABELS: dict[EndgameClass, EndgameLabel] = {
    "rook": "Rook",
    "minor_piece": "Minor Piece",
    "pawn": "Pawn",
    "queen": "Queen",
    "mixed": "Mixed",
    "pawnless": "Pawnless",
}


def classify_endgame_class(material_signature: str) -> EndgameClass:
    """Classify a material_signature string into one of six endgame categories.

    Categories (D-07):
    - queen: queen(s), may have pawns, no rook or minor pieces
    - rook: rook(s), may have pawns, no queen or minor pieces
    - minor_piece: bishop/knight, may have pawns, no queen or rook
    - pawn: only pawns, no pieces
    - mixed: two or more piece families present WITH pawns
    - pawnless: no pawns at all — bare kings or multi-family without pawns (e.g. KRN_KR)

    Pawns alongside a single piece family do NOT trigger mixed — a rook+pawns endgame
    is a rook endgame, a bishop+pawns endgame is a minor piece endgame.

    Args:
        material_signature: Canonical string like "KRPP_KRP" (stronger side first).

    Returns:
        One of: "rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"
    """
    # Remove the underscore separator and kings — only look at non-king piece/pawn types
    sig = material_signature.replace("_", "").replace("K", "")

    has_queen = "Q" in sig
    has_rook = "R" in sig
    has_minor = "B" in sig or "N" in sig
    has_pawn = "P" in sig

    # Count piece families (queen, rook, minor) — pawns are NOT a piece family.
    # A rook endgame with pawns (KRP_KRP) is still a rook endgame.
    # Mixed = two or more piece families present WITH pawns (e.g. queen+rook+pawns).
    # Pawnless = no pawns at all (bare kings, or multi-family without pawns like KRB_KR).
    piece_families = sum([has_queen, has_rook, has_minor])

    # Pawnless: any endgame with no pawns and either no pieces (bare kings)
    # or multiple piece families (e.g. KRN_KR, KQR_KQ).
    if not has_pawn and (piece_families != 1):
        return "pawnless"

    if piece_families >= 2:
        return "mixed"

    # Single piece family (may have pawns alongside)
    if has_queen:
        return "queen"
    if has_rook:
        return "rook"
    if has_minor:
        return "minor_piece"
    if has_pawn:
        return "pawn"

    # Should not be reachable, but kept as safety net
    return "pawnless"


# Minimum material imbalance (in centipawns) to count as conversion or recovery.
# Filters out minor imbalances like bishop pair (~50cp) that aren't meaningful
# advantages to convert or deficits to recover from.
_MATERIAL_ADVANTAGE_THRESHOLD = 300


def _aggregate_endgame_stats(rows: list[Row[Any]]) -> list[EndgameCategoryStats]:
    """Aggregate raw per-(game, class) endgame rows into EndgameCategoryStats list.

    Each row is: (game_id, endgame_class_int, result, user_color, user_material_imbalance)
    where endgame_class_int is 1-6 (see EndgameClassInt).
    A game_id may appear multiple times (once per endgame class it spent >= 6 plies in).
    Per D-02: multi-class per game.

    Computes per-category:
    - W/D/L counts and percentages
    - Conversion: win rate when user entered with material advantage (imbalance > 0) — D-08
    - Recovery: draw+win rate when user entered with material disadvantage (imbalance < 0) — D-09

    Returns categories sorted by total game count descending (D-05).
    """
    if not rows:
        return []

    # Accumulators per endgame class (per D-02: TypedDicts for internal data structures)
    wdl: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "draws": 0, "losses": 0}
    )
    # Conversion: games where user was up material at endgame entry
    conv: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )
    # Recovery: games where user was down material at endgame entry
    recov: dict[EndgameClass, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )

    for _game_id, endgame_class_int, result, user_color, user_material_imbalance in rows:
        endgame_class = _INT_TO_CLASS[endgame_class_int]
        outcome = derive_user_result(result, user_color)

        # W/D/L counts
        if outcome == "win":
            wdl[endgame_class]["wins"] += 1
        elif outcome == "draw":
            wdl[endgame_class]["draws"] += 1
        else:
            wdl[endgame_class]["losses"] += 1

        # Conversion: user entered with significant material advantage (>= 3 pawns / 300cp)
        # Threshold filters out minor imbalances (e.g. bishop pair) that don't represent
        # a meaningful advantage to "convert" into a win.
        if user_material_imbalance is not None and user_material_imbalance >= _MATERIAL_ADVANTAGE_THRESHOLD:
            conv[endgame_class]["games"] += 1
            if outcome == "win":
                conv[endgame_class]["wins"] += 1
            elif outcome == "draw":
                conv[endgame_class]["draws"] += 1

        # Recovery: user entered with significant material deficit (<= -3 pawns / -300cp)
        if user_material_imbalance is not None and user_material_imbalance <= -_MATERIAL_ADVANTAGE_THRESHOLD:
            recov[endgame_class]["games"] += 1
            if outcome == "win":
                recov[endgame_class]["wins"] += 1
            elif outcome == "draw":
                recov[endgame_class]["draws"] += 1

    # Build EndgameCategoryStats objects
    categories: list[EndgameCategoryStats] = []
    for endgame_class in wdl:
        c = wdl[endgame_class]
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

        conv_data = conv[endgame_class]
        recov_data = recov[endgame_class]

        conversion_games = conv_data["games"]
        conversion_wins = conv_data["wins"]
        conversion_draws = conv_data["draws"]
        conversion_losses = conversion_games - conversion_wins - conversion_draws
        conversion_pct = (
            round(conversion_wins / conversion_games * 100, 1)
            if conversion_games > 0
            else 0.0
        )

        recovery_games = recov_data["games"]
        recovery_wins = recov_data["wins"]
        recovery_draws = recov_data["draws"]
        recovery_saves = recovery_wins + recovery_draws  # derived, kept for backward compat
        recovery_pct = (
            round(recovery_saves / recovery_games * 100, 1)
            if recovery_games > 0
            else 0.0
        )

        conversion_stats = ConversionRecoveryStats(
            conversion_pct=conversion_pct,
            conversion_games=conversion_games,
            conversion_wins=conversion_wins,
            conversion_draws=conversion_draws,
            conversion_losses=conversion_losses,
            recovery_pct=recovery_pct,
            recovery_games=recovery_games,
            recovery_saves=recovery_saves,
            recovery_wins=recovery_wins,
            recovery_draws=recovery_draws,
        )

        # _ENDGAME_CATEGORY_LABELS is exhaustive for all EndgameClass values — direct lookup.
        # endgame_class is always a valid EndgameClass because _INT_TO_CLASS only contains them.
        label = _ENDGAME_CATEGORY_LABELS[endgame_class]

        categories.append(
            EndgameCategoryStats(
                endgame_class=endgame_class,
                label=label,
                wins=wins,
                draws=draws,
                losses=losses,
                total=total,
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
                conversion=conversion_stats,
            )
        )

    # Sort by total descending (D-05) — not a fixed category order
    categories.sort(key=lambda c: c.total, reverse=True)

    return categories


async def get_endgame_stats(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
) -> EndgameStatsResponse:
    """Orchestrate endgame stats query and return EndgameStatsResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch one row per (game, endgame_class) span meeting the ply threshold.
    3. Aggregate into per-category stats with conversion/recovery.
    4. Return sorted categories (by total desc, D-05).
    """
    cutoff = recency_cutoff(recency)
    rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
    )
    categories = _aggregate_endgame_stats(rows)

    # Total games matching current filters (not just endgame games)
    total_games = await count_filtered_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
    )
    # Count unique games that reached an endgame phase (not game×class combinations,
    # since a game can appear in multiple endgame classes).
    endgame_games = len({row[0] for row in rows})  # row[0] = game_id

    return EndgameStatsResponse(
        categories=categories,
        total_games=total_games,
        endgame_games=endgame_games,
    )


async def get_endgame_games(
    session: AsyncSession,
    user_id: int,
    endgame_class: EndgameClass,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    offset: int,
    limit: int,
) -> EndgameGamesResponse:
    """Orchestrate endgame games query and return paginated EndgameGamesResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch paginated Game objects for the requested endgame class.
    3. Build GameRecord objects matching the existing analysis schema.
    4. Return EndgameGamesResponse with pagination metadata.
    """
    cutoff = recency_cutoff(recency)
    games, matched_count = await _query_endgame_games(
        session,
        user_id=user_id,
        endgame_class=endgame_class,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        offset=offset,
        limit=limit,
    )

    game_records = [
        GameRecord(
            game_id=g.id,
            user_result=derive_user_result(g.result, g.user_color),
            played_at=g.played_at,
            time_control_bucket=g.time_control_bucket,
            platform=g.platform,
            platform_url=g.platform_url,
            white_username=g.white_username,
            black_username=g.black_username,
            white_rating=g.white_rating,
            black_rating=g.black_rating,
            opening_name=g.opening_name,
            opening_eco=g.opening_eco,
            user_color=g.user_color,
            move_count=g.move_count,
            termination=g.termination,
            time_control_str=g.time_control_str,
            result_fen=g.result_fen,
        )
        for g in games
    ]

    return EndgameGamesResponse(
        games=game_records,
        matched_count=matched_count,
        offset=offset,
        limit=limit,
    )


# --- Performance chart service functions (Phase 32) ---

# Weights for endgame_skill score. Conversion (winning when up) weighted more
# than recovery (drawing/winning when down) per D-06.
_ENDGAME_SKILL_CONVERSION_WEIGHT = 0.6
_ENDGAME_SKILL_RECOVERY_WEIGHT = 0.4


def _build_wdl_summary(rows: list[Row[Any]]) -> EndgameWDLSummary:
    """Build EndgameWDLSummary from a list of (played_at, result, user_color) rows."""
    wins = draws = losses = 0
    for _played_at, result, user_color in rows:
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
    return EndgameWDLSummary(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=win_pct,
        draw_pct=draw_pct,
        loss_pct=loss_pct,
    )


def _compute_rolling_series(rows: list[Row[Any]], window: int) -> list[dict]:
    """Compute a rolling-window win-rate series from chronological game rows.

    Mirrors the pattern in analysis_service.get_time_series.

    Args:
        rows: List of (played_at, result, user_color) tuples ordered by played_at ASC.
        window: Rolling window size. Partial windows (< window games) are included.

    Returns:
        List of dicts with keys: date, win_rate, game_count, window_size.
        One entry per date (last game of the day), not per game.
    """
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    data_by_date: dict[str, dict] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)

        # Rolling window: trailing `window` results
        window_slice = results_so_far[-window:]
        win_count = window_slice.count("win")
        window_total = len(window_slice)
        win_rate = win_count / window_total if window_total > 0 else 0.0

        date_key = played_at.strftime("%Y-%m-%d")
        data_by_date[date_key] = {
            "date": date_key,
            "win_rate": round(win_rate, 4),
            "game_count": window_total,
            "window_size": window,
        }

    return list(data_by_date.values())


async def get_endgame_performance(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
) -> EndgamePerformanceResponse:
    """Orchestrate endgame performance query and return EndgamePerformanceResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch WDL comparison rows and entry rows concurrently.
    3. Aggregate entry rows inline for conversion/recovery stats.
    4. Build WDL summaries and compute gauge values.
    5. Return EndgamePerformanceResponse.
    """
    cutoff = recency_cutoff(recency)

    # Fetch entry rows directly (not via get_endgame_stats) to avoid redundant
    # count_filtered_games query and enable concurrent execution with performance rows.
    (endgame_rows, non_endgame_rows), entry_rows = await asyncio.gather(
        query_endgame_performance_rows(
            session,
            user_id=user_id,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            recency_cutoff=cutoff,
        ),
        query_endgame_entry_rows(
            session,
            user_id=user_id,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            recency_cutoff=cutoff,
        ),
    )

    # Build WDL summaries for each group
    endgame_wdl = _build_wdl_summary(endgame_rows)
    non_endgame_wdl = _build_wdl_summary(non_endgame_rows)

    # Gauge: overall win rate across all games
    total_wins = endgame_wdl.wins + non_endgame_wdl.wins
    total_games = endgame_wdl.total + non_endgame_wdl.total
    overall_win_rate = total_wins / total_games * 100 if total_games > 0 else 0.0
    endgame_win_rate = endgame_wdl.win_pct  # already computed as wins/total*100

    # Relative strength: endgame win rate normalized by overall win rate (D-05)
    # Returns 0 when overall_win_rate is 0 to avoid division by zero
    relative_strength = (
        endgame_win_rate / overall_win_rate * 100 if overall_win_rate > 0 else 0.0
    )

    # Aggregate conversion/recovery: use sum-of-raw (not mean of percentages) per D-07.
    # Compute inline from entry_rows — avoids redundant get_endgame_stats + count_filtered_games calls.
    categories = _aggregate_endgame_stats(entry_rows)
    total_conversion_wins = sum(c.conversion.conversion_wins for c in categories)
    total_conversion_games = sum(c.conversion.conversion_games for c in categories)
    total_recovery_saves = sum(c.conversion.recovery_saves for c in categories)
    total_recovery_games = sum(c.conversion.recovery_games for c in categories)

    aggregate_conversion_pct = (
        total_conversion_wins / total_conversion_games * 100
        if total_conversion_games > 0
        else 0.0
    )
    aggregate_recovery_pct = (
        total_recovery_saves / total_recovery_games * 100
        if total_recovery_games > 0
        else 0.0
    )

    # Endgame skill: weighted combination of conversion and recovery rates (D-06)
    endgame_skill = (
        _ENDGAME_SKILL_CONVERSION_WEIGHT * aggregate_conversion_pct
        + _ENDGAME_SKILL_RECOVERY_WEIGHT * aggregate_recovery_pct
    )

    return EndgamePerformanceResponse(
        endgame_wdl=endgame_wdl,
        non_endgame_wdl=non_endgame_wdl,
        overall_win_rate=round(overall_win_rate, 1),
        endgame_win_rate=endgame_win_rate,
        aggregate_conversion_pct=round(aggregate_conversion_pct, 1),
        aggregate_conversion_wins=total_conversion_wins,
        aggregate_conversion_games=total_conversion_games,
        aggregate_recovery_pct=round(aggregate_recovery_pct, 1),
        aggregate_recovery_saves=total_recovery_saves,
        aggregate_recovery_games=total_recovery_games,
        relative_strength=round(relative_strength, 1),
        endgame_skill=round(endgame_skill, 1),
    )


async def get_endgame_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
    window: int = 50,
) -> EndgameTimelineResponse:
    """Orchestrate endgame timeline query and return EndgameTimelineResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch ALL rows (no recency filter) so the rolling window is pre-filled
       with games before the cutoff — avoids cold-start when filtering recent games.
    3. Compute rolling-window series over full history.
    4. Filter output to only emit points on or after the recency cutoff.
    5. Merge overall series by date, build per-type series.
    6. Return EndgameTimelineResponse.
    """
    cutoff = recency_cutoff(recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    # Fetch all games (no recency filter) so rolling windows are pre-filled.
    # Other filters (time_control, platform, etc.) still applied.
    endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,
    )

    # Compute rolling series over full history, then filter to recency window
    endgame_series = _compute_rolling_series(endgame_rows, window)
    non_endgame_series = _compute_rolling_series(non_endgame_rows, window)
    if cutoff_str:
        endgame_series = [pt for pt in endgame_series if pt["date"] >= cutoff_str]
        non_endgame_series = [pt for pt in non_endgame_series if pt["date"] >= cutoff_str]

    # Merge overall series by date. For each date that appears in either series,
    # find the latest point from each series up to that date.
    # We build cumulative dicts (date -> latest point) and collect all unique dates.
    endgame_by_date: dict[str, dict] = {}
    for pt in endgame_series:
        endgame_by_date[pt["date"]] = pt

    non_endgame_by_date: dict[str, dict] = {}
    for pt in non_endgame_series:
        non_endgame_by_date[pt["date"]] = pt

    all_dates = sorted(set(endgame_by_date.keys()) | set(non_endgame_by_date.keys()))

    # For each date, take the most recent known point from each series up to that date
    last_endgame_pt: dict | None = None
    last_non_endgame_pt: dict | None = None
    overall: list[EndgameOverallPoint] = []

    for date in all_dates:
        if date in endgame_by_date:
            last_endgame_pt = endgame_by_date[date]
        if date in non_endgame_by_date:
            last_non_endgame_pt = non_endgame_by_date[date]

        overall.append(
            EndgameOverallPoint(
                date=date,
                endgame_win_rate=last_endgame_pt["win_rate"] if last_endgame_pt else None,
                non_endgame_win_rate=last_non_endgame_pt["win_rate"] if last_non_endgame_pt else None,
                endgame_game_count=last_endgame_pt["game_count"] if last_endgame_pt else 0,
                non_endgame_game_count=last_non_endgame_pt["game_count"] if last_non_endgame_pt else 0,
                window_size=window,
            )
        )

    # Compute per-type rolling series and map class int -> EndgameClass string
    per_type: dict[str, list[EndgameTimelinePoint]] = {}
    for class_int, rows in per_type_rows.items():
        class_name = _INT_TO_CLASS[class_int]
        series = _compute_rolling_series(rows, window)
        per_type[class_name] = [
            EndgameTimelinePoint(
                date=pt["date"],
                win_rate=pt["win_rate"],
                game_count=pt["game_count"],
                window_size=pt["window_size"],
            )
            for pt in series
            if not cutoff_str or pt["date"] >= cutoff_str
        ]

    return EndgameTimelineResponse(overall=overall, per_type=per_type, window=window)


def _compute_conv_recov_rolling_series(
    rows: list[Row[Any]],
    window: int,
    rate_fn,
) -> list[ConvRecovTimelinePoint]:
    """Compute a rolling-window timeline series from chronologically sorted rows.

    Args:
        rows: list of (played_at, result, user_color, ...) tuples, sorted by played_at asc.
        window: rolling window size (number of trailing games).
        rate_fn: function taking a list of outcome strings ("win"/"draw"/"loss")
                 and returning a float rate (0.0-1.0).

    Partial windows (fewer games than `window`) are included from the start.
    Returns one point per date (last game of the day), not per game.
    """
    if not rows:
        return []

    outcomes: list[Literal["win", "draw", "loss"]] = []
    points_by_date: dict[str, ConvRecovTimelinePoint] = {}

    for played_at, result, user_color, *_rest in rows:
        outcome = derive_user_result(result, user_color)
        outcomes.append(outcome)
        date = played_at.strftime("%Y-%m-%d") if hasattr(played_at, "strftime") else str(played_at)

        # Rolling window: trailing `window` results (partial windows included)
        trailing = outcomes[-window:]
        rate = rate_fn(trailing)
        points_by_date[date] = ConvRecovTimelinePoint(
            date=date,
            rate=round(rate, 4),
            game_count=len(trailing),
            window_size=window,
        )

    return list(points_by_date.values())


async def get_conv_recov_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    window: int = 50,
) -> ConvRecovTimelineResponse:
    """Compute conversion and recovery rolling-window timelines.

    Conversion: win rate over trailing `window` games where user entered endgame
    with >= _MATERIAL_ADVANTAGE_THRESHOLD cp advantage.
    Recovery: save rate (win+draw) over trailing `window` games where user entered
    endgame with >= _MATERIAL_ADVANTAGE_THRESHOLD cp disadvantage.

    Fetches all games (no recency filter) so the rolling window is pre-filled
    with games before the cutoff. Output points are filtered to recency window.
    """
    cutoff = recency_cutoff(recency)
    cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

    # Fetch all games (no recency filter) so rolling windows are pre-filled
    rows = await query_conv_recov_timeline_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=None,
    )

    # Split by material advantage direction
    conversion_rows = [r for r in rows if r[3] is not None and r[3] >= _MATERIAL_ADVANTAGE_THRESHOLD]
    recovery_rows = [r for r in rows if r[3] is not None and r[3] <= -_MATERIAL_ADVANTAGE_THRESHOLD]

    # Conversion rate: wins / total in window
    conversion_series = _compute_conv_recov_rolling_series(
        conversion_rows,
        window,
        lambda outcomes: outcomes.count("win") / len(outcomes),
    )

    # Recovery rate: (wins + draws) / total in window
    recovery_series = _compute_conv_recov_rolling_series(
        recovery_rows,
        window,
        lambda outcomes: (outcomes.count("win") + outcomes.count("draw")) / len(outcomes),
    )

    # Filter output to recency window
    if cutoff_str:
        conversion_series = [pt for pt in conversion_series if pt.date >= cutoff_str]
        recovery_series = [pt for pt in recovery_series if pt.date >= cutoff_str]

    return ConvRecovTimelineResponse(
        conversion=conversion_series,
        recovery=recovery_series,
        window=window,
    )
