---
phase: 121-remote-worker-tier1-claiming
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/routers/eval_remote.py
  - app/schemas/eval_remote.py
  - scripts/remote_eval_worker.py
  - tests/test_eval_worker_endpoints.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: resolved
resolution: "WR-01 fixed in 9627e80c (release_job on lichess-defer + regression test); IN-01/IN-02 stale docstrings fixed. IN-03/IN-04 left as accepted nits."
---

# Phase 121: Code Review Report

> **Resolution (2026-06-15):** WR-01 fixed in commit `9627e80c` — the remote lease
> handler now calls `release_job(job_id)` when it defers a lichess-eval game, so the
> `eval_jobs` row returns to `pending` immediately instead of sitting `leased` for the
> full TTL. A regression test (`test_lichess_eval_game_claim_releases_lease`) locks it.
> IN-01 / IN-02 stale tier-3-only docstrings were refreshed in the same commit.
> IN-03 (R2 docstring traceability) and IN-04 (Path B no-stamp regression test) are
> accepted as low-value nits and left for a future touch.

# Phase 121: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 121 wires `lease_eval_game` to `claim_eval_job` (tier-1 > tier-2 > tier-3), threads an opaque `job_id` token through the lease/submit round-trip, stamps `eval_jobs.status='completed'` in `_apply_submit` (guarded by `WHERE status='leased'`), lowers `DEFAULT_IDLE_SLEEP` from 5.0 to 1.0, and adds `TestTier1Claiming` tests.

The core security properties hold: `require_operator_token` is unchanged on both endpoints; the `WHERE status='leased'` idempotency guard is correctly copied from `eval_drain._full_drain_tick`; SKIP LOCKED double-claim prevention is DB-level (unchanged); dead import `_claim_tier3_derived` is removed; no new session context wraps `claim_eval_job`. Session hygiene, type safety, and Sentry patterns all follow project conventions.

One warning is raised: the 204 early-return in `lease_eval_game` for lichess games now leaks an `eval_jobs` lease in a scenario that was impossible before this phase, because the remote worker can now claim tier-1 (rather than only tier-3 derived) jobs.

---

## Warnings

### WR-01: Tier-1 lichess game claim leaks the `eval_jobs` lease

**File:** `app/routers/eval_remote.py:343-347`

**Issue:** When `claim_eval_job` returns a tier-1 `ClaimedJob` with `is_lichess_eval_game=True`, the lease handler returns 204 (line 347) without stamping the `eval_jobs` row. The row stays `leased` (with `leased_by='remote-worker'`) until the TTL sweep (`LEASE_TTL_SECONDS`, nominally 120 s) resets it to `pending`.

Before Phase 121 the remote worker called `_claim_tier3_derived`, which produces no `eval_jobs` row. The leak was impossible. Now that the remote worker calls `claim_eval_job`, it can claim a tier-1 job for a lichess game — `enqueue_tier1_game` does not filter on `lichess_evals_at`, so a user triggering `POST /api/imports/analyze/{game_id}` for a lichess game creates a tier-1 `eval_jobs` row that the remote worker can win via SKIP LOCKED.

If the remote worker wins the claim race repeatedly, the lichess game enters a 120 s-per-cycle churn: claim → 204 → sweep → pending → claim again. The server drain (which processes lichess games correctly via `_full_drain_tick`) cannot make progress until it wins a SKIP LOCKED race cycle. In practice this is bounded (one 120 s delay per claim the remote worker wins), but it is a correctness regression invisible to monitoring.

The `eval_drain._full_drain_tick` does not have this problem: when it claims a lichess game it processes it fully (flaw-adjacent PVs + markers) and stamps the `eval_jobs` row on completion. The remote lease handler is the only path that holds the lease without either processing the game or releasing the row.

**Fix:** Stamp the leased row as completed (or a new `'deferred'` status) before returning 204 for the lichess-game path. The pattern already exists for Path A/C below. A minimal fix reuses `report_job_complete`:

```python
# D-4 / v1 scope: lichess PV-backfill games deferred to v2.
if is_lichess_eval_game:
    # Release the lease so the server drain can pick it up immediately.
    # Without this, the eval_jobs row stays 'leased' until the TTL sweep (~120s),
    # blocking the server drain from processing the game during that window.
    if claim.job_id is not None:
        from app.services.eval_queue_service import report_job_complete
        await report_job_complete(claim.job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Alternatively, stamp it to `'completed'` inline with the same pattern used in `_apply_submit` (lines 282-292). Using `report_job_complete` is cleaner since it already exists and carries the same `WHERE status='leased'` guard.

---

## Info

### IN-01: Stale module docstring in `eval_remote.py` — still says "tier-3 game"

**File:** `app/routers/eval_remote.py:3`

**Issue:** The module-level docstring reads:

```
POST /eval/remote/lease  — claim one tier-3 game and return its (ply, FEN) positions.
```

After Phase 121 the lease endpoint claims tier-1 > tier-2 > tier-3.

**Fix:** Update line 3 to:

```
POST /eval/remote/lease  — claim the next eval game (tier-1 > tier-2 > tier-3) and return its FEN positions.
```

---

### IN-02: Stale module docstring in `remote_eval_worker.py` — says "tier-3" in two places

**File:** `scripts/remote_eval_worker.py:3` and `scripts/remote_eval_worker.py:245`

**Issue:** Line 3 reads "lease a tier-3 game from the FlawChess API". Line 245 (argparse description) reads "lease tier-3 game → eval via EnginePool". Both are stale after Phase 121 which enables tier-1/2 claiming.

**Fix:**

- Line 3: "Loops: lease the highest-priority available game (tier-1 > tier-2 > tier-3) from the FlawChess API"
- Line 245: "lease game (tier-1 > tier-2 > tier-3) → eval via EnginePool → batch submit (Phase 121 SEED-048)."

---

### IN-03: R2 omitted from `TestTier1Claiming` class docstring

**File:** `tests/test_eval_worker_endpoints.py:679`

**Issue:** The `TestTier1Claiming` class docstring says "Tests R1, R3, R4, R5, R6". R2 (lease with a tier-3 claim returns `job_id=None` in the response) is tested in the existing `test_lease_returns_positions` (line 351: `assert body["job_id"] is None`), not in the new class. The docstring omitting R2 creates a gap in traceability for readers consulting the validation matrix.

**Fix:** Either add a brief note "R2 is covered by `test_lease_returns_positions`" to the class docstring, or promote the R2 assertion into a dedicated `TestTier1Claiming` method that mocks a tier-3 `ClaimedJob` and asserts `job_id=None` in the response.

---

### IN-04: Path B (holes remain, `stamp_complete=False`, `job_id` present) has no regression test

**File:** `tests/test_eval_worker_endpoints.py` (no specific line — test is missing)

**Issue:** The PLAN behavioral requirements specify: "Submit with `job_id` present but Path B (holes under cap, `stamp_complete=False`) → eval_jobs NOT stamped (leave for sweep/retry)." This is correctly implemented at `app/routers/eval_remote.py:282` (`if body.job_id is not None and stamp_complete:`), but the test suite has no case that seeds a game with a gap (some plies missing from the eval submission), submits with a `job_id`, and asserts the `eval_jobs` row is NOT stamped to `'completed'`. The absence means a future regression (e.g., removing the `and stamp_complete` guard) would not be caught.

**Fix:** Add a test in `TestTier1Claiming` that seeds a game, seeds a `leased` eval_jobs row, submits with `job_id` but only provides evals for a subset of plies (so `failed_ply_count > 0` and `stamp_complete=False`), then asserts the `eval_jobs` row remains `'leased'` rather than `'completed'`.

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
