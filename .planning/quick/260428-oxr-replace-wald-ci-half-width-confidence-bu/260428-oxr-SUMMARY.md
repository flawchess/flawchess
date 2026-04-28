---
quick_id: 260428-oxr
type: summary
status: complete
completed: 2026-04-28
commits:
  - 353cad5 refactor(score-confidence): bucket by p-value with N>=10 gate, drop CI half-width
  - 7c3730e test(score-confidence): rewrite bucket tests for p-value + N>=10 gate
  - f29617d fix(frontend): reframe confidence tooltip copy as statistical significance
files_modified:
  - app/services/score_confidence.py
  - app/services/opening_insights_constants.py
  - app/schemas/opening_insights.py
  - app/schemas/openings.py
  - tests/services/test_score_confidence.py
  - tests/services/test_opening_insights_service.py
  - frontend/src/lib/openingInsights.ts
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
---

# Quick Task 260428-oxr Summary

## One-liner

Replaced the trinomial Wald CI half-width confidence bucketing with two-sided Wald
p-value bucketing plus an N>=10 sample-size gate, so the confidence badge answers
"is this score plausibly different from 50% by chance?" instead of "is my point
estimate precise?".

## What changed

- **`app/services/score_confidence.py`** — `compute_confidence_bucket` now buckets
  by p-value with an N>=10 gate: n<10 → "low" (matches the unreliable-stats UI
  dim); n>=10 with p<0.01 → "high"; p<0.05 → "medium"; else "low". The Wald p-value
  formula is unchanged. SE==0 paths now flow through the unified bucket-decision
  block (no early return), collapsing duplicated logic. Caller signature is
  unchanged so the two consumers (`opening_insights_service.py:388`,
  `openings_service.py:448`) work without modification.
- **`app/services/opening_insights_constants.py`** — dropped
  `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH` and
  `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH`; added
  `OPENING_INSIGHTS_CONFIDENCE_MIN_N` (10),
  `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P` (0.01), and
  `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P` (0.05). Header comment rewritten.
- **`app/schemas/opening_insights.py` + `app/schemas/openings.py`** — inline field
  comments updated from "Trinomial Wald 95% CI half-width bucket" to
  "Two-sided Wald p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium)".
- **`tests/services/test_score_confidence.py`** — rewritten from scratch. Covers
  N<10 gate (n=9 all-wins still "low", n=1 single-win "low", balanced n=6 "low",
  MD-02 n=0 guard), p-value buckets at n>=10 (high/medium/low boundaries
  including the n=100 score=0.40 medium case), and SE==0 corners (all-wins/all-
  losses → "high", all-draws → "low" at n=10).
- **`tests/services/test_opening_insights_service.py`** — tightened the
  confidence smoke assertion to `confidence == "high"` (n=20, score=0.15,
  p≈1e-6); swapped the medium fixture in `test_ranking_confidence_desc_then_score_distance_desc`
  from (n=30, w=6, d=6, l=18) to (n=100, w=35, d=10, l=55) so the fixture
  actually lands in the medium bucket under the new rule (Rule 1 fix).
- **`frontend/src/lib/openingInsights.ts`** — `CONFIDENCE_BASE_COPY` rewritten
  to frame the bucket as statistical significance: "Not enough evidence — this
  could plausibly be chance" / "Likely a real effect (p < 0.05)" / "Strong
  evidence of a real effect (p < 0.01)". JSDoc on `formatConfidenceTooltip`
  updated.
- **`frontend/src/components/insights/OpeningInsightsBlock.tsx`** — section-title
  popover paragraph rewritten: "Confidence says whether the score is likely a
  real effect or could plausibly be chance. Low findings are worth a glance;
  high findings have strong statistical evidence (p < 0.01)."

## Why

The previous half-width bucketing produced confusing pairings between the
displayed bucket and the displayed p-value: e.g. "high confidence, p=1.0" with
N=10 all-draws (the helper returned "high" even though the p-value is the
weakest possible) and "high, p=0.0" with N=1 single-win. The new rule aligns the
bucket with the statistical significance the user can also see in the tooltip,
and respects the existing N<10 unreliable-stats opacity dim in the UI.

## Verification

- `uv run ruff check .` — passes.
- `uv run ty check app/ tests/` — passes (zero errors).
- `uv run pytest` — all 1158 backend tests pass.
- `cd frontend && npm run lint` — 0 errors (3 pre-existing warnings in
  `coverage/` artifacts, unrelated to this change).
- `cd frontend && npm test -- --run` — all 161 frontend tests pass.
- `cd frontend && npx tsc --noEmit` — passes.
- `grep -rn "HALF_WIDTH\|half_width" app/services tests/services
  frontend/src/lib/openingInsights.ts frontend/src/components/insights` — only
  intentional historical-context mentions in docstrings remain; no logic uses
  half-width anymore.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix broken `test_ranking_confidence_desc_then_score_distance_desc` fixture**
- **Found during:** Task 2
- **Issue:** The `medium_any_delta` fixture in `tests/services/test_opening_insights_service.py:598` (n=30, w=6, d=6, l=18) was relying on the old half-width bucketing to land in the "medium" bucket. Under the new p-value + N>=10 rule, that input produces p≈0.006 → "high", which broke the high-vs-medium ordering assertion. The plan called out two adjacent test files to update but missed this third one.
- **Fix:** Replaced the fixture with (n=100, w=35, d=10, l=55) which produces p≈0.031 → "medium" under the new rule, preserving the test's intent (high before medium, ties broken by |score - 0.5|). Added an inline comment explaining the bucket choice.
- **Files modified:** `tests/services/test_opening_insights_service.py`
- **Commit:** `7c3730e` (folded into the Task 2 commit per the plan's verification gate, since the fix is purely a fixture adjustment to keep the test consistent with the new helper).

## Self-Check

- File `app/services/score_confidence.py` — FOUND
- File `app/services/opening_insights_constants.py` — FOUND
- File `app/schemas/opening_insights.py` — FOUND
- File `app/schemas/openings.py` — FOUND
- File `tests/services/test_score_confidence.py` — FOUND
- File `tests/services/test_opening_insights_service.py` — FOUND
- File `frontend/src/lib/openingInsights.ts` — FOUND
- File `frontend/src/components/insights/OpeningInsightsBlock.tsx` — FOUND
- Commit `353cad5` — FOUND
- Commit `7c3730e` — FOUND
- Commit `f29617d` — FOUND

## Self-Check: PASSED
