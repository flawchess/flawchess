---
phase: quick-261104-hxl
plan: 01
status: complete
subsystem: openings-stats
tags: [opening-insights, frontend, backend, analytics]
requires: []
provides:
  - "CURRENT_FINDINGS_CAP / STALE_FINDINGS_CAP separate caps in opening_insights_service"
  - "Shared PlayedBeforeToggle component"
  - "Per-section collapsed Played before group in OpeningFindings"
affects: [Openings Stats findings, repertoire Played before toggle]
tech-stack:
  added: []
  patterns: ["nullable user override over a derived default for auto-open state (no tracking on mount)"]
key-files:
  created:
    - frontend/src/components/openings/stats/PlayedBeforeToggle.tsx
  modified:
    - app/services/opening_insights_service.py
    - app/schemas/opening_insights.py
    - tests/services/test_opening_insights_service.py
    - frontend/src/types/insights.ts
    - frontend/src/components/openings/stats/RepertoireList.tsx
    - frontend/src/components/openings/stats/OpeningFindings.tsx
    - frontend/src/lib/analytics.ts
    - frontend/src/components/openings/__tests__/OpeningFindings.test.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - CHANGELOG.md
decisions:
  - "Backend caps current and stale opening findings separately (10 each), current group first, Wilson order within each group; partially reverses D-38's no-current-first rule"
  - "Findings 'Played before' group auto-opens via a derived default (autoExpand) with a nullable user override, so it reacts to colour/filter data swaps and never tracks on mount"
metrics:
  duration: ~10min
  completed: 2026-11-04
actuals:
  tokens: 8766
  tasks: 3
  commits: 3
plan_head_before: 7827334e4893852a9c4391b459b82ee519e68b53
plan_head_after: 18de95f600d952b9592e448f725ba08850cbccc4
---

# Quick 261104-hxl Plan 01: Hide stale moves in Opening Findings behind "Played before" Summary

Backend now returns up to 10 current plus up to 10 stale findings per section (separate caps, Wilson order within each group), and Opening Stats shows only current moves in each findings grid with stale ones in a per-section collapsed "Played before (n)" group built on a PlayedBeforeToggle extracted from RepertoireList.

## Tasks

| Task | Name | Commit | Key files |
| ---- | ---- | ------ | --------- |
| 1 | Backend caps current and stale findings separately | 1da2d9f4c | opening_insights_service.py, opening_insights.py, test_opening_insights_service.py, insights.ts |
| 2 | Per-section Played before group via shared toggle | d8871c7d4 | PlayedBeforeToggle.tsx, RepertoireList.tsx, OpeningFindings.tsx, analytics.ts, OpeningFindings.test.tsx |
| 3 | Changelog bullet, StatsTab comment, verification sweep | 18de95f60 | CHANGELOG.md, StatsTab.tsx |

## What changed

- `_partition_section` filters the ranked list into current and stale, slices each to `CURRENT_FINDINGS_CAP` / `STALE_FINDINGS_CAP` (10 each) and returns current then stale. Eval enrichment still runs only on the partition output (now at most 20 per section). Module, `_build_sections`, schema and frontend type comments updated; `FINDINGS_CARD_CAP` is gone from app/ and tests/.
- `OpeningFindings`: `FindingsSubsection` splits on `is_current`; the main grid and its "N more" count only current cards; `PlayedBeforeGroup` renders the stale cards (all of them, no nested "N more") behind the shared toggle, auto-open when the section has no current findings. Empty line reads "Nothing stands out as {Color} in your current repertoire yet." when only stale findings exist. Merged empty block unchanged (fires only when both lists are fully empty).
- New panel target `opening-insights-played-before`, tracked on user expand only.
- `RepertoireList` renders through the shared `PlayedBeforeToggle` with `testId="repertoire-played-before-toggle"`; its tests pass unchanged.

## TDD Gate Compliance

- Task 1 RED: test module failed at collection (new constants not importable) before implementation; GREEN: 54 passed in the service + router suites.
- Task 2 RED: 6 of the new/rewritten OpeningFindings tests failed against HEAD; GREEN: 125 passed across OpeningFindings, RepertoireList and analytics tests.

## Verification

- `uv run pytest tests/services/test_opening_insights_service.py tests/routers/test_insights_openings.py` : 54 passed
- `uv run ruff format` (no changes), `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py --fail-over-depth 4`: clean
- Frontend: `npm run lint`, `npm run build`, openings tests + analytics test (161 passed), `npm run knip` (only pre-existing configuration hints): clean
- Manual dev-server spot check not run (optional in plan).

## Deviations from Plan

None - plan executed exactly as written. Commits landed directly on `main` per the orchestrator's sequential-execution instruction (no `git.allow_default_branch_commits` key in config; direct main commits for quick tasks match project practice).

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: frontend/src/components/openings/stats/PlayedBeforeToggle.tsx
- FOUND: 1da2d9f4c, d8871c7d4, 18de95f60 (ancestors of HEAD on main)
