---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
plan: "03"
subsystem: api
tags: [flaw-tags, library, game_flaws, taxonomy, backfill]

requires:
  - phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
    plan: "01"
    provides: "rebuilt flaw classifier (reversed/squandered ladder) + renamed tempo constants"
  - phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
    plan: "02"
    provides: "Alembic alter migration dropping is_while_ahead/is_result_changing, adding is_reversed/is_squandered"

provides:
  - "TagDistribution schema exposes reversed_rate and squandered_rate (not while_ahead_rate/result_changing_rate)"
  - "FlawTagFilter Literal at the HTTP boundary uses renamed members: reversed, squandered, hasty, unrushed"
  - "library_repository EXISTS predicates and 12-tuple aggregate reference is_reversed/is_squandered"
  - "library_service _CHIP_ORDER/_build_tag_distribution/_curate_chips_from_rows use new column/tag names"
  - "All six affected backend test files updated to new taxonomy; 108 targeted tests pass"
  - "Dev users 28 & 44 game_flaws rows repopulated via backfill_flaws.py (1620 rows each)"

affects:
  - 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
  - frontend plans consuming TagDistribution.reversed_rate / squandered_rate

tech-stack:
  added: []
  patterns:
    - "TagDistribution rate fields mirror schema: reversed_rate/squandered_rate computed as count/total over is_reversed/is_squandered"
    - "FlawTagFilter Literal at HTTP boundary auto-422s unknown tag names — rename preserves that invariant"

key-files:
  created: []
  modified:
    - app/schemas/library.py
    - app/routers/library.py
    - app/repositories/query_utils.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/services/stats_service.py
    - tests/test_library_repository.py
    - tests/test_library_router.py
    - tests/test_flaw_predicate.py
    - tests/services/test_library_service.py
    - tests/services/test_eval_chart_service.py
    - tests/test_backfill_flaws.py

key-decisions:
  - "TagDistribution drops while_ahead_rate and result_changing_rate; adds reversed_rate and squandered_rate (D-03)"
  - "FlawTagFilter Literal renames: while-ahead->reversed, result-changing->squandered, impatient->hasty, considered->unrushed"
  - "Impact tags in _USER_FRAMED_TAGS left unchanged (miss, lucky-escape only) — impact is mover-framed, not perspective-dependent"
  - "stats_service L43 prose 'to be considered' preserved as documented false positive (Pitfall 3)"
  - "Dev backfill limited to users 28 & 44 — other dev users intentionally left stale (v1.24 unshipped)"

patterns-established:
  - "All tag literal renames propagated through schema -> router -> repository -> service -> tests atomically per plan"

requirements-completed: [SC-1, SC-3, SC-4]

duration: ~90min (Tasks 1-3 by prior executor; Task 4 backfill by orchestrator)
completed: 2026-06-07
---

# Phase 110 Plan 03: API-Layer Propagation + Dev Backfill Summary

**Propagated impact/tempo tag renames through the full API layer (schemas, router Literal, repository aggregation, service distribution) and repopulated dev users 28 & 44 via backfill_flaws.py (1620 rows each, 59 reversed / 43 squandered per user)**

## Performance

- **Duration:** ~90 min (Tasks 1-3 executed by prior executor; Task 4 completed by orchestrator)
- **Started:** 2026-06-07T21:00:00Z
- **Completed:** 2026-06-07
- **Tasks:** 4
- **Files modified:** 12

## Accomplishments

- Swapped `TagDistribution` rate fields: `while_ahead_rate`/`result_changing_rate` removed, `reversed_rate`/`squandered_rate` added with matching style and docstrings
- Renamed `FlawTagFilter` Literal members at the HTTP boundary (`while-ahead`→`reversed`, `result-changing`→`squandered`, `impatient`→`hasty`, `considered`→`unrushed`); FastAPI 422-rejection of unknown tags preserved automatically
- Updated `library_repository.py` EXISTS predicates, 12-tuple aggregate, and `_reconstruct_tags` mapping to reference `is_reversed`/`is_squandered`; tempo names updated to `hasty`/`unrushed`
- Updated `library_service.py` `_CHIP_ORDER`, `_build_tag_distribution`, `_curate_chips_from_rows`, and the opponent-flip docstring; `_USER_FRAMED_TAGS` left as `{"miss", "lucky-escape"}` (impact is mover-framed, not perspective-dependent)
- Stats_service false-positive prose ("to be considered" at L43) correctly left untouched
- All six backend test files updated; 108 targeted tests pass with no deprecated impact/tempo references
- Dev backfill executed for users 28 & 44: 1620 flaw rows written per user across 476 distinct games; 59 `is_reversed=true`, 43 `is_squandered=true` per user (identical counts expected — same underlying game positions, deterministic classifier); `is_while_ahead`/`is_result_changing` columns absent (dropped in Plan 02 migration); SC-4 satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: Swap TagDistribution rate fields + rename FlawTagFilter Literal** - `2886fc9e` (feat)
2. **Task 2: Update library_repository/service tag aggregation to new column/tag names** - `63e28076` (feat)
3. **Task 3: Rename deprecated impact/tempo tag references across six backend test files** - `60782836` (test)
4. **Task 4: Dev-only backfill users 28 & 44** - completed by orchestrator (manual DB operation, no code commit)

## Files Created/Modified

- `app/schemas/library.py` — `TagDistribution`: removed `while_ahead_rate`/`result_changing_rate`, added `reversed_rate`/`squandered_rate`
- `app/routers/library.py` — `FlawTagFilter` Literal renamed to `reversed`/`squandered`/`hasty`/`unrushed`
- `app/repositories/query_utils.py` — docstring example updated from `result-changing` to `reversed` (comment only)
- `app/repositories/library_repository.py` — EXISTS predicates, 12-tuple aggregate, `_reconstruct_tags` use `is_reversed`/`is_squandered` and `hasty`/`unrushed`
- `app/services/library_service.py` — `_CHIP_ORDER`, `_build_tag_distribution`, `_curate_chips_from_rows`, `_TEMPO_TAGS`, opponent-flip docstring all updated
- `app/services/stats_service.py` — genuine tag-literal occurrences renamed; prose false positive preserved
- `tests/test_library_repository.py` — deprecated tag/column/rate references renamed
- `tests/test_library_router.py` — deprecated tag/column/rate references renamed
- `tests/test_flaw_predicate.py` — deprecated tag/column/rate references renamed; ES values updated for new impact ladder thresholds
- `tests/services/test_library_service.py` — deprecated tag/column/rate references renamed
- `tests/services/test_eval_chart_service.py` — deprecated tag/column/rate references renamed
- `tests/test_backfill_flaws.py` — deprecated tag/column/rate references renamed

## Decisions Made

- `_USER_FRAMED_TAGS` in `library_service.py` does NOT include impact tags (`reversed`/`squandered`) because impact is already mover-framed (outcome-independent relative to the moving side); only `miss` and `lucky-escape` require the perspective flip for the opponent view
- Impact tags confirmed perspective-independent: the opponent-flip docstring updated accordingly (old comment said "while-ahead / result-changing are mover-relative" — now documents the outcome-independent property)
- Dev backfill limited to users 28 & 44 by plan design; other dev users intentionally left stale since v1.24 is not yet shipped to production

## Deviations from Plan

None — plan executed exactly as written. The stats_service false-positive prose ("to be considered" at L43) was correctly identified and preserved per Pitfall 3 in the research notes.

## Issues Encountered

None during Tasks 1-3. Task 4 (dev backfill) required a checkpoint:human-action because it mutates the live dev DB outside the isolated test harness — this is expected project-norm behavior (no dev DB reset in plans).

## Backfill Results (Task 4)

- User 28: 1620 game_flaws rows written, 0 errors, 476 distinct games, 59 `is_reversed=true`, 43 `is_squandered=true`
- User 44: 1620 game_flaws rows written, 0 errors, 476 distinct games, 59 `is_reversed=true`, 43 `is_squandered=true`
- Identical counts expected: both dev users share the same 476 underlying chess games (same `platform_game_id`, imported under two accounts); the classifier is deterministic and outcome-independent
- Old columns `is_while_ahead`/`is_result_changing` are absent (dropped in Plan 02 migration)
- SC-4 satisfied

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plans 04-07 (frontend layer) can now consume `TagDistribution.reversed_rate`/`squandered_rate` and the renamed `FlawTagFilter` Literal members without any further backend changes
- Dev DB is ready for frontend development and testing (users 28 & 44 repopulated)
- SC-1 (grep-clean) and SC-3 (full suite + ty green) satisfied for the backend layer; SC-1 will be fully satisfied once the frontend plans complete

---
*Phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool*
*Completed: 2026-06-07*

## Self-Check: PASSED

- Task commits exist: `2886fc9e`, `63e28076`, `60782836` — verified via `git log --oneline`
- Modified files confirmed in task commit diffs (library.py, library_repository.py, library_service.py, stats_service.py, query_utils.py, all six test files)
- Task 4 backfill completed by orchestrator — 1620 rows per user confirmed via MCP spot-check
