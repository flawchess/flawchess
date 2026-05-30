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
