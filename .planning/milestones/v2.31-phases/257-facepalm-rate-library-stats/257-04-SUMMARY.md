---
phase: 257-facepalm-rate-library-stats
plan: 04
subsystem: api
tags: [facepalm, sqlalchemy, pydantic, react, recharts, library-stats]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats (plan 01)
    provides: FACEPALM_STATS_MIN = 0.7 and typed facepalm seeds
provides:
  - fetch_facepalm_share_counts (per-game scored and facepalm blunder counts of the user's own blunders)
  - FACEPALM_SHARE_MIN_SCORED = 50 and the pooled share on every Flaws Timeline point
  - FlawTrendPoint.facepalm_share / facepalm_in_window / scored_blunders_in_window (backend schema and TS mirror)
  - FacepalmShareChart under the Flaws Timeline for the selected time control
affects: [257-05, 257-06, 257-07]

actuals:
  tokens: 11700
  tasks: 2
  commits: 4
plan_head_before: bcae7c8ea83be10a4f9fde18cb0e9d6f85756e27
plan_head_after: da6b0f2da07ea601358735f6da12a3aa6fbfa7bb
commits: 4

tech-stack:
  added: []
  patterns:
    - "Share rides on the existing /flaw-stats response: one window walk computes the trend and the pooled share, so dates match point for point"
    - "Score expression evaluated once per row in a subquery fenced with .offset(0), aggregated in the outer query"

key-files:
  created:
    - frontend/src/components/library/FacepalmShareChart.tsx
    - frontend/src/components/library/__tests__/FacepalmShareChart.test.tsx
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - tests/services/test_library_service.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/lib/facepalm.ts

key-decisions:
  - "Share floor is 50 scored blunders per window (orchestrator decision 1, research A1), not the 20 announced in CONTEXT; the point stays, only the share is null"
  - "The share is rounded to the nearest whole percent in the chart; D-07's round-down covers the facepalm score, not this pooled share (comment at the rounding site)"
  - "No rolling-mean fallback built: the pooled share was judged stable at the chosen floor"
  - "FlawStatsResponse is unchanged (pinned by test_response_drops_the_unused_aggregates); only FlawTrendPoint grew"

requirements-completed: [D-01, D-03, D-04, D-05, D-07]

duration: 35 min
completed: 2026-11-20
---

# Phase 257 Plan 04: Facepalm share over time Summary

**The Flaws Timeline now carries a pooled facepalm share (facepalm blunders / scored blunders over the same 100-game window, from the user's own `game_flaws` rows), shown in a neutral one-line chart directly below the timeline on identical dates, with a gap where fewer than 50 blunders are scored.**

## Accomplishments

- `fetch_facepalm_share_counts` returns `{game_id: (scored, facepalm)}` over the filtered game set (`_filtered_games_base`), user-scoped on both `game_flaws` and `games`, own blunders only (`player_only_gate`), unscored blunders in neither count, mistakes and opponent blunders in neither. The score is bound once and fenced with `.offset(0)`.
- `_compute_flaw_trend` pools both counts in the existing window walk (sum over sum, never a mean of per-game shares) and emits `facepalm_share`, `facepalm_in_window`, `scored_blunders_in_window`; `_window_share` returns null below `FACEPALM_SHARE_MIN_SCORED`. `fetch_flaw_trend_rows` rows gain `game_id` and a `Game.id` tie-breaker in ORDER BY.
- `FacepalmShareChart`: TreePalm title "Facepalm share of blunders", subtitle naming 70% (from the exported `FACEPALM_HIGH_CUTOFF`), percent axis fitted to the data and clamped to [0, 1], per-week volume bars, inactivity markers, "last N games · rolling window" caption, one `FACEPALM_SHARE_LINE` line with `connectNulls={false}`, tooltip with the share and "N of M scored blunders", text fallback under two plotted shares. No legend or control, so no trackFeature event.
- `FlawTimeline` renders the share chart under `FlawTrendChart` in the same loading and error branches (the error shows once).

## Task Commits

1. `7c6a15533` test(257-04): failing backend tests for the pooled share (RED)
2. `6c216c286` feat(257-04): pooled facepalm share on every Flaws Timeline point (GREEN, backend + TS types + fixture)
3. `b4439350e` test(257-04): frontend tests for the share chart and its placement
4. `da6b0f2da` feat(257-04): Facepalm share chart below the Flaws Timeline

## TDD Gate Compliance

- **Task 1 (backend): RED then GREEN as required.** RED run: 7 `-k facepalm_share` tests failed at test time (3 `TypeError: _compute_flaw_trend() takes 1 positional argument but 2 were given`, 2 `ImportError` for `fetch_facepalm_share_counts`, 1 `ImportError` for `FACEPALM_SHARE_MIN_SCORED`, 1 `AttributeError` on `scored_blunders_in_window`); no collection errors, no fixture crashes. Semantic assessment: each failure is the planned missing behavior (new signature, function, constant, field) rather than a syntax or setup fault. `gsd_run check tdd-red-evidence` was not run (pytest JUnit XML was captured to scratch only), so the machine-validated evidence is absent. GREEN: the same 7 pass, plus `TestFlawStats` and the full library service, router and repository suites (256 tests).
- **Task 2 (frontend): gate deviation.** I drafted `FacepalmShareChart.tsx` and the `FlawTimeline` wiring before writing the tests, and could not honestly produce a RED run afterwards (the shared-checkout rules forbid reverting files). The tests were committed first (`b4439350e`) with the implementation still uncommitted, so the commit order is test then feat, but the tests were never observed failing on a missing component. As a substitute I ran a mutation check: changing `Math.round` to `Math.floor` in the percent rounding made the tooltip test fail, and reverting restored green. The `LibraryStatsSections` same-dates assertions were not mutation-checked.

## Deviations from Plan

None in code scope; plan executed as written. The Task 2 TDD ordering deviation is described above.

## Known Stubs

None.

## Threat Flags

None. T-257-05 (IDOR) is mitigated: `GameFlaw.user_id == user_id` and `Game.user_id == user_id` plus the user's filtered set, with `test_facepalm_share_counts_never_include_another_users_games`. T-257-06 (DoS) is mitigated by the single-evaluation `.offset(0)` fence; the prod latency read stays a plan 07 manual item.

## Verification

- `uv run pytest tests/services/test_library_service.py -k "facepalm_share or TestFlawStats"`: 12 passed; library service, router and repository suites: 256 passed.
- `uv run ty check app/ tests/ scripts/`, `ruff check .`, `ruff format --check`, `check_function_size.py app/ --fail-over-depth 4`: all clean.
- Frontend: `npm run lint`, `npm run build`, `npm run knip` clean; full `npm test`: 376 files, 6637 tests passed.
- Acceptance greps all satisfied (`fetch_facepalm_share_counts`, `.offset(0)`, `FACEPALM_SHARE_MIN_SCORED: int = 50`, `connectNulls={false}`, "nearest" comment, one `<FacepalmShareChart`, exported `FACEPALM_HIGH_CUTOFF`, `FACEPALM_SHARE_LINE`).

## Deferred to phase UAT

- Plan `<human-check>`: with the dev stack running, open Library, Stats tab as dev user 28, switch blitz and rapid, hover the new chart. Expect the chart under the Flaws Timeline on the same dates, a line without large week-to-week jumps, a tooltip with "N of M scored blunders", and the text fallback for a thin time control. Not run here.
- Prod share probe (`temp/facepalm-257/prod_share_probe.sql`) and prod query latency: manual items for plan 07.

## Self-Check: PASSED

Files verified present: `frontend/src/components/library/FacepalmShareChart.tsx`, `frontend/src/components/library/__tests__/FacepalmShareChart.test.tsx`; commits `7c6a15533`, `6c216c286`, `b4439350e`, `da6b0f2da` are ancestors of HEAD.
