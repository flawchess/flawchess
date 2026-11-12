---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 01
subsystem: engine-data-repair
tags: [stockfish, python-chess, root_moves, operator-script, postgres, guarded-update]

requires:
  - phase: quick 261112-j47
    provides: fixed engine wrapper (_select_final_infos) the re-search relies on
  - phase: quick 261112-k56
    provides: CACHED_PV_MIN_PLIES usable-pv rule
provides:
  - root_moves keyword through the fixed EnginePool wrapper (D-01)
  - scripts/repair_short_lines.py repair subcommand (S1, S3, D-01, D-02, D-04, D-07, D-10, D-13)
affects: [252-02, 252-06, 252-07, phase-250-prod-backfill]

actuals:
  tokens: 23600
  tasks: 3
  commits: 4
plan_head_before: bae07baac2b2e4047a323b7e4fd3ab6cae51c367
plan_head_after: b0266f2fd0ddf73ffc048beecca1c8a25d7a0174

tech-stack:
  added: []
  patterns:
    - "read session -> close -> engine gather with no session -> short write session (per-game advisory locks, ascending id, guarded batched UPDATE via unnest arrays)"
    - "state files typed Mapping[str, int | list[int]] so no pv/best_move can be persisted (no undo log)"

key-files:
  created:
    - scripts/repair_short_lines.py
    - tests/scripts/test_repair_short_lines.py
  modified:
    - app/services/engine.py
    - tests/services/engine_fakes.py
    - tests/services/test_engine_bound_lines.py
    - tests/services/test_engine_nodes.py
    - tests/services/test_engine.py

key-decisions:
  - "Guarded UPDATE binds 8 arrays through unnest() instead of a VALUES list with per-row binds: fixed parameter count, no risk of asyncpg's 32767-parameter limit on large batches; same IS NOT DISTINCT FROM guard and CAST convention"
  - "--scope lane uses EXISTS on benchmark_selection (armed, FULL_ANALYSIS_TRANCHES) instead of a JOIN so a game selected under two tranches is listed once"
  - "Connection and commit-latency monitoring is enabled only when the script owns its engine (real target) and not in dry runs; an injected test session shares Postgres with other xdist workers"
  - "The latency gate compares the first 5 commits with the last 5 and is silent until more than 5 commits exist"
  - "The work list is frozen at the first run of a (db, scope), dry runs included; delete the worklist file to refreeze"

patterns-established:
  - "Strictly-above gates: evaluate_repair_gates returns every gate value next to its threshold; IMMEDIATE_GATES stop a run after every batch, throughput/still-short gates are checked every GATE_CHECK_EVERY_BATCHES batches and at the pilot end"

requirements-completed: [D-01, D-02, D-04, D-07, D-08, D-10, D-13]

coverage:
  - id: D1
    description: "root_moves threaded keyword-only (default None) through _collect_analysis_infos, EnginePool._acquire_and_analyse and evaluate_nodes_with_pv; existing callers send what they sent before"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_engine_bound_lines.py#test_root_moves_reach_analysis_and_default_is_none"
        status: pass
      - kind: integration
        ref: "tests/services/test_engine_nodes.py#TestRealEnginePinnedSearch"
        status: pass
    human_judgment: false
  - id: D2
    description: "repair subcommand selects short stored lines (S1) and [] opening sentinels (S3), skips legit-short and guest games, re-searches pinned (D-01) or freely (D-02), writes with a guarded batched UPDATE"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-10 gates as named constants, pilot slice, failed-batch and mismatch stop, dry-run, lane scope, written report"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_pilot_whose_repair_does_not_stick_exits_3_with_stop_in_the_report"
        status: pass
      - kind: other
        ref: "uv run python scripts/repair_short_lines.py repair --db dev --dry-run --limit-games 20 --engines 2 --report-dir temp/line-repair/smoke"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-11-12
status: complete
---

# Phase 252 Plan 01: Line repair script and pinned re-search Summary

**`scripts/repair_short_lines.py repair` re-searches short stored pv lines through the fixed engine wrapper pinned to the stored best move (new `root_moves` keyword), writes them with a guarded batched UPDATE, and stops itself on every D-10 gate with a written report.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 (tracer, selection/write rules, gates)
- **Files modified:** 7 (2 new)

## Accomplishments

- `EnginePool.evaluate_nodes_with_pv(board, timeout_s=..., root_moves=[pin])`: pinned search proven against real Stockfish 18 (pv starts with the pin, at least 3 plies).
- Repair pipeline: selector A (short non-mate node0 rows of flaw lines) plus selector B (`[]` sentinels at node0 ply <= DEDUP_MAX_PLY with no usable pv), legit-short classification via `is_game_over(claim_draw=True)` on the game's move stack, D-01 pin / D-02 free search with an explicit `write_best` flag, `pin_mismatch` and not-longer results never written, failed rows retried once, guard skips classified (`game_deleted`, `concurrently_changed`, `row_count_mismatch`).
- Run mechanics: frozen newest-first work list and persisted cursor under `temp/line-repair/`, `--pilot` (first ceil(1%)), `--dry-run`, `--scope lane`, `--throttle-ms`, cooperative SIGTERM, Sentry capture of a failed batch, single-connection pool, markdown report with all gates.
- Dev dry-run smoke (20 games, 2 engines): 26 rows searched, 0 written, gates PASS, projected 0.09 days for the whole dev work list.

## Task Commits

1. **Task 1: Tracer, pinned re-search through the fixed wrapper** - `c464a226e` (feat)
2. **Task 2: Selection completeness and the D-01/D-02 write rules** - `2a09ab97a` (feat)
3. **Task 3: D-10 gates, pilot slice, lane scope and run report** - `b206885b4` (feat)
4. **Follow-up: timeout spy accepts root_moves** - `b0266f2fd` (fix)

## Files Created/Modified

- `app/services/engine.py` - `root_moves` threaded through the wrapper (docstrings updated)
- `scripts/repair_short_lines.py` - the operator script
- `tests/scripts/test_repair_short_lines.py` - 31 tests (DB integration with a fake searcher, one real-Stockfish tracer, pure gate tests)
- `tests/services/engine_fakes.py` - `ScriptedAnalysisProtocol.root_moves_calls`
- `tests/services/test_engine_bound_lines.py`, `tests/services/test_engine_nodes.py` - root_moves tests (unit and real engine)
- `tests/services/test_engine.py` - timeout spy signature

## Decisions Made

See `key-decisions` above. Notable for the later plans: the dry run also freezes the work list (delete `temp/line-repair/<db>-<scope>-worklist.json` to refreeze), and the connection/latency monitor is active only on real targets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing EnginePool timeout spy rejected the new keyword**
- **Found during:** Task 3 verification (a broader `tests/services/test_engine.py` run with `-n 4`)
- **Issue:** `TestNodesTimeoutOverride._make_timeout_spy` mirrors `_acquire_and_analyse`'s signature; `evaluate_nodes_with_pv` now forwards `root_moves=None`, so two tests failed with `TypeError`. The Task 1 targeted runs did not include this file.
- **Fix:** added `root_moves: Sequence[chess.Move] | None = None` to the spy.
- **Files modified:** `tests/services/test_engine.py` (not in the plan's `files_modified`)
- **Commit:** `b0266f2fd`

### Plan-form deviations (intent met)

- `test_root_moves_reach_analysis_and_default_is_none` was written in Task 1 (with the engine change) instead of Task 2; same file, same test.
- The guarded UPDATE uses `unnest()` array binds rather than a VALUES list with per-row binds (see key-decisions); `--scope lane` uses EXISTS rather than JOIN.
- Task 2 is marked `tdd="true"`: the tests were written together with the implementation, not strictly RED first. The D-02 illegal-overwrite fix was mutation-checked afterwards: removing the `board.is_legal(move)` check in `pick_pin` made `test_d02_illegal_best_move_searches_freely_and_overwrites_best_move` and `test_pick_pin_returns_only_a_legal_stored_move` fail (2 failed, 18 passed); restored, 20 passed.
- Two extra test seams beyond the plan's `_after_read_hook`: `_before_commit_hook` (used to raise a DB error inside the write session) and `stats_out` (so tests read counters).

**Total deviations:** 1 auto-fixed bug, 4 plan-form notes. **Impact:** none on scope or behavior.

## Verification Results

- `uv run pytest tests/scripts/test_repair_short_lines.py tests/services/test_engine_bound_lines.py tests/services/test_engine_nodes.py tests/services/test_engine.py -q`: 76 passed. Also `tests/services -n auto -k "engine or drain or pool"`: 452 passed, 5 skipped.
- `uv run ty check app/ tests/ scripts/`: All checks passed. `uv run ruff check`/`format`: clean.
- `scripts/check_function_size.py scripts/repair_short_lines.py --fail-over-depth 4` and `app/`: no breaches.
- `grep -c root_moves app/services/engine.py` = 9; seven D-10 constants present with values 0.03, 10.0, 8.0, 0.02, 0.01, 10, 3.0.
- Dev dry-run smoke exited 0, printed `gates: PASS (...)`, report under `temp/line-repair/smoke/`; `git status --porcelain reports/` empty.
- Not run here (orchestrator owns it): full backend suite, serial CI-style run, frontend gate.

## Issues Encountered

None open.

## Known Stubs

None.

## Threat Flags

None. T-252-01..03 mitigations are implemented: `--db` is a required Literal and the banner prints host:port/database; `--scope lane` is refused outside benchmark; guarded UPDATE, Python legality check before pinning, pin_mismatch never written, write only a strictly longer pv; single-connection pool, short sessions, `--throttle-ms`, connection and commit-latency gates.

## Next Phase Readiness

Plans 06 and 07 can run the pilot and full runs from the orchestrator (`setsid nohup`). Operator notes: stop the box's worker first (D-08); the prod pilot should be a real (not dry) run only after the dry-run preview is reviewed; the dry run freezes the work list.

## Self-Check: PASSED

- `scripts/repair_short_lines.py`, `tests/scripts/test_repair_short_lines.py`: FOUND
- Commits `c464a226e`, `2a09ab97a`, `b206885b4`, `b0266f2fd`: FOUND on the branch
