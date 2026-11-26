---
phase: 250-facepalm-blunder-selection
plan: 01
subsystem: database
tags: [alembic, python-chess, sqlalchemy, logistic-score, maia, blunder-check]

requires:
  - phase: 247-maia-flaw-stats
    provides: "maia_played_prob and the effective-moves entropy formula reused as reply_spread"
  - phase: 248-maia-refutation
    provides: "game_positions.pv refutation line and the Maia scoring pattern this extends"
provides:
  - "8 nullable game_flaws columns (maia_reply_spread, line_loss_1/3/5/7/9, line_mate_ply, facepalm_score) and 2 games stamps, metadata-only, applied to the dev DB"
  - "app/services/line_material.py: line_facts() material count along a stored line with D-05 NULL rules"
  - "app/services/facepalm_score.py: FacepalmModel, loss_feature, facepalm_score and its SQL twin facepalm_score_sql"
  - "D-04 constants FACEPALM_SCORE_MIN / PLAYED_PROB_OFFSET / LINE_DEPTH / LOSS_CAP / MATE_LOSS"
  - "public maia_flaw_stats.reply_spread"
affects: [250-02, 250-03, 250-04, 250-05, 250-06, facepalm fit, backfill, blunder-check selection]

actuals:
  tokens: 12263
  tasks: 3
  commits: 4
plan_head_before: f164c4b59e2b4e38193a872bbb15bbc6d77ccb24
plan_head_after: 6fcc5d37a691bd633062a6737eea234994ab6c3e

tech-stack:
  added: []
  patterns:
    - "Python/SQL twin pair for a score formula, pinned together by a VALUES-grid parity test with NULLs"
    - "Pure line replay builds per-ply steps once, then derives every stored depth plus the mate ply from them"

key-files:
  created:
    - alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py
    - app/services/line_material.py
    - app/services/facepalm_score.py
    - tests/services/line_material_fixtures.py
    - tests/services/test_line_material.py
    - tests/services/test_facepalm_score.py
  modified:
    - app/models/game_flaw.py
    - app/models/game.py
    - app/services/blunder_check_rules.py
    - app/services/maia_flaw_stats.py
    - tests/services/test_maia_flaw_scoring.py

key-decisions:
  - "A short line that ends on an opponent capture counts as settled by the recapture credit even when the credit is 0 (the static exchange was evaluated and found nothing to recapture), and the credit is applied whenever the legal line length is <= depth, including the line that is exactly depth plies long, as in the reference"
  - "facepalm_score_sql wraps its result in type_coerce(Float) only to satisfy ty (SQLAlchemy types func.exp as float | Decimal); the emitted SQL is unchanged"
  - "No CHECK on the score range; the range is a test concern so the ADD COLUMN stays catalog-only"

patterns-established:
  - "line_facts parses the stored line once into _Step records; depth losses, the mate ply and the credit all read those steps"
  - "Fixture module copies the gitignored label-cache strings verbatim; tests never read temp/ files"

requirements-completed: [D-01, D-02, D-04, D-05]

coverage:
  - id: D1
    description: "Migration e8b3c6d2f250 adds the 8 game_flaws columns and 2 games stamps, metadata-only; dev DB at head with no drift"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic check (No new upgrade operations detected)"
        status: pass
      - kind: unit
        ref: "tests/services/test_line_material.py#test_line_facts_round_trip_through_game_flaws_columns"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_schema_maia_columns_typed_nullable"
        status: pass
    human_judgment: false
  - id: D2
    description: "line_facts reproduces the reference capture_loss on label rows #13/#35/#153/#154/#156/#165/#170/#176/#177/#184 and the seven 1-ply mate lines"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/services/test_line_material.py#test_label_fixture_matches_reference"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-05 NULL rules: short lines give NULL depths, unusable input gives all-NULL facts without raising, the caller's board is never mutated"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_line_material.py#test_synthetic_rules, test_unusable_input_gives_null_facts, test_caller_board_is_not_mutated"
        status: pass
    human_judgment: false
  - id: D4
    description: "facepalm_score and facepalm_score_sql agree within 1e-9 on a grid with NULLs in every input, for both loss-floor variants"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_sql_twin_matches_python"
        status: pass
    human_judgment: false
  - id: D5
    description: "Known D-04 constants in the selection constants block and public reply_spread equal to the Phase 247 effective-moves formula"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_known_d04_constants, test_reply_spread_equals_phase_247_effective_moves"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 01: Facepalm Score Foundations Summary

**Ten nullable facepalm columns on game_flaws/games, a pure line-material counter that reproduces the owner's reference on 17 label fixtures, and the logistic facepalm score with a parity-tested SQL twin**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-13T19:04:31Z
- **Completed:** 2026-11-13T19:17:30Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments

- Alembic revision `e8b3c6d2f250` (down revision `d5b8e2f1a249`, which was the actual head) adds `maia_reply_spread`, `line_loss_1/3/5/7/9`, `line_mate_ply`, `facepalm_score` to `game_flaws` and `facepalm_spread_completed_at` / `facepalm_line_completed_at` to `games`. No default, CHECK or index; applied to the dev DB, `alembic check` clean.
- `line_facts(pre_board, played_uci, pv)` is a rewrite of the reference `capture_loss` as app code: piece values 1/3/3/5/9, captures only, the blunder's own capture credited, depth+1 recapture, desperado rule, static-exchange recapture credit, plus the D-05 NULL semantics (a depth the line does not reach is NULL unless a mate or the credit settles it) and the line mate ply.
- Oracle check: the reference `capture_loss` from `temp/blunder-check/refine.py` was run on every copied fixture string before commit; oracle matched 17/17 (ten label rows and seven 1-ply mate lines, all the expected values in the plan). Mutation check: disabling the recapture credit fails the #176, n176 and en passant cases; dropping the SQL loss floor fails the parity test.
- `facepalm_score` / `facepalm_score_sql` / `loss_feature` / `FacepalmModel`, the five D-04 constants and public `reply_spread` give plans 02 to 06 their shared building blocks. The fitted default model is plan 04's job.
- Verification: 6234 passed, 19 skipped on the full suite with `-n auto`; ruff, `ty check app/ tests/ scripts/`, `ty check analysis/` and `check_function_size.py --fail-over-depth 4` are clean.

## Task Commits

1. **Task 1: Tracer, one real blunder's line facts in the new columns** - `3a338f058` (feat)
2. **Task 2: Full D-02 fixture table and the D-05 NULL rules** - `566308247` (test)
3. **Task 3: Score formula with SQL twin, D-04 constants, public reply_spread** - `82b029160` (feat)
4. **Deviation fix: schema scan test accepts maia_reply_spread** - `6fcc5d37a` (test)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py` - metadata-only migration
- `app/models/game_flaw.py`, `app/models/game.py` - the new mapped columns and stamps
- `app/services/line_material.py` - `LineFacts`, `line_facts`, `null_line_facts`, depth/column constants
- `app/services/facepalm_score.py` - score formula and SQL twin
- `app/services/blunder_check_rules.py` - `FACEPALM_SCORE_MIN`, `PLAYED_PROB_OFFSET`, `LINE_DEPTH`, `LOSS_CAP`, `MATE_LOSS`
- `app/services/maia_flaw_stats.py` - public `reply_spread`
- `tests/services/line_material_fixtures.py` - `LineFixture` and the 17 `LINE_FIXTURES`
- `tests/services/test_line_material.py`, `tests/services/test_facepalm_score.py` - fixture, synthetic, NULL, round-trip and twin-parity tests

## Decisions Made

- The recapture credit settles a short line even when its value is 0, and it is applied whenever the legal line length is at most the depth (including a line exactly `depth` plies long), matching the reference.
- `type_coerce(Float)` on the SQL score only silences ty's `float | Decimal` typing of `func.exp`; the SQL is unchanged.
- No CHECK on the score range (research recommendation); the range is covered by the logistic form and tests.

## TDD Gate Compliance

Task 1 is a tracer that delivers the implementation together with its first tests, so Tasks 2 and 3 (marked `tdd="true"`) had no separate RED commit: their tests passed on first run for Task 2 because `line_facts` already existed, and Task 3's tests were written with the implementation in one commit. The tests were verified to detect regressions by mutation (credit disabled, SQL floor removed) instead. This plan is `type: execute`, so the plan-level RED/GREEN gate does not apply.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Phase 247/248 schema test broke on the new column prefix**
- **Found during:** full-suite run after Task 3
- **Issue:** `test_schema_maia_columns_typed_nullable` scans `game_flaws` for every `maia_%` column and asserts the exact set; `maia_reply_spread` now matches.
- **Fix:** added `maia_reply_spread: real` to the expected set with a Phase 250 comment.
- **Files modified:** tests/services/test_maia_flaw_scoring.py
- **Verification:** 53 passed in that module, then the full suite green
- **Committed in:** 6fcc5d37a

**2. [Rule 3 - Blocking] ty rejected the SQL twin's return type**
- **Found during:** Task 3
- **Issue:** `func.exp` yields `ColumnElement[float | Decimal]`, not assignable to the declared `ColumnElement[float]`.
- **Fix:** `type_coerce(..., Float(asdecimal=False))` on the result (typing only).
- **Files modified:** app/services/facepalm_score.py
- **Committed in:** 82b029160

---

**Total deviations:** 2 auto-fixed (1 bug in a dependent test, 1 blocking typing)
**Impact on plan:** Both necessary for the zero-error gates. No scope creep.

## Issues Encountered

- Task 2's `<verify>` asks for "at least 30 passed" in `test_line_material.py`; the file reports 32 passed (17 fixtures, 5 synthetic, 7 unusable-input, no-mutation, two tracer tests).
- The plan's synthetic expectations carry D-05 NULLs that the reference cannot produce (it returns a number for short lines); the oracle confirmed the loss values, and the NULL pattern is the D-05 rule implemented here.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The only new surface is nullable columns and pure functions; T-250-01 (malformed or illegal worker-supplied pv) is mitigated and tested with `zz99`, an illegal first token, a malformed token with a tail and an illegal mid-line token.

## Next Phase Readiness

- Plans that write the columns (hook, backfill, fit) can call `line_facts(...).as_columns()` and `reply_spread(...)` directly; `bulk_update_game_flaw_rows` already accepts the new keys.
- Plan 04 must add the fitted coefficients (a default `FacepalmModel`) to the constants block; `FACEPALM_SCORE_MIN` is the owner's starting 0.7 until D-18.
- Prod migration is catalog-only; nothing was run against prod.

## Self-Check: PASSED

All six created files exist, the four commits (`3a338f058`, `566308247`, `82b029160`, `6fcc5d37a`) are ancestors of HEAD, and `alembic heads` prints `e8b3c6d2f250 (head)`.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
