---
phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
plan: "03"
subsystem: ui
tags: [react, typescript, tanstack-query, tailwind, chess, tactic-explorer, pv-stepper]

requires:
  - phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
    provides: Plan 01 - backend tactic-lines endpoint + TacticLinesResponse Pydantic schema
  - phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
    provides: Plan 02 - useTacticLine hook, ChessBoard id prop, exported BoardArrow

provides:
  - TacticLinesResponse TS type in frontend/src/types/library.ts
  - getTacticLines API client method in frontend/src/api/client.ts
  - useTacticLines TanStack Query hook in frontend/src/hooks/useLibrary.ts
  - SanLadder component (real-ply-anchored clickable SAN move list)
  - TacticLineExplorer component (Dialog desktop / Drawer mobile, toggle, depth readout)
  - TacticLineExplorer test suite (7 tests)
  - PAYOFF_MOVE_ARROW color constant in theme.ts
  - FlawCard D-04 button row (Explore + Game, or Game only for untagged flaws)
  - LibraryGameCard D-03/D-02/D-01 Explore button (disabled+tooltip when not tagged flaw)
  - FlawCard test extensions (34 tests, updated game-btn testid, new D-04 assertions)

affects:
  - FlawCard
  - LibraryGameCard
  - theme.ts color constants
  - useLibrary hooks

tech-stack:
  added: []
  patterns:
    - "Lazy-enabled TanStack Query: useTacticLines passes enabled={open} so the fetch fires only when the explorer opens"
    - "FALLBACK_FEN safety constant for unconditional hook calls (avoids invalid FEN on error state)"
    - "Destructure hook result to avoid eslint-plugin-react-hooks/refs v7 false-positive on containerRef property access in JSX"
    - "Conditional tooltip wrapping for disabled buttons (ternary pattern from EndgameInsightsBlock.MaybeBlockedTooltip)"
    - "Mobile-parity: buttonRow rendered in both sm:hidden and hidden sm:block wrappers so both get the same buttons"

key-files:
  created:
    - frontend/src/components/library/SanLadder.tsx
    - frontend/src/components/library/TacticLineExplorer.tsx
    - frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx
  modified:
    - frontend/src/types/library.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - CHANGELOG.md

key-decisions:
  - "PAYOFF_MOVE_ARROW moved to theme.ts (not defined inline) to satisfy CLAUDE.md zero-hex-in-components rule"
  - "Destructured useTacticLine result to avoid react-hooks/refs v7 lint false-positive on containerRef"
  - "Conditional tooltip pattern (ternary wrap) instead of content={undefined} to avoid empty tooltip on enabled state"
  - "buttonRow rendered in both mobile + desktop wrappers with sm:hidden / hidden sm:block — jsdom ignores CSS so tests use getAllByTestId"

requirements-completed: []

duration: ~90min
completed: 2026-06-25
status: complete
---

# Phase 135 Plan 03: Data Layer + TacticLineExplorer + Entry Points Summary

**Walkable PV stepper (SanLadder + TacticLineExplorer Dialog/Drawer) wired into FlawCard and LibraryGameCard via lazy-fetched useTacticLines TanStack Query hook**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-06-24T~22:00Z
- **Completed:** 2026-06-25T00:10Z
- **Tasks:** 3
- **Files modified:** 8 files + 3 new files

## Accomplishments

- TacticLinesResponse TS type, getTacticLines API client, and useTacticLines lazy hook ship the data layer for the PV stepper
- SanLadder: stateless display component with real-game-ply move-number anchoring, punchline coloring per orientation, and click-to-jump
- TacticLineExplorer: Dialog (desktop ≥768px) / Drawer (mobile <768px), missed/allowed toggle (hidden for single-line flaws), root arrows (best-move blue + flaw-move red), PV arrows (engine blue at lighter alpha for payoff), depth readout in BoardControls infoSlot
- FlawCard D-04: Game+Explore button row (tagged flaws), Game-only (untagged); viewGameButton removed from header
- LibraryGameCard D-03/D-02/D-01: Explore button (always visible, disabled+tooltip when not a tagged flaw at the parked slider ply), TacticLineExplorer stacks over the game modal
- 7/7 TacticLineExplorer tests and 34/34 FlawCard tests pass; 1123/1123 total tests pass; tsc clean; lint clean; knip clean

## Task Commits

1. **Task 1: Data layer** - `70af55dd` (feat)
2. **Task 2: SanLadder + TacticLineExplorer + tests** - `7c14c391` (feat)
3. **Task 3: FlawCard D-04 + LibraryGameCard D-03/D-02/D-01 + test extensions** - `922750b1` (feat)

## Files Created/Modified

- `frontend/src/types/library.ts` - Added TacticLinesResponse interface
- `frontend/src/api/client.ts` - Added getTacticLines API client method
- `frontend/src/hooks/useLibrary.ts` - Added useTacticLines hook (lazy-enabled)
- `frontend/src/lib/theme.ts` - Added PAYOFF_MOVE_ARROW constant
- `frontend/src/components/library/SanLadder.tsx` - NEW: clickable SAN ladder with real-ply move numbers
- `frontend/src/components/library/TacticLineExplorer.tsx` - NEW: Dialog/Drawer explorer with toggle, arrows, depth readout
- `frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx` - NEW: 7 tests
- `frontend/src/components/library/FlawCard.tsx` - D-04 button row (Explore+Game or Game only), TacticLineExplorer render
- `frontend/src/components/library/__tests__/FlawCard.test.tsx` - Updated game-btn testid, D-04 assertions, mocks
- `frontend/src/components/results/LibraryGameCard.tsx` - D-03/D-02/D-01 Explore button + TacticLineExplorer
- `CHANGELOG.md` - Phase 135 Tactic Line Explorer entry under Unreleased

## Decisions Made

- PAYOFF_MOVE_ARROW moved to theme.ts: CLAUDE.md requires zero raw hex/rgba literals in components; this also makes the constant discoverable alongside BEST_MOVE_ARROW
- Destructure useTacticLine result: `eslint-plugin-react-hooks@7.1.1` rule `react-hooks/refs` flags property access like `tacticLine.containerRef` in JSX even when it's not a `.current` access; destructuring at the hook callsite avoids the false-positive
- Conditional tooltip wrapping (ternary): `Tooltip({ content: undefined })` renders an empty tooltip bubble on hover; wrapping with ternary renders the button directly when enabled, Tooltip+span only when disabled
- Mobile-parity via two wrapper divs (`sm:hidden` / `hidden sm:block`) duplicates the button row; all tests use `getAllByTestId` to accommodate the duplicate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] PAYOFF_ARROW_COLOR moved to theme.ts**
- **Found during:** Task 2 acceptance check
- **Issue:** `PAYOFF_ARROW_COLOR = 'rgba(59, 130, 246, 0.5)'` defined locally in TacticLineExplorer.tsx; plan acceptance criterion required `grep -c ... TacticLineExplorer.tsx` to return 0; CLAUDE.md requires all color constants with semantic meaning to live in theme.ts
- **Fix:** Added `PAYOFF_MOVE_ARROW` to theme.ts, removed local constant, updated import
- **Files modified:** frontend/src/lib/theme.ts, frontend/src/components/library/TacticLineExplorer.tsx
- **Verification:** grep returns 0; tsc clean; 7/7 tests pass
- **Committed in:** 7c14c391 (Task 2 commit)

**2. [Rule 1 - Bug] Destructured useTacticLine to fix react-hooks/refs lint errors**
- **Found during:** Task 3 lint run
- **Issue:** `eslint-plugin-react-hooks@7.1.1` rule `react-hooks/refs` flagged 11 errors on `tacticLine.containerRef`, `tacticLine.position`, etc. in JSX even though these are not `.current` accesses
- **Fix:** Replaced `const tacticLine = useTacticLine(...)` with full destructure; replaced all `tacticLine.xxx` with bare names
- **Files modified:** frontend/src/components/library/TacticLineExplorer.tsx
- **Verification:** `npm run lint` produces 0 errors (3 warnings in coverage files, pre-existing); tsc clean; 1123/1123 tests pass
- **Committed in:** 922750b1 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 2 color constant location, 1 Rule 1 lint bug)
**Impact on plan:** Both fixes necessary for correctness and code standards. No scope creep.

## Issues Encountered

- **ResizeObserver not defined in jsdom:** ChessBoard uses ResizeObserver; tests failed with `ReferenceError: ResizeObserver is not defined`. Fixed by adding `MockResizeObserver` stub via `vi.stubGlobal` in both TacticLineExplorer.test.tsx and FlawCard.test.tsx.
- **Invalid FEN on error state:** `useTacticLine({ rootFen: '' })` called `new Chess('')` which threw. Fixed with `FALLBACK_FEN` constant (starting position) so the hook always receives a valid FEN string.
- **Game-btn testid collision:** After D-04, `flaw-btn-game` appears twice in jsdom (mobile + desktop wrappers both rendered). Existing tests using `getByTestId` failed with "multiple elements found". Updated to `getAllByTestId(...)[0]!`.

## Known Stubs

None — all data flows are wired. The TacticLineExplorer calls useTacticLines which fetches from the real backend endpoint (Plan 01). No placeholders or hardcoded empty values remain.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The new `GET /library/flaws/{game_id}/{ply}/tactic-lines` endpoint was created in Plan 01; this plan only adds the frontend consumer.

## Next Phase Readiness

Phase 135 is complete: all 3 plans delivered. The tactic line explorer is fully wired end-to-end — backend endpoint (Plan 01), useTacticLine hook + ChessBoard primitives (Plan 02), and the full UI including data layer, SanLadder, TacticLineExplorer, and FlawCard/LibraryGameCard entry points (Plan 03).

---
*Phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se*
*Completed: 2026-06-25*
