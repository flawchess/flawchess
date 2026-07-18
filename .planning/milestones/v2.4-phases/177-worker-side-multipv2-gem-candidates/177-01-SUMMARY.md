---
phase: 177-worker-side-multipv2-gem-candidates
plan: 01
subsystem: api
tags: [fastapi, pydantic, sentry, remote-eval-worker, stockfish]

# Dependency graph
requires:
  - phase: 174-176 (v2.4 Backend Gem & Great Detection)
    provides: game_best_moves storage + _build_best_move_candidates (Pitfall-1 fallback mechanism)
provides:
  - Protocol-v2 wire schema (move_uci on LeasePosition, AtomicSecondBestEval, second_best[] on AtomicSubmitRequest)
  - worker_schema_version-gated /atomic-lease (both scope=explicit and scope=idle)
  - second_best_map wiring from worker submissions into _build_best_move_candidates
  - Sentry source-tagged fallback branch (drain-local vs worker-submit-fallback)
affects: [177-02 (tier-4b lease/submit pair), 177-03 (drain tier-aware minimal path), 177-04/05 (worker script rung + measurement)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Version gate as the FIRST statement in an endpoint body, before any claim/session work, so it applies uniformly across every scope/branch (Pitfall 4)"
    - "Tamper-guard loop mirrored across sibling submitted-entry lists (blob_nodes and second_best both validated 0 <= ply < game_length before any write)"
    - "Sentry source-tagging via an optional caller-supplied `source` param with a safe default, so existing callers stay unchanged while the new caller opts into a distinct tag"

key-files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/routers/eval_remote.py
    - app/services/eval_apply.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/test_eval_apply.py

key-decisions:
  - "worker_schema_version defaults to 1 on /atomic-lease (not a required param) so an un-updated worker binary that omits it entirely gets the same 204 as one that sends 1 explicitly (Pitfall 4)"
  - "_build_best_move_candidates's new `source` param defaults to 'drain-local' rather than being required, so the existing eval_drain.py call site (out of this plan's scope) keeps working unchanged and is already correctly labeled"
  - "second_best tamper guard only checks in-range ply (0 <= ply < game_length), not candidate membership — an in-range-but-not-a-real-candidate ply is silently dropped at the map lookup, mirroring how a foreign-but-in-range blob token is dropped at the classify SQL join rather than 422'd (S-02/T-177-02)"

requirements-completed: [PROTO-01, PROTO-03, OBS-01]

coverage:
  - id: D1
    description: "v1 worker (or one omitting worker_schema_version) gets 204 on /atomic-lease for both scope=explicit and scope=idle, before any claim_eval_job call"
    requirement: "PROTO-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_v1_worker_204"
        status: pass
    human_judgment: false
  - id: D2
    description: "A v2 lease response carries move_uci per non-terminal position (the played move) and None for the terminal donor"
    requirement: "PROTO-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_v2_worker_carries_move_uci"
        status: pass
    human_judgment: false
  - id: D3
    description: "second_best_map built from a v2 worker's submitted second_best data eliminates the fallback for every covered ply"
    requirement: "PROTO-03"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestPitfall1Fallback::test_build_best_move_candidates_uses_submitted_second_best"
        status: pass
    human_judgment: false
  - id: D4
    description: "A second_best entry with an out-of-range ply (>= game_length) is rejected 422 before any write"
    requirement: "PROTO-03"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_second_best_out_of_range_422"
        status: pass
    human_judgment: false
  - id: D5
    description: "The residual server-side fallback branch emits a Sentry tag naming its source (worker-submit-fallback vs drain-local)"
    requirement: "OBS-01"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestPitfall1Fallback::test_best_move_candidates_fallback_source_tag"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-07-17
status: complete
---

# Phase 177 Plan 01: Protocol-v2 schema + lease version gate + second_best wiring Summary

**Wire schema for worker-computed gem-candidate second-best evals, a lease-time worker_schema_version gate covering both atomic scopes, and second_best_map threaded into `_build_best_move_candidates` with a Sentry-tagged residual fallback.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-07-17T15:36:14Z
- **Completed:** 2026-07-17T15:50:06Z
- **Tasks:** 3
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments
- Extended `app/schemas/eval_remote.py` with `LeasePosition.move_uci`, the new `AtomicSecondBestEval` model, and `AtomicSubmitRequest.second_best` (default empty list) — all backward-compatible with v1 payloads.
- Gated `/atomic-lease` on `worker_schema_version >= WORKER_SCHEMA_VERSION_MIN (2)` as the first statement in the handler, before any `claim_eval_job` call, so both `scope=explicit` and `scope=idle` 204 uniformly for a v1 (or version-omitting) worker.
- `_build_lease_positions` now emits `move_uci` per non-terminal `LeasePosition` from the already-captured `_FullPlyEvalTarget.move_uci` (no re-parse).
- `_apply_atomic_submit` tamper-guards every submitted `second_best` ply (`0 <= ply < game_length`, 422 otherwise) and builds a real `second_best_map` from the request body instead of hard-coding `None`, passing `source="worker-submit-fallback"` through to `_build_best_move_candidates`.
- `_build_best_move_candidates` gained a `source: str = "drain-local"` parameter and now tags the Pitfall-1 fallback branch with `sentry_sdk.set_tag("source", source)` plus a `set_context` carrying `game_id`/`fallback_ply_count` (never embedded in the message string, per CLAUDE.md).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add protocol-v2 schema fields for fresh-lane second-best + move_uci** - `a4419ec1` (feat)
2. **Task 2: Version-gate /atomic-lease and emit move_uci per leased position** - `83743f38` (feat)
3. **Task 3: Consume + tamper-guard second_best; source-tag the fallback branch** - `50b83097` (feat)

_No TDD RED/GREEN split — tests and implementation were committed together per task, consistent with this plan's `tdd="true"` tasks being small, tightly-scoped changes verified by the same commit's test additions._

## Files Created/Modified
- `app/schemas/eval_remote.py` - `move_uci` on `LeasePosition`; new `AtomicSecondBestEval`; `second_best[]` on `AtomicSubmitRequest`
- `app/routers/eval_remote.py` - `WORKER_SCHEMA_VERSION_MIN` constant; `worker_schema_version` Query param + 204 gate on `/atomic-lease`; `_build_lease_positions` emits `move_uci`; `_apply_atomic_submit` tamper-guards + wires `second_best_map`
- `app/services/eval_apply.py` - `_build_best_move_candidates` gains `source` param + Sentry tag/context on the fallback branch
- `tests/test_eval_worker_endpoints.py` - new schema tests, `test_atomic_lease_v1_worker_204`, `test_atomic_lease_v2_worker_carries_move_uci`, `test_atomic_submit_second_best_out_of_range_422`; updated 3 pre-existing atomic-lease tests to pass `worker_schema_version=2` (otherwise silently hit the new 204 gate)
- `tests/services/test_eval_apply.py` - `test_build_best_move_candidates_uses_submitted_second_best`, `test_best_move_candidates_fallback_source_tag`

## Decisions Made
- `worker_schema_version` defaults to `1` on `/atomic-lease` (a `Query()` default, not a required param) so an un-updated worker binary that never sends the param gets identical 204 treatment to one that explicitly sends `1` — this is the literal Pitfall-4 requirement, not an incidental default.
- `_build_best_move_candidates`'s new `source` param defaults to `"drain-local"` rather than being required. This keeps the existing `eval_drain.py:850` call site (out of this plan's `files_modified` scope) working unchanged, and the default already carries the semantically correct label for that caller — Plan 03 can make it explicit later without a functional change.
- The `second_best` tamper guard checks only structural in-range-ness (`0 <= ply < game_length`), not candidate membership. A submitted ply that is in-range but not a real played==best candidate is never rejected — it is simply never read by the map lookup in `_build_best_move_candidates`, mirroring the established blob-node precedent (S-02/T-177-02: the server never trusts *which* plies a worker chose to send, only that they're structurally in-game).

## Deviations from Plan

None — plan executed exactly as written. One path correction: the plan's `files_modified` frontmatter and task `<files>` blocks list `tests/test_eval_apply.py`, but the actual existing test module (added in Phase 174) lives at `tests/services/test_eval_apply.py`. Used the real path; not a Rule 1-3 deviation since it's a pre-existing file location, not new work.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The `second_best_map` gap-fill mechanism is fully wired for the fresh lane (tier-1/2/3); Plan 02 (tier-4b dedicated lease/submit pair) and Plan 03 (drain tier-aware minimal path, `eval_drain.py` explicit `source="drain-local"`) can build on this schema and the now-generalized `_build_best_move_candidates(source=...)` signature without further changes to this plan's files.
- `scripts/remote_eval_worker.py` (Plan 04/05 territory) still sends `WORKER_SCHEMA_VERSION = 1` and no `worker_schema_version` query param on lease — until that script is updated, the live fleet will 204 on `/atomic-lease` under this plan's gate. This is expected/by-design (S-03 rollout), not a regression, but means Plan 01 alone should NOT be deployed to production without the worker-script bump landing in the same release window, or the atomic lane goes dark for the whole fleet.

---
*Phase: 177-worker-side-multipv2-gem-candidates*
*Completed: 2026-07-17*

## Self-Check: PASSED

All 5 modified files verified present on disk; all 3 task commit hashes (a4419ec1, 83743f38, 50b83097) verified present in git log.
