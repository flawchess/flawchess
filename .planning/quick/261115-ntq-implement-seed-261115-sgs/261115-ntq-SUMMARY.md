---
phase: quick-261115-ntq
plan: 01
subsystem: openings
tags: [openings, score-over-time, eval-expected, lateral, recharts]
requirements: [SEED-261115-sgs]
status: complete
key-files:
  created: []
  modified:
    - app/repositories/stats_repository.py
    - app/repositories/openings_repository.py
    - app/services/openings_service.py
    - app/schemas/openings.py
    - tests/test_openings_time_series.py
    - tests/test_openings_repository.py
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/pages/openings/useOpeningRowTimeSeries.ts
    - frontend/src/pages/openings/useRepertoireRows.ts
    - frontend/src/components/openings/stats/RepertoireCard.tsx
    - frontend/src/components/openings/__tests__/RepertoireList.test.tsx
    - frontend/src/components/charts/ScoreChart.tsx
    - frontend/src/components/charts/__tests__/ScoreChart.test.tsx
    - frontend/src/lib/theme.ts
    - CHANGELOG.md
decisions:
  - "OC-1 branch (b): eval series is opt-in (include_expected_score, default false) and fetched on demand per opening when a card's chart opens"
  - "Middlegame-entry eval for the timeline uses a LATERAL first-row lookup over the primary key (owner decision, 2026-11-15)"
commits: 4
plan_head_before: 5826310897a946105527b899a9f158e9c1aa0977
plan_head_after: 2b902944a852b96272264becb5b4721b5fb555b6
actuals:
  tokens: 60000
  tasks: 3
  commits: 4
---

# Quick Task 261115-ntq: Eval-expected score as the primary opening chart line (SEED-261115-sgs)

The per-opening "Score over time" chart now leads with the expected score from the opening eval over a rolling 100-game window, with the actual score as a fainter second line on one axis, a dashed colour-baseline reference line, no typical band, a legend, a tooltip with the eval game count and an info popover explaining the level gap. The eval series is opt-in on POST /openings/time-series and every card's chart fetches it on demand when opened.

## Commits

| Hash | Message |
|---|---|
| 4aca9b93c | feat(261115-ntq): opt-in eval-expected series on the opening time-series endpoint |
| 87d1fe2e2 | feat(261115-ntq): load every repertoire card's score chart on demand with the eval series |
| dd03036ce | feat(261115-ntq): two-line Score over time chart with colour-baseline reference |
| 2b902944a | perf(261115-ntq): LATERAL first-row lookup for the middlegame-entry eval in the timeline |

## What was built

- **Backend:** `middlegame_entry_subquery` (the existing batch selection, extracted unchanged for the avg-eval pillar) and its LATERAL twin `middlegame_entry_lateral` (first phase=1 row by ply per game, over the `(user_id, game_id, ply)` primary key) live next to each other in `stats_repository`. `query_time_series(..., include_mg_entry_eval)` returns 5 columns; with the flag false the two eval columns are literal NULLs and no phase=1 access exists. The service converts each game's middlegame-entry eval to expected score (mate first, then cp, user perspective), averages over the trailing `ROLLING_WINDOW_SIZE = 100` games skipping games without an eval, applies the 10-game floor per line (a point with fewer than 10 eval games carries `expected_score: null`), and emits `eval_game_count` and the colour baseline `expected_score_baseline` (about 0.523 White, 0.477 Black). Shared score verdict fields stay on actual score.
- **Loading:** the table-wide bookmark request is unchanged (flag omitted, same query as before). Every card's chart, bookmark or most-played, sends its own one-opening request with `include_expected_score: true` when opened, through the existing loading and error states. A bookmark row's front-loaded series still feeds its totals, verdict fields, `is_current` and `last_played_at`.
- **Chart:** `ScoreChart` draws the actual line first (grey, alpha, width 1.5) and the expected line on top (blue, width 2); the typical band, its watermark and mask are gone; the dashed reference line is at `expected_score_baseline`; the legend names are "Expected score from opening eval" and "Actual score" with an `InfoPopover` (`${testId}-info`), the title stays "Score over time", copy says eval and never pawns. Theme: `SCORE_OVER_TIME_LINE` renamed to `SCORE_OVER_TIME_EXPECTED_LINE`, plus `SCORE_OVER_TIME_ACTUAL_LINE`.
- **Tests:** `TestEvalExpectedSeries` (first phase=1 row by ply, phase=0 ignored, convert-then-average, black sign flip, mate both colours and mate over cp, eval-less games skipped but kept in the actual score, per-line 10-game floor, window 100, default request skips the join, colour baselines, other user's evals not counted) and `TestMiddlegameEntryParity` (LATERAL and batch selection return identical rows and evals for first-by-ply, out-of-order insertion, mate with cp, mate only, a phase=1 row with no eval, and a game with no phase=1 row; proved by reversing the LATERAL ordering and watching it fail). Frontend tests for the on-demand hook request shape (bookmark and most-played), bookmark-card chart open and error, and the two-line chart, baseline line, legend, popover.

## Measurements (OC-1)

### Planning measurement and decision rule (copied from the plan)

Decision rule: keep front-loading only if, on the heaviest dev user that has bookmarks, adding the eval series to the table-wide bookmark request adds at most 250 ms AND at most 25% to the median service time (median of 4 interleaved warm rounds). Otherwise load the eval series on demand.

| User | Games | Bookmarks | Before (median) | With eval series, sorted join (median) | Added |
|---|---|---|---|---|---|
| 7 (heaviest) | 67,244 | 5 | 1,041 ms / 871 ms | 2,846 ms / 2,183 ms | +1,805 ms (+173%) / +1,312 ms (+151%) |
| 28 | 5,295 | 10 | 1,136 ms | 1,279 ms | +143 ms (+13%) |

Planning EXPLAIN, user 7 bookmark 41 (5,620 games): 433 ms before vs 663 ms with the join (temp 411 blocks); the join reads every phase=1 row of the matched games and external-merge sorts about 209k rows. Verdict at planning: user 7 failed both thresholds, branch (b) on-demand selected. Step 0 re-observation: user 7 is still the heaviest dev user with bookmarks (67,244 games, bookmarks 41, 42, 45, 47, 48); base HEAD 5826310897a946105527b899a9f158e9c1aa0977.

### Post-change numbers (LATERAL, final code)

`temp/261115-ntq/measure_timeline.py`: one warm-up per arm, 4 interleaved rounds, medians. "before" is the base-commit query (3 columns) run through the same service. Two full runs per user; dev timing drifts between runs (user 28 before: 1,468 ms and 1,859 ms), so compare arms within a run.

| User (run) | before | false arm (shipped page-load request) | true arm (LATERAL, all bookmarks, rejected branch a) |
|---|---|---|---|
| 28 (1) | 1,468 ms | 1,533 ms (+4%) | 1,800 ms (+332 ms, +23%) |
| 28 (2) | 1,859 ms | 1,852 ms (0%) | 1,944 ms (+84 ms, +5%) |
| 7 (1), outlier, info only | 1,255 ms | 1,629 ms (+30%, rounds 1,067 to 2,441, noise) | 2,445 ms (+1,190 ms, +95%) |
| 7 (2), outlier, info only | 1,143 ms | 1,143 ms (0%) | 2,003 ms (+860 ms, +75%) |

On-demand single-opening request (`include_expected_score` true, heaviest bookmark), warm medians: user 28 bookmark 94 (1,454 games) 323 ms and 296 ms (flag false 275 and 262 ms); user 7 bookmark 41 (5,620 games) 553 ms and 567 ms (flag false 592 ms). All far below the 1,500 ms halt line.

EXPLAIN (ANALYZE, BUFFERS):
- False arm, both users: no phase reference anywhere in the plan. User 28: 249 ms and 214 ms, `shared hit=104418`; user 7: 80 ms and 95 ms, `shared hit=30364 read=167`.
- True arm with the LATERAL: a `Nested Loop Left Join` with `Index Scan using game_positions_pkey` per game (`Filter: (phase = 1)`, about 0.024 ms per loop over 1,454 loops on user 28; about 0.047 ms over 5,620 loops on user 7). User 28: 248 ms and 239 ms, `shared hit=114819`; user 7: 340 ms and 335 ms, `shared hit=59094 read=15331`, no temp blocks (the sorted join had temp read=411 written=413 and 663 ms for the same bookmark).

Verdict: the LATERAL cut the per-opening eval cost by roughly half (user 7 bookmark 41: 663 ms to about 340 ms of DB time) and removed the sort, but front-loading it still adds about +0.9 s over user 7's five bookmarks and +5% to +23% over user 28's ten (noisy), so the shipped design keeps the eval series opt-in and on demand. The false arm matches the base query within noise (0% to +4% on user 28, 0% on user 7 in the quieter run). No halt condition triggered.

## Deviations from plan

- **LATERAL instead of the sorted join (owner decision, 2026-11-15).** The plan reused the `DISTINCT ON` phase=1 selection (rejecting the LATERAL as a second definition of the middlegame-entry row). The owner accepted the LATERAL: `middlegame_entry_lateral` sits in `stats_repository` next to `middlegame_entry_subquery`, with comments tying them together and `TestMiddlegameEntryParity` asserting both return the same row and eval for the same games (including a game without a phase=1 eval and a mate eval). The LATERAL carries a `user_id` predicate so the primary key serves the lookup; it never changes the picked row since every position of a game has the game owner's user_id. The plan's note that a `user_id` predicate slowed the sorted join does not apply to the LATERAL.
- Front-loading the eval series (flag removed, bookmark cards reading front-loaded data) was considered and reversed the same day; the final design is the plan's on-demand design (Task 2 as written). The intermediate Task 2 revert was never committed (it was applied to the working tree and discarded), so history has no churn.
- Two further unpacking sites in `tests/test_openings_repository.py` (`TestDefaultPlatformExclusion`) needed the 5-column shape in addition to the two the plan named (Rule 3, blocking).
- `scripts/` shell note: a scratch script run from `temp/261115-ntq/` needs `PYTHONPATH=.` and its `*_test.py`-named scratch files were removed because pytest collected them.

## Known Stubs

None.

## Threat Flags

None. `include_expected_score` is a Pydantic bool on an authenticated endpoint; the LATERAL is scoped by `user_id` and by the user-scoped matched game ids (T-ntq-01, tested).

## Pre-merge gate (all run on the final HEAD 2b902944a)

- `uv run ruff format app/ tests/ scripts/ analysis/`: 612 files unchanged. `uv run ruff check . --fix`: passed.
- `uv run ty check app/ tests/ scripts/`: passed. `uv run --project analysis --with ty ty check analysis/`: passed.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: 1542 functions, no breaches.
- `uv run pytest -n auto -x`: 6597 passed, 19 skipped.
- Frontend: `npm run lint` clean; `npm run build` (tsc -b + vite) built; `npm test -- --run` 365 files, 6342 tests passed; `npm run knip` clean (two pre-existing configuration hints only).
- `git status --porcelain frontend/src/generated`: empty. Working tree clean.

## Self-Check: PASSED

All four commits exist on `worktree-agent-abc9e111e2c52601b`; the modified files listed above exist; SUMMARY frontmatter has `status: complete`.
