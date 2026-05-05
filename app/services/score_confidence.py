"""Two-sided Wald-z p-value + N-gate confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Bucketing rule (thresholds + N gate shared with eval_confidence.py):
  - n < 10                         -> "low" (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.01     -> "high"
  - n >= 10 and p_value < 0.05     -> "medium"
  - n >= 10 and p_value >= 0.05    -> "low"

p_value is the **two-sided** Wald p against H0: score == 0.50, computed as
`erfc(|z| / sqrt(2))`. Two-sided framing matches industry convention and
keeps this test on the same evidentiary footing as the eval test
(eval_confidence.py): "high" requires < 1% chance under H0 either way.

The directional verdict (weakness vs strength) is conveyed by the *sign* of
(score - 0.50), not by halving the p-value — a 60% score with two-sided
p < 0.01 is a high-confidence strength; a 40% score with the same p is a
high-confidence weakness.

The helper returns a 3-tuple (confidence, p_value, se). SE is preserved in
the return signature for upstream callers that build CI bounds; the score
CI itself is now Wilson (see `wilson_bounds`), so SE is informational only.
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CI_Z_95 as CI_Z_95,
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)


def wilson_bounds(p: float, n: int) -> tuple[float, float]:
    """Return (lower, upper) Wilson 95% score interval bounds, clamped to [0, 1].

    Preferred over Wald for chess-score proportions in [0, 1]:
      - Wald (score +/- z * SE) is symmetric around p, so it routinely extends
        past 0 or 1 and has to be clamped, hiding the underlying problem.
      - Wald collapses to width 0 at p=0 and p=1 (SE=0), claiming impossible
        certainty. Wilson is well-defined at the boundaries.
      - The observed proportion p is always inside the (unclamped) Wilson
        interval, since Wilson is the score-test inversion at p == pi0.

    The n <= 0 branch is purely defensive — callers are expected to gate.
    """
    if n <= 0:
        return (0.0, 1.0)
    z = CI_Z_95
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1.0 - p) / n + z2 / (4 * n * n))) / denom
    lower = max(0.0, min(1.0, center - margin))
    upper = max(0.0, min(1.0, center + margin))
    return lower, upper


def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Return (confidence_bucket, two_sided_p_value, standard_error) for a (W, D, L, N) row.

    confidence_bucket is determined by the two-sided Wald p-value plus an
    N >= 10 sample-size gate:
      - n < 10                   -> "low" (matches the unreliable-stats UI dim;
                                    avoids "high, p=0.0" with N=1 single-win or
                                    "high, p=1.0" with N=10 all-draws).
      - n >= 10, p < 0.01        -> "high"
      - n >= 10, p < 0.05        -> "medium"
      - n >= 10, p >= 0.05       -> "low"

    p_value is the two-sided p-value for the Wald z-test on H0: score == 0.50,
    computed as `erfc(|z| / sqrt(2))`. Bounded in [0, 1].

    standard_error is the Wald standard error of the score (W + 0.5*D) / N
    under the binomial-with-half-credit-for-draws variance, clamped at 0.0 for
    degenerate (all-wins / all-draws / all-losses) rows. Returned for backward
    compat with callers that historically built Wald CI bounds; the score CI
    is now Wilson (see `wilson_bounds`), so SE is informational only.

    Edge cases (SE == 0):
      - All-draws (score == 0.50): p_value = 1.0 -> "low" (n >= 10) or "low" (n < 10).
      - All-wins or all-losses (score != 0.50): p_value = 0.0 -> "high" (n >= 10)
        or "low" (n < 10, gated).
      - n <= 0: returns ("low", 1.0, 0.0) without raising.

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
    # zero-game rows) so this helper can never raise ZeroDivisionError. Returning ("low", 1.0, 0.0)
    # is the conservative two-sided null: no sample, no signal, no spread.
    if n <= 0:
        return "low", 1.0, 0.0
    score = (w + 0.5 * d) / n
    variance = (w + 0.25 * d) / n - score * score
    variance = max(variance, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        # Degenerate case: all-draws (score==pivot) -> p=1.0 (two-sided null);
        # all-wins/all-losses -> p=0.0 (two-sided p of an extreme observation).
        p_value = 1.0 if score == SCORE_PIVOT else 0.0
    else:
        z = (score - SCORE_PIVOT) / se
        # Two-sided p; bounded in [0, 1].
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
    return confidence, p_value, se
