---
phase: 263-foreign-blunder-fillers
plan: 01
subsystem: api
tags: [train, sqlalchemy, tablesample, alembic, postgres, tdd]

requires:
  - phase: 250-blunder-check-foreign-games
    provides: user_level_elo, level_fallback_elo, FOREIGN_RATING_BAND, the TABLESAMPLE foreign-game pattern
provides:
  - DrillSource.FOREIGN_BLUNDER = 3 with ck_drill_solves_source widened to (0, 1, 2, 3)
  - servable_blunder_predicates shared by pool_entry_stmt and the foreign draw statements
  - foreign_band_candidates_stmt and foreign_nearest_candidates_stmt (bounded TABLESAMPLE over non-guest games)
  - app/services/train_foreign.py (draw constants, ForeignCandidate, pure pick_foreign_candidates)
  - _backfill_foreign_blunders composition stage after herring reconstruction
  - owner-keyed answer key and solve classification (foreign puzzles read the game owner's rows)
  - DrillSourceWire Literal with "foreign_blunder"
  - conftest stub of the draw seam plus the real_foreign_draw opt-in fixture
affects: [263-02, 263-03, 263-04, 263-05, 263-06, 263-07, 263-08, 263-09, 263-10]

actuals:
  tokens: 15950
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Cross-user live join keyed on the game owner (Game.user_id), gated on DrillSolve.source, with DrillSolve.user_id kept as the access scope"
    - "Single test seam (_draw_foreign_candidates) stubbed by an autouse conftest fixture, opt-in via real_foreign_draw"

key-files:
  created:
    - app/services/train_foreign.py
    - alembic/versions/20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py
    - tests/train_foreign_seed.py
    - tests/repositories/test_train_foreign.py
    - tests/routers/test_phase_263_foreign_source_migration.py
  modified:
    - app/services/train_pool.py
    - app/repositories/train_repository.py
    - app/models/drill_solve.py
    - app/schemas/train.py
    - tests/conftest.py
    - tests/repositories/test_train_repository.py
    - tests/test_admin_activity_stats.py

key-decisions:
  - "A puzzle's game_flaws / game_positions rows are keyed by the game owner (Game.user_id), not the solver; the solver id stays the access scope in every WHERE"
  - "_wire_game_id sends game_id None on the wire for a foreign blunder; the drill_solves row keeps the real id for uq_drill_solves_session_puzzle"
  - "The lichess sharp-filler stage stays directly after the foreign stage (transitional) and only fills what the foreign stage leaves; 263-07 deletes it"
  - "No full_evals_completed_at and no facepalm cut in the foreign statement: D-06 allows exactly the six pool_entry_stmt predicates"

patterns-established:
  - "servable_blunder_predicates: one definition of a servable blunder for own and foreign draws"
  - "Migration with module-level UPGRADE_STATEMENTS / DOWNGRADE_STATEMENTS and a rolled-back round-trip test; downgrade deletes the new-source rows before narrowing the CHECK"

requirements-completed: [D-01, D-02, D-05, D-06, D-07, D-14, D-15, D-17]

coverage:
  - id: D1
    description: "A session short of own material is filled with a servable blunder from a similarly rated non-guest player; a full own supply calls no foreign draw"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key"
        status: pass
    human_judgment: false
  - id: D2
    description: "The draw reads only other users' non-guest games, with the six shared servability predicates, no extra predicate"
    requirement: "D-01, D-06"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_draw_returns_servable_stranger_blunder"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_draw_skips_guest_strangers"
        status: pass
    human_judgment: false
  - id: D3
    description: "Key, puzzle type and graded set come live from the game owner's rows; solving grades on the SR path with source foreign_blunder and no drill_items row"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key"
        status: pass
    human_judgment: false
  - id: D4
    description: "Seeded random in-band pick with nearest-first fallback, no time-control or facepalm input, served positions never redrawn, one puzzle per game"
    requirement: "D-14, D-15, D-17"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_foreign.py#TestPickForeignCandidates"
        status: pass
    human_judgment: false
  - id: D5
    description: "Migration b3d5f7a9c264 widens the CHECK and its downgrade deletes source 3 rows first"
    verification:
      - kind: integration
        ref: "tests/routers/test_phase_263_foreign_source_migration.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Prod EXPLAIN of the foreign draw at levels 1500 and 2600 stays inside the latency budget (band step 0.5 s cold, both steps 1.5 s cold)"
    verification: []
    human_judgment: true
    rationale: "Needs the prod database; the plan defers the EXPLAIN to 263-10 before the squash-merge and again after the deploy"

duration: 25min
completed: 2026-11-23
status: complete
plan_head_before: d28f50117b3e983c05a2dd901bc7db5cfab12eaf
plan_head_after: ff8ba374e08eab3e50fd88b57f2b81cef5090a8a
commits: 3
---

# Phase 263 Plan 01: Foreign Blunder Tracer Summary

**A short Train session now fills with a servable blunder from a similarly rated non-guest player's game (bounded TABLESAMPLE draw), keyed and graded live from the game owner's rows on the SR path, with the stranger's game id never on the wire.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-23
- **Tasks:** 3 (seed helper, draw read path plus suite seam, tracer)
- **Files modified:** 14 (5 created)

## Accomplishments

- Task 1 `acf6b9bf0`: `tests/train_foreign_seed.py` with `add_stranger`, `add_rated_games`, `add_foreign_blunder_game`, legal key and runner-up moves asserted at import. The worktree needed no provisioning beyond a no-op `uv sync --group maia-inference` (already installed); DB tests reach the dev container with no env file.
- Task 2 `ce8335782`: `servable_blunder_predicates` extracted from `pool_entry_stmt` (no SQL change), `foreign_band_candidates_stmt` and `foreign_nearest_candidates_stmt` over a `tablesample` CTE (non-guest, not the solver, `ANALYTICS_INCLUDED_PLATFORMS`, `ORDER BY random()` before the LIMIT in band mode, distance order in nearest mode), the pure `train_foreign` module, the `_draw_foreign_candidates` seam, and the autouse conftest stub with the `real_foreign_draw` opt-in.
- Task 3 `ff8ba374e`: `DrillSource.FOREIGN_BLUNDER = 3`, migration `b3d5f7a9c264`, `_served_foreign_positions`, `_backfill_foreign_blunders` (level from `user_level_elo` with `level_fallback_elo`, seeded RNG, at most two statements), the foreign stage in `_assemble_session_items` after herring reconstruction (herring games excluded, with a fix-site comment on the `uq_drill_solves_session_puzzle` collision), `_wire_game_id`, owner-keyed `_answer_keys_by_position` and `_classify_sr_solve(flaw_owner_id=...)`, explicit source dispatch in `_classify_and_certify_solve`, `_wire_source` and the `DrillSourceWire` alias on all six Literal sites.

## Mutation check (acceptance criterion)

Reverting the owner-keyed joins of `_answer_keys_by_position` to `DrillSolve.user_id` makes the tracer fail:

```
>       assert puzzle.key_move_uci == FOREIGN_KEY_UCI
E       AssertionError: assert None == 'e2e4'
1 failed, 13 deselected
```

Restored: `tests/repositories/test_train_foreign.py` 14 passed.

## Verification observed

- `uv run pytest -n auto -q` (full backend suite, before the last two test-only edits): 7065 passed, 9 skipped, 1 failed (`test_fetch_puzzle_difficulty_splits_by_source`, fixed below and re-run green: 46 passed in that file).
- Train suites from the plan's second verify command: 518 passed.
- `uv run ruff check .` clean, `ruff format --check` clean, `uv run ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4` clean (1701 functions, no breach).
- `uv run alembic heads` prints `b3d5f7a9c264 (head)` now (it printed `e5c1b7d3a9f2 (head)` before Task 3, as the Task 1 criterion expected).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test invariant] Existing tests that go red on a fourth source**
- **Found during:** Task 3 full-suite run
- **Issue:** `test_drill_solve_identity_column_matches_source` is an assumption-delta invariant that asserts its mapping equals `set(DrillSource)`; `test_fetch_puzzle_difficulty_splits_by_source` zero-fills over `DrillSource`.
- **Fix:** mapped `FOREIGN_BLUNDER` to `game_id` (distinctness now asserted over the two source-exclusive columns, the DB-backed companion expects every source except the foreign one, which test_train_foreign covers); the activity test seeds one foreign solve and expects `[1, 1, 0, 0]`. The "existing suites unchanged" criterion therefore holds for behaviour, not for these two literal expectations.
- **Files modified:** tests/repositories/test_train_repository.py, tests/test_admin_activity_stats.py
- **Commit:** ff8ba374e

**2. [Rule 2 - Missing tests] Extra tests beyond the three named**
- A guest-exclusion test (D-01 / T-263-03), pure `pick_foreign_candidates` and sizing tests (served, exclusion, band-first, one per game, sharp preference, seeded reproducibility), and a rolled-back migration round trip including the downgrade-order guard (T-263-05). Commits ce8335782 and ff8ba374e.

**3. [Rule 3 - Blocking] `_assemble_session_items(blunder_check_level=...)` defaults to None**
- An existing test calls `_assemble_session_items` directly without the new argument; a default keeps it unchanged. `compose_and_materialize_session` passes the stored level.

**4. [Structure] Helpers beyond the plan's list**
- `_foreign_picks` and `_has_sharp` (split of `_backfill_foreign_blunders` to keep nesting shallow), `ForeignCandidateSelect` alias and two private statement builders in `train_pool.py`. No behaviour beyond the plan.

## Known Stubs

None. `want_sharp=False` in the composition call is deliberate: 263-03 wires D-16 (first-session sharp preference) and `pick_foreign_candidates` already supports it.

## Threat Flags

None beyond the plan's threat model. The new cross-user read (T-263-03) is covered by the guest and own-game assertions in `test_train_foreign.py`; the wire game id (T-263-01) by the tracer's `puzzle.game_id is None`.

## Left for later plans

- Resume, completion leniency, composition puzzle types (263-03), reveal and facepalm (263-06), deletion of the lichess filler stage (263-07), warm-up retirement.
- Prod EXPLAIN of the draw at levels 1500 and 2600 (263-10 UAT list).

## Self-Check: PASSED

- FOUND: app/services/train_foreign.py, tests/train_foreign_seed.py, tests/repositories/test_train_foreign.py, tests/routers/test_phase_263_foreign_source_migration.py, alembic/versions/20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py
- FOUND commits acf6b9bf0, ce8335782, ff8ba374e on gsd/phase-263-foreign-blunder-fillers
