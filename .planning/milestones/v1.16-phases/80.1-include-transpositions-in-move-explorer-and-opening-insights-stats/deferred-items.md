# Phase 80.1 Deferred Items

Out-of-scope discoveries during execute. Not addressed in this phase.

## Pre-existing failure: `test_min_games_per_candidate_floor_at_10`

**Discovered during:** Plan 80.1-01 execution
**File:** `tests/repositories/test_opening_insights_repository.py:388-442`
**Status:** Failing on baseline (`b75a7998`, before this plan's changes)
**Cause:** Phase 79 commit `8dd03f40 refactor(insights): raise opening insights evidence floor to n>=20` raised `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE` from 10 to 20, but this test still seeds 10 games for entry A and asserts inclusion. With the floor at 20, 10 games is below the gate, so entry A is correctly excluded — the test docstring/seeds are stale.
**Fix:** Update seed counts to 20 / 19 (instead of 10 / 9) and rename. Out of scope here; belongs to a Phase 79 follow-up.

## Pre-existing project-wide `ruff format` drift (89 files)

**Discovered during:** Plan 80.1-04 Task 1 (regression matrix).
**Status:** Pre-existing on `main` (verified by formatting `git show main:<path>` on representative samples).
**Cause:** A prior ruff version bump or rules change (likely a cosmetic line-wrap pref) was never followed by a project-wide reformat. `uv run ruff format --check .` reports "92 files would be reformatted" on `main`.
**This plan's scope:** Phase 80.1 only formatted the three test files it modified (`tests/repositories/test_opening_insights_repository.py`, `tests/test_openings_repository.py`, `tests/test_openings_service.py`) — that brings them to clean format and resolves both pre-existing and Phase 80.1-introduced drift on those files. The remaining 89 files are unrelated and out of scope per the executor's SCOPE BOUNDARY rule.
**Fix:** Run `uv run ruff format .` and commit project-wide as a separate `style(repo): apply ruff format` change, ideally as a `/gsd:fast` task between phases. CI is currently not gating on ruff format (otherwise main would be red).
