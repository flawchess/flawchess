---
quick_id: 260618-rmk
title: "SEED-054 — store engine best_move/pv at flaw_ply (the better alternative), not only flaw_ply+1"
status: ready
created: 2026-06-18
mode: quick
---

# Quick Task 260618-rmk

Implement SEED-054 (`.planning/seeds/SEED-054-best-move-pv-at-flaw-ply.md`): the engine
`best_move` blue arrow is NULL on lichess flaws because the drain only engine-evaluates
`flaw_ply + 1` (the opponent's reply), never `flaw_ply` (the better alternative). Fix the
drain to also evaluate/write at `flaw_ply`, write `pv` at `flaw_ply` too, and add an
idempotent local-machine prod-targeting backfill script for already-stored lichess games.

## Tasks

### Task 1 — Drain fix (Parts 1 + 2) + shared pv-write helper

Files: `app/services/eval_drain.py`

- **Part 1 (lichess engine target):** `_flaw_adjacent_plies` (line ~792) currently returns
  `{flaw["ply"] + 1 ...}`. Return **both** `flaw_ply` and `flaw_ply + 1`. Rename to
  `_flaw_engine_plies` and update the docstring (no longer strictly "adjacent"); update the
  single call site (line ~1702) and the local var `flaw_adjacent_plies`. The existing filter
  + dedup-exclusion (lines ~1703-1716, 1734) are set-membership tests, so adding `flaw_ply`
  to the set automatically makes the engine evaluate the pre-blunder board → `best_move`
  written at `flaw_ply` by `_apply_full_eval_results`' lichess branch (preserves `%eval`).
- **Refactor:** extract `_batch_update_pv_rows(session, game_id, pv_rows)` from the inline pv
  `UPDATE … FROM (VALUES …)` in `_classify_and_fill_oracle` (lines ~763-789), mirroring
  `_batch_update_best_move_rows`. This is the shared write helper the backfill reuses so the
  `(game_id, ply)` keying is identical by construction. (Do NOT invent a context dataclass —
  the drain's batched gather architecture and the per-position backfill share the *write
  helpers*, not a single evaluate-and-write function.)
- **Part 2 (pv at flaw_ply too):** in the pv-collect loop (lines ~751-761), collect pv for
  **both** `flaw_ply` and `flaw_ply + 1` from `engine_result_map`, deduped by ply (consecutive
  flaws can collide). Then call `_batch_update_pv_rows`. chess.com flaws already have the
  engine result at `flaw_ply`; opening dedup-transplanted plies aren't in `engine_result_map`
  → pv stays NULL there (acceptable per seed).

verify: `uv run ty check app/` clean; targeted drain tests pass.
done: lichess drain writes `best_move` at flaw plies + `pv` at both `flaw_ply` and `flaw_ply+1`.

### Task 2 — Backfill script

Files: `scripts/backfill_best_move_pv.py` (new)

Mirror `scripts/backfill_eval.py` plumbing (`--db dev|benchmark|prod`, `db_url_for_target`,
`EnginePool`, streaming server-side cursor, batched writes, `_log`, Sentry, `--dry-run`,
`--limit`, `--user-id`, `--workers`).

- **Selection:** `games.lichess_evals_at IS NOT NULL`, position at a flaw ply or flaw+1
  (`EXISTS game_flaws gf WHERE gf.game_id = gp.game_id AND (gf.ply = gp.ply OR gf.ply = gp.ply - 1)`),
  `gp.best_move IS NULL` (idempotent / resumable — subsumes SEED-043's never-reprocessed cohort
  AND this keying gap in one pass).
- **Eval:** replay PGN to ply (pre-push board), `engine_service.evaluate_nodes_with_pv(board)`.
- **Write best_move + pv ONLY** via the shared `_batch_update_best_move_rows` /
  `_batch_update_pv_rows` from `eval_drain` — **never** `eval_cp` (preserve lichess `%eval`).
- Batch ~100 games per commit over the tunnel; larger local Stockfish pool.

verify: `--dry-run` prints a count; re-run is a no-op (NULL filter).
done: script exists, importable, `ty` clean, sizing query runnable.

## Gates
- `uv run ruff format app/ tests/ scripts/` + `uv run ruff check --fix`
- `uv run ty check app/ tests/ scripts/`
- `uv run pytest -n auto` (full backend suite)
- frontend: no change needed (arrow already reads `best_move[flaw_ply]`)

## Out of scope
- Running the prod backfill (manual, post-deploy, via `bin/prod_db_tunnel.sh`).
- Frontend changes; worker changes (server-side only, stale worker stays compatible).
