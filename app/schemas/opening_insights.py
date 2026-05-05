"""Pydantic v2 schemas for Phase 70 opening insights backend (D-26)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
)


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
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None
    color: Literal["all", "white", "black"] = "all"


class OpeningInsightFinding(BaseModel):
    """Single opening weakness or strength finding (D-03, D-05, D-25; Phase 75 D-09).

    Hash fields (entry_full_hash, resulting_full_hash) are typed as str to
    preserve 64-bit Zobrist hash precision at the JSON boundary — mirrors
    OpeningWDL.full_hash:str (RESEARCH.md Pitfall 1).

    Phase 75 (v1.14) replaced loss_rate/win_rate with score-based
    classification annotated by Wald confidence.
    """

    color: Literal["white", "black"]
    classification: Literal["weakness", "strength"]
    severity: Literal["minor", "major"]
    opening_name: str  # "<unnamed line>" sentinel when no openings-table match (D-23)
    opening_eco: str  # "" sentinel when no openings-table match (D-23)
    display_name: str  # may include "vs. " prefix per D-22 / RESEARCH.md Pitfall 4
    entry_fen: str
    entry_san_sequence: list[
        str
    ]  # SAN tokens from start to entry position (candidate excluded); added Phase 71 (D-13) for FE deep-link replay
    entry_full_hash: str  # str-form for JSON precision (RESEARCH.md Pitfall 1)
    candidate_move_san: str
    resulting_full_hash: str  # str-form, same reason
    # Range constraints enforce API-boundary invariants (CLAUDE.md: leverage
    # Pydantic for validation). n_games is gated by the SQL HAVING clause at
    # MIN_GAMES_PER_CANDIDATE; w/d/l are non-negative game counts; score is
    # in [0, 1] by construction (score = (w + d/2)/n); p_value is the
    # two-sided Wald p, bounded in [0, 1].
    n_games: int = Field(ge=OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    score: float = Field(
        ge=0.0, le=1.0
    )  # (W + D/2)/n; canonical classification metric (Phase 75 D-09)
    confidence: Literal[
        "low", "medium", "high"
    ]  # Two-sided Wald p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium) (shared via score_confidence.py)
    p_value: float = Field(
        ge=0.0, le=1.0
    )  # Two-sided Wald z-test p-value on H0: score = 0.50
    # Wilson 95% score interval bounds, clamped to [0, 1]. Same formula already
    # used internally for ranking (_wilson_bounds); now exposed so the FE can
    # render the CI whisker on the bullet chart.
    ci_low: float = Field(ge=0.0, le=1.0)
    ci_high: float = Field(ge=0.0, le=1.0)


class OpeningInsightsResponse(BaseModel):
    """Four-section response structured by color x classification (D-01, D-02).

    All four lists are always present; empty sections are valid empty-state
    (D-20). Phase 71 renders four labeled sections.
    """

    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
