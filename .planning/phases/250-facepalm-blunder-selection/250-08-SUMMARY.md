---
phase: 250-facepalm-blunder-selection
plan: 08
subsystem: tooling
tags: [blunder-check, calibration, facepalm-score, spot-check, changelog, pre-merge-gate]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "facepalm columns and score (plans 01, 02, 04, 05), D-12 slot plans and FOREIGN_RATING_BAND (plan 06), backfill modes (plan 07)"
provides:
  - "Calibration report with a Facepalm score section (scored share, NULL reasons, pass shares, quartiles) and fair-share proxies per threshold"
  - "Supply by origin section: own supply per user and foreign supply per pinned-Elo level (+-150, extremes flagged, scaled to the population)"
  - "Spot-check drawn with draw_slot_plan and kind-preserving redraws, printing the five score inputs"
  - "--facepalm-threshold CLI flag; CACHE_VERSION 2"
  - "The 249 findability code and the hazard shape draw removed from the app and scripts"
  - "Green pre-merge gate (parallel and serial) and Phase 250 CHANGELOG bullets"
affects: [250-09, 250-10, 250-11]

actuals:
  tokens: 32943
  tasks: 3
  commits: 3
plan_head_before: 112e498a106ee8c4c153b98c7fc08e9bc816bd84
plan_head_after: 13cc6250960a0624773d2d3112608faaae611223

tech-stack:
  added: []
  patterns:
    - "Report-only helpers (blunder_position_marginals) live in scripts/blunder_check/metrics.py; the app keeps only what the drill itself reads"
    - "A spot-check redraw stays the same kind (herring or blunder) so an unfillable shape cannot skew the D-12 mix"

key-files:
  created: []
  modified:
    - scripts/blunder_check/sample.py
    - scripts/blunder_check/render.py
    - scripts/blunder_check/spot_check.py
    - scripts/blunder_check/oddness.py
    - scripts/blunder_check/metrics.py
    - scripts/blunder_check_calibration.py
    - app/services/blunder_check_rules.py
    - app/services/blunder_check_candidates.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/scripts/test_blunder_check_metrics.py
    - tests/services/test_blunder_check_rules.py
    - tests/services/test_blunder_check_candidates.py
    - CHANGELOG.md

key-decisions:
  - "NULL reasons are checked in a fixed order (no spread, no line, no played prob, line too short) so the four columns sum with the scored share to 100% of the user blunders"
  - "D-03 fair-share proxies are the three drivers of fairness among passers (median played prob, median reply spread, share with mate or >= 2 material points down) plus the owner's label-measured fair share as a named constant, because the records cannot tell a fair position from an unfair one"
  - "Foreign supply also reports distinct games with a qualifying blunder, since a session takes at most one window per game and that is the pool a foreign slot draws from"
  - "hazard_position_weights and HazardWeights were deleted (render no longer reads them); blunder_position_marginals in metrics.py is the marginal of the app's conditional blunder-position weights over the uniform length draw"
  - "GoodMoveOddness.played_rank and the OddnessRow rank-1 shares were removed, so the arrow-oddness section is the probability AUC only"

requirements-completed: [D-03, D-10, D-12, D-13]

coverage:
  - id: D1
    description: "The calibration report renders a Facepalm score section per Elo bucket (scored share, NULL reasons no spread / no line / line too short, pass shares at the grid and the chosen threshold, score quartiles) from records that carry the facepalm fields, and the CLI takes --facepalm-threshold"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestFacepalmScoreSection, TestCliFacepalmReport, TestTracer"
        status: pass
    human_judgment: false
  - id: D2
    description: "Own supply per user and foreign supply per pinned-Elo level within +-FOREIGN_RATING_BAND (inclusive edge), scaled from the sample permille, with the extremes below 800 and from 2400 flagged"
    requirement: "D-10, D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestForeignSupplyByLevel, TestSupplyByOrigin"
        status: pass
    human_judgment: false
  - id: D3
    description: "Window composition text and weights use the D-12 shares and the conditional blunder-position marginals; the spot-check draws with draw_slot_plan (about one third herrings), redraws the same kind, prints the five score inputs and never says 'your move'"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestSpotCheckMix, TestWindowComposition"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_metrics.py#TestBlunderPositionMarginals"
        status: pass
    human_judgment: false
  - id: D4
    description: "Recommended constants show fair-share proxies at several thresholds so the owner can judge precision at FACEPALM_SCORE_MIN"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestRecommendedConstants"
        status: pass
    human_judgment: true
    rationale: "Whether the proxies are enough to judge precision is the owner's call; plan 09 prints them on prod next to the spot-check"
  - id: D5
    description: "The 249 findability code and the hazard shape draw are gone from the app and scripts, old caches are refused, and the full pre-merge gate passes (parallel and serial)"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_rules.py#TestRetiredSelectionCode, tests/scripts/test_blunder_check_calibration.py#TestCacheRoundTrip"
        status: pass
      - kind: other
        ref: "pre-merge gate commands, see Verification"
        status: pass
    human_judgment: false

duration: 37min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 08: Calibration Tooling and Pre-merge Gate Summary

**The Phase 248 calibration report and spot-check now measure the facepalm selection (Facepalm score section with NULL reasons, own and foreign supply per rating level with the extremes flagged, D-12 window draws), the 249 findability code is gone, and the full pre-merge gate is green in parallel and serial.**

## Performance

- **Duration:** 37 min
- **Started:** 2026-11-13T20:53:49Z
- **Completed:** 2026-11-13T21:31Z
- **Tasks:** 3 (1 tracer, 1 auto/tdd, 1 auto)
- **Files modified:** 13 (6 app/scripts source, 6 tests, CHANGELOG)

## Accomplishments

- **Tracer (Task 1):** `BlunderRecord` / `FlawRow` carry `facepalm_score`, `maia_reply_spread`, `line_loss_3`, `line_mate_ply`, `maia_played_prob` and a new `has_line` (the stored line on the `ply + 1` row, read with an outer join, never the line itself). `CACHE_VERSION` is 2, so a pre-250 cache raises "unsupported cache version". `section_facepalm_score` replaces the findability grid: per Elo bucket the scored share, NULL reasons (no spread, no line, line too short, no played prob), pass shares at 0.5 / 0.6 / 0.7 / 0.8 plus the chosen threshold, qualifying share of all user blunders and score quartiles. `--facepalm-threshold` replaces `--refutation-threshold` and `--miss-threshold`.
- **Supply by origin (Task 2):** own supply per user as before (facepalm predicate), plus foreign supply per pinned-Elo level from 600 to 2600 in steps of 200: qualifying blunders, usable ones (in band) and distinct games, scaled by `1000 / sample_permille`, with the levels below 800 and from 2400 labelled as extremes. Window-fit and herring-supply text use `HERRING_SHARE` and the conditional blunder-position marginals; the hazard model's herring share is no longer printed.
- **Spot-check (Task 2):** windows are drawn with `draw_slot_plan` (origin ignored, a sample has none); an unfillable shape is redrawn with `draw_herring_shape` / `draw_blunder_shape` up to `MAX_SHAPE_REDRAWS` times so the herring share stays at one third. A blunder window prints the facepalm score, played prob, reply spread, line loss 3 and mate ply after the refutation / missed move; a regression test asserts "your move" never appears in rendered output.
- **Oddness (Task 2):** probability AUC only; `played_rank` is gone from the Good-move scoring, `GoodMoveOddness` and `OddnessRow`.
- **Retirement (Task 3):** `findable`, `FindabilityInputs`, `_pair_passes`, `REFUTATION_PROB_MIN`, `BEST_PROB_MIN`, `draw_window_shape`, `hazard_position_weights`, `HazardWeights` and the `RANK_BASE` import are deleted from `app/services/blunder_check_rules.py` and the `metrics.py` re-exports. `draw_window_shape` has no reader left (`grep -rn` over app, scripts, tests prints nothing).
- **CHANGELOG:** one `### Changed` bullet (selection, the one-third mix, never shown twice) and one `### Added` bullet (analysis data inputs) under `[Unreleased]`, plain wording, no em-dashes, the score never called a share of players.

## Task Commits

1. **Task 1: tracer, facepalm records sampled, cached and rendered** - `5b51d316b` (feat)
2. **Task 2: supply by origin, D-12 spot-check, probability-only oddness** - `52d731189` (feat)
3. **Task 3: retire the 249 findability code, changelog** - `13cc62509` (refactor)

**Plan metadata:** committed separately (docs: complete plan)

Tracer gate: `human_verify_mode` is `end-of-phase` and the tracer's `<verify>` is automated-only, so it was re-run after the commit (`tests/scripts/test_blunder_check_calibration.py`, 55 passed) and then expanded.

## Verification

Pre-merge gate on `gsd/phase-250-facepalm-blunder-selection` (no merge to `main`):

- `uv run ruff format app/ tests/ scripts/ analysis/`: no diff on a second run. `uv run ruff check . --fix`: clean.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `uv run --project analysis --with ty ty check analysis/`: all checks passed.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: 1514 functions, no breaches.
- `uv run pytest -n auto -x`: **6329 passed, 19 skipped** (130 s).
- Serial `uv run pytest -x -q -p no:xdist` (CI shape): **6329 passed, 19 skipped** (18 min 51 s).
- Frontend: `npm run lint` clean, `npm run build` exit 0, `npm test -- --run` 6246 passed, `npm run knip` exit 0 (two pre-existing configuration hints only).
- The `hasattr` check on the retired 249 names exits 0; acceptance greps: `## Facepalm score` 1 and `## Findability grid` 0 in render.py; `maia_(played_rank|best_|refutation_)` 0 in sample.py and render.py; `maia_played_rank` 0 in oddness.py; `--help` lists `--facepalm-threshold` and not `--refutation-threshold`; `## Supply by origin` 1; `draw_slot_plan` 3 and `draw_window_shape` 0 in spot_check.py; the CHANGELOG grep prints 1.
- **Mutation check:** loosening the foreign band edge from `<=` to `<` fails `TestForeignSupplyByLevel` (the 2450 mover sits exactly 150 from 2600); restored. The `draw_slot_plan` wiring is proven by monkeypatching it to all-herring and all-blunder plans.
- **Dev smoke run** (read-only, `--db dev --sample-permille 1000 --limit-games 600 --oddness-sample 0`, output in the session scratchpad): sampler, cache, report and spot-check (24 windows) all produced. The 600 oldest games have no spread yet on dev, so every blunder reads "no spread" and the foreign table is all zeros; the real numbers are for plan 09 on prod. No "your move" in the spot-check.

## Decisions Made

See `key-decisions` above. One more: the report still prints the pure-miss cap (`MAX_MISS_SHARE`) in the own-supply estimate, labelled "report estimate only", because the plan did not retire it and the app does not cap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Oddness and spot-check answer lines changed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** the plan assigns `oddness.py` and the spot-check answer lines to Task 2, but dropping `maia_played_rank` / the best and refutation pairs from `BlunderRecord` (Task 1) breaks both modules, so Task 1 could not be green without them.
- **Fix:** the rank-free oddness and the score-input answer lines landed in the Task 1 commit; Task 2 added the supply section, the draws and the composition text.
- **Files modified:** scripts/blunder_check/oddness.py, scripts/blunder_check/spot_check.py, scripts/blunder_check/render.py
- **Commit:** 5b51d316b

**2. [Rule 3 - Blocking] One rules-test identity assertion moved to the Task 2 commit**
- **Found during:** Task 2
- **Issue:** `tests/services/test_blunder_check_rules.py` asserted `spot_check.draw_window_shape is rules.draw_window_shape`; the spot-check stopped importing the old draw, so the commit would be red.
- **Fix:** the assertion now checks `spot_check.draw_slot_plan is rules.draw_slot_plan`; the rest of that file was cleaned in Task 3.
- **Commit:** 52d731189

**3. [Rule 1 - Bug] `_rows` test helper read every table of a section**
- **Found during:** Task 1 tests
- **Issue:** the helper documented "first table" but parsed every `|` line, which misread sections with two tables once the recommended-constants section gained a second one.
- **Fix:** it now stops at the first non-table line after the table.
- **Commit:** 5b51d316b

### Notes (not deviations)

- `has_line` is the only new sampler field beyond the plan's list; the plan required it ("add a has_line field") in its own action text.
- Added beyond the plan's wording: a "games with a qualifying blunder" column in the foreign table (one window per game per session) and a `TestRetiredSelectionCode` guard test.
- The dev DB has no facepalm values for the sampled games, so the smoke run shows the NULL-reason path only; scored-path numbers are covered by the synthetic-collection tests.

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 test-helper bug). **Impact:** none on scope.

## Issues Encountered

None. A serial pytest run takes about 19 minutes here; the harness moves it to the background after 180 s, and waiting on `pgrep -f` matches the waiting shell itself, so completion was read from the task output instead.

## Known Stubs

None.

## Threat Flags

None. T-250-23 held (`make_readonly_engine` and its statement timeout are untouched, no write statement was added under `scripts/blunder_check`); T-250-24 held (the reports carry game links, ratings and numbers only, a test asserts no user id or email in the rendered spot-check, and no "your move"); T-250-25 mitigated (`CACHE_VERSION` 2, `test_cache_with_the_previous_version_is_refused`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 09 can run `scripts/blunder_check_calibration.py --db prod --facepalm-threshold 0.7` (and the spot-check) over the tunnel once the spread backfill has filled `facepalm_score`; read the Facepalm score section's NULL-reason columns first. Blunders whose stored line is shorter than `LINE_DEPTH` plies keep a NULL score by design (ship-as-fitted, owner decision in plan 04) and show up under "line too short" rather than being hidden.
- Run the calibration only when no backfill is writing (existing docstring rule).

## Self-Check: PASSED

- Modified files present; commits `5b51d316b`, `52d731189` and `13cc62509` are ancestors of HEAD (measured count 3 from the ledger base `112e498a1`).
- Full gate green as listed under Verification.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
