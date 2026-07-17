---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 06
subsystem: backend-eval-pipeline
tags: [stockfish, maia, gems-detection, eval-drain, atomic-submit, book-depth]

# Dependency graph
requires:
  - phase: 174-05
    provides: "_build_best_move_candidates / GameBestMove candidate-row builder (GEMS-03), called by both the local drain and the remote atomic-submit lane"
provides:
  - "Lichess-eval games get the SAME full-ply MultiPV-2 pass as engine games on the local drain (targets filter + SEED-054 flaw-ply exemption retired)"
  - "Hole-counting parity for lichess-eval games: a genuine Stockfish failure holds the game back for retry instead of silently completing"
  - "/atomic-lease no longer skips lichess-eval games; SEED-076 lease redundancy filter bypassed for them (was collapsing the lease to ply 0 only)"
  - "Book-depth detection (_contiguous_san_prefix) reconstructed from board.move_stack, immune to a sparse/pre-filtered targets list (CR-01 fixed)"
affects: [174-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reconstructing a position's complete move history from chess.Board.move_stack rather than requiring every intermediate ply to be present as a separate caller-supplied record"

key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - app/services/eval_apply.py
    - app/routers/eval_remote.py
    - app/services/eval_queue_service.py
    - tests/services/test_full_eval_drain.py
    - tests/services/test_eval_apply.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "Deleted the now-fully-dead _flaw_engine_plies helper (its only caller, the retired targets filter, is gone) rather than leaving it as untested dead code"
  - "Rule 1 fix (Task 2): bypassed the SEED-076 incremental-redundancy lease filter entirely for lichess-eval games in _build_lease_positions — its premise (an already-eval'd row means a prior worker already resolved it) is false for lichess games, whose %evals come from import, not an engine call; left unfixed it would have collapsed the lease to ply 0 only (always in-book), defeating Task 2's own acceptance criteria"
  - "Lease's own terminal target dropped for lichess games (include_terminal=not is_lichess_eval_game), mirroring the submit side, to avoid a wasted worker eval call on a position the submit path never uses"
  - "_contiguous_san_prefix rebuilt around the deepest target's board.move_stack + its own move_san, not a ply-0-anchored walk over the caller's targets list — makes book-depth detection correct regardless of which targets are present"

requirements-completed: [GEMS-02, GEMS-03]

coverage:
  - id: D1
    description: "Local drain gives lichess-eval games full-ply MultiPV-2 coverage; stored %evals + lichess_evals_at preserved; full_pv_completed_at stamped only on genuinely complete best-move coverage"
    requirement: GEMS-02
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestFlawPv::test_flaw_pv_written_for_analyzed_lichess_game"
        status: pass
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestFlawPv::test_lichess_game_forced_null_best_move_is_a_hole_not_false_completion"
        status: pass
    human_judgment: false
  - id: D2
    description: "/atomic-lease leases lichess-eval games (no 204 skip); a simulated remote-worker submission produces a GameBestMove candidate row via the Pitfall-1 fallback while preserving stored evals"
    requirement: GEMS-03
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_lichess_eval_game_returns_full_positions"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_lichess_eval_game_produces_best_move_candidate_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "Book-depth detection is robust to a sparse targets list (CR-01 fixed and regression-guarded)"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestCandidateGate::test_sparse_targets_book_depth_not_collapsed_cr01"
        status: pass
    human_judgment: false
  - id: D4
    description: "Manual dev-DB spot-check: drain one real lichess-eval game and confirm best-move rows span out-of-book plies while stored %evals persist"
    verification: []
    human_judgment: true
    rationale: "Requires running the live drain against the dev DB (mutating real rows), which the plan's own <verification> section labels a manual step; not attempted by the automated executor per CLAUDE.md's no-dev-DB-mutation-in-plans caution — left for human verification."

duration: ~50min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 06: Retire lichess-eval targets filter, fix CR-01 book-depth bug Summary

**Lichess-eval games now get the same full MultiPV-2 Stockfish pass as engine games on both the local drain and remote worker lane, with a book-depth detection fix (CR-01) that makes out-of-book gem/great candidacy correct regardless of which plies a caller happens to supply.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3
- **Files modified:** 7 (app/services/eval_drain.py, app/services/eval_apply.py, app/routers/eval_remote.py, app/services/eval_queue_service.py, tests/services/test_full_eval_drain.py, tests/services/test_eval_apply.py, tests/test_eval_worker_endpoints.py)

## Accomplishments

- Retired the `is_lichess_eval_game` targets filter + SEED-054 flaw-ply exemption in `_full_drain_tick` (eval_drain.py) — lichess-eval games' `targets` list is now the full contiguous ply-0-anchored list, identical in shape to an engine game's, so the existing gather over `engine_targets` evaluates every non-terminal ply with `evaluate_nodes_multipv2`.
- Fixed a hole-counting silent-completion trap in `_apply_full_eval_results`'s `is_lichess_eval_game` write branch: a `NULL best_move` on an engine-covered ply now increments `failed_ply_count`, holding the game back for a bounded SEED-045 retry (Path B/C) instead of self-terminating out of the 174-07 backfill lottery with a permanent NULL best_move.
- Removed `/atomic-lease`'s D-4/v1-scope 204 skip for lichess-eval games; threaded the real `is_lichess_eval_game` value through `AtomicLeaseResponse`.
- Found and fixed a genuine blocker in the SEED-076 lease-redundancy filter (`_build_lease_positions`): its "already-eval'd row = already resolved by a prior worker" premise is false for lichess-eval games (their %evals come from import, never an engine call), which would have collapsed a fresh lichess game's lease to ply 0 only (always in-book) — making Task 2's own acceptance criteria unreachable. Fixed by bypassing the redundancy filter entirely for lichess-eval games and dropping their lease's terminal target (mirroring the submit side).
- Rewrote `_contiguous_san_prefix` to reconstruct book depth from the deepest target's `board.move_stack` (which carries the game's full push history regardless of which other targets are present) instead of a ply-0-anchored walk over the caller's `targets` list — fixes CR-01 (book depth silently collapsing to 0 when ply 0 is absent from a sparse targets list) and is regression-guarded.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove the local-drain lichess-eval targets filter + flaw-ply exemption; analyze all plies** - `a8526290` (feat)
2. **Task 2: Remove the remote /atomic-lease lichess-eval skip so remote workers cover them too** - `7c8b84a9` (feat, includes a Rule 1 fix)
3. **Task 3: Book-depth-correct out-of-book detection + regression test + doc corrections** - `fb1bd216` (fix)

## Files Created/Modified

- `app/services/eval_drain.py` - `_full_drain_tick`: removed the lichess targets filter + `_flaw_engine_plies` call; `dedup_map`/`engine_targets` simplified to be unconditionally empty/full for lichess games
- `app/services/eval_apply.py` - `_apply_full_eval_results`'s `is_lichess_eval_game` branch now counts a NULL best_move as a hole; deleted the now-dead `_flaw_engine_plies` helper; rewrote `_contiguous_san_prefix` (book-depth CR-01 fix)
- `app/routers/eval_remote.py` - `/atomic-lease` handler: removed the lichess 204 skip, threads real `is_lichess_eval_game`; `_build_lease_positions` bypasses the SEED-076 redundancy filter and drops the terminal target for lichess games
- `app/services/eval_queue_service.py` - corrected a stale `release_job` docstring describing the retired lichess-defer path
- `tests/services/test_full_eval_drain.py` - adapted the SEED-054 flaw-pv test to the 6-engine-call unified-pass shape; added full best_move/eval-preservation coverage test + forced-failure hole-counting-parity regression test
- `tests/services/test_eval_apply.py` - `_target()` gained an optional `board` param; fixed `test_in_book_ply_no_row` to use a real connected board; added the CR-01 sparse-targets regression test
- `tests/test_eval_worker_endpoints.py` - replaced the retired lichess-204-defer test with a full-lease-coverage test; added a lichess-eval atomic-submit test proving a GameBestMove row is produced via the Pitfall-1 fallback

## Decisions Made

See `key-decisions` in frontmatter. Summary: deleted dead code (`_flaw_engine_plies`) rather than leaving it untested; bypassed the SEED-076 lease-redundancy filter for lichess games (Rule 1 fix, see Deviations); rebuilt book-depth detection around `board.move_stack` rather than a caller-supplied targets walk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SEED-076 lease-redundancy filter collapsed lichess-eval leases to ply 0 only**
- **Found during:** Task 2 (removing the `/atomic-lease` lichess skip)
- **Issue:** `_build_lease_positions`'s pre-existing `_lease_position_redundant` incremental check treats a game_positions row that already carries an eval as evidence a prior worker round already resolved that position (eval AND best_move together — true for engine games, since one engine call always produces both). For lichess-eval games this premise is false: their %eval columns are populated at IMPORT time, never by an engine call, and carry no best_move. Verified via a direct call to `_build_lease_positions` with realistic gp_rows (every row pre-populated with %eval): the lease collapsed to `[ply 0, terminal]` — ply 0 is always inside the opening book, so the resulting submission could never produce a single out-of-book best-move candidate row, silently defeating Task 2's own must-have.
- **Fix:** `_build_lease_positions` gained an `is_lichess_eval_game` param; when set, the redundancy filter is bypassed entirely (every position is leased) and the lease's own `_collect_full_ply_targets` call drops the terminal target (`include_terminal=not is_lichess_eval_game`), mirroring the submit side and avoiding a wasted worker eval call.
- **Files modified:** `app/routers/eval_remote.py`
- **Verification:** `tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_lichess_eval_game_returns_full_positions` (asserts all 4 real plies leased, no redundancy omission, no terminal donor); `test_atomic_submit_lichess_eval_game_produces_best_move_candidate_row` (proves the full round trip produces a candidate row).
- **Committed in:** `7c8b84a9` (Task 2 commit)

**2. [Rule 2 - Missing critical] Deleted `_flaw_engine_plies`, now fully dead code**
- **Found during:** Task 1
- **Issue:** Removing the lichess targets filter (its only call site) leaves `_flaw_engine_plies` with zero remaining callers project-wide — a genuinely dead, untestable helper, which the plan's own acceptance criteria ("no unused-symbol / dead-import lint") implicitly requires cleaning up.
- **Fix:** Deleted the function and its import; updated `_classify_with_overlay`'s docstring (its `overlay=False` mode currently has no caller — documented, not deleted, as a general-purpose mode) and the `_missing_flaw_pv_targets`/`_fill_engine_game_flaw_pvs` docstrings that referenced it by name.
- **Files modified:** `app/services/eval_apply.py`, `app/services/eval_drain.py`
- **Verification:** `uv run ty check app/ tests/` clean; `uv run ruff check` clean (no unused import).
- **Committed in:** `a8526290` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug fix, 1 Rule 2 dead-code removal)
**Impact on plan:** The Rule 1 fix was necessary for Task 2's own acceptance criteria to be achievable against a realistic lichess-eval game (every row pre-populated with %eval); without it the endpoint change would have been functionally inert. Both fixes stayed within Task 2's/Task 1's already-listed files. No scope creep.

## Issues Encountered

None beyond the deviations above — verified interactively (temporarily reverting each fix and confirming the corresponding test goes red) before committing:
- Reverting the `_contiguous_san_prefix` rewrite makes `test_sparse_targets_book_depth_not_collapsed_cr01` fail (confirmed).
- The full backend suite (`uv run pytest -n auto`) is green (3372 passed, 18 skipped) after every task's commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 174-07 (the 43k-game backlog backfill) can now rely on `full_pv_completed_at` meaning "genuinely complete best-move coverage" for a lichess-eval game, on both the local drain and remote lanes.
- Manual dev-DB spot-check (item D4 above) is the one verification item left for a human: drain one real lichess-eval game from the existing dev DB (~4.5k such games present, do NOT reset) and confirm best-move rows span out-of-book plies while stored %evals persist.

---
*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Completed: 2026-07-16*

## Self-Check: PASSED
- FOUND: .planning/phases/174-backend-maia-inference-best-move-storage-spike-gated/174-06-SUMMARY.md
- FOUND: a8526290 (Task 1 commit)
- FOUND: 7c8b84a9 (Task 2 commit)
- FOUND: fb1bd216 (Task 3 commit)
