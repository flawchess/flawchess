---
phase: 237-train-reveal-chips-move-tree
plan: 02
subsystem: ui
tags: [react, hooks, chess.js, move-tree, train, useAnalysisBoard, keyboard]
status: complete

requires:
  - phase: 190.1 / 236 (Train reveal lines, instant grade)
    provides: "buildLineBoxes grouping, GameMoveLineState, InstantGradeState pending/failed line states"
provides:
  - "useAnalysisBoard.graftLine(uciMoves, parentId): non-navigating, child-reusing, silent line graft; exported findChildBySquares"
  - "lib/trainRevealLines.ts: RoleKey, MAX_LINE_PLIES, ChipGroup, buildChipGroups, walkLinePath, nodeUci, pathToNode, classifyTreeNodes, buildTreeListView, resolveForwardTarget, RevealTreeSnapshot + caps, buildRevealTreeSnapshot"
  - "useTrainRevealTree: seeding, chip focus (D-01/D-04), user-move reporting (D-13), forward rule, list view, step info, deleteLine, snapshot/restore, keyboard"
  - "useBoardNavigationInput optional goHome (Home key)"
affects: [237-03, 237-04, 237-05, 237-06, 237-09]

tech-stack:
  added: []
  patterns:
    - "Known-line membership derived each render by walking each chip's UCI list through the tree, never stored on nodes"
    - "Late/restored lines graft with a functional setState that never writes currentNodeId"
    - "Commands read latest derived values through a ref synced after commit, so identities stay stable"
    - "Persist UCI paths, not node ids (ids differ across async rebuilds)"

key-files:
  created:
    - frontend/src/lib/trainRevealLines.ts
    - frontend/src/lib/__tests__/trainRevealLines.test.ts
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
    - frontend/src/hooks/__tests__/useBoardNavigationInput.test.ts
  modified:
    - frontend/src/hooks/useAnalysisBoard.ts
    - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
    - frontend/src/hooks/useBoardNavigationInput.ts

key-decisions:
  - "Tree convention: the hook's mainLine stays empty; semantics come from derived linePaths and the list component later receives a VIEW (listView.mainLine = active chip path, nodes filtered)"
  - "Chip key = primary role (roles[0]); focus state is keyed to startFen+active so a new puzzle or deactivation falls back to You without a reset effect"
  - "onChipSelect fires from selectChip (tap) AND from a root move onto a chip's first node, so plan 09's chips-selected telemetry sees both routes"
  - "Rewinding onto the puzzle position with no chip focused restores the You focus from goBack as well as goToRoot/Home (research A1, extended to the one-step-back route)"
  - "A sideline hanging off a chip's own line counts as on that chip's line: selectChip of the same chip does not jump to the root (research Open Question 2)"
  - "lastChildByParent is a ref (cleared with the tree), canGoForward uses an empty map since it only asks whether a target exists"
  - "Restore applies once per puzzle position while active; the nav target lands in the same render as the grafts (batched effect updates), so it walks the whole legal path or its longest legal prefix with no settle detection"

patterns-established:
  - "Mutation proof: graftLine writing currentNodeId, resolveForwardTarget using the lowest id, D-04 not clearing the focus, and the snapshot caps/silent landing removed each turned the targeted tests red"

requirements-completed: [D-01, D-02, D-03, D-04, D-13]

duration: 16 min
completed: 2026-10-09
actuals:
  tokens: 26000
  tasks: 3
  commits: 3
plan_head_before: 1f1cece0ec93fd87d3cae2a023e9bf01cc7b3b30
plan_head_after: a24273261f44cc482c58289dffe89bc351991af9
commits: 3

coverage:
  - id: D1
    description: "graftLine grafts a line under a node (or the root) with child reuse, never moves the board, plays no sound, ignores an unknown parent and stops at an illegal move"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts#useAnalysisBoard — graftLine (Phase 237)"
        status: pass
    human_judgment: false
  - id: D2
    description: "buildChipGroups merges coinciding roles into one chip labelled with the roles joined by ' = ', caps lines at 12 plies, keeps the Phase 236 loading/failed states and the standalone game chip pending rule"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRevealLines.test.ts#buildChipGroups"
        status: pass
    human_judgment: false
  - id: D3
    description: "Three chip lines seed ONE tree at the puzzle position, nothing seeds while inactive, and a line arriving late grafts in place without moving the board"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree seeding / late lines"
        status: pass
    human_judgment: false
  - id: D4
    description: "Chip focus: a tap jumps to the root unless the board is on that chip's line or a sideline of it (D-01); a root move matching no chip deselects every chip and the list shows only the user's line (D-04); rewinding restores You"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree user moves (D-04, D-13)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRevealLines.test.ts#buildTreeListView"
        status: pass
    human_judgment: false
  - id: D5
    description: "playMove/playLine report each user move with source and fork flag; a hand-played move onto an existing node is a board move, not a fork"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree user moves (D-04, D-13)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Forward steps into the ACTIVE chip at the root, then the last-visited child, then the known line; Home rewinds via the optional goHome without changing Analysis/Openings"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRevealLines.test.ts#resolveForwardTarget"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBoardNavigationInput.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree keyboard"
        status: pass
    human_judgment: false
  - id: D7
    description: "The tree serializes to capped UCI paths and restores from them (focus, sidelines, shown node) silently, reusing nodes when a chip line grafts in after the restore, never throwing on illegal paths"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree snapshot / restore"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRevealLines.test.ts#buildRevealTreeSnapshot"
        status: pass
    human_judgment: false
---

# Phase 237 Plan 02: Reveal Move Tree Summary

**One `useAnalysisBoard` tree now holds all three reveal chip lines as root branches via a non-navigating `graftLine`, with chip focus (D-01/D-04), fork reporting (D-13), a chip-aware forward rule, a filtered list view, Home-key support and UCI-path snapshot/restore, all proven through the real hook before any screen is touched.**

## Performance

- **Duration:** 16 min
- **Tasks:** 3 (1 tracer, 2 TDD-flagged auto)
- **Files:** 5 created, 3 modified (frontend only, no screen file)

## Accomplishments

- `useAnalysisBoard.graftLine(uciMoves, parentId)`: one functional `setState`, child reuse through the new exported `findChildBySquares` (also used by `makeMove` and `playUciLine`, shallower than their inline loops), never writes `currentNodeId`, silent, returns `prev` when nothing was created.
- `lib/trainRevealLines.ts` (pure): `buildChipGroups` lifted from `buildLineBoxes` with the D-02 generic merge, the Phase 236 pending/failed states, a standalone game chip that is `loading` until its search is ready and `failed` on error, and `lineUcis` capped at 12 plies and always starting with the chip's own move. Tree helpers: `walkLinePath`, `nodeUci` (promotion letter), `pathToNode`, `classifyTreeNodes`, `buildTreeListView`, `resolveForwardTarget`, `buildRevealTreeSnapshot`.
- `useTrainRevealTree`: seeds only while `active` (T-190-16, T-237-04), derives `linePaths`/`activeChip`/`isOffLine`/`stepInfo`/`listView` each render, and exposes `selectChip`, `playMove`, `playLine`, `goBack`, `goForward`, `goToNode`, `goToRoot`, `deleteLine`, `snapshot()`, plus a `restored` option and arrow/Home keyboard through `useBoardNavigationInput` (inert until active and a wrapper ref is mounted).
- `useBoardNavigationInput`: optional `goHome`; without it Home is ignored and not default-prevented.

## Task Commits

1. **Task 1 (tracer): graftLine, chip groups, seeding and late graft** - `656f89152` (feat)
2. **Task 2: navigation, forks, list view, Home key** - `fc54d056e` (feat)
3. **Task 3: snapshot and restore as UCI paths** - `a24273261` (feat)

Tracer gate: the `<verify>` ran end to end after the Task 1 commit (vitest on the three files, lint, build, knip), passed, and expansion proceeded.

## Verification

- Plan verification set: `useAnalysisBoard`, `trainRevealLines`, `useTrainRevealTree`, `useBoardNavigationInput`, `useChessGame` tests green (147 tests at Task 2; 79 in the two new-logic files at Task 3).
- `npm run lint`, `npm run build` (`tsc -b`), `npm run knip` clean after every task. `npm run lint:cognitive` flagged `classifyTreeNodes` (19), fixed by extracting `resolveFreeNodeOwner`; no new cognitive finding in the touched files.
- Full frontend suite after Task 3: 317 files, 5386 tests, all passing (so the `makeMove`/`playUciLine` refactor and the keyboard hook change regress nothing).
- No screen file changed.

## Mutation proof

Each critical behavior was proven by reverting it and watching its tests fail, then restoring the file from a backup:

- `graftLine` also writing `currentNodeId`: 6 tests red (graft, late-graft board position, sound).
- `resolveForwardTarget` at the root returning the lowest-id child: 3 tests red (pure and hook).
- Root move not clearing the focus (D-04): 3 hook tests red.
- Snapshot replay without the path/ply caps and the silent landing: round trip, path cap and ply cap tests red.

## TDD Gate Compliance

Tasks 2 and 3 were flagged `tdd="true"` but the plan is `type: execute`, and the tests were written together with the implementation rather than as a separate failing RED commit first. RED-equivalent evidence is the mutation runs above.

## Deviations from Plan

None that change behavior or scope. Small ordering and design notes:

- `classifyTreeNodes` (listed under Task 2) landed in Task 1, because the tracer's `activeChip` derivation needs it; its tests are in the Task 1 commit.
- `selectChip` also fires `onChipSelect` (the plan's behavior text only spelled it out for `playMove`); this keeps plan 09's chips-selected counter consistent across both routes.
- Rewinding with no focus restores You from `goBack` too, not only `goToRoot`/Home, so stepping back onto the puzzle position never leaves the root with no lit arrow.
- `TreeListView` and `ForwardTargetInput` are extra exported types (used in-file and by the hook; knip clean via `ignoreExportsUsedInFile`).
- Test infrastructure note: this project's vitest setup has no auto-cleanup, so tests that mount hooks registering window listeners unmount explicitly in `afterEach` (otherwise Home/arrow listeners leak across tests).

## Known Stubs

None.

## Threat Flags

None. T-237-04 (no seeding or restore while inactive) and T-237-05 (snapshot caps when building and replaying, chess.js-guarded replay) are implemented and pinned by tests; no new network, auth or storage surface.

## Next Phase Readiness

Plans 04/05 can render `useTrainRevealTree` (`listView`, `stepInfo`, `activeChip`, `rootFocus`) and wire `playMove`/`selectChip`/`deleteLine`; plan 06 adds the engine and sideline grading to the same hook; plan 09 passes `snapshot()` into the reveal cache and `restored` back in, and feeds `onUserMove`/`onUserStep`/`onChipSelect` to the v2 telemetry counters.

## Self-Check: PASSED

- FOUND: frontend/src/lib/trainRevealLines.ts, frontend/src/hooks/useTrainRevealTree.ts, frontend/src/lib/__tests__/trainRevealLines.test.ts, frontend/src/hooks/__tests__/useTrainRevealTree.test.ts, frontend/src/hooks/__tests__/useBoardNavigationInput.test.ts
- FOUND commits: 656f89152, fc54d056e, a24273261
