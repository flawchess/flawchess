---
phase: 177-worker-side-multipv2-gem-candidates
plan: 04
subsystem: infra
tags: [httpx, asyncio, stockfish, remote-eval-worker]

# Dependency graph
requires:
  - phase: 177-01 (Protocol-v2 schema + lease version gate + second_best wiring)
    provides: "move_uci on LeasePosition, AtomicSecondBestEval, second_best[] on AtomicSubmitRequest, worker_schema_version-gated /atomic-lease"
  - phase: 177-02 (Tier-4b lease/submit pair)
    provides: "POST /bestmove-lease + POST /bestmove-submit, BestMoveLeasePosition/BestMoveSubmitEval schemas"
provides:
  - "WORKER_SCHEMA_VERSION=2, sent as a query param on both /atomic-lease calls (scope=explicit and scope=idle)"
  - "_eval_targeted_second_best — the worker-side targeted MultiPV-2 re-search for fresh-lane gem candidates (played==best plies only)"
  - "_eval_atomic_game returning (evals, blob_nodes, second_best); second_best threaded into the /atomic-submit body"
  - "Rung-5 ladder entry (/bestmove-lease -> /bestmove-submit) via _eval_bestmove_positions + _handle_bestmove_response"
affects: [177-05 (measurement) — the fleet now needs a v2 worker binary deployed before the post-deploy before/after measurement can observe the throughput shift]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Targeted second search reuses the SAME asyncio.gather + pool.evaluate_nodes_multipv2 pattern as _eval_atomic_blob_nodes/_eval_flaw_blob_positions, applied to a played==best-filtered subset rather than a PV-walk"
    - "A failed engine search (all-None 7-tuple) is dropped from the returned list rather than submitted or retried — the server's own Pitfall-1 fallback is the safety net, not the worker"

key-files:
  created: []
  modified:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py

key-decisions:
  - "Task 1 and Task 2 both needed to touch _run_cycle's docstring and the same idle-branch body (the worker_schema_version query param and the rung-5 insertion point are adjacent lines in the same function) — split into two atomic commits anyway by temporarily reverting Task 2's docstring/body/functions, committing Task 1, then reapplying Task 2, rather than merging the two tasks into one commit."
  - "Engine-failure detection for the targeted second-best search checks r[0] is None and r[1] is None (both eval_cp and eval_mate absent) — a real search always returns at least one of them, so this pair uniquely identifies the all-None failure tuple evaluate_nodes_multipv2 returns on a stopped pool or engine error, without a separate sentinel flag."

requirements-completed: [PROTO-01, PROTO-02]

coverage:
  - id: D1
    description: "WORKER_SCHEMA_VERSION bumped 1 -> 2; both /atomic-lease calls (scope=explicit, scope=idle) send it as a query param, not just on submit"
    requirement: "PROTO-01"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_worker_schema_version_is_2"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_explicit_first_skips_entry_lease"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_falls_to_idle_when_entry_lease_204"
        status: pass
    human_judgment: false
  - id: D2
    description: "Targeted MultiPV-2 second-best search runs ONLY for plies where the worker's own MultiPV-1 best equals the leased move_uci; the full-ply pass stays MultiPV-1 (Phase 146 D-03 invariant preserved)"
    requirement: "PROTO-02"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_game_targeted_second_best_only_played_best"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_positions_uses_multipv1_no_second_best"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_game_full_ply_pass_stays_multipv1"
        status: pass
    human_judgment: false
  - id: D3
    description: "A failed targeted second-best search drops that ply from second_best rather than submitting garbage or failing the whole /atomic-submit"
    requirement: "PROTO-02"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_game_targeted_second_best_drops_failed_search"
        status: pass
    human_judgment: false
  - id: D4
    description: "New rung-5 ladder entry: on a 204 from /flaw-blob-lease (rung 4), the worker tries /bestmove-lease; a 200 evaluates leased candidate FENs at MultiPV=2 only and submits to /bestmove-submit; a 204 falls to the existing idle sleep"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_bestmove_lease_only_after_flaw_blob_204"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_handle_bestmove_response_submits_n_entries_no_atomic_submit"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_bestmove_lease_204_falls_to_idle_sleep_no_submit"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_all_queues_empty_sleeps_once"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-17
status: complete
---

# Phase 177 Plan 04: Worker-side protocol v2 — targeted second-best re-search + rung-5 tier-4b handler Summary

**`scripts/remote_eval_worker.py` bumped to `WORKER_SCHEMA_VERSION=2` (sent at lease time on both atomic scopes), runs a targeted MultiPV-2 re-search after its MultiPV-1 full pass for played==best plies, and drives a new rung-5 ladder entry for the `/bestmove-lease` + `/bestmove-submit` tier-4b pair.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-17T16:47:00Z
- **Completed:** 2026-07-17T17:12:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `WORKER_SCHEMA_VERSION` bumped `1 -> 2`; both `/atomic-lease` calls (`scope=explicit`, `scope=idle`) now append `worker_schema_version=WORKER_SCHEMA_VERSION` as a query param (Pitfall 4) — a v1/version-omitting worker binary now gets 204 on the whole atomic lane, not just tier-4b.
- New `_eval_targeted_second_best`: after the MultiPV-1 full-ply pass, filters leased positions to those whose `move_uci` (the move actually played) equals the worker's own MultiPV-1 best move, then runs a second, separate `evaluate_nodes_multipv2` search over exactly that candidate set via the same `asyncio.gather` + pool pattern `_eval_atomic_blob_nodes` uses. The full-ply pass itself remains untouched (`_eval_positions`, MultiPV-1).
- A failed targeted search (the all-None 7-tuple `evaluate_nodes_multipv2` returns on engine failure) drops that ply from the returned list — never submitted as garbage, never fails the whole `/atomic-submit` — the server's own Pitfall-1 fallback (`_build_best_move_candidates`) covers the gap.
- `_eval_atomic_game`'s return signature grew to `(evals, blob_nodes, second_best)`; `_handle_atomic_response` threads `second_best` into the `/atomic-submit` JSON body.
- New rung 5 in `_run_cycle`, placed strictly *after* rung 4 (`/flaw-blob-lease`) per Pitfall 6 so the worker's ladder ordering mirrors the server's `TIER_BLOB_BACKFILL(4) < TIER_BESTMOVE_BACKFILL(5)` priority: a 204 from `/flaw-blob-lease` now tries `/bestmove-lease` before falling to the idle sleep.
- New `_eval_bestmove_positions` + `_handle_bestmove_response`: evaluate each leased tier-4b candidate-ply FEN at MultiPV=2 *only* (no full pass, no blob walk — the server already validated played==best candidacy server-side), then POST the per-ply runner-up evals to `/bestmove-submit`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bump WORKER_SCHEMA_VERSION to 2 + send it on the lease; targeted fresh-lane re-search** - `345c6c9e` (feat)
2. **Task 2: Add rung-5 tier-4b handler driving /bestmove-lease → /bestmove-submit** - `52a54a82` (feat)

Both tasks touch overlapping regions of the same two files (`_run_cycle`'s docstring and idle-branch body carry both the `worker_schema_version` query-param change and the rung-5 insertion in adjacent lines). To keep the commits genuinely atomic per task rather than merging them, Task 2's docstring/body additions and its two new functions were implemented, then temporarily reverted, Task 1 was committed on its own, and Task 2's additions were reapplied and committed separately — each commit's diff was verified in isolation (tests, `ty`, `ruff`) before committing.

## Files Created/Modified
- `scripts/remote_eval_worker.py` — `WORKER_SCHEMA_VERSION=2`; `_eval_targeted_second_best`; `_eval_atomic_game` 3-tuple return; `worker_schema_version` query param on both `/atomic-lease` calls; `second_best` in the `/atomic-submit` body; rung-5 branch in `_run_cycle`; `_eval_bestmove_positions`; `_handle_bestmove_response`
- `tests/test_remote_eval_worker.py` — updated existing lease-param assertions (`test_ladder_explicit_first_skips_entry_lease`, `test_ladder_falls_to_idle_when_entry_lease_204`) and `_eval_atomic_game` unpacking (3 tests); new `test_worker_schema_version_is_2`, `test_eval_atomic_game_targeted_second_best_only_played_best`, `test_eval_atomic_game_targeted_second_best_drops_failed_search`, `test_ladder_bestmove_lease_only_after_flaw_blob_204`, `test_handle_bestmove_response_submits_n_entries_no_atomic_submit`, `test_bestmove_lease_204_falls_to_idle_sleep_no_submit`; `test_ladder_all_queues_empty_sleeps_once` extended to cover rung 5

## Decisions Made
- Engine-failure detection in `_eval_targeted_second_best` checks `r[0] is None and r[1] is None` (both `eval_cp` and `eval_mate` absent) rather than a separate sentinel — a genuine search result always populates at least one of them (a mate score sets `eval_mate`; any other position sets `eval_cp`), so this pair uniquely identifies the all-None failure tuple `evaluate_nodes_multipv2` returns on a stopped pool or engine error.
- Split the two tasks into two atomic commits despite their code living in the same function, by implementing both, then temporarily reverting Task 2's additions, committing Task 1 in isolation (verified with `pytest`/`ty`/`ruff` on that exact tree state), and reapplying + committing Task 2 separately (also independently verified). This keeps the git history matching the plan's task boundaries rather than collapsing them into one commit for convenience.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required. The live worker fleet still runs the pre-Phase-177 binary until this script is deployed to the 4 worker hosts (Adrian operates all of them, per RESEARCH.md's v1→v2 rollout sequencing note); until then, v1 workers will get 204 on the whole atomic lane per this plan's own version gate (expected/by-design — Plan 01's server-side gate already went live independently).

## Next Phase Readiness
- The worker script is now fully protocol-v2: version-gated at lease time, computing its own fresh-lane runner-up evals, and driving the tier-4b rung. Plan 05 (post-deploy measurement) can proceed once this script is deployed to the worker fleet and the server-side gate (already live from Plan 01) starts seeing v2 traffic.
- `_eval_bestmove_positions`/`_handle_bestmove_response` are structurally isolated from the fresh-lane atomic path (no shared handler code, mirroring `_handle_flaw_blob_response`'s isolation) — no further wiring needed for Plan 05.

---
*Phase: 177-worker-side-multipv2-gem-candidates*
*Completed: 2026-07-17*

## Self-Check: PASSED

Both modified files (`scripts/remote_eval_worker.py`, `tests/test_remote_eval_worker.py`) verified present on disk; both task commit hashes (`345c6c9e`, `52a54a82`) verified present in git log.
