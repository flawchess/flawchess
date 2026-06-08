---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
plan: 01
subsystem: api
tags: [python, flaws, classification, impact, tempo, tdd]

# Dependency graph
requires: []
provides:
  - "Constants WINNING_LINE_ES=0.70, LOSING_LINE_ES=0.30, SQUANDERED_EXIT_ES=0.60 in flaws_service.py"
  - "Renamed FlawTag Literals: reversed/squandered (impact), hasty/unrushed (tempo)"
  - "Renamed TempoTag Literals: hasty, unrushed (order: low-clock, hasty, unrushed)"
  - "_classify_impact helper: outcome-independent >= entry / <= exit boundary ladder"
  - "TestImpactLadder test class: reversed/squandered boundary tests + outcome-independence"
  - "Deleted: RESULT_WIN_THRESHOLD, RESULT_DRAW_THRESHOLD, _is_result_changing"
affects:
  - 110-02-PLAN.md (repo writer and migration depend on new tag names)
  - 110-03-PLAN.md (router/schema depend on FlawTag Literal changes)
  - 110-04-PLAN.md (library_service tempo/impact field renames)
  - 110-05-PLAN.md (frontend type changes depend on new tag names)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Outcome-independent impact classifier: pure ES-before/ES-after function, no game result"
    - ">= entry / <= exit inclusive boundary convention for impact thresholds"
    - "Most-severe-wins ladder: reversed checked before squandered; at most one impact tag per flaw"
    - "user_result kept in _build_tags/_classify_game_flaws signature for lucky-escape end-of-game rule"

key-files:
  created: []
  modified:
    - app/services/flaws_service.py
    - tests/services/test_flaws_service.py

key-decisions:
  - "Inclusive exit boundary (>= entry, <= exit) for _classify_impact per flaw-tag-definitions.md prose -- differs from old strict < exit in _is_result_changing"
  - "user_result retained in _build_tags and classify_game_flaws signatures -- _is_unpunished (lucky-escape end-of-game rule) still requires it even though the impact branch no longer reads it"
  - "Downstream files (library_repository.py, library_service.py, routers/library.py) NOT updated in this plan -- FlawTag Literal cascade causes ty check failures across app/ until plans 110-02+ complete; ty check scoped to modified files for this plan"

patterns-established:
  - "_classify_impact: standalone pure function with no user_result arg -- outcome-independent by construction"
  - "Impact tag appended via single _classify_impact call in _build_tags (replaces two separate conditional appends)"

requirements-completed: [SC-1, SC-2]

# Metrics
duration: 12min
completed: 2026-06-07
---

# Phase 110 Plan 01: Flaw-Tag Core Rebuild Summary

**Outcome-independent impact classifier (_classify_impact) with reversed/squandered two-rung ladder, renamed tempo tags (hasty/unrushed), new threshold constants, and pinned boundary tests (70/30, 85/60, 78->45 gap, most-severe-wins, outcome-independence)**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-07T20:08:38Z
- **Completed:** 2026-06-07T20:20:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Deleted `_is_result_changing` and its `RESULT_WIN_THRESHOLD`/`RESULT_DRAW_THRESHOLD` constants; replaced with outcome-independent `_classify_impact` using `>=` entry / `<=` exit boundaries
- Added three new constants: `WINNING_LINE_ES=0.70`, `LOSING_LINE_ES=0.30`, `SQUANDERED_EXIT_ES=0.60`; updated `FROM_WINNING_ES` comment to reflect squandered-entry role
- Renamed `FlawTag` and `TempoTag` Literal members throughout: `while-ahead`→`reversed`, `result-changing`→`squandered`, `impatient`→`hasty`, `considered`→`unrushed`
- Rebuilt `_build_tags` impact branch: single `_classify_impact` call appends at most one tag; `user_result` retained for `_is_unpunished`
- Added `TestImpactLadder` class (8 tests) covering all required boundaries plus outcome-independence; updated `TestTempoTags` and `TestConstants` for new names; 84 tests total pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Churn constants + rename Literals + add _classify_impact, rebuild _build_tags ladder** - `0fbdab0c` (feat)
2. **Task 2: Rewrite/extend test_flaws_service.py -- TestImpactLadder + renamed tempo + TestConstants** - `313c07ce` (test)

## Files Created/Modified
- `app/services/flaws_service.py` - New constants, renamed Literals, _classify_impact helper, updated _build_tags
- `tests/services/test_flaws_service.py` - TestImpactLadder, renamed tempo/constant tests, removed old impact tests

## Decisions Made
- Inclusive exit boundary `<=` (not strict `<`) per flaw-tag-definitions.md prose "or below" -- differs from the old `_is_result_changing` which used strict `<` exit. Documented at the `_classify_impact` docstring.
- `user_result` kept in `_build_tags` and `classify_game_flaws` signatures: even though the impact branch no longer reads it, `_is_unpunished` (lucky-escape end-of-game rule) still requires it. Removing it would silently break lucky-escape detection.

## Deviations from Plan

### Known Pending (Not Auto-fixed)

**1. [Scope Limitation] `uv run ty check app/` fails on downstream files**
- **Found during:** Task 1 verification
- **Issue:** Changing `FlawTag` and `TempoTag` Literals in `flaws_service.py` causes cascading type errors in `library_repository.py`, `library_service.py`, and `routers/library.py` which still reference old tag string literals (`"while-ahead"`, `"result-changing"`, `"impatient"`, `"considered"`) and the `GameFlaw` model still has `is_while_ahead`/`is_result_changing` columns. A full model change requires the plan 110-02 migration.
- **Why not fixed:** Fixing requires updating model columns + migration (plan 110-02 scope), library_repository/service/router tag names (plan 110-02/110-03 scope), and would have left the test suite broken without the migration. Applying partial fixes to downstream files without the matching DB migration would break the ~50 tests that exercise the `game_flaws` table.
- **Resolution:** `ty check app/services/flaws_service.py` passes. Full `ty check app/` passes once plans 110-02 through 110-07 complete. This is an expected intermediate state in a multi-plan phase.

---

**Total deviations:** 1 known-pending (scope boundary)
**Impact on plan:** The two in-scope files are complete and correct. The ty check gap is inherent to a multi-plan phase where the Literal type source-of-truth changes first.

## Issues Encountered
- `uv run ty check app/` acceptance criterion cannot pass within plan 110-01 scope alone due to cascading `FlawTag` Literal type errors in downstream files. Scoped resolution to `app/services/flaws_service.py` only; full `app/` will pass after phase 110 completes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 110-02 can proceed: `FlawTag`/`TempoTag` Literal names are now authoritative in `flaws_service.py`
- `_classify_impact` is callable and tested; `game_flaws_repository.py` write path and model can be updated in 110-02
- The 84 `test_flaws_service.py` tests are the regression gate for the new taxonomy

## Threat Flags
None - pure in-process classifier refactor over already-stored ES floats. No new input surface.

## Self-Check: PASSED
- `app/services/flaws_service.py` exists and contains `_classify_impact`: FOUND
- `tests/services/test_flaws_service.py` exists and contains `TestImpactLadder`: FOUND
- Task 1 commit `0fbdab0c`: FOUND
- Task 2 commit `313c07ce`: FOUND
- 84 tests pass, 0 failures

---
*Phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool*
*Completed: 2026-06-07*
