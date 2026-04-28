"""Wald p-value + N-gate confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Bucketing rule (replaces the prior trinomial Wald CI half-width buckets, which
answered "is the point estimate precise?" rather than "is this score different
from 50% by chance?"):
  - n < 10                        -> "low"   (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.01    -> "high"
  - n >= 10 and p_value < 0.05    -> "medium"
  - n >= 10 and p_value >= 0.05   -> "low"

The p_value formula itself (two-sided Wald z-test for H0: score == 0.50) is
unchanged from the half-width version.
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)


def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]:
    """Return (confidence_bucket, two_sided_p_value) for a (W, D, L, N) row.

    confidence_bucket is determined by the two-sided Wald p-value plus an
    N >= 10 sample-size gate:
      - n < 10                   -> "low" (matches the unreliable-stats UI dim;
                                    avoids "high, p=0.0" with N=1 single-win or
                                    "high, p=1.0" with N=10 all-draws).
      - n >= 10, p < 0.01        -> "high"
      - n >= 10, p < 0.05        -> "medium"
      - n >= 10, p >= 0.05       -> "low"

    p_value is the two-sided p-value for H0: score == 0.50, computed from the
    Wald z-statistic via math.erfc.

    Edge cases (SE == 0):
      - All-draws (score == 0.50): p_value = 1.0 -> "low" (n >= 10) or "low" (n < 10).
      - All-wins or all-losses (score != 0.50): p_value = 0.0 -> "high" (n >= 10)
        or "low" (n < 10, gated).

    No effect-size gate is applied (rejected during planning): the p-value bucket
    already encodes both magnitude and sample size, and the score classifier
    upstream applies the |score - 0.50| >= 0.05 minor/major effect threshold.

    Note: the `losses` parameter is accepted for API consistency with the
    (W, D, L, N) calling convention but is not used in the Wald formula
    (only W, D, N matter).
    """
    # MD-02 guard: callers today only pass rows with n >= 1, but openings_service.get_next_moves
    # has an inconsistent `if gc > 0` guard on the score expression while passing gc here
    # unconditionally. Defend against future contract drift (e.g. a new JOIN producing
    # zero-game rows) so this helper can never raise ZeroDivisionError. Returning ("low", 1.0)
    # is the conservative answer: no sample, no signal.
    if n <= 0:
        return "low", 1.0
    score = (w + 0.5 * d) / n
    variance = (w + 0.25 * d) / n - score * score
    variance = max(variance, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        # Degenerate case: all-draws (score==pivot) -> p=1.0; all-wins/all-losses -> p=0.0.
        p_value = 1.0 if score == SCORE_PIVOT else 0.0
    else:
        z = (score - SCORE_PIVOT) / se
        p_value = math.erfc(abs(z) / math.sqrt(2.0))

    # Bucket by p-value with an N >= 10 gate. Small samples are forced to "low"
    # to align with the unreliable-stats UI dim and avoid claiming "high" with
    # N=1 single-win or "high, p=1.0" with N=10 all-draws.
    if n < CONFIDENCE_MIN_N:
        confidence: Literal["low", "medium", "high"] = "low"
    elif p_value < CONFIDENCE_HIGH_MAX_P:
        confidence = "high"
    elif p_value < CONFIDENCE_MEDIUM_MAX_P:
        confidence = "medium"
    else:
        confidence = "low"
    return confidence, p_value
