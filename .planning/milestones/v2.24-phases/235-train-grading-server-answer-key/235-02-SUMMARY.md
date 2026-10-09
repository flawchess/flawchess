---
phase: 235-train-grading-server-answer-key
plan: 02
subsystem: ui
tags: [react, typescript, stockfish-wasm, train, grading, chess.js, vitest]

requires:
  - phase: 235-train-grading-server-answer-key (plan 01, same wave)
    provides: "TrainPuzzle JSON gains key_move_uci / puzzle_type / runner_up_uci (optional here, so a stale server still works)"
provides:
  - "GradingAnchor: the think-time search is an anchor (after-key position for a keyed puzzle, root search for D-07 fallback)"
  - "startGrading(fen, keyUci?) and key-anchored gradeMove / startGameMoveSearch"
  - "GradeResult.bestMoveUci / bestLine / esBefore now name the server key, so the reveal arrow, line boxes, board badge and free-play seed follow it with no further edits"
  - "terminalSearchResult: checkmate / stalemate after-move positions scored without a search"
  - "TrainPuzzle TS fields key_move_uci? / puzzle_type? / runner_up_uci?"
affects: [235-05 browser UAT of the reveal arrow, 235-03 server-side key payload, train reveal consumers]

actuals:
  tokens: 12500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Anchor search: grade a move by comparing two same-horizon (after-one-move) phone searches, never a server number"
    - "Optional TS field + single `?? null` default for a payload field a stale server may omit"
    - "Terminal-position short circuit before dispatching an engine search"

key-files:
  created: []
  modified:
    - frontend/src/types/train.ts
    - frontend/src/hooks/useTrainGradingEngine.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx

key-decisions:
  - "Kept the three movetime/node constants untouched (D-03): TRAIN_GRADING_MOVETIME_MS 1500, TRAIN_GRADING_MAX_NODES 2000000, pinned by a test"
  - "Mate distance in the terminal short circuit is the sign-only value 1 (DELIVERED_MATE_DISTANCE), because evalToExpectedScore reads only the sign"
  - "uciParser.rankLineForMove stays: its own test still imports it and knip exits 0, so the plan's 'delete if knip flags it' branch did not trigger"

requirements-completed: [D-01, D-03, D-07, D-08, D-09]

coverage:
  - id: D1
    description: "A keyed puzzle's think-time search evaluates the position after the key (width 1, mount budget), never the root"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#a keyed startGrading searches the position AFTER the key at the mount budget, never the root (D-08)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Playing the key grades good with no second search; any other move runs one after-move search and is graded by classifyLiveSeverity(after-key ES, after-played ES)"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#playing the key grades GOOD with no further search, and the key line is rooted at the puzzle fen (D-01)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#an off-key move runs ONE after-move search and is graded against the after-key ES, naming the key as best (D-01/D-09)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GradeResult.bestMoveUci / bestLine are the server key, and the reveal's best arrow names it even when the phone's own search prefers another move; played and game lines are clamped to the key line"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#keyed puzzle: grades against the server key and the best arrow names it (Phase 235)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#D-09 clamp: an off-key move whose after-search reads better than the key line grades good and its line is capped at the key line eval"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#D-09 game move: a different game move posts ONE after-move search and its eval is clamped to the key line"
        status: pass
    human_judgment: false
  - id: D4
    description: "A null, missing or illegal key keeps today's root search, exact-match fast path and root-vs-after-move drop"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#D-07: %s keeps the legacy root search and the exact-match fast path (3 cases)"
        status: pass
    human_judgment: false
  - id: D5
    description: "No global movetime raise: TRAIN_GRADING_MOVETIME_MS stays 1500 and TRAIN_GRADING_MAX_NODES stays 2000000"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#keeps the grading budget unchanged: no global movetime raise (D-03)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Checkmate and stalemate after-move positions are scored without dispatching a search, so a mating key or mating played move is never read as a neutral 0.5"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#a mating key is scored without a search, and a weaker move is graded against the mate, not a neutral 0.5 (T-235-05)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#a played move that itself mates is scored without a search and grades good against a non-mating key"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#a played move that stalemates is scored as a draw (evalCp 0) without a search"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-05: the key, runner-up and puzzle type are read only to start grading and never render before the attempt"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "D-05 gate A and gate B greps from the plan (three files only; no destructured or bracket read in TrainSolveScreen.tsx)"
        status: pass
    human_judgment: false
  - id: D8
    description: "On the real reveal the best arrow and BEST MOVE box name the server key in a live browser against a server that sends the key"
    verification: []
    human_judgment: true
    rationale: "Needs plans 01 and 03 on the server; the plan assigns the browser UAT to plan 05"

duration: 15min
completed: 2026-10-07
status: complete
plan_head_before: e4897d1d0704cf6324a5cf20a0bd93f2d6a25d1b
plan_head_after: cf6af5fdc0335f1b14bb78ce6065e9bd91933a8d
commits: 2
---

# Phase 235 Plan 02: Frontend Key-Anchored Grading Summary

**The phone now grades against the server key: the think-time search evaluates the position after `key_move_uci`, playing the key is good with no second search, any other move is graded by two same-horizon phone searches, and the reveal names the key.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-10-07T18:28:00Z
- **Completed:** 2026-10-07T18:43:35Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `GradingAnchor` replaces the root best-search result. `startGrading(fen, keyUci)` runs one width-1 search of the position after the key (D-08); a null, missing or illegal key falls back to today's root search with the old exact-match fast path (D-07).
- `gradeMoveInner` has one comparison: the key (or, on the legacy path, the root bestmove) grades good with no search, anything else runs one after-move search and is graded by `classifyLiveSeverity(anchor.es, esAfter)` (D-01). No server number enters the drop.
- `GradeResult.bestMoveUci`, `bestLine` and `esBefore` keep their names but now mean the key, its after-key line and the after-key ES (D-09), so the reveal arrow, line boxes, board badge and free-play seed name the key with no consumer edits. The played and game lines are clamped to the key line's eval.
- `terminalSearchResult` fixes a latent grading bug: the vendored Stockfish reports `mate 0` or no score for a mated or stalemated FEN, which read as a neutral 0.5. A mating key would have anchored at 0.5 and a non-best mating move was already graded as a blunder. Mate and stalemate are now scored directly with no dispatch.
- `TrainSolveScreen` passes `puzzle.key_move_uci ?? null` at both `startGrading` call sites; the key is read nowhere else (D-05).

## Task Commits

1. **Task 1 (tracer): key-anchored mount search, key fast path, reveal names the key** - `e486810a4` (feat)
2. **Task 2: legacy fallback, terminal positions, key-line clamp, game-move shortcut** - `cf6af5fdc` (fix)

The tracer feedback gate (auto-verifiable `<verify>` only, `end-of-phase` mode) was satisfied by re-running the plan's tracer verify after Task 1: targeted vitest, `npm run lint`, `npm run build` all green. Tracer verified end-to-end, then expanded.

## Files Created/Modified

- `frontend/src/types/train.ts` - optional `key_move_uci` / `puzzle_type` / `runner_up_uci` on `TrainPuzzle`; header and `PuzzleRevealResponse` docstrings rewritten (D-05, D-09)
- `frontend/src/hooks/useTrainGradingEngine.ts` - `GradingAnchor`, `anchorRef` / `anchorReadyRef`, `searchAfterMove`, `terminalSearchResult`, key-anchored `startGrading` / `gradeMoveInner` / `startGameMoveSearch`, rewritten grading-rule header and `GradeResult` comments
- `frontend/src/components/train/TrainSolveScreen.tsx` - both `startGrading` calls pass the key; `puzzle.key_move_uci` added to both dependency arrays
- `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts` - describes "key-anchored grading (Phase 235 D-01/D-08)" (4 cases) and "anchor fallbacks, terminal positions, clamp (Phase 235 D-07/D-09)" (9 cases)
- `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx` - tracer test "keyed puzzle: grades against the server key and the best arrow names it (Phase 235)"

## Decisions Made

- Movetime and node-cap constants untouched (D-03), pinned by a test.
- The terminal mate distance is the sign-only value 1 (`DELIVERED_MATE_DISTANCE`), matching what the old root search reported for a mate-in-one key.
- `uciParser.rankLineForMove` is kept: its own test still imports it and `npm run knip` exits 0, so the plan's "delete if knip flags it" branch never triggered.

## Mutation Proof (Task 2 step 4)

Each mutation was applied, the file run, and then reverted (suite green again afterwards, 254 tests in the three touched files).

| Mutation | Red result |
| --- | --- |
| a. `searchAfterMove` always dispatches (`terminalSearchResult` skipped) | 3 named tests red: "a mating key is scored without a search ... (T-235-05)" (expected 0 `go`, got 1), "a played move that itself mates is scored without a search ...", "a played move that stalemates is scored as a draw ..." (both time out waiting on a search that is never answered) |
| b. `playedMoveUci === anchor.keyUci` fast path removed from `gradeMoveInner` | 10 tests red, including the Task 1 case "playing the key grades GOOD with no further search, and the key line is rooted at the puzzle fen (D-01)" and the three D-07 fast-path cases |

TDD order for Task 2: the three terminal tests were written first and confirmed red against the Task 1 code before `terminalSearchResult` was added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Ordering - Rule 3] The anchor-based `startGameMoveSearch` landed in Task 1, not Task 2**
- **Found during:** Task 1
- **Issue:** Task 1's acceptance criterion requires `bestSearchRef` to be gone (count 0), but `startGameMoveSearch` read it for the exact-UCI rank lookup. The file cannot compile or lint without migrating that function in the same commit.
- **Fix:** Migrated `startGameMoveSearch` to the anchor (key shortcut plus clamp to the key line) and dropped the `rankLineForMove` import in Task 1. Task 2 then added its tests.
- **Files modified:** frontend/src/hooks/useTrainGradingEngine.ts
- **Verification:** the existing startGameMoveSearch tests pass unchanged through the legacy anchor; the new game-move tests pass.
- **Committed in:** e486810a4

**2. [Comment hygiene] Header comment in TrainSolveScreen.tsx**
- A blanket `sed` of `startGrading(puzzle.fen)` also rewrote the file-header comment to the new call text, which would have made the acceptance grep count 3 instead of 2. The header prose was rewritten without the literal call, restoring the count of 2.

---

**Total deviations:** 1 ordering deviation, 1 comment fix
**Impact on plan:** None on behavior; no scope creep.

## Notes on Acceptance Criteria

- `grep -c "searchAfterMove(" ...` returns 3 (anchor search, after-played search, game-move search). The plan counted the definition as a fourth; it is declared as `const searchAfterMove = useCallback(`, so the literal `searchAfterMove(` pattern does not match it. All four sites exist.
- D-05 gate A prints exactly `TrainReveal.tsx`, `TrainSolveScreen.tsx`, `types/train.ts`; gate B prints nothing.

## Issues Encountered

- The tracer test's color assertion first failed because the mocked board joins `rgba(...)` colors with commas; the test now splits only on commas outside parentheses.

## Known Stubs

None.

## Threat Flags

None. No new network surface; T-235-04 (no pre-attempt display), T-235-05 (terminal scoring) and T-235-06 (illegal key falls back, never throws) are all covered by the code and tests above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Frontend is correct against a server that does not send the key yet (fields are optional, legacy path), and picks up the key as soon as plan 01 / plan 03 ship it.
- Remaining for plan 05: browser UAT of the reveal arrow against a server that sends the key.
- Verification run: `npm run lint`, `npm run build`, `npm run knip` all exit 0; full `npm test -- --run`: 312 files, 5196 tests pass.

## Self-Check: PASSED

- All five modified files exist on disk and are in the diff of e486810a4 / cf6af5fdc.
- Commits e486810a4 and cf6af5fdc are ancestors of HEAD; `git rev-list --count` from the plan base is 2.

---
*Phase: 235-train-grading-server-answer-key*
*Completed: 2026-10-07*
