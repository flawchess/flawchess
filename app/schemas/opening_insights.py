"""Pydantic v2 schemas for the opening insights backend."""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
)


class OpeningInsightsRequest(BaseModel):
    """Request body for POST /api/insights/openings.

    Mirrors the existing /openings/* and /stats/most-played-openings filter
    surface.

    extra="forbid" gates injection of unknown fields (V4 ASVS):
    any unknown key in the request body returns 422 Unprocessable Entity.
    The router derives the user's identity from current_active_user only.
    """

    model_config = ConfigDict(extra="forbid")

    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None
    color: Literal["all", "white", "black"] = "all"

    @model_validator(mode="after")
    def _check_date_range(self) -> "OpeningInsightsRequest":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be <= to_date")
        return self


class OpeningInsightFinding(BaseModel):
    """Single opening weakness or strength finding.

    Hash fields (entry_full_hash, resulting_full_hash) are typed as str to
    preserve 64-bit Zobrist hash precision at the JSON boundary — mirrors
    OpeningWDL.full_hash:str.

    Classification is score-based, annotated by confidence (Wilson score-test).
    """

    color: Literal["white", "black"]
    classification: Literal["weakness", "strength"]
    severity: Literal["minor", "major"]
    opening_name: str  # "<unnamed line>" sentinel when no openings-table match
    opening_eco: str  # "" sentinel when no openings-table match
    display_name: str  # may include "vs. " prefix
    entry_fen: str
    entry_san_sequence: list[
        str
    ]  # SAN tokens from start to entry position (candidate excluded); for FE deep-link replay
    entry_full_hash: str  # str-form for JSON precision
    candidate_move_san: str
    resulting_full_hash: str  # str-form, same reason
    # Range constraints enforce API-boundary invariants (CLAUDE.md: leverage
    # Pydantic for validation). n_games is gated by the SQL HAVING clause at
    # MIN_GAMES_PER_CANDIDATE; w/d/l are non-negative game counts; score is
    # in [0, 1] by construction (score = (w + d/2)/n); p_value is the
    # two-sided Wilson score-test p, bounded in [0, 1].
    n_games: int = Field(ge=OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)  # (W + D/2)/n; canonical classification metric
    confidence: Literal[
        "low", "medium", "high"
    ]  # Two-sided Wilson score-test p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium) (shared via score_confidence.py)
    p_value: float = Field(
        ge=0.0, le=1.0
    )  # Two-sided Wilson score-test p-value on H0: score = 0.50 (null SE = 0.5/sqrt(n))
    # Wilson 95% score interval bounds, clamped to [0, 1]. Same formula used for
    # ranking (score_confidence.wilson_bounds); exposed so the FE can render the CI
    # whisker on the bullet chart.
    ci_low: float = Field(ge=0.0, le=1.0)
    ci_high: float = Field(ge=0.0, le=1.0)
    # MG-entry pillar (parity with OpeningWDL).
    # Populated after the finding is built by looking up resulting_full_hash in
    # query_opening_phase_entry_metrics_batch. Defaults mirror OpeningWDL defaults.
    # Card findings only. The z-test is centred on the
    # finding colour's baseline (opening_eval.finalize_opening_eval, D-13); avg_eval_pawns
    # stays the raw mean.
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None
    eval_confidence: Literal["low", "medium", "high"] = "low"
    # MAX(games.played_at) across all games where the user reached this
    # (entry, candidate) transition. Drives the finding card's relative "last played"
    # date and the score popover's "Last played" line. None when every contributing
    # game has a NULL played_at.
    last_played_at: datetime.datetime | None = None
    # True when last_played_at is on or after the finding colour's current-repertoire
    # cutoff (repertoire_recency, D-02/D-04). False adds the card's "Not played recently"
    # archive icon; it does not change the card order.
    is_current: bool = True


class OpeningInsightsResponse(BaseModel):
    """Per-section findings for the merged Openings Stats page, by color x classification.

    Four card lists (``white_weaknesses``, ``black_weaknesses``, ``white_strengths``,
    ``black_strengths``) hold at most FINDINGS_CARD_CAP (10) findings each, the top of the
    direction-aware Wilson bound order, any confidence (D-38): ``confidence`` decides the
    card's colour, not whether it is listed. All lists are always present; empty ones are a
    valid empty state. The per-colour eval baseline is not echoed: it is the fixed
    EVAL_BASELINE_PAWNS_* pair, mirrored by the frontend openingStatsZones constants
    (parity test in tests/services/test_opening_insights_arrow_consistency.py).
    """

    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
