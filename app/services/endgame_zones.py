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

from app.schemas.endgames import EndgameClass, MaterialBucket

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
    "achievable_score_gap",  # 260514 split-out — dedicated band so 3.1.5 can tighten without affecting 3.1.6
    # Phase 87.1 (SEED-016 D-02): per-span, per-type version of achievable_score_gap.
    # User-facing label is "Endgame Type Score Gap" (concepts) / "Score Gap" (card row).
    # Internal name retains "achievable" to mark the math-family with achievable_score_gap (Phase 85.1).
    "endgame_type_achievable_score_gap",
    # Phase 87.2 (D-02 / D-07): per-bucket Score Gap on Section 2 cards.
    # User-facing labels (card row): "Conversion Score Gap" / "Parity Score Gap" /
    # "Recovery Score Gap" / "Skill Score Gap" (D-07). Glossary umbrella: "Section 2
    # Score Gap" (D-07). Internal snake_case preserves grep-ability with the
    # achievable_score_gap family. Option (a) from D-02 RESEARCH: 4 distinct scalar
    # MetricIds (not a bucket-dispatched parent) because dispatch here is eval-entry-
    # bucket-keyed, not class-keyed like PER_CLASS_GAUGE_ZONES. See BucketedMetricId
    # note below.
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    "section2_score_gap_recov",
    "entry_eval_pawns",  # Phase 82 D-04: new endgame_start_vs_end Tile 1
    "entry_expected_score",  # Phase 83 D-17: new endgame_start_vs_end Tile 1 row 2 — achievable score
    "endgame_score",  # Phase 82 D-03: repurposed for endgame_start_vs_end Tile 2 (was the score_timeline metric in v22)
    # Phase 68 (260424-pc6): per-part absolute score metrics emitted by the
    # score_timeline subsection. `score_gap` still carries the signed
    # aggregate; `endgame_score_timeline` / `non_endgame_score_timeline` carry
    # each side's absolute 0-100% score so the prompt narrates two absolute
    # lines instead of two part-tagged score_gap blocks whose labels
    # contradicted their series values. Neither has a calibrated zone band —
    # callers render them as "typical" (see assign_zone NaN/unregistered
    # handling). Phase 82 D-01/D-02: renamed from "endgame_score" /
    # "non_endgame_score" to free the clean slot for the new subsection.
    "endgame_score_timeline",  # Phase 82 D-01: renamed from "endgame_score" (score_timeline subsection)
    "non_endgame_score_timeline",  # Phase 82 D-02: renamed from "non_endgame_score"
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    # Phase 87.5 D-06: restored from "conversion_elo_gap" — Endgame ELO Timeline
    # is now derived additively from Endgame Score Gap, not from Conv ΔES.
    "endgame_elo_gap",
    "win_rate",
]

SubsectionId = Literal[
    "overall",
    "endgame_start_vs_end",  # Phase 82 D-05
    "score_timeline",
    "endgame_metrics",
    # Phase 87.5 D-06: restored from "conversion_elo_timeline".
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    "results_by_endgame_type",
    "conversion_recovery_by_type",
]

# Phase 87.1 (SEED-016): `endgame_type_achievable_score_gap` is intentionally NOT
# added to BucketedMetricId — it is per-class only (via PER_CLASS_GAUGE_ZONES),
# not per-(class × material-axis). If benchmark §3.4.2 later requires per-rating-
# bucket bands, add it then in a follow-up.
# Phase 87.2 (D-02): the 3 Section 2 per-bucket ΔES MetricIds (`section2_score_gap_*`)
# are also NOT added here. They use 3 scalar MetricIds in ZONE_REGISTRY (option (a)),
# not a bucket-dispatched parent. The existing bucket-dispatch shape is class-keyed
# (PER_CLASS_GAUGE_ZONES), not eval-entry-bucket-keyed, so a new dispatch shape would
# be required for option (b) — D-02 RESEARCH recommends option (a) instead.
# Phase 87.4 (D-05): the 4th Skill ΔES bucket was dropped when the Endgame Skill
# concept was retracted; the 3 remaining buckets (conv/parity/recov) are unchanged.
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
# the `notable_endgame_elo_divergence` cross-section flag. Renamed in
# Phase 87.5 (D-06) alongside the Endgame ELO Timeline additive-K rewire.
NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD: int = 100

# Neutral band for clock-diff percentage of base time (mirrors the inline
# frontend constant in EndgameClockPressureSection.tsx line 18). Used by the
# `clock_entry_advantage` / `no_clock_entry_advantage` flags (D-09).
# Tightened from 10.0 to 5.0 — pooled IQR from reports/benchmarks-2026-05-01.md
# (260501-s0u benchmark calibration v2).
NEUTRAL_PCT_THRESHOLD: float = 5.0

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
    # Achievable Score Gap (Card 3 Achievable row, signed 0.0-1.0 scale).
    # Source: reports/benchmarks-latest.md §3.1.5 — pooled benchmark IQR
    # [-3.9pp, +4.6pp] rounds cleanly to ±5pp. Split off from `score_gap`
    # (260514-kei) because §3.1.6 (Endgame Score Gap) collapsed cleanly at
    # ±10pp while §3.1.5 needed a tighter band: the 2400-cohort median sits
    # at +3.5pp and would otherwise stay "typical blue" inside the old
    # shared ±10pp band. Per-ELO stratification deferred (d=0.62 keep-
    # separate verdict in the same §3.1.5).
    "achievable_score_gap": ZoneSpec(
        typical_lower=-0.05,
        typical_upper=0.05,
        direction="higher_is_better",
    ),
    # Phase 87.1 (SEED-016 D-04): per-span, per-type version. Calibrated
    # 260515 from §3.4.2 (reports/benchmarks-latest.md): pooled-across-classes
    # IQR (n=5,727 users, sparse cell excluded) = [-3.94pp, +4.34pp], rounded
    # to symmetric ±0.04. Per-class bands (PER_CLASS_GAUGE_ZONES below)
    # diverge by enough (width spread 6.6pp mixed -> 9.7pp minor_piece) to
    # warrant per-class overrides on top of this global default.
    "endgame_type_achievable_score_gap": ZoneSpec(
        typical_lower=-0.04,
        typical_upper=0.04,
        direction="higher_is_better",
    ),
    # Phase 87.2 (D-02): per-bucket bands for Section 2 ΔES Score Gap cards.
    # Calibrated 2026-05-15 from reports/benchmarks-latest.md §3.4.4 — pooled
    # per-user mean span gap per entry-eval bucket, sparse cell (2400,
    # classical) excluded, equal-footing filter applied, pooled [p25, p75]
    # rounded to nearest 1pp.
    #
    # Bands are intentionally OFF-ZERO for conversion and recovery because the
    # Lichess winning-chances sigmoid drives an asymmetric population null:
    # converting a winning position scores ~5pp BELOW entry ES (ceiling near
    # 1.0); recovering from a losing one scores ~6pp ABOVE (floor near 0.0).
    # Anchoring at 0 would mis-paint every typical user as "red on conv, green
    # on recov". The chart keeps 0 (or 50%) as the engine-neutral anchor; the
    # band is drawn offset where the calibration says it sits. The
    # MiniBulletChart asymmetric rendering contract is locked in by tests
    # added in quick task 260516-0ax.
    "section2_score_gap_conv": ZoneSpec(
        typical_lower=-0.11,
        typical_upper=0.00,
        direction="higher_is_better",
    ),
    "section2_score_gap_parity": ZoneSpec(
        typical_lower=-0.04,
        typical_upper=0.04,
        direction="higher_is_better",
    ),
    "section2_score_gap_recov": ZoneSpec(
        typical_lower=0.01,
        typical_upper=0.11,
        direction="higher_is_better",
    ),
    # Phase 87.4 (D-05): section2_score_gap_skill ZoneSpec deleted. The Skill
    # composite was retracted — no composite definition survived scrutiny on
    # cohort de-confounding, individual interpretation, temporal stability, or
    # the Phase 57 median-coincide invariant. See
    # `.planning/notes/endgame-skill-dropped-conversion-elo.md`.
    # entry_eval_pawns: average Stockfish eval at endgame entry, signed from
    # user's perspective. Phase 82 D-08.
    "entry_eval_pawns": ZoneSpec(
        # Pooled benchmark IQR `max(|p25|, |p75|) = 75 cp = 0.75 pawns`
        # (reports/benchmarks-2026-05-10.md §3, line 281). Single global
        # band justified (TC max d=0.22, ELO max d=0.28 per the same
        # §3 — both "review", not "keep separate"). Unit: signed pawns.
        typical_lower=-0.75,
        typical_upper=0.75,
        direction="higher_is_better",
    ),
    # entry_expected_score: per-user mean expected score (Lichess winning-
    # chances sigmoid applied to entry-ply Stockfish eval) over endgame-
    # reaching games. Phase 83 D-14/D-15/D-17.
    "entry_expected_score": ZoneSpec(
        # Pooled benchmark IQR (excl. sparse cell): [0.4629, 0.5536]
        # (reports/benchmarks-2026-05-11.md §7). Single global band justified —
        # TC max d=0.218 (bullet vs rapid), ELO max d=0.224 (800 vs 2000),
        # both "review" (≥ 0.2, < 0.5). Per-ELO stratification deferred.
        # Band locked to [0.45, 0.55]: round numbers, very close to pooled IQR,
        # match existing endgame_score band for visual parity with the §0
        # final-score zone (memory feedback_zone_band_judgement.md — band
        # alignment with neighbouring tile preferred over symmetric +1pp drift).
        # Unit: 0–1 scale (NOT percent), centered at 0.5 chess-fairness null.
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    "endgame_score": ZoneSpec(
        # Phase 82 D-10: reuse the live shared SCORE_BULLET_NEUTRAL band
        # (±0.05 around 0.5 → [0.45, 0.55]) for visual parity with the
        # Openings score bullet. Per-ELO ENDGAME_SCORE_ZONES deferred
        # (D-11). Unit: 0–1 scale (NOT percent).
        typical_lower=0.45,
        typical_upper=0.55,
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
    # Phase 82 D-01/D-02: renamed from "endgame_score" / "non_endgame_score"
    # to free the clean slot for the new endgame_start_vs_end subsection.
    # score_timeline-only; no calibrated band.
    "endgame_score_timeline": ZoneSpec(
        typical_lower=0.0,
        typical_upper=1.0,
        direction="higher_is_better",
    ),
    "non_endgame_score_timeline": ZoneSpec(
        typical_lower=0.0,
        typical_upper=1.0,
        direction="higher_is_better",
    ),
    # Phase 87.4 (D-05): endgame_skill ZoneSpec deleted. The Endgame Skill
    # composite concept was retracted end-to-end alongside the Conversion ELO
    # Timeline rewire (see `.planning/notes/endgame-skill-dropped-conversion-elo.md`).
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
    # Phase 87.5 D-06: restored from "conversion_elo_gap" — the additive-K
    # formula (endgame_elo = actual_elo + K · eg_score_gap) drives the gap.
    "endgame_elo_gap": ZoneSpec(
        typical_lower=-100.0,
        typical_upper=100.0,
        direction="higher_is_better",
    ),
    # Plain win rate (W / total, draws excluded) for per-type findings in the
    # results_by_endgame_type subsection. Band [0.45, 0.55] preserved from the
    # historical endgame_skill spec (retracted in Phase 87.4) so prior zone
    # assignments do not shift.
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
    # 260503: upper bound shifted 0.75 -> 0.77 — pooled p75 = 0.769 in
    # reports/benchmarks-2026-05-03.md, current 0.75 clipped ~25% of users
    # into the "above neutral" band.
    "conversion_win_pct": {
        "conversion": ZoneSpec(0.65, 0.77, "higher_is_better"),
        "parity": ZoneSpec(0.65, 0.77, "higher_is_better"),
        "recovery": ZoneSpec(0.65, 0.77, "higher_is_better"),
    },
    "parity_score_pct": {
        "conversion": ZoneSpec(0.45, 0.55, "higher_is_better"),
        "parity": ZoneSpec(0.45, 0.55, "higher_is_better"),
        "recovery": ZoneSpec(0.45, 0.55, "higher_is_better"),
    },
    "recovery_save_pct": {
        # 260503: tightened to [0.24, 0.36] — pooled p25/p75 = [0.243, 0.364]
        # in reports/benchmarks-2026-05-03.md. Previous [0.25, 0.40] upper
        # bound sat well above population p75 so almost no users ever read
        # "above neutral" on the recovery gauge.
        "conversion": ZoneSpec(0.24, 0.36, "higher_is_better"),
        "parity": ZoneSpec(0.24, 0.36, "higher_is_better"),
        "recovery": ZoneSpec(0.24, 0.36, "higher_is_better"),
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
    # Phase 82 D-05: new subsection, gates match time_pressure_at_entry
    # (thin < 10, adequate < 50, rich >= 50) — two single-aggregate tiles,
    # no per-type breakdown, so larger thin boundary than per-type subsections.
    "endgame_start_vs_end": (10, 50),
    "score_timeline": (10, 52),
    "endgame_metrics": (30, 100),
    "endgame_elo_timeline": (10, 40),  # Phase 87.5 D-06: restored from "conversion_elo_timeline".
    "time_pressure_at_entry": (10, 50),
    "clock_diff_timeline": (10, 52),
    "time_pressure_vs_performance": (30, 100),
    # 260501-s0u pass2: raised thin_max from 10 to 20 for per-type subsections.
    # 10-19 sequences was being labeled `adequate` and the LLM treated those
    # last_3mo windows as load-bearing (e.g. n=14 conv → "strong" headlines).
    # 20 is the minimum across the per-type emitter calls in the benchmark
    # cohort (≥20 endgame games per user gate).
    "results_by_endgame_type": (20, 40),
    "conversion_recovery_by_type": (20, 40),
}


# ---------------------------------------------------------------------------
# PER_CLASS_GAUGE_ZONES — per-endgame-class typical bands for Conversion and
# Recovery. Source: reports/benchmarks-2026-05-01.md (260501-s0u benchmark
# calibration v2), pooled p25/p75 per class. Codegen'd to frontend via
# scripts/gen_endgame_zones_ts.py.
#
# Each entry: conversion=(lower, upper), recovery=(lower, upper).
# Values are 0.0-1.0 fractions matching the frontend gauge scale.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands for Conversion, Recovery, and Score Gap for one endgame type."""

    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]  # Phase 87.1 — SEED-016 D-04


# 260503 shifts (reports/benchmarks-2026-05-03.md): rook recovery (0.28→0.26,
# 0.38→0.36) and pawn recovery (0.26→0.23, 0.36→0.34) — both pooled means sat
# below the previous lower bound. Pawn conversion upper bound nudged 0.77→0.79
# (pooled mean 0.738).
#
# Phase 87.1 (SEED-016 D-04): achievable_score_gap calibrated 260515 from
# reports/benchmarks-latest.md §3.4.2 — pooled per-user mean span gap per
# class, sparse cell (2400, classical) excluded, equal-footing filter applied.
# Per-class [p25, p75] rounded to nearest 1pp. Pawnless deferred (n=7 users —
# floor not met) and pinned to the global pooled band as a defensible default.
PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook": PerClassBands(
        conversion=(0.65, 0.75),
        recovery=(0.26, 0.36),
        # n=1,309 — pooled IQR [-4.97pp, +4.27pp]; TC d=0.20, ELO d=0.32 (both review).
        achievable_score_gap=(-0.05, 0.04),
    ),
    "minor_piece": PerClassBands(
        conversion=(0.63, 0.73),
        recovery=(0.31, 0.41),
        # n=1,129 — pooled IQR [-4.21pp, +5.53pp]; TC d=0.12 (collapse), ELO d=0.39 (review).
        achievable_score_gap=(-0.04, 0.06),
    ),
    "pawn": PerClassBands(
        conversion=(0.67, 0.79),
        recovery=(0.23, 0.34),
        # n=795 — pooled IQR [-3.98pp, +4.85pp]; TC d=0.29, ELO d=0.24 (both review).
        achievable_score_gap=(-0.04, 0.05),
    ),
    "queen": PerClassBands(
        conversion=(0.73, 0.83),
        recovery=(0.20, 0.30),
        # n=744 — pooled IQR [-4.63pp, +4.60pp]; TC d=0.49 (review/borderline keep), ELO d=0.39.
        achievable_score_gap=(-0.05, 0.05),
    ),
    "mixed": PerClassBands(
        conversion=(0.65, 0.75),
        recovery=(0.28, 0.38),
        # n=1,743 — pooled IQR [-3.05pp, +3.53pp]; TC d=0.15 (collapse), ELO d=0.57 (keep).
        # Tightest IQR of the 5 visible classes — multi-class spans average out.
        achievable_score_gap=(-0.03, 0.04),
    ),
    "pawnless": PerClassBands(
        conversion=(0.70, 0.80),
        recovery=(0.21, 0.31),
        # n=7 users at ≥20-span floor — defer per-class calibration. Pinned to the
        # global pooled band until a larger sample emerges.
        achievable_score_gap=(-0.04, 0.04),
    ),
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


def per_class_zone_spec(
    metric_id: Literal["conversion_win_pct", "recovery_save_pct"],
    endgame_class: EndgameClass,
) -> ZoneSpec:
    """Return the per-endgame-class ZoneSpec for Conv/Recov.

    PER_CLASS_GAUGE_ZONES holds class-specific typical bands sourced from
    pooled FlawChess benchmark data (reports/benchmarks-2026-05-01.md).
    Conversion is always higher_is_better; recovery is always
    higher_is_better. Both are 0.0-1.0 fractions.
    """
    bands = PER_CLASS_GAUGE_ZONES[endgame_class]
    lo, hi = bands.conversion if metric_id == "conversion_win_pct" else bands.recovery
    return ZoneSpec(lo, hi, "higher_is_better")


def assign_per_class_zone(
    metric_id: Literal["conversion_win_pct", "recovery_save_pct"],
    endgame_class: EndgameClass,
    value: float,
) -> Zone:
    """Assign a zone using per-endgame-class typical bands.

    Used by the per-type conversion_recovery_by_type findings so the
    [summary] zone label and the inline (typical LO to UP) bound both
    reflect the class-specific baseline rather than a one-size-fits-all
    bucket band. Returns `"typical"` for NaN (see `assign_zone`).
    """
    if math.isnan(value):
        return "typical"
    return _zone_from_spec(per_class_zone_spec(metric_id, endgame_class), value)


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
