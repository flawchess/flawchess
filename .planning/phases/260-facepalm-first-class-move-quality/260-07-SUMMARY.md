---
phase: 260-facepalm-first-class-move-quality
plan: 07
subsystem: api
tags: [fastapi, sqlalchemy, library, facepalm, changelog, pytest]

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-01: severity=facepalm clause (reads build_flaw_filter_clauses facepalm_score); 260-03: frontend sends no range params"
provides:
  - "min_facepalm_pct / max_facepalm_pct removed from /library/games and /library/flaws, library_service, apply_game_filters and every library_repository signature"
  - "_facepalm_clause, facepalm_range_active, FACEPALM_PCT_MIN / MAX and _FACEPALM_PCT_SCALE deleted"
  - "Stale clients that still send the range params get 200 and the unfiltered result"
  - "Stats-cut pin test parses FACEPALM_HIGH_CUTOFF from frontend/src/lib/facepalm.ts"
  - "CHANGELOG [Unreleased] Changed and Removed bullets for the phase"
affects: [phase-260-merge, uat]

requirements-completed: [D-13, D-15, D-16, D-21, D-22, D-23, D-25]

actuals:
  tokens: 16900
  tasks: 3
  commits: 3
plan_head_before: aab1db098955fde086be4b98e1a98eecbe10fb9c
plan_head_after: cab6427274e32d01e21fdf8cee6dac5106b950bd

tech-stack:
  added: []
  patterns:
    - "A backend test reads a frontend constant by regex (parity-test precedent) so the two cut values cannot drift"

key-files:
  created: []
  modified:
    - app/routers/library.py
    - app/services/library_service.py
    - app/repositories/query_utils.py
    - app/repositories/library_repository.py
    - app/services/blunder_check_rules.py
    - frontend/src/lib/facepalm.ts
    - tests/test_library_router.py
    - tests/test_library_repository.py
    - tests/repositories/test_library_repository.py
    - tests/test_query_utils.py
    - tests/services/test_facepalm_score.py
    - CHANGELOG.md

key-decisions:
  - "build_flaw_filter_clauses keeps facepalm_score (the severity clause's bound expression) and query_flaws still passes its chip"
  - "Truth tables of plan 01 already pin the opponent-above-cut and unscored cases on both consumers, so only the L-01 regression and the single-flaw-row AND were rewritten onto severity=facepalm"

coverage:
  - id: D1
    description: "No backend signature carries the facepalm range; the severity clause still reads the bound score"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/test_library_router.py#TestFlawSeverityFacepalmEndToEnd"
        status: pass
      - kind: command
        ref: "uv run ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4"
        status: pass
    human_judgment: false
  - id: D2
    description: "A stale client sending the removed range params gets 200 and the unfiltered result on both list endpoints"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/test_library_router.py#test_removed_facepalm_range_params_are_ignored"
        status: pass
    human_judgment: false
  - id: D3
    description: "Behaviours worth keeping (L-01 opponent regression, single-flaw-row AND) pinned on severity=facepalm; the stats-cut pin reads the frontend cut"
    requirement: "D-21"
    verification:
      - kind: unit
        ref: "tests/test_library_repository.py#TestFacepalmGamesFilter"
        status: pass
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_facepalm_stats_min_is_the_frontend_facepalm_cut"
        status: pass
    human_judgment: false
  - id: D4
    description: "Final visual UAT and desktop layout measurement on the rebased branch"
    requirement: "D-22, D-15, D-16, D-25"
    human_judgment: true
    rationale: "Colours, layout and the end-to-end split after the refit need the owner's eyes and browser measurement; listed below as unverified"

duration: 25min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 07: Remove the backend facepalm range and close the phase Summary

**The `min_facepalm_pct` / `max_facepalm_pct` chain is deleted from router to repository, stale clients still get 200, the cut pin reads the frontend constant, and the full pre-merge gate is green.**

## Performance

- **Duration:** about 25 min (Task 1 resumed from an interrupted run)
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 12 modified

## Accomplishments

- Router, service, `apply_game_filters` and the repository lost the range params; the EXISTS gate is now `flaw_severity or flaw_tags or tactic_active`. `_facepalm_clause`, `facepalm_range_active`, `FACEPALM_PCT_MIN` / `FACEPALM_PCT_MAX` and `_FACEPALM_PCT_SCALE` are gone. `facepalm_score` stays on `build_flaw_filter_clauses` and the chip comment in `query_flaws` now says "the chip and the severity clause".
- `test_removed_facepalm_range_params_are_ignored` proves a stale client gets 200 and the same `matched_count` on `/api/library/flaws` and `/api/library/games`.
- Range-only tests deleted (clause-builder class, `TestFacepalmGate`, the range cases of `TestFacepalmRangeQueryFlaws`, the router range classes). Kept and rewritten onto `severity=["facepalm"]`: the L-01 opponent regression (Games and Flaws) and the single-flaw-row AND with another family; seeds sit at `FACEPALM_STATS_MIN` plus or minus `SEED_FACEPALM_MARGIN`. `test_item_carries_expression_score_or_none` kept (class renamed `TestFacepalmChipQueryFlaws`).
- The stats-cut pin parses `export const FACEPALM_HIGH_CUTOFF = <int>;` from `frontend/src/lib/facepalm.ts`; mutation check (cut set to 71) fails the test, then restored. Preset wording removed from the `FACEPALM_STATS_MIN` and `FACEPALM_HIGH_CUTOFF` comments (declaration line byte-identical).
- CHANGELOG: five `### Changed` bullets and a `### Removed` subsection under `[Unreleased]`; two Phase 259 bullets that named the Facepalm filter now say "Facepalm tag" (noun phrase only).

## Task Commits

1. **Task 1: Tracer, range params gone from router to repository** - `0ed7a9072` (refactor)
2. **Task 2: Range tests rewritten, cut pin reads the frontend constant** - `9c234ab68` (test)
3. **Task 3: CHANGELOG bullets** - `cab642727` (docs)

Task 1 was resumed from an interrupted run: a previous executor died on an infrastructure error with 5 files edited and nothing committed. Every hunk was reviewed against the plan; the app-side deletions were complete and correct and the router-test rewrite matched the plan, so they were kept as they were. The Games-range tests deleted from `tests/test_library_router.py` are covered by plan 01's `TestFlawSeverityFacepalmEndToEnd` (facepalm, blunder, no-severity, Games tab, opponent never listed), so no behaviour pin was lost.

## Deviations from Plan

**1. [Plan-internal inconsistency] Acceptance grep for `min_facepalm_pct` in tests**
- **Found during:** Task 2
- **Issue:** the Task 2 acceptance command counts non-comment `min_facepalm_pct` occurrences across the five test files and expects 0, but Task 1 requires `test_removed_facepalm_range_params_are_ignored` in `tests/test_library_router.py` to send exactly that param. The count is 1 (the stale-client dict in that one test).
- **Fix:** kept the literal; building the name from fragments only to dodge the grep would hide the test's intent. No other occurrence remains in app/ or tests/.

**Total deviations:** 1 (acceptance-criterion conflict, no behaviour impact).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-260-13 mitigated (stale params ignored, test proves 200 and unchanged result); T-260-14 mitigated (plan 01 truth tables plus the rewritten L-01 regression pass in the full suite).

## Verification

- `uv run pytest -n auto -x`: 6858 passed, 8 skipped, exit 0.
- `uv run ruff format app/ tests/ scripts/ analysis/`: no changes; `uv run ruff check . --fix`, `uv run ty check app/ tests/ scripts/`, `uv run --project analysis --with ty ty check analysis/`, `scripts/check_function_size.py app/ --fail-over-depth 4`: all clean.
- Frontend: `npm run lint`, `npm run build`, `npm run knip` exit 0; `npm test -- --run` 6777 passed (381 files).
- Acceptance greps: all pass except the conflict noted above; CHANGELOG checks (`Facepalm, Blunder and Mistake` 1, `### Removed` 1, "pawn" 0).

## Unverified, left for the orchestrator before the squash-merge

- Serial backend suite (`uv run pytest -x`) in this worktree, to surface isolation bugs `-n auto` hides.
- Final visual UAT (D-22): Library Games tab desktop and mobile, Flaws tab, /analysis; card with 8 rows, Facepalm last with "???", ring behaviour per tag, dark red dots and "You · Facepalm" tooltip, old `?severity=blunder` bookmark still loads.
- Desktop layout measurement (D-15, D-16, D-25) at 1280px or wider: miniboard height equals `DESKTOP_BOARD_SIZE`, miniboard and MoveStats card bottoms within 1px, chart taller, tags card height kept; repeat on a card without tags.

## Next Phase Readiness

All seven plans are committed. After the UAT and serial suite above the phase is ready for the squash-merge to main.

## Self-Check: PASSED

Commits 0ed7a9072, 9c234ab68 and cab642727 are ancestors of HEAD; `grep` confirms no `_facepalm_clause`, `facepalm_range_active`, `FACEPALM_PCT_MIN/MAX` or `_FACEPALM_PCT_SCALE` in app/ or tests/.
