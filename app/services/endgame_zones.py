"""Gauge zone registry: authoritative Python source of truth for endgame metric thresholds.

Python is the authoritative home for gauge thresholds. The
constants exported here drive `insights_service.compute_findings` zone
assignment and get code-generated to `frontend/src/generated/endgameZones.ts`
by `scripts/gen_endgame_zones_ts.py` so the frontend
gauges and the insights narrative agree by construction.

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.schemas.endgames import EndgameClass, MaterialBucket, TimeControlBucket

# ---------------------------------------------------------------------------
# Literal type aliases — the Pydantic schemas in app/schemas/insights.py
# re-import these so the wire format and the registry share one name set.
# ---------------------------------------------------------------------------

Zone = Literal["weak", "typical", "strong"]
Trend = Literal["improving", "declining", "stable", "n_a"]
SampleQuality = Literal["thin", "adequate", "rich"]
Window = Literal["all_time", "last_3mo"]

MetricId = Literal[
    "score_gap",
    "achievable_score_gap",  # Own band so §3.1.5 can tighten without affecting §3.1.6
    # Per-span, per-type version of achievable_score_gap.
    # User-facing label is "Endgame Type Score Gap" (concepts) / "Score Gap" (card row).
    # Internal name retains "achievable" to mark the math-family with achievable_score_gap.
    "endgame_type_achievable_score_gap",
    # Per-bucket Score Gap on Section 2 cards.
    # User-facing labels (card row): "Conversion Score Gap" / "Parity Score Gap" /
    # "Recovery Score Gap". Internal snake_case preserves grep-ability with the
    # achievable_score_gap family. Three scalar MetricIds (not a bucket-dispatched
    # parent) because dispatch here is eval-entry-bucket-keyed, not class-keyed like
    # PER_CLASS_GAUGE_ZONES. See BucketedMetricId note below.
    "score_gap_conv",
    "score_gap_parity",
    "score_gap_recov",
    "entry_eval_pawns",  # New endgame_start_vs_end Tile 1
    "entry_expected_score",  # New endgame_start_vs_end Tile 1 row 2 — achievable score
    "endgame_score",  # endgame_start_vs_end Tile 2 (distinct from endgame_score_timeline)
    # Scalar Non-Endgame Score ("Games without Endgame" card),
    # added to endgame_start_vs_end alongside endgame_score so the LLM reads
    # both cards' aggregates as the comparison pair. Same 0.45-0.55 vs-50% band
    # as endgame_score (the UI colors both cards identically).
    "non_endgame_score",
    # Per-part absolute score metrics emitted by the
    # score_timeline subsection. `score_gap` still carries the signed
    # aggregate; `endgame_score_timeline` / `non_endgame_score_timeline` carry
    # each side's absolute 0-100% score so the prompt narrates two absolute
    # lines instead of two part-tagged score_gap blocks whose labels
    # contradicted their series values. Neither has a calibrated zone band —
    # callers render them as "typical" (see assign_zone NaN/unregistered
    # handling). Distinct from the scalar "endgame_score" / "non_endgame_score"
    # metrics above.
    "endgame_score_timeline",  # score_timeline subsection
    "non_endgame_score_timeline",  # score_timeline subsection
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    # Endgame ELO gap: a logistic stretch around Actual ELO driven by the endgame /
    # non-endgame scores (endgame_service._endgame_elo_logistic).
    "endgame_elo_gap",
    "win_rate",
    # (my_clock - opp_clock) / base_clock at endgame entry; scalar zone
    # for the Clock Gap bullet on the time-pressure cards. No LLM narration:
    # insights_service.py uses a named allow-list, so adding this MetricId does
    # NOT auto-fire any LLM finding.
    "clock_gap_pct",
]

SubsectionId = Literal[
    # `overall` is not emitted by the findings assembly — its sole finding
    # (score_gap) lives in the dedicated `score_gap` subsection. The id stays a
    # valid SubsectionId (still constructable; used by schema tests).
    "overall",
    "endgame_start_vs_end",
    # Dedicated subsection mirroring the UI "Endgame Score
    # Differences" card — Eval Score Gap (achievable_score_gap) + Endgame Score
    # Gap (score_gap). Sits between endgame_start_vs_end and score_timeline.
    "score_gap",
    "score_timeline",
    # The aggregate-over-TC `endgame_metrics` subsection is not emitted; one
    # subsection per time control mirrors the UI's per-TC Endgame Metrics cards.
    # The id stays a valid
    # SubsectionId (still constructable; used by schema tests and the
    # SAMPLE_QUALITY_BANDS band shared by the per-TC subsections).
    "endgame_metrics",
    "endgame_metrics_bullet",
    "endgame_metrics_blitz",
    "endgame_metrics_rapid",
    "endgame_metrics_classical",
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    # The aggregate-over-TC `results_by_endgame_type` and
    # `conversion_recovery_by_type` subsections are not emitted; one
    # subsection per time control mirrors the UI's per-TC collapsible Endgame
    # Type breakdown (TypeTable). Each per-TC subsection carries a
    # WDL table (rendered from categories_by_tc) plus Conversion / Recovery /
    # Score-Gap [summary] blocks per endgame class. The two ids below stay valid
    # SubsectionIds (still constructable; used by schema tests and the
    # SAMPLE_QUALITY_BANDS band shared by the per-TC subsections).
    "results_by_endgame_type",
    "conversion_recovery_by_type",
    "endgame_type_bullet",
    "endgame_type_blitz",
    "endgame_type_rapid",
    "endgame_type_classical",
]

# `endgame_type_achievable_score_gap` is intentionally NOT
# added to BucketedMetricId — it is per-class only (via PER_CLASS_GAUGE_ZONES),
# not per-(class × material-axis). If benchmark §3.4.2 later requires per-rating-
# bucket bands, add it then in a follow-up.
# The 3 Section 2 per-bucket ΔES MetricIds (`score_gap_*`)
# are also NOT added here. They use 3 scalar MetricIds in ZONE_REGISTRY,
# not a bucket-dispatched parent. The existing bucket-dispatch shape is class-keyed
# (PER_CLASS_GAUGE_ZONES), not eval-entry-bucket-keyed, so a bucket-dispatched parent
# would need a new dispatch shape. The three buckets are conv/parity/recov.
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

# Minimum weekly data points in window to compute a trend.
TREND_MIN_WEEKLY_POINTS: int = 20

# Minimum slope-to-volatility ratio to emit a directional trend.
TREND_MIN_SLOPE_VOL_RATIO: float = 0.5

# Max |endgame_elo - actual_elo| that counts as not-notable.
NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD: int = 100

# Neutral band for clock-diff percentage of base time. Codegen'd to
# frontend/src/generated/endgameZones.ts (EndgameClockDiffOverTimeChart). Used by the
# `clock_entry_advantage` / `no_clock_entry_advantage` flags.
# Tightened to the pooled IQR from the 2026-05-01 benchmark (calibration v2).
NEUTRAL_PCT_THRESHOLD: float = 5.0

# Neutral band for net timeout rate in percentage points.
NEUTRAL_TIMEOUT_THRESHOLD: float = 5.0

# Minimum endgame games per TC before the insights prompt narrates
# that TC's type table or time-pressure curve.
# Codegen-emitted to frontend/src/generated/endgameZones.ts to
# eliminate cross-stack drift. Backend imports from here.
MIN_GAMES_PER_TC_CARD: int = 20

# Minimum games per (TC, quintile) bin for a reliable bullet.
# This is the floor for min(n_user_in_Q, n_opp_in_Q)
# before build_quintile_bullets emits delta + stats. Below it: stats are None.
MIN_GAMES_PER_PRESSURE_BIN: int = 5

# Editorial half-width cap for the per-(TC, quintile) Score-Delta
# neutral bands. Calibrated against benchmark §3.3.3 — cap
# confirmed at 0.06 (prevents extreme delta-IQR widths from creating unusably wide
# bands; applied independently to each edge: lower = max(p25 - p50, -0.06),
# upper = min(p75 - p50, +0.06); activated in 14 of 20 cells at one or both edges).
PRESSURE_BIN_NEUTRAL_CAP: float = 0.06


# ---------------------------------------------------------------------------
# ZONE_REGISTRY — scalar metrics (one band per metric).
# ---------------------------------------------------------------------------

ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] = {
    # Score Gap: signed 0.0-1.0 scale (endgame score minus non-endgame score).
    # Typical band = -0.10 to +0.10 (±10pp).
    "score_gap": ZoneSpec(
        typical_lower=-0.10,
        typical_upper=0.10,
        direction="higher_is_better",
    ),
    # Achievable Score Gap (Card 3 Achievable row, signed 0.0-1.0 scale).
    # Source: reports/benchmark/benchmarks-latest.md §3.1.5 — pooled benchmark IQR
    # [-3.9pp, +4.6pp] rounds cleanly to ±5pp. Split off from `score_gap`
    # because §3.1.6 (Endgame Score Gap) collapsed cleanly at
    # ±10pp while §3.1.5 needed a tighter band: the 2400-cohort median sits
    # at +3.5pp and would otherwise stay "typical blue" inside the old
    # shared ±10pp band. Per-ELO stratification deferred (d=0.62 keep-
    # separate verdict in the same §3.1.5).
    "achievable_score_gap": ZoneSpec(
        typical_lower=-0.05,
        typical_upper=0.05,
        direction="higher_is_better",
    ),
    # Per-span, per-type version. Calibrated (2026-05-15 benchmark)
    # from §3.4.2 (reports/benchmark/benchmarks-latest.md): pooled-across-classes
    # IQR (n=5,727 users, sparse cell excluded) = [-3.94pp, +4.34pp], rounded
    # to symmetric ±0.04. Per-class bands (PER_CLASS_GAUGE_ZONES below)
    # diverge by enough (width spread 6.6pp mixed -> 9.7pp minor_piece) to
    # warrant per-class overrides on top of this global default.
    "endgame_type_achievable_score_gap": ZoneSpec(
        typical_lower=-0.04,
        typical_upper=0.04,
        direction="higher_is_better",
    ),
    # Per-bucket bands for Section 2 ΔES Score Gap cards.
    # Calibrated from the 2026-05-15 benchmark — pooled
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
    # MiniBulletChart asymmetric rendering contract is locked in by tests.
    "score_gap_conv": ZoneSpec(
        typical_lower=-0.11,
        typical_upper=0.00,
        direction="higher_is_better",
    ),
    "score_gap_parity": ZoneSpec(
        typical_lower=-0.04,
        typical_upper=0.04,
        direction="higher_is_better",
    ),
    "score_gap_recov": ZoneSpec(
        typical_lower=0.01,
        typical_upper=0.11,
        direction="higher_is_better",
    ),
    # entry_eval_pawns: average Stockfish eval at endgame entry, signed from
    # user's perspective.
    "entry_eval_pawns": ZoneSpec(
        # Editorial tighten inside the IQR so the 0-centered EG-entry tile
        # actually paints; live was 0.75 but the tile painted neutral for
        # ~70% of users. Band ±0.60 pawns.
        # Unit: signed pawns.
        typical_lower=-0.60,
        typical_upper=0.60,
        direction="higher_is_better",
    ),
    # entry_expected_score: per-user mean expected score (Lichess winning-
    # chances sigmoid applied to entry-ply Stockfish eval) over endgame-
    # reaching games.
    "entry_expected_score": ZoneSpec(
        # Pooled benchmark IQR (excl. sparse cell): [0.4629, 0.5536]
        # (2026-05-11 benchmark). Single global band justified —
        # TC max d=0.218 (bullet vs rapid), ELO max d=0.224 (800 vs 2000),
        # both "review" (≥ 0.2, < 0.5). Per-ELO stratification deferred.
        # Band locked to [0.45, 0.55]: round numbers, very close to pooled IQR,
        # match existing endgame_score band for visual parity with the final-score
        # zone (band alignment with the neighbouring tile is preferred over a
        # symmetric +1pp drift).
        # Unit: 0–1 scale (NOT percent), centered at 0.5 chess-fairness null.
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    "endgame_score": ZoneSpec(
        # Reuse the live shared SCORE_BULLET_NEUTRAL band
        # (±0.05 around 0.5 → [0.45, 0.55]) for visual parity with the
        # Openings score bullet. Per-ELO ENDGAME_SCORE_ZONES deferred.
        # Unit: 0–1 scale (NOT percent).
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    # Scalar Non-Endgame Score ("Games without Endgame" card).
    # Same 0.45-0.55 vs-50% band as endgame_score — the UI colors both cards
    # with the identical SCORE_BULLET_NEUTRAL band, so the LLM's zone matches
    # what the user sees. Unit: 0-1 scale (NOT percent).
    "non_endgame_score": ZoneSpec(
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    # Absolute per-part rolling Score % used by the
    # score_timeline subsection's two-line chart. There is no calibrated
    # cohort band for "your endgame Score in isolation" (the zoned signal is
    # score_gap, not absolute score), so the typical band is defined to span
    # the full [0, 1] range — every value resolves to "typical". Keeping
    # entries here (rather than making assign_zone return "typical" for
    # unknown metrics) preserves the MetricId-Literal invariant and the
    # single-source-of-truth contract for all metrics referenced in
    # compute_findings.
    # score_timeline-only; no calibrated band. Distinct from the scalar
    # "endgame_score" / "non_endgame_score" metrics above.
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
    # Clock diff at endgame entry, % of base time, signed.
    # Typical band = ±NEUTRAL_PCT_THRESHOLD. Above = user has more time left
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
    # endgame_elo comes from the logistic stretch around Actual ELO
    # (endgame_service._endgame_elo_logistic).
    "endgame_elo_gap": ZoneSpec(
        typical_lower=-100.0,
        typical_upper=100.0,
        direction="higher_is_better",
    ),
    # Plain win rate (W / total, draws excluded) for per-type findings in the
    # results_by_endgame_type subsection. Band [0.45, 0.55] is the same
    # vs-50% band as endgame_score.
    "win_rate": ZoneSpec(
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    # Clock Gap percentage at endgame entry — (user_clock - opp_clock)
    # / base_clock. Positive = user has more time (good); negative = user has
    # less. Calibrated from reports/benchmark/benchmarks-latest.md §3.3.1 clock-gap-%
    # submetric (2026-05-17 snapshot, n=1,743 pooled users). TC d=0.23 and
    # ELO d=0.21 are both "review" — pooled IQR [-0.0641, +0.0466] rounded to
    # (-0.065, +0.047) is a defensible single band. Asymmetric because
    # blitz/rapid/classical users tend to enter endgames with a slight clock
    # deficit. clock_gap_pct is a ratio — its absolute IQR IS the delta IQR
    # (no p50 subtraction needed). No LLM finding is registered for this metric
    # (insights_service.py uses a named allow-list; time-pressure LLM narration
    # is not wired).
    "clock_gap_pct": ZoneSpec(
        typical_lower=-0.065,
        typical_upper=0.047,
        direction="higher_is_better",
    ),
}


# ---------------------------------------------------------------------------
# BUCKETED_ZONE_REGISTRY — per-MaterialBucket bands for Conv/Parity/Recov
# rate metrics. Each bucket shares the same band per metric (FE
# FIXED_GAUGE_ZONES pattern).
# ---------------------------------------------------------------------------

BUCKETED_ZONE_REGISTRY: Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]] = {
    # Upper bound 0.77: pooled p75 = 0.769 (2026-05-03 benchmark); 0.75 clipped
    # ~25% of users into the "above neutral" band.
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
        # [0.24, 0.36]: pooled p25/p75 = [0.243, 0.364] (2026-05-03 benchmark). An
        # upper bound of 0.40 sits well above population p75, so almost no users
        # ever read "above neutral" on the recovery gauge.
        "conversion": ZoneSpec(0.24, 0.36, "higher_is_better"),
        "parity": ZoneSpec(0.24, 0.36, "higher_is_better"),
        "recovery": ZoneSpec(0.24, 0.36, "higher_is_better"),
    },
}


# ---------------------------------------------------------------------------
# SAMPLE_QUALITY_BANDS — per-subsection (thin_max, adequate_max) bands.
# value < thin_max → thin; < adequate_max → adequate; otherwise → rich.
# Per-subsection denominators stay honest: type breakdown splits 5 ways, so
# its bands are ~5× smaller than overall.
# ---------------------------------------------------------------------------

SAMPLE_QUALITY_BANDS: Mapping[SubsectionId, tuple[int, int]] = {
    "overall": (50, 200),
    # Dedicated score_gap subsection uses the `overall` band —
    # score_gap's denominator is all games (endgame +
    # non_endgame), and achievable_score_gap's cohort (endgame games with eval)
    # is comparably large given >99% eval coverage.
    "score_gap": (50, 200),
    # Gates match time_pressure_at_entry
    # (thin < 10, adequate < 50, rich >= 50) — two single-aggregate tiles,
    # no per-type breakdown, so larger thin boundary than per-type subsections.
    "endgame_start_vs_end": (10, 50),
    "score_timeline": (10, 52),
    "endgame_metrics": (30, 100),
    # Per-TC Endgame Metrics subsections. Denominators are
    # per-(TC × bucket) — a single TC's conversion/parity/recovery span count —
    # so they sit in the same small-sample regime as the per-type subsections
    # (card-level gate is MIN_GAMES_PER_TC_CARD=20 total across the 3 buckets).
    # Use the per-type (20, 40) band rather than the aggregate (30, 100) so a
    # 20-game TC bucket is not mislabeled `thin`.
    "endgame_metrics_bullet": (20, 40),
    "endgame_metrics_blitz": (20, 40),
    "endgame_metrics_rapid": (20, 40),
    "endgame_metrics_classical": (20, 40),
    "endgame_elo_timeline": (10, 40),
    "time_pressure_at_entry": (10, 50),
    "clock_diff_timeline": (10, 52),
    "time_pressure_vs_performance": (30, 100),
    # thin_max is 20 for per-type subsections: 10-19 sequences labeled `adequate`
    # made the LLM treat those
    # last_3mo windows as load-bearing (e.g. n=14 conv → "strong" headlines).
    # 20 is the minimum across the per-type emitter calls in the benchmark
    # cohort (≥20 endgame games per user gate).
    "results_by_endgame_type": (20, 40),
    "conversion_recovery_by_type": (20, 40),
    # Per-TC Endgame Type subsections share the per-type (20, 40)
    # band — each class's Conv/Recov span count within a single TC is small, so
    # the same small-sample regime applies (TC-level gate is MIN_GAMES_PER_TC_CARD
    # summed across the 4 visible classes).
    "endgame_type_bullet": (20, 40),
    "endgame_type_blitz": (20, 40),
    "endgame_type_rapid": (20, 40),
    "endgame_type_classical": (20, 40),
}


# ---------------------------------------------------------------------------
# PER_CLASS_GAUGE_ZONES — per-endgame-class typical bands for Conversion and
# Recovery. Source: 2026-05-01 benchmark (calibration v2),
# pooled p25/p75 per class. Codegen'd to frontend via
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
    achievable_score_gap: tuple[float, float]


# 2026-05-03 benchmark shifts: rook recovery (0.28→0.26,
# 0.38→0.36) and pawn recovery (0.26→0.23, 0.36→0.34) — both pooled means sat
# below the previous lower bound. Pawn conversion upper bound nudged 0.77→0.79
# (pooled mean 0.738).
#
# achievable_score_gap calibrated (2026-05-15 benchmark) from
# reports/benchmark/benchmarks-latest.md §3.4.2 — pooled per-user mean span gap per
# class, sparse cell (2400, classical) excluded, equal-footing filter applied.
# Per-class [p25, p75] rounded to nearest 1pp. Pawnless deferred (n=7 users —
# floor not met) and pinned to the global pooled band as a defensible default.
PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook": PerClassBands(
        conversion=(0.65, 0.75),
        recovery=(0.26, 0.36),
        # n=1,309 — pooled IQR [-4.97pp, +4.27pp]; TC d=0.20, ELO d=0.32 (both review).
        achievable_score_gap=(-0.05, 0.05),
    ),
    "minor_piece": PerClassBands(
        conversion=(0.63, 0.73),
        # Pooled recovery is 32.7%.
        recovery=(0.28, 0.38),
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
        achievable_score_gap=(-0.04, 0.05),
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
# PER_CLASS_TC_GAUGE_ZONES — per-(class × TC) typical bands for Conv/Recov/ScoreGap.
# Source: reports/benchmark/benchmarks-latest.md §3.4.1 (TC marginal
# tables, p25/p75 per class per TC). Cohen's d per class ≈ 1.2–1.7 across TCs
# → all classes "keep separate" → per-(class × TC) bands are required.
#
# Added ALONGSIDE PER_CLASS_GAUGE_ZONES (not replacing it). PER_CLASS_GAUGE_ZONES
# stays as the pooled-class fallback for cells absent here (per_class_tc_zone_spec).
#
# pawnless is OMITTED: n far below floor for per-(class × TC) analysis; hidden
# in the collapsible tile UI (which shows rook/minor_piece/pawn/queen only).
#
# Score Gap (achievable_score_gap): TC d ≈ 0.07–0.18 (all collapse verdict).
# The four per-(class × TC) ΔES bands are near-identical per class by design
# (Score Gap forced per-TC for visual consistency — "redundancy is chosen").
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerClassTcBands:
    """Per-(class × TC) typical bands. Same shape as PerClassBands but TC-keyed."""

    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]


PER_CLASS_TC_GAUGE_ZONES: Mapping[
    EndgameClass,
    Mapping[Literal["bullet", "blitz", "rapid", "classical"], PerClassTcBands],
] = {
    "rook": {
        "bullet": PerClassTcBands(
            conversion=(0.56, 0.75), recovery=(0.27, 0.43), achievable_score_gap=(-0.05, 0.05)
        ),
        "blitz": PerClassTcBands(
            conversion=(0.67, 0.82), recovery=(0.20, 0.37), achievable_score_gap=(-0.05, 0.05)
        ),
        "rapid": PerClassTcBands(
            conversion=(0.69, 0.83), recovery=(0.17, 0.30), achievable_score_gap=(-0.05, 0.05)
        ),
        "classical": PerClassTcBands(
            conversion=(0.74, 0.87), recovery=(0.13, 0.25), achievable_score_gap=(-0.05, 0.05)
        ),
    },
    "minor_piece": {
        "bullet": PerClassTcBands(
            conversion=(0.51, 0.73), recovery=(0.29, 0.50), achievable_score_gap=(-0.04, 0.06)
        ),
        "blitz": PerClassTcBands(
            conversion=(0.64, 0.81), recovery=(0.21, 0.40), achievable_score_gap=(-0.04, 0.06)
        ),
        "rapid": PerClassTcBands(
            conversion=(0.68, 0.83), recovery=(0.15, 0.33), achievable_score_gap=(-0.04, 0.06)
        ),
        "classical": PerClassTcBands(
            conversion=(0.75, 0.89), recovery=(0.12, 0.28), achievable_score_gap=(-0.04, 0.06)
        ),
    },
    "pawn": {
        "bullet": PerClassTcBands(
            conversion=(0.57, 0.80), recovery=(0.25, 0.46), achievable_score_gap=(-0.04, 0.05)
        ),
        "blitz": PerClassTcBands(
            conversion=(0.68, 0.87), recovery=(0.17, 0.36), achievable_score_gap=(-0.04, 0.05)
        ),
        "rapid": PerClassTcBands(
            conversion=(0.75, 0.91), recovery=(0.10, 0.28), achievable_score_gap=(-0.04, 0.05)
        ),
        "classical": PerClassTcBands(
            conversion=(0.80, 0.92), recovery=(0.08, 0.21), achievable_score_gap=(-0.04, 0.05)
        ),
    },
    "queen": {
        "bullet": PerClassTcBands(
            conversion=(0.64, 0.83), recovery=(0.19, 0.36), achievable_score_gap=(-0.04, 0.05)
        ),
        "blitz": PerClassTcBands(
            conversion=(0.70, 0.90), recovery=(0.14, 0.31), achievable_score_gap=(-0.04, 0.05)
        ),
        "rapid": PerClassTcBands(
            conversion=(0.75, 0.92), recovery=(0.08, 0.25), achievable_score_gap=(-0.04, 0.05)
        ),
        # conversion=(0.88, 1.00) and recovery=(0.00, 0.09) are small-n benchmark
        # artifacts (n≈30–35 users). Accepted as-is per the "use benchmark numbers" rule.
        # The narrow recovery band will paint most users
        # as "typical" or "weak" in classical queen recovery, which is accurate for
        # this small classical cohort.
        "classical": PerClassTcBands(
            conversion=(0.88, 1.00), recovery=(0.00, 0.09), achievable_score_gap=(-0.04, 0.05)
        ),
    },
    "mixed": {
        "bullet": PerClassTcBands(
            conversion=(0.60, 0.72), recovery=(0.30, 0.40), achievable_score_gap=(-0.03, 0.04)
        ),
        "blitz": PerClassTcBands(
            conversion=(0.68, 0.76), recovery=(0.25, 0.35), achievable_score_gap=(-0.03, 0.04)
        ),
        "rapid": PerClassTcBands(
            conversion=(0.70, 0.79), recovery=(0.23, 0.31), achievable_score_gap=(-0.03, 0.04)
        ),
        "classical": PerClassTcBands(
            conversion=(0.70, 0.83), recovery=(0.18, 0.30), achievable_score_gap=(-0.03, 0.04)
        ),
    },
    # pawnless: OMITTED — n below per-class TC floor; hidden in live UI.
}


# ---------------------------------------------------------------------------
# PRESSURE_BIN_SCORE_NEUTRAL_ZONES — per-(TC, pressure-quintile) neutral bands.
# Calibrated from benchmark §3.3.3 (2026-05-17).
# ELO is pooled by acceptance (accept-pooled-with-caveat decision, 2026-05-17).
# ELO gradient inside the band is intentional: stronger players land higher
# (greener) because they score better against their opponents at every TC.
# Quintile index 0 = 0-20% clock remaining (max pressure); 4 = 80-100% (min).
#
# Semantics: band is on Score-Delta (user_score − cohort_score), NOT absolute
# score. Transformation: lower = max(p25 - p50, -cap), upper = min(p75 - p50,
# +cap) where cap = PRESSURE_BIN_NEUTRAL_CAP = 0.06. Both edges capped
# independently so bands are asymmetric in general.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PressureBinBand:
    """Neutral [lower, upper] band for Score-Delta in one (TC, quintile) cell."""

    lower: float
    upper: float


# Calibrated from reports/benchmark/benchmarks-latest.md §3.3.3 chess-score-per-pressure-bin
# (2026-05-17 benchmark snapshot, n=1,912 completed users across 19 non-sparse cells).
# Each band = delta IQR: lower = max(p25-p50, -0.06), upper = min(p75-p50, +0.06).
# "cap" in comments below means the edge hit ±PRESSURE_BIN_NEUTRAL_CAP=0.06.
PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[
    Literal["bullet", "blitz", "rapid", "classical"],
    Mapping[Literal[0, 1, 2, 3, 4], PressureBinBand],
] = {
    "bullet": {
        # p25/p50/p75: 0.2872/0.3495/0.4138 → delta IQR (-0.0623, +0.0643)
        0: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4645/0.5126/0.5650 → delta IQR (-0.0481, +0.0524)
        1: PressureBinBand(-0.0481, 0.0524),  # no cap
        # p25/p50/p75: 0.5198/0.5578/0.6071 → delta IQR (-0.0380, +0.0493)
        2: PressureBinBand(-0.0380, 0.0493),  # no cap
        # p25/p50/p75: 0.5066/0.5629/0.6230 → delta IQR (-0.0563, +0.0601)
        3: PressureBinBand(-0.0563, 0.06),  # upper edge capped
        # p25/p50/p75: 0.4414/0.5455/0.6538 → delta IQR (-0.1041, +0.1083)
        4: PressureBinBand(-0.06, 0.06),  # both edges capped
    },
    "blitz": {
        # p25/p50/p75: 0.3070/0.3889/0.4667 → delta IQR (-0.0819, +0.0778)
        0: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4554/0.5133/0.5784 → delta IQR (-0.0579, +0.0651)
        1: PressureBinBand(-0.0579, 0.06),  # upper edge capped
        # p25/p50/p75: 0.4930/0.5487/0.6017 → delta IQR (-0.0557, +0.0530)
        2: PressureBinBand(-0.0557, 0.0530),  # no cap
        # p25/p50/p75: 0.5000/0.5598/0.6146 → delta IQR (-0.0598, +0.0548)
        3: PressureBinBand(-0.0598, 0.0548),  # no cap
        # p25/p50/p75: 0.4615/0.5500/0.6250 → delta IQR (-0.0885, +0.0750)
        4: PressureBinBand(-0.06, 0.06),  # both edges capped
    },
    "rapid": {
        # p25/p50/p75: 0.3000/0.4000/0.5000 → delta IQR (-0.1000, +0.1000)
        0: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4340/0.5000/0.5753 → delta IQR (-0.0660, +0.0753)
        1: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4858/0.5421/0.6111 → delta IQR (-0.0563, +0.0690)
        2: PressureBinBand(-0.0563, 0.06),  # upper edge capped
        # p25/p50/p75: 0.4808/0.5390/0.6000 → delta IQR (-0.0582, +0.0610)
        3: PressureBinBand(-0.0582, 0.06),  # upper edge capped
        # p25/p50/p75: 0.4688/0.5370/0.6077 → delta IQR (-0.0682, +0.0707)
        4: PressureBinBand(-0.06, 0.06),  # both edges capped
    },
    "classical": {
        # p25/p50/p75: 0.3290/0.4183/0.5515 → delta IQR (-0.0893, +0.1332)
        0: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.3718/0.5000/0.5833 → delta IQR (-0.1282, +0.0833)
        1: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.3919/0.5000/0.5897 → delta IQR (-0.1081, +0.0897)
        2: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4198/0.5000/0.6124 → delta IQR (-0.0802, +0.1124)
        3: PressureBinBand(-0.06, 0.06),  # both edges capped
        # p25/p50/p75: 0.4205/0.5183/0.6094 → delta IQR (-0.0978, +0.0911)
        4: PressureBinBand(-0.06, 0.06),  # both edges capped
    },
}


# ---------------------------------------------------------------------------
# TC_METRIC_BANDS — per-TC typical bands for Conversion/Recovery/Parity rate and ΔES gap.
# Cohen's d ≈ 0.9 on the TC axis makes per-TC bands necessary for Conv/Recov.
# parity_rate is ALSO per-TC: the per-TC card shows
# each TC's actual §3.2.1 parity IQR rather than the editorial global band. NOTE:
# parity rate collapses on TC (d = 0.08 per §3.2.1), so the bullet/blitz/rapid
# bands are near-identical; only classical (n=579, noisier tails) widens visibly.
# The parity ΔES-gap neutral band stays global (ZONE_REGISTRY["score_gap_parity"]) — only
# the gauge rate band went per-TC.
#
# Source: reports/benchmark/benchmarks-latest.md §3.2.1 (rates p25/p75) and
#         §3.2.2 (ΔES gap p25/p75). Sparse cell (2400, classical) excluded.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TcMetricBands:
    """Per-TC typical [lower, upper] bands for Conv/Recov/Parity rate and DeltaES gap."""

    conv_rate: tuple[float, float]
    recov_rate: tuple[float, float]
    parity_rate: tuple[float, float]
    conv_score_gap: tuple[float, float]
    recov_score_gap: tuple[float, float]


TC_METRIC_BANDS: Mapping[Literal["bullet", "blitz", "rapid", "classical"], TcMetricBands] = {
    "bullet": TcMetricBands(
        conv_rate=(0.588, 0.719),
        recov_rate=(0.295, 0.412),
        parity_rate=(0.436, 0.572),
        conv_score_gap=(-0.195, -0.057),
        recov_score_gap=(0.074, 0.177),
    ),
    "blitz": TcMetricBands(
        conv_rate=(0.667, 0.769),
        recov_rate=(0.251, 0.357),
        parity_rate=(0.448, 0.569),
        conv_score_gap=(-0.085, 0.003),
        recov_score_gap=(0.011, 0.084),
    ),
    "rapid": TcMetricBands(
        conv_rate=(0.696, 0.800),
        recov_rate=(0.218, 0.333),
        parity_rate=(0.449, 0.575),
        conv_score_gap=(-0.063, 0.021),
        recov_score_gap=(-0.008, 0.062),
    ),
    "classical": TcMetricBands(
        conv_rate=(0.685, 0.833),
        recov_rate=(0.174, 0.316),
        parity_rate=(0.404, 0.591),
        conv_score_gap=(-0.053, 0.038),
        recov_score_gap=(-0.037, 0.035),
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
    SubsectionFinding, not via the zone value.
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


# The five metrics_elo metrics whose zone band is per-TC. The
# parity ΔES gap (`score_gap_parity`) is intentionally absent — its neutral
# band stays global (ZONE_REGISTRY["score_gap_parity"], see the TC_METRIC_BANDS note),
# so callers fall back to `assign_zone` / the scalar registry for it.
TcBandMetricId = Literal[
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "score_gap_conv",
    "score_gap_recov",
]


def tc_metric_zone_spec(metric_id: TcBandMetricId, tc: TimeControlBucket) -> ZoneSpec:
    """Return the per-TC ZoneSpec for a metrics_elo metric.

    Sources the band from TC_METRIC_BANDS so the LLM payload's `zone=` label and
    inline `(typical …)` bound match the UI's per-TC gauges for that same time
    control. All five bands are `higher_is_better` (the conv/recov ΔES gaps are
    negative-valued but a higher/less-negative gap is still the better side).
    `score_gap_parity` is NOT a TcBandMetricId — its neutral band is global.
    """
    bands = TC_METRIC_BANDS[tc]
    lo_hi: dict[TcBandMetricId, tuple[float, float]] = {
        "conversion_win_pct": bands.conv_rate,
        "parity_score_pct": bands.parity_rate,
        "recovery_save_pct": bands.recov_rate,
        "score_gap_conv": bands.conv_score_gap,
        "score_gap_recov": bands.recov_score_gap,
    }
    lo, hi = lo_hi[metric_id]
    return ZoneSpec(lo, hi, "higher_is_better")


def assign_tc_metric_zone(metric_id: TcBandMetricId, tc: TimeControlBucket, value: float) -> Zone:
    """Assign a zone for a per-TC metrics_elo metric using TC_METRIC_BANDS.

    Returns `"typical"` for NaN (see `assign_zone` docstring for rationale).
    """
    if math.isnan(value):
        return "typical"
    return _zone_from_spec(tc_metric_zone_spec(metric_id, tc), value)


def per_class_zone_spec(
    metric_id: Literal["conversion_win_pct", "recovery_save_pct"],
    endgame_class: EndgameClass,
) -> ZoneSpec:
    """Return the per-endgame-class ZoneSpec for Conv/Recov.

    PER_CLASS_GAUGE_ZONES holds class-specific typical bands sourced from
    pooled FlawChess benchmark data (2026-05-01 benchmark).
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


# Metrics carrying a per-(class × TC) band. Conversion / Recovery
# rate and the per-span Score Gap all dispatch via PER_CLASS_TC_GAUGE_ZONES so the
# per-TC Endgame Type subsections band against the same IQR the UI tile shows.
PerClassTcMetricId = Literal[
    "conversion_win_pct",
    "recovery_save_pct",
    "endgame_type_achievable_score_gap",
]


def per_class_tc_zone_spec(
    metric_id: PerClassTcMetricId,
    endgame_class: EndgameClass,
    tc: TimeControlBucket,
) -> ZoneSpec:
    """Return the per-(class × TC) ZoneSpec for Conv / Recov / Score Gap.

    Sources the band from PER_CLASS_TC_GAUGE_ZONES (§3.4.1 calibration)
    so the LLM payload's `zone=` label and inline `(typical …)` bound match the
    per-TC Endgame Type card tile for that (class, TC). All three bands are
    `higher_is_better` (the Score Gap is negative-valued but a higher / less
    negative gap is the better side). Falls back to the pooled-class band
    (PER_CLASS_GAUGE_ZONES) when the (class, TC) cell is absent — e.g. pawnless,
    which is omitted from PER_CLASS_TC_GAUGE_ZONES (and from the per-TC cards).
    """
    per_class = PER_CLASS_TC_GAUGE_ZONES.get(endgame_class)
    bands = per_class.get(tc) if per_class is not None else None
    if bands is None:
        # Defensive fallback: pawnless / missing cell → pooled-class band.
        pooled = PER_CLASS_GAUGE_ZONES[endgame_class]
        lo_hi = {
            "conversion_win_pct": pooled.conversion,
            "recovery_save_pct": pooled.recovery,
            "endgame_type_achievable_score_gap": pooled.achievable_score_gap,
        }[metric_id]
        return ZoneSpec(lo_hi[0], lo_hi[1], "higher_is_better")
    lo_hi = {
        "conversion_win_pct": bands.conversion,
        "recovery_save_pct": bands.recovery,
        "endgame_type_achievable_score_gap": bands.achievable_score_gap,
    }[metric_id]
    return ZoneSpec(lo_hi[0], lo_hi[1], "higher_is_better")


def assign_per_class_tc_zone(
    metric_id: PerClassTcMetricId,
    endgame_class: EndgameClass,
    tc: TimeControlBucket,
    value: float,
) -> Zone:
    """Assign a zone using per-(class × TC) typical bands.

    Used by the per-TC Endgame Type findings so the [summary] zone label and the
    inline (typical LO to UP) bound both reflect the (class, TC)-specific baseline
    that the UI tile gauges against. Returns `"typical"` for NaN (see `assign_zone`).
    """
    if math.isnan(value):
        return "typical"
    return _zone_from_spec(per_class_tc_zone_spec(metric_id, endgame_class, tc), value)


def sample_quality(subsection_id: SubsectionId, sample_size: int) -> SampleQuality:
    """Classify `sample_size` into thin/adequate/rich using per-subsection bands.

    Each subsection has its own `(thin_max, adequate_max)` pair
    so denominators stay honest (per-type bands are 5× smaller than overall).
    """
    thin_max, adequate_max = SAMPLE_QUALITY_BANDS[subsection_id]
    if sample_size < thin_max:
        return "thin"
    if sample_size < adequate_max:
        return "adequate"
    return "rich"
