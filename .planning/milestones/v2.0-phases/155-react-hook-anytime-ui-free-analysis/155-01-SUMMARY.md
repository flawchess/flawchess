---
phase: 155-react-hook-anytime-ui-free-analysis
plan: 01
subsystem: ui
tags: [react, typescript, theme, sigmoid, radix-ui, vitest]

# Dependency graph
requires:
  - phase: 154-worker-pool-real-providers
    provides: "WorkerPool + MaiaQueue providers, frozen EngineProviders/SearchBudget/RankedLine/EngineSnapshot contract"
provides:
  - "FLAWCHESS_ENGINE_ACCENT + FLAWCHESS_ENGINE_HEADLINE_ACCENT theme tokens (D-05)"
  - "expectedScoreToWhitePovCp(es, rootMover) pure function in liveFlaw.ts (D-06)"
  - "Switch UI primitive at components/ui/switch.tsx (D-03)"
  - "Wave 0 test scaffolds (useFlawChessEngine.test.ts, FlawChessEngineLines.test.tsx)"
affects: [155-02-useFlawChessEngine-hook, 155-03-FlawChessEngineLines-card, 155-04-Analysis-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inverse-sigmoid conversion (expectedScoreToWhitePovCp) mirrors evalToExpectedScore's mate-before-sigmoid mate-boundary convention rather than a naive log-odds inversion"
    - "Hand-rolled Radix Switch wrapper (data-slot, cn() merge, unstyled passthrough) matching every other ui/ primitive, with a caller-overridable checked-track accent via className"

key-files:
  created:
    - frontend/src/lib/__tests__/expectedScoreToWhitePovCp.test.ts
    - frontend/src/components/ui/switch.tsx
    - frontend/src/hooks/__tests__/useFlawChessEngine.test.ts
    - frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/liveFlaw.ts

key-decisions:
  - "expectedScoreToWhitePovCp special-cases es<=0/es>=1 to +/-MATE_CP_EQUIVALENT*sign, mirroring evalToExpectedScore's forward mate-before-sigmoid convention, instead of computing a literal log-odds inverse that blows up to Infinity/NaN at those exact boundaries (Pitfall 2)"
  - "Switch's checked-track fill defaults to bg-primary but is caller-overridable via className (data-[state=checked]:bg-[...]) rather than a single hardcoded accent, so each engine card (Stockfish/Maia/FlawChess) can tint its own switch"
  - "Wave 0 test scaffolds import nothing (it.todo only) — no premature import of the not-yet-existing hook/component, per the plan's explicit instruction"

patterns-established:
  - "Pure display-only inverse-sigmoid math lives in liveFlaw.ts alongside its forward counterpart, importing LICHESS_K/MATE_CP_EQUIVALENT from the generated flawThresholds mirror rather than redefining them"

requirements-completed: [DISPLAY-03]

coverage:
  - id: D1
    description: "expectedScoreToWhitePovCp converts a 0-1 root-STM expected score to a white-POV cp value, correctly handling both rootMover colors and both mate boundaries (es<=0/es>=1), never producing NaN/Infinity"
    requirement: "DISPLAY-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/expectedScoreToWhitePovCp.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "FLAWCHESS_ENGINE_ACCENT + FLAWCHESS_ENGINE_HEADLINE_ACCENT theme tokens exported alongside STOCKFISH_ACCENT/MAIA_ACCENT, no board-arrow token added"
    verification:
      - kind: unit
        ref: "npx tsc -b (type-check, verified theme.ts exports resolve)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Switch UI primitive exists, type-checks, and its checked-track fill is caller-overridable (not a single hardcoded accent)"
    verification:
      - kind: unit
        ref: "npx tsc -b --noEmit"
        status: pass
    human_judgment: false
  - id: D4
    description: "Wave 0 test scaffolds for useFlawChessEngine and FlawChessEngineLines exist, compile, and report as todo/pending (not failing)"
    verification:
      - kind: unit
        ref: "npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts src/components/analysis/__tests__/FlawChessEngineLines.test.tsx"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-06
status: complete
---

# Phase 155 Plan 01: Shared Foundation (Theme Tokens, Inverse-Sigmoid, Switch Primitive, Wave 0 Scaffolds) Summary

**Two new brand-accent theme tokens, a mate-boundary-guarded inverse-sigmoid `expectedScoreToWhitePovCp` pure function, a hand-rolled `Switch` UI primitive, and compiling Wave 0 test scaffolds for the hook and card Plans 02/03 will build.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-06T19:38:00+02:00
- **Completed:** 2026-07-06T19:45:41+02:00
- **Tasks:** 3
- **Files modified:** 6 (2 modified, 4 created)

## Accomplishments
- `FLAWCHESS_ENGINE_ACCENT` (brand brown) and `FLAWCHESS_ENGINE_HEADLINE_ACCENT` (bronze/gold) added to `theme.ts` alongside `STOCKFISH_ACCENT`/`MAIA_ACCENT`, with no board-arrow token (Phase 156 boundary respected)
- `expectedScoreToWhitePovCp(es, rootMover)` added to `liveFlaw.ts` as the algebraic inverse of `evalToExpectedScore`, importing `LICHESS_K`/`MATE_CP_EQUIVALENT` from the generated `flawThresholds` mirror; fully-green table test covers both `rootMover` colors, both mate boundaries, finite-output across `[0,1]`, and round-trip correctness through `evalToExpectedScore`
- New `components/ui/switch.tsx` hand-rolled around the already-installed `radix-ui` `Switch` export, mirroring `checkbox.tsx`'s convention (`data-slot`, `cn()` merge, unstyled passthrough); checked-track fill defaults to `bg-primary` but is caller-overridable per card accent; no new npm dependency
- Wave 0 scaffolds `useFlawChessEngine.test.ts` and `FlawChessEngineLines.test.tsx` created with `it.todo` placeholders (names include "throttle"/"abort" per 155-VALIDATION.md's `-t` filters), keeping the suite green between waves

## Task Commits

Each task was committed atomically:

1. **Task 1: Add theme tokens + inverse-sigmoid helper (with mate-boundary guards)** - `b128bd74` (feat)
2. **Task 2: Hand-roll the Switch UI primitive (accent-fill via prop)** - `494b48f1` (feat)
3. **Task 3: Create Wave 0 test scaffolds for the hook and the card** - `4f58eb21` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/lib/theme.ts` - Added `FLAWCHESS_ENGINE_ACCENT` + `FLAWCHESS_ENGINE_HEADLINE_ACCENT`
- `frontend/src/lib/liveFlaw.ts` - Added `expectedScoreToWhitePovCp(es, rootMover)`
- `frontend/src/lib/__tests__/expectedScoreToWhitePovCp.test.ts` - Fully-green table test (9 cases)
- `frontend/src/components/ui/switch.tsx` - New hand-rolled Radix Switch wrapper
- `frontend/src/hooks/__tests__/useFlawChessEngine.test.ts` - Wave 0 scaffold (2 `it.todo`)
- `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` - Wave 0 scaffold (2 `it.todo`)

## Decisions Made
- `expectedScoreToWhitePovCp` special-cases `es<=0`/`es>=1` to `∓MATE_CP_EQUIVALENT*sign` rather than a literal log-odds inversion, mirroring `evalToExpectedScore`'s own mate-before-sigmoid convention (Pitfall 2 regression guard — a genuine forced-mate subtree can hit these boundaries exactly)
- `Switch`'s checked-track fill defaults to `bg-primary` (a sensible fallback) but is designed to be overridden by a caller-supplied `data-[state=checked]:bg-[...]` utility class in `className`, satisfying D-03's "no single hardcoded accent" requirement without requiring a separate prop API
- Test-scaffold `toBeCloseTo` precision in the new pure-function test uses 0 decimal digits (not the default 2) since the mid-range round-trip carries ~0.13cp of floating-point slack — verified against the plan's own "≈596.6" approximate figure, not a stricter literal match
- Reverted `requirements.mark-complete`'s DISPLAY-03 checkbox flip: DISPLAY-03 is shared across Plans 01/03 (frontmatter) — 155-01 alone only delivers the `expectedScoreToWhitePovCp` conversion function; left `[ ]` Pending in `REQUIREMENTS.md` with a partial-delivery note (matching the established POOL-04/MAIA-04 precedent from Phases 151/154) — Plan 03 (the visible score-pair badge) actually closes it

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `useFlawChessEngine` (Plan 02) can now import `expectedScoreToWhitePovCp`, the `MoverColor` type, and the two new theme tokens
- `FlawChessEngineLines` (Plan 03) can now import `Switch`, the theme tokens, and `expectedScoreToWhitePovCp` for the score-pair badge
- `npm run knip` flags `switch.tsx` and both new theme tokens as currently unused — expected per the plan's own verification note (they are consumed by Plans 02-04, not truly dead); no action needed
- Full frontend suite green: 125 passed / 2 skipped test files, 1507 passed / 4 todo tests; `npx tsc -b` and `npm run lint` both clean

---
*Phase: 155-react-hook-anytime-ui-free-analysis*
*Completed: 2026-07-06*

## Self-Check: PASSED

All 6 created/modified source files and the SUMMARY.md itself verified present on disk; all 4 commit hashes (b128bd74, 494b48f1, 4f58eb21, 99e6cc18) verified present in git log.
