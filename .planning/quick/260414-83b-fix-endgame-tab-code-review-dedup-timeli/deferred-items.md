# Deferred Items — 260414-83b

Out-of-scope findings from executing this quick task. Logged per GSD scope boundary rule.

## Pre-existing ruff F841 errors (unrelated code paths)

These exist on `b3dc7a5` baseline (verified via `git stash`). CI must already be tolerating them or they slipped in after the last green build.

- `app/services/endgame_service.py:911` — `game_id: int = row[0]` assigned but never used in `_compute_clock_pressure`.
- `app/services/endgame_service.py:914` — `termination: str | None = row[3]` assigned but never used in `_compute_clock_pressure`.

Fix: either prefix with `_game_id` / `_termination` or drop the bindings and access via `row[0]` / `row[3]` only when needed.

## Pre-existing ruff format drift

83 files in the repo would be reformatted by `uv run ruff format` on the base commit. Out of scope for a 3-task code-review fix.
