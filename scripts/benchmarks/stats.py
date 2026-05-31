"""Pure statistics helpers for the benchmark generator (unit-tested, no DB).

The skill computes percentiles / mean / SD in SQL (`percentile_cont`, `stddev_samp`)
but **hand-computes** the Cohen's d collapse verdict in post-processing. Per SEED-029,
that hand-computed step moves here as a deterministic, tested function — the prior
LLM flow mislabeled at least one pair (see the chapter 2 ELO-axis footnote).

Per locked decision #2 this module emits the verdict *numbers* (max |d| + the pair);
the SKILL.md LLM applies the fixed `collapse / review / keep` threshold word.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import NamedTuple


class LevelStat(NamedTuple):
    """One marginal-axis level's aggregate, the input to Cohen's d."""

    label: str
    n: int
    mean: float
    var: float  # sample variance (var_samp)


class DResult(NamedTuple):
    """max |d| over an axis, and the pair (in input order) that produced it."""

    max_abs_d: float
    pair: tuple[str, str]
    d: float  # signed d for `pair` (mean_a - mean_b)


# SKILL.md "Sample floors": >= 10 users per marginal level for Cohen's d inclusion.
COHENS_D_MIN_N: int = 10


def cohens_d(a: LevelStat, b: LevelStat) -> float:
    """Pooled-SD Cohen's d between two levels. SKILL.md "Collapse verdict methodology".

    d = (mean_a - mean_b) / pooled_sd, where
    pooled_sd = sqrt(((n_a-1)*var_a + (n_b-1)*var_b) / (n_a + n_b - 2)).
    """
    pooled_var = ((a.n - 1) * a.var + (b.n - 1) * b.var) / (a.n + b.n - 2)
    return (a.mean - b.mean) / math.sqrt(pooled_var)


def spread_d(levels: Sequence[LevelStat]) -> DResult:
    """§3.4.1 collapse d: `(max_mean − min_mean) / sqrt(mean(group variances))`.

    A DIFFERENT recipe from `max_abs_d`'s pairwise pooled SD: the SKILL.md §3.4.1 verdict
    (line "Cohen's d (per class, per axis, per metric)") divides the full spread of group
    means by the root-mean of ALL eligible group variances, not the pooled SD of the two
    extreme groups. Reproduces the report's §3.4.1 conv/recov d's exactly (e.g. rook conv
    TC 1.24, pawn recov ELO 0.65). §3.4.2 / §3.1.5 use `max_abs_d` (pairwise pooled).
    The returned `pair` is (max-mean label, min-mean label); `d` is signed (max − min ≥ 0).
    """
    eligible = [lv for lv in levels if lv.n >= COHENS_D_MIN_N]
    if len(eligible) < 2:
        raise ValueError(
            f"spread_d needs >= 2 levels with n >= {COHENS_D_MIN_N}, got {len(eligible)}"
        )
    hi = max(eligible, key=lambda lv: lv.mean)
    lo = min(eligible, key=lambda lv: lv.mean)
    mean_var = sum(lv.var for lv in eligible) / len(eligible)
    d = (hi.mean - lo.mean) / math.sqrt(mean_var)
    return DResult(max_abs_d=abs(d), pair=(hi.label, lo.label), d=d)


def max_abs_d(levels: Sequence[LevelStat]) -> DResult:
    """max |Cohen's d| across all unordered pairs of levels (each n >= COHENS_D_MIN_N).

    Pairs are evaluated in input order, so for a deterministic, stable result pass
    `levels` already sorted in the report's display order (ELO ascending; TC in
    bullet/blitz/rapid/classical order). On ties the earlier pair wins.
    """
    eligible = [lv for lv in levels if lv.n >= COHENS_D_MIN_N]
    if len(eligible) < 2:
        raise ValueError(
            f"max_abs_d needs >= 2 levels with n >= {COHENS_D_MIN_N}, got {len(eligible)}"
        )
    best: DResult | None = None
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            a, b = eligible[i], eligible[j]
            d = cohens_d(a, b)
            if best is None or abs(d) > best.max_abs_d:
                best = DResult(max_abs_d=abs(d), pair=(a.label, b.label), d=d)
    assert best is not None  # guaranteed: len(eligible) >= 2
    return best
