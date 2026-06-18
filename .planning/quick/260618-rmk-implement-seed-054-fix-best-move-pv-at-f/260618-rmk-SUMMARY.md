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

**`scripts/backfill_best_move_pv.py`** (new, ~370 lines)
- Lichess-only (`games.lichess_evals_at IS NOT NULL`), positions at a flaw ply or flaw+1
  (`EXISTS game_flaws … gf.ply = gp.ply OR gf.ply = gp.ply - 1`), idempotent on
  `best_move IS NULL` (subsumes the SEED-043 never-reprocessed cohort AND this keying gap).
- Reuses `_batch_update_best_move_rows` / `_batch_update_pv_rows` from `eval_drain` →
  identical keying. Writes best_move + pv ONLY, never `eval_cp` (lichess `%eval` preserved).
- Mirrors `backfill_eval.py` plumbing: `--db dev|benchmark|prod`, `--dry-run`, `--limit`,
  `--user-id`, `--workers`, `--timeout`; server-side cursor streaming, ~100-games-per-commit
  batches, local `EnginePool`. Runs from Adrian's machine over the prod tunnel → zero prod
  compute; never touches `full_evals_completed_at` (no analyzed-gate / stats regression).

**`tests/services/test_full_eval_drain.py`** — updated 3 tests (`TestFlawPv` ×2,
`TestBatchedWriteRegression`) to assert pv at flaw_ply + flaw_ply+1 and the lichess engine
now evaluates both flaw plies (2 calls, was 1), incl. a new best_move assertion at flaw_ply.

## Verification
- `ruff format` + `ruff check`: clean. `ty check app/ tests/`: zero errors (the 4 ty errors
  under `scripts/` are pre-existing in `seed_openings.py` / `seed_cohort_cdf.py`, outside the
  CI `app/ tests/` scope, untouched here).
- `uv run pytest -n auto`: **2774 passed, 15 skipped**.
- Backfill smoke on dev: `--dry-run` → 117,761 target positions; `--limit 4 --workers 2`
  wrote 4 rows. DB spot-check (game 296338): best_move + pv set at flaw plies 30, 36 AND
  flaw+1 plies 31, 37; `eval_cp` (lichess %eval) preserved on all. Re-run is a no-op (NULL
  filter). No frontend change (arrow already reads `best_move[flaw_ply]`).

## Follow-ups (out of scope here)
- **Deploy** `bin/deploy.sh` (backend only; stale remote worker stays compatible — server
  owns ply-selection).
- **Run the prod backfill** after deploy: `bin/prod_db_tunnel.sh` then
  `uv run python scripts/backfill_best_move_pv.py --db prod --workers <local-cores>`
  (size first with `--dry-run`). Multi-hour run is fine — idempotent restart.
- **Close SEED-043's lichess option (a) as superseded** by this backfill (per seed).
- `pv[flaw_ply]` (Part 2) is latent: nothing renders the ideal-continuation line yet.
