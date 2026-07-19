---
quick_id: 260719-fsz
status: complete
date: 2026-07-19
files_modified:
  - app/services/eval_queue_service.py
  - app/services/eval_drain.py
  - tests/services/test_eval_queue.py
  - tests/services/test_full_eval_drain.py
---

# Quick Task 260719-fsz — Summary

## Goal
Close two best-move (gem/great, tier-4b) coverage holes so every game we can classify
eventually gets `best_moves_completed_at` + `game_best_moves` rows, including
lichess-imported games with pre-existing evals and guest games. Runtime self-healing
lanes — no backfill script, no migration.

## What changed

### app/services/eval_queue_service.py
- **Population A (guest lichess games, ~18,882):** dropped the inlined `is_guest = false`
  clause from the tier-3 residual lichess-eval fallback (`_claim_tier3_derived`). Guests
  now get the full engine pass on their imported-eval games — a deliberate scoped reversal
  of QUEUE-08 for THIS lane only.
- **Population B (non-guest lichess orphans, ~12,643):** dropped `AND lichess_evals_at IS NULL`
  from both stages of `_claim_tier4_bestmove`, so lichess-eval games with `full_pv` set but
  `best_moves` NULL (orphaned during a Maia-down window) self-heal via the cheap minimal lane.
  Lanes stay disjoint on `full_pv_completed_at` (residual = NULL, tier-4b = NOT NULL), so no
  D-03 contention.
- **Population B2 (guest orphan self-heal):** parameterized the shared `_es_weighted_user_pick`
  with `include_guests: bool = False`, passed `True` ONLY from `_claim_tier4_bestmove`. tier-3
  needs-engine and tier-4-blob keep the default and still exclude guests.
- **Honesty fix:** the tier-4b `ClaimedJob` now resolves `is_lichess_eval_game` from the game
  row instead of the (now-false) hardcoded `False`.

### app/services/eval_drain.py
- **Divergence-guard parity (the subtle one):** for a lichess-eval game the minimal drain
  now overrides `best_cp`/`best_mate` from the fresh MultiPV-2 search (`res[0]/res[1]`,
  white-perspective Stockfish) instead of the stored `game_positions.eval_cp` (which holds
  LICHESS %eval). Without this, the query-time gem/great divergence guard
  (`library_service.py`) would compare lichess-to-lichess, never fire, and silently over-badge
  gems on lichess games. Stored `best_move` is kept as the identity key; engine games untouched.

### Tests (mutation-proven — each fix fails its test when reverted)
- `tests/services/test_eval_queue.py`: reversed `test_residual_fallback_excludes_guest_backlog_game`
  → `..._includes_...` (A); `test_excludes_guests` → `test_includes_guest_orphan` (B2);
  `test_excludes_lichess_eval` → `test_includes_lichess_eval_orphan` (B); updated
  `test_claimed_job_fields` rationale and added `test_claimed_job_lichess_flag` (honesty).
  Non-regression keepers unchanged: `test_tier3_guest_excluded_from_lottery`,
  `test_tier4_excludes_guests`, `test_excludes_pv_incomplete` (also proves lane disjointness).
- `tests/services/test_full_eval_drain.py`: added `TestTier4bMinimalDrainLichessBestCp`
  (parametrized lichess/engine) asserting stored `best_cp` is fresh-Stockfish for lichess
  and unchanged for engine games.

## Verification
- Mutation discipline: all 5 production changes proven by reverting each and confirming the
  specific test fails, then restoring.
- Full pre-merge gate: `ruff format` (2 files), `ruff check --fix` clean, `ty check` clean,
  `pytest -n auto -x` → **3513 passed, 18 skipped**.

## Not done / out of scope (deliberate)
- No migration (predicate/logic only). No frontend. No one-off backfill script — the existing
  ~12,643 (B) and ~18,882 (A) drain opportunistically through the lanes at the lowest idle rung.
- Deploy is separate: these changes take effect in prod only after the next `bin/deploy.sh`.
