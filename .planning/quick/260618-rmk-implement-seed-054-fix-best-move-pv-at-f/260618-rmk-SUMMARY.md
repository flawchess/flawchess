---
quick_id: 260618-rmk
title: "SEED-054 — store engine best_move/pv at flaw_ply, not only flaw_ply+1"
status: complete
completed: 2026-06-18
---

# Quick Task 260618-rmk — Summary

Implemented SEED-054: the engine now captures `best_move` + `pv` at `flaw_ply` (the
pre-blunder decision board, the "better alternative" the blue arrow renders), not only at
`flaw_ply + 1` (the opponent's reply). Plus an idempotent local-machine prod-targeting
backfill for already-stored lichess games.

## What changed

**`app/services/eval_drain.py`**
- **Part 1:** renamed `_flaw_adjacent_plies` → `_flaw_engine_plies`; it now returns
  `{flaw_ply, flaw_ply + 1}` (was `{flaw_ply + 1}`). The existing lichess
  eval-preservation filter + opening-dedup exclusion + engine-target selection are all
  set-membership tests, so adding `flaw_ply` makes the engine evaluate the pre-blunder
  board → `_apply_full_eval_results`' lichess branch writes `best_move` there (lichess
  `%eval` still preserved). Updated the call site + local var `flaw_engine_plies`.
- **Refactor:** extracted `_batch_update_pv_rows(session, game_id, pv_rows)` from the
  inline pv `UPDATE … FROM (VALUES …)` in `_classify_and_fill_oracle`, mirroring
  `_batch_update_best_move_rows`. This is the shared write helper the backfill reuses so
  `(game_id, ply)` keying is identical by construction. (No context dataclass — the drain's
  batched gather and the per-position backfill share the *write helpers*, not one
  evaluate-and-write function, per CLAUDE.md anti-over-engineering guidance.)
- **Part 2:** the flaw-pv loop now collects pv for **both** `flaw_ply` and `flaw_ply + 1`
  from `engine_result_map` (deduped by ply — consecutive flaws can collide), then writes via
  `_batch_update_pv_rows`. chess.com already has the engine result at `flaw_ply`; opening
  dedup-transplanted plies are absent from `engine_result_map` → pv stays NULL there
  (acceptable per seed).

**`scripts/backfill_best_move_pv.py`** (new, ~400 lines)
- Covers BOTH holes (widened after review): lichess flaw plies (best_move + pv NULL) AND
  engine-analyzed games' flaw plies (best_move already set, pv NULL — the `pv[flaw_ply]`
  keying gap, ~26.5k on dev). Predicate: `best_move IS NULL OR pv IS NULL`, positions at a
  flaw ply or flaw+1 (`EXISTS game_flaws … gf.ply = gp.ply OR gf.ply = gp.ply - 1`),
  idempotent (filled rows leave the predicate). Subsumes SEED-043 + the lichess keying gap
  + the engine-game pv gap in one pass.
- **Per-row `need_bm`/`need_pv` flags** (selected as booleans, not the pv text) so the writer
  fills ONLY the originally-NULL column — an engine game's existing `best_move` is never
  clobbered by a fresh (non-deterministic) search; only its missing pv is filled. Verified on
  dev: 5 engine-game positions → `written_best_move=0, written_pv=5`, best_move + eval_cp
  unchanged, pv lines start with the existing best_move.
- **No guest filter** (decided against during review): the flaw-row `EXISTS` already bounds
  scope to already-analyzed games (flaw rows only exist post-drain), so the engine compute was
  already spent; a guest who ran on-demand "Analyze" on a lichess game hit the same broken
  arrow and should get the fix too. Filtering guests would be unnecessary and slightly wrong.
- Reuses `_batch_update_best_move_rows` / `_batch_update_pv_rows` from `eval_drain` →
  identical keying. Writes best_move + pv ONLY, never `eval_cp` (lichess `%eval` / prior engine
  eval preserved).
- Mirrors `backfill_eval.py` plumbing: `--db dev|benchmark|prod`, `--dry-run`, `--limit`,
  `--user-id` (documented w/ example), `--workers`, `--timeout`; server-side cursor streaming,
  ~100-games-per-commit batches, local `EnginePool`. Runs from Adrian's machine over the prod
  tunnel → zero prod compute; never touches `full_evals_completed_at` (no analyzed-gate / stats
  regression).
- **Efficiency note:** the selection query is engine-bound overall, but `EXPLAIN` shows it
  seq-scans `game_positions` (predicate non-selective) rather than driving from the ~40k flaw
  rows. Acceptable for a one-time run; a flaw-driven rewrite is a possible future optimization.

**`tests/services/test_full_eval_drain.py`** — updated 3 tests (`TestFlawPv` ×2,
`TestBatchedWriteRegression`) to assert pv at flaw_ply + flaw_ply+1 and the lichess engine
now evaluates both flaw plies (2 calls, was 1), incl. a new best_move assertion at flaw_ply.

## Verification
- `ruff format` + `ruff check`: clean. `ty check app/ tests/`: zero errors (the 4 ty errors
  under `scripts/` are pre-existing in `seed_openings.py` / `seed_cohort_cdf.py`, outside the
  CI `app/ tests/` scope, untouched here).
- `uv run pytest -n auto`: **2774 passed, 15 skipped**.
- Backfill smoke on dev (final widened scope): `--dry-run` → 70,494 target positions.
  Lichess path (`--limit 4`): best_move + pv set at flaw plies 30/36 AND flaw+1 plies 31/37
  (game 296338), `eval_cp` %eval preserved. Engine-game pv-only path (`--user-id 2 --limit 5`):
  `written_best_move=0, written_pv=5`, best_move + eval_cp unchanged on game 157929 plies
  8/13/26, pv lines start with the existing best_move. Re-run is a no-op (predicate filter).
  No frontend change (arrow already reads `best_move[flaw_ply]`).

## Follow-ups (out of scope here)
- **Deploy** `bin/deploy.sh` (backend only; stale remote worker stays compatible — server
  owns ply-selection).
- **Run the prod backfill** after deploy: `bin/prod_db_tunnel.sh` then
  `uv run python scripts/backfill_best_move_pv.py --db prod --workers <local-cores>`
  (size first with `--dry-run`). Multi-hour run is fine — idempotent restart.
- **Close SEED-043's lichess option (a) as superseded** by this backfill (per seed).
- `pv[flaw_ply]` (Part 2) is latent: nothing renders the ideal-continuation line yet.
