---
quick_id: 260414-pv4
description: Fix time pressure queries to use whole-game endgame rule (not per-class spans) + update endgame concepts docs
date: 2026-04-14
status: complete
---

# Quick Task 260414-pv4 — Summary

## Problem

`query_clock_stats_rows` (endgame_repository.py) grouped by `(game_id, endgame_class)` with `HAVING count(ply) >= 6`, applying the 6-ply threshold per class span. That is correct for Endgame Type Breakdown and Conversion & Recovery, but wrong for Time Pressure sections: those care about the whole endgame phase of a game, not per-class spans.

Two resulting bugs:
1. **Qualification gap.** A game with e.g. 4 plies in KP_KP + 4 in KR_KR (8 total endgame plies, qualifies as endgame elsewhere) was excluded from time pressure entirely — neither span met the per-class threshold.
2. **Double counting.** Games with multiple qualifying spans produced multiple rows. `_compute_clock_pressure` worked around it via a Python `earliest_by_game` collapse (b7ed4b4); `_compute_time_pressure_chart` did not collapse — `tc_game_count` and bucket accumulators double-counted.

## Fix

- **Repo**: `query_clock_stats_rows` now filters via `_any_endgame_ply_subquery` (whole-game 6-ply rule, shared with `count_endgame_games`, etc.) and groups only by `Game.id`. Aggregates full endgame-ply / clock arrays per game so `_extract_entry_clocks` parity scan still finds the earliest user and opponent entry clocks.
- **Service**: removed `earliest_by_game` collapse in `_compute_clock_pressure`; rows now iterate 1-to-1 with games in both consumers. `_compute_time_pressure_chart` no longer needs to collapse by construction — fixes the double-count bug latent from the b7ed4b4 pass.
- **Docs**: Time Pressure popover copy (`EndgameClockPressureSection`, `EndgameTimePressureSection`) clarifies the whole-game rule; Endgame Type Breakdown / Conversion & Recovery copy untouched (still per-class).
- **Tests**: reframed `test_net_timeout_rate_deduplication` for the new row shape (1 per game). Added two regression tests — split-class qualification (4+4 now qualifies) and double-count guard (7+7 game counted once in chart).

## Commits

- `d006672` fix(quick-260414-pv4): use whole-game rule in query_clock_stats_rows
- `c2a8587` refactor(quick-260414-pv4): simplify clock pressure consumers; regression tests
- `f5dfee4` docs(quick-260414-pv4): clarify whole-game rule in Time Pressure popovers

## Validation

- `uv run ruff check .` — passes
- `uv run ty check app/ tests/` — passes
- `uv run pytest tests/` — 701 passed, 1 skipped
- `cd frontend && npm run lint && npm run build` — passes

## Deviations

- Dropped unused `game_id`/`termination` locals in `_compute_time_pressure_chart` (F841 fix in the function being modified).
- Removed dead `PERSISTENCE_PLIES` import in `tests/test_endgame_repository.py` (F401 blocking `ruff check .`).

Both are Rule-1/3 auto-fixes, same-file scope, required for the ruff gate.

## Out of Scope (preserved)

- `query_endgame_entry_rows`, `query_endgame_bucket_rows`, conversion/recovery queries — all still use per-class spans (correct for their sections).
- `_any_endgame_ply_subquery` itself — reused, unmodified.
