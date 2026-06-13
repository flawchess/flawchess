---
phase: 117-priority-queue-flaw-integration
fixed_at: 2026-06-13T15:00:00Z
review_path: .planning/phases/117-priority-queue-flaw-integration/117-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 117: Code Review Fix Report

**Fixed at:** 2026-06-13T15:00:00Z
**Source review:** `.planning/phases/117-priority-queue-flaw-integration/117-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, WR-03, IN-02; IN-01 comment-only per instructions)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: enqueue_tier1_game guest guard passes on missing user, causing FK violation

**Files modified:** `app/services/eval_queue_service.py`
**Commit:** `6ea00163`
**Applied fix:** Changed `if is_guest:` to `if is_guest is None or is_guest:` with a bug-fix comment
explaining that `scalar_one_or_none()` returns `None` for a deleted/missing user, and that
`if None:` evaluates to `False`, bypassing the guard and reaching the FK insert.


### WR-01: _classify_and_fill_oracle swallows DB errors, permanently marking games done with no flaws

**Files modified:** `app/services/eval_drain.py`
**Commit:** `56a15e71` (plus style fix `fd4ebd44` from ruff format)
**Applied fix:** Removed the outer `try/except Exception` that wrapped the entire function body.
DB errors in `bulk_insert_game_flaws` and the oracle-count `UPDATE` now propagate to the
write-session context manager, which triggers a rollback — preventing `_mark_full_evals_completed`
and `_mark_full_pv_completed` from committing. The game is not marked complete and will be retried.

Only the per-flaw PV write loop retains individual fault tolerance via an inner `try/except`,
preserving the Sentry capture for bad PV rows. T-108-04 (one bad game must not abort the drain)
is preserved at the `run_full_eval_drain` loop level, which has its own `except Exception`.

The docstring was also updated to reflect the new exception boundary semantics, and two inline
bug-fix comments were added at `bulk_insert_game_flaws` and the oracle UPDATE explaining why
those errors must propagate.

**Note:** This fix requires human verification — the logic change (propagating vs. swallowing)
involves transaction boundary semantics. The 5 pre-existing test errors in `TestBestMove`,
`TestFlawPv`, `TestClassifyHook`, and `TestOracleCounts` (session-scoped fixture interaction
with joined eager loads when both test files run together) are unrelated to this fix and exist
on the original branch. They pass in isolation.


### WR-02: type: ignore in admin router violates project convention

**Files modified:** `app/routers/admin.py`
**Commit:** `d439f190`
**Applied fix:** Added `from typing import Annotated, Literal` and annotated `enqueue_status`
as `Literal["enqueued", "skipped_guest", "already_queued"]` from first assignment. This
eliminates the need for any suppression comment — ty infers the Literal type through all
branches, so the return type matches `EnqueueTier1Response.status` without a cast or ignore.
The `# type: ignore[arg-type]` was removed entirely.


### WR-03: Game.is_analyzed docstring is factually wrong after Phase 117

**Files modified:** `app/models/game.py`
**Commit:** `b3aefcf3`
**Applied fix:** Updated the `is_analyzed` hybrid property docstring to reflect that
`white_blunders` is non-NULL for engine-analyzed games (Phase 117+, D-117-09) as well as
Lichess games. Removed the incorrect "currently Lichess games only" claim and added a
D-117-09 reference. The `@hybrid_property` expression is unchanged.


### IN-02: _apply_full_eval_results silently discards pv_string

**Files modified:** `app/services/eval_drain.py`
**Commit:** `8107bfb5`
**Applied fix:** Added a 3-line comment at the `_pv_string` discard site in
`_apply_full_eval_results` explaining that pv is intentionally written only at flaw-adjacent
plies in `_classify_and_fill_oracle` (D-117-02), and warning against adding a general pv write
there.


### IN-01: Tier-3 derived pick double-claim race (comment only, no behavioral change)

**Files modified:** `app/services/eval_queue_service.py`
**Commit:** `7fdbafe3`
**Applied fix:** Added a `# Phase 118:` comment block at the `_claim_tier3_derived` SELECT
explaining the double-claim race, why it is accepted at Phase 117 single-worker scale, and what
to do in Phase 118 (FOR UPDATE SKIP LOCKED with a transient eval_jobs row). No behavioral
change as instructed.

---

## Gate Results

```
uv run ruff format app/ tests/  — 1 file reformatted (list comprehension in _classify_and_fill_oracle)
uv run ruff check app/ tests/  — All checks passed
uv run ty check app/ tests/    — All checks passed (zero errors)
uv run pytest tests/services/test_eval_queue.py tests/services/test_full_eval_drain.py -x
  — 22 passed; 5 pre-existing errors in session-scoped fixture (full_drain_test_user_117)
    when both files run together; all 5 tests pass when run in isolation.
    Errors are unrelated to Phase 117 fixes (fixture uses scalar_one_or_none() on a
    User query that gets joined eager loads from the preceding queue test session).
```

---

_Fixed: 2026-06-13T15:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
