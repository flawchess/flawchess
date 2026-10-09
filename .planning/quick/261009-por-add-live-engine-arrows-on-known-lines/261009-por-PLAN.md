---
phase: quick-261009-por
plan: 01
quick_id: 261009-por
mode: quick
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/trainArrows.ts
  - frontend/src/lib/__tests__/trainArrows.test.ts
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
  - CHANGELOG.md
autonomous: true
requirements: ["QUICK-261009-por"]

estimate:
  tokens: 60000
  raw_tokens: 60000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "On a stepped known-line position the line's next precomputed move keeps the solid blue engine-pointer arrow (layerKey step-next), and it is the LAST arrow in the array so it paints on top"
    - "On a stepped known-line position the reveal engine's top moves (up to the Stockfish arrows setting) that differ from the line's next move by from-to squares draw as translucent STOCKFISH_SECONDARY_LINE arrows at TRAIN_BEST_MOVE_ARROW_WIDTH, each only once its own PvLine depth is at least TRAIN_STEP_LIVE_ARROW_MIN_DEPTH"
    - "When the engine agrees with the line, the Stockfish arrows setting is 0, the search is still below the depth gate, or the engine has not reached the shown position yet (empty pvLines), a stepped position draws exactly the single line arrow it draws today (Stockfish arrows 1)"
    - "The reveal engine searches at max(Stockfish lines, Stockfish arrows) on every node (puzzle position, known lines and sidelines), so secondary moves exist on the known lines"
    - "The puzzle-position overlay and the off-line (sideline) overlay are unchanged"
  artifacts:
    - path: "frontend/src/lib/trainArrows.ts"
      provides: "buildTrainStepOverlayArrows (line pointer + depth-gated, deduped live secondary arrows) and the exported TRAIN_STEP_LIVE_ARROW_MIN_DEPTH constant"
      contains: "TRAIN_STEP_LIVE_ARROW_MIN_DEPTH"
    - path: "frontend/src/components/train/TrainSolveScreen.tsx"
      provides: "resolveRevealBoardOverlay step branch draws the merged step arrows from the reveal engine's lines and the sfArrows setting"
      contains: "buildTrainStepOverlayArrows"
    - path: "frontend/src/hooks/useTrainRevealTree.ts"
      provides: "one MultiPV width on every reveal node"
      contains: "Math.max(sfLines, sfArrows)"
    - path: "frontend/src/lib/__tests__/trainArrows.test.ts"
      provides: "unit matrix for buildTrainStepOverlayArrows"
      contains: "buildTrainStepOverlayArrows"
  key_links:
    - from: "frontend/src/components/train/TrainSolveScreen.tsx"
      to: "frontend/src/lib/trainArrows.ts buildTrainStepOverlayArrows"
      via: "resolveRevealBoardOverlay step branch, fed revealTree.pvLines (staleness-guarded) and sfArrows"
      pattern: "buildTrainStepOverlayArrows\\(step\\.nextMoveUci"
    - from: "frontend/src/hooks/useTrainRevealTree.ts"
      to: "useStockfishEngine"
      via: "multiPv option, no longer branched on isOffLine"
      pattern: "multiPv: Math\\.max\\(sfLines, sfArrows\\)"
---

<objective>
Train puzzle reveal: when the user steps through a known line (a chip's precomputed server line), the board keeps the solid blue pointer at the line's next move and ALSO shows the live reveal engine's other top moves as translucent secondary arrows, without ever contradicting the line on an early, shallow search.

Purpose: today a stepped line position shows one blue arrow only; the live engine (already running on known-line nodes since Phase 237 plan 06, at MultiPV 1 for the eval bar) is invisible there. Merging the two lets the user see the engine's alternatives while the line's move stays "the answer".

Output: a pure, unit-tested arrow-merging helper in `frontend/src/lib/trainArrows.ts`, the step branch of `resolveRevealBoardOverlay` wired to it, the reveal engine's MultiPV raised on known-line nodes, tests, and a CHANGELOG bullet. Frontend only, no backend change.

Locked design from the orchestrator brief (numbered 1-7 there) is honored as follows: (1) line arrow kept, primary, painted last; (2) live moves as `STOCKFISH_SECONDARY_LINE` secondaries at the free-play width, deduped against the line move; (3) a named depth gate; (4) MultiPV raised on known-line nodes using the off-line rule; (5) root and off-line overlays unchanged; (6) rely on the existing staleness-guarded `pvLines`; (7) shallow functions, no magic numbers, rationale comments, distinct layerKeys.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@frontend/src/lib/trainArrows.ts
@frontend/src/hooks/uciParser.ts

Key facts gathered while planning (do not re-derive):

- `PvLine` (`frontend/src/hooks/uciParser.ts`) carries a per-line `depth: number` plus `moves: string[]` (UCI). The depth gate reads each line's OWN depth: in a MultiPV search the secondary lines of an iteration can trail the top line by one depth, so a per-line check is the honest one and keeps the helper a pure function of `pvLines`.
- `buildTrainFreePlayArrows` (`trainArrows.ts` ~line 257) is the pattern to mirror: reverse-rank push so the primary paints last, `STOCKFISH_SECONDARY_LINE` for non-primary ranks, `TRAIN_BEST_MOVE_ARROW_WIDTH` everywhere, private `squaresFromUci` for malformed-UCI skipping. `buildTrainStepArrows(nextMoveUci)` builds the line pointer with layerKey `'step-next'` via `enginePointerArrows`.
- `ChessBoard`'s `ArrowOverlay` sorts by `onTop`, hover, then `arrowSortKey(color)` and width; `TRAIN_BEST_MOVE_ARROW` and `STOCKFISH_SECONDARY_LINE` share a sort tier and width, so the stable sort keeps input order: the arrow pushed LAST paints on top. Do not add `onTop` to the line arrow (it would change today's stepped board).
- `resolveRevealBoardOverlay` (`frontend/src/components/train/TrainSolveScreen.tsx` ~lines 277-336) is the single overlay resolver; its `step !== null` branch currently returns `buildTrainStepArrows(step.nextMoveUci)`. The component computes `offLineArrows` (~line 1470) from `revealTree.pvLines` and `sfArrows` (read via `useEngineDisplaySettings()` at ~line 722) and calls the resolver at ~line 1476. `PvLine` is not yet imported in this file.
- `useTrainRevealTree` (`frontend/src/hooks/useTrainRevealTree.ts` ~lines 505-525) passes `multiPv: isOffLine ? Math.max(sfLines, sfArrows) : <a module constant equal to 1 declared just above NO_PV_LINES>`. `pvLines` is already staleness-guarded (`NO_PV_LINES` until `engine.currentFen === shownFen`). `sfLines` is 1-5 and `sfArrows` 0-3 (`frontend/src/lib/engineSettings.ts`), so `Math.max(sfLines, sfArrows)` is always at least 1.
- The off-line Stockfish row (`TrainMoveTreeList`) renders only when `tree.isOffLine`, so a wider MultiPV on the known lines changes no list UI.
- The reveal engine searches `go movetime 1500 nodes 2000000` (`useStockfishEngine.ts`).
- Component tests (`TrainSolveScreen.test.tsx`): the `FakeWorker` class (~line 336) emits `info depth 10 multipv N ... pv <this.pv>` for every rank and the same PV regardless of FEN. Existing stepped-position assertions (the Phase 237 tracer test ~line 1425 asserting `data-arrows-count` '1' and `data-arrow-ucis` 'g1f3' at the 'e5' step; the "stepping a reveal line clears the overlay" test ~line 1457) rely on that depth 10 being BELOW the new gate: their reveal engine reports a disagreeing first move ('e2e4') that must stay hidden. They must keep passing unchanged and now double as the component-level below-gate check. The off-line test (~line 2522) shows the two-worker factory pattern (first Worker = grading engine, later Workers = reveal engine).
- The hook test `useTrainRevealTree.test.ts` (~line 1031, describe "the one reveal engine") mocks `useStockfishEngine` and records `engineState.lastMultiPv`; its test "runs MultiPV 1 at the puzzle position and on the known lines" asserts the old width and must be rewritten. `afterEach` already clears the `sfLines`/`sfArrows` localStorage keys.
- knip config has `ignoreExportsUsedInFile: true`, and test files count as importers, so `buildTrainStepArrows` stays a valid export once the screen stops importing it.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Tracer, live engine arrows on a stepped known-line position (helper, resolver wiring, end-to-end component check)</name>
  <files>frontend/src/lib/trainArrows.ts, frontend/src/lib/__tests__/trainArrows.test.ts, frontend/src/components/train/TrainSolveScreen.tsx, frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx</files>
  <behavior>
    Unit tests for `buildTrainStepOverlayArrows(nextMoveUci, pvLines, count)` in a new describe block in `trainArrows.test.ts` (reuse the existing `pv(multipv, firstMove)` fixture shape, but give it a depth parameter; build depths from the exported `TRAIN_STEP_LIVE_ARROW_MIN_DEPTH`, never a bare number):
    - Agree: next 'g1f3', count 1, rank 0 'g1f3' at the gate depth: exactly one arrow, layerKey 'step-next', color TRAIN_BEST_MOVE_ARROW.
    - Disagree at the gate depth (boundary is inclusive): next 'g1f3', count 1, rank 0 'b1c3' at exactly TRAIN_STEP_LIVE_ARROW_MIN_DEPTH: two arrows; the first is b1c3 in STOCKFISH_SECONDARY_LINE at TRAIN_BEST_MOVE_ARROW_WIDTH; the LAST is the step-next g1f3 arrow in TRAIN_BEST_MOVE_ARROW.
    - Below the gate: same lines at TRAIN_STEP_LIVE_ARROW_MIN_DEPTH - 1: only the line arrow.
    - Setting 0: count 0 with a deep disagreeing line: only the line arrow.
    - Engine not at the shown position yet: empty pvLines: only the line arrow.
    - Count 3, rank 0 agrees, ranks 1 and 2 disagree and are deep: three arrows, step-next last, both live arrows secondary-colored, every layerKey unique, none equal to 'step-next' and none starting with 'free-'.
    - Mixed depths: count 2, rank 0 deep and disagreeing, rank 1 shallow: only rank 0's live arrow plus the line arrow.
    - Squares-only dedupe: next 'e7e8q', rank 0 'e7e8n' deep: only the line arrow (the board draws arrows by squares, so an under-promotion on the same squares would just sit under the line arrow).
    - Malformed live UCI ('zz') is skipped without throwing.
    - End of the line (nextMoveUci null), count 1, deep 'b1c3': exactly one secondary-colored live arrow and no step-next arrow (one rule everywhere; see action).
    - Count above available lines yields only the available arrows.
  </behavior>
  <action>
    RED first: add the describe block above to `frontend/src/lib/__tests__/trainArrows.test.ts` (import the new helper and constant alongside the existing `trainArrows` imports; `STOCKFISH_SECONDARY_LINE`, `TRAIN_BEST_MOVE_ARROW`, `TRAIN_BEST_MOVE_ARROW_WIDTH` are already imported there) and run it to see it fail.

    GREEN in `frontend/src/lib/trainArrows.ts` (per locked design items 2, 3, 6, 7):
    - Add an exported constant `TRAIN_STEP_LIVE_ARROW_MIN_DEPTH = 12` next to the arrow-width constants, with a comment carrying the rationale: the reveal engine's throttled commits paint every early iteration, and the first iterations of a MultiPV search still reorder candidates as depth climbs, so a shallow live arrow that disagrees with the line would flicker in and out against the line's move; 12 sits above that early churn and should be reached inside the 1500 ms movetime on most hardware; a device too slow to reach it simply never shows live arrows on a stepped position, which fails safe toward today's line-only board. It is deliberately higher than EvalBar's depth 8 mate-display floor because a disagreeing arrow is a visible claim against the line.
    - Add a private helper (e.g. `stepLiveArrows(nextMoveUci, pvLines, count)`) that walks ranks from `Math.min(count, pvLines.length) - 1` down to 0 (reverse rank order, mirroring `buildTrainFreePlayArrows`), and for each rank uses early `continue`s to skip: a line whose own `depth` is below the gate, a malformed first move (`squaresFromUci` returns null), and a first move whose from-to squares (first four characters) equal the line's next move's from-to squares. Each kept move becomes an arrow with color `STOCKFISH_SECONDARY_LINE`, width `TRAIN_BEST_MOVE_ARROW_WIDTH`, layerKey `step-live-${rank}` (distinct from `step-next` and from the free-play `free-*` keys so `dedupeArrowsByMove` never collapses them). Every live arrow is secondary-colored, rank 0 included, because on a stepped position the line owns the solid blue. Keep nesting depth at most 3.
    - Add the exported `buildTrainStepOverlayArrows(nextMoveUci: string | null, pvLines: readonly PvLine[], count: number): BoardArrow[]` returning the live arrows followed by `buildTrainStepArrows(nextMoveUci)`, so the line pointer is pushed LAST and paints on top (same-tier stable sort in `ChessBoard`'s `ArrowOverlay`). Do not set `onTop` on it. Discretion choice to document in its JSDoc: at the end of a line (`nextMoveUci` null) the same rule still applies, so deep live moves draw as secondaries with no primary; there is no line move to contradict and one rule keeps the helper branch-free.
    - Update `buildTrainStepArrows`' JSDoc (it currently says the line pointer is the ONLY arrow while stepping) to say it is the primary arrow and that `buildTrainStepOverlayArrows` adds the live secondaries.

    Wire it in `frontend/src/components/train/TrainSolveScreen.tsx` (design items 1, 5, 6):
    - Add two fields to `RevealBoardOverlayInput`: `liveLines: readonly PvLine[]` (the reveal engine's staleness-guarded lines for the shown position) and `liveArrowCount: number` (the Stockfish arrows setting), each with a one-line doc comment. Add `import type { PvLine } from '@/hooks/uciParser'`.
    - In `resolveRevealBoardOverlay`'s `step !== null` branch replace `buildTrainStepArrows(step.nextMoveUci)` with `buildTrainStepOverlayArrows(step.nextMoveUci, liveLines, liveArrowCount)`; leave markers, lastMove and lastMoveColor untouched, and leave the off-line, non-root and root branches exactly as they are. Swap the `buildTrainStepArrows` import for `buildTrainStepOverlayArrows`.
    - At the resolver call site (~line 1476) pass `liveLines: revealTree.pvLines` and `liveArrowCount: sfArrows`. Do not add branching to the component body (its complexity is pinned).
    - Update the resolver's JSDoc (a stepped position now also shows the live engine's other top moves as translucent secondaries, deep enough only, the line's pointer on top) and the Phase 228 comment above `const { sfArrows } = useEngineDisplaySettings()` (the setting now also caps the stepped-position secondaries).

    End-to-end component check in `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`:
    - Give `FakeWorker` a third optional constructor parameter for the reported search depth, defaulting to a named test constant equal to 10 (so every existing test is byte-for-byte unaffected), and emit `info depth ${depth} ...` from it.
    - Add one test next to the Phase 237 tracer test: same flow (guess critical, drop d2d4 so You and Best are separate chips, tap the Best chip, tap the 'e5' token of the Best line so the next line move is g1f3), but the grading engine (first Worker) keeps the `'e2e4', 'e2e4 e7e5 g1f3'` PV that builds the Best line, while the reveal engine (later Workers, per the off-line test's two-worker factory pattern) reports a legal disagreeing move `'b1c3'` at `TRAIN_STEP_LIVE_ARROW_MIN_DEPTH` (import it from `@/lib/trainArrows`). Assert at the step position: `data-arrows-count` '2', `data-arrow-ucis` 'b1c3,g1f3', `data-arrow-colors` equal to STOCKFISH_SECONDARY_LINE then TRAIN_BEST_MOVE_ARROW (import STOCKFISH_SECONDARY_LINE from `@/lib/theme` if not already imported). If the Best line turns out to be sourced differently than the first Worker's PV, adapt the fixture so the stepped position's line move still differs from the reveal engine's move; do not weaken the assertions.
    - Do not modify the existing stepped-position tests; they are the below-gate component check.

    No new interactive element, so no testid and no Umami `trackFeature` event: the arrows are passive display and the Stockfish arrows setting change is already tracked. Never run prettier (the frontend has none; ESLint only).
  </action>
  <verify>
    <automated>npm --prefix frontend test -- trainArrows.test.ts TrainSolveScreen.test.tsx</automated>
  </verify>
  <done>
    The new `buildTrainStepOverlayArrows` describe block passes, including the inclusive gate boundary, setting 0, empty lines, squares-only dedupe, end-of-line and line-arrow-last cases; the new component test sees exactly the b1c3 secondary under the g1f3 line arrow at the stepped position; every pre-existing test in both files passes unchanged, the stepped-position ones still showing exactly one arrow because their reveal engine reports depth 10.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Expansion, one MultiPV width on known-line nodes so 2-3 live arrows exist, plus changelog and frontend gate</name>
  <files>frontend/src/hooks/useTrainRevealTree.ts, frontend/src/hooks/__tests__/useTrainRevealTree.test.ts, CHANGELOG.md</files>
  <behavior>
    - At the puzzle position with default settings (Stockfish lines 2, arrows 1) the reveal engine is asked for MultiPV 2, and still 2 after playing e2e4 along a known line (isOffLine false).
    - With Stockfish arrows 3, a known-line node searches at MultiPV 3.
    - The three existing off-line width tests (default 2, arrows 3 gives 3, arrows 0 gives 2) keep passing unchanged.
  </behavior>
  <action>
    RED: in `frontend/src/hooks/__tests__/useTrainRevealTree.test.ts`, describe "useTrainRevealTree: the one reveal engine", rewrite the test titled "runs MultiPV 1 at the puzzle position and on the known lines" so it asserts the settings width instead: defaults give 2 at the root and 2 after `playMove('e2', 'e4')` with `isOffLine` false; add a second test that sets the Stockfish arrows localStorage key to '3' before `renderTree()`, plays e2e4 along the known line, and expects 3. Run it to see the old code fail.

    GREEN in `frontend/src/hooks/useTrainRevealTree.ts` (per locked design item 4):
    - Delete the module constant that pinned the known-line search width to one (declared right above `NO_PV_LINES`) together with its doc comment.
    - Pass `multiPv: Math.max(sfLines, sfArrows)` to `useStockfishEngine` unconditionally (the existing off-line rule, now on every node). Discretion choice, documented in the comment: the puzzle position uses the same width too rather than a third special case; it draws no live arrows, but one width everywhere means stepping between the root, the known lines and a sideline never re-issues `setoption name MultiPV` and never restarts a search just for a width change. The accepted cost is a slightly shallower top line (eval bar, sideline grading seed) within the same 1500 ms movetime. `isOffLine` stays computed: it is still returned.
    - Rewrite the "The one reveal engine" block comment and the file-header paragraph that describe MultiPV 1 on the known lines, so they say the engine runs the settings width everywhere and that stepped known-line positions draw its other top moves as secondary arrows under the line's pointer (`buildTrainStepOverlayArrows`).

    `CHANGELOG.md`: add one user-facing bullet under `## [Unreleased]` → `### Changed`, Train-prefixed like the existing bullet there, e.g. "Train: when you step through a solution line, the board now also shows the engine's other top moves as faint arrows (as many as your Stockfish arrows setting), once its search is deep enough. The line's next move keeps the solid blue arrow." Use em-dashes sparingly.

    Then run the frontend gate from the repo root (see verify). Do not run prettier.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- useTrainRevealTree.test.ts TrainSolveScreen.test.tsx TrainReveal.test.tsx trainArrows.test.ts && ! grep -rn "TRAIN_REVEAL_ONLINE_MULTIPV" frontend/src && grep -n "multiPv: Math.max(sfLines, sfArrows)" frontend/src/hooks/useTrainRevealTree.ts && npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend run knip</automated>
  </verify>
  <done>
    The reveal engine asks for max(Stockfish lines, Stockfish arrows) at the root, on known lines and off them; the hook tests assert it; the old known-line width constant is gone from `frontend/src`; the touched test files, lint (including max-depth 4), `tsc -b` build and knip all pass; CHANGELOG.md has the new Unreleased bullet.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| verdict gate (client) | Answer lines and engine arrows must not be visible before the solve verdict lands |
| browser engine worker | Local Stockfish wasm search; its output is display data only, never sent to the server by this change |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261009por-01 | Information disclosure | resolveRevealBoardOverlay step branch | medium | mitigate | Live step arrows are built only inside the `step !== null` branch; `stepInfo` exists only after the reveal tree is seeded, which `useTrainRevealTree` does only while `active` (post-verdict, T-190-16/T-237-04), and the engine is `enabled: active && engineEnabled`. No pre-verdict path reaches `buildTrainStepOverlayArrows`. |
| T-261009por-02 | Tampering (integrity of what is taught) | buildTrainStepOverlayArrows | low | mitigate | Stale-position arrows prevented by the existing `NO_PV_LINES` staleness guard; shallow contradicting arrows prevented by the per-line `TRAIN_STEP_LIVE_ARROW_MIN_DEPTH` gate; the line's own move always keeps the primary arrow drawn last. Covered by Task 1 unit and component tests. |
| T-261009por-03 | Denial of service | useTrainRevealTree MultiPV width | low | accept | Width rises from 1 to at most 5 on known-line nodes; search is still bounded by the existing `movetime 1500 nodes 2000000` cap, identical to the already-shipped off-line width. |
| T-261009por-SC | Tampering | npm/pip/cargo installs | high | accept | No package installs in this plan; no new dependency is added. |
</threat_model>

<verification>
- Repo-root: `npm --prefix frontend test -- trainArrows.test.ts TrainSolveScreen.test.tsx useTrainRevealTree.test.ts TrainReveal.test.tsx` passes.
- `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `npm --prefix frontend run knip` pass.
- Recommended before integrating: the full frontend suite `npm --prefix frontend test` (the reveal is covered by several heavy component files).
- Manual (optional, owner): on the dev build, solve a Train puzzle, tap a chip's list move, wait a moment: the line's blue arrow stays, and any deep-enough engine alternative appears as a faint blue arrow; with Stockfish arrows 0 only the line arrow shows.
</verification>

<success_criteria>
- Stepped known-line positions show the line pointer plus depth-gated, deduped live secondary arrows capped by the Stockfish arrows setting; agreeing, shallow, empty or setting-0 cases look exactly like today's single line arrow.
- The reveal engine runs one MultiPV width, max(Stockfish lines, Stockfish arrows), on every node.
- Root and sideline overlays unchanged; all existing reveal tests pass unchanged except the rewritten MultiPV-width hook test.
- CHANGELOG `## [Unreleased]` bullet added; lint, build, knip green.
</success_criteria>

<output>
Create `.planning/quick/261009-por-add-live-engine-arrows-on-known-lines/261009-por-SUMMARY.md` when done
</output>
