"""Global empirical-CDF artifact: authoritative Python source of the pooled
percentile breakpoints for Phase 93's 4 chip-eligible ΔES metrics.

Methodology source-of-truth: `.claude/skills/benchmarks/SKILL.md` Chapter 4.
Regenerate via `scripts/gen_global_percentile_cdf.py --db benchmark` against
the benchmark Docker DB on port 5433. No CI gate; manual recalibration step
(mirrors `scripts/backfill_eval.py --db benchmark`).

This module is a sibling of `app/services/endgame_zones.py` (D-04), NOT a
graft into it: CDF tables (99 percentile breakpoints per metric, pooled
across the canonical CTE) have a different shape than ZoneSpec (IQR bands
per (TC, ELO) cell).

D-01 — Python-only artifact. No TS mirror, no edits to
`scripts/gen_endgame_zones_ts.py` or `frontend/src/generated/endgameZones.ts`.
Phase 94 backend imports `GLOBAL_PERCENTILE_CDF` + `interpolate_percentile`,
computes a scalar percentile per request, and emits a nullable
`{metric}_percentile` field; the chip renders from that scalar.

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free, matching the purity invariant of `endgame_zones.py`.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

from app.services.endgame_zones import MetricId

# ---------------------------------------------------------------------------
# Audit-trail and breakpoint constants.
# ---------------------------------------------------------------------------

# Locked benchmark snapshot month (D-04 "Claude's Discretion" item #4). Carried
# on every CdfTable for future-recalibration auditability — if the breakpoint
# values look anomalous, the snapshot tag tells you which benchmark DB month
# they came from.
BENCHMARK_DB_SNAPSHOT_MONTH: Final[str] = "2026-03"

# Every integer percentile from p1 through p99 (99 breakpoints total). NO
# sub-percent steps (no p0.5 / p2.5 / p97.5 / p99.5) — chip phrasing operates
# on whole-percent precision per ROADMAP success criterion #5. Tail-bounded at
# p1/p99 because the n≈2000 cohort gives ~5pp sampling SE at the deep tails;
# extending to p0.1/p99.9 would swing on single outliers.
BREAKPOINT_LABELS: Final[tuple[str, ...]] = tuple(f"p{i}" for i in range(1, 100))

# Parallel tuple of float percentiles. Position i corresponds to
# BREAKPOINT_LABELS[i] and to cdf.breakpoints[i] in every CdfTable; stored as a
# constant so `_interpolate_with_table` does not re-parse labels per call.
BREAKPOINT_PERCENTILES: Final[tuple[float, ...]] = tuple(float(i) for i in range(1, 100))

# Edge clamp values. Anything <= breakpoints[0] (the p1 value) is rendered as
# the 0th percentile; anything >= breakpoints[-1] (p99) is rendered as the
# 100th percentile. We do not extrapolate beyond the resolved range — the
# tails of the cohort are too thin to assign meaningful percentiles below p1
# or above p99.
_LEFT_TAIL_CLAMP: Final[float] = 0.0
_RIGHT_TAIL_CLAMP: Final[float] = 100.0

# Narrower Literal alias over the in-scope Phase 93 subset (D-02). The
# registry uses this as the key type so the 4-metric scope is grep-able and
# type-checkable. `interpolate_percentile` accepts the broader `MetricId`
# (caller convenience: Phase 94 iterates over all metrics on the response)
# and returns None when the key is not in `GLOBAL_PERCENTILE_CDF`.
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
]


# ---------------------------------------------------------------------------
# CdfTable — per-metric breakpoint table + audit-trail fields.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CdfTable:
    """99-breakpoint empirical CDF for one metric, pooled across the canonical CTE.

    `breakpoints[i]` corresponds to `BREAKPOINT_LABELS[i]` /
    `BREAKPOINT_PERCENTILES[i]`. Units are 0-1 score-gap units (matches the
    internal SQL output unit — see SKILL.md §1 "Display formatting"). The
    tuple is monotone non-decreasing by construction (it is the empirical CDF
    of the cohort); this invariant is enforced by the regeneration script and
    asserted in unit tests.
    """

    breakpoints: tuple[float, ...]
    n_users: int
    snapshot_month: str = field(default=BENCHMARK_DB_SNAPSHOT_MONTH)


# ---------------------------------------------------------------------------
# GLOBAL_PERCENTILE_CDF — placeholder registry (overwritten by the script).
#
# Initial values satisfy the monotone-non-decreasing invariant via a linear
# ramp from -0.49 to +0.49 in 0.01 steps (99 values). These MUST be replaced
# by running `scripts/gen_global_percentile_cdf.py --db benchmark` against
# the live benchmark DB — Task 3 of Plan 93-02.
#
# Inclusion floors per metric (D-04 "Claude's Discretion" item #2):
#   - score_gap                  : ≥30 endgame games AND ≥30 non-endgame games
#   - achievable_score_gap       : ≥20 endgame-entry games
#   - section2_score_gap_conv    : ≥20 entry-eval-bucket spans / bucket
#   - section2_score_gap_parity  : ≥20 entry-eval-bucket spans / bucket
# Each entry's n_users is the count of users that cleared the floor at the
# snapshot month, post sparse-cell-(2400, classical) exclusion.
# ---------------------------------------------------------------------------

_PLACEHOLDER_BREAKPOINTS: Final[tuple[float, ...]] = tuple(
    round(-0.49 + i * 0.01, 4) for i in range(99)
)
_PLACEHOLDER_N_USERS: Final[int] = 1

# --- BEGIN GENERATED REGISTRY ---
GLOBAL_PERCENTILE_CDF: Mapping[CdfMetricId, CdfTable] = {
    # score_gap — inclusion floor ≥30 endgame AND ≥30 non-endgame games per user (pooled).
    "score_gap": CdfTable(
        breakpoints=(
            -0.3030,
            -0.2725,
            -0.2503,
            -0.2362,
            -0.2218,
            -0.2075,
            -0.1963,
            -0.1896,
            -0.1775,
            -0.1706,
            -0.1649,
            -0.1586,
            -0.1506,
            -0.1450,
            -0.1408,
            -0.1361,
            -0.1330,
            -0.1290,
            -0.1236,
            -0.1197,
            -0.1165,
            -0.1129,
            -0.1093,
            -0.1054,
            -0.1029,
            -0.0966,
            -0.0918,
            -0.0886,
            -0.0848,
            -0.0811,
            -0.0786,
            -0.0754,
            -0.0721,
            -0.0680,
            -0.0644,
            -0.0624,
            -0.0575,
            -0.0550,
            -0.0512,
            -0.0460,
            -0.0434,
            -0.0403,
            -0.0362,
            -0.0339,
            -0.0305,
            -0.0284,
            -0.0237,
            -0.0191,
            -0.0147,
            -0.0129,
            -0.0095,
            -0.0063,
            -0.0015,
            0.0014,
            0.0040,
            0.0073,
            0.0104,
            0.0132,
            0.0165,
            0.0199,
            0.0234,
            0.0263,
            0.0288,
            0.0322,
            0.0352,
            0.0396,
            0.0452,
            0.0479,
            0.0520,
            0.0555,
            0.0589,
            0.0618,
            0.0673,
            0.0699,
            0.0742,
            0.0788,
            0.0829,
            0.0873,
            0.0950,
            0.0981,
            0.1030,
            0.1070,
            0.1132,
            0.1190,
            0.1245,
            0.1301,
            0.1364,
            0.1437,
            0.1509,
            0.1586,
            0.1659,
            0.1712,
            0.1824,
            0.1934,
            0.2046,
            0.2203,
            0.2296,
            0.2528,
            0.2786,
        ),
        n_users=1726,
    ),
    # achievable_score_gap — inclusion floor ≥30 endgame-entry games per user (pooled).
    "achievable_score_gap": CdfTable(
        breakpoints=(
            -0.2132,
            -0.1790,
            -0.1509,
            -0.1312,
            -0.1220,
            -0.1093,
            -0.1015,
            -0.0938,
            -0.0888,
            -0.0844,
            -0.0804,
            -0.0764,
            -0.0721,
            -0.0672,
            -0.0636,
            -0.0592,
            -0.0563,
            -0.0526,
            -0.0502,
            -0.0479,
            -0.0462,
            -0.0435,
            -0.0415,
            -0.0396,
            -0.0370,
            -0.0351,
            -0.0330,
            -0.0314,
            -0.0294,
            -0.0278,
            -0.0258,
            -0.0238,
            -0.0218,
            -0.0198,
            -0.0181,
            -0.0162,
            -0.0148,
            -0.0131,
            -0.0113,
            -0.0097,
            -0.0079,
            -0.0069,
            -0.0053,
            -0.0036,
            -0.0021,
            -0.0007,
            0.0010,
            0.0029,
            0.0052,
            0.0060,
            0.0075,
            0.0091,
            0.0107,
            0.0126,
            0.0142,
            0.0155,
            0.0175,
            0.0185,
            0.0204,
            0.0220,
            0.0235,
            0.0254,
            0.0271,
            0.0283,
            0.0300,
            0.0313,
            0.0328,
            0.0340,
            0.0358,
            0.0376,
            0.0393,
            0.0416,
            0.0435,
            0.0446,
            0.0461,
            0.0479,
            0.0502,
            0.0528,
            0.0545,
            0.0572,
            0.0593,
            0.0618,
            0.0639,
            0.0686,
            0.0715,
            0.0744,
            0.0771,
            0.0801,
            0.0854,
            0.0892,
            0.0921,
            0.0966,
            0.1011,
            0.1063,
            0.1133,
            0.1202,
            0.1341,
            0.1486,
            0.1885,
        ),
        n_users=1786,
    ),
    # section2_score_gap_conv — inclusion floor ≥30 spans in Up-entry-eval bucket (pooled).
    "section2_score_gap_conv": CdfTable(
        breakpoints=(
            -0.3414,
            -0.3021,
            -0.2756,
            -0.2565,
            -0.2361,
            -0.2232,
            -0.2154,
            -0.2013,
            -0.1885,
            -0.1807,
            -0.1725,
            -0.1633,
            -0.1573,
            -0.1489,
            -0.1441,
            -0.1389,
            -0.1354,
            -0.1296,
            -0.1261,
            -0.1230,
            -0.1209,
            -0.1172,
            -0.1117,
            -0.1076,
            -0.1057,
            -0.1041,
            -0.0999,
            -0.0970,
            -0.0938,
            -0.0902,
            -0.0887,
            -0.0858,
            -0.0837,
            -0.0812,
            -0.0782,
            -0.0761,
            -0.0741,
            -0.0723,
            -0.0691,
            -0.0669,
            -0.0653,
            -0.0634,
            -0.0613,
            -0.0597,
            -0.0575,
            -0.0554,
            -0.0532,
            -0.0515,
            -0.0489,
            -0.0470,
            -0.0451,
            -0.0435,
            -0.0419,
            -0.0398,
            -0.0383,
            -0.0369,
            -0.0352,
            -0.0331,
            -0.0307,
            -0.0288,
            -0.0270,
            -0.0249,
            -0.0230,
            -0.0211,
            -0.0193,
            -0.0177,
            -0.0158,
            -0.0137,
            -0.0116,
            -0.0088,
            -0.0073,
            -0.0059,
            -0.0028,
            -0.0009,
            0.0013,
            0.0034,
            0.0052,
            0.0068,
            0.0089,
            0.0123,
            0.0148,
            0.0175,
            0.0204,
            0.0232,
            0.0251,
            0.0279,
            0.0301,
            0.0325,
            0.0377,
            0.0409,
            0.0442,
            0.0483,
            0.0527,
            0.0556,
            0.0598,
            0.0683,
            0.0765,
            0.0866,
            0.1005,
        ),
        n_users=1642,
    ),
    # section2_score_gap_parity — inclusion floor ≥30 spans in Equal-entry-eval bucket (pooled).
    "section2_score_gap_parity": CdfTable(
        breakpoints=(
            -0.1518,
            -0.1317,
            -0.1129,
            -0.0988,
            -0.0902,
            -0.0867,
            -0.0831,
            -0.0790,
            -0.0744,
            -0.0699,
            -0.0655,
            -0.0615,
            -0.0589,
            -0.0571,
            -0.0550,
            -0.0518,
            -0.0497,
            -0.0474,
            -0.0451,
            -0.0424,
            -0.0404,
            -0.0386,
            -0.0368,
            -0.0350,
            -0.0335,
            -0.0317,
            -0.0301,
            -0.0274,
            -0.0253,
            -0.0236,
            -0.0223,
            -0.0208,
            -0.0194,
            -0.0178,
            -0.0167,
            -0.0152,
            -0.0137,
            -0.0128,
            -0.0114,
            -0.0100,
            -0.0086,
            -0.0076,
            -0.0062,
            -0.0046,
            -0.0034,
            -0.0019,
            -0.0003,
            0.0007,
            0.0023,
            0.0033,
            0.0046,
            0.0055,
            0.0068,
            0.0075,
            0.0088,
            0.0100,
            0.0112,
            0.0127,
            0.0141,
            0.0155,
            0.0171,
            0.0187,
            0.0197,
            0.0204,
            0.0221,
            0.0233,
            0.0254,
            0.0263,
            0.0275,
            0.0283,
            0.0299,
            0.0316,
            0.0332,
            0.0345,
            0.0363,
            0.0377,
            0.0394,
            0.0413,
            0.0426,
            0.0440,
            0.0459,
            0.0477,
            0.0497,
            0.0518,
            0.0535,
            0.0556,
            0.0582,
            0.0610,
            0.0631,
            0.0660,
            0.0685,
            0.0730,
            0.0762,
            0.0805,
            0.0879,
            0.0944,
            0.1022,
            0.1135,
            0.1383,
        ),
        n_users=1419,
    ),
}
# --- END GENERATED REGISTRY ---


# ---------------------------------------------------------------------------
# Public helper — interpolate_percentile.
# ---------------------------------------------------------------------------


def _interpolate_with_table(table: CdfTable, value: float) -> float | None:
    """Linear-interpolate `value` against `table.breakpoints`; return percentile or None.

    Returns None when `value` is NaN. Clamps to `_LEFT_TAIL_CLAMP` / `_RIGHT_TAIL_CLAMP`
    at the resolved tails. Linear interpolation between adjacent breakpoints
    elsewhere. Degenerate intervals (`bp[i] == bp[i-1]`, all values pinned at
    the same number) return the lower percentile.

    Exposed (with leading underscore) so the unit tests can construct synthetic
    tables and exercise the interpolation math without depending on the
    registry's placeholder / real values.
    """
    if math.isnan(value):
        return None

    bps = table.breakpoints
    if value <= bps[0]:
        return _LEFT_TAIL_CLAMP
    if value >= bps[-1]:
        return _RIGHT_TAIL_CLAMP

    # `bisect_left` returns the first index `i` such that bps[i] >= value;
    # since we already handled both edges, 1 <= i <= len(bps) - 1.
    i = bisect.bisect_left(bps, value)
    lo_value = bps[i - 1]
    hi_value = bps[i]
    lo_pct = BREAKPOINT_PERCENTILES[i - 1]
    hi_pct = BREAKPOINT_PERCENTILES[i]

    if hi_value == lo_value:
        # Degenerate interval (cohort has many users with identical metric
        # values, e.g. all pinned at 0.0). Return the lower percentile rather
        # than divide-by-zero — the user effectively sits at the bottom of
        # the pinned plateau.
        return lo_pct

    frac = (value - lo_value) / (hi_value - lo_value)
    return lo_pct + frac * (hi_pct - lo_pct)


def interpolate_percentile(metric_id: MetricId, value: float) -> float | None:
    """Linear-interpolate `value` against the metric's CDF; return percentile in [0, 100] or None.

    Phase 94 hand-off shape — backend imports this helper and emits the result
    as a nullable `{metric}_percentile` field on the endgame API response.

    Returns None when:
      - `metric_id` is not in GLOBAL_PERCENTILE_CDF (metric is not chip-eligible
        under D-02 — e.g. Recovery, raw % gauges, anything outside the 4 in-scope
        ΔES metrics).
      - `value` is NaN.

    Clamps:
      - value <= breakpoints[0]  (p1)  -> 0.0   (left tail beyond resolved range)
      - value >= breakpoints[-1] (p99) -> 100.0 (right tail beyond resolved range)
    """
    table = GLOBAL_PERCENTILE_CDF.get(metric_id)  # ty: ignore[invalid-argument-type]  # MetricId is wider than CdfMetricId by design
    if table is None:
        return None
    return _interpolate_with_table(table, value)
