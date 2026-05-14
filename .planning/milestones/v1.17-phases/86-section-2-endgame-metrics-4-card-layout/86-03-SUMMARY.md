---
phase: 86
plan: 03
subsystem: frontend
tags: [refactor, scaffolding, endgame-metrics]
requires:
  - 86-02 (backend wave done; not consumed by this plan directly but ensures lib helpers will pair with server skill / opp_skill fields downstream)
provides:
  - frontend/src/lib/endgameMetrics.ts (shared helpers + constants for Phase 86 cards and Phase 87 per-type cards)
  - EndgameOverallConnectorArrows.tsx with 4-testid prop API (reusable for Phase 86 Conv/Parity/Recov + Skill-below-Parity layout)
affects:
  - EndgameOverallPerformanceSection.tsx (Phase 85 call site updated to pass existing testids explicitly; behavior unchanged)
tech-stack:
  patterns:
    - "Lift shared helpers into a dedicated `lib/` module before building the new components that consume them (D-08)"
    - "Parameterize a DOM-measuring component via testid props rather than forking the file (D-09a)"
key-files:
  created:
    - frontend/src/lib/endgameMetrics.ts (132 LOC, 13 named exports)
  modified:
    - frontend/src/components/charts/EndgameOverallConnectorArrows.tsx
    - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
decisions:
  - "`endgameSkill()` from the legacy file (lines 155-165) intentionally NOT lifted — D-04 retires it in favor of server-side `skill` / `opp_skill` produced by Plan 86-02."
  - "Connector-arrows file kept its existing name `EndgameOverallConnectorArrows.tsx` (D-09a planner discretion) — rename would add diff churn for no real value; Phase 86 will import under a local alias if helpful."
metrics:
  completed_date: 2026-05-14
  tasks_completed: 2
  duration_minutes: 5
  test_files_passed: 32
  tests_passed: 375
---

# Phase 86 Plan 03: Frontend Scaffolding (Shared Lib + Generalized Connector Arrows) Summary

Lift Phase 85's private endgame-metrics helpers into a shared `lib/endgameMetrics.ts` module and parameterize `EndgameOverallConnectorArrows` with four testid props so Phase 86's Conv/Parity/Recov + Skill-below-Parity layout can reuse the same geometry as Phase 85's three-card + score-differences layout.

## What Changed

### Task 1: `frontend/src/lib/endgameMetrics.ts` (new, 132 LOC)

Created the shared module with 13 named exports lifted verbatim from `EndgameScoreGapSection.tsx`:

- `MIRROR_BUCKET: Record<MaterialBucket, MaterialBucket>`
- `userRate(row: MaterialRow): number`
- `opponentRate(row: MaterialRow, mirror: MaterialRow | undefined): number | null`
- `formatScorePct(score: number): string`
- `formatDiffPct(userR: number, oppR: number): string`
- `BUCKET_DISPLAY_LABELS`, `BUCKET_DISPLAY_LABELS_WITH_METRIC`
- `NEUTRAL_ZONE_MIN`, `NEUTRAL_ZONE_MAX`, `BULLET_DOMAIN`, `MIN_OPPONENT_BASELINE_GAMES`
- `FIXED_GAUGE_ZONES`, `ENDGAME_SKILL_ZONES` (wrapping the codegen registry values with `colorizeGaugeZones` from theme)

Function bodies and constant values are byte-for-byte identical to the legacy declarations. The module's top docstring references D-08 (lift) and D-12 (the explicit list of helpers to copy) and notes that the legacy composite-skill helper is intentionally not lifted per D-04 (retired in favor of backend `skill` / `opp_skill` fields produced in Plan 86-02).

Legacy file `EndgameScoreGapSection.tsx` is untouched and continues to declare its private copies; deletion is deferred to Plan 86-05.

**Commit:** `5d503341`

### Task 2: Parameterized `ConnectorArrows` (D-09a)

Added a new `ConnectorArrowsProps` interface with four required testid props (`leftCardTestId`, `middleCardTestId`, `rightCardTestId`, `targetTileTestId`) and switched the four `container.querySelector` calls to template-literal selectors driven by those props. Added the testids to the `useEffect` dependency array so layout recomputes if a parent ever changes them. Updated the file-header comment to reflect the dual-call-site role (Phase 85 + Phase 86) per D-09a. Geometry constants, ResizeObserver setup, mobile-bail check, and the JSX rectangle/clip-path construction are all byte-for-byte unchanged.

Updated Phase 85's sole call site in `EndgameOverallPerformanceSection.tsx:251` to pass the existing four testids explicitly: `tile-games-without-endgame`, `tile-at-endgame-entry`, `tile-games-with-endgame`, `endgame-score-differences`. No other line in that file was touched.

**Commit:** `5755d876`

## Verification

- `npx tsc --noEmit` → exit 0
- `npm run lint` → exit 0
- `npm test -- --run EndgameOverallPerformanceSection` → 19 tests passed
- Full frontend test suite (`npm test -- --run`) → 375 tests across 32 files passed
- `grep -c "^export " frontend/src/lib/endgameMetrics.ts` → 13 (matches the required helper count)
- `grep -c "endgameSkill" frontend/src/lib/endgameMetrics.ts` → 0 (D-04 retirement confirmed)
- `grep -c "\[data-testid=\"tile-games-without-endgame\"\]\|\[data-testid=\"tile-at-endgame-entry\"\]\|\[data-testid=\"tile-games-with-endgame\"\]\|\[data-testid=\"endgame-score-differences\"\]" frontend/src/components/charts/EndgameOverallConnectorArrows.tsx` → 0 (no hard-coded selectors remain)

## Deviations from Plan

None — plan executed exactly as written.

## Notes for Downstream Plans

- **Plan 86-04** can `import { … } from '@/lib/endgameMetrics'` for the new Conv/Parity/Recov + Skill cards instead of duplicating the helpers.
- **Plan 86-04 / 86-05** can also import `ConnectorArrows` from `EndgameOverallConnectorArrows` and pass the Phase 86 testids (whatever they will be — e.g. `card-conversion`, `card-parity`, `card-recovery`, `card-endgame-skill`) directly. A local alias at the import site is fine if the file name reads oddly next to a Phase 86 component.
- **Plan 86-05** is the only place where `EndgameScoreGapSection.tsx` gets deleted; until then, the legacy private declarations and the new `lib/endgameMetrics.ts` exports coexist by design.

## Self-Check: PASSED

- frontend/src/lib/endgameMetrics.ts — FOUND
- frontend/src/components/charts/EndgameOverallConnectorArrows.tsx — FOUND (modified)
- frontend/src/components/charts/EndgameOverallPerformanceSection.tsx — FOUND (modified)
- Commit 5d503341 — FOUND in `git log`
- Commit 5755d876 — FOUND in `git log`
