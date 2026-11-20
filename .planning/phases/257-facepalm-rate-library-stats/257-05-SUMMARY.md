---
phase: 257-facepalm-rate-library-stats
plan: 05
subsystem: api
tags: [facepalm, sqlalchemy, pydantic, library-stats, flaw-comparison]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats (plan 01)
    provides: FACEPALM_STATS_MIN, facepalm_type_expr, typed facepalm seeds
provides:
  - _flaw_comparison_anchor, the one anchor of fetch_flaw_comparison and fetch_facepalm_comparison
  - fetch_facepalm_comparison (six per-game COUNT FILTER columns, score and type scored once per blunder)
  - FacepalmMetric, FACEPALM_METRICS, FacepalmBullet and FlawComparisonTc.facepalm_bullets (backend and TS mirror)
  - makeFacepalmBullet and the makeTcEntry `facepalm` option for plan 06
affects: [257-06, 257-07]

actuals:
  tokens: 33000
  tasks: 1
  commits: 2
plan_head_before: d8386f5b88086698a544e77dd351629866871d23
plan_head_after: 929364ac84e24c1279d27504db788fa649cd795e
commits: 2

tech-stack:
  added: []
  patterns:
    - "Shared anchor subquery helper so two per-game readers return the same (game_id, tc, user_moves) set"
    - "Neutral paired row: FlawBullet shape with has_zone False and zones 0.0, significance computed but colour-free"

key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - tests/services/test_flaw_comparison.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts

key-decisions:
  - "Facepalm rows ride FlawComparisonTc (one cache entry, same gate and TC list); no split endpoint pre-built"
  - "Total column is the count of scored blunders >= FACEPALM_STATS_MIN; type columns add a ftype equality, so total == missed wins + allowed losses holds whenever a scored row has a type (seeded and dev data)"
  - "The inner scan IN list uses select(anchor.game_id).correlate(None) so it stays restricted to the anchor's games"

requirements-completed: [D-01, D-02, D-04, D-06, D-12, D-13]

duration: 40 min
completed: 2026-11-20
---

# Phase 257 Plan 05: Paired facepalm rows per time control Summary

**GET /library/flaw-comparison now returns, per time control, three neutral paired facepalm rows (total, missed wins, allowed losses) per 100 of the user's moves next to the opponents' in the same games, built on a shared anchor and with the score and type evaluated once per blunder.**

## Accomplishments

- `_flaw_comparison_anchor` extracted verbatim from `fetch_flaw_comparison` (no behaviour change); both readers call it, pinned by `test_facepalm_anchor_same_game_set_as_flaw_comparison` (unanalyzed, NULL-bucket and zero-ply games excluded by both).
- `fetch_facepalm_comparison`: `facepalm_scored` subquery (score `s`, type `ftype`, `.offset(0)` fence, inner scan restricted to the anchor's games with `correlate(None)`), outer LEFT OUTER JOIN from the anchor with six COUNT FILTER columns (`player_/opp_facepalm`, `_missed_win`, `_allowed_loss`). Opponent scores appear only as aggregate counts (D-06); no drill or tag-filter reader was touched.
- `FacepalmBullet` has exactly `FlawBullet`'s fields with `has_zone` False and zones 0.0 on both return paths; `_compute_facepalm_bullets` reads `_paired_series`, the single owner of the per-100-user-moves denominator, so `player_rate - opp_rate == delta`. Significance is still computed (D-13). Rows exist also below the gate.
- TS mirror (`FacepalmMetric`, `FacepalmBullet`, `FlawComparisonTc.facepalm_bullets`) and `makeFacepalmBullet` plus the `makeTcEntry` `facepalm` option.

## Task Commits

1. `d33b037db` test(257-05): failing tests for the three paired facepalm rows (RED)
2. `929364ac8` feat(257-05): three paired facepalm rows per time control (GREEN)

## TDD Gate Compliance

- RED: commit `d33b037db`. `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` (reason `target_test_failed`, JUnit) for target `test_facepalm_rows_are_paired_per_100_user_moves`; all 10 `test_facepalm_*` tests failed at test time on the planned missing behavior (`FlawComparisonTc` has no `facepalm_bullets`; `ImportError` for `fetch_facepalm_comparison`, `FACEPALM_METRICS`, `FacepalmBullet`). Semantic assessment: no collection or fixture faults (the new imports are inside the tests, so the 26 existing tests kept running); each failure is the missing feature.
- GREEN: commit `929364ac8`; all 36 tests in the file pass.
- Mutation check: changing the SQL cut from `FACEPALM_STATS_MIN` to 0.5 fails `test_facepalm_cut_is_the_stats_min` and the paired-rows test; restored from a scratch copy.
- No REFACTOR commit.

## Deviations from Plan

None - plan executed as written. The new test file imports `FACEPALM_STATS_MIN`, `SEED_FACEPALM_MARGIN` and `facepalm_fact_columns` at module top (they exist since plan 01); only the not-yet-existing symbols are imported inside the tests.

## Verification

- `uv run pytest tests/services/test_flaw_comparison.py -x`: 36 passed; with the library service, router and both repository test files: 292 passed.
- `uv run ty check app/ tests/ scripts/`, `ruff check .`, `ruff format --check`, `check_function_size.py app/ --fail-over-depth 4` (1667 functions, no breaches): clean.
- Frontend: `npm run lint`, `npm run build`, `npm run knip` clean; `npm test -- --run`: 376 files, 6637 tests passed.
- Acceptance greps: anchor 1, `fetch_facepalm_comparison` 1, `class FacepalmBullet` 1, `facepalm_bullets` in schemas 3 and in the TS types 1, `_compute_facepalm_bullets` 1.

## Dev timing (input for the plan 07 prod EXPLAIN item)

On dev user 28 (about 2,850 analyzed games, 10,699 own and opponent blunders): `fetch_facepalm_comparison` alone is 255 to 355 ms wall (181 ms execution in `EXPLAIN (ANALYZE, BUFFERS)`) next to a 290 to 590 ms `fetch_flaw_comparison`; the whole `get_flaw_comparison` is about 1.07 s warm (3.3 s cold). The plan's research estimate was 50 to 69 ms, so the facepalm read is roughly 4x that on today's dev data. The plan shows a `Subquery Scan on facepalm_scored` with 10,699 rows from one pass, so the fence works and the score is evaluated once per blunder. The 1 s fallback threshold (split endpoint) belongs to the prod measurement in plan 07; this plan did not pre-build one.

## Known Stubs

None.

## Threat Flags

None. T-257-07 (IDOR) is mitigated by `Game.user_id` in the shared anchor, `GameFlaw.user_id` in the inner scan and `test_facepalm_two_user_isolation`; T-257-08: the reader returns counts only and no filter or drill reader changed; T-257-09: single-evaluation fence and anchor-restricted inner scan as planned, prod latency stays a plan 07 manual item.

## Deferred to Later Plans

- Plan 06 renders the rows (card, `GapCell.noVerdict`, `FACEPALM_GAP_META`).
- Plan 07: prod `EXPLAIN (ANALYZE, BUFFERS)` of the new reader and the opponent-side visual read (opponent side is near zero on dev, 30 of 745+ rows for user 28 rapid).

## Self-Check: PASSED

- FOUND: app/repositories/library_repository.py, app/services/library_service.py, app/schemas/library.py, tests/services/test_flaw_comparison.py, frontend/src/types/library.ts, frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
- FOUND commits (ancestors of HEAD): d33b037db, 929364ac8
