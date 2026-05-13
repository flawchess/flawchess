---
phase: 85-section-1-games-with-vs-without-endgame-cards
plan: 01
subsystem: api
tags: [pydantic, fastapi, wilson, p-value, endgame]

# Dependency graph
requires:
  - phase: 81
    provides: endgame_score_p_value field + compute_confidence_bucket Wilson helper as the mirror template
provides:
  - non_endgame_score_p_value field on EndgamePerformanceResponse (Wilson score-test, n>=10 wire-format gate)
  - service-layer Wilson p-value computation on non_endgame_wdl mirroring the endgame_score_p_value block
  - pytest coverage of both gate branches of the new field
affects: [phase-85 Section 1 frontend card wiring, future Section 1 'Games without Endgame' card]

# Tech tracking
tech-stack:
  added: []
  patterns: [single Wilson code path via compute_confidence_bucket for all score sig tests on endgame WDL]

key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py

key-decisions:
  - "Mirror endgame_score_p_value rather than inventing a new helper — single Wilson code path per project convention (memory feedback_wilson_chess_score.md)"
  - "Same n>=10 wire-format gate as endgame_score_p_value / entry_eval_p_value / entry_expected_score_p_value — uniform reliability surface on the response"

patterns-established:
  - "Sibling Wilson p-value blocks (endgame_wdl + non_endgame_wdl) computed back-to-back in the performance aggregator with identical gate semantics"

requirements-completed:
  - SEC1-03
  - SEC1-06

# Metrics
duration: ~10min
completed: 2026-05-13
---

# Phase 85 Plan 01: Add non_endgame_score_p_value to EndgamePerformanceResponse Summary

**One additive Pydantic field plus 8 lines of service code: Wilson score-test p-value of non_endgame_wdl vs 50%, gated to None when total < 10, mirroring the existing endgame_score_p_value contract for the Section 1 'Games without Endgame' card.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-13T16:38Z (approximate; orchestrator-spawned)
- **Completed:** 2026-05-13T16:48Z (approximate)
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `EndgamePerformanceResponse.non_endgame_score_p_value: float | None = None` field with docstring mirroring endgame_score_p_value
- Service computes the mirror Wilson p-value via `compute_confidence_bucket(non_endgame_wdl.wins, draws, losses, total)` and gates to None below n=10
- Response constructor wires the new field alongside the existing `endgame_score_p_value`
- `TestEntryEvalAggregation.test_non_endgame_score_p_value_gated_below_n_ten` covers both gate branches (None below 10, float in [0, 1] at/above)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add non_endgame_score_p_value to EndgamePerformanceResponse and compute it in the service** — `9a488a1b` (feat)
2. **Task 2: Extend pytest coverage for non_endgame_score_p_value gate + numeric range** — `2b16b9f2` (test)

## Files Created/Modified

- `app/schemas/endgames.py` — added `non_endgame_score_p_value: float | None = None` field with docstring on `EndgamePerformanceResponse`
- `app/services/endgame_service.py` — added sibling Wilson block on `non_endgame_wdl` immediately below the existing `endgame_score_p_value` block; wired the new keyword argument into the `EndgamePerformanceResponse(...)` constructor
- `tests/test_endgame_service.py` — added `test_non_endgame_score_p_value_gated_below_n_ten` to `TestEntryEvalAggregation`, mirroring `test_endgame_score_p_value_gated_below_n_ten` but feeding `non_endgame_rows` and asserting on `non_endgame_score_p_value`

## Decisions Made

- Followed the plan's prescription verbatim: reuse `compute_confidence_bucket`, mirror the existing `endgame_score_p_value` block style (underscored-discard tuple unpack, inline n>=10 gate constant), one-line inline comment referencing Phase 85 D-01.
- Kept the test independent of the `endgame_score_p_value` behavior on the same response (feeds `endgame_rows=[]`) so a future refactor that splits the two p-values still passes — per Task 2's behavior spec.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Notes

**Milestone-boundary callout (Phase 85 D-01 / CONTEXT):** The v1.17 ROADMAP framing said the milestone was a "frontend-only refactor" with Phase 84 as the lone backend touch. Phase 85 adds one additive backend field (`non_endgame_score_p_value`) per user authorization recorded in 85-CONTEXT D-01. The field is strictly additive (default `None`, never required at any existing call site) and reuses the established Wilson code path, so the deviation from "frontend-only" is the minimum-surface backend change needed to keep the two Section 1 cards' p-values derived at a single site rather than independently computed by the frontend.

## Verification

- `uv run ruff check app/schemas/endgames.py app/services/endgame_service.py tests/test_endgame_service.py` — all checks passed
- `uv run ruff format --check` on the three modified files — already formatted
- `uv run ty check app/ tests/` — all checks passed (0 errors)
- `uv run pytest tests/test_endgame_service.py -x -k "non_endgame_score_p_value or endgame_score_p_value"` — 4 passed, 235 deselected
- `uv run pytest tests/test_endgame_service.py -x` — 239 passed (no regressions)
- `grep -n "non_endgame_score_p_value" app/schemas/endgames.py app/services/endgame_service.py tests/test_endgame_service.py` — field defined (schema:153), assigned + wired (service:1769, 1824), and asserted in tests

## Self-Check: PASSED

- File `app/schemas/endgames.py` modified — FOUND
- File `app/services/endgame_service.py` modified — FOUND
- File `tests/test_endgame_service.py` modified — FOUND
- Commit `9a488a1b` (Task 1) — FOUND
- Commit `2b16b9f2` (Task 2) — FOUND

## Next Phase Readiness

- Backend exposes `non_endgame_score_p_value` with identical n>=10 gating semantics to `endgame_score_p_value`. Section 1 'Games without Endgame' card can consume the field through the existing `/api/endgames/performance` payload.
- No frontend changes in this plan; the new TS field will surface via the existing OpenAPI codegen pass on the next frontend build.
- No blockers for downstream Phase 85 plans wiring the Section 1 cards.

---
*Phase: 85-section-1-games-with-vs-without-endgame-cards*
*Completed: 2026-05-13*
