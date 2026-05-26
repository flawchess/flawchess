"""Cohort empirical-CDF artifact: per-(metric, anchor, TC) percentile breakpoints.

Phase 94.4 — peer-relative percentile chip (CONTEXT D-09 / D-09a / D-13)
-----------------------------------------------------------------------

This module retires the Phase 94.3 flat ``GLOBAL_PERCENTILE_CDF`` registry
(16-key, pooled across all anchors) and replaces it with
``COHORT_PERCENTILE_CDF`` — an 8-metric × ~33-anchor × 4-TC nested registry
(≤ 1,056 cells; suppressed cells absent by construction). The chip is now
peer-relative: every user's percentile is read against a sliding-window
cohort of K=200 nearest-anchor users in the user's own TC.

Key reshape vs Phase 94.3:

- **CdfMetricId collapses 16 → 8** (CONTEXT D-13). The 12 Phase 94.3
  TC-suffixed entries (``time_pressure_score_gap_{bullet,blitz,rapid,classical}``,
  ``clock_gap_*``, ``net_flag_rate_*``) retire entirely — TC is now an outer
  key, not a metric suffix. ``recovery_score_gap`` is added as a peer to
  ``section2_score_gap_{conv,parity}``.
- **Registry shape** widens: ``Mapping[CdfMetricId, Mapping[tuple[int, TimeControlBucket], CdfTable]]``
  keyed by ``(anchor_elo, time_control_bucket)`` per metric (CONTEXT D-09 /
  RESEARCH Pattern 1).
- **Helper renames**: ``interpolate_percentile(metric, value)`` →
  ``interpolate_cohort_percentile(metric, value, anchor, tc) -> float | None``
  (CONTEXT D-09a). The new helper rounds ``anchor`` to the nearest 50-Elo
  grid step and returns ``None`` when no CDF exists at the resolved
  ``(metric, anchor, tc)`` cell — that yields a suppressed chip in the
  rendering layer.

Regenerate via ``scripts/gen_global_percentile_cdf.py --target benchmark``
against the benchmark Docker DB on port 5433. The script performs in-Python
ranking over a single per-(metric, TC) query (32 queries total) — see
RESEARCH Pitfall 8 for the cost rationale.

This module is a sibling of ``app/services/endgame_zones.py`` (D-04), NOT a
graft into it: CDF tables (99 percentile breakpoints per cell, sliding-window
cohort) have a different shape than ZoneSpec (IQR bands per (TC, ELO) cell).

D-01 — Python-only artifact. No TS mirror.

The module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free, matching the purity invariant of ``endgame_zones.py``.
"""

from __future__ import annotations

import bisect
import math
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

from app.services.endgame_zones import MetricId

# ``TimeControlBucket`` is duplicated inline here (rather than imported from
# ``app.services.canonical_slice_sql``) to break a circular import:
# ``canonical_slice_sql`` imports ``CdfMetricId`` from this module. The 4-value
# Literal is stable across the codebase — see ``canonical_slice_sql.py``.
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]

# ---------------------------------------------------------------------------
# Audit-trail and breakpoint constants.
# ---------------------------------------------------------------------------

# Locked benchmark snapshot month (D-04 "Claude's Discretion" item #4). Carried
# on every CdfTable for future-recalibration auditability — if the breakpoint
# values look anomalous, the snapshot tag tells you which benchmark DB month
# they came from.
BENCHMARK_DB_SNAPSHOT_MONTH: Final[str] = "2026-05"

# Anchor grid step (CONTEXT D-11). Must match
# ``COHORT_ANCHOR_STEP_ELO`` in ``scripts/gen_global_percentile_cdf.py`` —
# duplicated here so ``interpolate_cohort_percentile`` can round inputs
# without depending on the script module. Keep these in sync.
COHORT_ANCHOR_STEP_ELO: Final[int] = 50

# Every integer percentile from p1 through p99 (99 breakpoints total). NO
# sub-percent steps (no p0.5 / p2.5 / p97.5 / p99.5) — chip phrasing operates
# on whole-percent precision per ROADMAP success criterion #5.
BREAKPOINT_LABELS: Final[tuple[str, ...]] = tuple(f"p{i}" for i in range(1, 100))

# Parallel tuple of float percentiles. Position i corresponds to
# BREAKPOINT_LABELS[i] and to cdf.breakpoints[i] in every CdfTable.
BREAKPOINT_PERCENTILES: Final[tuple[float, ...]] = tuple(float(i) for i in range(1, 100))

# Edge clamp values. Anything <= breakpoints[0] (the p1 value) is rendered as
# the 0th percentile; anything >= breakpoints[-1] (p99) is rendered as the
# 100th percentile. We do not extrapolate beyond the resolved range — the
# tails of the cohort are too thin to assign meaningful percentiles below p1
# or above p99.
_LEFT_TAIL_CLAMP: Final[float] = 0.0
_RIGHT_TAIL_CLAMP: Final[float] = 100.0

# Phase 94.4 CdfMetricId — collapsed from 16 to 8 (CONTEXT D-13). The 12
# Phase 94.3 TC-suffixed entries retire; ``recovery_score_gap`` joins as a
# peer to the section2 family. TC is an outer key on the registry (not a
# suffix on the metric name), so each metric has at most 4 cells per anchor.
#
# This Literal is the single source of truth — ``scripts/gen_global_percentile_cdf.py``
# re-exports it (drift-impossibility per RESEARCH §Pattern 3).
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
]


# ---------------------------------------------------------------------------
# CdfTable — per-cell breakpoint table + audit-trail fields.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CdfTable:
    """99-breakpoint empirical CDF for one (metric, anchor, TC) cell.

    ``breakpoints[i]`` corresponds to ``BREAKPOINT_LABELS[i]`` /
    ``BREAKPOINT_PERCENTILES[i]``. Units are 0-1 score-gap units (matches the
    internal SQL output unit — see SKILL.md §1 "Display formatting"). The
    tuple is monotone non-decreasing by construction; this invariant is
    enforced by the regeneration script.
    """

    breakpoints: tuple[float, ...]
    n_users: int
    snapshot_month: str = field(default=BENCHMARK_DB_SNAPSHOT_MONTH)


# ---------------------------------------------------------------------------
# COHORT_PERCENTILE_CDF — placeholder registry (overwritten by the script).
#
# The script ``scripts/gen_global_percentile_cdf.py --target benchmark``
# populates this dict between the BEGIN/END sentinels by running 32 per-
# (metric, TC) queries against the benchmark DB, then ranking results in
# Python across 33 anchors per (metric, TC) — see the regen script for the
# K=200 sliding-window policy (CONTEXT D-11).
# ---------------------------------------------------------------------------

# --- BEGIN GENERATED REGISTRY ---
COHORT_PERCENTILE_CDF: Mapping[CdfMetricId, Mapping[tuple[int, TimeControlBucket], CdfTable]] = {}
# --- END GENERATED REGISTRY ---


# ---------------------------------------------------------------------------
# Public helper — interpolate_cohort_percentile.
# ---------------------------------------------------------------------------


def _interpolate_with_table(table: CdfTable, value: float) -> float | None:
    """Linear-interpolate ``value`` against ``table.breakpoints``; return percentile or None.

    Returns None when ``value`` is NaN. Clamps to ``_LEFT_TAIL_CLAMP`` /
    ``_RIGHT_TAIL_CLAMP`` at the resolved tails. Linear interpolation between
    adjacent breakpoints elsewhere. Degenerate intervals (``bp[i] == bp[i-1]``,
    all values pinned at the same number) return the lower percentile.

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

    # ``bisect_left`` returns the first index ``i`` such that bps[i] >= value;
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


def _round_anchor_to_grid(anchor: int) -> int:
    """Round ``anchor`` to the nearest ``COHORT_ANCHOR_STEP_ELO`` (50-Elo grid step).

    Tie-breaking uses banker's-rounding-equivalent ``round(x / step) * step``
    so the rounded value is deterministic for downstream lookups.
    """
    return int(round(anchor / COHORT_ANCHOR_STEP_ELO) * COHORT_ANCHOR_STEP_ELO)


def interpolate_cohort_percentile(
    metric: CdfMetricId,
    value: float,
    anchor: int,
    tc: TimeControlBucket,
) -> float | None:
    """Linear-interpolate ``value`` against the cohort CDF at ``(metric, anchor, tc)``.

    CONTEXT D-09a. Phase 94.4 chip lookup shape — replaces
    ``interpolate_percentile(metric, value)`` from Phase 94.3.

    Anchor handling: ``anchor`` is rounded to the nearest 50-Elo grid step
    (``COHORT_ANCHOR_STEP_ELO``). The cohort CDF is populated on a 50-Elo
    grid from 800 to 2400 (CONTEXT D-11), so input anchors are snapped to
    that grid before lookup. Off-grid input is tolerated; sub-800 or
    super-2400 anchors round into the registry range but typically resolve
    to a suppressed cell.

    Returns None when:
      - ``(metric, rounded_anchor, tc)`` is absent from
        ``COHORT_PERCENTILE_CDF`` (cell was suppressed at regen time per the
        K=200 / ±150-Elo policy — chip suppresses naturally).
      - ``value`` is NaN.

    Clamps:
      - value <= breakpoints[0]  (p1)  -> 0.0   (left tail beyond resolved range)
      - value >= breakpoints[-1] (p99) -> 100.0 (right tail beyond resolved range)
    """
    rounded_anchor = _round_anchor_to_grid(anchor)
    per_cell = COHORT_PERCENTILE_CDF.get(metric)
    if per_cell is None:
        return None
    table = per_cell.get((rounded_anchor, tc))
    if table is None:
        return None
    return _interpolate_with_table(table, value)


# ---------------------------------------------------------------------------
# Legacy stub — interpolate_percentile (retired in Plan 05).
# ---------------------------------------------------------------------------
#
# Plan 04 retires the flat ``GLOBAL_PERCENTILE_CDF`` registry and the 2-arg
# ``interpolate_percentile`` helper. Plan 05 (94.4-05) finishes the cutover
# at every call site (``user_benchmark_percentiles_service.py``,
# ``endgame_service.py``, tests). Between Plan 04 and Plan 05, leaving the
# old name a hard ImportError would break the wider test suite and bury the
# cutover signal. Instead the name is preserved as a stub returning ``None``
# with a one-shot ``DeprecationWarning`` per import.


def interpolate_percentile(
    metric_id: MetricId | CdfMetricId | str,
    value: float,  # noqa: ARG001 — preserved for caller signature compatibility
) -> float | None:
    """DEPRECATED (Phase 94.4 Plan 04 stub) — use ``interpolate_cohort_percentile``.

    Returns ``None`` unconditionally. The flat ``GLOBAL_PERCENTILE_CDF``
    registry retired in Phase 94.4 Plan 04 (CONTEXT D-09) in favour of the
    cohort-keyed ``COHORT_PERCENTILE_CDF`` and the 4-arg
    ``interpolate_cohort_percentile(metric, value, anchor, tc)`` helper.

    This stub exists ONLY to keep the module importable while Plan 05
    (94.4-05) finishes the cutover at every call site. Once those call
    sites are gone, the stub is removed.
    """
    warnings.warn(
        "interpolate_percentile is deprecated and returns None; "
        "use interpolate_cohort_percentile(metric, value, anchor, tc) "
        "from Phase 94.4 Plan 04 onwards.",
        DeprecationWarning,
        stacklevel=2,
    )
    _ = metric_id  # signature-only; the stub never reads either arg
    return None
