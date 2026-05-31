---
status: complete
phase: quick-260519-vf2
plan: "01"
subsystem: endgame-zones
tags: [zones, benchmarks, calibration, codegen]
dependency_graph:
  requires: [reports/benchmarks-diff-2026-05-17-vs-2026-05-19.md]
  provides: [updated zone registry, regenerated TS mirror, hand-written TS band, STATE bookkeeping]
  affects: [app/services/endgame_zones.py, frontend/src/generated/endgameZones.ts, frontend/src/lib/endgameEntryEvalZones.ts, frontend/src/components/charts/EndgameOverallShared.ts]
tech_stack:
  added: []
  patterns: [zone-registry update, codegen drift gate]
key_files:
  modified:
    - app/services/endgame_zones.py
    - frontend/src/generated/endgameZones.ts
    - frontend/src/lib/endgameEntryEvalZones.ts
    - frontend/src/components/charts/EndgameOverallShared.ts
    - tests/services/test_endgame_zones.py
    - tests/services/test_insights_llm.py
    - .planning/STATE.md
decisions:
  - "Task 3 pre-resolved: defer-both (no split-overlay for C, PER_CLASS_SCORE_BULLET_ZONES is shared-config feature)"
  - "WDL bar decision-reversal (item G) confirmed: SHOW_WDL_BAR_IN_TYPE_CARDS remains true, no code change"
metrics:
  duration: ~35 minutes
  completed: "2026-05-19T20:52:00Z"
  tasks_completed: 4
  tasks_total: 5
---

# Phase quick-260519-vf2 Plan 01: benchmarks-diff Net Actionable Worklist Summary

Applied four zone band changes from the game-time-bucketing re-evaluation (benchmarks-diff-2026-05-17-vs-2026-05-19.md), updated TS mirrors, and recorded moot/deferred bookkeeping in STATE.md.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Python zone-registry edits (A/D/E/F) + regenerate TS | ee7010fb | app/services/endgame_zones.py, frontend/src/generated/endgameZones.ts, tests/services/test_endgame_zones.py, tests/services/test_insights_llm.py (partial) |
| 2 | Hand-written EG-entry TS band (A frontend mirror) + SCORE_GAP_DOMAIN (B) | 10f88f8b | frontend/src/lib/endgameEntryEvalZones.ts, frontend/src/components/charts/EndgameOverallShared.ts, frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts |
| 3 | Task 3 checkpoint decision | (pre-resolved, no code) | (defer-both) |
| 4 | Decision-reversal confirmation (G) + close-as-moot bookkeeping | (no code) | .planning/STATE.md (modified, uncommitted) |
| 5 | Full gate sweep + test fixes | d35991f9 | tests/services/test_insights_llm.py |

## Changes Applied

| Item | Description | Before | After |
|------|-------------|--------|-------|
| A | entry_eval_pawns neutral band (Python + TS) | +-0.75 pawns | +-0.60 pawns |
| B | SCORE_GAP_DOMAIN half-axis | 0.20 | 0.22 |
| D | minor_piece recovery band | (0.31, 0.41) | (0.28, 0.38) |
| E | rook achievable_score_gap upper | (-0.05, 0.04) | (-0.05, 0.05) |
| F | queen achievable_score_gap lower | (-0.05, 0.05) | (-0.04, 0.05) |
| G | SHOW_WDL_BAR_IN_TYPE_CARDS | confirmed true | confirmed true (no change) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Zone boundary tests used hardcoded old band values**
- **Found during:** Task 1 verify step (pytest run)
- **Issue:** tests/services/test_endgame_zones.py had assertions for -0.75/+0.75 entry_eval_pawns boundary; tests/services/test_insights_llm.py had assertions for (-0.75 to +0.75) in pawn rendering, (-5 to +4) for rook ASG, (-5 to +5) for queen ASG
- **Fix:** Updated all test assertions to match the new band values exactly. These are correctness updates, not weakened tests.
- **Files modified:** tests/services/test_endgame_zones.py, tests/services/test_insights_llm.py
- **Commits:** ee7010fb (partial), d35991f9

**2. [Rule 2 - Missing] Frontend endgameEntryEvalZones.test.ts had hardcoded old band**
- **Found during:** Task 2 (check before running frontend tests)
- **Issue:** Tests asserted ENDGAME_ENTRY_EVAL_NEUTRAL_{MIN,MAX}_PAWNS == +-0.75 and that the neutral band fills 1/3 of the axis (which changes with band width)
- **Fix:** Updated test to check +-0.60 and simplified the domain test (no longer asserts 1/3 fill ratio since band width changed)
- **Files modified:** frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts
- **Commit:** 10f88f8b

## Task 3 Decision: defer-both (pre-resolved)

Item C (timeline overlay unification) and PER_CLASS_SCORE_BULLET_ZONES were pre-resolved as deferred:
- C: no split overlay exists in EndgameScoreOverTimeChart.tsx (it draws a gap-of-two-series, not a cohort reference band). Implementing [46,56] would be a new feature.
- PER_CLASS_SCORE_BULLET_ZONES: new registry + codegen + shared config rewiring, not a quick-task scope.
Both recorded in STATE.md Deferred Items.

## WDL Bar Confirmation (item G)

`SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true` at frontend/src/lib/endgameMetrics.ts line 95.
`EndgameTypeCard.tsx` line 311 gates MiniWDLBar on it. The 2026-05-17 "drop WDL bar" recommendation was reversed by diff item G. No code change.

## CHANGELOG Note

Zone recalibration is borderline user-facing (gauges paint more accurately). The CHANGELOG.md entry was not added automatically. Decision for the user: add a one-line bullet under `## [Unreleased] ### Changed` such as "Recalibrated endgame zone bands from game-time-bucketed benchmark cohort (entry eval +-0.60, score gap domain 0.22, minor piece recovery, rook/queen score gap)." Or skip it as internal calibration.

## STATE.md Deferred-Items Rows Added (uncommitted)

Four rows added to the v1.17 table:
- `zones-moot`: 3.1.4 ENDGAME_SCORE_ZONES per-ELO deferral -> MOOT
- `zones-moot`: 3.1.5 Achievable Score Gap per-ELO deferral -> MOOT
- `zones-moot`: §3.3.3 5-quintile decision -> RESOLVED to Q0-only
- `zones-defer`: C + PER_CLASS_SCORE_BULLET_ZONES -> deferred to scoped phase

## Gate Results

| Gate | Result |
|------|--------|
| uv run ruff check . | PASS |
| uv run ruff format --check (touched file) | PASS |
| uv run ty check app/ tests/ | PASS |
| uv run pytest -q (1564 passed, 6 skipped) | PASS |
| gen_endgame_zones_ts.py --check (drift gate) | PASS |
| frontend npm run lint | PASS |
| frontend npm run knip | PASS |
| frontend npm test (586 passed, 49 test files) | PASS |
| frontend npm run build | PASS |

## Self-Check: PASSED

- app/services/endgame_zones.py: entry_eval_pawns typical_lower=-0.60, typical_upper=0.60. FOUND.
- frontend/src/lib/endgameEntryEvalZones.ts: ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.60. FOUND.
- frontend/src/components/charts/EndgameOverallShared.ts: SCORE_GAP_DOMAIN = 0.22. FOUND.
- frontend/src/generated/endgameZones.ts: minor_piece recovery [0.28, 0.38]. FOUND.
- frontend/src/generated/endgameZones.ts: rook achievable_score_gap [-0.05, 0.05]. FOUND.
- frontend/src/generated/endgameZones.ts: queen achievable_score_gap [-0.04, 0.05]. FOUND.
- Commits ee7010fb, 10f88f8b, d35991f9: all present in git log.
