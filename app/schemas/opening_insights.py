"""Pydantic v2 schemas for Phase 70 opening insights backend (D-26)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD


class OpeningInsightsRequest(BaseModel):
    """Request body for POST /api/insights/openings (D-10, D-13).

    Mirrors the existing /openings/* and /stats/most-played-openings filter
    surface. Does NOT extend or import app.schemas.insights.FilterContext —
    decoupling avoids cross-feature breakage when one filter shape evolves (D-11).

    extra="forbid" gates injection of unknown fields (T-70-05-02 / V4 ASVS):
    any unknown key in the request body returns 422 Unprocessable Entity.
    The router derives the user's identity from current_active_user only.
    """

    model_config = ConfigDict(extra="forbid")

    recency: (
        Literal["week", "month", "3months", "6months", "year", "3years", "5years", "all"] | None
    ) = None
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD
    color: Literal["all", "white", "black"] = "all"


class OpeningInsightFinding(BaseModel):
    """Single opening weakness or strength finding (D-03, D-05, D-25).

    Hash fields (entry_full_hash, resulting_full_hash) are typed as str to
    preserve 64-bit Zobrist hash precision at the JSON boundary — mirrors
    OpeningWDL.full_hash:str (RESEARCH.md Pitfall 1).
    """

    color: Literal["white", "black"]
    classification: Literal["weakness", "strength"]
    severity: Literal["minor", "major"]
    opening_name: str  # "<unnamed line>" sentinel when no openings-table match (D-23)
    opening_eco: str  # "" sentinel when no openings-table match (D-23)
    display_name: str  # may include "vs. " prefix per D-22 / RESEARCH.md Pitfall 4
    entry_fen: str
    entry_san_sequence: list[str]  # SAN tokens from start to entry position (candidate excluded); added Phase 71 (D-13) for FE deep-link replay
    entry_full_hash: str  # str-form for JSON precision (RESEARCH.md Pitfall 1)
    candidate_move_san: str
    resulting_full_hash: str  # str-form, same reason
    n_games: int
    wins: int
    draws: int
    losses: int
    win_rate: float  # used as classifier for strengths (D-04)
    loss_rate: float  # used as classifier for weaknesses (D-04)
    score: float  # (W + D/2)/n; informative only per D-06


class OpeningInsightsResponse(BaseModel):
    """Four-section response structured by color x classification (D-01, D-02).

    All four lists are always present; empty sections are valid empty-state
    (D-20). Phase 71 renders four labeled sections.
    """

    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
