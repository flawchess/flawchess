---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-
fixed_at: 2026-06-16T00:00:00Z
review_path: .planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 123: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 critical + 4 warnings; 3 info findings out of scope)
- Fixed: 5
- Skipped: 0

All in-scope findings were fixed and verified (ruff format + ruff check + ty + targeted pytest). The full Phase 123 test set (63 tests across `test_eval_worker_endpoints.py`, `test_eval_drain.py`, `test_remote_eval_worker.py`) passes, including a new CR-01 regression test.

## Fixed Issues

### CR-01: Remote entry-submit never stamps zero-target leased games — re-lease livelock

**Files modified:** `app/routers/eval_remote.py`, `tests/test_eval_worker_endpoints.py`
**Commit:** 4071cfe2
**Status:** fixed: requires human verification (liveness/correctness logic — confirm the lease-ownership stamping semantics match the intended D-09 / R-02 invariant)
**Applied fix:** Used the review's Option B (no schema/worker change). The worker already sends `X-Worker-Id` on every request, so `entry_submit_eval` now takes a `worker_id` dependency and, at submit time, queries the full set of games leased to this worker that are still pending (`entry_eval_leased_by == worker_id AND evals_completed_at IS NULL`). It stamps `evals_completed_at` on that **full leased set** — including zero-target games that never appear in `body.evals` — mirroring the in-process server pool's "stamp every claimed game" invariant. This breaks the re-lease livelock where unreachable-ply games bounced between TTL cycles forever. Added `test_entry_submit_stamps_full_leased_set_including_zero_target_games`: it leases a batch containing zero-target padding games (no `game_positions`), submits only the one real game's evals, and asserts a leased zero-target padding game is still stamped `evals_completed_at`.

### WR-02: entry-submit trusts worker-supplied game_id without verifying the lease

**Files modified:** `app/routers/eval_remote.py`
**Commit:** 4071cfe2 (folded into the CR-01 entry-submit rework — same handler, interrelated logic)
**Applied fix:** `game_ids_submitted` is now filtered to the lease-owned pending set (`leased_set` computed for CR-01). Re-derivation, classification, and eval application only run for submitted game_ids the worker actually holds a live lease on. A stale or wrong game_id from a buggy/out-of-sync worker is ignored rather than stamping/classifying an unrelated game. (Not an authz hole — the operator is trusted — but the submit body never proved a game was leased.)

### WR-04: entry-submit failure leaves leases live for the full TTL with no release

**Files modified:** `app/routers/eval_remote.py`
**Commit:** 4071cfe2 (folded into the CR-01 entry-submit rework — same `except` block)
**Applied fix:** On a write-phase exception, after capturing to Sentry the handler now best-effort clears the leases (`entry_eval_lease_expiry = NULL`, `entry_eval_leased_by = NULL`) for the leased set in a fresh session before re-raising, so the games are reclaimable immediately instead of stalling for the full 20s TTL. Mirrors the full-ply path's explicit `release_job` "release now, don't wait for TTL" design. The release runs in its own session (the failed `write_session` rolled back) and its own try/except so a release failure is captured but does not mask the original exception.

### WR-01: X-Worker-Id header is unvalidated and overflows VARCHAR(16) on entry-lease

**Files modified:** `app/routers/eval_remote.py`
**Commit:** 0af103d0
**Applied fix:** `worker_id_label` now truncates the resolved label to 16 chars (`label[:16]`), so a long `X-Worker-Id` header can never overflow `games.entry_eval_leased_by` (VARCHAR(16)) and surface as an unhandled 500 on entry-lease. Defense-in-depth — the worker's own `< 10`-char validation is not authoritative server-side. `eval_jobs.leased_by` is VARCHAR(100), so truncating to 16 is safe for the full-ply path too.

### WR-03: Backlog probe counts leased rows, masking an all-leased empty claim

**Files modified:** `app/routers/eval_remote.py`
**Commit:** f3c96be3
**Applied fix:** The D-5 backlog existence probe now uses the same predicate as `_claim_entry_eval_games`: added `AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())` to the probe SQL. Probe and claim stay in lock-step, so a deep-but-fully-leased backlog no longer passes the probe only to have the claim return `[]` and waste a claim transaction per cycle near the tail.

## Skipped Issues

None — all in-scope findings were fixed.

### Out-of-scope (Info) findings — for reference

These were below the `critical_warning` fix scope and were not separately addressed, except IN-01 which was incidentally resolved:

- **IN-01** (Sentry context `worker_id` static literal): incidentally fixed in commit 4071cfe2 — the entry-submit Sentry context now reports the real `worker_id` instead of the `"entry-submit"` literal, since the handler now has the worker identity.
- **IN-02** (EntrySubmitEval.game_id bounds / per-request game cap): not addressed (Info, out of scope). WR-02's handler-side lease filter already enforces the "evals must belong to the leased batch" trust boundary at runtime.
- **IN-03** (entry-lease claim-order re-sort asymmetry): not addressed (Info, out of scope). Order does not affect correctness for entry-ply.

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
