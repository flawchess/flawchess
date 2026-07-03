---
phase: quick-260703-kyb
plan: 01
subsystem: ui
tags: [react, typescript, analysis-board, move-tree, chess]

requires: []
provides:
  - Multi-line sideline state (pvNodeIds membership set) in useAnalysisBoard
  - deleteSubtree / clearAllSidelines hook ops replacing the clearPvLine singleton
  - Flat sibling-block rendering (VariationTree) with per-line × delete affordance
  - Multi-line tracking (openLines/pendingFlaw) + focused-line overlays in Analysis.tsx
affects: [analysis-board, variation-tree, tactic-lines]

tech-stack:
  added: []
  patterns:
    - "Flat sibling blocks (one indent level) instead of recursive Level-1/Level-2 nesting"
    - "Membership-set (pvNodeIds: Set<NodeId>) instead of a single ordered array for multi-line PV state"
    - "Pure module-scope helper functions called from useMemo to satisfy the React Compiler's memoization-preservation lint on complex control flow"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useAnalysisBoard.ts
    - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
    - frontend/src/pages/Analysis.tsx

key-decisions:
  - "insertPvLine UNIONS grafted ids into pvNodeIds instead of replacing a singleton pvLine array — multiple tactic lines can be open simultaneously"
  - "deleteSubtree(rootId) is the single delete op behind both the free-move × affordance and the tactic chip toggle-off"
  - "buildSiblingBlocks enumerates branch roots via a lowest-id-child rule so sub-forks surface as additional flat blocks, never deeper indentation"
  - "activePvKeys (a `${ply}:${orientation}` string-key Set) replaces the activePvNodeId/activePvOrientation singleton so multiple chips can read 'on' simultaneously"
  - "findFocusedFlaw/buildFocusedPvLine/isNodeInsideSubtree extracted to pure module-scope functions (not inlined useMemo bodies) because the React Compiler's memoization-preservation eslint rule could not analyze the nested for/while/early-return control flow inline"
  - "Reordered task execution ahead of the plan's literal Task 2→3 order (executed VariationTree.tsx before Analysis.tsx) so `tsc -b` stayed green at every commit — Analysis.tsx's prop usage depends on the new VariationTree prop types"

patterns-established:
  - "Sideline lines render unconditionally (not gated on currentNodeId being inside them) — 'always visible' is now a rendering default, not a navigation side effect"

requirements-completed: [QUICK-260703-kyb]

coverage:
  - id: D1
    description: "insertPvLine unions grafted node ids into a pvNodeIds membership set instead of replacing a singleton pvLine array; multiple tactic lines can be open simultaneously"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts#insertPvLine unions ids: two lines off two different forks are both open simultaneously; mainLine unmutated"
        status: pass
    human_judgment: false
  - id: D2
    description: "deleteSubtree(rootId) removes exactly one open line and its descendants, recovers currentNodeId to the fork parent when the board was inside it, and leaves other open lines untouched"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts#deleteSubtree removes exactly one open line and recovers currentNodeId to its fork parent; the other line is untouched"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts#deleteSubtree is a no-op on currentNodeId when the board is NOT inside the deleted subtree"
        status: pass
    human_judgment: false
  - id: D3
    description: "clearAllSidelines() strips every non-mainLine node, empties pvNodeIds, and recovers currentNodeId to the nearest mainLine ancestor — powers Reset"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts#clearAllSidelines strips every non-mainLine node, empties pvNodeIds, and recovers currentNodeId to mainLine"
        status: pass
    human_judgment: false
  - id: D4
    description: "VariationTree renders every open sideline (tactic or free-move) as a flat, always-visible sibling block — one indent level, no recursive nesting — regardless of where currentNodeId is parked"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(7) both variation-pv-section (tactic) and variation-freemove-section render simultaneously, regardless of currentNodeId"
        status: pass
    human_judgment: false
  - id: D5
    description: "Free-move sidelines expose a per-line × delete affordance (btn-delete-line-{rootId}, aria-label 'Delete variation') calling onDeleteLine(rootId); tactic lines render no × (they close via their chip)"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(8) the free-move line exposes btn-delete-line-{rootId} calling onDeleteLine; the tactic line has no ×"
        status: pass
    human_judgment: false
  - id: D6
    description: "Multiple tactic chips read 'active' simultaneously via activePvKeys (a `${ply}:${orientation}` key set) instead of a single node/orientation match"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(12b) two chips can be simultaneously active via activePvKeys (flat siblings)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Analysis.tsx tracks every open line in openLines (keyed by ply:orientation), opens/closes each line independently via handlePvChipClick + deleteSubtree, and Reset clears all sidelines via clearAllSidelines()"
    requirement: "QUICK-260703-kyb"
    verification:
      - kind: unit
        ref: "npx tsc -b (zero errors) + npm test -- --run (1256 passed, includes Analysis.tsx-adjacent suites)"
        status: pass
    human_judgment: false
  - id: D8
    description: "HUMAN-UAT items (a-f): visual/behavioral confirmation of multi-line persistence, independent tactic-chip toggling, ×-delete recovery, and mobile parity — cannot be automated in this environment"
    verification: []
    human_judgment: true
    rationale: "Requires visually driving the live /analysis page in a browser (desktop + mobile viewport) with a real game that has ≥2 flaw chips; no such interactive session was available in this execution context."

duration: ~50min
completed: 2026-07-03
status: complete
---

# Quick 260703-kyb: Persistent flat sidelines in the analysis move list Summary

**Analysis move list now keeps every user-created line (free-move fork or tactic PV) as a flat, always-visible sibling — replacing the singleton `pvLine`/`clearPvLine` model with a `pvNodeIds` membership set, `deleteSubtree`/`clearAllSidelines` hook ops, and a flat sibling-block renderer with per-line × delete.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3 completed
- **Files modified:** 5

## Accomplishments

- `useAnalysisBoard.ts`: `pvLine: NodeId[]` singleton replaced with `pvNodeIds: Set<NodeId>` membership set; `insertPvLine` now UNIONS new ids into the set instead of clobbering. `clearPvLine` split into `deleteSubtree(rootId)` (removes one line + descendants, recovers `currentNodeId` to the fork parent) and `clearAllSidelines()` (strips every non-mainLine node, used by Reset). `nextId` exposed publicly so callers can snapshot a line's root id before grafting. `goForward` now steps into any open sideline via `pvNodeIds` membership, not a `pvLine[0]` special case.
- `VariationTree.tsx`: single-chain Level-1/Level-2 nesting renderer replaced with `buildSiblingBlocks` — a flat sibling-block model (one indent level, secondary sub-forks surface as additional flat blocks via a lowest-id-child rule, never deeper nesting). Desktop renders each block via a `renderSiblingBlock` helper with a branch label + × delete button for free-move blocks; mobile mirrors this via `siblingBlockToChips`, wrapping each block's chips in single parentheses. `FlawChip` reads "active" from an `activePvKeys` string-key set instead of a node/orientation singleton.
- `Analysis.tsx`: singleton `activePvFlaw` replaced with `openLines` (Map keyed by `${ply}:${orientation}`) + a transient `pendingFlaw`. `handlePvChipClick` toggles OFF only the clicked chip's own line and toggles ON a new line without touching any other open line. `focusedFlaw`/`focusedPvLine` (pure helper functions, called from `useMemo`) derive which open line the board is currently "in" and drive the depth-arrow/sideline-coloring overlays that previously read off the singleton state.
- Full frontend gate green at every commit: `npm run lint`, `npx tsc -b`, `npm test -- --run` (1256 tests), `npm run knip`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-line state in useAnalysisBoard.ts** - `c6a90005` (feat)
2. **Task 3: Flat sibling rendering + × affordance in VariationTree.tsx** - `fd3056d4` (feat)
3. **Task 2: Multi-line tracking + focused-line overlays in Analysis.tsx** - `8d5e4090` (feat)

_Note: Tasks 2 and 3 were executed in reverse order relative to the plan's numbering — see Deviations below._

## Files Created/Modified

- `frontend/src/hooks/useAnalysisBoard.ts` - `pvNodeIds` Set replaces `pvLine` array; `deleteSubtree`/`clearAllSidelines` replace `clearPvLine`; `nextId` exposed
- `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` - rewritten to the multi-line contract (union, independent delete, clearAllSidelines, free-move sub-fork)
- `frontend/src/components/analysis/VariationTree.tsx` - flat sibling-block renderer (`buildSiblingBlocks`, `renderSiblingBlock`, `siblingBlockToChips`) with × delete affordance; `activePvKeys` replaces the node/orientation singleton
- `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` - rewritten to a two-sibling fixture (one tactic line, one free-move line off different forks)
- `frontend/src/pages/Analysis.tsx` - `openLines`/`pendingFlaw` multi-line state; `focusedFlaw`/`focusedPvLine`/`isNodeInsideSubtree`/`buildFocusedPvLine` helpers; `activePvKeys`; `onDeleteLine` wired to `deleteSubtree`

## Decisions Made

- **insertPvLine unions, never clobbers:** the grafted PV's node ids are added to the existing `pvNodeIds` set rather than replacing it, so opening a second tactic line leaves the first fully intact — this is the load-bearing fix for the reported bug (creating a new line no longer silently deletes the previous one).
- **deleteSubtree is the single delete primitive:** both the free-move × button and the tactic chip's toggle-off call the same `deleteSubtree(rootId)`, guaranteeing identical recovery behavior (board returns to the fork parent) regardless of which affordance triggered the delete.
- **Flat sibling enumeration via a lowest-id-child rule:** `buildSiblingBlocks` treats a node as a new "branch root" only if its parent is on the main line, OR its parent is off-mainline and it is NOT that parent's lowest-id child. This keeps a line's own continuation as one flat block while still surfacing genuine sub-forks as additional flat siblings — satisfying the "one indent level, no recursive nesting" constraint without losing any branch.
- **React Compiler memoization workaround:** `focusedFlaw`/`focusedPvLine`'s underlying logic (nested for/while loops with early returns) tripped the React Compiler's `react-hooks/preserve-manual-memoization` lint rule when written inline inside `useMemo`. Extracted to pure module-scope functions (`findFocusedFlaw`, `buildFocusedPvLine`, `isNodeInsideSubtree`) called FROM a trivial `useMemo` body — this is a lint-compliance refactor with no behavioral change, verified by re-running `npm run lint` to green.
- **Execution order deviation (Rule 3 — blocking issue):** the plan's Task 2 (Analysis.tsx) references `VariationTree` props (`pvNodeIds`, `activePvKeys`, `onDeleteLine`) that only exist after Task 3 (VariationTree.tsx) is implemented — doing Task 2 first would have left `tsc -b` red mid-plan, violating "do not commit a broken gate." Executed VariationTree.tsx (plan's Task 3) as the second commit and Analysis.tsx (plan's Task 2) as the third, keeping every commit's `tsc -b` green. All three task commits are present with their original plan-task labels in the commit messages; no plan content was skipped or altered.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reordered Task 2 and Task 3 execution to keep `tsc -b` green at every commit**
- **Found during:** Planning the commit sequence before starting Task 2
- **Issue:** Task 2 (Analysis.tsx) passes `pvNodeIds`/`activePvKeys`/`onDeleteLine` props to `VariationTree`, which only gains those prop types in Task 3. Executing in the plan's literal 1→2→3 order would commit Analysis.tsx with `tsc -b` red.
- **Fix:** Executed Task 3 (VariationTree.tsx) before Task 2 (Analysis.tsx); each commit's message identifies which plan-task it corresponds to.
- **Files modified:** No extra files — same file set as planned, different commit order.
- **Verification:** `npx tsc -b` returned zero errors after every commit.
- **Committed in:** `fd3056d4` (VariationTree.tsx, "Task 3"), `8d5e4090` (Analysis.tsx, "Task 2")

**2. [Rule 3 - Blocking] Extracted `findFocusedFlaw`/`buildFocusedPvLine`/`isNodeInsideSubtree` to module scope**
- **Found during:** Task 2 (Analysis.tsx), running `npm run lint`
- **Issue:** The React Compiler's `react-hooks/preserve-manual-memoization` ESLint rule reported "Compilation Skipped: Existing memoization could not be preserved" for the `focusedFlaw` `useMemo`, whose body contained a `for` loop with a nested `while` loop and multiple early returns — a control-flow shape the compiler's static analysis could not verify.
- **Fix:** Moved the logic into pure module-scope functions and reduced the `useMemo` bodies to a single function call each. No behavioral change.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** `npm run lint` returned zero errors (was 2 errors); `npx tsc -b` and the full test suite stayed green.
- **Committed in:** `8d5e4090` (part of the Task 2 commit — the fix was applied before that commit, not as a separate follow-up)

---

**Total deviations:** 2 auto-fixed (2 blocking/Rule 3)
**Impact on plan:** Both were mechanical adjustments required to keep the gate green at every commit; no scope change, no plan content altered or skipped.

## Issues Encountered

- `VariationTree.test.tsx` case (11) ("inaccuracy severity renders no chip and no marker") initially failed after the Task 3 rewrite: because sidelines now render unconditionally (not gated on `currentNodeId`), the shared `buildPvFixture()` fixture's un-tagged free-move sideline contributed an extra × delete-icon `<svg>`, breaking the `svgs.length === 0` assertion. Fixed by isolating that test to a mainLine-only node map (no sidelines at all) rather than passing `pvNodeIds` to suppress the icon, keeping the assertion's intent (severity-glyph-only) unambiguous.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All automated verification green (lint, tsc -b, 1256 tests, knip). No blockers for merge.
- **HUMAN-UAT required** before considering this fully done — the following items need manual visual/interactive verification on the live `/analysis` page (game mode, a game with ≥2 flaw chips):
  - (a) two free-move lines off different game moves both persist and render simultaneously
  - (b) a free-move line survives navigating to another move and back
  - (c) two tactic chips can be open simultaneously as siblings
  - (d) clicking a tactic chip again toggles only its own line off (others stay open)
  - (e) the × removes a free-move line and returns the board to its fork
  - (f) all of the above verified on a mobile viewport (< 640px) via the Moves tab (`HorizontalMoveList` chip layout, single-paren wrapping, inline × affordance)

## Known Stubs

None.

## Threat Flags

None — this is a frontend-only rendering/state change; no new network input, trust boundary, or injection surface (per the plan's `<threat_model>`, confirmed unchanged during implementation).

---
*Phase: quick-260703-kyb*
*Completed: 2026-07-03*

## Self-Check: PASSED

All 5 modified source files verified present on disk. All 3 task commit hashes (`c6a90005`, `fd3056d4`, `8d5e4090`) verified present in `git log`.
