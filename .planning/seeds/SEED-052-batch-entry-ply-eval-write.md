---
id: SEED-052
status: implemented
resolved: 2026-06-16
resolved_by: quick task 260616-kzb
planted: 2026-06-16
planted_during: Phase 123 (remote-worker-fan-out-for-entry-ply-import-time-eval)
trigger_when: when touching the eval-drain write path, doing an N+1 / DB round-trip perf pass, or if Sentry flags an N+1 on /api/eval/remote/entry-submit
scope: Small
---

# SEED-052: Batch `_apply_eval_results` (entry-ply / cold-drain eval write) into one round-trip

Batch the entry-ply / endgame-span-entry eval write the same way quick task
**260616-jq1** batched the full-ply lane for **FLAWCHESS-6B**. `_apply_eval_results`
(`app/services/eval_drain.py`, ~lines 1089-1138) still issues **one ORM Core
`update(GamePosition).where(game_id, ply[, endgame_class]).values(eval_cp, eval_mate)`
per row in a `for` loop** — the identical N+1 shape, just on the other worker lane.

## Why This Matters

The full-ply `/submit` lane (`_apply_full_eval_results`) and the flaw-PV write were
batched to single `UPDATE … FROM (VALUES …)` round-trips in 260616-jq1 (Fixes
FLAWCHESS-6B). The **entry-ply lane** (`/api/eval/remote/entry-submit`, Phase 123
SEED-051, plus the in-process cold drain) was left on the old per-row pattern because
it was out of scope for that Sentry issue.

It hasn't been Sentry-flagged yet only because it touches **fewer rows per game**
(endgame-span-entry + entry plies, not all ~40-80 plies). It's still a real N+1 and
now a **stylistic inconsistency**: the file's eval-write path is otherwise batched
raw SQL. Closing it removes the last per-row eval UPDATE loop and makes the lane
behave like the full-ply lane under load (fresh-import drain over big accounts).

## When to Surface

**Trigger:** when next editing the eval-drain write path, during any N+1 / DB
round-trip perf sweep, or if Sentry raises a `performance_n_plus_one_db_queries`
issue on `/api/eval/remote/entry-submit`. Low urgency — perf/consistency cleanup,
not a user-facing bug.

This seed will surface during `/gsd-new-milestone` when the milestone scope matches
(import/eval performance, observability cleanup).

## Scope Estimate

**Small** — a few hours; a `/gsd-quick` task. Mirror 260616-jq1 exactly:

- Collect `(ply, eval_cp, eval_mate)` write-rows in one pass, then emit a single
  batched `UPDATE … FROM (VALUES …)` via `sa.text().bindparams()` with
  `CAST(:p AS smallint)` (asyncpg named-param compat — `::type` breaks adjacent to `$N`).
- Guard empty input (no zero-row VALUES UPDATE). Sequential `await session.execute`
  on the caller-owned session — **no `asyncio.gather`** (CLAUDE.md hard rule).
- **Preserve exactly:** the `(None, None)` skip + per-row Sentry warning
  (`source="eval_drain"`, bounded ctx — no PGN/FEN/user_id), the optional
  `endgame_class` WHERE disambiguation, and the `(eval_calls_made, eval_calls_failed)`
  return tuple.
- Consider reusing/generalizing the `_batch_update_eval_rows` helper from 260616-jq1
  if it generalizes cleanly (note: that helper also writes `best_move` and uses
  `COALESCE(v.best_move, …)` no-clobber — the entry-ply lane writes only eval_cp/eval_mate
  and has the `endgame_class` predicate, so a shared helper needs a careful signature
  or a sibling helper).

**Decision at plan time:** raw `sa.text` (consistent with 260616-jq1; the file's
eval-write style is now raw) vs keeping it ORM. Recommend raw for consistency.

## Breadcrumbs

- `app/services/eval_drain.py:1089-1138` — `_apply_eval_results` (the per-row loop to batch)
- `app/services/eval_drain.py` `_batch_update_eval_rows` / `_batch_update_best_move_rows` — the batched analog from 260616-jq1 (the pattern to mirror)
- `app/routers/eval_remote.py` — `/entry-submit` endpoint calls `_apply_eval_results` (no +1 shift; do NOT swap to the full-ply path)
- `.planning/quick/260616-jq1-batch-the-two-per-row-update-loops-in-th/` — the precedent quick task (PLAN + SUMMARY)
- Related: SEED-051 (remote-worker entry-ply fresh-import drain — the feature that exercises this lane)

## Notes

Captured after quick task 260616-jq1 (FLAWCHESS-6B). Surfaced during the investigation
of which worker write paths are ORM vs raw SQL: row creation is asyncpg binary COPY
(import), full-ply eval writes are now raw batched VALUES, but this entry-ply lane was
the one remaining per-row ORM `update()` loop.
