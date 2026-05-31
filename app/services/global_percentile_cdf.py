"""Cohort empirical-CDF artifact: per-(metric, anchor, TC) percentile breakpoints.

Phase 94.4 — peer-relative percentile chip (CONTEXT D-09 / D-09a / D-13)
Phase 99.1 — registry relocated to DB (D-04: pure module, repo async)
-----------------------------------------------------------------------

This module provides the pure synchronous interpolation logic for the cohort
CDF.  The breakpoint data that was formerly inline in this module (as a large
in-source dict) now lives in the ``benchmark_cohort_cdf`` DB table, seeded by
``scripts/seed_cohort_cdf.py``.  The caller fetches the relevant cells once
per import via ``app.repositories.benchmark_cohort_cdf_repository.load_cohort_cells``
and passes the resulting ``CdfTable`` to ``interpolate_cohort_percentile``.

The chip is peer-relative: every user's percentile is read against an
in-window cohort of users near the user's anchor rating in the user's own TC.
The 11-metric ``CdfMetricId`` Literal (D-13 + Phase 99 rate families) and the
``CdfTable`` dataclass are the single source of truth imported repo-wide.

Key reshape vs Phase 94.3:

- **CdfMetricId collapses 16 → 11** (CONTEXT D-13, Phase 99 rate families).
  The 12 Phase 94.3 TC-suffixed entries retire — TC is an outer key on the
  DB table, not a metric suffix.
- **Helper shape (Phase 99.1 D-04)**: ``interpolate_cohort_percentile(value,
  table)`` takes a prefetched ``CdfTable | None`` and stays synchronous.
  The old 4-arg shape ``(metric, value, anchor, tc)`` that read from the
  in-source registry is retired.

Regen via ``scripts/gen_global_percentile_cdf.py --target benchmark`` to emit
the updated ``app/data/cohort_cdf.tsv``; then run ``scripts/seed_cohort_cdf.py``
to load the new breakpoints into the DB.

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
from dataclasses import dataclass, field
from typing import Final, Literal

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
# peer to the score-gap-bucket family. TC is an outer key on the registry (not a
# suffix on the metric name), so each metric has at most 4 cells per anchor.
#
# This Literal is the single source of truth — ``scripts/gen_global_percentile_cdf.py``
# re-exports it (drift-impossibility per RESEARCH §Pattern 3).
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    # Phase 99: raw-rate percentile families (TC is an outer registry key, NOT a
    # suffix here — per Phase 94.4 D-13 / Anti-Patterns in 99-RESEARCH.md).
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
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



def interpolate_cohort_percentile(value: float, table: CdfTable | None) -> float | None:
    """Linear-interpolate ``value`` against a PREFETCHED cohort CDF cell.

    Phase 99.1 shape (D-04, supersedes Phase 94.4 D-09a wording): the caller
    is responsible for fetching the ``CdfTable`` from the DB via
    ``app.repositories.benchmark_cohort_cdf_repository.load_cohort_cells``
    and resolving the correct cell with ``_round_anchor_to_grid``.  This
    function is pure / synchronous and performs no DB or I/O.

    Returns None when:
      - ``table`` is None (cell absent from the DB — suppressed at seed time
        per the K=200 / ±150-Elo policy; chip suppresses naturally).
      - ``value`` is NaN (handled inside ``_interpolate_with_table``).

    Clamps:
      - value <= breakpoints[0]  (p1)  -> 0.0   (left tail beyond resolved range)
      - value >= breakpoints[-1] (p99) -> 100.0 (right tail beyond resolved range)
    """
    if table is None:
        return None
    return _interpolate_with_table(table, value)


# Legacy ``interpolate_percentile`` stub retired in Phase 94.4 Plan 05b — every
# call site now uses ``interpolate_cohort_percentile``. Re-introducing a stub
# would mask future regressions (it returned None unconditionally), so the
# name is gone outright; an ImportError from any straggler is the desired
# signal.
