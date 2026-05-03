"""Two-sided Wald-z p-value + N-gate confidence helper for one-sample mean-vs-zero tests.

Used for Stockfish eval at middlegame entry (D-04). Callers supply already-trimmed
inputs per D-08: rows with |eval_cp| >= 2000 are excluded upstream in SQL via FILTER
predicates; the helper math is phase-agnostic.

Bucketing rule (thresholds imported from opening_insights_constants to maintain visual
and semantic consistency with the WDL confidence pills introduced in Phase 75 v1.14):
  - n < 10                        -> "low"   (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.05    -> "high"
  - n >= 10 and p_value < 0.10    -> "medium"
  - n >= 10 and p_value >= 0.10   -> "low"

p_value is the **two-sided** Wald z-test p against H0: mean == 0. Two-sided framing is
correct here because both directions are independently meaningful: a positive mean means
the user systematically enters the phase better off, a negative mean means systematically
worse off. The opening-insights helper (score_confidence.py) uses one-sided framing for
its directional question ("is score < 0.5?"); this helper uses two-sided because the
question is symmetric ("is the mean different from 0?"). Mathematically:
  p_value = erfc(|z| / sqrt(2))   [range: 0..1, two-sided normal approximation]
No 0.5× factor (that would halve to one-sided).

Statistical rationale for stdlib-only path: scipy.stats.ttest_1samp would give an exact
t-distribution p-value, but with N >= 10 (the gate is forced-low below that) the t and z
distributions differ by < 1% at p = 0.05 and < 6% at p = 0.10. scipy adds ~30 MB of
runtime dependency for sub-1% precision gain. This project lists 11 runtime deps, all
critical (CLAUDE.md); adding scipy is out of scope. Using math.erfc is consistent with
score_confidence.compute_confidence_bucket, which uses the same stdlib approximation.

Call sites (Phase 80):
  Called once per opening row in app.services.stats_service.get_most_played_openings
  finalizer — for MG-entry eval (eval_sum_mg, eval_sumsq_mg, eval_n_mg).
  Not exposed via routers directly.
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CI_Z_95 as CI_Z_95,
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
)


def compute_eval_confidence_bucket(
    eval_sum: float, eval_sumsq: float, n: int
) -> tuple[Literal["low", "medium", "high"], float, float, float]:
    """Compute (confidence, p_value, mean, ci_half_width) for H0: mean == 0.

    eval_sum: sum of (signed user-perspective) eval_cp values across n games.
    eval_sumsq: sum of squared eval_cp values (centipawns squared).
    n: count of games used in the mean (mate-excluded, NULL-excluded,
       outlier-trimmed |eval_cp| < 2000 per D-08; trim happens upstream in SQL).

    Procedure:
      - n == 0 -> ("low", 1.0, 0.0, 0.0).
      - n == 1 -> ("low", 1.0, eval_sum, 0.0)  # variance undefined; gated.
      - mean = eval_sum / n.
      - variance = max(0.0, (eval_sumsq - n * mean * mean) / (n - 1))  # Bessel-corrected.
      - se = sqrt(variance / n).
      - If se == 0.0: p_value = 0.0 if mean != 0 else 1.0.
      - Else: z = mean / se; p_value = math.erfc(abs(z) / math.sqrt(2.0))  # TWO-SIDED.
      - ci_half_width = CI_Z_95 * se.
      - Bucket:
          if n < CONFIDENCE_MIN_N: confidence = "low"
          elif p_value < CONFIDENCE_HIGH_MAX_P: confidence = "high"
          elif p_value < CONFIDENCE_MEDIUM_MAX_P: confidence = "medium"
          else: confidence = "low"

    Edge cases:
      - n <= 0: returns ("low", 1.0, 0.0, 0.0). No data, no signal.
      - n == 1: variance undefined (division by n-1 = 0); returns ("low", 1.0, mean, 0.0).
        Forced "low" by the N gate anyway.
      - All evals identical (variance = 0): SE = 0. If mean != 0 -> p = 0.0, confidence
        depends on N gate (>= 10 -> "high"). If mean == 0 -> p = 1.0 -> "low".
      - NaN inputs: not possible — eval_cp is SmallInteger, color_sign is +-1, both
        non-null by SQL filter (FILTER (WHERE eval_cp IS NOT NULL AND eval_mate IS NULL
        AND abs(eval_cp) < 2000) per D-08).
    """
    # Guard: n <= 0 — no sample, no signal. Return the two-sided null (p=1.0) and
    # zero for both mean and CI. Mirrors the n <= 0 guard in score_confidence.py.
    if n <= 0:
        return "low", 1.0, 0.0, 0.0

    mean = eval_sum / n

    # n == 1: variance is undefined (denominator n-1 = 0). Return mean but force "low"
    # via p_value = 1.0 (two-sided null) and ci_half_width = 0.0 (undefined spread).
    if n == 1:
        return "low", 1.0, mean, 0.0

    # Bessel-corrected sample variance: (sumsq - n * mean^2) / (n - 1).
    # Clamped at 0.0 to handle floating-point rounding where the raw value is
    # slightly negative despite mathematically being non-negative.
    variance = max(0.0, (eval_sumsq - n * mean * mean) / (n - 1))
    se = math.sqrt(variance / n)

    if se == 0.0:
        # Degenerate: all evals identical. Mean != 0 -> perfectly determined result
        # (z = +-inf, two-sided p = 0.0); mean == 0 -> the distribution IS zero (p = 1.0).
        p_value = 0.0 if mean != 0.0 else 1.0
    else:
        z = mean / se
        # Two-sided p-value: erfc(|z| / sqrt(2)) is in [0, 1].
        # No 0.5* factor — that would give one-sided p. Both positive and negative
        # deviations from zero are equally meaningful for the "is mean != 0?" question.
        p_value = math.erfc(abs(z) / math.sqrt(2.0))

    ci_half_width = CI_Z_95 * se

    # Bucket by N gate first, then p-value. N < CONFIDENCE_MIN_N (10) is forced "low"
    # even when SE = 0 would otherwise give a zero p-value (e.g. n=9 with all-same eval).
    if n < CONFIDENCE_MIN_N:
        confidence: Literal["low", "medium", "high"] = "low"
    elif p_value < CONFIDENCE_HIGH_MAX_P:
        confidence = "high"
    elif p_value < CONFIDENCE_MEDIUM_MAX_P:
        confidence = "medium"
    else:
        confidence = "low"

    return confidence, p_value, mean, ci_half_width
