---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, entry-ply, skip-locked, operator-token, scope-param, worker-id, tdd]

# Dependency graph
requires:
  - phase: 123-01
    provides: "_claim_entry_eval_games, ENTRY_LEASE_* constants, games.entry_eval_leased_by column, WORKER_ID_SERVER_POOL"
  - phase: 120-remote-eval-worker
    provides: "require_operator_token, claim_eval_job, LeaseResponse/SubmitRequest schemas, _WORKER_ID_REMOTE"
  - phase: 91-cold-eval-drain
    provides: "_apply_eval_results, _apply_full_eval_results, _collect_eval_targets_from_db, _mark_evals_completed, _classify_and_insert_flaws"
provides:
  - "POST /eval/remote/entry-lease — batched entry-ply lease endpoint (D-07), D-5 backlog-gated"
  - "POST /eval/remote/entry-submit — batched entry-ply submit endpoint (D-07), no-shift write path"
  - "scope: Literal['explicit','idle']|None param on /lease + claim_eval_job (D-05)"
  - "worker_id_label dependency: X-Worker-Id header → leased_by/entry_eval_leased_by; absent → 'remote-worker' (D-10)"
  - "EntryLeasePosition / EntryLeaseResponse / EntrySubmitEval / EntrySubmitRequest / EntrySubmitResponse schemas"
affects:
  - 123-03-worker-ladder

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-5 backlog probe: SELECT 1 ... ORDER BY id DESC LIMIT 1 OFFSET :offset with offset=THRESHOLD-1; returns 204 when shallow"
    - "scope=None: bundled tier-1>2>3 (backward-compat); scope=explicit: tier-1/2 only; scope=idle: tier-3 only"
    - "worker_id_label FastAPI dependency: Header(alias='X-Worker-Id') or _WORKER_ID_REMOTE fallback"
    - "Entry-submit: _apply_eval_results (no +1 shift) NOT _apply_full_eval_results — critical SEED-044 path distinction"
    - "Commit-before-work: entry-lease commits SKIP-LOCKED claim then derives FENs in a new session"

key-files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/services/eval_queue_service.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "D-02: D-5 backlog gate is remote-lease-only; server pool (_pick_pending_game_ids) does NOT run this probe"
  - "D-05: scope=None is backward-compat bundled flow; explicit/idle select single tiers — zero-coordination rollout"
  - "D-07: /entry-lease derives FENs server-side via _collect_eval_targets_from_db; worker never parses PGN"
  - "D-10: X-Worker-Id is advisory only (T-123-03 accept); never used for authz — operator-token is the real gate"
  - "_apply_eval_results vs _apply_full_eval_results: entry-ply uses no-shift path; verified by test_entry_submit_no_shift"

patterns-established:
  - "worker_id_label as a shared FastAPI Depends for both entry and full-ply endpoints"
  - "Two-session discipline in /entry-lease: claim session committed and closed; FEN derivation in second session"
  - "Server re-derives EvalTargets in /entry-submit (game_id → server-controlled ply/endgame_class) — worker can only contribute eval_cp/eval_mate"

requirements-completed: ["SEED-051-D-2", "SEED-051-D-5", "SEED-051-D-7", "D-02", "D-05", "D-07", "D-09", "D-10"]

# Metrics
duration: ~20min
completed: 2026-06-16
---

# Phase 123 Plan 02: Entry Endpoints Summary

**Batched /entry-lease + /entry-submit endpoints with D-5 backlog gate, no-shift write path, scope selector on /lease, and X-Worker-Id advisory label — all behind existing operator-token auth**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-16T05:35:00Z
- **Completed:** 2026-06-16T05:51:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Five entry-ply Pydantic schemas added to `app/schemas/eval_remote.py`: `EntryLeasePosition`, `EntryLeaseResponse`, `EntrySubmitEval`, `EntrySubmitRequest`, `EntrySubmitResponse` — batch-keyed by `game_id`, depth-15 only (no `best_move`/`pv`), reuse `MAX_SUBMIT_EVALS` DoS cap (T-123-05)
- `claim_eval_job` gains `scope: Literal["explicit", "idle"] | None = None`: None = bundled tier-1>2>3 (backward-compat), explicit = tier-1/2 only, idle = tier-3 only; `ty check` clean throughout
- `worker_id_label` FastAPI dependency reads `X-Worker-Id` header (advisory only); absent → `"remote-worker"` fallback (D-10); wired into both new and existing `/lease` endpoint
- `POST /eval/remote/entry-lease`: D-5 backlog probe (OFFSET=THRESHOLD-1 bound as `:param`, never f-string); returns 204 when backlog < 300; commits SKIP-LOCKED claim, derives FENs in second session; returns `EntryLeaseResponse` with `{game_id, ply, fen}` per position
- `POST /eval/remote/entry-submit`: SF-version gate first (T-123-07); re-derives `_EvalTarget`s server-side (Pitfall 1 / T-123-04); applies via `_apply_eval_results` (NO +1 shift — critical path distinction vs full-ply `/submit`); classifies flaws; stamps `evals_completed_at`; idempotent (ON CONFLICT DO NOTHING)
- 17 new tests covering: auth (missing/wrong token), D-5 gate boundary (THRESHOLD-1 → 204, THRESHOLD → 200), entry-lease positions, entry-submit no-shift, stamps `evals_completed_at`, idempotency, scope selection (explicit/idle/absent), X-Worker-Id population and fallback — all 38 tests in the file pass (2694 total suite pass)

## Task Commits

1. **Task 1: Entry-ply schemas + scope param** — `52afee9f` (feat)
2. **Task 2: /entry-lease + /entry-submit endpoints** — `1d9a2110` (feat)
3. **Task 3: TDD tests** — `034ea085` (test)

## Files Created/Modified

- `app/schemas/eval_remote.py` — 5 new entry-ply schemas appended in a clearly delimited section
- `app/services/eval_queue_service.py` — `scope` param added to `claim_eval_job`; three branches: scope=None (bundled, unchanged), scope="explicit" (early return after tier-1/2), scope="idle" (skip to tier-3 only)
- `app/routers/eval_remote.py` — `worker_id_label` dependency; scope param on `/lease`; two new endpoints `/entry-lease` and `/entry-submit` with Sentry instrumentation
- `tests/test_eval_worker_endpoints.py` — URL constants, `_get_game_entry_eval_leased_by` helper, `_patch_router_session` patching `eval_drain.async_session_maker`, `_insert_game_positions` accepting `phase` kwarg, 17 new test functions

## Decisions Made

- `scope=None` is the exact bundled behavior unchanged (D-05 backward-compat for un-upgraded workers)
- D-5 probe uses `OFFSET = THRESHOLD - 1` (299) — THRESHOLD-th row is at OFFSET 299 (0-indexed); at THRESHOLD rows present the offset finds a row and the gate opens (Pitfall 6 boundary)
- Server re-derives `_EvalTarget`s in `/entry-submit` so worker can only contribute `eval_cp`/`eval_mate` for server-chosen plies — T-123-04 mitigation
- Two-session discipline in `/entry-lease`: claim session is committed and closed; FEN derivation opens a fresh session — no concurrent session use
- `_apply_eval_results` (no shift) vs `_apply_full_eval_results` (+1 shift): entry-ply evals sit at the correct `ply` already; applying the post-move shift would corrupt every stored eval; `test_entry_submit_no_shift` asserts this invariant

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _insert_game_positions lacked phase kwarg — phase=0 rows produce no entry targets**
- **Found during:** Task 3 test development
- **Issue:** `_collect_target_specs` requires `phase == 1` (midgame) to yield a `middlegame_entry` target. The existing `_insert_game_positions` helper hardcoded `phase=0` for all rows
- **Fix:** Added `phase=r.get("phase", 0)` to the INSERT loop; tests pass `"phase": 1` for entry-ply target rows
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** `test_entry_lease_returns_positions` passes with non-empty positions list

**2. [Rule 1 - Bug] _patch_router_session only patched eval_remote's session maker, not eval_drain's**
- **Found during:** Task 3 test development
- **Issue:** `_load_pgns_for_games` (called inside `/entry-lease`) opens sessions via `eval_drain.async_session_maker`, not the router's local binding; without patching it, PGN loading returned empty results and no positions were generated
- **Fix:** Extended `_patch_router_session` to also `monkeypatch.setattr(eval_drain_module, "async_session_maker", session_maker)`
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** Positions list is non-empty; all entry tests pass

**3. [Rule 1 - Bug] LIFO insertion order: game with positions must be inserted LAST**
- **Found during:** Task 3 test development
- **Issue:** `/entry-lease` claims games in LIFO order (id DESC, BATCH_SIZE=50). If the game with positions was inserted first (lower ID) and padding after (higher IDs), it fell outside the first 50 and was never leased in the test. The padding games had no positions so their entry targets were empty
- **Fix:** Inserted all padding games first (lower IDs) and the game with positions last (highest ID) in `test_entry_lease_returns_positions`, `test_entry_submit_no_shift`, `test_entry_submit_stamps_evals_completed_at`, `test_entry_submit_idempotent`, and the worker-id tests
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** All affected tests pass

**4. [Rule 1 - Bug] Worker-id tests checked positions list, but games without positions have empty lists**
- **Found during:** Task 3 test development
- **Issue:** `test_worker_id_header_populates_leased_by_on_entry_lease` and `test_worker_id_absent_falls_back_to_remote_worker_on_entry_lease` originally derived `leased_game_ids` from `body["positions"]`; when padding games (no positions) are the ones leased, the list is empty and the assertion never fires
- **Fix:** Both tests now iterate over all `game_ids` and query `entry_eval_leased_by` directly from the DB, asserting `found_any` at the end
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** Both worker-id tests pass

---

**Total deviations:** 4 auto-fixed (all Rule 1 bugs discovered during TDD test development; no scope creep)
**Impact on plan:** All fixes necessary for test correctness. No behavioral changes to production code.

## Issues Encountered

None beyond the four TDD test setup bugs fixed above.

## User Setup Required

None — no external service configuration required. Worker binary updates (Plan 03) are in the next wave.

## Next Phase Readiness

- Plan 03 (worker ladder, D-10 worker IDs, binary packaging) can now call `/entry-lease` + `/entry-submit` — both endpoints are live and tested
- The `scope` param on `/lease` allows the new worker binary to send `scope=explicit` or `scope=idle` without affecting the un-upgraded server (zero-coordination rollout, D-05)
- All SEED-051 design decisions for the server side (D-02, D-05, D-07, D-09, D-10) are implemented and green

## Self-Check: PASSED

Files confirmed:
- `app/schemas/eval_remote.py`: FOUND (EntryLeaseResponse present)
- `app/services/eval_queue_service.py`: FOUND (scope param present)
- `app/routers/eval_remote.py`: FOUND (/entry-lease, /entry-submit present)
- `tests/test_eval_worker_endpoints.py`: FOUND (17 new tests)
Commits confirmed:
- `52afee9f`: FOUND
- `1d9a2110`: FOUND
- `034ea085`: FOUND
All 2694 tests pass (full suite, 2026-06-16).

---
*Phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big*
*Completed: 2026-06-16*
