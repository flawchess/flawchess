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
    # score_gap — inclusion floor ≥30 endgame AND ≥30 non-endgame games per user.
    "score_gap": CdfTable(
        breakpoints=(
            -0.3149,
            -0.2833,
            -0.2618,
            -0.2363,
            -0.2207,
            -0.2073,
            -0.1976,
            -0.1902,
            -0.1800,
            -0.1743,
            -0.1686,
            -0.1610,
            -0.1548,
            -0.1480,
            -0.1421,
            -0.1379,
            -0.1345,
            -0.1304,
            -0.1251,
            -0.1210,
            -0.1161,
            -0.1129,
            -0.1085,
            -0.1044,
            -0.1012,
            -0.0958,
            -0.0924,
            -0.0890,
            -0.0854,
            -0.0822,
            -0.0784,
            -0.0739,
            -0.0705,
            -0.0671,
            -0.0635,
            -0.0619,
            -0.0574,
            -0.0540,
            -0.0502,
            -0.0468,
            -0.0436,
            -0.0404,
            -0.0351,
            -0.0330,
            -0.0296,
            -0.0262,
            -0.0213,
            -0.0177,
            -0.0141,
            -0.0116,
            -0.0095,
            -0.0058,
            -0.0019,
            0.0009,
            0.0050,
            0.0073,
            0.0114,
            0.0139,
            0.0174,
            0.0198,
            0.0225,
            0.0260,
            0.0283,
            0.0319,
            0.0371,
            0.0411,
            0.0448,
            0.0488,
            0.0541,
            0.0586,
            0.0610,
            0.0646,
            0.0693,
            0.0735,
            0.0783,
            0.0823,
            0.0870,
            0.0905,
            0.0955,
            0.0984,
            0.1048,
            0.1085,
            0.1149,
            0.1206,
            0.1269,
            0.1330,
            0.1403,
            0.1461,
            0.1522,
            0.1595,
            0.1669,
            0.1744,
            0.1821,
            0.1962,
            0.2087,
            0.2232,
            0.2429,
            0.2571,
            0.2917,
        ),
        n_users=2003,
    ),
    # achievable_score_gap — inclusion floor ≥20 endgame-entry games per user.
    "achievable_score_gap": CdfTable(
        breakpoints=(
            -0.2182,
            -0.1877,
            -0.1566,
            -0.1430,
            -0.1325,
            -0.1230,
            -0.1150,
            -0.1093,
            -0.1002,
            -0.0927,
            -0.0883,
            -0.0834,
            -0.0791,
            -0.0753,
            -0.0709,
            -0.0681,
            -0.0639,
            -0.0603,
            -0.0566,
            -0.0530,
            -0.0506,
            -0.0482,
            -0.0448,
            -0.0427,
            -0.0399,
            -0.0376,
            -0.0355,
            -0.0338,
            -0.0318,
            -0.0296,
            -0.0282,
            -0.0255,
            -0.0240,
            -0.0214,
            -0.0195,
            -0.0179,
            -0.0160,
            -0.0145,
            -0.0130,
            -0.0111,
            -0.0095,
            -0.0078,
            -0.0065,
            -0.0048,
            -0.0030,
            -0.0009,
            0.0006,
            0.0027,
            0.0044,
            0.0060,
            0.0075,
            0.0089,
            0.0110,
            0.0130,
            0.0152,
            0.0172,
            0.0188,
            0.0203,
            0.0225,
            0.0243,
            0.0260,
            0.0272,
            0.0288,
            0.0310,
            0.0323,
            0.0338,
            0.0356,
            0.0376,
            0.0393,
            0.0411,
            0.0428,
            0.0444,
            0.0458,
            0.0478,
            0.0497,
            0.0520,
            0.0547,
            0.0571,
            0.0600,
            0.0618,
            0.0637,
            0.0669,
            0.0699,
            0.0729,
            0.0757,
            0.0784,
            0.0817,
            0.0874,
            0.0911,
            0.0961,
            0.1011,
            0.1079,
            0.1128,
            0.1221,
            0.1296,
            0.1387,
            0.1519,
            0.1754,
            0.2082,
        ),
        n_users=2299,
    ),
    # section2_score_gap_conv — inclusion floor ≥20 spans per entry-eval bucket.
    "section2_score_gap_conv": CdfTable(
        breakpoints=(
            -0.3461,
            -0.3107,
            -0.2897,
            -0.2687,
            -0.2484,
            -0.2383,
            -0.2238,
            -0.2146,
            -0.2033,
            -0.1923,
            -0.1836,
            -0.1781,
            -0.1717,
            -0.1643,
            -0.1591,
            -0.1505,
            -0.1448,
            -0.1388,
            -0.1352,
            -0.1308,
            -0.1268,
            -0.1230,
            -0.1206,
            -0.1169,
            -0.1131,
            -0.1090,
            -0.1056,
            -0.1020,
            -0.0991,
            -0.0953,
            -0.0916,
            -0.0889,
            -0.0860,
            -0.0826,
            -0.0795,
            -0.0771,
            -0.0752,
            -0.0729,
            -0.0709,
            -0.0682,
            -0.0664,
            -0.0647,
            -0.0624,
            -0.0610,
            -0.0597,
            -0.0577,
            -0.0560,
            -0.0538,
            -0.0520,
            -0.0500,
            -0.0477,
            -0.0454,
            -0.0432,
            -0.0417,
            -0.0399,
            -0.0380,
            -0.0367,
            -0.0346,
            -0.0330,
            -0.0306,
            -0.0283,
            -0.0261,
            -0.0240,
            -0.0216,
            -0.0200,
            -0.0183,
            -0.0167,
            -0.0138,
            -0.0119,
            -0.0093,
            -0.0071,
            -0.0051,
            -0.0031,
            -0.0011,
            0.0010,
            0.0043,
            0.0070,
            0.0092,
            0.0123,
            0.0148,
            0.0174,
            0.0195,
            0.0220,
            0.0243,
            0.0272,
            0.0298,
            0.0338,
            0.0356,
            0.0388,
            0.0432,
            0.0452,
            0.0503,
            0.0552,
            0.0598,
            0.0682,
            0.0757,
            0.0816,
            0.0919,
            0.1053,
        ),
        n_users=2060,
    ),
    # section2_score_gap_parity — inclusion floor ≥20 spans per entry-eval bucket.
    "section2_score_gap_parity": CdfTable(
        breakpoints=(
            -0.1697,
            -0.1465,
            -0.1301,
            -0.1159,
            -0.1062,
            -0.0987,
            -0.0936,
            -0.0886,
            -0.0846,
            -0.0811,
            -0.0767,
            -0.0730,
            -0.0681,
            -0.0646,
            -0.0617,
            -0.0591,
            -0.0564,
            -0.0533,
            -0.0496,
            -0.0464,
            -0.0441,
            -0.0418,
            -0.0402,
            -0.0381,
            -0.0364,
            -0.0347,
            -0.0327,
            -0.0308,
            -0.0287,
            -0.0270,
            -0.0247,
            -0.0223,
            -0.0210,
            -0.0192,
            -0.0174,
            -0.0160,
            -0.0142,
            -0.0132,
            -0.0119,
            -0.0102,
            -0.0085,
            -0.0068,
            -0.0056,
            -0.0043,
            -0.0036,
            -0.0024,
            -0.0007,
            0.0006,
            0.0021,
            0.0035,
            0.0049,
            0.0066,
            0.0076,
            0.0091,
            0.0102,
            0.0114,
            0.0131,
            0.0144,
            0.0155,
            0.0172,
            0.0185,
            0.0198,
            0.0211,
            0.0225,
            0.0238,
            0.0254,
            0.0268,
            0.0286,
            0.0296,
            0.0310,
            0.0330,
            0.0350,
            0.0366,
            0.0382,
            0.0405,
            0.0426,
            0.0451,
            0.0474,
            0.0489,
            0.0510,
            0.0525,
            0.0551,
            0.0575,
            0.0598,
            0.0625,
            0.0643,
            0.0668,
            0.0701,
            0.0732,
            0.0753,
            0.0803,
            0.0832,
            0.0865,
            0.0917,
            0.1006,
            0.1103,
            0.1217,
            0.1404,
            0.1665,
        ),
        n_users=1804,
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
