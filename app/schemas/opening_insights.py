"""Pydantic v2 schemas for Phase 70 opening insights backend (D-26)."""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
    EVAL_BASELINE_PAWNS_WHITE,
    EVAL_BASELINE_PAWNS_BLACK,
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
    """Single opening weakness or strength finding (D-03, D-05, D-25; Phase 75 D-09).

    Hash fields (entry_full_hash, resulting_full_hash) are typed as str to
    preserve 64-bit Zobrist hash precision at the JSON boundary — mirrors
    OpeningWDL.full_hash:str (RESEARCH.md Pitfall 1).

    Phase 75 (v1.14) replaced loss_rate/win_rate with score-based
    classification annotated by confidence (Wilson score-test as of quick
    task 260507-aw5; Wald previously).
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
    # two-sided Wilson score-test p, bounded in [0, 1].
    n_games: int = Field(ge=OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    score: float = Field(
        ge=0.0, le=1.0
    )  # (W + D/2)/n; canonical classification metric (Phase 75 D-09)
    confidence: Literal[
        "low", "medium", "high"
    ]  # Two-sided Wilson score-test p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium) (shared via score_confidence.py)
    p_value: float = Field(
        ge=0.0, le=1.0
    )  # Two-sided Wilson score-test p-value on H0: score = 0.50 (null SE = 0.5/sqrt(n))
    # Wilson 95% score interval bounds, clamped to [0, 1]. Same formula already
    # used internally for ranking (_wilson_bounds); now exposed so the FE can
    # render the CI whisker on the bullet chart.
    ci_low: float = Field(ge=0.0, le=1.0)
    ci_high: float = Field(ge=0.0, le=1.0)
    # MG-entry pillar (parity with OpeningWDL Phase 80 — quick task 260506-u2b).
    # Populated after the finding is built by looking up resulting_full_hash in
    # query_opening_phase_entry_metrics_batch. Defaults mirror OpeningWDL defaults.
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None
    eval_confidence: Literal["low", "medium", "high"] = "low"
    # MAX(games.played_at) across all games where the user reached this
    # (entry, candidate) transition. Drives the "Last played: <relative>" line
    # in the OpeningFindingCard score-confidence popover (quick task
    # 260508-r61). None when every contributing game has a NULL played_at.
    last_played_at: datetime.datetime | None = None


class OpeningInsightsResponse(BaseModel):
    """Four-section response structured by color x classification (D-01, D-02).

    All four lists are always present; empty sections are valid empty-state
    (D-20). Phase 71 renders four labeled sections.

    Quick task 260506-u2b: top-level per-color MG-entry eval baselines mirror
    MostPlayedOpeningsResponse so the FE can render the same reference tick on
    the finding cards' eval bullet charts.
    """

    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    # Per-color engine-asymmetry baselines (in pawns). Rendered as a small
    # reference tick on the finding card's MG-entry bullet chart. NOT used as
    # the H0 reference for the z-test (anchored at 0 cp per 260504-rvh).
    eval_baseline_pawns_white: float = EVAL_BASELINE_PAWNS_WHITE
    eval_baseline_pawns_black: float = EVAL_BASELINE_PAWNS_BLACK
