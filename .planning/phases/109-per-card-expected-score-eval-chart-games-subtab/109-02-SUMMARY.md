---
phase: 109-per-card-expected-score-eval-chart-games-subtab
plan: "02"
subsystem: frontend-types
tags: [theme, types, frontend, eval-chart]
requirements: [LIBG-10]

dependency_graph:
  requires: []
  provides:
    - "EVAL_CHART_AREA_WHITE_AHEAD/BLACK_AHEAD/LINE/MIDLINE/PHASE_LINE in theme.ts"
    - "EvalPoint, FlawMarker (with is_user), PhaseTransitions interfaces in library.ts"
    - "GameFlawCard extended with eval_series/flaw_markers/phase_transitions"
  affects:
    - "frontend/src/components/library/EvalChart.tsx (plan 04 imports these)"
    - "frontend/src/components/results/LibraryGameCard.tsx (plan 04 uses GameFlawCard new fields)"

tech_stack:
  added: []
  patterns:
    - "oklch color constants in theme.ts (same export const pattern as SEV_* block)"
    - "TypeScript interfaces with nullable fields mirroring backend Pydantic models"

key_files:
  modified:
    - path: "frontend/src/lib/theme.ts"
      role: "Five EVAL_CHART_* oklch color constants added after SEV_* block"
    - path: "frontend/src/types/library.ts"
      role: "EvalPoint, FlawMarker, PhaseTransitions interfaces added; GameFlawCard extended with three nullable fields"

decisions:
  - "Added comment block noting Phase 109 / EvalChart.tsx as the consumer of the new constants (discoverability)"
  - "Placed new interfaces between GameFlawCard closing brace and LibraryGamesResponse (forward-reference safe in TypeScript)"

metrics:
  duration: "3m"
  completed: "2026-06-06T23:15:17Z"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 2
---

# Phase 109 Plan 02: Frontend Prerequisites (Theme Constants + TypeScript Types) Summary

**One-liner:** Five `EVAL_CHART_*` oklch constants in `theme.ts` and `EvalPoint`/`FlawMarker` (with `is_user`)/`PhaseTransitions` interfaces + extended `GameFlawCard` in `library.ts`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add EVAL_CHART_* theme constants + extend library.ts types | `777efb70` | `frontend/src/lib/theme.ts`, `frontend/src/types/library.ts` |

## What Was Built

**theme.ts additions** (after the existing `SEV_*` severity-color block):

- `EVAL_CHART_AREA_WHITE_AHEAD = 'oklch(0.70 0 0 / 0.35)'` — light grey fill for White-ahead region
- `EVAL_CHART_AREA_BLACK_AHEAD = 'oklch(0.28 0 0 / 0.45)'` — dark grey fill for Black-ahead region
- `EVAL_CHART_LINE = 'oklch(0.82 0 0)'` — ES line stroke
- `EVAL_CHART_MIDLINE = 'oklch(0.55 0 0)'` — 50% reference dashed line
- `EVAL_CHART_PHASE_LINE = 'oklch(0.55 0 0 / 0.60)'` — vertical phase-transition lines

**library.ts additions:**

Three new exported interfaces added between `GameFlawCard` and `LibraryGamesResponse`:

- `EvalPoint` — per-ply white-perspective ES datapoint (`ply`, `es | null`, `eval_cp | null`, `eval_mate | null`)
- `FlawMarker` — flaw dot data with `is_user: boolean` discriminator for filled (player) vs hollow (opponent) rendering
- `PhaseTransitions` — first ply of middlegame/endgame (`middlegame_ply | null`, `endgame_ply | null`)

`GameFlawCard` extended with three nullable fields (null for unanalyzed games):
- `eval_series: EvalPoint[] | null`
- `flaw_markers: FlawMarker[] | null`
- `phase_transitions: PhaseTransitions | null`

## Verification

- `grep -c "EVAL_CHART_" frontend/src/lib/theme.ts` returns 5
- `EvalPoint`, `FlawMarker`, `PhaseTransitions` interfaces present with correct shapes
- `is_user: boolean` present on `FlawMarker`
- `eval_series` present on `GameFlawCard`
- `npm run lint` clean
- `npx tsc --noEmit` zero errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. These are compile-time declarations only; no runtime data or UI rendering involved in this plan.

## Threat Flags

None. This plan adds compile-time color constants and TypeScript type declarations only; no runtime data flow, no input surface, no trust boundary crossing.

## Self-Check: PASSED

- `frontend/src/lib/theme.ts` modified with 5 EVAL_CHART_* constants: FOUND
- `frontend/src/types/library.ts` modified with 3 new interfaces + GameFlawCard extension: FOUND
- Commit `777efb70` exists: FOUND
