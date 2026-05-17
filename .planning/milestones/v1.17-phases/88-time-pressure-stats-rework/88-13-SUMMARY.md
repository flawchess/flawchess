---
phase: 88-time-pressure-stats-rework
plan: 13
subsystem: ui
tags: [endgame-analytics, time-pressure, frontend-polish, scope-amendment, react, tailwind]

# Dependency graph
requires:
  - phase: 88-time-pressure-stats-rework
    provides: "Plan 88-12 lifted PressureQuintileBullet typing and the per-(TC, quintile) neutral-band registry; this plan reuses both unchanged."
provides:
  - "PRESSURE_DELTA_DOMAIN widened from 0.20 to 0.30 (frontend-only axis change)."
  - "PRESSURE_LABELS qualitative-label map (Q0..Q3) + pressureLabel(quintileIndex) helper inside EndgameTimePressureCard."
  - "Q4 (80-100% clock remaining) filtered from display on every TC card; backend payload unchanged."
  - "Title-popover body rewritten to drop Q0/Q4 framing; describes only the 4 displayed quintiles."
  - "Time Pressure section on Endgames.tsx renders without an outer charcoal wrap; each TC card stands alone."
affects: [88-14-top-zone-stats, 88-15-line-chart-restoration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Display-label helper with type-narrowed Record<0|1|2|3, string> defense-in-depth (parent filter + helper null-guard)."

key-files:
  created: []
  modified:
    - frontend/src/lib/pressureBulletConfig.ts
    - frontend/src/lib/pressureBulletConfig.test.ts
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
    - frontend/src/pages/Endgames.tsx
    - CHANGELOG.md

key-decisions:
  - "Source visible labels from a frontend-only PRESSURE_LABELS map instead of bin.quintile_label so backend stays API-stable while UI carries the qualitative copy."
  - "Filter Q4 at the parent map() level (cheap; 5 entries always); keep PRESSURE_LABELS strictly 0|1|2|3 so the type system rejects accidental Q4 lookups."
  - "Keep the helper (`pressureLabel`) null-guarded even though the parent filter already drops Q4: defense-in-depth and clean type narrowing inside QuintileRow/EmptyBinRow."
  - "Title popover body explicitly mentions the hidden 80-100% bin so the asymmetry is documented in-product, not just in the codebase."

patterns-established:
  - "Frontend-only quintile suppression with backend retaining the full payload (the asymmetry is intentional and lives in the consuming component, not the API)."

requirements-completed: [A-1, A-4, A-5]

# Metrics
duration: ~18min
completed: 2026-05-17
---

# Phase 88-13: Time Pressure Cards Polish (A-1 + A-4 + A-5) Summary

**Frontend-only polish slice on the Phase 88 Time Pressure cards: qualitative labels, hidden 80-100% low-signal tail, widened ±30% score-delta axis, and per-TC charcoal containers replacing the outer section wrap.**

## Performance

- **Duration:** ~18 minutes
- **Started:** 2026-05-17T20:18:00Z
- **Completed:** 2026-05-17T20:30:00Z
- **Tasks:** 1
- **Files modified:** 6

## Accomplishments

- **A-5 axis widening:** `PRESSURE_DELTA_DOMAIN` bumped from `0.20` to `0.30` in `frontend/src/lib/pressureBulletConfig.ts`. The ±0.06 D-02 editorial neutral cap is untouched; only the colored side-zones grow. Consumer (`EndgameTimePressureCard.tsx`) already passed the constant through, so the visual change is a single constant flip.
- **A-4 visible-quintile filter + label remap:** Q4 (80-100% clock remaining) is filtered out of every TC card. A new `PRESSURE_LABELS: Record<0|1|2|3, string>` map + `pressureLabel()` helper drives all four user-facing surfaces (visible row label, popover name, popover explanation, `MiniBulletChart` ariaLabel, EmptyBinRow label). Backend `bin.quintile_label` is no longer displayed but stays on the type for API stability.
- **A-4 title-popover body:** rewritten to describe the four visible quintiles plus an honest note that the 80-100% bin is intentionally hidden as a low-signal tail. The legacy "Q0 = 0-20% ... Q4 = 80-100%" line is gone.
- **A-1 outer-wrap removal:** the `<div className="charcoal-texture rounded-md p-4">` wrap around `<EndgameTimePressureSection>` is gone from `Endgames.tsx`. Each TC card retains its own `charcoal-texture` internally, matching the `EndgameTypeBreakdownSection` convention immediately below it.
- **Tests:** 9 new test cases in `EndgameTimePressureCard.test.tsx` covering Q4-hidden (both n>0 and n=0 paths), the 4 qualitative labels on visible rows, the EmptyBinRow label, the Q0 popover content, and the title popover no longer referencing Q0/Q4. The existing `out-of-range quintile_index` test stays valid (the new filter just shifts where the drop happens; defense-in-depth `pressureLabel(null)` and `getPressureBinBand(null)` still guard the row). `pressureBulletConfig.test.ts` asserts `PRESSURE_DELTA_DOMAIN === 0.30`.
- **CHANGELOG:** bullet appended under `## [Unreleased]` → `### Changed`.

Plan 88-13 lands the frontend-only polish slice locked in `88-CONTEXT.md` §2 (2026-05-17). Plans 88-14 (top-zone stats) and 88-15 (line-chart restoration) follow.

## Task Commits

1. **Task 1: Frontend refinements (A-1 + A-4 + A-5) with tests** — `9ba7c64b` (feat)

## Files Created/Modified

- `frontend/src/lib/pressureBulletConfig.ts` — `PRESSURE_DELTA_DOMAIN` 0.20 → 0.30, JSDoc updated to reflect ±30% rationale and explicit note that the ±0.06 D-02 cap is unchanged.
- `frontend/src/lib/pressureBulletConfig.test.ts` — constant assertion updated to `0.30` with annotated test name.
- `frontend/src/components/charts/EndgameTimePressureCard.tsx` — added `PRESSURE_LABELS` map, `MAX_VISIBLE_QUINTILE_INDEX`, `pressureLabel()` helper, parent-side `filter(bin => bin.quintile_index <= MAX_VISIBLE_QUINTILE_INDEX)`, label-source swap in `QuintileRow` (visible label + popover name + popover explanation + ariaLabel) and `EmptyBinRow`, plus rewritten title-popover body.
- `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` — 9 new test cases under two new `describe` blocks for Plan 88-13 A-4; existing malformed-quintile test rewords its comment to reflect the new parent filter while keeping its assertion intact.
- `frontend/src/pages/Endgames.tsx` — outer `<div className="charcoal-texture rounded-md p-4">` wrap around `<EndgameTimePressureSection>` removed (lines 530-538); inline comment links the change back to Plan 88-13 A-1 and the `EndgameTypeBreakdownSection` convention.
- `CHANGELOG.md` — bullet appended under `## [Unreleased]` → `### Changed` referencing Phase 88-13.

## Decisions Made

- **Helper + filter, both null-guarded.** The parent filter (`quintile_index <= MAX_VISIBLE_QUINTILE_INDEX`) drops Q4 before any row renders. The `pressureLabel()` helper still returns `null` for out-of-range indices and both row components early-return on `null`. Single source of truth on what is displayable; defense-in-depth on what reaches the render path.
- **Typed `PRESSURE_LABELS: Record<0|1|2|3, string>`.** Restricting the index type prevents a future caller from accidentally indexing it with `4` and getting a TypeScript error rather than `undefined`.
- **Title popover acknowledges the hidden 80-100% bin in user-facing copy.** A silent filter is invisible to users; the popover note makes the asymmetry honest in-product, matching the "no precomputed stories" feedback memory.

## Deviations from Plan

None — plan executed exactly as written. The plan's verify command includes a `pytest scripts/gen_endgame_zones_ts.py --check`-style line in `<verify>` but the actual codegen check is invoked via `uv run python scripts/gen_endgame_zones_ts.py --check`; ran the canonical command which reported "OK: frontend/src/generated/endgameZones.ts is up to date." No codegen drift, as expected (this plan does not touch the codegen pipeline).

## Issues Encountered

None — the worktree had no `node_modules` (a fresh worktree), so I ran `npm install` before vitest. This is expected setup, not a deviation.

## Verification Results

- `vitest run --run EndgameTimePressureCard.test.tsx EndgameTimePressureSection.test.tsx pressureBulletConfig.test.ts`: **41 / 41 pass**
- Full frontend suite (`vitest run`): **503 / 503 pass** across 43 files (test count grew from 494+ baseline by ~9 new cases on this plan; the rest is unchanged from prior phases).
- `npx tsc --noEmit -p tsconfig.app.json`: **clean** (exit 0).
- `npm run lint`: **clean** (exit 0).
- `npm run knip`: **clean** (exit 0).
- `npm run build`: **clean** (exit 0), production bundle compiles.
- `uv run python scripts/gen_endgame_zones_ts.py --check`: **OK: frontend/src/generated/endgameZones.ts is up to date.**

Plan verification greps:
- `grep -c "PRESSURE_DELTA_DOMAIN = 0.30" src/lib/pressureBulletConfig.ts` → **1**
- `grep -c "High Pressure (0-20%)" src/components/charts/EndgameTimePressureCard.tsx` → **1**
- `grep -c "Very Low Pressure (60-80%)" src/components/charts/EndgameTimePressureCard.tsx` → **1**
- Outer `charcoal-texture rounded-md p-4` wrap around `EndgameTimePressureSection data=` in `Endgames.tsx` → **0** (removed, as required).

## User Setup Required

None — frontend-only constants + labels + outer-wrap removal. No env vars, no schema, no migrations, no benchmark rerun.

## Next Phase Readiness

- Plans 88-14 (top-zone stats) and 88-15 (line-chart restoration) can proceed; their respective scopes are independent of this card-chrome / quintile-filter / axis-width slice.
- The user-approved SC #1 amendment recorded in `88-CONTEXT.md` §2 (2026-05-17) is now partially landed (A-1 + A-4 + A-5). 88-14 will land the top-zone stats slice, 88-15 the line-chart restoration.
- Re-verification of the entire Phase 88 SC bundle should follow after 88-15 ships, not after this plan.

## Self-Check: PASSED

- File `frontend/src/lib/pressureBulletConfig.ts`: FOUND (PRESSURE_DELTA_DOMAIN = 0.30 confirmed via grep).
- File `frontend/src/components/charts/EndgameTimePressureCard.tsx`: FOUND (High Pressure / Very Low Pressure labels confirmed via grep).
- File `frontend/src/pages/Endgames.tsx`: FOUND (no outer charcoal-texture wrap around EndgameTimePressureSection, confirmed via grep -c → 0).
- File `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx`: FOUND, +9 new test cases in two new describe blocks.
- File `frontend/src/lib/pressureBulletConfig.test.ts`: FOUND, asserts 0.30.
- File `CHANGELOG.md`: FOUND, Phase 88-13 bullet under `## [Unreleased]` → `### Changed`.
- Commit `9ba7c64b`: FOUND in `git log --oneline`.

---
*Phase: 88-time-pressure-stats-rework*
*Plan: 13*
*Completed: 2026-05-17*
