---
phase: 259-facepalm-first-principles-refit
plan: 04
subsystem: database
tags: [alembic, game_flaws, maia, facepalm, post-commit-hook, postgres]

requires:
  - phase: 259-01
    provides: "facepalm_material_inputs, the single write-time function for the stored loss and missed"
  - phase: 259-03
    provides: "D-09 owner decision confirm-retire (task 1 precondition)"
provides:
  - "migration d1e5f7a9c259: game_flaws.material_loss, material_missed, maia_best_reply_prob (REAL, NULL) with three NOT VALID CHECKs"
  - "full-mode hook writes the two scalars and the best-reply probability for blunders of both sides, next to the unchanged 9-slot arrays"
  - "FACEPALM_COLUMNS gains the two scalars (so spread and line rows carry them); FACEPALM_REPLY_COLUMNS is its own tuple"
  - "_post_blunder_policy: one post-blunder inference feeds both the reply spread and the reply probability"
affects: [259-05, 259-06, 259-09, line-pass, reply-backfill]

actuals:
  tokens: 33000
  tasks: 2
  commits: 2
plan_head_before: c086a6c76bd429daa9f806af828643447a062ffd
plan_head_after: e90a20b192c3b349e8256088a5b5d84aacca6fc8
commits: 2

tech-stack:
  added: []
  patterns:
    - "reply probability lives in its own column tuple outside FACEPALM_COLUMNS, so line mode cannot null it (Pitfall 4)"
    - "one post-blunder policy serves two derived values (spread and reply probability), no second inference"

key-files:
  created:
    - alembic/versions/20261122_120000_d1e5f7a9c259_phase_259_facepalm_scalars.py
  modified:
    - app/models/game_flaw.py
    - app/services/maia_flaw_stats.py
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_scoring.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/maia_fakes.py

key-decisions:
  - "Added FULL_ROW_COLUMNS (base key + FACEPALM + PRE + REPLY tuples) to maia_flaw_scoring as the single statement of the full-mode key set; tests read it instead of hand-typed lists"
  - "An empty post-blunder policy counts reply_missing (token absent from the policy) while the spread stays None, as the plan words it"

patterns-established:
  - "Scalars are written by every mode that computes line facts (full, spread, line) through _facepalm_values; the reply probability only by the mode that runs Maia on the post-blunder board"

requirements-completed: [D-05, D-07, D-10, D-11]

coverage:
  - id: D1
    description: "Instant migration adds the three REAL columns and NOT VALID CHECKs; dev schema is at d1e5f7a9c259 and alembic check reports no drift"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head; uv run alembic current prints d1e5f7a9c259 (head); uv run alembic check reports no new upgrade operations"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full-mode hook stores material_loss, material_missed and maia_best_reply_prob for a user and an opponent blunder, equal to facepalm_material_inputs and the fake policy's value of the first refutation token, with the arrays unchanged"
    requirement: "D-07, D-10"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_writes_material_inputs_and_reply_prob_for_both_sides"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pitfall 4: line mode never writes the reply probability and leaves a stored one untouched; spread, opponent and pre key sets gain no reply key"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_line_mode_rows_never_carry_the_reply_prob"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_line_mode_preserves_a_stored_reply_prob"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_spread_and_opponent_key_sets_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "R1 stays behaviour-neutral: facepalm_expr and facepalm_type_expr compile to SQL that reads none of the three new columns"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_r1_score_expressions_read_no_new_column"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 04: Facepalm scalars write side (R1, part one) Summary

**Migration d1e5f7a9c259 adds material_loss, material_missed and maia_best_reply_prob to game_flaws, and the full-mode hook now stores them for blunders of both sides next to the unchanged material arrays, with the live score still reading only the arrays.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-11-21T16:17:00Z
- **Completed:** 2026-11-21T16:40:00Z
- **Tasks:** 2
- **Files modified:** 7 (1 created)

## Accomplishments

- Instant migration (nullable ADD COLUMN, three NOT VALID CHECKs, literal SQL), applied to the dev DB; `alembic check` shows no model drift.
- `_post_blunder_policy` split out of `_derive_reply_spread`: the single post-blunder inference now yields both `maia_reply_spread` and `maia_best_reply_prob` (first token of the stored refutation line), counting `reply_missing` when the token is absent or not in the policy.
- `_facepalm_values` adds `facepalm_material_inputs(...)` as `material_loss` / `material_missed`; arrays and mate plies untouched, so spread and line passes also refresh the scalars.
- `FACEPALM_REPLY_COLUMNS` is a separate tuple: line mode cannot overwrite a stored reply probability (T-259-07), proven by a mutation (adding the key to `FACEPALM_COLUMNS` fails three tests).

## Task Commits

1. **Task 1: tracer, migration + columns + full-mode writes** - `4d2b6836f` (feat)
2. **Task 2: key sets of every mode, Pitfall 4 and R1 neutrality pinned** - `e90a20b19` (test)

**Plan metadata:** recorded in the follow-up docs commit (SUMMARY, STATE, ROADMAP).

## Files Created/Modified

- `alembic/versions/20261122_120000_d1e5f7a9c259_phase_259_facepalm_scalars.py` - the three columns and NOT VALID CHECKs, downgrade drops them
- `app/models/game_flaw.py` - mapped columns and matching `CheckConstraint(postgresql_not_valid=True)` entries
- `app/services/maia_flaw_stats.py` - `reply_missing` reason, scalar keys on `FacepalmStats`, `MaiaReplyStats` / `null_maia_reply_stats`
- `app/repositories/game_flaws_repository.py` - scalars in `FACEPALM_COLUMNS`, new `FACEPALM_REPLY_COLUMNS`
- `app/services/maia_flaw_scoring.py` - `stored_best_reply_prob`, `_post_blunder_policy`, `refutation_reply_uci`, `_reply_prob`, `_FlawValues.reply`, `FULL_ROW_COLUMNS`
- `tests/services/test_maia_flaw_scoring.py`, `tests/services/maia_fakes.py` - new tests, existing pins updated for the scalars and the reply column

## Decisions Made

- Added `FULL_ROW_COLUMNS` as the one statement of the full-mode key set (tests and the `FACEPALM_REPLY_COLUMNS` import use it), rather than a loose import.
- Empty post-blunder policy counts `reply_missing` (a token not in the policy), keeping the spread None.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests pinned the old column sets**
- **Found during:** Task 1 (first full run of the scoring tests)
- **Issue:** 13 tests failed once the scalars joined `FACEPALM_COLUMNS` and a new `maia_` column existed: the schema scan, `_expected_line_facts`, the stale-facepalm seeds and `assert_maia_lane_state`.
- **Fix:** `_expected_line_facts` adds the scalars via `facepalm_material_inputs`; `_STALE_FACEPALM` gains exact-binary scalar values; the schema test lists `maia_best_reply_prob`; `maia_fakes.assert_maia_lane_state` also checks `FACEPALM_REPLY_COLUMNS` for None on non-scored rows.
- **Files modified:** tests/services/test_maia_flaw_scoring.py, tests/services/maia_fakes.py
- **Committed in:** `4d2b6836f`

---

**Total deviations:** 1 auto-fixed (1 blocking). **Impact on plan:** pin updates the plan anticipated for Task 2 surfaced during Task 1; no scope creep. `tests/scripts/test_backfill_maia_flaws.py` needed no edit (it passes unchanged).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None: the migration is catalog-only and no new endpoint, auth path or trust boundary was added.

## Next Phase Readiness

- Plan 05 (reply backfill mode and its stamp) can build on `FACEPALM_REPLY_COLUMNS`, `_post_blunder_policy` and `_reply_prob`.
- Plan 06 (line pass) writes the scalars for existing rows through line mode, which already carries them.
- The reply probability, the migration and the scalars are on the dev DB only; nothing was deployed.

## Self-Check: PASSED

- Files: migration, SUMMARY and all modified files present on disk.
- Commits `4d2b6836f` and `e90a20b19` are ancestors of HEAD.
- Verify gates: `alembic current` = `d1e5f7a9c259 (head)`, `alembic check` clean, 153 tests in the two plan test files pass, `ty check app/ tests/ scripts/`, depth gate and `ruff check` clean.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
