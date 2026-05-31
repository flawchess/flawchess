---
phase: 101-frontend-major-dependency-upgrades
plan: 01
subsystem: infra
tags: [dependencies, vite, eslint, typescript, recharts, jsdom, lucide-react, frontend-tooling]

# Dependency graph
requires:
  - phase: 100-test-database-isolation
    provides: parallel-safe pytest suite used as the backend half of the per-cluster gate
provides:
  - 11 frontend dependencies advanced to their latest major (lucide-react 1, Vite 8, jsdom 29, eslint 10, TypeScript 6, recharts 3) plus shadcn straggler 4.9.0
  - recharts 3 chart-code migration (chart.tsx types, CartesianGrid yAxisId on all 4 multi-axis charts, zone-band full-bleed fix)
  - six atomically-committed clusters on main, each bisectable to one cluster on a gate failure
affects: [frontend, charts, endgames, openings, build-tooling, ci]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "recharts 3: CartesianGrid must carry a yAxisId matching its primary named YAxis or grid lines silently vanish"
    - "recharts 3: a hidden numeric XAxis needs a (non-existent) dataKey so combineAxisDomain honors an explicit [0,1] domain instead of falling back to category indices"

key-files:
  created: []
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/eslint.config.js
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/src/components/ui/chart.tsx
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
    - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
    - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
    - frontend/src/components/charts/ScoreGapByTimePressureChart.tsx
    - frontend/src/components/charts/ScoreChart.tsx
    - CHANGELOG.md

key-decisions:
  - "D-06: each cluster squash-merged to main as one atomic commit in low→high risk order (lucide→Vite→jsdom→eslint→TS→recharts) so a gate failure bisects to exactly one cluster"
  - "D-03: @types/node held at ^24.12.4 (Node 24 line), not bumped to 25"
  - "D-04: shadcn straggler advanced 4.8.3 → 4.9.0 inside Wave 1"
  - "D-05: react-hooks/set-state-in-effect re-evaluated after eslint 10 — behavior unchanged, blanket 'off' retained"
  - "D-02 escape hatch NOT triggered: typescript-eslint peer-compat with TS6/eslint-10 was clean, no overrides needed"
  - "D-01: recharts 3 gated on human visual UAT before merge; UAT surfaced one regression (zone bands), fixed and re-approved"

patterns-established:
  - "Per-cluster full local gate (backend ruff/ty/pytest + frontend lint/test/build/knip) as the integration-to-main gate for dependency maintenance"
  - "recharts 3 migration pitfalls (CartesianGrid yAxisId, hidden-axis domain) documented inline at each fix site"

requirements-completed: [criterion-1, criterion-2, criterion-3, criterion-4, criterion-5]

# Metrics
duration: ~75min
completed: 2026-05-31
---

# Phase 101: Frontend Major Dependency Upgrades Summary

**Brought 11 majors-behind frontend dependencies to their latest major across six atomically-gated clusters, including a full recharts 2 → 3 chart migration that passed human visual UAT after one regression fix.**

## Performance

- **Duration:** ~75 min (execution + UAT loop)
- **Completed:** 2026-05-31
- **Tasks:** 15 (6 clusters) + 1 UAT-driven fix
- **Files modified:** 12

## Accomplishments
- All 11 target deps on latest major: lucide-react 1.17, Vite 8.0 (+ plugin-react 6), jsdom 29, eslint 10 (+ @eslint/js, globals 17, eslint-plugin-react-refresh 0.5), TypeScript 6.0, recharts 3.8; shadcn straggler 4.9.0. @types/node held at 24.x (D-03).
- recharts 3 migration: chart.tsx recharts-3 types, CartesianGrid yAxisId on all 4 multi-axis charts (Pitfall-1), and a zone-band full-bleed fix found in visual UAT (D-01) and locked with a regression test.
- Six bisectable atomic clusters on main (D-06); full local gate green at the final integration (backend 2198 passed / 16 skipped, frontend 745 passed, build + knip clean, npm audit 0 high).

## Task Commits

Each cluster was committed atomically to `main` in low→high risk order:

1. **W1: lucide-react 1.x + shadcn 4.9.0** - `72a4972d` (chore)
2. **W2: Vite 8 + @vitejs/plugin-react 6** - `641960a4` (chore)
3. **W3: jsdom 29 (@types/node held at 24.x)** - `e1f19a7c` (chore)
4. **W4: eslint 10 + @eslint/js + globals 17 + react-refresh 0.5** - `795a38e3` (chore)
5. **W5: TypeScript 6.0.3** - `55ac5ded` (chore)
6. **W6: recharts 2 → 3 (charts migrated + zone-band full-bleed fix)** - `ab935ac8` (chore, squash of recharts code + the UAT regression fix)

## Files Created/Modified
- `frontend/package.json` / `package-lock.json` - bumped version constraints; recharts 3 pulls the redux ecosystem + es-toolkit transitives (expected, audit clean)
- `frontend/eslint.config.js`, `tsconfig.json`, `tsconfig.app.json` - eslint 10 / TS6 config adjustments (ignoreDeprecations "6.0")
- `frontend/src/components/ui/chart.tsx` - recharts 3 types (TooltipContentProps, DefaultLegendContentProps)
- 4 multi-axis charts - CartesianGrid yAxisId added; ScoreGapByTimePressureChart also got the `dataKey="__bleed__"` full-bleed fix
- `CHANGELOG.md` - Unreleased `### Changed` bullet

## Deviations / Notes
- **Branch model:** per the plan's D-06 design, clusters landed directly on `main` (gated) rather than on a single phase branch; the risky recharts cluster was staged on `gsd/phase-101-c6-recharts` for the blocking visual UAT, then squash-merged to `main` after approval. The vestigial phase branch (planning-only) was not used for implementation.
- **UAT regression:** recharts 3's `combineAxisDomain` broke the hidden-bleed-axis trick the score-gap zone bands relied on (bands colored only the left third). Fixed with `dataKey="__bleed__"` on the hidden axis + a regression-guard test.

## Self-Check: PASSED
- All 11 deps on latest major (or held with documented reason) ✓
- Six atomic bisectable clusters on main ✓
- Full local gate green (backend + frontend) ✓
- recharts 3 visual UAT approved on desktop + mobile (D-01) ✓
- typescript-eslint ↔ TS6/eslint-10 peer-compat clean ✓
