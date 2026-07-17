---
phase: 175-board-filter-gem-great-consumption
plan: 04
subsystem: ui
tags: [react, typescript, filters, gem-great, library-tab]

# Dependency graph
requires:
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-01: GET /library/games?has_gem=&has_great= query params + apply_game_filters composition (backend)"
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-03: GemIcon/GreatMoveIcon, MAIA_ACCENT/GREAT_ACCENT glyph primitives (frontend)"
provides:
  - "FlawFilterState.hasGem/.hasGreat booleans + DEFAULT_FLAW_FILTER defaults + isFlawFilterNonDefault gate"
  - "FlawFilterControl 'Best Moves' toggle section (filter-has-gem / filter-has-great pills, Games tab only)"
  - "buildLibraryParams(hasGem, hasGreat) + libraryApi.getGames(has_gem, has_great) param threading"
affects: [175-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two independent boolean filter toggles (not a 3-state cycle) mirroring SeverityFilterButton's pill shape, gated on !showTacticFilter to scope a Games-tab-only filter"
    - "Conditional-inclusion query param threading (has_gem/has_great included only when true) mirroring the existing rated/tactic_orientation pattern"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/hooks/__tests__/useLibrary.test.ts
    - frontend/src/api/__tests__/client.test.ts

key-decisions:
  - "Added MAIA_ACCENT_BG/GREAT_ACCENT_BG to theme.ts (14% alpha, same convention as SEV_*_BG) — the Best Moves pills needed a selected-state background color and none existed yet; per CLAUDE.md theme.ts rule, no hard-coded semantic colors in the component."
  - "The 'Best Moves' section is gated on `!showTacticFilter` (i.e. renders only on the Games tab), the exact inverse of how the existing tactic sections are gated ON to the Flaws tab — reuses the existing prop signal instead of adding a new one, since only GET /library/games accepts has_gem/has_great (Plan 01 scoped the backend param to that one endpoint)."
  - "buildLibraryParams was exported (previously a private helper) so it can be unit-tested directly for the has_gem/has_great conditional-inclusion behavior, matching the file's existing exported-pure-function pattern (libraryGamePollInterval)."
  - "hasGem/hasGreat are threaded into useLibraryGames unconditionally (not gated behind the isFiltering flag that gates severity/tags) — they already default to false and buildLibraryParams omits them when false, so no separate gate is needed; the 'unanalyzed games see 0 results' bug that isFiltering guards against does not apply to a boolean EXISTS predicate."

requirements-completed: [FILT-01]

coverage:
  - id: D1
    description: "FlawFilterState gains hasGem/hasGreat booleans (default false); isFlawFilterNonDefault returns true when either is set, lighting the Games-tab filter-active dot"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawFilterStore.test.ts (hasGem=false/hasGreat=false in DEFAULT_FLAW_FILTER; isFlawFilterNonDefault true for hasGem, true for hasGreat, false when both false)"
        status: pass
    human_judgment: false
  - id: D2
    description: "FlawFilterControl renders two independent 'has gem'/'has great' pill toggles (filter-has-gem/filter-has-great, GemIcon/GreatMoveIcon, aria-pressed/aria-label, text-sm) on the Games tab; hidden on the Flaws tab; toggling one does not affect the other"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx::Best Moves (gem / great toggles, FILT-01 Phase 175) (8 tests: render on Games tab, hidden on Flaws tab, default aria-pressed=false, reflects props, independent onHasGemToggle/onHasGreatToggle firing, aria-label)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GamesTab.tsx wires both desktop (Tags sidebar panel) and mobile (Tags drawer) FlawFilterControl render sites to pendingFlawFilter.hasGem/hasGreat and toggle updaters"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "grep -c FlawFilterControl frontend/src/pages/library/GamesTab.tsx == 4 (2 import/type refs + 2 render sites, both carrying hasGem/hasGreat/onHasGemToggle/onHasGreatToggle props)"
        status: pass
    human_judgment: false
  - id: D4
    description: "has_gem/has_great thread through the existing buildLibraryParams -> libraryApi.getGames path (no parallel fetch path), included in the request only when true, omitted when false"
    requirement: "FILT-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useLibrary.test.ts::buildLibraryParams — has_gem / has_great (6 tests: include-when-true, omit-when-false, both-true, defaults-omitted)"
        status: pass
      - kind: unit
        ref: "frontend/src/api/__tests__/client.test.ts::libraryApi.getGames > has_gem / has_great (5 tests: forwards has_gem, forwards has_great, forwards both, omits when false, omits when undefined)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-16
status: complete
---

# Phase 175 Plan 04: FILT-01 Library Gem/Great Filter UI Summary

**Two independent "has gem" / "has great" pill toggles on the Library Games tab's Tags filter strip (desktop sidebar + mobile drawer), threading `has_gem`/`has_great` through the existing `buildLibraryParams` → `libraryApi.getGames` wiring to the Plan 01 backend query params.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-16T23:10:31+02:00 (immediately following 175-03)
- **Completed:** 2026-07-16T23:19:32+02:00
- **Tasks:** 2
- **Files modified:** 10 (6 source, 4 test)

## Accomplishments
- `FlawFilterState.hasGem`/`.hasGreat` booleans (default `false`) added to `useFlawFilterStore.ts`, with `isFlawFilterNonDefault` extended to light the filter-active dot when either is set.
- `FlawFilterControl.tsx` gains a "Best Moves" pill section — `filter-has-gem` (GemIcon + "Gem") and `filter-has-great` (GreatMoveIcon + "Great") — mirroring `SeverityFilterButton`'s shape exactly: rounded-full pill, colored border/background when selected via `MAIA_ACCENT`/`MAIA_ACCENT_BG` and `GREAT_ACCENT`/`GREAT_ACCENT_BG`, `aria-pressed`, `aria-label`, `text-sm` floor. Rendered only when `!showTacticFilter` (Games tab), the inverse gate of the tactic sections (Flaws tab).
- `MAIA_ACCENT_BG`/`GREAT_ACCENT_BG` added to `theme.ts` — 14% alpha of the existing accent hues, same composite-pill convention as `SEV_*_BG`, since neither pill background existed before this plan.
- `GamesTab.tsx` wires both render sites (desktop Tags sidebar panel + mobile Tags drawer) to `pendingFlawFilter.hasGem`/`hasGreat` and toggle handlers that flip the boolean on the pending (staged) filter draft — committed on Apply, same as every other Tags-panel field.
- `buildLibraryParams` (useLibrary.ts) gains optional `hasGem`/`hasGreat` params, included as `has_gem`/`has_great` only when `true` (mirrors the `rated`/severity conditional-inclusion pattern); exported for direct unit testing. `useLibraryGames` passes `flawFilter.hasGem`/`hasGreat` unconditionally (they already default to `false`, same no-op-when-unset behavior).
- `libraryApi.getGames` (api/client.ts) gains `has_gem?`/`has_great?: boolean` params, serialized into the query string only when truthy — same pattern as `tactic_orientation`'s omit-when-default handling. No new fetch path.

## Task Commits

Each task was committed atomically:

1. **Task 1: FlawFilterState toggles + FlawFilterControl best-move section** - `6f471b87` (feat)
2. **Task 2: Thread has_gem/has_great through buildLibraryParams and the API client** - `8b609e5d` (feat)

## Files Created/Modified
- `frontend/src/hooks/useFlawFilterStore.ts` - `hasGem`/`hasGreat` fields, defaults, `isFlawFilterNonDefault` gate
- `frontend/src/components/filters/FlawFilterControl.tsx` - `BestMoveFilterButton` component + "Best Moves" section, extended props
- `frontend/src/pages/library/GamesTab.tsx` - both render sites wired to `pendingFlawFilter.hasGem`/`hasGreat`
- `frontend/src/lib/theme.ts` - `MAIA_ACCENT_BG`, `GREAT_ACCENT_BG`
- `frontend/src/hooks/useLibrary.ts` - `buildLibraryParams(hasGem, hasGreat)` (exported), `useLibraryGames` threading
- `frontend/src/api/client.ts` - `libraryApi.getGames` `has_gem`/`has_great` param type + conditional serialization
- `frontend/src/hooks/__tests__/useFlawFilterStore.test.ts` - default + non-default coverage
- `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` - Best Moves toggle test suite (8 tests)
- `frontend/src/hooks/__tests__/useLibrary.test.ts` - `buildLibraryParams` has_gem/has_great coverage (6 tests)
- `frontend/src/api/__tests__/client.test.ts` - `libraryApi.getGames` has_gem/has_great coverage (5 tests)

## Decisions Made
- `MAIA_ACCENT_BG`/`GREAT_ACCENT_BG` added to `theme.ts` (14% alpha, `SEV_*_BG` convention) — the Best Moves pills needed a selected-state background and none existed; per CLAUDE.md's theme.ts rule, no hard-coded semantic colors in the component itself.
- The "Best Moves" section is gated on `!showTacticFilter` — the exact inverse of how the tactic sections gate ON to the Flaws tab — reusing the existing prop signal rather than adding a new one, since only `GET /library/games` accepts `has_gem`/`has_great` (Plan 01 scoped the backend param to that one endpoint; the Flaws/Stats/Comparison endpoints never got it).
- `buildLibraryParams` was exported (previously module-private) to unit-test the conditional-inclusion behavior directly, matching the file's existing exported-pure-function pattern (`libraryGamePollInterval`).
- `hasGem`/`hasGreat` thread into `useLibraryGames` unconditionally (not gated behind the `isFiltering` flag that gates severity/tags) — they already default to `false` and `buildLibraryParams` omits them when `false`, so no separate gate is needed. The "unanalyzed games see 0 results" bug that `isFiltering` guards against (severity/tags default to blunder+mistake, which the backend's severity EXISTS excludes unanalyzed games from) does not apply to a boolean EXISTS predicate whose default is simply "off."

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FILT-01 is now fully delivered end-to-end: the backend `has_gem`/`has_great` EXISTS filter (Plan 01) has a working UI (this plan) that composes with every other Library filter through the single `buildLibraryParams` → `libraryApi.getGames` path.
- Full frontend suite (2265 tests across 168 files) passes with no regressions; `npx tsc -b`, `npm run lint`, and `npm run knip` are all clean.
- Phase 175's remaining plan (175-05) can proceed independently — this plan's scope (Library filter UI) is self-contained and does not block or depend on board-side consumption work.

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-16*

## Self-Check: PASSED

All 6 source files + 4 test files confirmed present on disk with the expected content; both task commits (`6f471b87`, `8b609e5d`) confirmed in git history.

## Fix (post-verify): Best Moves section never rendered on the real Games tab

**Bug (human verification):** The "Best Moves" (Gem/Great) toggle section never appeared on the actual Library Games tab. Task 1 gated it on `{!showTactics && (...)}`, with comments claiming "Games tab only (showTacticFilter=false)". That discriminator was wrong: **both** library tabs render `FlawFilterControl` with `showTacticFilter=true` (GamesTab.tsx lines ~338/~518 and FlawsTab.tsx lines ~315/~532), so `!showTactics` was false on the real Games tab and the section was hidden. The Task-1 test passed only because it rendered with the default `showTacticFilter=false`, which does not match real usage.

**Root cause of the miss:** I invented a "Games tab = !showTacticFilter" discriminator from the PATTERNS note without verifying it against both tabs' actual render calls — `showTacticFilter` is true on both, so it cannot distinguish them.

**Fix:** Gate the section on the presence of the gem/great toggle handlers instead — `{(onHasGemToggle || onHasGreatToggle) && (...)}`. Only GamesTab passes `onHasGemToggle`/`onHasGreatToggle`; FlawsTab passes neither, so the section correctly renders on Games and stays hidden on Flaws, independent of `showTacticFilter`. Corrected the now-wrong `showTacticFilter=false` comments at the render site and the props interface. Added a fix-site comment per CLAUDE.md.

**Tests fixed to match real usage:** the "renders on the Games tab" cases now render with `showTacticFilter=true` PLUS the handlers (mirroring GamesTab); the "hidden on the Flaws tab" case renders with `showTacticFilter=true` but WITHOUT the handlers (mirroring FlawsTab). Proven the section genuinely depends on the handlers by temporarily reverting to the old `!showTactics` gate and confirming the Games-tab cases fail (7 failures), then restoring the correct gate. No gem/great was introduced into FlawsTab.

**Verification:** `npx tsc -b`, `npm run lint`, `npm run knip` all clean; `npm test -- --run` green (2272 tests across 168 files).

**Fix commit:** `666c8265` (fix).
