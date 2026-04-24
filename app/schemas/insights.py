"""Pydantic v2 schemas for the endgame findings pipeline (Phase 63).

Defined per FIND-01 / FIND-05 — the schema is the contract consumed by
`insights_service.compute_findings` (Plan 04) and by the Phase 65 LLM endpoint's
prompt-assembly. Field names are LOCKED once this ships: renaming after
Phase 65 forces a prompt revision.

Re-exports `Zone`, `Trend`, `SampleQuality`, `Window`, `MetricId`, and
`SubsectionId` from `app.services.endgame_zones` so consumers only need one
import path. Plan 01 owns those type aliases; this module does not redefine
them.

Field declaration order matters for `findings_hash` determinism (FIND-05):
Pydantic v2's `model_dump_json` emits fields in declaration order, and the
service re-serialises with `json.dumps(sort_keys=True)` for cross-session
stability (see Plan 04 / RESEARCH.md §Hash Implementation).
"""

import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Re-import the Literal aliases owned by Plan 01 so `from app.schemas.insights
# import Zone` works and consumers do not need to know about
# `app.services.endgame_zones`.
from app.services.endgame_zones import (
    MetricId as MetricId,
)
from app.services.endgame_zones import (
    SampleQuality as SampleQuality,
)
from app.services.endgame_zones import (
    SubsectionId as SubsectionId,
)
from app.services.endgame_zones import (
    Trend as Trend,
)
from app.services.endgame_zones import (
    Window as Window,
)
from app.services.endgame_zones import (
    Zone as Zone,
)
from app.schemas.endgames import (
    EndgameCategoryStats,
    EndgamePerformanceResponse,
    TimePressureChartResponse,
)

__all__ = [
    "EndgameInsightsReport",
    "EndgameInsightsResponse",
    "EndgameTabFindings",
    "FilterContext",
    "InsightsError",
    "InsightsErrorResponse",
    "InsightsStatus",
    "MetricId",
    "PlayerProfileEntry",
    "SampleQuality",
    "SectionId",
    "SectionInsight",
    "SubsectionFinding",
    "SubsectionId",
    "TimePoint",
    "Trend",
    "Window",
    "Zone",
]


# ---------------------------------------------------------------------------
# Literal aliases owned by this module (cross-section concepts, not zone-level).
# ---------------------------------------------------------------------------

# Section grouping used by Phase 65 prompt-assembly. NOT stored on
# SubsectionFinding — section membership is derived at consumption time
# (CONTEXT.md §Specifics).
SectionId = Literal[
    "overall",
    "metrics_elo",
    "time_pressure",
    "type_breakdown",
]

# Discriminator on EndgameInsightsResponse. Frontend TanStack Query branches
# on this value (Phase 66) — "cache_hit" vs "fresh" vs "stale_rate_limited"
# drive different banner states.
InsightsStatus = Literal["fresh", "cache_hit", "stale_rate_limited"]

# Error codes on InsightsErrorResponse. Stable machine-readable prefixes,
# NOT user-facing copy — Phase 66 frontend owns the retry-message mapping.
# "rate_limit_exceeded" fires only when BOTH tier-1 cache lookup AND tier-2
# get_latest_report_for_user return None (D-11); "provider_error" covers
# ModelAPIError subclasses; "validation_failure" covers
# UnexpectedModelBehavior after output_retries exhaust; "config_error" is
# defensive (should never reach clients — lifespan aborts first).
InsightsError = Literal[
    "rate_limit_exceeded", "provider_error", "validation_failure", "config_error"
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FilterContext(BaseModel):
    """User's active dashboard filter state, forwarded to `compute_findings`.

    Mirrors the endgame router's query-parameter surface. Three caveats:

    1. ``color`` is carried here for filter-faithfulness but is NOT forwarded
       to ``endgame_service.get_endgame_overview`` (which has no color filter).
       Per INS-03, ``color`` is also NOT fed into the LLM prompt — Phase 65
       treats it as context-only. Plan 63-03 defines the schema; wiring is a
       Plan 63-04 concern (the service must drop ``color`` before calling
       the endgame service).

    2. ``rated_only`` is included for filter-faithfulness and IS forwarded
       to the endgame service (as the ``rated`` parameter). Per INS-03 it is
       not fed into the LLM prompt.

    3. ``opponent_type`` is hardcoded to ``"human"`` inside
       ``compute_findings``; Phase 63 does not expose bot-filter findings.

    4. ``recency`` is the user's dashboard recency filter — SEPARATE from the
       two internal windows (``all_time``, ``last_3mo``) that
       ``compute_findings`` always produces (RESEARCH.md §Pitfall 4).
    """

    recency: Literal[
        "all_time",
        "week",
        "month",
        "3months",
        "6months",
        "year",
        "3years",
        "5years",
    ] = "all_time"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    color: Literal["all", "white", "black"] = "all"
    time_controls: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    rated_only: bool = False


class SubsectionFinding(BaseModel):
    """Finding for one subsection x one time window.

    Empty-window convention: when a subsection has zero qualifying games for
    the window, the service emits ``value=float('nan')`` (serialised as JSON
    ``null`` by Pydantic v2), ``zone="typical"``, ``trend="n_a"``,
    ``sample_size=0``, ``sample_quality="thin"``,
    ``is_headline_eligible=False``. Phase 65 prompt-assembly skips findings
    where ``sample_quality == "thin"`` AND ``value`` is null.

    ``dimension`` carries per-combo or per-bucket identity (e.g.
    ``{"platform": "chess.com", "time_control": "blitz"}`` for
    ``endgame_elo_timeline``, ``{"bucket": "conversion"}`` for
    ``endgame_metrics`` bucketed rows). Keeping combo identity in a dedicated
    ``dict[str, str] | None`` preserves the ``value: float`` contract.

    Field declaration order is load-bearing for ``findings_hash`` stability
    (Plan 04 re-serialises with ``json.dumps(sort_keys=True)`` for final
    determinism, but the declaration order is still the canonical shape).
    """

    subsection_id: SubsectionId
    parent_subsection_id: SubsectionId | None = None
    window: Window
    metric: MetricId
    value: float
    zone: Zone
    trend: Trend
    weekly_points_in_window: int
    sample_size: int
    sample_quality: SampleQuality
    is_headline_eligible: bool
    dimension: dict[str, str] | None = None
    # Phase 65 D-02: populated ONLY for the 4 timeline subsections
    # (score_gap_timeline, clock_diff_timeline, endgame_elo_timeline,
    # type_win_rate_timeline). None for non-timeline findings — default
    # preserves existing callers unchanged. Append-only: reordering this
    # field above another existing field would churn findings_hash.
    series: list["TimePoint"] | None = None


class EndgameTabFindings(BaseModel):
    """Deterministic findings for the Endgame tab.

    ``findings_hash`` is a 64-char lowercase hex SHA256 of the canonical JSON
    of this model with ``as_of`` and ``findings_hash`` itself excluded.
    Excluding ``as_of`` means identical findings on different days cache-hit
    (FIND-05).

    ``findings_hash`` is populated by ``compute_findings`` AFTER all other
    fields are set. Callers pass ``findings_hash=""`` as a placeholder during
    construction; the service computes the hash and returns a new model with
    the hash filled.
    """

    as_of: datetime.datetime
    filters: FilterContext
    findings: list[SubsectionFinding]
    # Raw 10-bucket time-pressure chart data (user_series + opp_series) from
    # the all_time window. Rendered directly in the user prompt by
    # `_assemble_user_prompt` because the 20-point curve does not fit the
    # single-value SubsectionFinding shape. Optional so existing test fixtures
    # that construct EndgameTabFindings without chart data still work.
    time_pressure_chart: TimePressureChartResponse | None = None
    # Endgame vs non-endgame WDL summary (all_time window) — feeds the
    # `## Chart: overall_wdl` block in the user prompt so the LLM can see the
    # underlying Win/Draw/Loss/Score % rows behind the single `score_gap`
    # finding. Optional for backwards compatibility with test fixtures.
    overall_performance: EndgamePerformanceResponse | None = None
    # Per-endgame-type W/D/L summary (all_time window) — feeds the
    # `## Chart: results_by_endgame_type_wdl` block so the LLM can see the
    # Score % per type behind the single `win_rate` finding (which excludes
    # draws). Optional for backwards compatibility.
    type_categories: list[EndgameCategoryStats] | None = None
    # Per-(platform, time_control) Elo context used by the LLM to calibrate
    # narrative tone to skill level. None when no qualifying combo exists
    # (new user with too few games). See PlayerProfileEntry for shape.
    player_profile: list["PlayerProfileEntry"] | None = None
    findings_hash: str


class PlayerProfileEntry(BaseModel):
    """One (platform, time_control) combo's Elo context for the LLM prompt.

    Surfaces current rating, historical range, and window-keyed stats so the
    LLM can adjust register (beginner vs intermediate vs advanced) without
    being told an explicit skill-level label. Populated by
    `compute_player_profile` from the endgame_elo timeline combos.

    The new shape mirrors the unified `[summary]` block format used for all
    other windowed metrics: an all_time line (mean / n / buckets / trend /
    std) plus a last_3mo line anchored to calendar-now. When a combo has no
    games in the last 90 calendar days, the last_3mo fields stay None and
    the prompt emits "last_3mo : no data" — this replaces the old free-text
    `trajectory` string ("+93 over 3 months") which was anchored to the
    combo's last game date, not calendar-now, and silently misled on stale
    combos.
    """

    platform: Literal["chess.com", "lichess"]
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    games: int  # total qualifying points in the combo (drives sort order)
    current_elo: int
    min_elo: int
    max_elo: int
    window_days: int  # span from first to last qualifying point

    # all_time window stats (always populated when the entry is emitted).
    all_time_mean: int
    all_time_n: int  # total endgame games across all weekly points
    all_time_buckets: int  # count of qualifying weekly points
    all_time_trend: Literal["improving", "regressing", "flat"]
    all_time_std: int

    # last_3mo (calendar-last-90d) window stats. None when the combo has no
    # weekly points in the last 90 days — the prompt emits "no data" in that
    # case so the LLM can't read stale combos as recent activity.
    last_3mo_mean: int | None = None
    last_3mo_n: int | None = None
    last_3mo_buckets: int | None = None
    last_3mo_trend: Literal["improving", "regressing", "flat"] | None = None
    last_3mo_std: int | None = None

    # Stale marker: populated when the combo's last weekly point is more
    # than ~6 months behind calendar-now. Both fields are emitted as a pair.
    stale_last_bucket: str | None = None  # YYYY-MM
    stale_months: int | None = None


class TimePoint(BaseModel):
    """One point on a resampled timeseries attached to a timeline SubsectionFinding.

    `bucket_start` is ISO YYYY-MM-DD: first-of-week (Monday) for `last_3mo`
    window, first-of-month for `all_time` window (D-03).

    `n` is the sample size for this bucket (weekly game count for last_3mo,
    summed-over-the-month for all_time — see insights_service resampler).

    `actual_elo` is populated ONLY for `endgame_elo_timeline` series; None for
    all other timelines. Carrying the user's actual rating alongside the gap
    lets the prompt render `gap=<v>, elo=<r>` per bucket so the LLM can
    distinguish endgame-skill regression from rating growth outpacing skill.
    """

    bucket_start: str  # ISO YYYY-MM-DD
    value: float
    n: int
    actual_elo: int | None = None


class SectionInsight(BaseModel):
    """One `section` entry in EndgameInsightsReport. LLM emits up to 4 of these.

    Length bounds enforce prompt-compliance: headline <=120 chars (~12 words),
    bullets 0-5 items, each at most 200 chars (~20 words). The prompt asks
    for 1-5 bullets per section but the schema leaves min_length at 0 so the
    LLM is not forced to pad with weak bullets. Pydantic rejects oversized
    output -> pydantic-ai's output_retries (2) retries the Agent.
    """

    section_id: SectionId
    headline: str = Field(..., max_length=120)
    bullets: list[str] = Field(default_factory=list, max_length=5)


class EndgameInsightsReport(BaseModel):
    """LLM-produced structured report.

    Shape locked by:
      - INS-06: `overview` is `str` (not `str | None`); Pydantic rejects null.
        Always-populate rule is enforced in the system prompt (endgame_insights.md).
      - D-19: `sections` has `min_length=1, max_length=4`. LLM decides which
        to include based on sample_quality of underlying findings.
      - D-20: `unique_section_ids` validator is a cheap safety net — duplicate
        section_id raises ValueError; pydantic-ai catches and retries.
      - D-17: `model_used` + `prompt_version` echoed back for frontend debug.
      - v9: `player_profile` (~3-5 sentence paragraph) and `recommendations`
        (2-4 short bullets) are first-class top-of-page blocks rendered above
        the `overview`. The LLM derives both from the `## Player profile`
        block in the user prompt and the per-section findings.
    """

    player_profile: str = Field(..., min_length=1, max_length=800)
    overview: str
    recommendations: list[str] = Field(..., min_length=2, max_length=4)
    sections: list[SectionInsight] = Field(..., min_length=1, max_length=4)
    model_used: str
    prompt_version: str

    @model_validator(mode="after")
    def unique_section_ids(self) -> "EndgameInsightsReport":
        ids = [s.section_id for s in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate section_id")
        return self

    @model_validator(mode="after")
    def recommendations_length(self) -> "EndgameInsightsReport":
        for rec in self.recommendations:
            if not rec.strip():
                raise ValueError("recommendation must not be empty")
            if len(rec) > 200:
                raise ValueError("recommendation exceeds 200 chars")
        return self


class EndgameInsightsResponse(BaseModel):
    """HTTP 200 success envelope.

    `stale_filters` is populated ONLY when `status == "stale_rate_limited"`
    AND the fallback log's filter_context differs from the current request's
    FilterContext (D-14). Phase 66 reads this to show a "showing stale
    results for <filters>" banner.
    """

    report: EndgameInsightsReport
    status: InsightsStatus
    stale_filters: FilterContext | None = None


class InsightsErrorResponse(BaseModel):
    """HTTP 429 / 502 / 503 error envelope. Frontend owns user-facing copy.

    `retry_after_seconds` populated ONLY for 429 (computed from oldest miss
    in the rate-limit window, D-15 + RESEARCH.md §4). Null for 502/503.
    """

    error: InsightsError
    retry_after_seconds: int | None = None


# Update SubsectionFinding to resolve the forward reference to TimePoint.
# TimePoint is defined after SubsectionFinding (required because SubsectionFinding
# uses it in a list annotation), so we call model_rebuild() to resolve it.
SubsectionFinding.model_rebuild()
# Same pattern for EndgameTabFindings -> PlayerProfileEntry forward ref.
EndgameTabFindings.model_rebuild()
