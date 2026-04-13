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

import statistics
from collections import defaultdict
from collections.abc import Sequence
from enum import IntEnum
from typing import Any, Literal, cast

from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD
from app.repositories.endgame_repository import (
    count_endgame_games,
    count_filtered_games,
    query_clock_stats_rows,
    query_conv_recov_timeline_rows,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
    query_endgame_performance_rows,
    query_endgame_timeline_rows,
)
from app.schemas.openings import GameRecord
from app.schemas.endgames import (
    ClockPressureResponse,
    ClockStatsRow,
    ConvRecovTimelinePoint,
    ConvRecovTimelineResponse,
    ConversionRecoveryStats,
    EndgameClass,
    EndgameCategoryStats,
    EndgameGamesResponse,
    EndgameLabel,
    EndgameOverallPoint,
    EndgameOverviewResponse,
    EndgamePerformanceResponse,
    EndgameStatsResponse,
    EndgameTimelinePoint,
    EndgameTimelineResponse,
    EndgameWDLSummary,
    MaterialBucket,
    MaterialRow,
    ScoreGapMaterialResponse,
    TimePressureBucketPoint,
    TimePressureChartResponse,
    TimePressureChartRow,
)
from app.services.openings_service import MIN_GAMES_FOR_TIMELINE, derive_user_result, recency_cutoff

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
# Lowered from 300cp to 100cp alongside the persistence filter — the persistence
# requirement (imbalance must also hold 4 plies later) eliminates transient noise
# from piece trades, allowing a lower threshold for a larger meaningful dataset.
_MATERIAL_ADVANTAGE_THRESHOLD = 100


def _aggregate_endgame_stats(rows: Sequence[Row[Any] | tuple[Any, ...]]) -> list[EndgameCategoryStats]:
    """Aggregate raw per-(game, class) endgame rows into EndgameCategoryStats list.

    Each row is: (game_id, endgame_class_int, result, user_color, user_material_imbalance, user_material_imbalance_after)
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

    for _game_id, endgame_class_int, result, user_color, user_material_imbalance, user_material_imbalance_after in rows:
        endgame_class = _INT_TO_CLASS[endgame_class_int]
        outcome = derive_user_result(result, user_color)

        # W/D/L counts
        if outcome == "win":
            wdl[endgame_class]["wins"] += 1
        elif outcome == "draw":
            wdl[endgame_class]["draws"] += 1
        else:
            wdl[endgame_class]["losses"] += 1

        # Conversion: user entered with significant material advantage (>= 100cp)
        # that persisted 4 plies into the endgame — filters transient trade imbalances.
        if (
            user_material_imbalance is not None
            and user_material_imbalance >= _MATERIAL_ADVANTAGE_THRESHOLD
            and user_material_imbalance_after is not None
            and user_material_imbalance_after >= _MATERIAL_ADVANTAGE_THRESHOLD
        ):
            conv[endgame_class]["games"] += 1
            if outcome == "win":
                conv[endgame_class]["wins"] += 1
            elif outcome == "draw":
                conv[endgame_class]["draws"] += 1

        # Recovery: user entered with significant material deficit (<= -100cp)
        # that persisted 4 plies into the endgame.
        if (
            user_material_imbalance is not None
            and user_material_imbalance <= -_MATERIAL_ADVANTAGE_THRESHOLD
            and user_material_imbalance_after is not None
            and user_material_imbalance_after <= -_MATERIAL_ADVANTAGE_THRESHOLD
        ):
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
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    # Count games that reached an endgame phase (any endgame_class IS NOT NULL position).
    # No ply threshold — simpler definition than per-type classification.
    endgame_games = await count_endgame_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )

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
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
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

# Weights for endgame_skill score. Conversion (winning when up) weighted 70/30
# over recovery (drawing/winning when down) per D-06 (updated from 60/40).
_ENDGAME_SKILL_CONVERSION_WEIGHT = 0.7
_ENDGAME_SKILL_RECOVERY_WEIGHT = 0.3


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


def _wdl_to_score(wdl: EndgameWDLSummary) -> float:
    """Convert WDL summary to score in range 0.0-1.0.

    Score formula: (Win% + Draw%/2) / 100.
    Returns 0.0 for empty WDL (total == 0).
    """
    if wdl.total == 0:
        return 0.0
    return (wdl.win_pct + wdl.draw_pct / 2) / 100


# Display labels for material buckets (section 2 of endgame-analysis-v2.md).
# Unicode: \u2265 = >=, \u2264 = <=, \u2212 = minus sign
_MATERIAL_BUCKET_LABELS: dict[MaterialBucket, str] = {
    "conversion": "Conversion (\u2265 +1)",
    "even": "Even",
    "recovery": "Recovery (\u2264 \u22121)",
}


def _compute_score_gap_material(
    endgame_wdl: EndgameWDLSummary,
    non_endgame_wdl: EndgameWDLSummary,
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> ScoreGapMaterialResponse:
    """Compute endgame score gap and material-stratified WDL table.

    Args:
        endgame_wdl: WDL summary for games that reached an endgame.
        non_endgame_wdl: WDL summary for games that never reached an endgame.
        entry_rows: Per-(game, class) rows from query_endgame_entry_rows.
            Each row: (game_id, endgame_class_int, result, user_color,
                       user_material_imbalance, user_material_imbalance_after).

    Returns:
        ScoreGapMaterialResponse with score gap and 3-row material breakdown.
    """
    endgame_score = _wdl_to_score(endgame_wdl)
    non_endgame_score = _wdl_to_score(non_endgame_wdl)
    score_difference = endgame_score - non_endgame_score

    # overall_score: weighted combination from both WDL summaries combined.
    combined_wins = endgame_wdl.wins + non_endgame_wdl.wins
    combined_draws = endgame_wdl.draws + non_endgame_wdl.draws
    combined_total = endgame_wdl.total + non_endgame_wdl.total
    if combined_total > 0:
        overall_win_pct = combined_wins / combined_total * 100
        overall_draw_pct = combined_draws / combined_total * 100
        overall_score = (overall_win_pct + overall_draw_pct / 2) / 100
    else:
        overall_score = 0.0

    bucket_wins: dict[MaterialBucket, int] = {"conversion": 0, "even": 0, "recovery": 0}
    bucket_draws: dict[MaterialBucket, int] = {"conversion": 0, "even": 0, "recovery": 0}
    bucket_losses: dict[MaterialBucket, int] = {"conversion": 0, "even": 0, "recovery": 0}
    bucket_games: dict[MaterialBucket, int] = {"conversion": 0, "even": 0, "recovery": 0}

    # Phase 59: group rows by game_id, then pick one span per game.
    # Priority within a game's rows:
    #   1) any row satisfying CONVERSION persistence (imbalance >= +threshold AND imbalance_after >= +threshold)
    #   2) else any row satisfying RECOVERY persistence (imbalance <= -threshold AND imbalance_after <= -threshold)
    #   3) else fall back to the row with the LOWEST endgame_class_int for determinism; bucket as "even".
    #
    # Conversion-over-recovery tiebreak (priority 1 > priority 2): when a game has BOTH a
    # conversion-qualifying span AND a recovery-qualifying span, we bucket as "conversion".
    # Rationale: reaching a winning position is the earlier causal event in the game — the
    # user first had an advantage, then (possibly after trades) a disadvantage. Inverting this
    # would systematically double-penalize conversion failures. Do NOT change this without
    # updating the invariant test (see tests/test_endgame_service.py::TestScoreGapMaterialInvariant).
    #
    # NULL imbalance rows (user_material_imbalance is None OR user_material_imbalance_after
    # is None) cannot satisfy priorities 1 or 2, so they fall through to priority 3 and the
    # game is bucketed as "even". This replaces the Phase 53 `continue` that silently
    # dropped such games and broke sum(material_rows.games) == endgame_wdl.total.

    rows_by_game: dict[int, list[Sequence[Any]]] = defaultdict(list)
    for row in entry_rows:
        rows_by_game[row[0]].append(row)

    for game_id, game_rows in rows_by_game.items():
        chosen_row: Sequence[Any] | None = None
        chosen_bucket: MaterialBucket = "even"

        # Pass 1: look for a CONVERSION-qualifying span.
        for r in game_rows:
            imb = r[4]
            imb_after = r[5]
            if (
                imb is not None
                and imb_after is not None
                and imb >= _MATERIAL_ADVANTAGE_THRESHOLD
                and imb_after >= _MATERIAL_ADVANTAGE_THRESHOLD
            ):
                chosen_row = r
                chosen_bucket = "conversion"
                break

        # Pass 2: look for a RECOVERY-qualifying span (only if no conversion match).
        if chosen_row is None:
            for r in game_rows:
                imb = r[4]
                imb_after = r[5]
                if (
                    imb is not None
                    and imb_after is not None
                    and imb <= -_MATERIAL_ADVANTAGE_THRESHOLD
                    and imb_after <= -_MATERIAL_ADVANTAGE_THRESHOLD
                ):
                    chosen_row = r
                    chosen_bucket = "recovery"
                    break

        # Pass 3: fallback to "even". Pick the row with the lowest endgame_class_int for
        # deterministic output regardless of SQL row order.
        if chosen_row is None:
            chosen_row = min(game_rows, key=lambda r: r[1])
            chosen_bucket = "even"

        result_str: str = chosen_row[2]
        user_color: str = chosen_row[3]
        outcome = derive_user_result(result_str, user_color)

        bucket_games[chosen_bucket] += 1
        if outcome == "win":
            bucket_wins[chosen_bucket] += 1
        elif outcome == "draw":
            bucket_draws[chosen_bucket] += 1
        else:
            bucket_losses[chosen_bucket] += 1

    # Build MaterialRow for each bucket in fixed order: conversion, even, recovery.
    material_rows: list[MaterialRow] = []
    for bucket_key in ("conversion", "even", "recovery"):
        b: MaterialBucket = bucket_key  # type: ignore[assignment]
        games = bucket_games[b]
        if games > 0:
            win_pct = round(bucket_wins[b] / games * 100, 1)
            draw_pct = round(bucket_draws[b] / games * 100, 1)
            loss_pct = round(bucket_losses[b] / games * 100, 1)
            row_score = (win_pct + draw_pct / 2) / 100
        else:
            win_pct = draw_pct = loss_pct = 0.0
            row_score = 0.0

        material_rows.append(
            MaterialRow(
                bucket=b,
                label=_MATERIAL_BUCKET_LABELS[b],
                games=games,
                win_pct=win_pct,
                draw_pct=draw_pct,
                loss_pct=loss_pct,
                score=row_score,
            )
        )

    return ScoreGapMaterialResponse(
        endgame_score=endgame_score,
        non_endgame_score=non_endgame_score,
        score_difference=score_difference,
        overall_score=overall_score,
        material_rows=material_rows,
    )


# Minimum endgame games per time control to include a row in the clock stats table.
# Rows below this threshold are too sparse for meaningful averages.
MIN_GAMES_FOR_CLOCK_STATS = 10

# Number of time-remaining buckets for the pressure-performance chart (Phase 55).
NUM_BUCKETS = 10
BUCKET_WIDTH_PCT = 10  # each bucket spans 10 percentage points

# Display labels for time control buckets.
_TIME_CONTROL_LABELS: dict[str, str] = {
    "bullet": "Bullet",
    "blitz": "Blitz",
    "rapid": "Rapid",
    "classical": "Classical",
}

# Fixed display order for time control rows (fastest to slowest).
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]


def _extract_entry_clocks(
    plies: list[int],
    clocks: list[float | None],
    user_color: str,
) -> tuple[float | None, float | None]:
    """Return (user_entry_clock, opp_entry_clock) at endgame entry.

    user_color determines ply parity: white=even plies (0,2,4,...), black=odd plies (1,3,...).
    Scans the ply/clock arrays and returns the first non-None clock for each parity.
    Returns (None, None) if the expected entry plies have no clock data.
    """
    user_parity = 0 if user_color == "white" else 1
    user_clock: float | None = None
    opp_clock: float | None = None
    for ply, clock in zip(plies, clocks):
        if ply % 2 == user_parity and user_clock is None:
            user_clock = clock
        elif ply % 2 != user_parity and opp_clock is None:
            opp_clock = clock
        if user_clock is not None and opp_clock is not None:
            break
    return user_clock, opp_clock


def _compute_clock_pressure(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> ClockPressureResponse:
    """Compute time pressure stats at endgame entry, grouped by time control.

    Each row from query_clock_stats_rows has the shape:
    (game_id, time_control_bucket, time_control_seconds, termination, result,
     user_color, ply_array, clock_array)

    Returns ClockPressureResponse with:
    - rows: one ClockStatsRow per time control with >= MIN_GAMES_FOR_CLOCK_STATS games
    - total_clock_games: total games with both clocks present (all time controls, pre-filter)
    - total_endgame_games: total distinct endgame games (all time controls, pre-filter)
    """
    # Accumulators per time control bucket.
    # Using plain dicts to avoid ty complaints with mutable defaults in TypedDict.
    tc_game_ids: dict[str, set[int]] = defaultdict(set)
    tc_timeout_win_ids: dict[str, set[int]] = defaultdict(set)
    tc_timeout_loss_ids: dict[str, set[int]] = defaultdict(set)
    tc_user_clocks: dict[str, list[float]] = defaultdict(list)
    tc_opp_clocks: dict[str, list[float]] = defaultdict(list)
    tc_clock_diffs: dict[str, list[float]] = defaultdict(list)
    tc_user_pcts: dict[str, list[float]] = defaultdict(list)
    tc_opp_pcts: dict[str, list[float]] = defaultdict(list)
    # time_control_seconds per bucket (consistent within bucket; store first seen)
    tc_seconds: dict[str, int | None] = {}

    for row in clock_rows:
        game_id: int = row[0]
        time_control_bucket: str | None = row[1]
        time_control_seconds: int | None = row[2]
        termination: str | None = row[3]
        result: str = row[4]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]

        # Skip rows without a time control bucket
        if time_control_bucket is None:
            continue

        tc = time_control_bucket
        tc_game_ids[tc].add(game_id)

        # Store time_control_seconds for pct computation (first seen per bucket)
        if tc not in tc_seconds:
            tc_seconds[tc] = time_control_seconds

        # Extract entry clocks using ply parity
        user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)

        # Only accumulate clock stats when BOTH clocks are available
        if user_clock is not None and opp_clock is not None:
            tc_user_clocks[tc].append(user_clock)
            tc_opp_clocks[tc].append(opp_clock)
            tc_clock_diffs[tc].append(user_clock - opp_clock)

            tc_secs = tc_seconds.get(tc)
            if tc_secs is not None and tc_secs > 0:
                tc_user_pcts[tc].append(user_clock / tc_secs * 100)
                tc_opp_pcts[tc].append(opp_clock / tc_secs * 100)

        # Track timeouts — deduplicated by game_id per bucket
        if termination == "timeout":
            outcome = derive_user_result(result, user_color)
            if outcome == "win":
                tc_timeout_win_ids[tc].add(game_id)
            elif outcome == "loss":
                tc_timeout_loss_ids[tc].add(game_id)

    # Build response rows in fixed order; collect pre-filter totals
    grand_endgame_game_ids: set[int] = set()
    grand_clock_game_count = 0
    for game_ids in tc_game_ids.values():
        grand_endgame_game_ids.update(game_ids)
    for user_clocks in tc_user_clocks.values():
        grand_clock_game_count += len(user_clocks)

    rows: list[ClockStatsRow] = []
    for tc in _TIME_CONTROL_ORDER:
        game_ids = tc_game_ids.get(tc, set())
        total_endgame_games = len(game_ids)

        # Filter rows below the minimum games threshold
        if total_endgame_games < MIN_GAMES_FOR_CLOCK_STATS:
            continue

        user_clocks = tc_user_clocks.get(tc, [])
        opp_clocks = tc_opp_clocks.get(tc, [])
        clock_diffs = tc_clock_diffs.get(tc, [])
        user_pcts = tc_user_pcts.get(tc, [])
        opp_pcts = tc_opp_pcts.get(tc, [])

        clock_games = len(user_clocks)
        user_avg_seconds = statistics.mean(user_clocks) if user_clocks else None
        opp_avg_seconds = statistics.mean(opp_clocks) if opp_clocks else None
        avg_clock_diff_seconds = statistics.mean(clock_diffs) if clock_diffs else None
        user_avg_pct = statistics.mean(user_pcts) if user_pcts else None
        opp_avg_pct = statistics.mean(opp_pcts) if opp_pcts else None

        timeout_wins = len(tc_timeout_win_ids.get(tc, set()))
        timeout_losses = len(tc_timeout_loss_ids.get(tc, set()))
        net_timeout_rate = (timeout_wins - timeout_losses) / total_endgame_games * 100

        label = _TIME_CONTROL_LABELS.get(tc, tc.capitalize())

        rows.append(ClockStatsRow(
            time_control=cast(Literal["bullet", "blitz", "rapid", "classical"], tc),
            label=label,
            total_endgame_games=total_endgame_games,
            clock_games=clock_games,
            user_avg_pct=user_avg_pct,
            user_avg_seconds=user_avg_seconds,
            opp_avg_pct=opp_avg_pct,
            opp_avg_seconds=opp_avg_seconds,
            avg_clock_diff_seconds=avg_clock_diff_seconds,
            net_timeout_rate=net_timeout_rate,
        ))

    return ClockPressureResponse(
        rows=rows,
        total_clock_games=grand_clock_game_count,
        total_endgame_games=len(grand_endgame_game_ids),
    )


def _build_bucket_series(
    buckets: list[list[float]],
) -> list[TimePressureBucketPoint]:
    """Build 10-point series from accumulated [score_sum, game_count] pairs.

    Each element of buckets is [score_sum, game_count] for one bucket index.
    Returns a list of TimePressureBucketPoint with score=None when game_count==0.
    """
    points: list[TimePressureBucketPoint] = []
    for i, bucket in enumerate(buckets):
        score_sum = bucket[0]
        count = bucket[1]
        lo = i * BUCKET_WIDTH_PCT
        hi = (i + 1) * BUCKET_WIDTH_PCT
        label = f"{lo}-{hi}%"
        score = (score_sum / count) if count > 0 else None
        points.append(TimePressureBucketPoint(
            bucket_index=i,
            bucket_label=label,
            score=score,
            game_count=int(count),
        ))
    return points


def _compute_time_pressure_chart(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> TimePressureChartResponse:
    """Compute time-pressure performance chart data from clock_rows.

    Reuses the same clock_rows already fetched by query_clock_stats_rows in
    get_endgame_overview -- no additional DB query needed.

    For each game with both clocks and valid time_control_seconds:
    - Bucket user's time% -> accumulate user_score into user_series
    - Bucket opp's time% -> accumulate (1 - user_score) into opp_series

    Returns rows for time controls with >= MIN_GAMES_FOR_CLOCK_STATS games.
    Each row contains exactly NUM_BUCKETS (10) points per series.
    """
    # Accumulators: [score_sum, game_count] per bucket per time control.
    tc_user_buckets: dict[str, list[list[float]]] = defaultdict(
        lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
    )
    tc_opp_buckets: dict[str, list[list[float]]] = defaultdict(
        lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
    )
    # Count games with valid time_control_bucket (regardless of clock data).
    tc_game_count: dict[str, int] = defaultdict(int)

    for row in clock_rows:
        game_id: int = row[0]
        time_control_bucket: str | None = row[1]
        time_control_seconds: int | None = row[2]
        termination: str | None = row[3]
        result: str = row[4]
        user_color: str = row[5]
        ply_array: list[int] = row[6]
        clock_array: list[float | None] = row[7]

        # Skip rows without a time control bucket
        if time_control_bucket is None:
            continue

        tc = time_control_bucket
        tc_game_count[tc] += 1

        # Extract entry clocks via ply parity — same as _compute_clock_pressure
        user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)

        # Skip if either clock is missing — can't bucket without both
        if user_clock is None or opp_clock is None:
            continue

        # Skip if time_control_seconds is absent or zero — can't compute percentage
        if time_control_seconds is None or time_control_seconds <= 0:
            continue

        user_pct = user_clock / time_control_seconds * 100
        opp_pct = opp_clock / time_control_seconds * 100

        # Clamp to [0, NUM_BUCKETS-1] — 100% maps to bucket 9, not 10
        user_bucket = min(int(user_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)
        opp_bucket = min(int(opp_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)

        user_score = {"win": 1.0, "draw": 0.5, "loss": 0.0}[derive_user_result(result, user_color)]

        # Accumulate: initialise defaultdict entry if needed, then update
        tc_user_buckets[tc][user_bucket][0] += user_score
        tc_user_buckets[tc][user_bucket][1] += 1
        tc_opp_buckets[tc][opp_bucket][0] += (1.0 - user_score)
        tc_opp_buckets[tc][opp_bucket][1] += 1

    # Build rows in fixed time control order, filtering below minimum threshold
    rows: list[TimePressureChartRow] = []
    for tc in _TIME_CONTROL_ORDER:
        total_games = tc_game_count.get(tc, 0)
        if total_games < MIN_GAMES_FOR_CLOCK_STATS:
            continue

        label = _TIME_CONTROL_LABELS.get(tc, tc.capitalize())
        user_series = _build_bucket_series(tc_user_buckets[tc])
        opp_series = _build_bucket_series(tc_opp_buckets[tc])

        rows.append(TimePressureChartRow(
            time_control=cast(Literal["bullet", "blitz", "rapid", "classical"], tc),
            label=label,
            total_endgame_games=total_games,
            user_series=user_series,
            opp_series=opp_series,
        ))

    return TimePressureChartResponse(rows=rows)


def _compute_rolling_series(rows: list[Row[Any]], window: int) -> list[dict]:
    """Compute a rolling-window win-rate series from chronological game rows.

    Mirrors the pattern in openings_service.get_time_series.

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

    # Drop early points with too few games in the rolling window
    return [pt for pt in data_by_date.values() if pt["game_count"] >= MIN_GAMES_FOR_TIMELINE]


def _get_endgame_performance_from_rows(
    endgame_rows: list[Row[Any]],
    non_endgame_rows: list[Row[Any]],
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> EndgamePerformanceResponse:
    """Compute EndgamePerformanceResponse from pre-fetched rows.

    Extracted from get_endgame_performance so get_endgame_overview can share
    the rows it already fetched — avoids a redundant query_endgame_entry_rows call.

    Args:
        endgame_rows: (played_at, result, user_color) for games that reached endgame.
        non_endgame_rows: (played_at, result, user_color) for games that did not.
        entry_rows: (game_id, endgame_class_int, result, user_color,
                     user_material_imbalance, user_material_imbalance_after).
    """
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


async def get_endgame_performance(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> EndgamePerformanceResponse:
    """Orchestrate endgame performance query and return EndgamePerformanceResponse.

    Steps:
    1. Convert recency to cutoff datetime.
    2. Fetch WDL comparison rows and entry rows sequentially.
    3. Delegate aggregation to _get_endgame_performance_from_rows.
    4. Return EndgamePerformanceResponse.
    """
    cutoff = recency_cutoff(recency)

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and shares a single DB connection anyway.
    endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    entry_rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )

    return _get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, entry_rows)


async def get_endgame_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    recency: str | None,
    rated: bool | None,
    opponent_type: str,
    window: int = 50,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
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

    # Drop early points with too few games in the rolling window
    return [pt for pt in points_by_date.values() if pt.game_count >= MIN_GAMES_FOR_TIMELINE]


async def get_conv_recov_timeline(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    window: int = 50,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )

    # Split by material advantage direction — require persistence at entry AND 4 plies later.
    # r[3] = user_material_imbalance (at entry), r[4] = user_material_imbalance_after (4 plies later)
    conversion_rows = [
        r for r in rows
        if r[3] is not None and r[3] >= _MATERIAL_ADVANTAGE_THRESHOLD
        and r[4] is not None and r[4] >= _MATERIAL_ADVANTAGE_THRESHOLD
    ]
    recovery_rows = [
        r for r in rows
        if r[3] is not None and r[3] <= -_MATERIAL_ADVANTAGE_THRESHOLD
        and r[4] is not None and r[4] <= -_MATERIAL_ADVANTAGE_THRESHOLD
    ]

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


async def get_endgame_overview(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    window: int = 50,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> EndgameOverviewResponse:
    """Compose all five endgame dashboard payloads into a single response.

    Fetches entry_rows and performance rows once, then threads them to both
    the stats/performance builders and _compute_score_gap_material — eliminating
    redundant DB queries that the previous implementation issued separately in
    get_endgame_stats and get_endgame_performance (Phase 53).

    All queries run sequentially on one AsyncSession — no asyncio.gather.
    See endgame_repository.py for AsyncSession concurrency notes.
    """
    cutoff = recency_cutoff(recency)

    # Fetch entry_rows once — shared by stats, performance, and score_gap_material.
    # Previously fetched redundantly by both get_endgame_stats and get_endgame_performance.
    entry_rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )

    # Stats: aggregate per-category W/D/L + conversion/recovery from entry_rows
    categories = _aggregate_endgame_stats(entry_rows)
    total_games = await count_filtered_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    # Count games that reached an endgame phase (any endgame_class IS NOT NULL position).
    # No ply threshold — matches the "reached an endgame phase" wording in the UI.
    endgame_games = await count_endgame_games(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    stats = EndgameStatsResponse(
        categories=categories,
        total_games=total_games,
        endgame_games=endgame_games,
    )

    # Performance: fetch WDL comparison rows, then use shared entry_rows
    endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    performance = _get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, entry_rows)

    # Score gap & material breakdown — zero extra queries, reuses performance WDLs + entry_rows
    score_gap_material = _compute_score_gap_material(
        performance.endgame_wdl, performance.non_endgame_wdl, entry_rows
    )

    timeline = await get_endgame_timeline(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        recency=recency,
        rated=rated,
        opponent_type=opponent_type,
        window=window,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    conv_recov_timeline = await get_conv_recov_timeline(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
        window=window,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )

    # Clock pressure: fetch per-span arrays, then compute stats in service layer
    clock_rows = await query_clock_stats_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=cutoff,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    clock_pressure = _compute_clock_pressure(clock_rows)
    time_pressure_chart = _compute_time_pressure_chart(clock_rows)

    return EndgameOverviewResponse(
        stats=stats,
        performance=performance,
        timeline=timeline,
        conv_recov_timeline=conv_recov_timeline,
        score_gap_material=score_gap_material,
        clock_pressure=clock_pressure,
        time_pressure_chart=time_pressure_chart,
    )
