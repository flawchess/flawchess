---
phase: 150-consolidate-write-path
plan: 05
subsystem: api
tags: [sqlalchemy-async, eval-pipeline, refactor, module-split, circular-import]

requires:
  - phase: 150-consolidate-write-path
    provides: "apply_completion_decision (150-03) and the 4-way diff/upsert _classify_and_fill_oracle (150-04) — both physically relocated (not re-exported) into eval_apply.py by this plan"
provides:
  - "app/services/eval_apply.py — new shared write-path module exposing apply_full_eval(write_session, ..., update_opening_cache=..., record_heartbeat=...), consumed by both eval_drain.py::_full_drain_tick and eval_remote.py::_apply_atomic_submit"
  - "app/services/eval_entry.py — new entry-ply (import-time, no-shift) module holding 14 of 16 entry-lane primitives, consumed by eval_remote.py::entry_submit_eval and import_service.py"
affects: [150-06-if-any, future-eval-pipeline-changes]

tech-stack:
  added: []
  patterns:
    - "Caller-owns-session convention on apply_full_eval (mirrors apply_completion_decision): the function takes write_session as its first positional arg rather than opening/committing its own, so per-module async_session_maker test monkeypatches keep routing correctly regardless of which module a shared function is physically defined in"
    - "Explicit opt-in parameters (update_opening_cache/upsert_opening_cache_fn, record_heartbeat/heartbeat_*, count_flaws_written) for behavior that differs by caller, instead of forcing identical behavior or silently extending one caller's side-effect to the other (Pitfall 4)"
    - "Backward-compat re-import: eval_drain.py imports back a superset of the symbols it physically moved out (into eval_apply.py / eval_entry.py) purely so pre-existing `from app.services.eval_drain import <symbol>` references in tests/scripts keep working unmodified — these are re-bound names (marked noqa: F401 where eval_drain's own code no longer calls them directly), not re-definitions"

key-files:
  created:
    - app/services/eval_apply.py
    - app/services/eval_entry.py
  modified:
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - app/services/import_service.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/write_path_golden_scenarios.py
    - tests/services/test_full_eval_drain.py
    - tests/services/test_eval_drain.py

key-decisions:
  - "apply_full_eval takes discrete pre-computed inputs (targets/dedup_map/engine_result_map/flaw_pv_blobs/...) rather than the router's AtomicSubmitRequest wire shape, so both _full_drain_tick's engine-gather-derived inputs and _apply_atomic_submit's worker-submitted inputs can feed the SAME function; each caller keeps its own read/gather phase (which differs structurally between the two lanes) and calls apply_full_eval only for the shared write_session body"
  - "apply_full_eval does NOT open or commit its own session — the caller does, exactly mirroring apply_completion_decision's pre-existing convention — so eval_drain.py's and eval_remote.py's own async_session_maker test patches continue to route correctly for the write phase"
  - "_build_flaw_blob_lease_positions (the tier-4 flaw-blob-only lane) was ALSO relocated to eval_apply.py, even though RESEARCH.md's R7 section marks that lane as functionally isolated from the live-submit path (D-04 isolation boundary). Reinterpreted that isolation as a semantic/behavioral property, not a file-location constraint — relocating it (unchanged, unmerged with apply_full_eval) was required to fully eliminate eval_remote.py's private-drain-import leak for the shared write path"
  - "Task 2 (entry-lane split) moved 14 of 16 entry-lane symbols to eval_entry.py, but deliberately kept _pick_pending_game_ids and _load_pgns_for_games in eval_drain.py — see Deviations for the full rationale (both open their own internal session, unlike every other entry-lane function, which takes session as a parameter)"

patterns-established:
  - "When physically relocating a function that opens its own internal AsyncSession via a module-level async_session_maker import, every existing test that monkeypatches session routing for that function's OLD module must also patch the NEW module's async_session_maker binding — module-level name bindings are per-file, not shared, unlike third-party singletons (chess.pgn, sentry_sdk) which are safely patchable from any importer"

requirements-completed: [WRITE-04]

coverage:
  - id: D1
    description: "app/services/eval_apply.py exists and exposes apply_full_eval(...), consumed by BOTH _full_drain_tick and the router's atomic-submit lane"
    requirement: "WRITE-04"
    verification:
      - kind: unit
        ref: "grep -n 'apply_full_eval' app/services/eval_drain.py app/routers/eval_remote.py (both call it)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -q (39 + 68 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Shared-write-path primitives physically MOVED (not re-exported) — no eval_drain.py <-> eval_apply.py circular import"
    requirement: "WRITE-04"
    verification:
      - kind: unit
        ref: "uv run python -c 'import app.main' (succeeds)"
        status: pass
      - kind: unit
        ref: "uv run ty check app/ tests/ (clean; would surface a cycle immediately)"
        status: pass
    human_judgment: false
  - id: D3
    description: "eval_remote.py no longer imports private (underscore-prefixed) helpers from eval_drain.py for the shared write path or entry lane, except one flagged deliberate residual (_load_pgns_for_games)"
    requirement: "WRITE-04"
    verification:
      - kind: unit
        ref: "grep -n 'from app.services.eval_drain import' app/routers/eval_remote.py -> only ENTRY_LEASE_* constants + _load_pgns_for_games remain"
        status: pass
    human_judgment: false
  - id: D4
    description: "apply_full_eval's update_opening_cache parameter defaults each caller to its pre-existing behavior (drain=True via _upsert_opening_cache, atomic-submit=False) — no silent behavior change (Pitfall 4)"
    requirement: "WRITE-04"
    verification:
      - kind: unit
        ref: "app/services/eval_drain.py _full_drain_tick passes update_opening_cache=True, upsert_opening_cache_fn=_upsert_opening_cache; app/routers/eval_remote.py's atomic-submit wrapper leaves update_opening_cache=False (default)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full backend suite green, ruff + ty clean, after both tasks"
    requirement: "WRITE-04"
    verification:
      - kind: unit
        ref: "uv run pytest -n auto -q (3162 passed, 18 skipped)"
        status: pass
      - kind: other
        ref: "uv run ruff check . && uv run ruff format --check app/ tests/ scripts/ && uv run ty check app/ tests/ (all clean)"
        status: pass
    human_judgment: false

duration: 100min
completed: 2026-07-04
status: complete
---

# Phase 150 Plan 05: Consolidate Write Path — Module Split (R7 / WRITE-04) Summary

**Physically relocated the shared write-path primitives (~1770 lines) from `eval_drain.py` into a new `app/services/eval_apply.py` exposing `apply_full_eval(...)`, consumed by both `_full_drain_tick` and the router's atomic-submit lane; then split the entry-ply (import-time) primitives into a new `app/services/eval_entry.py`. `eval_drain.py` shrank from 3188 to 1074 lines. The router's 21-symbol private-helper leak into `eval_drain.py` is gone; one narrow, deliberate residual import (`_load_pgns_for_games`) remains and is flagged below.**

## Performance

- **Duration:** ~100 min
- **Tasks:** 2 completed
- **Files created:** 2 (`app/services/eval_apply.py`, `app/services/eval_entry.py`)
- **Files modified:** 7 (`app/services/eval_drain.py`, `app/routers/eval_remote.py`, `app/services/import_service.py`, `tests/test_eval_worker_endpoints.py`, `tests/services/write_path_golden_scenarios.py`, `tests/services/test_full_eval_drain.py`, `tests/services/test_eval_drain.py`)

## Accomplishments

**Task 1 — `eval_apply.py` + kill the router import leak:**
- Physically moved (not re-exported) the shared-write-path primitives out of `eval_drain.py` into `app/services/eval_apply.py`: `_FullPlyEvalTarget`, `_collect_full_ply_targets`, `_fetch_dedup_evals`, `_resolve_full_eval`, `_post_move_eval`, the batched eval/best-move/pv/flaw-pv writers, `_apply_full_eval_results`, `apply_completion_decision` (moved from Plan 03's home), `_classify_and_fill_oracle` (moved from Plan 04's home), `_classify_with_overlay`, `_flaw_engine_plies`, `_reconstruct_pos_eval`, `_walk_pv_boards`, `_placeholder_defender_node`, `_build_line_blobs`, `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`, `_build_flaw_blob_lease_positions`, `_parse_token`, blob-assembly helpers, `_GameColorView`, `_signal_flaw_completion`, and `MAX_EVAL_ATTEMPTS`.
- New `apply_full_eval(write_session, ...)` encapsulates the shared write_session body (evals → classify/diff-upsert → optional flaws-written count → optional opening-cache fill → completion decision → optional worker heartbeat), generalized from `_apply_atomic_submit`'s original inline body so both `_full_drain_tick` and the router's atomic-submit wrapper call it.
- `eval_remote.py`'s 21-symbol private-helper import block (L81-107 pre-plan) is gone, replaced by an import from `eval_apply.py`; `_apply_atomic_submit` keeps its own read/CPU phase (unchanged) and delegates the write phase to `apply_full_eval`.
- `eval_drain.py`'s `_full_drain_tick` write-session block shrank to a single `apply_full_eval(...)` call with `update_opening_cache=True` and `upsert_opening_cache_fn=_upsert_opening_cache` (the drain-tick-only cache fill, Pitfall 4 preserved exactly).

**Task 2 — entry-lane split into `eval_entry.py`:**
- Moved 14 of 16 entry-lane symbols into `app/services/eval_entry.py`: `_EvalTarget`, `_TargetSpec`, `_collect_target_specs`, `_snapshot_boards`, `_collect_eval_targets_per_game`, `_collect_midgame_eval_targets`, `_collect_endgame_span_eval_targets`, `_split_into_contiguous_islands`, `_batch_update_entry_eval_rows`, `_apply_eval_results`, `_claim_entry_eval_games`, `_mark_evals_completed`, `_collect_eval_targets_from_db`, `_classify_and_insert_flaws`.
- `eval_remote.py` and `import_service.py` now import these from `eval_entry.py` instead of `eval_drain.py`.
- `_pick_pending_game_ids` and `_load_pgns_for_games` deliberately stay in `eval_drain.py` (see Deviations) — they are the only two entry-lane functions that open their own internal `AsyncSession`, and moving them would require re-auditing every test that patches session routing for the entry-ply drain.

## Task Commits

1. **Task 1: Create eval_apply.py, move shared primitives, expose apply_full_eval, kill the router import leak** - `01e727f2` (feat)
2. **Task 2: Split eval_drain.py entry-lane vs full-lane into eval_entry.py** - `b3bb2672` (feat)

## Files Created/Modified

- `app/services/eval_apply.py` (NEW, ~1817 lines) - Shared write-path module: all primitives listed above plus `apply_full_eval`.
- `app/services/eval_entry.py` (NEW, ~592 lines) - Entry-ply collection/write/classify primitives.
- `app/services/eval_drain.py` (3188 → 1074 lines) - Retains full-lane orchestration (`run_eval_drain`, `_full_drain_tick`, `run_full_eval_drain`, `resweep_holed_games`, `_any_active_import_or_entry_ply_pending`, `_upsert_opening_cache`) plus `_pick_pending_game_ids`/`_load_pgns_for_games`; re-imports a superset of moved symbols from `eval_apply.py`/`eval_entry.py` for its own runtime use and for test/script backward compatibility.
- `app/routers/eval_remote.py` - Private-helper import block replaced with `eval_apply.py` + `eval_entry.py` imports; `_apply_atomic_submit`'s write phase now calls `apply_full_eval`.
- `app/services/import_service.py` - `_classify_and_insert_flaws`/`_collect_midgame_eval_targets`/`_collect_endgame_span_eval_targets` now imported from `eval_entry.py`.
- `tests/test_eval_worker_endpoints.py`, `tests/services/write_path_golden_scenarios.py`, `tests/services/test_full_eval_drain.py` - `_patch_router_session`/`run_scenario`/`_patch_drain_for_tick_tests` (+ one standalone test) now also patch `app.services.eval_apply`'s own `async_session_maker` binding.
- `tests/services/test_eval_drain.py` - 2 `chess.pgn.read_game` monkeypatch sites now patch `app.services.eval_entry.chess.pgn` instead of `app.services.eval_drain.chess.pgn` (the latter no longer imports `chess`).

## Decisions Made

- **`apply_full_eval` takes discrete pre-computed inputs, not the router's wire-level `AtomicSubmitRequest`.** This lets `_full_drain_tick` (engine-gather-derived inputs) and `_apply_atomic_submit` (worker-submitted inputs) share the identical write-session function while each keeps its own structurally-different read/gather phase. `apply_full_eval` is genuinely the "write_session: bulk_insert/update flaws, oracle counts, PV writes, apply_completion_decision(...), upsert_worker_heartbeat(...), commit" step from PATTERNS.md's orchestration shape — not the whole `_apply_atomic_submit` function.
- **`apply_full_eval` does not own or commit its session** (mirrors `apply_completion_decision`'s existing convention) — the caller opens `async with async_session_maker() as write_session:` and commits after. This was essential for test compatibility: had `apply_full_eval` opened its own session via `eval_apply.py`'s own `async_session_maker`, every existing `_full_drain_tick` test (which patches `eval_drain`'s own `async_session_maker`) would have silently connected to the wrong DB inside the write phase.
- **`_build_flaw_blob_lease_positions` relocated to `eval_apply.py`** despite RESEARCH.md flagging the tier-4 flaw-blob lane as "stays isolated (not touched by this phase)". Read that isolation as a semantic/behavioral property (never merges with the live-submit write path), not a file-location constraint — moving the function unchanged was required to make the `_build_flaw_blob_lease_positions`/`_assemble_flaw_blobs_from_submit`/`_parse_token` group of imports in `eval_remote.py` come entirely from `eval_apply.py`, closing the private-import leak for the shared write path.
- **Task 2 keeps `_pick_pending_game_ids`/`_load_pgns_for_games` in `eval_drain.py`** rather than moving all 16 entry-lane symbols — see Deviations for the full reasoning; this is the phase's one flagged partial-descope, sanctioned by D-05/the plan's own Task 2 language ("or flag descope").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test session-patching gap for relocated functions with their own internal session**
- **Found during:** Task 1, running `tests/services/test_flaw_upsert_equivalence.py` for the first time against the new `eval_apply.py`.
- **Issue:** `scenario_4_flip_in` failed — `ply=2 allowed_pv_lines: expected [], got None`. Root cause: `_derive_atomic_sentinel_lines` (moved to `eval_apply.py`) opens its own internal `AsyncSession` via `async with async_session_maker() as session:`. Existing test fixtures patched `eval_remote_module.async_session_maker` and `eval_drain_module.async_session_maker` to route to the test DB, but had no way to know a THIRD module (`eval_apply.py`) now also needed its own `async_session_maker` binding patched — module-level name bindings are per-file (unlike `chess.pgn`/`sentry_sdk`, which are shared singleton module objects safely patchable from any importer). The function silently connected to the real production sessionmaker, found no matching game, and returned an empty sentinel set, which propagated into `_classify_and_fill_oracle` writing a true `NULL` instead of a `[]` sentinel.
- **Fix:** Added `monkeypatch.setattr(eval_apply_module, "async_session_maker", session_maker)` alongside the existing `eval_remote_module`/`eval_drain_module` patches in `_patch_router_session` (test_eval_worker_endpoints.py), `run_scenario` (write_path_golden_scenarios.py), `_patch_drain_for_tick_tests` (test_full_eval_drain.py), and one standalone test in `test_full_eval_drain.py` that duplicates that fixture inline.
- **Files modified:** `tests/test_eval_worker_endpoints.py`, `tests/services/write_path_golden_scenarios.py`, `tests/services/test_full_eval_drain.py`.
- **Verification:** All 8 golden equivalence scenarios pass; full `test_eval_worker_endpoints.py` (68) and `test_full_eval_drain.py` (39) suites green.
- **Committed in:** `01e727f2` (Task 1 commit — fixed before committing).

**2. [Rule 1 - Bug] Same session-patching gap recurred during Task 2's entry-lane split investigation**
- **Found during:** Task 2 planning — before moving any entry-lane symbols, audited which of the 16 candidates open their own internal session (the exact failure mode from deviation 1). Found `_pick_pending_game_ids` and `_load_pgns_for_games` both do; the other 14 take `session: AsyncSession` as an explicit parameter.
- **Issue:** N/A (caught proactively before landing, not a runtime failure this time) — moving all 16 would have reproduced deviation 1's bug class across `test_eval_drain.py`'s many `_pick_pending_game_ids`/`run_eval_drain` tests.
- **Fix:** Kept `_pick_pending_game_ids`/`_load_pgns_for_games` in `eval_drain.py` (their only caller, `run_eval_drain`, also stays there) instead of moving them to `eval_entry.py`. Documented the rationale inline in `eval_drain.py` above `_pick_pending_game_ids` and in this SUMMARY.
- **Files modified:** N/A (design decision, not a code fix).
- **Verification:** Full backend suite green with zero test session-patch changes required for the entry-lane symbols that DID move (confirming the "session-param functions are safe to move" hypothesis).
- **Committed in:** `b3bb2672` (Task 2 commit).

**3. [Rule 3 - Blocking] Two additional missing backward-compat re-exports discovered via full-suite runs**
- **Found during:** Task 1, running the full backend suite and `scripts/*.py` import smoke-tests after the initial move.
- **Issue:** `_assemble_flaw_blobs_from_submit`, `_build_flaw_blob_lease_positions`, `_assemble_one_line_blob`, and `_batch_update_flaw_pv_lines` were used via `from app.services.eval_drain import <symbol>` in `tests/test_eval_worker_endpoints.py`, `tests/services/test_eval_drain.py`, and `scripts/backfill_multipv.py`, but were not yet in `eval_drain.py`'s backward-compat re-import list, causing `ImportError` at test-collection / script-import time.
- **Fix:** Added all four to `eval_drain.py`'s `from app.services.eval_apply import (...)` block (marked `# noqa: F401` where `eval_drain.py`'s own code doesn't call them directly).
- **Files modified:** `app/services/eval_drain.py`.
- **Verification:** `uv run python -c "from scripts.backfill_multipv import ..."` succeeds; full suite green.
- **Committed in:** `01e727f2` (Task 1 commit).

---

**Total deviations:** 2 auto-fixed bugs (Rule 1, both caught by the test suite/proactive audit before commit) + 1 auto-fixed blocking issue (Rule 3, missing backward-compat imports). No scope creep — all three are corrections that keep the move behavior-preserving, not new functionality.

## Issues Encountered

None beyond the deviations above, all resolved before their respective task commits landed.

## User Setup Required

None - no external service configuration required.

## Flagged Partial Descope (D-05 / Task 2)

Per the plan's explicit allowance ("If ... this split materially balloons context or surfaces an unexpected coupling that would risk the no-behavior-change contract, it is an ACCEPTABLE partial-R7 descope per D-05 — but you MUST flag it explicitly"):

- **`_pick_pending_game_ids` and `_load_pgns_for_games` were NOT moved to `eval_entry.py`.** They are the only 2 of the 16 entry-lane symbols that open their own internal `AsyncSession` (every other entry-lane function takes `session` as an explicit parameter). Moving them would require auditing and updating every existing `test_eval_drain.py` test that patches session routing for `run_eval_drain`/`_pick_pending_game_ids` directly (a materially larger, less-mechanical change with real regression risk — see Deviation 1/2 above for the exact failure class this would risk). Both stay in `eval_drain.py`, alongside their only caller (`run_eval_drain`).
- **Consequence:** `app/routers/eval_remote.py` retains exactly ONE private (underscore-prefixed) import from `eval_drain.py` — `_load_pgns_for_games` (used by `entry_submit_eval`) — plus the three public `ENTRY_LEASE_*` constants. This is a narrow, deliberate, and documented residual, not the 21-symbol leak the phase's WRITE-04 requirement targeted (which is fully eliminated — see coverage D3). The `import app.main` / `ty check` / circular-import risk (RESEARCH.md Pitfall 3) this phase specifically targeted is fully resolved regardless of this residual, since `_load_pgns_for_games` was never part of that risk (it has no dependency on `eval_apply.py` or the shared write path).

## Next Phase Readiness

- WRITE-04 (R7, module split) is complete: `apply_full_eval` lives in `eval_apply.py`, consumed by both live write lanes; the router's private-helper leak into `eval_drain.py`'s internals is eliminated for the shared write path; entry-lane primitives are substantially split into `eval_entry.py` with one flagged, justified residual.
- This completes Phase 150's planned dependency chain (R1 → R4 → R3 → R7); R5 (EnginePool generic method) and R6 (ES-lottery parameterization) were the plan's ride-alongs, already delivered in 150-02 (WRITE-05, WRITE-06). With this plan's WRITE-04, all six of Phase 150's requirements (WRITE-01..06) are now complete.
- Full backend suite green (3162 passed / 18 skipped); ruff + ty clean across the whole repo (pre-existing `alembic/versions/*.py` format drift confirmed unrelated via `git stash` diff, not touched by this plan).
- No blockers.

---
*Phase: 150-consolidate-write-path*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: app/services/eval_apply.py
- FOUND: app/services/eval_entry.py
- FOUND: .planning/phases/150-consolidate-write-path/150-05-SUMMARY.md
- FOUND commit: 01e727f2 (Task 1)
- FOUND commit: b3bb2672 (Task 2)
