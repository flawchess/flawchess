---
phase: 176-backfill
reviewed: 2026-07-17T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py
  - app/core/config.py
  - app/models/eval_jobs.py
  - app/models/game.py
  - app/services/eval_apply.py
  - app/services/eval_queue_service.py
  - app/services/maia_engine.py
  - tests/services/test_eval_queue.py
  - tests/services/test_full_eval_drain.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
  warning_resolved: 1
status: resolved
---

> **Resolution note (post-review):** WR-01 fixed in commit `83fe9dde` — the D-04
> migration stamp now requires `full_pv_completed_at IS NOT NULL` and stamps that
> timestamp directly (no `now()` fallback). The two info items are accepted as-is
> (inherited no-lock lottery shape; minor optional test-coverage note).

# Phase 176-backfill: Code Review Report

**Reviewed:** 2026-07-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the tier-4b best-move backfill lottery (Phase 176 BACK-01): the new
`games.best_moves_completed_at` column + partial index, the D-04 one-time
migration stamp, the `_claim_tier4_bestmove` ES lottery rung, the
`BEST_MOVE_BACKFILL_ENABLED` kill-switch, and the `is_maia_available()`
guardrail wired through `apply_completion_decision`.

The core guardrail — never stamping `best_moves_completed_at` when Maia is
absent — is correctly implemented and is proven by an explicit negative
(mutation-test-style) assertion in `test_full_eval_drain.py`
(`test_maia_absent_never_stamps_best_moves_completed_at`), not just a positive
happy-path check. The partial-index predicate is byte-identical between
`app/models/game.py` and the migration, as the model's own comment demands.
The two config gates (`EVAL_AUTO_DRAIN_ENABLED` and `BEST_MOVE_BACKFILL_ENABLED`)
are both checked, in the right order (cheap flag check before the DB
round-trip), and the only call site of `apply_completion_decision` threads
`maia_available` through correctly — there is no bypass path via
`eval_drain.py` or `eval_remote.py` that could stamp the column without the
guard.

One real defect was found in the migration's D-04 one-time backfill: its
`EXISTS (game_best_moves)` proxy for "best-move pass already ran" is not
equivalent to "the pass actually completed" (`full_pv_completed_at IS NOT
NULL`), because `game_best_moves` rows are upserted unconditionally on every
`apply_full_eval` pass — including Path B (holes remain, under the retry cap)
where neither completion marker is stamped. See CR-01 below. The concurrency
shape (plain SELECT, no locking) is correctly inherited from the existing
tier-3/tier-4 pattern and is not a new risk introduced by this phase, but is
worth flagging as informational since the task explicitly asked to check it.

## Warnings

### WR-01: Migration D-04 backfill can stamp `best_moves_completed_at` on games whose best-move pass never actually completed

**File:** `alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py:38-46`

**Issue:** The one-time backfill uses `EXISTS (SELECT 1 FROM game_best_moves gbm
WHERE gbm.game_id = g.id)` as a proxy for "this game's best-move pass already
ran to completion." That proxy is unsound: `app/services/eval_apply.py`'s
`apply_full_eval` calls `_upsert_best_move_rows(write_session, best_move_rows)`
*unconditionally*, before `apply_completion_decision` runs (lines 2093-2138).
On Path B (`failed_ply_count > 0 AND new_attempts < MAX_EVAL_ATTEMPTS`), the
game is left pending — `full_pv_completed_at` and `full_evals_completed_at`
stay `NULL`, and `full_eval_attempts` is merely incremented — but any
best-move candidates already found on that (incomplete) pass are still
persisted to `game_best_moves`. Such a game satisfies the migration's `EXISTS`
predicate while `full_pv_completed_at IS NULL`, so the `UPDATE` fires:

```sql
SET best_moves_completed_at = COALESCE(g.full_pv_completed_at, now())
```

Since `full_pv_completed_at` is NULL for this row, the `COALESCE` falls
through to `now()`, stamping `best_moves_completed_at` on a game the rest of
the system still considers eval-incomplete. This directly contradicts the
column's own docstring in `app/models/game.py` ("NULL = best-move pass not yet
attempted (or attempted with Maia absent)" and the self-termination predicate
comment that treats `full_pv_completed_at IS NOT NULL` and
`best_moves_completed_at IS NULL` as the two halves of one coherent
lifecycle). The presence of the `COALESCE(..., now())` fallback is itself a
tell — it exists only to paper over exactly this case, rather than the
migration excluding it.

Functionally this does **not** corrupt the tier-4b lottery routing itself:
`_claim_tier4_bestmove`'s predicate requires `full_pv_completed_at IS NOT
NULL AND best_moves_completed_at IS NULL`, so a row with `best_moves_completed_at`
prematurely set (while `full_pv_completed_at` stays NULL) is simply excluded
from tier-4b — it will next be picked up by the still-active Path B retry
cycle for tier-1/2/3 instead, and if/when that game finally reaches Path A/C
its `_mark_best_moves_completed` call re-stamps it harmlessly. The bug is a
data-integrity/timestamp-accuracy defect (a "completed" marker recording a
pass that was actually still mid-retry), not an availability/lockout bug, and
is confined to the one-time migration run against whatever fraction of the
existing games corpus happens to be stuck in Path B retry with partial
`game_best_moves` coverage at deploy time.

**Fix:** Gate the backfill on the real completion signal instead of the
`game_best_moves` proxy, and drop the now-unreachable `COALESCE` fallback:

```sql
UPDATE games g
SET best_moves_completed_at = g.full_pv_completed_at
WHERE g.full_pv_completed_at IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM game_best_moves gbm WHERE gbm.game_id = g.id
  )
```

This preserves the intent (skip re-draining games that already have
best-move coverage) while never stamping a game whose pass hasn't actually
finished.

## Info

### IN-01: Tier-4b inherits tier-3/tier-4's "no locking, double-claim possible" concurrency shape

**File:** `app/services/eval_queue_service.py:666-743`

**Issue:** `_claim_tier4_bestmove` is a plain `SELECT` with no `FOR UPDATE SKIP
LOCKED` and no eval_jobs row, exactly like `_claim_tier4_blob` and
`_claim_tier3_derived`. If the in-process drain ever runs more than one
concurrent tick (e.g., to keep multiple Stockfish pool workers busy), two
ticks could pick the same game_id and run two concurrent `apply_full_eval`
write-session transactions against it (concurrent `game_best_moves` upserts,
concurrent `game_flaws` diff/upsert, concurrent `games` UPDATEs). This is not
a new risk introduced by this phase — the module's own docstring documents it
as an accepted, deferred trade-off for tier-3/4 ("Add FOR UPDATE SKIP LOCKED
when multi-worker leasing is added") — but since the task explicitly asked to
check the concurrency shape of the new rung, it's worth confirming there is no
tier-4b-specific mitigation beyond what tier-4 already has, and that the same
inherited risk now also applies to `game_best_moves`/`best_moves_completed_at`.

**Fix:** No action required unless/until the in-process drain is changed to
run concurrent ticks against the derived tiers (3/4/4b) — at that point,
apply the same `FOR UPDATE SKIP LOCKED` treatment tier-1/2 already has, or
accept the documented idempotent-but-wasteful double-claim trade-off
uniformly across tiers 3/4/4b.

### IN-02: No test asserts `BEST_MOVE_BACKFILL_ENABLED=True` alone (without `EVAL_AUTO_DRAIN_ENABLED`) fails to reach tier-4b

**File:** `tests/services/test_eval_queue.py:2032-2380`

**Issue:** `TestTier4bBestMoveBackfill` covers `BEST_MOVE_BACKFILL_ENABLED=False`
with `EVAL_AUTO_DRAIN_ENABLED=True` (`test_gated_off`), proving the dedicated
gate suppresses the rung. There is no symmetric test for the other
combination — `EVAL_AUTO_DRAIN_ENABLED=False` with `BEST_MOVE_BACKFILL_ENABLED=True`
— which the code handles correctly (the bundled `scope=None` path returns
`None` before ever reaching tier-3, per `claim_eval_job`'s early
`if not settings.EVAL_AUTO_DRAIN_ENABLED: return None` at line 829-830) but is
currently only exercised indirectly via the general `EVAL_AUTO_DRAIN_ENABLED`
tests elsewhere in the suite, not scoped to tier-4b specifically.

**Fix:** Add a small test asserting `claim_eval_job()` returns `None` when
`EVAL_AUTO_DRAIN_ENABLED=False` and `BEST_MOVE_BACKFILL_ENABLED=True` with an
otherwise-eligible tier-4b candidate present, for full "both gates
independently required" coverage symmetry with `test_gated_off`.

---

_Reviewed: 2026-07-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
