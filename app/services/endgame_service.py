"""Endgame service: classification, aggregation, and orchestration for endgame analytics.

Exposes:
- classify_endgame_class: pure function mapping material_signature to category name
- _aggregate_endgame_stats: aggregates raw per-game rows into EndgameCategoryStats list
- get_endgame_stats: orchestrator for GET /api/endgames/stats
- get_endgame_games: orchestrator for GET /api/endgames/games
"""

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    count_filtered_games,
    query_endgame_entry_rows,
    query_endgame_games as _query_endgame_games,
)
from app.schemas.analysis import GameRecord
from app.schemas.endgames import (
    ConversionRecoveryStats,
    EndgameClass,
    EndgameCategoryStats,
    EndgameGamesResponse,
    EndgameLabel,
    EndgameStatsResponse,
)
from app.services.analysis_service import derive_user_result, recency_cutoff

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


def _aggregate_endgame_stats(rows: list[tuple]) -> list[EndgameCategoryStats]:
    """Aggregate raw per-game endgame entry rows into EndgameCategoryStats list.

    Each row is: (game_id, result, user_color, material_signature, user_material_imbalance)
    where user_material_imbalance > 0 = user was up material at endgame entry.

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
        lambda: {"games": 0, "wins": 0}
    )
    # Recovery: games where user was down material at endgame entry
    recov: dict[str, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "saves": 0}
    )

    for _game_id, result, user_color, material_signature, user_material_imbalance in rows:
        endgame_class = classify_endgame_class(material_signature)
        outcome = derive_user_result(result, user_color)

        # W/D/L counts
        if outcome == "win":
            wdl[endgame_class]["wins"] += 1
        elif outcome == "draw":
            wdl[endgame_class]["draws"] += 1
        else:
            wdl[endgame_class]["losses"] += 1

        # Conversion: user entered with material advantage (positive imbalance)
        if user_material_imbalance is not None and user_material_imbalance > 0:
            conv[endgame_class]["games"] += 1
            if outcome == "win":
                conv[endgame_class]["wins"] += 1

        # Recovery: user entered with material disadvantage (negative imbalance)
        if user_material_imbalance is not None and user_material_imbalance < 0:
            recov[endgame_class]["games"] += 1
            if outcome in ("win", "draw"):
                recov[endgame_class]["saves"] += 1

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
        conversion_pct = (
            round(conversion_wins / conversion_games * 100, 1)
            if conversion_games > 0
            else 0.0
        )

        recovery_games = recov_data["games"]
        recovery_saves = recov_data["saves"]
        recovery_pct = (
            round(recovery_saves / recovery_games * 100, 1)
            if recovery_games > 0
            else 0.0
        )

        conversion_stats = ConversionRecoveryStats(
            conversion_pct=conversion_pct,
            conversion_games=conversion_games,
            conversion_wins=conversion_wins,
            recovery_pct=recovery_pct,
            recovery_games=recovery_games,
            recovery_saves=recovery_saves,
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
    2. Fetch one row per game at endgame transition point.
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
    # Endgame games = sum of all category totals (each row is one game)
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
