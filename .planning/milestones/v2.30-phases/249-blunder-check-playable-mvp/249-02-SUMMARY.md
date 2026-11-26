---
phase: 249-blunder-check-playable-mvp
plan: 02
subsystem: database
tags: [postgres, alembic, fastapi, sqlalchemy, blunder-check, beta-gate]
status: complete

requires:
  - phase: 248-maia-refutation
    provides: game_flaws.maia_refutation_prob/rank, games.maia_refutation_completed_at (alembic head c4e9b1d7f248)
provides:
  - blunder_check_sessions / blunder_check_windows / blunder_check_answers tables (D-15)
  - ix_games_user_full_evals partial index (index-only own-game pick)
  - /api/blunder-check router with the current_beta_user gate (D-01) and GET /sessions/open
  - repository read/insert paths for the session composer (picks, loaders, served sets, elo source)
  - tests/blunder_check_seed.py shared seed helper
affects: [249-03, 249-04, 249-05, phase-251]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: 205eeb98cb6994fb4b743645f00b7a999aaeed74
plan_head_after: 5a3562f365b37983bb60f2b87a92dede7396dede

tech-stack:
  added: []
  patterns:
    - "Own session/window/answer tables per game mode instead of widening drill_sessions"
    - "Windows snapshot start_fen + move_ucis so a foreign game delete (FK SET NULL) never breaks another user's session"
    - "Beta gate as a FastAPI dependency (current_beta_user) layered on current_active_user"

key-files:
  created:
    - app/models/blunder_check.py
    - alembic/versions/20261110_120000_d5b8e2f1a249_phase_249_blunder_check_tables.py
    - app/routers/blunder_check.py
    - app/schemas/blunder_check.py
    - app/repositories/blunder_check_repository.py
    - tests/blunder_check_seed.py
    - tests/routers/test_blunder_check_sessions.py
    - tests/repositories/test_blunder_check_repository.py
  modified:
    - app/models/game.py
    - alembic/env.py
    - app/main.py

key-decisions:
  - "D-15: own tables, not shared drill_sessions columns (schedule-bound NOT NULL columns, and uq_drill_sessions_user_open would block concurrent puzzle + blunder-check sessions); Phase 251 reads a UNION over both session tables"
  - "No age weighting in pick_own_game_ids: ordering by age needs the heap and defeats the index-only scan"
  - "insert_session only treats uq_blunder_check_sessions_user_open as an expected race loss; any other IntegrityError re-raises"
  - "Games index created non-concurrently (project precedent: quiescent backend at container start)"

patterns-established:
  - "Seed helper self-check: seed_judged_game runs the production _run_all_moves_pass on the in-memory rows and raises when a seeded blunder ply is not classified as a blunder"
  - "with_user_blunder / with_opponent_gift shift row ply and every later row so the reply is not itself a drop"

requirements-completed: [D-01, D-09, D-10, D-15, D-19]

coverage:
  - id: D1
    description: "Every /api/blunder-check route answers 401 anon, 403 non-beta, 200 beta"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py"
        status: pass
  - id: D2
    description: "Three own tables with SMALLINT IntEnum + CHECK, TEXT + CHECK status, explicit-ondelete FKs, one open session per user; alembic check reports no drift"
    requirement: "D-15"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py (schema, insert tests); alembic upgrade head + alembic check on a scratch DB"
        status: pass
  - id: D3
    description: "served_for_games returns prompted blunder plies and judged ranges per game"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py::test_served_*"
        status: pass
  - id: D4
    description: "Foreign pick returns only fully evaluated, rating-banded, non-guest, non-own games"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py::test_pick_foreign_game_ids_applies_every_filter"
        status: pass
---

# Phase 249 Plan 02: Blunder-check persistence, beta gate and read paths Summary

**Three own blunder-check tables with a beta-gated `/api/blunder-check` router (tracer: `GET /sessions/open`) and every repository read the session composer needs, proven against real seeded rows.**

## Accomplishments

- Task 1 (tracer): models, migration `d5b8e2f1a249` (no drift), `ix_games_user_full_evals`, router with `current_beta_user` (401/403/200), session response schema, `open_session_progress`, 5 router tests including user scoping (T-249-03).
- Task 2: `insert_session` (SAVEPOINT, returns None to the one-open-index loser), `pick_own_game_ids`, `pick_foreign_game_ids` (TABLESAMPLE SYSTEM, guests and own games excluded), `load_candidate_games`, `load_positions`, `load_blunder_flaws`, `served_for_games`, `recent_rated_games`, plus `tests/blunder_check_seed.py` and 13 repository tests.
- Mutation-checked two tests: removing the guest filter fails the foreign-pick test, widening the prompted-ply predicate fails the served test.

## Task Commits

1. Task 1 (tracer): `4095e6c9a` feat(249-02): blunder-check tables, beta gate and open-session tracer
2. Task 2: `5a3562f36` feat(249-02): session insert race, candidate loaders, served sets and test seed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verified the migration on a scratch database, not the shared dev DB**
- **Found during:** Task 1 verify
- **Issue:** The plan's verify runs `uv run alembic upgrade head` against the dev DB, which the run rules forbid (another worktree shares it).
- **Fix:** Created `scratch_249_02` in the dev Postgres container, ran `upgrade head`, `alembic check` ("No new upgrade operations detected"), a downgrade to `c4e9b1d7f248` and re-upgrade, then dropped the database. The test suite also exercises the migration via the auto-refreshing template DB.

**2. [Rule 1 - Design] `with_user_blunder` / `with_opponent_gift` shift all later rows**
- **Issue:** Shifting only row `ply` makes the very next reply a large recovery (an opponent "blunder" of equal size), polluting fixtures.
- **Fix:** The swing persists from row `ply` onward. Documented in the helper docstrings.

**3. [Rule 2 - Extension] `register_user(..., guest=False)` extra keyword**
- Needed so the foreign-pick test can create a guest owner; default behavior matches the planned signature.

**4. SEED_PGN** is a deterministic seeded quiet playout (60 plies, verified legal by python-chess replay), not a famous game; the plan only required a legal mainline of at least 44 plies.

## Known Stubs

None. (`_SESSION_ID_MAX` and `_WINDOW_POSITION_MAX` in the router are defined per the plan but unused until plan 04-05 add path-id routes.)

## Threat Flags

None beyond the plan's threat model; T-249-02..06 are mitigated as planned (beta gate, user-id scoping, one-open index + SAVEPOINT, guest and own-game exclusion in the foreign pick, game ids only).

## Verification

- `alembic heads` -> `d5b8e2f1a249 (head)`; `alembic check` clean on a scratch DB.
- 18 tests passed (5 router, 13 repository); `ruff format/check` clean; `ty check app/ tests/ scripts/` clean; `check_function_size.py app/ --fail-over-depth 4` OK.

## Self-Check: PASSED

- Files exist: all 8 created files and 3 modified files listed above.
- Commits `4095e6c9a` and `5a3562f36` are ancestors of HEAD.
