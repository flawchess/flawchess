---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
plan: 02
subsystem: frontend
tags: [endgames, types, zones, bullet-chart]
requires:
  - 81-01 (backend EndgamePerformanceResponse fields)
provides:
  - frontend EndgamePerformanceResponse mirror (D-11)
  - endgameEntryEvalZones module (D-15)
affects:
  - frontend/src/types/endgames.ts
  - frontend/src/lib/endgameEntryEvalZones.ts
tech-stack:
  added: []
  patterns:
    - sibling-module mirror (openingStatsZones.ts → endgameEntryEvalZones.ts)
    - zone-color helper centered on 0 with symmetric neutral band
key-files:
  created:
    - frontend/src/lib/endgameEntryEvalZones.ts
    - frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts
  modified:
    - frontend/src/types/endgames.ts
decisions:
  - "Reuse openingStatsZones.ts structure (same shape, different constants) so Plan 03 reads as familiar territory"
  - "Place ±0.75 neutral band as inclusive on both sides (>= MAX → SUCCESS, <= MIN → DANGER) to match openingStatsZones.evalZoneColor sign convention"
metrics:
  duration_minutes: 3
  completed: 2026-05-09
---

# Phase 81 Plan 02: Frontend Endgame Entry-Eval Types & Zones Summary

Mirrored the 6 new backend `EndgamePerformanceResponse` fields on the TS side and added a sibling `endgameEntryEvalZones.ts` module exporting the ±2.0 pawn axis domain (D-15), the ±0.75 pawn neutral band (Q1/A1 / benchmark v3 §3c), and a zone-color helper consumed by Plan 03's Tile 1.

## What Was Built

- **`frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts`** — 6 RED-then-GREEN unit tests covering constant values and `endgameEntryEvalZoneColor` boundary inclusivity.
- **`frontend/src/lib/endgameEntryEvalZones.ts`** — new module with:
  - `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75`
  - `ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.75`
  - `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0` (D-15)
  - `ENDGAME_ENTRY_EVAL_CENTER = 0`
  - `endgameEntryEvalZoneColor(value: number): string` — returns `ZONE_SUCCESS` at/above +0.75, `ZONE_DANGER` at/below −0.75, `ZONE_NEUTRAL` in between. Imports zone tokens from `@/lib/theme` (no hard-coded colors).
- **`frontend/src/types/endgames.ts`** — `EndgamePerformanceResponse` now mirrors the 6 backend fields:
  - `entry_eval_mean_pawns: number`
  - `entry_eval_n: number`
  - `entry_eval_p_value: number | null`
  - `endgame_score_p_value: number | null`
  - `entry_eval_ci_low_pawns: number | null`
  - `entry_eval_ci_high_pawns: number | null`

  All non-optional in the TS interface (the backend always returns the keys with defaults — Plan 01 Pitfall 7 / Pattern G).

## Tasks & Commits

| Task | Name                                       | Commit   |
| ---- | ------------------------------------------ | -------- |
| 1    | RED zone-color tests                       | a1212b21 |
| 2    | GREEN — endgameEntryEvalZones.ts module    | 87630dae |
| 3    | Mirror EndgamePerformanceResponse fields   | e55acec9 |

## Verification

- `cd frontend && npm test -- --run src/lib/__tests__/endgameEntryEvalZones.test.ts` — 6/6 passed
- `cd frontend && npm test -- --run` — 317/317 passed (full suite, no regressions)
- `cd frontend && npm run lint` — 0 errors
- `cd frontend && npx tsc --noEmit` — 0 errors (strict, `noUncheckedIndexedAccess` enabled)
- `cd frontend && npm run knip` — 0 issues (the test file imports all 4 constants and the helper, so they are referenced even before Plan 03 consumes them in production)

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

Per-task TDD cycle followed:
- Task 1 → `test(81-02)` commit (RED, vitest reports "Cannot find package '@/lib/endgameEntryEvalZones'")
- Task 2 → `feat(81-02)` commit (GREEN, all 6 tests pass)
- Task 3 → `feat(81-02)` commit (interface mirror, full test suite remained green)

## Known Stubs

None. The new exports are consumed by Plan 03 (the section component) per the phase wave plan; knip is satisfied because the test file imports each export.

## Self-Check: PASSED

- `frontend/src/lib/endgameEntryEvalZones.ts` — FOUND
- `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` — FOUND
- `frontend/src/types/endgames.ts` modified — verified by `grep -c entry_eval_mean_pawns` = 1
- Commits `a1212b21`, `87630dae`, `e55acec9` — all on branch
