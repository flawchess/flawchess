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

from collections import defaultdict
from enum import IntEnum
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    count_filtered_games,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
    query_endgame_performance_rows,
    query_endgame_timeline_rows,
)
from app.schemas.analysis import GameRecord
from app.schemas.endgames import (
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
    - mixed: two or more piece families present (queen+rook, queen+minor, rook+minor)
    - pawnless: no pieces and no pawns (bare kings only)

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
    # Mixed = two or more piece families present (e.g. queen+rook, rook+minor).
    piece_families = sum([has_queen, has_rook, has_minor])
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

    # No pieces, no pawns — bare kings
    return "pawnless"


# Minimum material imbalance (in centipawns) to count as conversion or recovery.
# Filters out minor imbalances like bishop pair (~50cp) that aren't meaningful
# advantages to convert or deficits to recover from.
_MATERIAL_ADVANTAGE_THRESHOLD = 300


def _aggregate_endgame_stats(rows: list[tuple]) -> list[EndgameCategoryStats]:
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

    # Accumulators per endgame class
    wdl: dict[str, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "draws": 0, "losses": 0}
    )
    # Conversion: games where user was up material at endgame entry
    conv: dict[str, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )
    # Recovery: games where user was down material at endgame entry
    recov: dict[str, dict[str, int]] = defaultdict(
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

        label = _ENDGAME_CATEGORY_LABELS.get(endgame_class, endgame_class.replace("_", " ").title())

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
    # endgame_games counts (game, class) combinations, not unique games.
    # A game in two classes (e.g. rook then pawn) contributes 2 to this total.
    # This is intentional per D-02 — each class gets its own W/D/L count.
    endgame_games = sum(c.total for c in categories)

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


def _build_wdl_summary(rows: list[tuple]) -> EndgameWDLSummary:
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


def _compute_rolling_series(rows: list[tuple], window: int) -> list[dict]:
    """Compute a rolling-window win-rate series from chronological game rows.

    Mirrors the pattern in analysis_service.get_time_series.

    Args:
        rows: List of (played_at, result, user_color) tuples ordered by played_at ASC.
        window: Rolling window size. Partial windows (< window games) are included.

    Returns:
        List of dicts with keys: date, win_rate, game_count, window_size.
    """
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    data: list[dict] = []

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)

        # Rolling window: trailing `window` results
        window_slice = results_so_far[-window:]
        win_count = window_slice.count("win")
        window_total = len(window_slice)
        win_rate = win_count / window_total if window_total > 0 else 0.0

        data.append({
            "date": played_at.strftime("%Y-%m-%d"),
            "win_rate": round(win_rate, 4),
            "game_count": window_total,
            "window_size": window,
        })

    return data


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
    2. Fetch endgame and non-endgame game rows for WDL comparison.
    3. Fetch existing endgame stats for aggregate conversion/recovery numerators/denominators.
    4. Build WDL summaries and compute gauge values.
    5. Return EndgamePerformanceResponse.
    """
    cutoff = recency_cutoff(recency)

    # Fetch WDL rows and existing stats concurrently (stats needed for conversion/recovery)
    # Note: get_endgame_stats is awaited separately to access conversion/recovery raw counts
    endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
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

    # Aggregate conversion/recovery: use sum-of-raw (not mean of percentages) per D-07
    # Reuse existing get_endgame_stats which returns categories with raw conversion counts
    stats = await get_endgame_stats(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
    )

    total_conversion_wins = sum(c.conversion.conversion_wins for c in stats.categories)
    total_conversion_games = sum(c.conversion.conversion_games for c in stats.categories)
    total_recovery_saves = sum(c.conversion.recovery_saves for c in stats.categories)
    total_recovery_games = sum(c.conversion.recovery_games for c in stats.categories)

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
        aggregate_recovery_pct=round(aggregate_recovery_pct, 1),
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
    2. Fetch endgame rows, non-endgame rows, and per-type rows concurrently.
    3. Compute rolling-window series for overall (endgame + non-endgame) and per type.
    4. Merge overall series by date (all unique dates from both series).
    5. Return EndgameTimelineResponse.
    """
    cutoff = recency_cutoff(recency)

    endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
    )

    # Compute rolling series for both overall groups
    endgame_series = _compute_rolling_series(endgame_rows, window)
    non_endgame_series = _compute_rolling_series(non_endgame_rows, window)

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
        ]

    return EndgameTimelineResponse(overall=overall, per_type=per_type, window=window)
