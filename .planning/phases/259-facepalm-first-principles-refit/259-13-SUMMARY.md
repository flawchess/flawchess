---
phase: 259-facepalm-first-principles-refit
plan: 13
subsystem: facepalm
tags: [facepalm, drop-release, quiet-rule, d-05, d-06, line-material]

requires:
  - phase: 259-12
    provides: "switch release live: the score reads the stored scalars, no reader of the 9-slot arrays in the score path"
provides:
  - "Writers (hook, full, spread, line modes) store material_loss, material_missed and both mate plies from the quiet facts; no 9-slot array is written"
  - "FACEPALM_COLUMNS / FacepalmStats without the array keys"
  - "Features pull and blunder-check sample/render off the arrays and the shipped rule"
  - "app/services/line_material.py holds the quiet rule only"
affects: [259-14, 259-15]

actuals:
  tokens: 36500
  tasks: 3
  commits: 3
commits: 3
plan_head_before: d5ba13cfd18a426c16cfaa0ba7c16f0990cb55d7
plan_head_after: bff487492

tech-stack:
  added: []
  patterns:
    - "Stored facepalm facts = quiet_line_facts / quiet_best_line_facts -> material_inputs_from_facts, computed once in _facepalm_values"

key-files:
  created: []
  modified:
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_stats.py
    - app/services/maia_flaw_scoring.py
    - app/services/line_material.py
    - app/services/facepalm_inputs.py
    - scripts/backfill_maia_flaws.py
    - scripts/blunder_check/facepalm_features.py
    - scripts/blunder_check/sample.py
    - scripts/blunder_check/render.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/scripts/test_facepalm_features.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/scripts/test_miss_labels.py
    - tests/services/line_material_fixtures.py
    - tests/services/test_line_material.py
    - tests/services/test_facepalm_inputs.py
  deleted:
    - scripts/blunder_check/quiet_rule_review.py
    - tests/scripts/test_quiet_rule_review.py

key-decisions:
  - "The blunder-check cache version is 6: a version 5 cache still carries the arrays and is refused"
  - "render._loses_material reads the stored material_loss (>= FAIR_LOSS_MIN) instead of the depth-3 slot"
  - "opponent_blunders_with_line_facts renamed to opponent_blunders_with_material_inputs (counted on material_loss IS NOT NULL), per the plan"

requirements-completed: [D-05, D-06]

duration: 12min
completed: 2026-11-22
status: complete
---

# Phase 259 Plan 13: Drop Release Code, Part One Summary

**Every writer now stores the quiet-rule scalars and mate plies only, every script that read the 9-slot arrays or the shipped line rule moved to the quiet facts, and the shipped rule is deleted.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-11-22T12:14:00Z
- **Completed:** 2026-11-22T12:26:00Z
- **Tasks:** 3
- **Files modified:** 17 modified, 2 deleted

## Accomplishments

- Task 1 (tracer): `FACEPALM_COLUMNS` is (maia_reply_spread, line_mate_ply, material_loss, material_missed, best_line_mate_ply); `FacepalmStats` / `null_facepalm_stats` lost the two array keys; `_facepalm_values` computes the quiet facts once and takes the mate plies and the scalars from them; `_material_or_none` is gone. New DB test `test_writers_store_no_material_array`: a seeded game scored in full mode and rewritten by the line pass carries no array key in any mode's rows, stores no array value, and keeps the quiet mate plies and scalars.
- Task 2: the features pull builds from the quiet facts and no longer writes the per-depth material slots or the shipped-rule loss/missed pair (the committed TSVs keep them as history; the fit tool already treats the shipped columns as optional). The blunder-check sample drops the array fields and the `played_3` / `best_3` properties (cache version 6); `render._loses_material` reads `material_loss`. The D-09 review tool and its test are deleted (its committed report is the record).
- Task 3: `line_facts`, `best_line_facts`, `_facts_after_first_move`, `_loss_at_depth`, `_recapture_credit`, `_net_loss` and `_MAX_WALK_PLIES` are deleted; the module docstring describes the quiet rule. The shipped-rule tests are gone, and the best-line, owner-miss and nine-slot tests assert on `quiet_best_line_facts` / `quiet_line_facts` with expected values from the fixtures.

## Task Commits

1. **Task 1: writers store the quiet facts, no arrays** - `fbe6d4344` (refactor)
2. **Task 2: scripts off the arrays and the shipped rule, review tool retired** - `da36a44f0` (refactor)
3. **Task 3: shipped line rule deleted** - `bff487492` (refactor)

## Files Created/Modified

See frontmatter `key-files`. Net diff over the plan: 19 files, +335 / -1396 lines.

## Decisions Made

- `test_miss_labels.py` carried one assertion that the fixtures separate the old rule from the quiet rule (`expected_quiet_loss != expected_loss`); dropped with the field.
- The blunder-check test helper `_blunder(played_3=..., best_3=...)` keeps those two parameters as seeds for `material_loss` / `material_missed` so the many call sites stay unchanged; the record itself holds no per-depth material.
- The mate-ply change in `test_line_mode_picks_up_a_changed_best_line_with_a_new_cutoff`: the fixture game is a quiet Ruy Lopez, so two best lines no longer differ in missed gain; the second best line is now the scholar's mate, which differs in `best_line_mate_ply` and missed.
- `_SHORT_LINE_AFTER_PLY_2` is cut to two plies (the quiet walk settles a loss from three), so the "repair shortened the line" test still changes the stored loss.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] tests/scripts/test_miss_labels.py read the removed `LineFixture.expected_loss`**
- **Found during:** Task 3
- **Issue:** one assertion compared the quiet loss with the shipped loss of fixture 153.
- **Fix:** dropped that assertion; the quiet values stay asserted against `expected_quiet_loss`.
- **Files modified:** tests/scripts/test_miss_labels.py
- **Committed in:** bff487492

**2. [Rule 3 - Blocking] tests/scripts/test_blunder_check_calibration.py read the removed record array fields**
- **Found during:** Task 2
- **Issue:** the `BlunderRecord` constructor in the test helper, the cache round-trip, the proxy-table `punished` check and the older-cache test used `played_material` / `best_material` / `played_3`.
- **Fix:** helper no longer builds the arrays; the cache test asserts the keys are absent and refuses version 5 too; the proxy check reads `material_loss`.
- **Files modified:** tests/scripts/test_blunder_check_calibration.py
- **Committed in:** da36a44f0

**3. [Rule 1 - Bug] REAL-column comparisons in the rewritten tests**
- **Found during:** Task 1
- **Issue:** `material_missed` is a float32 column, so exact equality against the Python float failed (1.3870967626 vs 1.3870967741).
- **Fix:** compare the scalars with `pytest.approx(rel=1e-6)` in the backfill tests.
- **Committed in:** fbe6d4344

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug). **Impact:** test-only, no behavior change.

## Issues Encountered

The `_SEEDED_FACEPALM` stand-in wrote `material_loss` alone and tripped `ck_game_flaws_material_pair` (both or neither); it now seeds `material_missed` too.

## Remaining references to the arrays (for plan 14)

Outside migrations only the model declaration remains: `app/models/game_flaw.py` (lines 51/53 `__table_args__` list, 84-90 CHECK constraints, 220-223 columns), plus two test string literals that assert the arrays are absent (`tests/services/test_maia_flaw_scoring.py`) and `_SHAPE_COLUMNS` in `tests/services/test_facepalm_score.py:537` (model-level shape check; plan 14 removes it with the columns).

## Verification

- `uv run pytest -n auto -q`: 6875 passed, 8 skipped
- `uv run ruff check .`, `uv run ruff format` (no changes), `uv run ty check app/ tests/ scripts/`: clean
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: no breaches
- Acceptance greps: `played_line_material|best_line_material` in app/repositories, app/services, scripts: 0 (non-comment); `grep -wE 'line_facts|best_line_facts'` over app, scripts, tests (non-comment): 0; `_material_or_none`: 0; `_recapture_credit`: 0; `quiet_rule_review.py`: deleted; `played_mat_|best_mat_|loss_shipped` in facepalm_features.py: 0.

## Known Stubs

None.

## Self-Check: PASSED

- Commits fbe6d4344, da36a44f0, bff487492 are ancestors of HEAD.
- Deleted files confirmed absent; `app/services/line_material.py` contains `def quiet_line_facts`; `app/repositories/game_flaws_repository.py` FACEPALM_COLUMNS contains `material_missed`.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-22*
