---
quick_id: 261122-l3u
slug: keep-the-second-best-move-in-the-drain-o
status: complete
commit: 2f43ec19a
date: 2026-11-22
---

# Quick 261122-l3u: Keep the second-best move in the drain's opening flaw recovery

## What changed

- `app/services/eval_drain.py`: `_fill_engine_game_flaw_pvs` now takes `second_best_map` and records the
  second-best move of its own MultiPV-2 search. `_fill_engine_game_flaw_second_best` and its call are
  removed. No extra engine time.
- `tests/services/test_full_eval_drain.py`: `TestFlawPvRecoveryKeepsSecondBest` (3 tests).
- `CHANGELOG.md`: bullet under `[Unreleased]` / Fixed.

## Verification

- Before the fix, reproduced with the engine and classifier mocked: step 3b recovered the line for both
  plies, step 3c ran zero searches and left `second_best_map` empty.
- New tests pass; with the recording line disabled, 2 of the 3 fail.
- Drain, worker-endpoint and flaws-service suites: 435 passed. `ruff`, `ty`, nesting-depth gate: clean.
- The full pre-merge gate was not run.

## Follow-ups

- The fix stops new damage only after it is deployed (the server pool runs the full drain).
- Existing rows: Phase 252 decision D-16 and plan 252-10 (node-0 pass through the tier-4 re-walk, before
  the prod and benchmark retags).
- Prod rows could not be attributed to the server pool directly (no per-game record of the analysing
  path); the attribution rests on the code and the reproduction.
