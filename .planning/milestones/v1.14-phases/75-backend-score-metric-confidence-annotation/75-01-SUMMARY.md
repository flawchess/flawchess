---
phase: 75
plan: 01
subsystem: backend/openings
tags:
  - openings
  - insights
  - constants
  - ci-consistency-test
requirements:
  - INSIGHT-SCORE-03
  - INSIGHT-SCORE-05
  - INSIGHT-SCORE-07
dependency_graph:
  requires:
    - .planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md
  provides:
    - OPENING_INSIGHTS_SCORE_PIVOT
    - OPENING_INSIGHTS_MINOR_EFFECT
    - OPENING_INSIGHTS_MAJOR_EFFECT
    - OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH
    - OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH
    - OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE (was 20, now 10)
    - SCORE_PIVOT / MINOR_EFFECT_SCORE / MAJOR_EFFECT_SCORE (frontend exports for Phase 76)
  affects:
    - app/repositories/openings_repository.py (broken until Plan 02 — still imports removed OPENING_INSIGHTS_LIGHT_THRESHOLD)
    - app/services/opening_insights_service.py (broken until Plan 02 — same reason)
tech_stack:
  added: []
  patterns:
    - constants-as-source-of-truth across backend/frontend with regex-driven CI lock-step
    - pure-additive frontend exports decouple Phase 75 / Phase 76 merge ordering
key_files:
  created: []
  modified:
    - app/services/opening_insights_constants.py
    - frontend/src/lib/arrowColor.ts
    - tests/services/test_opening_insights_arrow_consistency.py
decisions:
  - D-10 — score-pivot + symmetric effect-size + confidence half-widths in single constants module
  - D-12 — pure-additive frontend exports (option (b) merge ordering); getArrowColor body untouched
  - D-13 — CI test asserts effect-size lock-step only; confidence buckets out-of-scope until Phase 76
metrics:
  duration_seconds: ~660
  completed_at: "2026-04-28T10:14:46Z"
  tasks: 3
  files_modified: 3
  commits: 3
---

# Phase 75 Plan 01: Constants foundation — score metric + confidence buckets Summary

**One-liner:** Rewrite `opening_insights_constants.py` for score-based effect sizes and Wald-CI half-width buckets, add three pure-additive frontend exports, and rewrite the CI consistency test for score-based lock-step — all while leaving the v1.13 service body untouched (Plan 02 owns the service rewrite).

## Outcome

Plan 01 lands the **shape** that Plans 02 and 03 will build on:

- Backend constants module is rewritten wholesale per D-10. The Phase 70 `OPENING_INSIGHTS_LIGHT_THRESHOLD` (the only metric threshold) is removed. Six new score-based constants ship: `OPENING_INSIGHTS_SCORE_PIVOT=0.50`, `OPENING_INSIGHTS_MINOR_EFFECT=0.05`, `OPENING_INSIGHTS_MAJOR_EFFECT=0.10`, `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH=0.10`, `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH=0.20`. The discovery floor `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE` drops from 20 to 10 (the confidence badge now replaces the prior hard floor).
- Frontend `arrowColor.ts` gains three pure-additive top-level exports: `SCORE_PIVOT=0.50`, `MINOR_EFFECT_SCORE=0.05`, `MAJOR_EFFECT_SCORE=0.10`. The `getArrowColor()` body and the existing `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` / hex constants are byte-for-byte identical (Phase 76 owns the body rewrite). This decouples merge ordering: Plan 01 ships, the CI consistency test is green immediately, Phase 76 then refactors the body to consume the new exports.
- CI consistency test is rewritten per D-13. Four assertions (`SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`, `MIN_GAMES_FOR_COLOR` all match their backend counterparts). The Phase 70 `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` integer-percent assertions are removed. Confidence bucket constants are deliberately NOT in the CI test (Phase 76 decides whether the moves-explorer endpoint exposes confidence per move or the frontend computes it locally).

## Tasks executed

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Rewrite `opening_insights_constants.py` with score-based thresholds and confidence half-widths | `0ce9da8` |
| 2 | Add `SCORE_PIVOT` / `MINOR_EFFECT_SCORE` / `MAJOR_EFFECT_SCORE` pure-additive exports to `arrowColor.ts` | `9027336` |
| 3 | Rewrite `test_opening_insights_arrow_consistency.py` for score-based lock-step assertions | `e3baa9e` |

## Verification (per-task scope)

- Task 1: `uv run ty check app/services/opening_insights_constants.py` → all checks passed; `uv run ruff format --check ...` → already formatted; all six constants present, `OPENING_INSIGHTS_LIGHT_THRESHOLD` fully removed.
- Task 2: All six grep checks (`SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`, `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`, `MIN_GAMES_FOR_COLOR`) pass; `npm run lint -- --max-warnings=0` clean; `npm run knip` clean; `npm test` 152/152 passed.
- Task 3: With the broken-cross-module-import workaround (`--confcutdir=tests/services` to bypass `tests/conftest.py` which loads the `seed_fixtures` plugin) → 4/4 tests pass; `uv run ruff format --check` clean; `uv run ty check tests/services/test_opening_insights_arrow_consistency.py` clean.

## Known transient breakage (expected — resolved by Plan 02)

The plan explicitly anticipates this; documenting here for the verifier and the Plan 02 executor:

- `app/services/opening_insights_service.py` line 35 still imports `OPENING_INSIGHTS_LIGHT_THRESHOLD as LIGHT_THRESHOLD` — Plan 02 rewrites this to consume the new score-based constants and drops the `LIGHT_THRESHOLD` / `DARK_THRESHOLD` re-exports.
- `app/repositories/openings_repository.py` lines 19-20 still import `OPENING_INSIGHTS_LIGHT_THRESHOLD` and use it on lines 686-687 in the SQL HAVING clause — Plan 02 rewrites the HAVING to the score-based effect-size gate per D-08.
- Consequence: `uv run pytest <any test>` fails at COLLECTION because `tests/conftest.py` registers `tests.seed_fixtures` as a `pytest_plugins`, and `seed_fixtures` imports `app.main`, which transitively imports the broken `openings_repository.py`. The broad `uv run ty check app/ tests/` likewise reports `OPENING_INSIGHTS_LIGHT_THRESHOLD` import errors in the two service/repository modules.
- This is the documented expected state per Plan 01 acceptance criteria: *"At this point pytest may break elsewhere because Plan 02 has not yet fixed `opening_insights_service.py` (which still imports `OPENING_INSIGHTS_LIGHT_THRESHOLD`). That breakage is OK and expected within this plan boundary; Plan 02 fixes it."*
- The new consistency test logic itself is correct — verified by running with `--confcutdir=tests/services` to bypass the conftest plugin chain.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist on disk:

- `app/services/opening_insights_constants.py` — FOUND
- `frontend/src/lib/arrowColor.ts` — FOUND (modified)
- `tests/services/test_opening_insights_arrow_consistency.py` — FOUND

Commits exist on branch:

- `0ce9da8` — FOUND (`feat(75-01): rewrite opening_insights_constants for score-based classification`)
- `9027336` — FOUND (`feat(75-01): add score-based exports to arrowColor.ts`)
- `e3baa9e` — FOUND (`test(75-01): rewrite arrow-consistency test for score-based lock-step`)

## Next Steps

- Plan 02 (wave 2 / depends on Plan 01): rewrite `opening_insights_service.py` `_classify_row` for score-based classification, add `_compute_confidence` helper (trinomial Wald 95% CI + two-sided p-value), wire `confidence` and `p_value` into `OpeningInsightFinding`, rewrite SQL HAVING in `openings_repository.py`, drop `loss_rate` / `win_rate` from the schema, update `test_opening_insights_service.py`. After Plan 02 lands, the broad `pytest` and `ty check` will be green again.
- Plan 03 (wave 2): boundary tests + integration sanity for the new metric / confidence pipeline.
- Plan 04: API contract test sweep + final tidy.
