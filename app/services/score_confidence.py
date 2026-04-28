"""Trinomial Wald confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Body migrated verbatim from app/services/opening_insights_service.py:105-152.
The signature is widened from (row: Any) to explicit (w, d, l, n) so callers
do not need a SQLAlchemy Row shim.
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH as CONFIDENCE_HIGH_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH as CONFIDENCE_MEDIUM_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)


def compute_confidence_bucket(
    w: int, d: int, l: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]:
    """Return (confidence_bucket, two_sided_p_value) for a (W, D, L, N) row.

    confidence_bucket is determined by the trinomial Wald 95% CI half-width:
      - half_width <= 0.10 -> "high"
      - half_width <= 0.20 -> "medium"
      - else               -> "low"

    p_value is the two-sided p-value for H0: score == 0.50, computed from the
    Wald z-statistic via math.erfc.

    Edge case: when SE == 0 (all draws or all wins or all losses), the bucket
    is "high" and p_value is 1.0 if score == 0.50 else 0.0.
    """
    score = (w + 0.5 * d) / n
    variance = (w + 0.25 * d) / n - score * score
    variance = max(variance, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        if score == SCORE_PIVOT:
            return "high", 1.0
        return "high", 0.0

    half_width = 1.96 * se  # 1.96 = z_{0.975}, constant of the formula
    if half_width <= CONFIDENCE_HIGH_MAX_HALF_WIDTH:
        confidence: Literal["low", "medium", "high"] = "high"
    elif half_width <= CONFIDENCE_MEDIUM_MAX_HALF_WIDTH:
        confidence = "medium"
    else:
        confidence = "low"

    z = (score - SCORE_PIVOT) / se
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return confidence, p_value
