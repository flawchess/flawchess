---
phase: 28-engine-analysis-import
plan: 03
subsystem: backend
tags: [import, admin-script, engine-analysis, lichess, chess.com, argparse, testing]

dependency_graph:
  requires:
    - phase: 28-01
      provides: engine-analysis-schema (eval_cp/eval_mate/white_accuracy/black_accuracy columns)
  provides:
    - admin-reimport-script
    - eval-extraction-tests
  affects: [import_pipeline, backfill_workflow]

tech_stack:
  added: []
  patterns: [argparse-mutually-exclusive, module-level-imports-for-testability, mock-patch-async]

key_files:
  created:
    - scripts/reimport_games.py
    - tests/test_reimport.py
  modified: []

key-decisions:
  - "get_job imported at module level (not inside function) so tests can patch scripts.reimport_games.get_job"
  - "reimport_user() uses existing create_job + run_import pipeline — no custom platform calls"
  - "Eval extraction tests use python-chess node.eval() directly — verifies extraction logic without needing 28-02 wired"
  - "get_platform_jobs_for_user queries import_jobs table directly (no new repository function) — simpler for a one-off admin script"

patterns-established:
  - "Admin scripts: module-level app.* imports with sys.path.insert at top; asyncio.run(main()) at bottom"
  - "Testability: all external dependencies imported at module level, never inside functions"

requirements-completed: [ENGINE-01, ENGINE-02, ENGINE-03]

metrics:
  duration: 15min
  completed: "2026-03-25"
  tasks_completed: 1
  files_changed: 2
---

# Phase 28 Plan 03: Admin Re-Import Script Summary

**Admin re-import script with --user-id/--all/--yes flags that deletes and re-imports games via the updated pipeline, plus 13 tests covering CLI parsing, lichess %eval extraction logic, and re-import orchestration flow.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-25T21:37:32Z
- **Completed:** 2026-03-25T21:52:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- `scripts/reimport_games.py`: admin CLI to delete + re-import games for one user or all users, using the updated import pipeline that now extracts eval/accuracy data
- `tests/test_reimport.py`: 13 tests — argument parsing (6), python-chess eval extraction logic (4), and re-import orchestration flow (3)
- Confirmed lichess `%eval` PGN annotations parse correctly via `node.eval().white().score()` and `.mate()` — the same extraction logic plan 28-02 wires into `_flush_batch`

## Task Commits

1. **Task 1: Create admin re-import script with integration test** - `d600d9b` (feat)

## Files Created/Modified

- `scripts/reimport_games.py` — Admin re-import script with `--user-id N`, `--all`, `--yes` flags; queries import jobs to discover platforms, deletes games, calls `run_import` per platform, reports per-user errors and final summary
- `tests/test_reimport.py` — 13 tests: `TestParseArgs` (6), `TestEvalExtraction` (4), `TestReimportFlow` (3)

## Decisions Made

- `get_job` imported at module level so `patch("scripts.reimport_games.get_job")` works in tests — local function imports are not patchable via the module path
- Re-import uses `create_job + run_import` (existing pipeline) rather than calling platform clients directly — avoids duplicating import logic
- Eval extraction tests are separate from the DB integration tests — they verify the python-chess extraction API directly so they pass before plan 28-02 wires evals into `_flush_batch`
- `get_platform_jobs_for_user` queries `import_jobs` directly with SQLAlchemy `select` — no new repository function needed for a one-off admin script

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Initial test used local import `from app.services.import_service import get_job` inside `reimport_user()`, which made it unpatchable via `scripts.reimport_games.get_job`. Fixed by moving the import to module level (Rule 1: auto-fix bug) — test passed after the fix.

## Known Stubs

None — the re-import script correctly invokes the full import pipeline. The eval/accuracy population itself depends on plan 28-02 wiring eval extraction into `_flush_batch`, which runs in parallel.

## Self-Check

- [x] `scripts/reimport_games.py` exists
- [x] Contains `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`
- [x] Contains `_BATCH_SIZE = 10`
- [x] Contains `--user-id` argument
- [x] Contains `--all` argument
- [x] Contains `--yes` / `-y` argument
- [x] Contains `delete_all_games_for_user` call
- [x] Contains `asyncio.run(main())` at bottom
- [x] Imports from `app.repositories.game_repository`
- [x] `tests/test_reimport.py` exists with argument parsing tests
- [x] `tests/test_reimport.py` contains eval_cp population verification (TestEvalExtraction class)
- [x] `uv run pytest tests/test_reimport.py -x` exits 0 — 13/13 passed
- [x] `uv run ruff check scripts/reimport_games.py` exits 0
- [x] Commit d600d9b exists

## Self-Check: PASSED

## Next Phase Readiness

- Re-import script is ready for admin use after Phase 28 ships
- Plan 28-02 (eval extraction wiring into `_flush_batch`) runs in parallel — once merged, re-import will populate `eval_cp`/`eval_mate`/`white_accuracy`/`black_accuracy` for backfilled games

---
*Phase: 28-engine-analysis-import*
*Completed: 2026-03-25*
