---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 01
subsystem: database
tags: [postgresql, sqlalchemy, alembic, skip-locked, lease, eval-drain, entry-ply]

# Dependency graph
requires:
  - phase: 122-feedback
    provides: "Current Alembic head (7d5a4aa09a47)"
  - phase: 120-remote-eval-worker
    provides: "eval_queue_service.WORKER_ID_SERVER_POOL, claim_eval_job, SKIP-LOCKED pattern"
  - phase: 91-cold-eval-drain
    provides: "_pick_pending_game_ids, run_eval_drain, ix_games_evals_pending, _mark_evals_completed"
provides:
  - "games.entry_eval_lease_expiry (DateTime tz, nullable) — entry-ply lease TTL column"
  - "games.entry_eval_leased_by (VARCHAR(16), nullable) — worker-id observability column (D-09)"
  - "_claim_entry_eval_games(session, worker_id, batch_size, ttl_seconds) — shared SKIP-LOCKED LIFO claim helper"
  - "ENTRY_LEASE_TTL_SECONDS=20, ENTRY_LEASE_BATCH_SIZE=50, ENTRY_LEASE_BACKLOG_THRESHOLD=300 — named tuning constants"
  - "_pick_pending_game_ids now leases through _claim_entry_eval_games (D-01 server partition)"
  - "_insert_game test fixture evals_completed_at kwarg for pending-game insertion"
affects:
  - 123-02-entry-lease-submit-endpoints
  - 123-03-worker-ladder

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UPDATE ... WHERE id IN (SELECT ... FOR UPDATE SKIP LOCKED) RETURNING — shared LIFO lease claim over games"
    - "Commit-before-work discipline: _pick_pending_game_ids commits lease before engine drain"
    - "TTL reclaim: entry_eval_lease_expiry < now() predicate re-opens crashed batch"

key-files:
  created:
    - alembic/versions/20260616_120000_phase_123_entry_eval_lease.py
  modified:
    - app/models/game.py
    - app/services/eval_drain.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/test_eval_drain.py

key-decisions:
  - "D-01: _pick_pending_game_ids is now a lease claim (SKIP LOCKED) — server and remote workers partition the same import"
  - "D-03/D-04: ENTRY_LEASE_TTL_SECONDS=20 (short; entry batches are seconds of work; well under full-ply 120s)"
  - "D-09: entry_eval_leased_by is VARCHAR(16) not TEXT — fits 'remote-worker' (13 chars) and short worker IDs"
  - "RETURNING clause order: _pick_pending_game_ids sorts result DESC to preserve D-11 LIFO list contract"
  - "Crash recovery: crashed games reclaimable via TTL expiry (not instant); test_eval_drain updated to reflect"

patterns-established:
  - "Shared claim helper: both server and remote endpoints call _claim_entry_eval_games — single canonical claim"
  - "Module-level constants with rationale comments for tuning knobs (D-03 style)"
  - "Lease default in _insert_game: evals_completed_at=_EVALS_NOW preserves pre-Phase-123 test behavior; pass None for pending"

requirements-completed: ["SEED-051-D-1", "SEED-051-D-3", "SEED-051-D-9", "D-01", "D-03", "D-04", "D-09"]

# Metrics
duration: 45min
completed: 2026-06-16
---

# Phase 123 Plan 01: Foundation Lease Claim Summary

**Alembic migration adds entry-ply lease columns to games; shared SKIP-LOCKED LIFO claim helper partitions server and remote workers; D-01 server drain commits lease before engine work**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-16T12:00:00Z
- **Completed:** 2026-06-16T12:45:00Z
- **Tasks:** 3 (+ 2 Rule 1 bug fixes)
- **Files modified:** 5

## Accomplishments
- Migration adds `entry_eval_lease_expiry` (DateTime tz) and `entry_eval_leased_by` (VARCHAR(16)) to `games` — round-trips clean
- `_claim_entry_eval_games` is the single canonical SKIP-LOCKED LIFO claim helper: one `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING` with all values bound as `:params`
- D-01 implemented: `_pick_pending_game_ids` now calls `_claim_entry_eval_games` with `WORKER_ID_SERVER_POOL` and commits before drain work
- Three named tuning constants (TTL 20s, batch 50, threshold 300) with inline rationale comments
- Four new lease tests: partition (disjoint), LIFO ordering, TTL reclaim, leased_by population — all green

## Task Commits

1. **Task 1: Migration + model columns** — `8a3c84b3` (feat)
2. **Task 2: Shared claim helper + constants + D-01 server lease** — `95605ae5` (feat)
3. **Task 3: Lease-partition + TTL-reclaim tests** — `313b0965` (test)
4. **Style: ruff formatting** — `979be4b5` (style)
5. **Rule 1 fixes: RETURNING sort + crash test update** — `f09138bc` (fix)

## Files Created/Modified
- `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py` — migration adding 2 nullable cols to games, no backfill, no new index
- `app/models/game.py` — `entry_eval_lease_expiry` and `entry_eval_leased_by` mapped_columns in eval-marker block
- `app/services/eval_drain.py` — `ENTRY_LEASE_*` constants, `_claim_entry_eval_games` helper, D-01 `_pick_pending_game_ids` rewrite
- `tests/test_eval_worker_endpoints.py` — `_insert_game` `evals_completed_at` kwarg + 4 new lease tests
- `tests/services/test_eval_drain.py` — crash test updated to reflect D-01 lease-based re-pick semantics

## Decisions Made
- `ENTRY_LEASE_TTL_SECONDS = 20`: short but generous — entry batches are seconds of work; RESEARCH Pitfall 3 recommends 15–30s; 20s is the midpoint
- `_claim_entry_eval_games` returns IDs in arbitrary RETURNING order; `_pick_pending_game_ids` sorts DESC to preserve the D-11 LIFO list-ordering contract asserted by `TestLifoOrder`
- `_EVALS_NOW` module-level sentinel in test fixture (not a per-call `datetime.now()`) matches legacy hardcoded-at-import behavior and avoids default-argument-is-mutable footgun

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RETURNING clause order not guaranteed**
- **Found during:** Task 2 implementation (running full test suite)
- **Issue:** `UPDATE … RETURNING id` does not guarantee row order; `TestLifoOrder.test_lifo_order` asserts `picked == expected` with exact descending order
- **Fix:** Added `sorted(game_ids, reverse=True)` in `_pick_pending_game_ids` after the lease claim returns
- **Files modified:** `app/services/eval_drain.py`
- **Verification:** `TestLifoOrder` passes; full suite green
- **Committed in:** `f09138bc`

**2. [Rule 1 - Bug] test_idempotent_on_simulated_crash expected instant re-pick after crash**
- **Found during:** Task 2 implementation (running full test suite)
- **Issue:** Test step (c) called `_pick_pending_game_ids` immediately after a simulated crash and expected the games to appear. With D-01, the lease was already committed before the crash, so the games have an active lease and are NOT instantly re-pickable
- **Fix:** Updated test step (c) to back-date the leases (simulate TTL expiry) then verify re-pick. Preserves the core T-91-09 invariant: games ARE reclaimable after the TTL, just not instantly
- **Files modified:** `tests/services/test_eval_drain.py`
- **Verification:** `TestIdempotentOnSimulatedCrash` passes; full suite green (2677 passed)
- **Committed in:** `f09138bc`

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs caused by D-01's changed _pick_pending_game_ids semantics)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the two D-01 behavioral regressions fixed above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Plan 02 (`/entry-lease` + `/entry-submit` endpoints) can now call `_claim_entry_eval_games` directly — the shared helper, constants, and columns are all in place
- Plan 03 (worker ladder, D-10 worker IDs) depends on the endpoint shape from Plan 02
- Migration is deployed to dev DB and verified round-trip

## Self-Check: PASSED

All files created, all commits present, key content verified:
- migration file: FOUND
- game model: FOUND
- eval_drain.py: FOUND
- SUMMARY.md: FOUND
- Commits 8a3c84b3, 95605ae5, 313b0965, f09138bc: all FOUND
- `_claim_entry_eval_games`, `ENTRY_LEASE_TTL_SECONDS`, `entry_eval_leased_by`, `FOR UPDATE SKIP LOCKED`: all FOUND

---
*Phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big*
*Completed: 2026-06-16*
