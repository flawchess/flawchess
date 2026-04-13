# Deferred Items — Phase 60

Out-of-scope findings surfaced during plan execution. Not fixed here.

## Pre-existing ruff F841 in `app/services/endgame_service.py`

- **Location:** lines 892 (`game_id`) and 895 (`termination`) inside the clock-stats loop (around `_compute_clock_pressure`).
- **Type:** `F841 Local variable ... is assigned to but never used`.
- **Status:** Pre-existing before Phase 60 — confirmed by `git stash && uv run ruff check app/` on the pre-edit tree.
- **Why deferred:** Not in Phase 60 scope (opponent baseline in `_compute_score_gap_material`). Unrelated to opponent baseline changes.
- **Suggested fix:** Prefix with `_` (`_game_id`, `_termination`) or drop the annotations entirely since the values are unused.
