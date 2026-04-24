"""Gauge zone registry: authoritative Python source of truth for endgame metric thresholds.

Python is the authoritative home for gauge thresholds (per Phase 63 D-01). The
constants exported here drive `insights_service.compute_findings` zone
assignment and get code-generated to `frontend/src/generated/endgameZones.ts`
by `scripts/gen_endgame_zones_ts.py` in a follow-up plan so the frontend
gauges and the insights narrative agree by construction (FIND-02).

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.schemas.endgames import MaterialBucket

# ---------------------------------------------------------------------------
# Literal type aliases — the Pydantic schemas in app/schemas/insights.py (Plan
# 03) re-import these so the wire format and the registry share one name set.
# ---------------------------------------------------------------------------

Zone = Literal["weak", "typical", "strong"]
Trend = Literal["improving", "declining", "stable", "n_a"]
SampleQuality = Literal["thin", "adequate", "rich"]
Window = Literal["all_time", "last_3mo"]

MetricId = Literal[
    "score_gap",
    # Phase 68 (260424-pc6): per-part absolute score metrics emitted by the
    # score_timeline subsection. `score_gap` still carries the signed
    # aggregate; `endgame_score` / `non_endgame_score` carry each side's
    # absolute 0-100% score so the prompt narrates two absolute lines
    # instead of two part-tagged score_gap blocks whose labels contradicted
    # their series values. Neither has a calibrated zone band — callers
    # render them as "typical" (see assign_zone NaN/unregistered handling).
    "endgame_score",
    "non_endgame_score",
    "endgame_skill",
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    "endgame_elo_gap",
    "win_rate",
]

SubsectionId = Literal[
    "overall",
    "score_timeline",
    "endgame_metrics",
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    "results_by_endgame_type",
    "conversion_recovery_by_type",
    "type_win_rate_timeline",
]

BucketedMetricId = Literal[
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
]


# ---------------------------------------------------------------------------
# ZoneSpec — boundaries and direction for one metric in the registry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoneSpec:
    """Zone boundaries and direction for one metric.

    Values on or between `typical_lower` and `typical_upper` count as
    `typical`. `direction` determines which side of the band maps to
    `strong` vs `weak`:
    - `higher_is_better`: value >= typical_upper -> strong; < typical_lower -> weak
    - `lower_is_better`:  value <= typical_lower -> strong; > typical_upper -> weak
    """

    typical_lower: float
    typical_upper: float
    direction: Literal["higher_is_better", "lower_is_better"]


# ---------------------------------------------------------------------------
# Named-constant thresholds — no magic numbers in function bodies. Every
# value referenced by a flag rule or trend gate lives here with a comment
# explaining its source.
# ---------------------------------------------------------------------------

# Minimum weekly data points in window to compute a trend (FIND-04).
TREND_MIN_WEEKLY_POINTS: int = 20

# Minimum slope-to-volatility ratio to emit a directional trend (FIND-04).
# Placeholder value — Plan 04 may tune against the SEED-001 fixture.
TREND_MIN_SLOPE_VOL_RATIO: float = 0.5

# Max |endgame_elo - actual_elo| that counts as not-notable (D-09 flag 4).
# Values above this threshold across any (platform, time_control) combo fire
# the `notable_endgame_elo_divergence` cross-section flag.
NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD: int = 100

# Neutral band for clock-diff percentage of base time (mirrors the inline
# frontend constant in EndgameClockPressureSection.tsx line 18). Used by the
# `clock_entry_advantage` / `no_clock_entry_advantage` flags (D-09).
NEUTRAL_PCT_THRESHOLD: float = 10.0

# Neutral band for net timeout rate in percentage points (mirrors the inline
# frontend constant in EndgameClockPressureSection.tsx line 23).
NEUTRAL_TIMEOUT_THRESHOLD: float = 5.0


# ---------------------------------------------------------------------------
# ZONE_REGISTRY — scalar metrics (one band per metric).
# ---------------------------------------------------------------------------

ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] = {
    # Score Gap: signed 0.0-1.0 scale (score_difference from ScoreGapMaterialResponse).
    # Typical band = -0.10 to +0.10 (±10pp), mirrors EndgamePerformanceSection.tsx
    # SCORE_GAP_NEUTRAL_MIN/MAX.
    "score_gap": ZoneSpec(
        typical_lower=-0.10,
        typical_upper=0.10,
        direction="higher_is_better",
    ),
    # Phase 68 (260424-pc6): absolute per-part rolling Score % used by the
    # score_timeline subsection's two-line chart. There is no calibrated
    # cohort band for "your endgame Score in isolation" (the zoned signal is
    # score_gap, not absolute score), so the typical band is defined to span
    # the full [0, 1] range — every value resolves to "typical". Keeping
    # entries here (rather than making assign_zone return "typical" for
    # unknown metrics) preserves the MetricId-Literal invariant and the
    # single-source-of-truth contract for all metrics referenced in
    # compute_findings.
    "endgame_score": ZoneSpec(
        typical_lower=0.0,
        typical_upper=1.0,
        direction="higher_is_better",
    ),
    "non_endgame_score": ZoneSpec(
        typical_lower=0.0,
        typical_upper=1.0,
        direction="higher_is_better",
    ),
    # Endgame Skill: simple average of Conv/Parity/Recov rates (0.0-1.0).
    # Mirrors ENDGAME_SKILL_ZONES in EndgameScoreGapSection.tsx lines 101-105.
    "endgame_skill": ZoneSpec(
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    # Clock diff at endgame entry, % of base time, signed.
    # Typical band = ±NEUTRAL_PCT_THRESHOLD (10%). Above = user has more time left
    # at endgame entry than opponent (good); below = user has less (bad).
    "avg_clock_diff_pct": ZoneSpec(
        typical_lower=-NEUTRAL_PCT_THRESHOLD,
        typical_upper=NEUTRAL_PCT_THRESHOLD,
        direction="higher_is_better",
    ),
    # Net timeout rate (signed percent).
    # Formula: (timeout_wins - timeout_losses) / total_endgame_games * 100.
    # Positive = user wins more flag battles than they lose (strong); negative
    # = user gets flagged more than they flag (weak). higher_is_better keeps
    # the metric's natural reading — no sign-flip gymnastics anywhere else in
    # the pipeline.
    "net_timeout_rate": ZoneSpec(
        typical_lower=-NEUTRAL_TIMEOUT_THRESHOLD,
        typical_upper=NEUTRAL_TIMEOUT_THRESHOLD,
        direction="higher_is_better",
    ),
    # Endgame ELO gap (endgame_elo - actual_elo, signed Elo).
    # Typical band = ±100 Elo, matches NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD.
    # Per-combo fan-out happens at the finding level, not here — the registry
    # entry is the band used for each individual (platform, tc) finding.
    "endgame_elo_gap": ZoneSpec(
        typical_lower=-100.0,
        typical_upper=100.0,
        direction="higher_is_better",
    ),
    # Plain win rate (W / total, draws excluded) for per-type findings in the
    # results_by_endgame_type and type_win_rate_timeline subsections. Band
    # mirrors endgame_skill (0.45-0.55) because before the relabel these same
    # values were zoned with the endgame_skill spec. Kept identical to
    # preserve all prior zone assignments.
    "win_rate": ZoneSpec(
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
}


# ---------------------------------------------------------------------------
# BUCKETED_ZONE_REGISTRY — per-MaterialBucket bands for Conv/Parity/Recov
# rate metrics. Each bucket shares the same band per metric (FE
# FIXED_GAUGE_ZONES pattern).
# ---------------------------------------------------------------------------

BUCKETED_ZONE_REGISTRY: Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]] = {
    "conversion_win_pct": {
        "conversion": ZoneSpec(0.65, 0.75, "higher_is_better"),
        "parity": ZoneSpec(0.65, 0.75, "higher_is_better"),
        "recovery": ZoneSpec(0.65, 0.75, "higher_is_better"),
    },
    "parity_score_pct": {
        "conversion": ZoneSpec(0.45, 0.55, "higher_is_better"),
        "parity": ZoneSpec(0.45, 0.55, "higher_is_better"),
        "recovery": ZoneSpec(0.45, 0.55, "higher_is_better"),
    },
    "recovery_save_pct": {
        # D-10: recovery typical band re-centered to [0.25, 0.35] (was [0.30, 0.40]).
        # Pooled benchmark median is 0.32 — re-centering makes "typical" honest.
        # Same change applied to FIXED_GAUGE_ZONES.recovery in
        # EndgameScoreGapSection.tsx so FE and registry agree.
        "conversion": ZoneSpec(0.25, 0.35, "higher_is_better"),
        "parity": ZoneSpec(0.25, 0.35, "higher_is_better"),
        "recovery": ZoneSpec(0.25, 0.35, "higher_is_better"),
    },
}


# ---------------------------------------------------------------------------
# SAMPLE_QUALITY_BANDS — per-subsection (thin_max, adequate_max) bands.
# value < thin_max → thin; < adequate_max → adequate; otherwise → rich.
# Per-subsection denominators stay honest: type breakdown splits 5 ways, so
# its bands are ~5× smaller than overall (D-16 rationale).
# ---------------------------------------------------------------------------

SAMPLE_QUALITY_BANDS: Mapping[SubsectionId, tuple[int, int]] = {
    "overall": (50, 200),
    "score_timeline": (10, 52),
    "endgame_metrics": (30, 100),
    "endgame_elo_timeline": (10, 40),
    "time_pressure_at_entry": (10, 50),
    "clock_diff_timeline": (10, 52),
    "time_pressure_vs_performance": (30, 100),
    "results_by_endgame_type": (10, 40),
    "conversion_recovery_by_type": (10, 40),
    "type_win_rate_timeline": (5, 20),
}


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _zone_from_spec(spec: ZoneSpec, value: float) -> Zone:
    """Map a scalar value to a zone using the direction semantics in spec."""
    if spec.direction == "higher_is_better":
        if value >= spec.typical_upper:
            return "strong"
        if value >= spec.typical_lower:
            return "typical"
        return "weak"
    # lower_is_better: low values are strong, high values are weak.
    if value <= spec.typical_lower:
        return "strong"
    if value <= spec.typical_upper:
        return "typical"
    return "weak"


def assign_zone(metric_id: MetricId, value: float) -> Zone:
    """Assign a zone for a scalar metric.

    Returns `"typical"` for NaN so empty-window findings do not raise and do
    not fire false-positive flags. Callers distinguish "no data" from
    "typical data" via `is_headline_eligible=False` on the emitted
    SubsectionFinding (Plan 03), not via the zone value.
    """
    if math.isnan(value):
        return "typical"
    return _zone_from_spec(ZONE_REGISTRY[metric_id], value)


def assign_bucketed_zone(
    metric_id: BucketedMetricId,
    bucket: MaterialBucket,
    value: float,
) -> Zone:
    """Assign a zone for a per-MaterialBucket metric.

    Returns `"typical"` for NaN (see `assign_zone` docstring for rationale).
    """
    if math.isnan(value):
        return "typical"
    return _zone_from_spec(BUCKETED_ZONE_REGISTRY[metric_id][bucket], value)


def sample_quality(subsection_id: SubsectionId, sample_size: int) -> SampleQuality:
    """Classify `sample_size` into thin/adequate/rich using per-subsection bands.

    Bands per D-16: each subsection has its own `(thin_max, adequate_max)` pair
    so denominators stay honest (per-type bands are 5× smaller than overall).
    """
    thin_max, adequate_max = SAMPLE_QUALITY_BANDS[subsection_id]
    if sample_size < thin_max:
        return "thin"
    if sample_size < adequate_max:
        return "adequate"
    return "rich"
