---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 12
subsystem: release
tags: [facepalm-score, refit, constants, blunder-check, deploy]
requires:
  - phase: 254-11
    provides: "Fit report 2026-11-15, owner decision FACEPALM_SCORE_MIN = 0.50 and confirmed forms"
provides:
  - "Refitted FACEPALM_* constants and the cut 0.50 live on prod (constants-only release)"
  - "tests/facepalm_models.py: the frozen Phase 250 model for tests written against the pre-refit score"
  - "fit_facepalm.py selects forms at a fixed threshold (FIT_SELECTION_THRESHOLD = 0.7), independent of the shipped cut"
affects: [254-13, 254-17, 254-14]
tech-stack:
  added: []
  patterns:
    - "Tests about the historic model pin a frozen model constant; tests about behaviour use the shipped FACEPALM_MODEL"
key-files:
  created:
    - tests/facepalm_models.py
  modified:
    - app/services/blunder_check_rules.py
    - scripts/blunder_check/fit_facepalm.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_facepalm_owner_fixtures.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/scripts/test_fit_facepalm.py
    - tests/scripts/test_blunder_check_calibration.py
    - CHANGELOG.md
key-decisions:
  - "Owner fixtures are recorded as a known shortfall: they score 0.146 and 0.154 (0.022 and 0.020 before), above the old model but below the cut; the planned 'at or above the cut' assertion cannot hold with this fit (owner confirmed the forms with these numbers)"
  - "Window 14 is asserted unscored (line too short), not numerically below the cut"
  - "The fit's selection threshold stays 0.7 (the labels' meaning, D-23) while the shipped cut is 0.50; without this the constants check would reproduce a different model"
requirements-completed: [D-01, D-03, D-04, D-05, D-13]
coverage:
  - id: D1
    description: "The shipped constants are the refit of the committed features table"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-15.tsv --check-constants (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Owner fixtures: higher than under the frozen Phase 250 model, below the cut, in the Python twin and through facepalm_expr over seeded rows"
    requirement: "D-13"
    verification:
      - kind: integration
        ref: "tests/services/test_facepalm_owner_fixtures.py"
        status: pass
    human_judgment: true
    rationale: "The plan's goal for these two positions (qualify for the drill) is not met; the owner accepted the fit knowing it"
  - id: D3
    description: "Full pre-merge gate green on the refit branch tip"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -x (6607 passed, 19 skipped); frontend lint, build, test (6346 passed), knip"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live qualifying share on prod matches the calibration estimate at the chosen cut"
    requirement: "D-13"
    verification:
      - kind: integration
        ref: "backfill_maia_flaws.py --db prod --status --mode spread: 929,926 of 1,952,059 scored (47.6%), estimate 47.7%"
        status: pass
    human_judgment: false
duration: 70 min
completed: 2026-11-15
status: complete
commits: 5
actuals:
  tasks: 3
  commits: 5
---

# Phase 254 Plan 12: Ship the refit Summary

**The refitted facepalm constants and the cut 0.50 are live on prod (`76b303eee`); 47.6% of scored user-side blunders now qualify for the drill, as the calibration predicted (47.7%).**

## Tasks 1 and 2 (executor, refit branch)

- Constants pasted from `reports/blunder-check/facepalm-fit-2026-11-15.md`, `FACEPALM_SCORE_MIN = 0.5`, both lambdas 1.0. `--check-constants` exit 0.
- Test changes: frozen `PHASE_250_MODEL` in `tests/facepalm_models.py`; reproduction and legacy constants tests pin it; Window 14 reads the 2026-11-15 features row and asserts no score; owner fixtures as a recorded shortfall (SQL comparison at 1e-6 because two inputs are stored as 4-byte floats); two `test_maia_flaw_scoring.py` tests now expect a score for no-loss rows without a reply spread (spread form `best_prob_for_misses` reads the spread only on rows that lose material); one calibration test fixture adjusted.
- Changelog bullet under `## [Unreleased]` `### Changed`.
- Gate, every command exit 0: `ruff format`, `ruff check . --fix`, `ty check app/ tests/ scripts/`, `ty check analysis/`, `check_function_size.py app/ --fail-over-depth 4`, `pytest -n auto -x` (6607 passed, 19 skipped), frontend `lint`, `build`, `test -- --run` (6346 passed), `knip`.
- Branch commits: `dfb62852a`, `24353d165`, `97e212f73`, `6e5aca2c9`.

Owner fixture scores (`FACEPALM_DRILL_LAMBDA` 1.0): 817357:24 0.021508 to 0.145764; 820181:65 0.020084 to 0.153981.

## Task 3: ship (owner go-ahead: "ship the refit first", "do this autonomously")

- Refit squash on main: `83987f7e2` (branch tree plus one Phase 255 planning commit already on local main). Branch deleted, refit worktree removed.
- Release PR #481, CI green (run 43766172503), squash-merged to production as `76b303eee`. The release diff is the constants, the fit tool default and tests.
- Deployed with `bin/deploy.sh`, finished 2026-11-15T22:02Z, server SHA `76b303ee`, site HTTP 200. Forward-port `ab15fab8c` (run by hand; the script skipped it).
- Live counts with the deployed code: `spread_stamped_games=1041229 spread_pending_games=0 user_blunders_total=2327683 user_blunders_with_spread=2326316 user_blunders_with_score=1952059 user_blunders_qualifying=929926`. Qualifying share 47.6% of scored; before the refit 627,406 at the cut 0.70.
- Smoke (read-only, live expression): the owner fixtures are not on prod, so four set 7 pure misses labelled fair were read: 2952292:85 scores 0.706, 1554612:24 0.723, 1941531:89 0.713 (all qualify, stored column 0.41, 0.18, 0.34); 3264420:25 scores 0.039 (best-move probability 5%). Library and drill lambda give the same value.
- Sentry at 22:05Z: no issue first seen in the previous 2 hours. A check one hour after the deploy is appended below.
- No prod write pass (D-01).

## Deviations from Plan

- **Owner fixtures and Window 14 assertions** changed as described (must-haves 3 and 4 of the plan do not hold with this fit).
- **`fit_facepalm.py` default threshold** changed (script, not app code): needed for the constants check after the cut moved. `scripts/blunder_check/render.py` still defaults its threshold to `FACEPALM_SCORE_MIN`, so reports now print "qualifying" at 0.50.
- **Checkouts:** tasks 1 and 2 ran in `.claude/worktrees/phase-254-refit`, the merge and this SUMMARY in `.claude/worktrees/phase-254-main`; the main checkout is on the Phase 255 branch of another session.
- **Library smoke** by read-only query, not in the browser.

## Issues Encountered

None blocking.

## Known Stubs

None.

## Threat Flags

None new.

## Next Phase Readiness

The stored `facepalm_score` column is stale by design from this release on. Plans 13 and 17 remove its writers and readers on the drop cycle branch; plan 14's one-way drop needs the owner's approval. After Phase 252's prod repair: a gap-fill line pass (D-21) and SEED-261115-agg.

## Self-Check: PASSED

`git show origin/production:app/services/blunder_check_rules.py` has `FACEPALM_SCORE_MIN: float = 0.5`; `origin/production` tree equals `origin/main` tree at the release; `git branch --show-current` prints `main`.
