---
phase: 117-priority-queue-flaw-integration
reviewed: 2026-06-13T14:00:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - app/services/eval_queue_service.py
  - app/services/eval_drain.py
  - app/services/engine.py
  - app/models/eval_jobs.py
  - app/models/game.py
  - app/models/game_position.py
  - app/repositories/game_repository.py
  - app/routers/admin.py
  - app/schemas/admin.py
  - alembic/versions/20260613_120000_phase_117_queue_pv.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: fixed
---

# Phase 117: Code Review Report

**Reviewed:** 2026-06-13T14:00:00Z
**Depth:** deep
**Files Reviewed:** 10 (including migration)
**Status:** issues_found

## Summary

Phase 117 introduces a tiered priority queue with SKIP LOCKED lease semantics, PV/best_move capture, and a classify-and-fill-oracle post-game hook. The overall architecture is sound: session discipline is respected (no gather inside AsyncSession), SKIP LOCKED is applied correctly to the eval_jobs table, WR-02 repointing to `lichess_evals_at` is correct, and the PV off-by-one (writing at ply N+1) is correct per D-117-02.

One **BLOCKER**: the guest guard in `enqueue_tier1_game` treats a missing user the same as a non-guest user, reaching the FK insert and raising an unhandled 500 at the admin router. Three **WARNINGS**: the `_classify_and_fill_oracle` exception handler hides DB transaction state corruption in a failure scenario; the `type: ignore` suppression convention is wrong; and the `Game.is_analyzed` docstring is now factually wrong. Two **INFO** items: the tier-3 pick has a benign double-claim race and the `_apply_full_eval_results` pv_string is silently discarded rather than written there.

---

## Critical Issues

### CR-01: `enqueue_tier1_game` guest guard passes on missing user, causing FK violation and 500

**File:** `app/services/eval_queue_service.py:324-326`

**Issue:** `scalar_one_or_none()` returns `None` when the user does not exist. `if is_guest:` evaluates `if None:` which is `False`, so the guard passes and the code proceeds to `pg_insert(EvalJob)`. The insert hits the `ForeignKey("users.id")` constraint and raises an `IntegrityError`. This exception is unhandled inside `enqueue_tier1_game` and propagates to the admin router, resulting in an HTTP 500. This path is reachable in practice: the admin router passes `game.user_id` directly, and if the user row was deleted between the game load and the user lookup, the guard silently passes.

The same `None`-is-falsy pattern in the admin router at line 121 (`if user is not None and user.is_guest:`) correctly handles the missing-user case, but `enqueue_tier1_game` does not.

**Fix:**
```python
# eval_queue_service.py, enqueue_tier1_game, line 323-326
user_result = await session.execute(select(User.is_guest).where(User.id == user_id))
is_guest = user_result.scalar_one_or_none()
# None = user not found (deleted); treat as non-enqueue to avoid FK violation.
if is_guest is None or is_guest:
    return False
```

---

## Warnings

### WR-01: `_classify_and_fill_oracle` exception handler swallows DB errors mid-write, leaving partial state visible to subsequent commit

**File:** `app/services/eval_drain.py:460-468`

**Issue:** `_classify_and_fill_oracle` runs inside the same `write_session` transaction as `_apply_full_eval_results`, `_mark_full_evals_completed`, `_mark_full_pv_completed`, and the job-status update. It wraps its entire body in a bare `except Exception` that captures to Sentry and returns — leaving the outer write transaction to commit whatever partial state was written before the exception.

Specifically: if an exception fires mid-way through the flaw-PV loop (lines 442-458) after some `pv` updates but before others, the outer `await write_session.commit()` at line 1242 commits those partial PV writes. The flaw rows themselves (written by `bulk_insert_game_flaws`) are already flushed within the session. The oracle-count UPDATE was completed before the PV loop. So the committed state is: some flaw-adjacent positions have `pv` written, others do not. This is technically fine for idempotency (a re-run of the tick won't happen — the game is already marked `full_evals_completed_at`), but if the exception fires BEFORE the oracle count UPDATE (e.g. during `bulk_insert_game_flaws` — which uses the raw asyncpg COPY path via `game_flaws_repository`), then game_flaws rows may be partially inserted with oracle counts still NULL. Because `full_evals_completed_at` is set unconditionally afterward, the game will never be retried.

The most dangerous scenario: if `bulk_insert_game_flaws` raises, the exception is caught, the function returns, and `_mark_full_evals_completed` + commit run. The game is marked done with no flaw rows and no oracle counts, permanently.

**Fix:** Separate the exception boundary so only the PV loop is individually fault-tolerant. The flaw insert and oracle count update are atomic prerequisites; if either fails the game should NOT be marked complete:

```python
# Option A: let FK/DB errors in bulk_insert_game_flaws + oracle UPDATE propagate
# to the outer write_session. Only catch within the per-flaw PV loop.
await bulk_insert_game_flaws(session, rows)

await session.execute(
    update(games_table)
    .where(games_table.c.id == game_id)
    .values(white_inaccuracies=..., ...)
)

# PV writes are best-effort — catch individually.
for flaw in flaw_list:
    flaw_ply: int = flaw["ply"]
    pv_ply = flaw_ply + 1
    engine_entry = engine_result_map.get(pv_ply)
    if engine_entry is None:
        continue
    _cp, _mt, _bm, pv_string = engine_entry
    if pv_string is None:
        continue
    try:
        await session.execute(
            update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == pv_ply)
            .values(pv=pv_string)
        )
    except Exception as exc:
        sentry_sdk.set_context("classify_oracle", {"game_id": game_id, "pv_ply": pv_ply})
        sentry_sdk.capture_exception(exc)
```

If a full rewrite is out of scope, at minimum add a comment documenting that the `except` here intentionally accepts partial-PV committed state as a trade-off, and that the flaw insert + oracle count update preceding the PV loop are NOT individually fault-tolerant (any exception there silently skips both flaw rows and oracle counts).


### WR-02: `# type: ignore[arg-type]` in admin router violates project convention; should be `# ty: ignore[...]`

**File:** `app/routers/admin.py:126`

**Issue:** CLAUDE.md states "Use `# ty: ignore[rule-name]` (not `# type: ignore`) to suppress errors that can't be fixed." The admin router uses `# type: ignore[arg-type]`, which is the mypy/pyright convention, not the project's `ty` convention. This is the only `type: ignore` in the entire `app/` tree introduced by Phase 117; all other suppressions use `ty: ignore`.

The underlying suppression is also avoidable: `enqueue_status` is a `str` at the type checker level but is always assigned a `Literal` value. Using `cast` makes the intent explicit without suppression:

**Fix:**
```python
from typing import cast, Literal

EnqueueStatusLiteral = Literal["enqueued", "skipped_guest", "already_queued"]
enqueue_status_typed = cast(EnqueueStatusLiteral, enqueue_status)
return EnqueueTier1Response(status=enqueue_status_typed, game_id=game_id)
```

Or simply rename `enqueue_status` to `Literal`-typed from first assignment:
```python
enqueue_status: Literal["enqueued", "skipped_guest", "already_queued"]
if inserted:
    enqueue_status = "enqueued"
else:
    user = await session.get(User, game.user_id)
    if user is not None and user.is_guest:
        enqueue_status = "skipped_guest"
    else:
        enqueue_status = "already_queued"

return EnqueueTier1Response(status=enqueue_status, game_id=game_id)
```


### WR-03: `Game.is_analyzed` hybrid property docstring is factually wrong after Phase 117

**File:** `app/models/game.py:181-193`

**Issue:** The docstring states: "Cheap detector: `white_blunders` is populated only when the import pipeline ingested per-color move-quality counts — currently Lichess games that already have computer analysis enabled." After Phase 117, `_classify_and_fill_oracle` fills `white_blunders` for engine-analyzed games too (D-117-09). The docstring is now false: `white_blunders IS NOT NULL` is no longer "currently Lichess games only." Any code reader or future developer relying on this docstring will draw wrong conclusions about which games appear in the `is_analyzed` filtered sets in `library_repository.py`.

The PLAN explicitly documents D-117-09 but the docstring was not updated.

**Fix:**
```python
@hybrid_property
def is_analyzed(self) -> bool:
    """True when this game has full-game move-quality analysis (flaw counts populated).

    Cheap detector: `white_blunders` is non-NULL when per-color move-quality counts
    are present — either ingested from Lichess at import time (lichess_evals_at IS NOT NULL)
    or computed by the full-ply eval drain (Phase 117+). Chess.com games without
    per-game analysis return False. Used as the analyzed/total denominator for the
    flaw-stats coverage badge and the you-vs-opponent comparison.

    See D-117-09: after Phase 117, this property returns True for engine-analyzed
    games as well as Lichess games with computer analysis.
    """
    return self.white_blunders is not None
```

---

## Info

### IN-01: Tier-3 derived pick has a benign double-claim race (acknowledged in design)

**File:** `app/services/eval_queue_service.py:177-221`

**Issue:** `_claim_tier3_derived` does a plain `SELECT ... LIMIT 1` with no locking. Two concurrent drain workers can independently pick the same game. Both proceed to process it: both write evals (idempotent), both call `bulk_insert_game_flaws` (ON CONFLICT DO NOTHING — idempotent), both update oracle counts (idempotent), both set completion markers (idempotent). This wastes ~60 engine calls but produces correct data. The design accepts this trade-off to avoid pre-populating 558k backlog rows in eval_jobs.

This is documented in the module docstring but worth calling out explicitly: in a multi-worker deployment (Phase 118 browser workers), the tier-3 double-claim frequency scales with the number of workers. At two server-pool workers the risk is low; at N browser workers it could cause significant duplicate work.

**No code change required for Phase 117.** Consider adding a `FOR UPDATE SKIP LOCKED` to `_claim_tier3_derived` in Phase 118 when multiple workers are introduced, even if it requires a transient row in eval_jobs for the tier-3 claim window.


### IN-02: `_apply_full_eval_results` silently discards `pv_string` from engine results

**File:** `app/services/eval_drain.py:289`

**Issue:** `_resolve_full_eval` returns a 4-tuple `(eval_cp, eval_mate, best_move, pv_string)`. In `_apply_full_eval_results`, the caller unpacks as `eval_cp, eval_mate, best_move, _pv_string` — the leading underscore signals intentional discard. The `pv` column is only written in `_classify_and_fill_oracle` at flaw-adjacent plies. This is correct per D-117-02, but is a non-obvious design choice.

A future maintainer adding general PV-write logic to `_apply_full_eval_results` might write `pv_string` to ALL positions accidentally. A comment would prevent this.

**Fix:** Add a single-line comment at the discard site:
```python
eval_cp, eval_mate, best_move, _pv_string = _resolve_full_eval(...)
# _pv_string intentionally discarded here: pv is written ONLY at flaw-adjacent plies
# (ply = flaw_ply + 1) in _classify_and_fill_oracle below (D-117-02).
```

---

_Reviewed: 2026-06-13T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
