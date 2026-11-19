---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 03
subsystem: api
tags: [blunder-check, train, guests, cooldown, fastapi, sqlalchemy]

requires:
  - phase: 251-01
    provides: dated blunder-check sessions, train_settings.blunder_check_level, CROSS_MODE_COOLDOWN_DAYS, BlunderCheckLevel
  - phase: 251-12
    provides: per-user blunder-check size passed to compose_windows(count=)
provides:
  - "/blunder-check routes open to every authenticated user, registered or guest (D-18), still scoped to the caller"
  - "LEVEL_ELO, level_fallback_elo and user_level_elo(fallback=): a user without rated games composes at the stored level's Elo (D-17)"
  - "Cross-mode cooldown both directions (D-16): blunder_check_cooled_pairs (puzzle side) and puzzle_cooled_pairs (blunder-check side)"
  - "Measured 18-window foreign-only compose latency and a rating-extreme supply finding for plan 251-09"
affects: [251-09]

plan_head_before: 85fe46969e4e547db3d1da9977bf77df8ff2444b
plan_head_after: 4a3fd81c9c723bb80006e6046b442137f2ae75e2

actuals:
  tokens: 10500
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Cooldown is a read-time filter on (game_id, ply) pairs loaded once per composition; no due_date write"
    - "The cooled pairs also count as served blunder plies for the blunder-check Python judge, so a herring round that reloads the game cannot compose them"

key-files:
  created:
    - tests/repositories/test_cross_mode_cooldown.py
  modified:
    - app/routers/blunder_check.py
    - app/services/blunder_check_selection.py
    - app/services/blunder_check_service.py
    - app/repositories/blunder_check_repository.py
    - app/repositories/train_repository.py
    - tests/routers/test_blunder_check_sessions.py
    - tests/routers/test_blunder_check_drill.py
    - tests/routers/test_blunder_check_solution.py
    - tests/services/test_blunder_check_selection.py

key-decisions:
  - "The cooldown is keyed on the flaw (game_id, ply) and runs from the last serve in local days via session_date; a window counts as served from composition, shown or not (plan A7)"
  - "The cooldown filter is in _select_candidates' due and pool statements and both waiting-count statements, never in pool_entry_stmt (which feeds _material_flags and the eligibility watermark)"
  - "Stored level applies only when the user has no rated games at all (D-17); rated games always win"

patterns-established:
  - "User-id scoping stays in every repository lookup after the beta gate removal; another user's session id answers 404 for non-beta users and guests"

requirements-completed: []

coverage:
  - id: D1
    description: "No /blunder-check route answers 403 for a missing beta flag; a non-beta user and a guest reach every route"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py#test_open_session_non_beta_200_null"
        status: pass
      - kind: integration
        ref: "tests/routers/test_blunder_check_drill.py#test_non_beta_user_reaches_the_drill_routes"
        status: pass
      - kind: integration
        ref: "tests/routers/test_blunder_check_drill.py#test_guest_reaches_the_drill_routes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Removing the gate keeps caller scoping: another user's session id answers 404 for a non-beta user and a guest (T-251-09)"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_drill.py#test_non_beta_user_cannot_touch_another_users_session"
        status: pass
      - kind: integration
        ref: "tests/routers/test_blunder_check_solution.py#test_better_move_non_beta_user_and_guest_reach_the_routes"
        status: pass
    human_judgment: false
  - id: D3
    description: "A guest composes foreign-only sessions at the stored level (beginner 1000, advanced 2000), a non-beta user at the 1500 default; rated games ignore the stored level"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py#test_guest_start_session_composes_at_stored_level"
        status: pass
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py#test_non_beta_start_session_composes_foreign_at_default_level"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_level_rated_games_win_over_the_stored_level"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cross-mode cooldown in both directions, waiting count mirrors composition, due_date untouched, due item resurfaces after the window"
    verification:
      - kind: integration
        ref: "tests/repositories/test_cross_mode_cooldown.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "18-window foreign-only compose latency at the three levels, and thin supply at the rating extremes"
    verification:
      - kind: other
        ref: "temp/251-probe/bc_compose_probe.py (dev DB, recorded below)"
        status: pass
    human_judgment: true
    rationale: "A measurement on a dev-sized dataset; whether the rating-extreme supply gap matters on prod, and the fix, are an owner decision (see Findings)"

duration: 55min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 03: Open blunder check to everyone, stored level, cross-mode cooldown Summary

**The beta gate is gone from every blunder-check route (guests and non-beta users play, still scoped to the caller), users without rated games compose at their stored level's Elo (1000/1500/2000), and a flaw served in either Train mode stays out of the other for 7 local days without touching `drill_items.due_date`.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Commits:** 3 (measured from `plan_head_before`)
- **Files:** 10 (1 created, 9 modified); no migration, no STATE/ROADMAP writes

## Accomplishments

- **D-18:** `current_beta_user` and `BetaUser` deleted; each of the 8 handlers takes `Annotated[User, Depends(current_active_user)]`. No repository lookup changed, so every query is still scoped by the auth-derived user id (T-251-09, tested for a non-beta user and a guest on start/begin/finish/better-move/solution/answer).
- **D-17:** `LEVEL_ELO` (1000/1500/2000, A1), `level_fallback_elo(level)`, `user_level_elo(rows, *, fallback=)`, `_foreign_source(..., fallback_elo=)` and `compose_windows(..., fallback_level_elo=)`. `compose_or_resume` always passes `level_fallback_elo(settings.blunder_check_level)`. The fallback only applies when no rated game yields a pinned Elo.
- **D-16 puzzle side:** `train_repository.blunder_check_cooled_pairs(session, user_id=, since=)` is loaded once per composition and once per waiting-count read; the tuple NOT IN lands in `_select_candidates`' due and pool statements and in both count statements of `get_waiting_puzzle_count`. `pool_entry_stmt` is untouched.
- **D-16 blunder-check side:** `blunder_check_repository.puzzle_cooled_pairs` (drill SR rows of sessions dated inside the window) feeds `pick_own_game_ids`, `_unserved_qualifying_blunder_exists` and `served_for_games` (cooled plies join the served set), threaded from `compose_or_resume` through `compose_windows` and `_Source.cooled_pairs`.

## Task Commits

1. **Task 1 (tracer): open blunder check, stored level** - `6a0956d57` (feat)
2. **Task 2 RED: cooldown behaviour tests** - `1868eabdd` (test)
3. **Task 2 GREEN: cooldown in both modes** - `4a3fd81c9` (feat)

## TDD notes (Task 2)

- **RED** (`1868eabdd`): 4 of 7 tests failed on the planned assertions: `{(1,2),(2,2)} == {(2,2)}` (a due cooled item composed), the same for the untracked pool flaw, `4 == 2` in the mirror test, and a blunder-check own session composed for a flaw served as a puzzle 2 days ago. Semantic assessment: each failed on the missing behaviour, not on a fixture, import or collection fault. The 3 passing tests are regression guards (resurface outside the window, pool flags unaffected, outside-window blunder check composes). `gsd_run check tdd-red-evidence` was not run (pytest format unsupported; plan type is `execute`).
- **GREEN** (`4a3fd81c9`): all green. An eighth test, `test_cooldown_cooled_blunder_not_composed_through_a_herring_round`, was added during GREEN because the SQL pick filter alone hides the served-set path; proven by mutation: neutralising the cooled loop in `served_for_games` fails exactly that test.
- Task 1 mutation check: replacing the service's `fallback_level_elo` with the constant 1500 fails both `test_guest_start_session_composes_at_stored_level` cases.

## Latency probe (A2, RESEARCH Pitfall 8)

`temp/251-probe/bc_compose_probe.py` on the dev DB (167,526 games, 9,771 fully evaluated, all non-guest), user 153 with no games at all (so the stored level is the level), `compose_windows(count=18, fallback_level_elo=...)`, 3 rounds each, read-only:

| Level | Fallback Elo | Windows composed | Time per round |
|---|---|---|---|
| beginner | 1000 | 0 / 18 (all 3 rounds) | 709, 595, 541 ms |
| intermediate | 1500 | 18 / 18 (all foreign, all 3 rounds) | 507, 317, 319 ms |
| advanced | 2000 | 0 / 18 (all 3 rounds) | 472, 464, 413 ms |

**Latency is fine: an 18-window foreign-only compose is about 0.3-0.5 s, far below the 2 s threshold. The slider maximum of 18 is not a latency problem.** The problem is supply, see Findings.

## Findings for the owner and plan 251-09

1. **Rating-extreme guests get an empty session on dev-sized data (decision needed).** At beginner (1000) and advanced (2000) the 18-window compose returned 0 windows, so POST /blunder-check/sessions would answer 409 "No blunder-check sequences available" for a guest at those levels. Cause, measured on the same DB: the foreign pick is a `TABLESAMPLE SYSTEM (2%)` of `games`, and the number of fully evaluated non-guest games within the pinned-Elo band (+-150) of each level is 660 (1000), 4,232 (1500) and 1,188 (2000), of which 569 / 3,924 / 1,020 hold a blunder flaw. A 2% page sample yields about 13 candidates at 1000 and 24 at 2000 before the unserved-facepalm filter, against about 85 at 1500. Four dev samples per level: 0 in-band games out of 10-25 picked at 1000 and at 2000, 10-36 of 10-36 at 1500. This is a thin-supply symptom of the existing 2% sample, not a bug in this plan, and prod density may differ. My test for the stored level raises the sample to 100% on purpose. Options (not done, outside this plan's files): a larger `FOREIGN_SAMPLE_PERCENT` or a retry round at a higher percentage when a fallback-level compose comes back short; or widen the band for the fallback case. Plan 251-09 should not trust the slider maximum of 18 at the rating extremes until this is resolved; short or empty sessions are expected there.
2. **Pinned vs raw prefilter at the extremes.** Picked games at the 1000 level have pinned Elos from about 1420 because raw ratings 350..1650 map through `normalize_to_lichess_blitz`; the raw prefilter (level +-650) is wide, so the exact pinned band (+-150) check is what empties the batch.
3. **Dev-DB-only guest signal.** The guest test seeds foreign games with a user created by `register_user`; prod guests will also be foreign-only. D-17's promise for beginners and advanced players depends on finding 1.

## EXPLAIN (both cooled-pair queries, dev DB, user 28)

The dev tables are tiny (25 blunder-check sessions, 141 windows, 34 drill sessions, 234 drill solves), so the default planner picks sequential scans on them and the numbers say little about prod. With `SET LOCAL enable_seqscan = off` both queries use indexes end to end:

- `blunder_check_cooled_pairs` (windows JOIN sessions, user_id and session_date filter): default plan Hash Join over a Seq Scan on `blunder_check_windows` and a Seq Scan on `blunder_check_sessions`, 1.5 ms. Index-forced: Bitmap Index Scan on `ix_blunder_check_windows_user_game` + Index Scan on `blunder_check_sessions_pkey`, 0.49 ms.
- `puzzle_cooled_pairs` (drill_sessions JOIN drill_solves): default plan Seq Scan on `drill_sessions` (filtered by user_id and session_date) then Bitmap Index Scan on `uq_drill_solves_session_puzzle`, 1.2 ms. Index-forced: Index Scan on `drill_sessions_pkey` then the same drill_solves index, 0.32 ms.

**Follow-up (no migration here; plan 02 owns the Alembic head):** `drill_sessions` has no `(user_id, session_date)` index (only the primary key and the partial unique open index), so `puzzle_cooled_pairs` and the existing `completed_session_in_window` scan the table for the user. Low urgency at prod volumes; worth a look when the table grows.

## Deviations from Plan

**1. [Rule 2 - Missing critical test] Herring-round path for the cooled blunder**
- **Found during:** Task 2 GREEN (mutation check)
- **Issue:** The planned five behaviours do not exercise `served_for_games`; the SQL pick filter hid the cooled blunder before the Python judge ran, so removing the served-set addition passed every test, although a herring-round plain pick reloads the game and the judge would then fill a blunder slot with the cooled blunder.
- **Fix:** Added `test_cooldown_cooled_blunder_not_composed_through_a_herring_round`; proven by mutation.
- **Commit:** `4a3fd81c9`

**2. [Rule 3 - Blocking] ty typing of the helper columns**
- **Issue:** `ColumnElement[int]` parameters rejected ORM attributes; typed `_not_cooled` with `SQLColumnExpression[int]` as the blunder-check repository already does.
- **Commit:** `4a3fd81c9`

**Total deviations:** 2 (1 test addition, 1 typing fix). **Impact:** none on scope.

## Issues Encountered

None blocking. Full backend suite (`uv run pytest -n auto`: 7038 passed, 19 skipped), `ruff format`, `ruff check`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean. The probe's first runs measured a user with games (so the level came from their own rating, not the stored one); the probe now picks a user with no games at all, which is what a guest is.

## Known Stubs

None.

## Threat Flags

None. No new endpoint. The gate removal widens who reaches existing routes (T-251-09, mitigated and tested), and guest churn composing foreign sessions is covered by the existing one-open-session index, the completed-in-window guard and the per-user size cap (T-251-10); latency measured above. Finding 1 means a guest at an extreme level may see 409 rather than a session, which is a UX gap, not a security one.

## Next Phase Readiness

Plan 251-09 (launch slider) should keep 18 as the maximum on latency grounds and take Finding 1 into account for the rating-extreme levels. Plan 02 owns the migration head; nothing here adds one. The cooldown semantics for a window that was composed but not yet shown (counted as served) are noted in `blunder_check_cooled_pairs`; RESEARCH Open Question 3 (a BC window on a blunder the user has seen as a puzzle can be recognised) is limited in time by the 7-day cooldown, not removed.

## Self-Check: PASSED

- Created files exist: `tests/repositories/test_cross_mode_cooldown.py`, this SUMMARY.
- Commits `6a0956d57`, `1868eabdd`, `4a3fd81c9` are ancestors of HEAD.
- Acceptance greps: `beta_enabled` count 0 in the router; `Depends(current_active_user)` 8 = `@router.` 8; `LEVEL_ELO` 7 occurrences; `blunder_check_cooled_pairs` 3 in `train_repository.py`; `puzzle_cooled_pairs` in the blunder-check repository and service; no new `due_date` write in the diff; `-k guest` selects 4 tests and `-k level` 13 tests, all pass.
- Not run here: the frontend gates (no frontend files touched).
