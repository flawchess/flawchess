---
phase: 117-priority-queue-flaw-integration
plan: 03
subsystem: engine
tags: [stockfish, eval_drain, game_flaws, pv, best_move, queue, asyncio]

requires:
  - phase: 117-01
    provides: best_move + pv columns on game_positions; full_pv_completed_at on games
  - phase: 117-02
    provides: claim_eval_job + ClaimedJob; WORKER_ID_SERVER_POOL; report_job_complete

provides:
  - evaluate_nodes_with_pv — 4-tuple (eval_cp, eval_mate, best_move, pv_string) from one search
  - PV extractors _pv_to_best_move / _pv_to_uci_string / PV_CAP_PLIES=12
  - Queue-lease pick in _full_drain_tick (replaces LIFO id-DESC)
  - best_move threaded through dedup transplant and engine write path
  - WR-02 gate repointed from white_blunders to lichess_evals_at (D-117-07)
  - _classify_and_fill_oracle: classify_game_flaws + oracle counts + flaw PV at ply N+1
  - _mark_full_pv_completed / full_pv_completed_at second completion marker (D-117-12)
  - _signal_flaw_completion stub for per-user cache invalidation (D-117-11)
  - EVAL-04, EVAL-06, QUEUE-03 test coverage in test_full_eval_drain.py

affects: [118-cache-invalidation, frontend-flaw-pv-display, eval-drain-tuning]

tech-stack:
  added: []
  patterns:
    - "evaluate_nodes_with_pv reuses the existing 1M-node search — zero extra engine compute; InfoDict returned once, extractors applied on top"
    - "_GameColorView duck-typed wrapper swaps user_color to call count_game_severities for both white and black oracle counts"
    - "Flaw PV written at ply N+1 (the position AFTER the flawed move); engine_result_map[ply+1]['pv'] is already computed from the same tick's gather"
    - "asyncio.gather on EnginePool stays strictly OUTSIDE any AsyncSession scope — CLAUDE.md hard rule enforced structurally"
    - "WR-02 discriminator is lichess_evals_at IS NULL (engine-written source); white_blunders is a report column only, not a gate"

key-files:
  created: []
  modified:
    - app/services/engine.py
    - app/services/eval_drain.py
    - app/repositories/game_repository.py
    - tests/services/test_full_eval_drain.py
    - tests/services/test_engine_pv.py
    - tests/services/test_eval_queue.py

key-decisions:
  - "D-117-07: WR-02 gate repointed from white_blunders IS NULL to lichess_evals_at IS NULL — lichess_evals_at is the correct discriminator for engine-written vs lichess-%eval-written rows"
  - "D-117-02: Flaw PV written at ply N+1 (after the flawed move), not at ply N — the refutation line starts from the resulting position"
  - "D-117-01: 4-tuple (eval_cp, eval_mate, best_move, pv_string) from evaluate_nodes_with_pv — drain has flaw PV without a second engine call"
  - "D-117-08: count_game_severities called twice via _GameColorView duck-typed wrapper — minimal-change path, no new param on the function"
  - "D-117-11: _signal_flaw_completion is a Phase 117 no-op stub — real cache invalidation deferred to Phase 118"
  - "D-117-12: full_pv_completed_at set in the same write transaction as full_evals_completed_at — atomic with flaws and oracle counts"
  - "POSITION_COPY_COLUMNS must include best_move and pv — bulk_insert_positions uses COPY and requires exact column coverage (Rule 1 fix)"

patterns-established:
  - "Rule 1 fix — POSITION_COPY_COLUMNS: adding new model columns requires updating the COPY tuple; covered by test_bulk_insert_positions_column_coverage"
  - "TDD: RED test committed before GREEN implementation for Tasks 1 and 3"

requirements-completed: [EVAL-04, EVAL-06, QUEUE-03]

duration: 40min
completed: 2026-06-13
---

# Phase 117 Plan 03: Queue-Lease Pick, PV Capture, and Flaw Classification Hook Summary

**Queue-lease drain pick, evaluate_nodes_with_pv 4-tuple (zero extra search), best_move threaded through dedup + write, WR-02 gate repointed to lichess_evals_at, and _classify_and_fill_oracle wiring classify_game_flaws + oracle counts + flaw PV at ply N+1**

## Performance

- **Duration:** ~40 min (across two sessions)
- **Started:** 2026-06-13T09:33:09Z
- **Completed:** 2026-06-13T10:11:43Z
- **Tasks:** 3 (TDD: 2 RED + 2 GREEN commits each; Task 3 = extended test file)
- **Files modified:** 7

## Accomplishments

- `evaluate_nodes_with_pv` returns `(eval_cp, eval_mate, best_move, pv_string)` in a single 1M-node search — no extra engine compute; `PV_CAP_PLIES = 12` caps the PV string
- `_full_drain_tick` now picks via `claim_eval_job` queue lease instead of LIFO id-DESC; `best_move` written for every evaluated non-dedup'd ply, transplanted via dedup for opening-region plies
- `_classify_and_fill_oracle` runs on full-eval completion: `classify_game_flaws` inserts `game_flaws` rows, oracle count columns (`white_/black_inaccuracies/mistakes/blunders`) filled via `count_game_severities` for both colors using `_GameColorView`, flaw PV written at ply N+1 from the same tick's `engine_result_map`
- WR-02 gate repointed from `white_blunders IS NULL` to `lichess_evals_at IS NULL` across all affected sites in `eval_drain.py`; `full_pv_completed_at` second marker set atomically with evals + flaws
- `POSITION_COPY_COLUMNS` updated with `best_move` and `pv` — bulk COPY path now covers all 117-01 columns

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: PV extractor tests** — `05b4b9a4` (test)
2. **Task 1 GREEN: evaluate_nodes_with_pv + extractors** — `f927dbf4` (feat)
3. **Task 2: eval_drain.py — queue pick, best_move, WR-02, classify+oracle+PV hook** — `00877f14` (feat)
4. **Task 3: Extended drain tick tests** — `0b660fde` (test)

## Files Created/Modified

- `app/services/engine.py` — `evaluate_nodes_with_pv`, `_pv_to_best_move`, `_pv_to_uci_string`, `_analyse_with_pv`, `PV_CAP_PLIES = 12`
- `app/services/eval_drain.py` — queue-lease pick, best_move threading, WR-02 repoint, `_classify_and_fill_oracle`, `_mark_full_pv_completed`, `_signal_flaw_completion`, `_GameColorView`
- `app/repositories/game_repository.py` — `best_move` and `pv` added to `POSITION_COPY_COLUMNS` (Rule 1 fix)
- `tests/services/test_full_eval_drain.py` — `TestWr02Repointed`, `TestBestMove`, `TestFlawPv`, `TestClassifyHook`, `TestOracleCounts`; updated `_patch_drain_for_tick_tests` and `TestMarkerWrite`
- `tests/services/test_engine_pv.py` — `ty: ignore` annotation fix (invalid-argument-type)
- `tests/services/test_eval_queue.py` — `.unique().scalar_one_or_none()` fix for `lazy="joined"` relationship (Rule 1)
- `app/models/eval_jobs.py`, `app/services/eval_queue_service.py`, `tests/test_migration_117.py` — ruff format collateral (style only)

## Decisions Made

- **D-117-07**: WR-02 gate uses `lichess_evals_at IS NULL` — `white_blunders` is a report column, not a source discriminator; `lichess_evals_at` precisely marks lichess-%eval-written rows.
- **D-117-02**: Flaw PV at ply N+1 (position after the flawed move) — the refutation line describes what the opponent should play from the resulting position, not from before the blunder.
- **4-tuple form for `evaluate_nodes_with_pv`**: returns `(eval_cp, eval_mate, best_move, pv_string)` so the drain has both PV artifacts from one search; no second `analyse()` call needed in the hook.
- **`_GameColorView` duck-type**: `count_game_severities` reads only `game.user_color`; a shallow wrapper with swapped color avoids adding a parameter to the existing function (minimal-change, per RESEARCH Open Q2).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] POSITION_COPY_COLUMNS missing best_move and pv**
- **Found during:** Full suite run after Tasks 2 and 3
- **Issue:** `test_bulk_insert_positions_column_coverage` failed — `POSITION_COPY_COLUMNS` did not include `best_move` and `pv` added by the 117-01 migration; bulk COPY would silently omit those columns for new imports
- **Fix:** Added `"best_move"` and `"pv"` to `POSITION_COPY_COLUMNS` in `game_repository.py`
- **Files modified:** `app/repositories/game_repository.py`
- **Verification:** `test_bulk_insert_positions_column_coverage` passes; full suite 2586 passed
- **Committed in:** `00877f14` (Task 2 commit, included as part of the drain changes)

**2. [Rule 1 - Bug] test_eval_queue.py cross-test contamination**
- **Found during:** Task 3 (full suite run after adding session-scoped user fixture)
- **Issue:** `scalar_one_or_none()` on a query returning a User with `lazy="joined"` oauth_accounts raises a uniqueness error when multiple rows are returned after the join
- **Fix:** Changed to `.unique().scalar_one_or_none()` in the eval_queue test fixture
- **Files modified:** `tests/services/test_eval_queue.py`
- **Verification:** Full suite passes
- **Committed in:** `0b660fde` (Task 3 commit)

**3. [Rule 1 - Bug] Various test assertion/constant fixes during TDD iteration**
- `test_dedup_hits_parity_source` assertion updated from 2-tuple to 3-tuple after `_fetch_dedup_evals` return type extension
- `test_dedup_excludes_analyzed_source` updated to use `lichess_evals_at` gate instead of `white_blunders`
- `_patch_drain_for_tick_tests` updated to mock `claim_eval_job` directly (not the old LIFO pick)
- `TestMarkerWrite` updated to mock `evaluate_nodes_with_pv` 4-tuple instead of 2-tuple `evaluate_nodes`
- Invalid hex literals (`0xBEEF_DEDU_P001` etc.) corrected to valid hex
- `_blunder_eval_sequence` eval values tuned to produce exactly one blunder (not two)
- All committed in `0b660fde` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs)
**Impact on plan:** All fixes essential for correctness. No scope creep.

## Issues Encountered

- **Off-by-one PV write (Pitfall 4)**: The flaw PV must be written to ply N+1 (position after the flawed move), not ply N. The `engine_result_map` is keyed by ply, so `engine_result_map[flaw_ply + 1]` contains the PV string from the board state after the blunder — this required careful index tracking through the `_classify_and_fill_oracle` helper.
- **Blunder eval sequence for tests**: The first attempt at `_blunder_eval_sequence` produced two blunders instead of one because the black-to-move eval drop at ply 1 also crossed the `BLUNDER_DROP` threshold. Fixed by setting ply 1 `eval_cp` to 30 (sub-threshold for black) and ply 3 to -480 (keeps black slightly winning, tiny drop).

## Next Phase Readiness

- `evaluate_nodes_with_pv` and `_classify_and_fill_oracle` are the two main integration points for Phase 118 (cache invalidation); `_signal_flaw_completion` stub is ready to wire
- Oracle count columns (`white_/black_inaccuracies/mistakes/blunders`) are filled for all engine-analyzed games going forward; historical backfill is a separate concern
- `full_pv_completed_at` marker enables future queries to distinguish games with flaw PV written vs only eval_cp/eval_mate

## Known Stubs

- `_signal_flaw_completion(user_id: int)` in `app/services/eval_drain.py`: Phase 117 no-op stub; inserts `user_id` into `_recently_flaw_completed_users` set only. Phase 118 wires real per-user cache invalidation (D-117-11).

---
*Phase: 117-priority-queue-flaw-integration*
*Completed: 2026-06-13*
