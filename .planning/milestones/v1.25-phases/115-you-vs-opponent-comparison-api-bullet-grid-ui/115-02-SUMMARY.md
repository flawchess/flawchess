---
phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui
plan: 02
subsystem: frontend
tags: [react, typescript, vitest, tailwind, tanstack-query, mini-bullet-chart, flaw-comparison]

# Dependency graph
requires:
  - phase: 115-01
    provides: GET /api/library/flaw-comparison endpoint, FlawBullet + FlawComparisonResponse Pydantic schemas
provides:
  - "MiniBulletChart invertColors?: boolean prop (D-08) — ZONE_SUCCESS left / ZONE_DANGER right when true"
  - "FlawBullet + FlawComparisonResponse TS interfaces in frontend/src/types/library.ts"
  - "libraryApi.getFlawComparison in frontend/src/api/client.ts"
  - "useLibraryFlawComparison hook in frontend/src/hooks/useLibrary.ts"
  - "FlawBulletPopover (HelpCircle, per-tag copy, D-15 caveats)"
  - "FlawComparisonGrid (family-grouped 3-col/1-col grid, loading/error/gate/zero-event states)"
  - "FlawStatsPanel surgery: NormToggle + per_game deleted, Band fixed per-100, Zone 3 = FlawComparisonGrid"
  - "FlawTagDistribution.tsx deleted; dead theme.ts exports removed — knip clean"
affects:
  - 115-checkpoint-human-verify

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "invertColors boolean on MiniBulletChart: positiveColor/negativeColor pair derived at render-time; all 6 existing callers unchanged (default false)"
    - "FlawComparisonGrid self-fetches via hook — parent (FlawStatsPanel) zones 1–2 unaffected by zone-3 gate"
    - "Family-grouped grid: FAMILIES const array drives both render order and test assertions (single source)"
    - "Zero-event placeholder: min-h-[56px] row keeps grid stable across filter changes (D-11 no-reflow)"

key-files:
  created:
    - frontend/src/components/popovers/FlawBulletPopover.tsx
    - frontend/src/components/library/FlawComparisonGrid.tsx
    - frontend/src/components/library/__tests__/FlawComparisonGrid.test.tsx
  modified:
    - frontend/src/components/charts/MiniBulletChart.tsx
    - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
    - frontend/src/types/library.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/components/library/FlawStatsPanel.tsx
    - frontend/src/components/library/FlawStatsBand.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/lib/theme.ts
  deleted:
    - frontend/src/components/library/FlawTagDistribution.tsx

key-decisions:
  - "invertColors defaults false — zero changes required for 6 existing MiniBulletChart callers (endgame + openings)"
  - "FlawComparisonGrid self-fetches (not passed data from parent) — zone-3 gate/loading/error is isolated; parent Band + trend stay live regardless of gate"
  - "Dead theme.ts exports (FAM_TEMPO_LOW_CLOCK/HASTY/UNRUSHED/UNMEASURED + PHASE_*) removed alongside FlawTagDistribution deletion — knip CI gate enforces this"
  - "GridBody uses Map<string, FlawBullet> for O(1) tag lookup — FAMILIES const drives both render order and test assertions"

metrics:
  duration: 30min
  completed: 2026-06-11
---

# Phase 115 Plan 02: Frontend Bullet-Grid Comparison UI Summary

**Family-grouped MiniBulletChart comparison grid replacing FlawTagDistribution: invertColors prop, TS types, hook + API client, FlawBulletPopover, FlawComparisonGrid, FlawStatsPanel surgery, knip-clean deletion**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-11T15:58:00Z
- **Completed:** 2026-06-11T16:14:03Z
- **Tasks:** 3 auto + 1 checkpoint
- **Files created:** 3
- **Files modified:** 8
- **Files deleted:** 1

## Accomplishments

- **MiniBulletChart `invertColors` prop (D-08):** `positiveColor`/`negativeColor` pair maps to `ZONE_DANGER`/`ZONE_SUCCESS` when inverted; background zone order also inverts (`left=SUCCESS / right=DANGER`). All 6 existing callers unchanged (default `false`).
- **TS types:** `FlawBullet` + `FlawComparisonResponse` interfaces in `types/library.ts` mirroring backend schema field-for-field (snake_case, nullable delta/CI).
- **API client:** `libraryApi.getFlawComparison` mirrors `getFlawStats` exactly.
- **Hook:** `useLibraryFlawComparison` (queryKey `['library-flaw-comparison', params]`, same LIBRARY_STALE_TIME + refetchOnWindowFocus:false).
- **FlawBulletPopover:** MetricStatPopover shell with HelpCircle trigger; per-tag copy registry for all 15 tags; sign-convention line + tempo/exposure/severity-basis/filter caveats per D-15/FLAWUI-02/03/D-14.
- **FlawComparisonGrid:** self-fetching family-grouped grid (6 families, 3-col desktop / 1-col mobile); loading skeleton / error (LoadError) / below-gate CTA (D-10) / normal states; FlawBulletRow with zero-event placeholder (D-11 — no reflow via `min-h`); invertColors MiniBulletChart; all `data-testid` + ARIA (FLAWUI-06).
- **FlawStatsPanel surgery:** deleted NormToggle + NormalizationMode + `normalization` useState (D-02); added `filters` + `flawFilter` props; Zone 3 now `<FlawComparisonGrid .../>` (self-fetching); FlawTrendChart unchanged (FLAWUI-05).
- **FlawStatsBand:** `normalization` prop removed; hardcoded `per_100_moves` dict + `"/ 100 moves"` suffix (D-02).
- **GlobalStats:** passes `filters={filters}` and `flawFilter={DEFAULT_FLAW_FILTER}` into `<FlawStatsPanel>`.
- **FlawTagDistribution deleted:** `git rm`; dead theme.ts exports removed (`FAM_TEMPO_LOW_CLOCK/HASTY/UNRUSHED/UNMEASURED`, `PHASE_OPENING/MIDDLEGAME/ENDGAME`); knip clean.

## Task Commits

1. **Task 1: MiniBulletChart invertColors + FlawBullet TS types + useLibraryFlawComparison hook** — `ed583176` (feat)
2. **Task 2: FlawBulletPopover + FlawComparisonGrid + grid tests** — `3dab886d` (feat)
3. **Task 3: FlawStatsPanel surgery + GlobalStats wiring + delete FlawTagDistribution** — `263eb73e` (feat)

## Verification Results

- **MiniBulletChart tests:** 39/39 (invertColors GREEN + full regression guard)
- **FlawComparisonGrid tests:** 9/9 (CTA gate, 6 headers, 15 rows, popover ARIA, zero-event placeholder, error copy, loading)
- **Full frontend suite:** 901/901
- **lint:** clean
- **tsc:** clean (zero errors)
- **knip:** clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Dead theme.ts exports caused knip CI failure**
- **Found during:** Task 3 verification (`npm run knip`)
- **Issue:** Deleting `FlawTagDistribution.tsx` left 7 exports in `theme.ts` without any importer: `FAM_TEMPO_LOW_CLOCK`, `FAM_TEMPO_HASTY`, `FAM_TEMPO_UNRUSHED`, `FAM_TEMPO_UNMEASURED`, `PHASE_OPENING`, `PHASE_MIDDLEGAME`, `PHASE_ENDGAME`. Knip would fail CI.
- **Fix:** Removed all 7 dead exports from `theme.ts` with explanatory comment referencing the deletion.
- **Files modified:** `frontend/src/lib/theme.ts`
- **Verification:** `npm run knip` — clean after removal.

---

**Total deviations:** 1 auto-fixed (Rule 2 — knip dead export cleanup)
**Impact on plan:** Minimal — no logic change, only export removal for constants that were only ever used by the deleted component.

## Known Stubs

None — all data flows are wired: `FlawComparisonGrid` self-fetches via `useLibraryFlawComparison` → `libraryApi.getFlawComparison` → `GET /api/library/flaw-comparison`. No mock or placeholder data in production paths.

## Threat Flags

No new security surface introduced. The `FlawComparisonGrid` makes authenticated reads identical in shape to `FlawStatsPanel`; user identity is session JWT (T-115-05 mitigated — no user_id in request). All delta/CI/zone values are rendered as React text children (T-115-06 mitigated — no `dangerouslySetInnerHTML`).

## Next Phase Readiness

- Task 4 is a `checkpoint:human-verify` — user must visually verify the grid in a running dev environment with ≥20 analyzed games (users 28/44 per RESEARCH).
- A2 data-basis pre-check is BLOCKING: user must confirm dev `game_flaws` is on the 2026-06-11 mate-ladder + recalibrated `reversed`/`squandered` threshold basis before trusting visual deltas.

## Self-Check: PASSED

- All 3 created files confirmed on disk
- All 11 modified/deleted files processed
- All 3 task commits confirmed in git history (ed583176, 3dab886d, 263eb73e)
- 901/901 tests passing; lint + tsc + knip clean

---
*Phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui*
*Completed: 2026-06-11*
