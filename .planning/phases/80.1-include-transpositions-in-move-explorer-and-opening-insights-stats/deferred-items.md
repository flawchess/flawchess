# Phase 80.1 Deferred Items

Out-of-scope discoveries during execute. Not addressed in this phase.

## Pre-existing failure: `test_min_games_per_candidate_floor_at_10`

**Discovered during:** Plan 80.1-01 execution
**File:** `tests/repositories/test_opening_insights_repository.py:388-442`
**Status:** Failing on baseline (`b75a7998`, before this plan's changes)
**Cause:** Phase 79 commit `8dd03f40 refactor(insights): raise opening insights evidence floor to n>=20` raised `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE` from 10 to 20, but this test still seeds 10 games for entry A and asserts inclusion. With the floor at 20, 10 games is below the gate, so entry A is correctly excluded — the test docstring/seeds are stale.
**Fix:** Update seed counts to 20 / 19 (instead of 10 / 9) and rename. Out of scope here; belongs to a Phase 79 follow-up.
