---
phase: quick-260616-kzb
plan: "01"
type: execute
subsystem: eval_drain
tags: [performance, n-plus-one, batch-write, seed-052]
must_haves:
  truths:
    - "_apply_eval_results issues a single batched UPDATE … FROM (VALUES …) per drain batch, not one UPDATE per row"
    - "The (None, None) skip + per-row Sentry warning, optional endgame_class WHERE disambiguation, and (eval_calls_made, eval_calls_failed) return are all preserved"
    - "No asyncio.gather on the caller-owned session; empty input emits no zero-row VALUES UPDATE"
  artifacts:
    - "app/services/eval_drain.py — new _batch_update_entry_eval_rows helper + rewritten _apply_eval_results"
    - "tests/services/test_eval_drain.py — multi-game / multi-class batched-write regression test"
  key_links:
    - "app/services/eval_drain.py:1089 (_apply_eval_results)"
    - "app/services/eval_drain.py:436 (_batch_update_eval_rows — the full-ply precedent to mirror)"
---

# Quick Task 260616-kzb: Batch entry-ply eval write (SEED-052)

Mirror quick task **260616-jq1** (FLAWCHESS-6B): replace the per-row `update(GamePosition)`
loop in `_apply_eval_results` (`app/services/eval_drain.py`) with a single batched
`UPDATE … FROM (VALUES …)` round-trip. Closes the last per-row eval UPDATE loop on the
entry-ply / cold-drain lane.

## Key structural difference from the full-ply precedent

`_apply_eval_results` collects targets **across many games** in a drain batch
(`_collect_eval_targets_from_db` over a `game_ids` list), unlike the per-game full-ply
helpers. So `game_id` must live **in the VALUES tuple** (not a single `:game_id` param),
and the WHERE matches on `v.game_id`. The lane also writes only `eval_cp`/`eval_mate`
(no `best_move`) and carries the optional `endgame_class` predicate. → a **sibling helper**,
not a reuse of `_batch_update_eval_rows`.

## Tasks

### Task 1 — Add `_batch_update_entry_eval_rows` + rewrite `_apply_eval_results`
- **files:** `app/services/eval_drain.py`
- **action:**
  - Add `_batch_update_entry_eval_rows(session, rows)` taking
    `rows: list[tuple[game_id, ply, eval_cp, eval_mate, endgame_class]]`. Emit one
    `UPDATE game_positions SET eval_cp = v.eval_cp, eval_mate = v.eval_mate
    FROM (VALUES …) AS v(game_id, ply, eval_cp, eval_mate, endgame_class)
    WHERE game_positions.game_id = v.game_id AND game_positions.ply = v.ply
    AND (v.endgame_class IS NULL OR game_positions.endgame_class = v.endgame_class)`.
    Use `CAST(:p AS integer|smallint)` (asyncpg named-param compat — `::type` breaks
    adjacent to `$N`). Guard empty input. Sequential `await session.execute` — no gather.
  - Rewrite `_apply_eval_results`: one pass accumulates `eval_calls_made`/`eval_calls_failed`,
    fires the existing `(None, None)` per-row Sentry warning (`source="eval_drain"`, bounded
    ctx — game_id/ply[/endgame_class], no PGN/FEN/user_id), and collects surviving write-rows;
    then one call to the new helper. Same `(eval_calls_made, eval_calls_failed)` return.
- **verify:** `grep` shows no `update(GamePosition)` loop in `_apply_eval_results`; the
  per-row Sentry/skip path unchanged; casts present.
- **done:** function compiles, `ty`/`ruff` clean.

### Task 2 — Multi-game / multi-class regression test
- **files:** `tests/services/test_eval_drain.py`
- **action:** Add a test that builds `_EvalTarget`s across two game_ids (one
  `middlegame_entry` with `endgame_class=None`, one `endgame_span_entry` with an int class)
  plus a `(None, None)` failure target, runs `_apply_eval_results`, and asserts: eval_cp/mate
  landed on the right `(game_id, ply)` rows, the endgame_class predicate matched, the failed
  row stayed NULL, and the `(made, failed)` counts are correct.
- **verify:** `uv run pytest tests/services/test_eval_drain.py -n auto` green.
- **done:** new test passes alongside the existing suite.

### Task 3 — Gates
- Full local gate on touched area: `ruff format`, `ruff check`, `ty check`, and the
  eval-drain + eval-remote test files.

## Preserve exactly
- `(None, None)` → skip row + per-row Sentry warning (message + tags + bounded ctx).
- Optional `endgame_class` WHERE disambiguation.
- `(eval_calls_made, eval_calls_failed)` return tuple semantics.
- No `asyncio.gather` on the session; no zero-row VALUES UPDATE.
