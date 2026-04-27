---
phase: 260427-g4a
plan: 01
subsystem: backend/openings
tags: [bug-fix, hotfix, sentry, sql, opening-insights]
requires:
  - phase 70 opening_insights pipeline
provides:
  - STARTING_POSITION_HASH constant in openings_repository
  - _safe_replay defensive guard in opening_insights_service
affects:
  - POST /api/insights/openings (no longer 500s on non-standard-FEN games)
tech-stack:
  added: []
  patterns:
    - Sentry capture with set_context (no variable data in exception message)
    - SQL EXISTS predicate as a positive whitelist for standard-start games
key-files:
  created: []
  modified:
    - app/repositories/openings_repository.py
    - app/services/opening_insights_service.py
    - tests/repositories/test_opening_insights_repository.py
    - tests/services/test_opening_insights_service.py
decisions:
  - Use a positive EXISTS (has_standard_start) rather than NOT EXISTS — handles missing ply-0 rows the same as non-standard ones, more conservative.
  - Cache _safe_replay results across the Pass-2 lineage walk and the per-row build loop so a bad row triggers exactly one Sentry capture and is consistently dropped from both passes.
  - Update _seed_game_with_positions test helper to default ply-0 to STARTING_POSITION_HASH so existing fixtures stay valid; opt-out flags (force_ply0_hash, skip_auto_ply0) for the regression tests.
metrics:
  duration: ~25 minutes
  completed: 2026-04-27
  commit: 8bc4337
---

# Quick Task 260427-g4a: Fix Opening Insights IllegalMoveError Summary

Two-layer fix for the chess.IllegalMoveError 500 on POST /api/insights/openings: filter the CTE so games imported from non-standard starting FENs no longer feed the transition aggregation, and add a defensive `_safe_replay` guard that logs+skips any residual replay failure instead of bubbling a 500.

## Diagnosis

User 7 (hikaru) had 4 chess.com games imported from PGNs with `[SetUp "1"][FEN "..."]` headers (themed events / puzzles starting from a custom position). In those games, `game_positions[ply=0].move_san = 'Bb2'` is legal from the custom FEN but illegal from `chess.Board()`. The CTE in `query_opening_transitions` aggregates `entry_san_sequence` via `array_agg(move_san) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)`. After GROUP BY collapses transpositions, `func.min(entry_san_sequence)` lexicographically picked `[Bb2, ...]` over legal alternatives starting with `[Nf3, ...]` because `'B' < 'N'`. `_compute_prefix_hashes` then called `chess.Board().push_san('Bb2')` and raised `chess.IllegalMoveError`, propagating as a 500.

## Two-Layer Fix

**Repository layer (correctness fix)** — `app/repositories/openings_repository.py`:

- Added module-level `STARTING_POSITION_HASH` constant (signed int64 of the Polyglot Zobrist hash for the standard starting position, matching the storage convention used in `opening_insights_service._compute_prefix_hashes`).
- Added an `EXISTS` correlated-subquery predicate (`has_standard_start`) to the `transitions_cte` WHERE clause. The CTE now only emits rows for games whose ply-0 `full_hash` equals `STARTING_POSITION_HASH`. Games with a non-standard ply-0 hash (chess.com themed events) or missing a ply-0 row (data corruption) are excluded.

**Service layer (defensive guard)** — `app/services/opening_insights_service.py`:

- Added `_safe_replay(san_sequence, *, entry_hash, candidate_san)` helper. Wraps `_replay_san_sequence` and `_compute_prefix_hashes` in a single try/except for `chess.IllegalMoveError`, `chess.InvalidMoveError`, and `ValueError`. On failure, calls `sentry_sdk.set_tag("source", "opening_insights")` + `set_context("opening_insights_replay", {entry_hash, candidate_san, san_sequence})` + `capture_exception(exc)` and returns None. No variable data is embedded in the exception message — preserves Sentry grouping per CLAUDE.md.
- Refactored `compute_insights` to call `_safe_replay` exactly once per row in the Pass-2 unmatched-parent walk, caching `(entry_fen, prefix_hashes)` keyed by `(color, entry_hash, move_san)`. The per-row build loop reuses the cache: bad rows are dropped (with a `continue`), good rows reuse the precomputed `entry_fen` (replacing the inline `_replay_san_sequence` call) and pass `prefix_hashes` into `_attribute_finding` via a new optional kwarg.
- `_attribute_finding` now accepts `prefix_hashes: list[int] | None = None` and skips the inline `_compute_prefix_hashes` call when provided. Default behavior unchanged for any future callers.

## Tests

| Layer | Test | Purpose |
| ----- | ---- | ------- |
| Repository | `test_non_standard_start_game_excluded_from_transitions` | A game with ply-0 hash != `STARTING_POSITION_HASH` produces zero transition rows. |
| Repository | `test_standard_start_game_included_in_transitions` | A normal game (ply-0 hash == `STARTING_POSITION_HASH`) still produces a transition row. |
| Repository | `test_game_without_ply0_row_excluded_from_transitions` | Game missing a ply-0 row is excluded by the EXISTS predicate. |
| Service | `test_safe_replay_unreplayable_san_does_not_500` | `entry_san_sequence=['Bb2']` → no exception bubbles up; bad row dropped. |
| Service | `test_safe_replay_captures_to_sentry_with_set_context` | `capture_exception` called exactly once; `set_context("opening_insights_replay", ...)` + `set_tag("source", "opening_insights")` populated; exception message contains no variable data. |
| Service | `test_safe_replay_mixed_batch_keeps_good_drops_bad` | Mixed batch yields the good row's finding and silently skips the bad one. |

Test helper `_seed_game_with_positions` was updated so that any test seeding ply-0 with a synthetic hash now writes `STARTING_POSITION_HASH` by default (existing fixtures stay valid); a missing ply-0 row is auto-inserted unless `skip_auto_ply0=True`. Opt-outs `force_ply0_hash` and `skip_auto_ply0` are used by the new regression tests.

## Verification

- `uv run pytest` — 1144 tests passed, 0 failed.
- `uv run ty check app/ tests/` — All checks passed.
- `uv run ruff check .` — All checks passed.
- Smoke test against local dev DB user 7 (hikaru) via `query_opening_transitions`:

  | Color | Rows returned | Unreplayable rows |
  | ----- | -------------:| -----------------:|
  | white | 2582          | 0 |
  | black | 2289          | 0 |

  (Before the fix: `bad=11` for user 7.)

## Files Modified

- `app/repositories/openings_repository.py` — added `STARTING_POSITION_HASH` constant and CTE filter.
- `app/services/opening_insights_service.py` — added `_safe_replay`; refactored `compute_insights` and `_attribute_finding` to use it.
- `tests/repositories/test_opening_insights_repository.py` — added 3 regression tests; updated seed helper.
- `tests/services/test_opening_insights_service.py` — added 3 regression tests.

## Commit

- `8bc4337` — `fix(70): exclude non-standard-FEN games from opening-insights transitions (#71 hotfix)`

## Self-Check: PASSED

- Files exist: `app/repositories/openings_repository.py`, `app/services/opening_insights_service.py`, `tests/repositories/test_opening_insights_repository.py`, `tests/services/test_opening_insights_service.py` — all FOUND.
- Commit `8bc4337` — FOUND in `git log`.
- All 6 new tests pass; 1144/1144 total tests pass.
- ty + ruff checks pass.
- Dev DB smoke test confirms `bad=0` (was 11 before the fix).
