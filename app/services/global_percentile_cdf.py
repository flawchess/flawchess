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
        breakpoints=_PLACEHOLDER_BREAKPOINTS,
        n_users=_PLACEHOLDER_N_USERS,
    ),
    # achievable_score_gap — inclusion floor ≥20 endgame-entry games per user.
    "achievable_score_gap": CdfTable(
        breakpoints=_PLACEHOLDER_BREAKPOINTS,
        n_users=_PLACEHOLDER_N_USERS,
    ),
    # section2_score_gap_conv — inclusion floor ≥20 spans per entry-eval bucket.
    "section2_score_gap_conv": CdfTable(
        breakpoints=_PLACEHOLDER_BREAKPOINTS,
        n_users=_PLACEHOLDER_N_USERS,
    ),
    # section2_score_gap_parity — inclusion floor ≥20 spans per entry-eval bucket.
    "section2_score_gap_parity": CdfTable(
        breakpoints=_PLACEHOLDER_BREAKPOINTS,
        n_users=_PLACEHOLDER_N_USERS,
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
