---
phase: 146-offload-live-submit-forcing-line-continuation-eval-to-the-re
plan: "02"
subsystem: eval-pipeline
tags:
  - eval-remote
  - tier-4
  - flaw-blobs
  - fleet-worker
  - performance
  - d-04
  - multipv-1
dependency_graph:
  requires:
    - "Phase 145 tier-4 server endpoints (/flaw-blob-lease, /flaw-blob-submit, FlawBlobLeaseResponse, FlawBlobSubmitRequest)"
    - "Phase 146 Plan 01: blob_map={} unconditional, SubmitEval second-best dropped, tier-4 recency drain"
  provides:
    - "Fleet worker drains tier-4 flaw-blob queue continuously (D-04)"
    - "Full-ply worker pass reduced to MultiPV-1 (evaluate_nodes_with_pv) — second-best only on tier-4 blob rung"
    - "HTTP_TIMEOUT_S restored to 30.0 — SEED-071 120s stopgap removed"
  affects:
    - "scripts/remote_eval_worker.py (fleet worker running on prod machines)"
    - "Tactic tag gating: games deferred by Plan 01 now drain to gated retag via D-07"
tech_stack:
  added: []
  patterns:
    - "_eval_flaw_blob_positions: asyncio.gather over evaluate_nodes_multipv2 in worker process (safe — no AsyncSession)"
    - "Handler mirror pattern: _handle_flaw_blob_response mirrors _handle_entry_ply_response (raise_for_status, json, eval, dry_run guard, submit, return not loop)"
    - "Four-rung ladder: tier-1/2 → entry-ply → tier-3 → tier-4 blob, single sleep on all-204"
key_files:
  created: []
  modified:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py
    - tests/test_eval_queue_service.py
decisions:
  - "_eval_flaw_blob_positions maps r[0]/r[1]/r[4]/r[5]/r[6] explicitly; r[2]/r[3] (best_move/pv) intentionally excluded — PV-continuation FENs have no pv/best_move output contract (RESEARCH Pitfall 3)"
  - "HTTP_TIMEOUT_S=30.0 is the correct landing point: 10x margin over p99<3s; no further reduction without prod latency observation (RESEARCH §5)"
  - "rung-4 204 path falls through to the same single asyncio.sleep(idle_sleep) — no double-sleep (T-146-06)"
  - "Pre-existing ty error in test_eval_queue_service.py (test_engine: object → AsyncEngine) fixed as Rule 1 — blocks ty check requirement"

requirements-completed: []

coverage:
  - id: D1
    description: "Fleet worker drains tier-4 flaw-blob queue: rung-4 _handle_flaw_blob_response calls /flaw-blob-lease then /flaw-blob-submit after all tier-1/2/3 return 204"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_flaw_blob_on_all_tier123_204"
        status: pass
    human_judgment: false
  - id: D2
    description: "All-four-tiers-204 path sleeps exactly once — no double-sleep from rung-4 insertion (T-146-06)"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_all_queues_empty_sleeps_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "_eval_flaw_blob_positions maps multipv2 7-tuple indices correctly: r[0]/r[1]/r[4]/r[5]/r[6], token echoed unchanged (D-04a), r[2]/r[3] absent"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_flaw_blob_positions_maps_indices_correctly"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full-ply pass uses evaluate_nodes_with_pv (MultiPV-1): second_cp/second_mate/second_uci absent from _eval_positions output"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_positions_uses_multipv1_no_second_best"
        status: pass
    human_judgment: false
  - id: D5
    description: "HTTP_TIMEOUT_S == 30.0 (SEED-071 120s stopgap removed)"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_http_timeout_s_restored_to_30"
        status: pass
    human_judgment: false
  - id: D6
    description: "End-to-end dev drain: live submit -> NULL blobs -> worker tier-4 drain -> gated retag (needs running worker + dev server)"
    verification: []
    human_judgment: true
    rationale: "Requires a running fleet worker and dev server; automated tests mock both HTTP and EnginePool. See 146-VALIDATION.md."

duration: 8min
completed: "2026-07-01"
status: complete
---

# Phase 146 Plan 02: Fleet worker tier-4 drain rung, MultiPV-1 full-ply, HTTP_TIMEOUT_S=30 — Summary

**Fleet worker upgraded with a four-rung lease ladder (tier-4 blob drain via /flaw-blob-lease + /flaw-blob-submit), full-ply pass reduced to MultiPV-1, and HTTP_TIMEOUT_S restored to 30s — closing the offload loop opened by Plan 01.**

## Performance

- **Duration:** ~8 minutes
- **Started:** 2026-07-01T00:09:30Z
- **Completed:** 2026-07-01T00:18:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Fleet worker now continuously drains the tier-4 flaw-blob queue after exhausting tier-1/2/3: it polls `/flaw-blob-lease`, evaluates the leased continuation FENs at MultiPV-2, and submits token-keyed results to `/flaw-blob-submit` (D-04). This closes the offload loop — games deferred by Plan 01 (NULL blobs) now receive the gated retag (D-07) promptly.
- Full-ply pass (`_eval_positions`) reduced from MultiPV-2 to MultiPV-1 (`evaluate_nodes_with_pv`) now that `SubmitEval` no longer carries `second_cp/second_mate/second_uci` (D-03 consequence, RESEARCH §1 single-consumer grep confirmed safe). The tier-4 blob rung (`_eval_flaw_blob_positions`) retains MultiPV-2 — the blob contract requires second-best.
- `HTTP_TIMEOUT_S` lowered from the 120s SEED-071 stopgap back to 30.0. The live `/submit` no longer runs any engine (Plan 01), so p99 < 3s; 30s provides a 10x safety margin (RESEARCH §5).

## Task Commits

Each task used TDD (RED → GREEN):

1. **Task 1 RED: failing tests for tier-4 flaw-blob drain rung** — `a5adb79a` (test)
2. **Task 1 GREEN: tier-4 flaw-blob drain rung implementation** — `56f9e32a` (feat)
3. **Task 2 RED: failing tests for MultiPV-1 + HTTP_TIMEOUT_S=30** — `bc2554ee` (test)
4. **Task 2 GREEN: MultiPV-1 reduction + HTTP_TIMEOUT_S=30** — `20feeae8` (feat)

## Files Created/Modified

- `scripts/remote_eval_worker.py` — added `_eval_flaw_blob_positions` helper, `_handle_flaw_blob_response` handler; updated `_run_cycle` with rung-4; switched `_eval_positions` to `evaluate_nodes_with_pv`; `HTTP_TIMEOUT_S=30.0`; docstrings updated
- `tests/test_remote_eval_worker.py` — added 5 new tests (3 for Task 1, 2 for Task 2); `HTTP_TIMEOUT_S` and `_eval_flaw_blob_positions` promoted to module-level import block; `patch` added to mock imports
- `tests/test_eval_queue_service.py` — pre-existing ty error fixed: `test_engine: object` → `test_engine: AsyncEngine` (Rule 1 bug; was blocking `ty check` zero-errors requirement)

## Decisions Made

- Token is echoed unchanged in `_eval_flaw_blob_positions` (D-04a): `str(pos["token"])` passed directly to the output dict; worker has no flaw-structure knowledge.
- `_eval_flaw_blob_positions` excludes `r[2]` (best_move) and `r[3]` (pv) from the output dict — these are PV-continuation FENs that the blob contract does not need. Mapped explicitly to avoid RESEARCH Pitfall 3 index errors.
- `HTTP_TIMEOUT_S` stays at 30.0; further reduction (to e.g. 10s) requires observing prod p99 on the new path (out of scope per RESEARCH §5).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing ty error in tests/test_eval_queue_service.py**
- **Found during:** Task 1 GREEN verification (`uv run ty check app/ tests/`)
- **Issue:** `tier4_session_maker` fixture typed `test_engine: object` — too broad; ty inferred `invalid-argument-type` when passing it to `async_sessionmaker`. Error was already present after Plan 01 but the `# type: ignore[call-overload]` suppressor used the wrong rule name for the new ty error category.
- **Fix:** Changed `test_engine: object` to `test_engine: AsyncEngine` and added `AsyncEngine` to the SQLAlchemy imports; removed the now-unnecessary `# type: ignore[call-overload]`.
- **Files modified:** tests/test_eval_queue_service.py
- **Committed in:** 56f9e32a (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Ruff F401/F811: redundant local import after module-level promotion**
- **Found during:** Task 2 GREEN ruff check
- **Issue:** `_eval_flaw_blob_positions` was added to the module-level import block AND still had a `from scripts.remote_eval_worker import _eval_flaw_blob_positions` local import inside `test_eval_flaw_blob_positions_maps_indices_correctly`. Ruff flagged F401 (unused) and F811 (redefinition).
- **Fix:** Removed the local import from the test function body.
- **Files modified:** tests/test_remote_eval_worker.py
- **Committed in:** 20feeae8 (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes were necessary for `ty check` / `ruff check` verification gates. No scope creep.

## Known Stubs

None. All changes are complete functional implementations.

## Threat Flags

No new threat surface. The flaw-blob lease/submit endpoints and the token-opaque protocol are unchanged from Phase 145. The worker's `asyncio.gather` over `evaluate_nodes_multipv2` is bounded by the server-side `MAX_SUBMIT_EVALS=1024` cap (T-146-05).

## Self-Check: PASSED
