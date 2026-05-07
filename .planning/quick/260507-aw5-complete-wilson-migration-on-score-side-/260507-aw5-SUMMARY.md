---
title: Complete Wilson migration on score side
quick_id: 260507-aw5
date: 2026-05-07
status: complete
---

# Summary: Wilson migration on score side

## What changed

Migrated `score_confidence.compute_confidence_bucket` from a trinomial Wald p-value to a Wilson score-test p-value. The Wilson 95% CI (`wilson_bounds`) was already used for ranking and display; the p-value was the last Wald holdout on the score side. CI and significance call now agree by construction (the Wilson score test is the inversion of the Wilson CI).

Eval side (`eval_confidence.py`) intentionally untouched — Wilson is binomial-specific and doesn't apply to continuous one-sample mean tests.

## Code changes

- **`app/services/score_confidence.py`**: replaced empirical-variance Wald z with null-variance Wilson score-test z. Dropped the SE=0 special-case branch (Wilson is well-defined at all boundaries). Empirical (trinomial) SE retained in the 3-tuple return as informational. Module + function docstrings rewritten to explain Wilson rationale.
- **`app/schemas/openings.py`** + **`app/schemas/opening_insights.py`**: Pydantic Field comments updated from "Wald" to "Wilson score-test" terminology.
- **`app/services/opening_insights_constants.py`**: confidence-bucket comments and CI-z comment updated. Discovery-floor rationale updated to note Wilson reduces (but doesn't eliminate) post-selection inference sensitivity, and the n>=20 floor stays per quick 260506.
- **`app/services/opening_insights_service.py`**: Wilson-bucket comment updated.
- **`tests/services/test_score_confidence.py`**: 16 tests updated. The three previously-degenerate Wald boundary cases (n=10 all-wins, n=10 all-losses, n=9 all-wins) now test against Wilson's well-defined p-values (~0.00157, 0.00157, 0.0027 respectively).
- **`tests/services/test_opening_insights_arrow_consistency.py`**: structural-assertion docstring updated.
- **`frontend/src/components/insights/OpeningInsightsBlock.tsx`**: confidence tooltip text updated; "at least 10 games" stale reference fixed to "at least 20 games" (matching the n=20 floor from quick 260506).
- **`frontend/src/components/insights/WdlConfidenceTooltip.tsx`**: docstring + tooltip body updated.
- **`CHANGELOG.md`**: entry under `[Unreleased] / Changed`.

## Verification

- `uv run ruff check app/ tests/` — clean
- `uv run ty check app/ tests/` — clean
- `uv run pytest tests/services/ tests/test_zobrist.py` — 257 passed, 6 skipped
- `cd frontend && npm test -- --run` — 281 passed
- `cd frontend && npm run lint` — clean (3 pre-existing eslint-disable warnings unchanged)
- Spot-check: no active "Wald" references remain in score-side code paths; eval-side Wald references intentionally preserved; historical comments document the migration.

## Out of scope (flagged for later)

- z → t for eval-side small-N correction (sub-1% impact at n>=10 per existing docstring).
- BH-FDR multiple-comparisons correction across surfaced findings.
- Re-evaluating whether n>=20 floor can drop back to n>=10 now that Wilson is less sensitive to post-selection inference (separate decision).
