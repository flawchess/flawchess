"""Wald p-value + N-gate confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Bucketing rule:
  - n < 10                        -> "low"   (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.05    -> "high"
  - n >= 10 and p_value < 0.10    -> "medium"
  - n >= 10 and p_value >= 0.10   -> "low"

p_value is the **one-sided** Wald p for the directional question "is the score
on the side of 0.5 the user actually cares about?" (i.e. for a weakness, "is
score < 0.5?"; for a strength, "is score > 0.5?"). Mathematically it equals
half the two-sided p; switching framing makes the tooltip copy honest, since
a finding card asks a directional question, not a two-tailed one.
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
    """Return (confidence_bucket, one_sided_p_value) for a (W, D, L, N) row.

    confidence_bucket is determined by the one-sided Wald p-value plus an
    N >= 10 sample-size gate:
      - n < 10                   -> "low" (matches the unreliable-stats UI dim;
                                    avoids "high, p=0.0" with N=1 single-win or
                                    "high, p=0.5" with N=10 all-draws).
      - n >= 10, p < 0.05        -> "high"
      - n >= 10, p < 0.10        -> "medium"
      - n >= 10, p >= 0.10       -> "low"

    p_value is the one-sided p-value for the directional Wald z-test on
    H0: score == 0.50, computed as 0.5 * erfc(|z| / sqrt(2)). The one-sided
    framing matches the directional question a finding card actually asks
    ("is this score worse/better than 50%?"); it is mathematically equivalent
    to halving the two-sided p, with p_value bounded in [0, 0.5].

    Edge cases (SE == 0):
      - All-draws (score == 0.50): p_value = 0.5 -> "low" (n >= 10) or "low" (n < 10).
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
    # zero-game rows) so this helper can never raise ZeroDivisionError. Returning ("low", 0.5)
    # is the conservative one-sided null: no sample, no signal.
    if n <= 0:
        return "low", 0.5
    score = (w + 0.5 * d) / n
    variance = (w + 0.25 * d) / n - score * score
    variance = max(variance, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        # Degenerate case: all-draws (score==pivot) -> p=0.5 (one-sided null);
        # all-wins/all-losses -> p=0.0 (one-sided p of an extreme observation).
        p_value = 0.5 if score == SCORE_PIVOT else 0.0
    else:
        z = (score - SCORE_PIVOT) / se
        # One-sided p for the directional alternative; equals (two-sided p) / 2.
        p_value = 0.5 * math.erfc(abs(z) / math.sqrt(2.0))

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
