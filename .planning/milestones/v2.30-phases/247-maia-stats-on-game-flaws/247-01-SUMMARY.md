---
phase: 247-maia-stats-on-game-flaws
plan: 01
subsystem: maia-engine
tags: [maia, onnxruntime, policy, entropy, stats]
requires: []
provides:
  - "full_policy(fen, elo): every legal move's Maia probability from one forward pass"
  - "start_maia(intra_op_num_threads=...) per-process ORT thread option"
  - "compute_maia_flaw_stats: pure derivation of the eight D-01 per-flaw values (D-15 second rule)"
  - "tests.services.maia_fakes.fake_full_policy deterministic test helper"
affects: [247-02, 247-04, 247-05]
status: complete
commits: 3
plan_head_before: 4ec3c84e788c439c77f95dab83a71ba15aec3024
plan_head_after: b1c13f8f863ad1fde47e5013013b110557b30ad8
actuals:
  tokens: 5850
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "score_move delegates to full_policy: one encoding, one softmax"
    - "pure stats module returns (stats | None, reasons) with typed MaiaReason Literal"
key-files:
  created:
    - app/services/maia_flaw_stats.py
    - tests/services/maia_fakes.py
    - tests/services/test_maia_flaw_stats.py
  modified:
    - app/services/maia_engine.py
    - tests/services/test_maia_engine.py
key-decisions:
  - "Rank = 1 + count of strictly more probable legal moves (ties share a rank)"
  - "Second-pair reason precedence: single_legal_move, second_missing, second_equals_best, second_not_legal"
requirements-completed: [D-01, D-03, D-04, D-15]
---

# Phase 247 Plan 01: Maia primitives Summary

`full_policy` (one ORT pass, all legal-move probabilities, symmetric Elo feed), the pure `compute_maia_flaw_stats` (eight D-01 values, D-15 second-equals-best rule), a single-thread `start_maia` option, and the shared `fake_full_policy` test helper.

## Accomplishments

- `app/services/maia_engine.py`: `full_policy(fen, elo)` holds the former `score_move` body; `score_move` now returns `full_policy(...).get(uci)`. `start_maia(*, intra_op_num_threads=None)` builds `SessionOptions` only when a thread count is given; no argument keeps the exact old call, so `app/main.py` lifespan is unchanged.
- `app/services/maia_flaw_stats.py`: `RANK_BASE`, `MaiaReason`, `MaiaFlawStats`, `null_maia_stats`, `compute_maia_flaw_stats` (entropy in bits, effective moves = 2^H, strict-greater rank).
- `tests/services/maia_fakes.py`: `fake_full_policy` (weights n..1 over UCI-sorted legal moves, normalized).
- Tests: tracer `test_full_policy_feeds_flaw_stats` (real ORT), 8 pure stats tests, plus the 5 engine-edge tests (real ORT legal-move/sum/score_move agreement, None session, symmetric Elo feed via recording fake, thread option passthrough, single-thread real load).

## Mutation proofs

- Task 2: removing the `second_uci == best_uci` branch failed `test_second_pair_reasons_d15`; flipping strict `>` to `>=` in the rank helper failed `test_rank_strict_greater_with_ties` (also `test_best_pair_reasons`, `test_second_pair_reasons_d15`). Restored: 8 passed.
- Task 3: dropping `sess_options` when `intra_op_num_threads` is set failed `test_start_maia_thread_option_passthrough`; feeding `elo_oppo` a different value failed `test_full_policy_symmetric_elo_feed`. Restored: 20 passed (engine + stats files), no skips.

## Verification

- `uv run pytest -n auto -x`: 5711 passed, 20 skipped.
- `uv run ty check app/ tests/ scripts/`: All checks passed. `uv run ruff check .` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.

## Deviations from Plan

None - plan executed as written. (Two unneeded `ty: ignore` directives were removed after ty flagged them as unused.)

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Files and commits (4d57e03bd, 220bc50d4, b1c13f8f8) verified present.
