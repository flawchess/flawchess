---
phase: 96-import-readiness-gate
plan: "02"
subsystem: frontend
tags: [readiness-gate, import, endgames, routing, toast]
dependency_graph:
  requires: ["96-01"]
  provides: ["tier1-route-gate", "tier2-endgames-lock", "import-state-machine", "tier2-toast"]
  affects: ["frontend/src/App.tsx", "frontend/src/pages/Endgames.tsx", "frontend/src/pages/Import.tsx"]
tech_stack:
  added: []
  patterns:
    - "useRef fire-once guard for tier2 toast (wasTier2FalseRef)"
    - "Readiness-driven page state machine with in-page CTA"
    - "Whole-page early-return gate after all hooks (D-01/D-02)"
key_files:
  created:
    - "frontend/src/components/EndgamesProcessingState.tsx"
    - "frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx"
    - "frontend/src/pages/__tests__/Import.stateMachine.test.tsx"
  modified:
    - "frontend/src/pages/Endgames.tsx"
    - "frontend/src/pages/Import.tsx"
    - "frontend/src/App.tsx"
decisions:
  - "wasTier2FalseRef placed in AppRoutes (not module scope) so it resets on token change (impersonation/re-login)"
  - "ImportRequiredRoute no longer uses useUserProfile for gating; readiness.tier1 is the sole signal"
  - "Endgames tier2 early-return placed after all hook calls (not at the literal top) to comply with React rules of hooks"
  - "profileHasCompletedImport() function removed from App.tsx; all three nav surfaces use readiness.tier1"
  - "window.location.reload() in Sentry error boundary fallback retained (pre-existing, not readiness logic)"
metrics:
  duration_minutes: 13
  completed_date: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 3
---

# Phase 96 Plan 02: Import Readiness Gate — UI Wiring Summary

Wired the Tier-1 route/nav gate and Tier-2 Endgames lock against the `useReadiness` hook from Plan 01. All three nav surfaces (desktop, mobile bottom bar, drawer) now key off `readiness.tier1` instead of `profileHasCompletedImport()`. The Endgames page renders a whole-page `EndgamesProcessingState` when `!tier2`. The Import page is driven as a readiness state machine with an in-page "Explore Openings" CTA at Tier 1. A fire-once Tier-2 toast fires on `tier2 false->true` transition.

## Tasks

### Task 1: EndgamesProcessingState component + Endgames tier2 gate

**Commit:** `033001a4`

Created `frontend/src/components/EndgamesProcessingState.tsx` with `data-testid="endgames-processing-state"`, `Cpu` icon (`h-8 w-8 text-amber-600 animate-pulse`), heading "Analyzing endgames", Stockfish counter ("Stockfish: {analysedCount} / {totalCount} games" using `Math.max(totalCount - pendingCount, 0)`), and body line. No CTA button.

Wired the gate in `Endgames.tsx`: `useReadiness()` called at the top; early-return rendering `<EndgamesProcessingState>` when `!tier2` placed after all other hook calls (after the render section comment) to comply with React rules of hooks.

Tests in `Endgames.readinessGate.test.tsx`: 4/4 pass.

### Task 2: App.tsx tier1 gate signal swap + fire-once Tier-2 toast

**Commit:** `52d5c79a`

Replaced `profileHasCompletedImport()` with `readiness.tier1` in all three nav surfaces:
- `NavHeader` (desktop nav)
- `MobileBottomBar` (mobile bottom nav)
- `MobileMoreDrawer` (mobile drawer)

`ImportRequiredRoute` now uses `readiness.tier1` and `readiness.isLoading` instead of profile timestamps. The `profileHasCompletedImport()` function and `UserProfile` type import removed (no remaining consumers).

Added `wasTier2FalseRef`-guarded Tier-2 toast in `AppRoutes`:
- Observes `tier2=false` to mark the session as having seen the locked state
- Fires `toast('Endgame analysis complete!', { action: { label: 'Explore Endgames', ... } })` on `false->true` transition
- Suppressed when `location.pathname.startsWith('/endgames')`
- `wasTier2FalseRef` reset on token change (reset in the `restoredForTokenRef` block)

### Task 3: Import page readiness state machine + Explore Openings CTA

**Commit:** `f6c33acd`

Fixed the hot-import `isDone` copy in `ImportProgressBar`: "Imported N games from {platform}" replaced with "Games imported. Openings ready." (Constraint 3 compliance).

Added readiness state machine section in `ImportPage`:
- At Tier 1 (`tier1=true`): shows `<Button variant="default" data-testid="btn-explore-openings">Explore Openings</Button>` + status text
- When `tier1 && !tier2 && pendingCount > 0`: shows "Analyzing endgames ({X} / {Y})" with `toLocaleString()`
- When `tier2=true`: shows "Ready. All analysis complete."

Added `['imports','readiness']` to the polling invalidation set in `ImportProgressBar.useEffect`.

Tests in `Import.stateMachine.test.tsx`: 7/7 pass (2 static source-file assertions + 5 component tests).

## Verification

- `cd frontend && npm run lint` -- clean
- `cd frontend && npx tsc --noEmit` -- zero errors
- `cd frontend && npm test -- --run Endgames.readinessGate` -- 4/4 pass
- `cd frontend && npm test -- --run Import.stateMachine` -- 7/7 pass
- `grep window.location.reload frontend/src/App.tsx` -- only in Sentry error boundary fallback (pre-existing, not readiness logic)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] React rules of hooks: Endgames tier2 gate placement**
- **Found during:** Task 1
- **Issue:** Plan specified "add at the TOP of the page component... then `if (!tier2) return...`", but `EndgamesPage` has many hooks (useLocation, useNavigate, useFilterStore, useEndgameInsights, etc.) called after that point. Putting the early return before them violates React's rules of hooks.
- **Fix:** `useReadiness()` is called first, then all other hooks as before. The `if (!tier2) return` early return is placed in the render section (after the `// ── Render` comment), which is after all hooks have been called.
- **Files modified:** `frontend/src/pages/Endgames.tsx`
- **Commit:** `033001a4`

**2. [Rule 1 - Bug] Static file read in tests: URL vs path**
- **Found during:** Task 3
- **Issue:** `new URL('../Import.tsx', import.meta.url)` produced a non-file-scheme URL in the vitest jsdom environment; `readFileSync` rejected it with "The URL must be of scheme file".
- **Fix:** Used `resolve(__dirname, '../Import.tsx')` to get an absolute path string instead.
- **Files modified:** `frontend/src/pages/__tests__/Import.stateMachine.test.tsx`
- **Commit:** `f6c33acd`

**3. [Rule 1 - Bug] `toBeInTheDocument` not available**
- **Found during:** Task 1
- **Issue:** Project uses `@testing-library/react` but NOT `@testing-library/jest-dom`, so `toBeInTheDocument()` matcher is unavailable.
- **Fix:** Replaced `toBeInTheDocument()` with `toBeTruthy()` (for positive assertions) and `.toBeNull()` (for negative/queryBy assertions). Also wrapped test render with `TooltipProvider` to satisfy Radix UI context requirement when tier2=true renders the full Endgames page.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx`
- **Commit:** `033001a4`

## Known Stubs

None. All new UI elements are fully wired to live data from `useReadiness`.

## Threat Flags

None. This plan only modifies client-side routing/gating logic. No new network endpoints, auth paths, or schema changes. Trust boundary T-96-04 (client-side route gate is UX, not a security boundary) documented in the plan's threat model.

## Self-Check: PASSED

All created files found:
- `frontend/src/components/EndgamesProcessingState.tsx` -- FOUND
- `frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx` -- FOUND
- `frontend/src/pages/__tests__/Import.stateMachine.test.tsx` -- FOUND

All commits present:
- `033001a4` feat(96-02): add EndgamesProcessingState and wire Endgames tier2 gate -- FOUND
- `52d5c79a` feat(96-02): swap App.tsx gate signal to tier1 and add fire-once Tier-2 toast -- FOUND
- `f6c33acd` feat(96-02): drive Import page as readiness state machine with Explore Openings CTA -- FOUND
