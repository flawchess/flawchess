"""Two-sided Wilson score-test p-value + N-gate confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Bucketing rule (thresholds + N gate shared with eval_confidence.py):
  - n < 10                         -> "low" (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.01     -> "high"
  - n >= 10 and p_value < 0.05     -> "medium"
  - n >= 10 and p_value >= 0.05    -> "low"

p_value is the **two-sided** Wilson score-test p against H0: score == 0.50,
computed as `erfc(|z| / sqrt(2))` where `z = (score - 0.50) / SE_null` and
`SE_null = sqrt(0.50 * 0.50 / n) = 0.5 / sqrt(n)` is the standard error
under the null (binomial-equivalent collapsing draws to half-credit).
Two-sided framing matches industry convention and keeps this test on the
same evidentiary footing as the eval test (eval_confidence.py): "high"
requires < 1% chance under H0 either way.

The directional verdict (weakness vs strength) is conveyed by the *sign* of
(score - 0.50), not by halving the p-value — a 60% score with two-sided
p < 0.01 is a high-confidence strength; a 40% score with the same p is a
high-confidence weakness.

**Why Wilson score-test (null variance) over Wald (estimated variance):**
Wald uses `var = (W + 0.25*D)/N - score^2` (the empirical trinomial variance),
which collapses to 0 at all-wins (W=N) or all-losses (L=N) — at the boundary
the Wald z is undefined and the test has to special-case the answer. Wilson
uses the null variance `0.5*0.5/n`, which is positive for any n>0 regardless
of observed outcomes, so the test is well-defined everywhere on the simplex.
Wilson is also the natural pair to the Wilson confidence interval already
returned by `wilson_bounds`: with the previous Wald p-value the CI and the
significance call could disagree at boundary scores. Now they agree by
construction (the Wilson score test is the inversion of the Wilson CI).

The helper returns a 3-tuple (confidence, p_value, se). SE is the *empirical*
trinomial standard error `sqrt(((W + 0.25*D)/N - score^2) / N)`, retained in
the return signature for callers that historically built Wald CI bounds; the
score CI itself is now Wilson (see `wilson_bounds`), so SE is informational
only — it describes the actual variance of the chess score on the data, not
the test SE used for the p-value.

Phase 83 Plan 2 Task 1: the Wilson math `(p_value, se_null)` is factored into
the private `_wilson_score_test_vs_half` helper so it can be reused by the
`compute_score_confidence_from_mean(score, n)` sibling without duplicating
the math. `compute_confidence_bucket(w, d, losses, n)` continues to accept
the (W, D, L, N) calling convention and returns the empirical SE; the sibling
accepts a pre-aggregated float mean and returns SE=0.0 (no W/D/L breakdown is
available to compute the trinomial variance from). Bucketing thresholds and
the N>=10 gate are shared.
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

    The Wilson score-test p-value computed by `compute_confidence_bucket` is
    the inversion of this interval: p < alpha iff the Wilson 1-alpha CI
    excludes 0.5. CI bounds and significance verdict therefore agree by
    construction.

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


def _wilson_score_test_vs_half(score: float, n: int) -> tuple[float, float]:
    """Return (p_value, se_null) for the two-sided Wilson score-test of H0: score == 0.5.

    Pure Wilson math — no bucketing, no N-gate, no edge-case clamp. Callers
    must gate on `n > 0` themselves; this helper assumes `n >= 1`.

    SE_null is the standard error under H0=0.5: `sqrt(0.5 * 0.5 / n)`, which
    is positive for any n>=1 so the test is well-defined everywhere.
    p_value is `erfc(|z| / sqrt(2))` for `z = (score - 0.5) / SE_null`.

    Phase 83 Plan 2 Task 1: single source of Wilson math; both
    `compute_confidence_bucket` and `compute_score_confidence_from_mean`
    delegate here so the formula appears exactly once in the codebase.
    """
    se_null = math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)
    z = (score - SCORE_PIVOT) / se_null
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return p_value, se_null


def _bucket_from_p_value(
    p_value: float, n: int
) -> Literal["low", "medium", "high"]:
    """Bucket a Wilson p-value into low/medium/high, with the N>=10 sample-size gate."""
    if n < CONFIDENCE_MIN_N:
        return "low"
    if p_value < CONFIDENCE_HIGH_MAX_P:
        return "high"
    if p_value < CONFIDENCE_MEDIUM_MAX_P:
        return "medium"
    return "low"


def compute_score_confidence_from_mean(
    score: float, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Return (confidence_bucket, two_sided_p_value, se) for a pre-aggregated (score, n).

    Sibling of `compute_confidence_bucket` accepting a float mean instead of
    the (W, D, L, N) breakdown. Bucketing and the N>=10 gate are identical;
    the only behavioural difference is the third tuple element:

      compute_confidence_bucket(w, d, losses, n) -> empirical trinomial SE
      compute_score_confidence_from_mean(score, n) -> 0.0 (no W/D/L breakdown)

    Returning 0.0 (instead of, say, the Wilson null SE) matches the contract
    expected by callers of `compute_confidence_bucket` for degenerate rows
    (all-wins / all-draws / all-losses already return SE=0.0). The third
    element is informational only — the Wilson p-value carries the test signal.

    Phase 83 Plan 2 Task 1: the new entry_expected_score aggregator in
    endgame_service is a float mean, not a (W, D, L) triple, so it cannot
    call `compute_confidence_bucket` directly. This sibling preserves the
    single Wilson code path while accepting the right input shape.

    n <= 0 returns ("low", 1.0, 0.0) without raising (mirrors the MD-02
    defensive guard on `compute_confidence_bucket`).
    """
    if n <= 0:
        return "low", 1.0, 0.0
    p_value, _se_null = _wilson_score_test_vs_half(score, n)
    return _bucket_from_p_value(p_value, n), p_value, 0.0


def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Return (confidence_bucket, two_sided_p_value, standard_error) for a (W, D, L, N) row.

    confidence_bucket is determined by the two-sided Wilson score-test p-value
    plus an N >= 10 sample-size gate:
      - n < 10                   -> "low" (matches the unreliable-stats UI dim;
                                    avoids "high, p ~ 0" with N=1 single-win or
                                    "high, p=1.0" with N=10 all-draws).
      - n >= 10, p < 0.01        -> "high"
      - n >= 10, p < 0.05        -> "medium"
      - n >= 10, p >= 0.05       -> "low"

    p_value is the two-sided Wilson score-test p-value on H0: score == 0.50,
    using the *null* standard error `SE_null = sqrt(0.5 * 0.5 / n) = 0.5/sqrt(n)`
    rather than the Wald empirical SE. Computed as `erfc(|z|/sqrt(2))` with
    `z = (score - 0.5) / SE_null`. Bounded in [0, 1].

    standard_error is the *empirical* trinomial standard error of the score
    `(W + 0.5*D) / N` under the binomial-with-half-credit-for-draws variance,
    clamped at 0.0 for degenerate (all-wins / all-draws / all-losses) rows.
    Returned for backward compat with callers that historically built Wald CI
    bounds; the score CI is now Wilson (see `wilson_bounds`), so SE is
    informational only — it describes the data's variance, not the test SE.

    Edge cases (Wilson is well-defined at all boundaries):
      - All-draws (score == 0.50): z = 0 -> p_value = 1.0 -> "low".
      - All-wins (score = 1, n>=10): z = sqrt(n), p ~ 0.00157 at n=10 -> "high".
      - All-losses (score = 0, n>=10): z = -sqrt(n), p ~ 0.00157 at n=10 -> "high".
      - n <= 0: returns ("low", 1.0, 0.0) without raising.

    No effect-size gate is applied (rejected during planning): the p-value bucket
    already encodes both magnitude and sample size, and the score classifier
    upstream applies the |score - 0.50| >= 0.05 minor/major effect threshold.

    Note: the `losses` parameter is accepted for API consistency with the
    (W, D, L, N) calling convention but is not used in the Wilson formula
    (only W, D, N matter for the score; the null SE depends on n only).
    """
    # MD-02 guard: callers today only pass rows with n >= 1, but openings_service.get_next_moves
    # has an inconsistent `if gc > 0` guard on the score expression while passing gc here
    # unconditionally. Defend against future contract drift (e.g. a new JOIN producing
    # zero-game rows) so this helper can never raise ZeroDivisionError. Returning ("low", 1.0, 0.0)
    # is the conservative two-sided null: no sample, no signal, no spread.
    if n <= 0:
        return "low", 1.0, 0.0

    score = (w + 0.5 * d) / n

    # Phase 83 Plan 2 Task 1: Wilson math factored into `_wilson_score_test_vs_half`
    # so the formula `(p_value, se_null)` lives in exactly one place. This call
    # is the inversion of `wilson_bounds` — rejecting H0 at alpha iff the Wilson
    # 1-alpha CI excludes 0.5.
    p_value, _se_null = _wilson_score_test_vs_half(score, n)

    # Empirical (trinomial) SE of the chess score, returned for backward compat.
    # Not used in the test — informational only. Clamped to 0 for degenerate
    # rows (all-wins / all-draws / all-losses).
    empirical_variance = max(0.0, (w + 0.25 * d) / n - score * score)
    se = math.sqrt(empirical_variance / n)

    return _bucket_from_p_value(p_value, n), p_value, se
