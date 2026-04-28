---
quick_id: 260428-oxr
type: execute
wave: 1
autonomous: true
files_modified:
  - app/services/score_confidence.py
  - app/services/opening_insights_constants.py
  - app/schemas/opening_insights.py
  - app/schemas/openings.py
  - tests/services/test_score_confidence.py
  - tests/services/test_opening_insights_service.py
  - frontend/src/lib/openingInsights.ts
  - frontend/src/components/insights/OpeningInsightsBlock.tsx

must_haves:
  truths:
    - "compute_confidence_bucket(w,d,l,n) bucket derives from p-value + N>=10 gate, not Wald CI half-width"
    - "N<10 always yields confidence='low' regardless of p-value"
    - "N>=10 with p<0.01 yields 'high'; p<0.05 yields 'medium'; else 'low'"
    - "Caller signature is unchanged: tuple[Literal['low','medium','high'], float]"
    - "Frontend tooltip copy describes statistical significance, not sample size"
    - "Old half-width threshold constants are removed (no dead code)"
  artifacts:
    - path: "app/services/score_confidence.py"
      provides: "Rewritten compute_confidence_bucket using p-value buckets + N>=10 gate"
    - path: "app/services/opening_insights_constants.py"
      provides: "OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P, MEDIUM_MAX_P, MIN_N constants (half-width constants removed)"
    - path: "tests/services/test_score_confidence.py"
      provides: "Tests covering N<10 gate, p-value boundaries, SE=0 edge cases under new rules"
    - path: "frontend/src/lib/openingInsights.ts"
      provides: "Updated formatConfidenceTooltip copy framing significance"
  key_links:
    - from: "app/services/opening_insights_service.py:388"
      to: "compute_confidence_bucket"
      via: "import; signature unchanged"
    - from: "app/services/openings_service.py:448"
      to: "compute_confidence_bucket"
      via: "import; signature unchanged"
---

<objective>
Replace the trinomial Wald CI half-width confidence bucketing with two-sided
Wald p-value bucketing plus an N>=10 sample-size gate. The function answers
"is this score plausibly different from 50% by chance?" instead of "is my
point estimate precise?". Keep the caller signature identical so the two
consumers (opening_insights_service.py:388, openings_service.py:448) work
unchanged. Remove dead half-width constants and rewrite tests + frontend
tooltip copy to match the new semantics.

Purpose: The previous bucketing produced confusing pairings (e.g. "high
confidence, p=1.0" when N=10 all-draws; "high confidence, p=0.0" with N=1).
The new rule aligns the bucket with the displayed p-value and the existing
n<10 unreliable-stats opacity dim in the UI.

Output: Rewritten helper + constants + tests + frontend tooltip copy.
3 atomic commits.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@app/services/score_confidence.py
@app/services/opening_insights_constants.py
@tests/services/test_score_confidence.py

<interfaces>
<!-- Caller call sites (DO NOT MODIFY) -->

app/services/opening_insights_service.py:388:
```python
confidence, p_value = compute_confidence_bucket(row.w, row.d, row.l, row.n)
```

app/services/openings_service.py:448:
```python
confidence, p_value = compute_confidence_bucket(w, d, lo, gc)
```

Required signature (unchanged):
```python
def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]: ...
```

The `losses` parameter is accepted for (W,D,L,N) calling convention but is
not used in the formula (only W, D, N matter for score and Wald p-value).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite compute_confidence_bucket and constants</name>
  <files>
    app/services/score_confidence.py,
    app/services/opening_insights_constants.py,
    app/schemas/opening_insights.py,
    app/schemas/openings.py
  </files>
  <action>
**In `app/services/opening_insights_constants.py`:**
- DROP `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH` (= 0.10) and
  `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH` (= 0.20).
- ADD three new constants in their place, with an updated header comment
  describing the new bucketing rule (p-value + N>=10 gate):
  ```python
  # Confidence buckets — two-sided Wald p-value thresholds plus N>=10 gate.
  # Replaces the prior CI half-width bucketing (which answered "is the point
  # estimate precise?" rather than "is this score different from 50% by chance?").
  # With N < 10, confidence is forced to "low" regardless of p-value: small
  # samples already carry the unreliable-stats opacity dim in the UI, and the
  # bucket should match that signal.
  OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
  OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.01
  OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.05
  ```

**In `app/services/score_confidence.py`:**
- Update the module docstring: replace "Trinomial Wald confidence helper"
  framing to describe p-value + N-gate bucketing. Keep the references to
  the two consumers (Phase 75 D-07 lock, Phase 76 D-06 split).
- Replace the half-width imports with:
  ```python
  from app.services.opening_insights_constants import (
      OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
      OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
      OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
      OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
  )
  ```
- Rewrite the function body. Keep:
  - The `if n <= 0: return "low", 1.0` guard (MD-02 contract drift defense).
  - The score/variance/SE computation block (unchanged Wald formula).
  - The `se == 0.0` branch (degenerate case): keep `p_value = 1.0` if
    score == SCORE_PIVOT else `p_value = 0.0`.
  - The Wald z + `math.erfc(abs(z) / sqrt(2))` p-value computation when SE > 0.
- Replace the bucket-derivation block. The new bucketing logic, applied AFTER
  p_value is computed (covering both the SE==0 and SE>0 paths), is:
  ```python
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
  ```
  Restructure so p_value is computed first (in both SE==0 and SE>0 paths),
  then a single bucket-decision block runs at the end. This collapses the
  prior duplicated SE==0 early-return.
- Update the function docstring to describe the new rules:
  - N<10 → "low" (matches unreliable-stats opacity dim)
  - p<0.01 → "high"; p<0.05 → "medium"; else → "low"
  - SE==0: with N>=10, all-wins/all-losses gives p=0.0 ("high"); all-draws
    gives p=1.0 ("low"). With N<10, falls under the gate ("low").
  - No effect-size gate (rejected by user; see plan rationale).
- Remove the `half_width = 1.96 * se` line (dead).
- Keep `losses` parameter doc note ("accepted for API consistency").

**In `app/schemas/opening_insights.py` (line 78) and `app/schemas/openings.py` (line 204):**
- Update the inline comment on the `confidence: Literal[...]` field from
  "Trinomial Wald 95% CI half-width bucket" to
  "Two-sided Wald p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium)".
  Preserve the Phase reference suffix.

**No other backend file is touched.** The score classifier
(`OPENING_INSIGHTS_MINOR_EFFECT` / `OPENING_INSIGHTS_MAJOR_EFFECT`) is
unrelated and stays. The two callers (`opening_insights_service.py:388`,
`openings_service.py:448`) are unchanged because the signature is unchanged.

Commit message:
`refactor(score-confidence): bucket by p-value with N>=10 gate, drop CI half-width`
  </action>
  <verify>
    <automated>uv run ruff check app/services/score_confidence.py app/services/opening_insights_constants.py app/schemas/opening_insights.py app/schemas/openings.py && uv run ty check app/services/score_confidence.py app/services/opening_insights_constants.py app/schemas/opening_insights.py app/schemas/openings.py</automated>
  </verify>
  <done>
- `compute_confidence_bucket` returns "low" for any (w,d,l,n) with n<10.
- For n>=10, bucket follows p-value: <0.01 high, <0.05 medium, else low.
- `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH` and
  `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH` no longer exist.
- New `_HIGH_MAX_P`, `_MEDIUM_MAX_P`, `_MIN_N` constants are exported.
- Schema field comments updated.
- ruff + ty pass with zero errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite test_score_confidence.py and fix related tests</name>
  <files>
    tests/services/test_score_confidence.py,
    tests/services/test_opening_insights_service.py
  </files>
  <action>
**Rewrite `tests/services/test_score_confidence.py` from scratch.** Replace
the file with the new test suite below. Update the module docstring to
reference the new bucketing rules (no more "half-width = 0.10/0.20 boundary"
prose).

The new tests (each pairs a clear (w,d,l,n) input with the expected bucket
under the new rules):

```python
"""Unit tests for app.services.score_confidence.compute_confidence_bucket.

Bucketing rule under test (replaces the prior Wald CI half-width buckets):
  - n < 10                        -> "low"  (unreliable-stats gate)
  - n >= 10 and p_value < 0.01    -> "high"
  - n >= 10 and p_value < 0.05    -> "medium"
  - n >= 10 and p_value >= 0.05   -> "low"

p_value is the two-sided p-value for H0: score == 0.50 from the Wald z-test;
the formula itself is unchanged. SE == 0 cases produce p_value = 1.0 if
score == 0.5 (all draws) or 0.0 otherwise (all wins / all losses).
"""

import pytest

from app.services.score_confidence import compute_confidence_bucket


# --- N < 10 gate ---------------------------------------------------------

def test_n_below_gate_returns_low_even_with_strong_evidence() -> None:
    # n=9 all wins: p_value would be 0.0 (SE=0) but n<10 forces "low".
    confidence, p_value = compute_confidence_bucket(w=9, d=0, losses=0, n=9)
    assert confidence == "low"
    assert p_value == 0.0


def test_n_below_gate_single_win_is_low() -> None:
    # n=1 single win used to produce "high, p=0.0" under the old rule. Now: "low".
    confidence, _p = compute_confidence_bucket(w=1, d=0, losses=0, n=1)
    assert confidence == "low"


def test_n_below_gate_balanced_is_low() -> None:
    confidence, _p = compute_confidence_bucket(w=2, d=2, losses=2, n=6)
    assert confidence == "low"


def test_n_zero_returns_low_one() -> None:
    """MD-02 guard: n<=0 returns ("low", 1.0) without raising."""
    confidence, p_value = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 1.0


# --- N >= 10 buckets by p-value ------------------------------------------

def test_high_at_strong_evidence() -> None:
    # n=400 with score = 0.40: SE small, |z| large, p << 0.01.
    confidence, p_value = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    assert confidence == "high"
    assert p_value < 0.01


def test_medium_at_moderate_evidence() -> None:
    # Pick a (w,d,l,n) that sits in 0.01 <= p < 0.05.
    # n=50, w=15, d=10, losses=25: score = (15 + 5)/50 = 0.40
    # variance = (15 + 2.5)/50 - 0.16 = 0.35 - 0.16 = 0.19
    # se = sqrt(0.19/50) ≈ 0.0616; z = -0.10/0.0616 ≈ -1.62; p ≈ 0.105 -> low actually.
    # Use n=100, w=35, d=20, losses=45: score=0.45, var=(35+5)/100 - 0.2025 = 0.1975
    # se = sqrt(0.001975) ≈ 0.0444; z = -0.05/0.0444 ≈ -1.125; p ≈ 0.26 -> low.
    # Stronger: n=100 score=0.40: w=35, d=10, losses=55. score=0.40
    # var=(35+2.5)/100 - 0.16 = 0.215; se=sqrt(0.00215)≈0.0464; z=-2.16; p≈0.031 -> medium.
    confidence, p_value = compute_confidence_bucket(w=35, d=10, losses=55, n=100)
    assert confidence == "medium"
    assert 0.01 <= p_value < 0.05


def test_low_at_weak_evidence_with_large_n() -> None:
    # Score very close to 0.50 with n=100: |z| small, p large.
    # n=100, w=48, d=4, losses=48: score=0.50 exactly -> p=1.0 -> low.
    confidence, p_value = compute_confidence_bucket(w=48, d=4, losses=48, n=100)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


def test_low_at_n10_balanced() -> None:
    # n=10 score exactly 0.5: p=1.0, n>=10, falls into "else low".
    confidence, p_value = compute_confidence_bucket(w=2, d=6, losses=2, n=10)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


# --- SE == 0 boundary cases (n >= 10) -----------------------------------

def test_se_zero_all_wins_n10_is_high() -> None:
    """All wins at n=10: score=1.0, p=0.0 -> high (10+ identical outcomes IS strong evidence)."""
    confidence, p_value = compute_confidence_bucket(w=10, d=0, losses=0, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_losses_n10_is_high() -> None:
    confidence, p_value = compute_confidence_bucket(w=0, d=0, losses=10, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_draws_n10_is_low() -> None:
    """All draws at n=10: score=0.5, p=1.0 -> low (no evidence of any direction)."""
    confidence, p_value = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert confidence == "low"
    assert p_value == 1.0
```

For each `medium` test case, sanity-check the chosen (w,d,l,n) before
committing by running it through the formula in a Python REPL. If the
suggested values land outside the intended bucket, swap them for nearby
values that hit the bucket. The asserted bounds on `p_value` are the
contract; the exact (w,d,l,n) is incidental.

**In `tests/services/test_opening_insights_service.py`:**
- Update line 708's inline arithmetic comment (around
  `test_compute_insights_populates_confidence_and_p_value`):
  - The current comment says `half_width ≈ 0.140 → medium`.
  - Replace with: `# z ≈ -4.89; p ≈ 1e-6; n=20 >= 10 → high`.
  - Tighten the assertion `finding.confidence in {"low","medium","high"}`
    to `assert finding.confidence == "high"` since under the new rules
    p≈1e-6 with n=20 is unambiguously "high".

Do NOT modify `tests/services/test_opening_insights_arrow_consistency.py` —
its assertions only reference `MAJOR_EFFECT_SCORE`, `MIN_GAMES_FOR_COLOR`,
and the structural existence of `compute_confidence_bucket`. None of those
change.

Do NOT modify `tests/test_openings_service.py:562-614` — that test computes
its expected confidence by calling `compute_confidence_bucket` directly, so
it auto-adapts to the new rules. (n=3 in that test, so the new code returns
"low" while the helper-driven assertion stays consistent.)

Run the full backend test suite to catch any other unrelated breakage:
`uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py tests/test_openings_service.py -x`

Commit message:
`test(score-confidence): rewrite bucket tests for p-value + N>=10 gate`
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py tests/test_openings_service.py -x</automated>
  </verify>
  <done>
- `tests/services/test_score_confidence.py` rewritten; all new tests pass.
- `tests/services/test_opening_insights_service.py` line ~708 comment +
  assertion updated to match new rules; test passes.
- Other touched test files (arrow consistency, openings service) still pass
  unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update frontend tooltip copy and Insights popover prose</name>
  <files>
    frontend/src/lib/openingInsights.ts,
    frontend/src/components/insights/OpeningInsightsBlock.tsx
  </files>
  <action>
**In `frontend/src/lib/openingInsights.ts`:**
- Replace the `CONFIDENCE_BASE_COPY` map with copy that frames the bucket as
  statistical-significance evidence (the new semantics):
  ```ts
  const CONFIDENCE_BASE_COPY: Record<ConfidenceLevel, string> = {
    low: 'Not enough evidence — this could plausibly be chance',
    medium: 'Likely a real effect (p < 0.05)',
    high: 'Strong evidence of a real effect (p < 0.01)',
  };
  ```
- Keep `formatConfidenceTooltip` body unchanged (it appends `(p = X.XXX)`).
- Update the JSDoc on `formatConfidenceTooltip` to reflect the new framing:
  `/** Tooltip copy for confidence indicators — significance level explainer plus the actual p-value. */`

**In `frontend/src/components/insights/OpeningInsightsBlock.tsx` (around lines 22-25):**
- Replace the popover paragraph that currently reads
  "Confidence says how big the sample is. Low findings are worth a glance;
  high findings are well-supported."
  with a paragraph that matches the new semantics:
  ```tsx
  <p>
    <strong>Confidence</strong> says whether the score is likely a real effect
    or could plausibly be chance. <em>Low</em> findings are worth a glance;{' '}
    <em>high</em> findings have strong statistical evidence (p &lt; 0.01).
  </p>
  ```
  Keep the surrounding `<Score>` / 5%-gap paragraphs untouched.

Avoid em-dashes per CLAUDE.md style guide ("a single em-dash per paragraph
is plenty"). The first paragraph in the new tooltip copy uses one em-dash;
that's the budget.

Run frontend lint + tests to confirm no other component regresses:
`cd frontend && npm run lint && npm test`

If `OpeningFindingCard.test.tsx` or `OpeningInsightsBlock.test.tsx` asserts
on the old tooltip strings (search for "Small sample" / "Enough games" /
"Sample is large enough" / "how big the sample is"), update those
assertions to match the new copy.

Commit message:
`fix(frontend): reframe confidence tooltip copy as statistical significance`
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run</automated>
  </verify>
  <done>
- `formatConfidenceTooltip` returns the new significance-framed copy with
  the existing `(p = X.XXX)` suffix.
- `OpeningInsightsBlock` popover paragraph reflects the new semantics.
- Any test that asserted on old strings is updated.
- Frontend lint and tests pass.
  </done>
</task>

</tasks>

<verification>
After all three tasks:
- `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest`
  passes end-to-end.
- `cd frontend && npm run lint && npm test -- --run` passes.
- `grep -rn "HALF_WIDTH\|half_width\|half-width" app/services tests/services frontend/src/lib/openingInsights.ts frontend/src/components/insights`
  returns zero matches in confidence-bucketing context (the unrelated
  bullet-chart "half-width" hits in `frontend/src/components/charts/*`
  are about chart geometry, not statistics, and stay).
- Manual sanity check (optional): N=1 single-win, N=10 all-draws, and
  N=10 all-wins all return the bucket described in the background section.
</verification>

<success_criteria>
- compute_confidence_bucket bucketing matches the new rule for all four
  characteristic cases: N<10 always low, N>=10 + small p high, N>=10 +
  moderate p medium, N>=10 + large p low.
- Old half-width constants are gone; new p-value + N constants exist.
- Frontend tooltip and popover copy describes statistical significance.
- All backend + frontend tests pass.
- 3 atomic commits land in this order: refactor(score-confidence) →
  test(score-confidence) → fix(frontend).
</success_criteria>

<output>
This is a `/gsd-quick` plan; no SUMMARY.md is required. Commit history (the
three commits above) is the artifact. The change ships on whatever branch
this plan is executed against; merge to main via PR per CLAUDE.md.
</output>
