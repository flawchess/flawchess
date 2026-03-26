"""Pydantic v2 schemas for the endgame analytics API.

Provides response models for:
- GET /api/endgames/stats: per-category W/D/L with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.analysis import GameRecord

EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]
EndgameLabel = Literal["Rook", "Minor Piece", "Pawn", "Queen", "Mixed", "Pawnless"]


class ConversionRecoveryStats(BaseModel):
    """Inline conversion/recovery stats for one endgame category (D-06, D-08, D-09).

    Conversion: win rate when user entered this endgame type with material advantage.
    Recovery: draw+win rate when user entered this endgame type with material disadvantage.
    Both are computed per endgame type (D-11), not per game phase.
    """

    conversion_pct: float   # win rate when up material entering endgame (0-100), per D-08
    conversion_games: int   # games where user entered this endgame type with material advantage
    conversion_wins: int    # wins among those games
    conversion_draws: int   # draws among those games
    conversion_losses: int  # losses among those games (= conversion_games - wins - draws)

    recovery_pct: float     # draw+win rate when down material entering endgame (0-100), per D-09
    recovery_games: int     # games where user entered this endgame type with material disadvantage
    recovery_saves: int     # draws+wins among those games (kept for backward compat)
    recovery_wins: int      # wins among those games
    recovery_draws: int     # draws among those games


class EndgameCategoryStats(BaseModel):
    """W/D/L + inline conversion/recovery for one endgame category (D-06, D-10).

    endgame_class maps to one of the six categories defined in D-07:
    rook | minor_piece | pawn | queen | mixed | pawnless
    """

    endgame_class: EndgameClass
    label: EndgameLabel
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    conversion: ConversionRecoveryStats  # Inline, not a separate section (D-10)


class EndgameStatsResponse(BaseModel):
    """Response for GET /api/endgames/stats.

    Categories sorted by total game count descending (D-05).
    No color filter applied — stats cover both colors (D-02).
    """

    categories: list[EndgameCategoryStats]
    total_games: int       # Total games matching current filters (not just endgame games)
    endgame_games: int     # Games that reached an endgame phase


class EndgameGamesResponse(BaseModel):
    """Response for GET /api/endgames/games (D-12, D-14).

    Reuses GameRecord from analysis schema for consistency with existing game displays.
    """

    games: list[GameRecord]
    matched_count: int
    offset: int
    limit: int
