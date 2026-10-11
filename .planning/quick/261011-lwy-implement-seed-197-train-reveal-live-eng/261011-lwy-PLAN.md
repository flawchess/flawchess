---
phase: quick-261011-lwy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/trainRevealPreview.ts
  - frontend/src/lib/__tests__/trainRevealPreview.test.ts
  - frontend/src/lib/trainRevealLines.ts
  - frontend/src/lib/__tests__/trainRevealLines.test.ts
  - frontend/src/components/train/__tests__/TrainLineChips.test.tsx
  - frontend/src/hooks/useRevealPreview.ts
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
  - frontend/src/components/board/HorizontalMoveList.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/__tests__/EngineLines.test.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/__tests__/TrainMoveTreeList.test.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/lib/trainArrows.ts
  - frontend/src/lib/__tests__/trainArrows.test.ts
  - CHANGELOG.md
autonomous: true
requirements:
  - SEED-197

estimate:
  tokens: 180000
  raw_tokens: 180000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "When the reveal opens, each chip contributes only its first move to the move tree, and the list shows that first move followed by a dimmed preview of at most TRAIN_PREVIEW_MAX_PLIES (6) engine moves seeded from the chip's graded line (seed items 1-3, CONTEXT 'Preview at open', 'Mobile fit')"
    - "At a leaf, the forward button or ArrowRight commits the preview's next move as a real tree node at once, and tapping preview token i commits i+1 plies (at the puzzle position the chip move is played first). Committed nodes never change afterwards (seed item 4)"
    - "A leaf shows its own live PV only once the reveal engine's top line reaches TRAIN_LIVE_ALT_MIN_DEPTH (10) and its first move is legal there. Before that it shows the remaining tail of the nearest ancestor preview whose line matches the committed path (seed item 3, CONTEXT 'Preview replacement depth')"
    - "There is no preview when the current node already has children or at checkmate/stalemate. The preview is never stored in the tree or in the Analyze snapshot, and a snapshot round trip keeps the main line (seed items 5, 8, 9)"
    - "Moves committed from the preview are never graded or badged, while moves the user plays on the board are graded as before (CONTEXT 'Grading of preview-committed moves')"
    - "At a leaf with a preview, the Stockfish row shows engine lines 2..N labelled with their true rank, and everywhere else it shows all N. The board's solid blue pointer is always the preview's next move, i.e. what the forward button commits (seed item 7)"
    - "The chip eval stays the frozen graded reading and carries a 'Graded eval' label, while a live eval badge in formatScore styling leads the preview (seed items 1, 6)"
  artifacts:
    - path: "frontend/src/lib/trainRevealPreview.ts"
      provides: "Pure preview model: anchor rule, live/stored/seed/inherited resolution, legal-prefix replay, display clip"
      contains: "TRAIN_PREVIEW_MAX_PLIES"
    - path: "frontend/src/lib/__tests__/trainRevealPreview.test.ts"
      provides: "Unit tests for the anchor rule, precedence, inheritance, clip, terminal and seed guard"
      contains: "resolvePreviewAnchor"
    - path: "frontend/src/hooks/useRevealPreview.ts"
      provides: "Ephemeral preview state: stored live PVs per leaf, preview-committed node ids, the resolved view"
      contains: "useRevealPreview"
    - path: "frontend/src/hooks/useTrainRevealTree.ts"
      provides: "First-move-only chip seeding, commit-on-step navigation, chipMove, grading exclusion"
      contains: "commitPreview"
    - path: "frontend/src/components/analysis/VariationTree.tsx"
      provides: "Opt-in dimmed preview render mode for the wrap variant (main-line leaf and inside sideline parentheses)"
      contains: "VariationTreePreview"
    - path: "frontend/src/components/train/TrainMoveTreeList.tsx"
      provides: "Preview wiring plus the Stockfish row rule (lines 2..N at a previewed leaf)"
      contains: "rankOffset"
  key_links:
    - from: "frontend/src/hooks/useTrainRevealTree.ts"
      to: "useAnalysisBoard.playUciLine"
      via: "goForward falls back to commitPreview(1) when resolveForwardTarget returns null; commitPreview plays the SHOWN preview's steps"
      pattern: "commitPreview"
    - from: "frontend/src/hooks/useRevealPreview.ts"
      to: "frontend/src/lib/trainRevealPreview.ts"
      via: "resolvePreviewAnchor + resolvePreview, fed by seeds, the stored map and the guarded pvLines"
      pattern: "resolvePreviewAnchor"
    - from: "frontend/src/components/train/TrainMoveTreeList.tsx"
      to: "frontend/src/components/analysis/VariationTree.tsx"
      via: "preview prop whose onTokenClick(i) calls tree.commitPreview(i + 1)"
      pattern: "commitPreview"
    - from: "frontend/src/components/train/TrainSolveScreen.tsx"
      to: "buildTrainStepOverlayArrows"
      via: "resolveRevealBoardOverlay keys the primary pointer on the preview's first step when it is anchored at the current node"
      pattern: "buildTrainStepOverlayArrows"
    - from: "frontend/src/hooks/useTrainRevealTree.ts"
      to: "frontend/src/hooks/useTreeMoveGrading.ts"
      via: "isFreeNode excludes chip first-move nodes AND preview-committed node ids"
      pattern: "isFreeNode"
---

<objective>
Implement SEED-197 on the Train puzzle solution (reveal) screen. Each chip owns only its first move, everything after it is an ordinary free node, and a dimmed live-engine preview sits at the end of the current branch. The forward button, ArrowRight or a tap on a preview token commits the preview into the tree.

Purpose: the fixed 12-ply chip lines are unintuitive (it is unclear how a chip's eval relates to the list) and they go stale, even though the live engine already searches every shown node. The preview shows the freshest engine continuation and keeps the committed history stable.

Output: a new pure lib `trainRevealPreview.ts` and a new hook `useRevealPreview.ts`; reworked `trainRevealLines.ts` / `useTrainRevealTree.ts`; a preview render mode in `VariationTree`; a new Stockfish row rule and board pointer; a "Graded eval" chip label; rewritten tests; a CHANGELOG bullet. Frontend only, no backend change (the reveal endpoint carries no pv/eval).

Decomposition note: this plan follows the caller's constraint and the research's recommended seam split (pure lib, then hooks, then UI) rather than a leading tracer slice. Task 3's TrainMoveTreeList test, which drives the real hook into the real VariationTree, plus the integration suite are the end-to-end proof.

Locked inputs (honor exactly, do not revisit):
- SEED-197 "Design" items 1-9 (`.planning/seeds/SEED-197-train-reveal-live-engine-preview.md`).
- CONTEXT decisions:
  - Mobile fit: clip to `TRAIN_PREVIEW_MAX_PLIES = 6` and auto-scroll.
  - Preview replacement depth: reuse `TRAIN_LIVE_ALT_MIN_DEPTH = 10`, no new depth constant.
  - Game chip search: keep the Game chip's reveal-time full-line search.
  - Grading of preview-committed moves: do NOT grade them.
  - Preview at open: the preview hangs off the active chip's first move while that node is a leaf.
- Research assumptions A1/A2 are confirmed by the owner. A3-A7 are applied as written in RESEARCH.md.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md
@.planning/seeds/SEED-197-train-reveal-live-engine-preview.md
@.planning/quick/261011-lwy-implement-seed-197-train-reveal-live-eng/261011-lwy-CONTEXT.md
@.planning/quick/261011-lwy-implement-seed-197-train-reveal-live-eng/261011-lwy-RESEARCH.md
@frontend/src/lib/trainRevealLines.ts
@frontend/src/hooks/useTrainRevealTree.ts

Working rules for the executor:
- Work ONLY in this worktree (branch `quick/seed-197-live-engine-preview`). Use repo-root-relative paths.
- Stage by explicit path (`git add <path> ...`). Never `git stash`, never `git add -A`.
- Frontend has no Prettier: never run it. eslint `max-depth` 4 is a hard gate, so put loops in helpers.
- `noUncheckedIndexedAccess` is on: narrow every `arr[i]` / `pvLines[0]`.
- Never add per-file vitest timeouts. A heavy-test timeout is fixed project-wide in `vite.config.ts`. If you see one, hoist any `await import` out of the test body into `beforeAll`.
- `npm run lint` and `npm test` do not type-check. Until Task 3's `npm run build`, `tsc` may report errors in files that a LATER task owns (for example `TrainSolveScreen.tsx` still reading removed hook fields after Task 2). Do not chase those early. Task 3 must leave the full gate green.
- No new Umami event: preview commits are stepping (frontend/CLAUDE.md D-06).
- Do not touch the Game chip's reveal-time "played in game" search dispatch in `TrainSolveScreen.tsx` (CONTEXT: Game chip search kept). Its line still supplies the chip eval and seeds the Game chip's preview.

Interfaces the tasks build on (verified in this worktree):
- `TrainEngineLine` (`hooks/trainGradingSupport.ts`): `{ moves: string[]; evalCp: number | null; evalMate: number | null }`, white POV.
- `PvLine` (`hooks/uciParser.ts`): `{ multipv; depth; moves: string[]; evalCp; evalMate }`, white POV.
- `MoveNode` (`hooks/useAnalysisBoard.ts`): `{ id; san; fen; from; to; parentId }`.
- `useAnalysisBoard.playUciLine(ucis)` plays from `currentNodeId` in one functional setState. It reuses a child with the same from/to, stops at the first illegal move, lands on the end and sounds. `graftLine(ucis, parentId)` grafts without navigating.
- `walkLinePath(nodes, ucis, fromId = null)` and `nodeUci(node)` in `lib/trainRevealLines.ts`. `terminalPositionEval(fen)` in `lib/liveFlaw.ts` is non-null for checkmate and any draw.
- `replayPvLine(baseFen, ucis)` (exported from `components/analysis/EngineLines.tsx`) returns per-move `{ san, fen }`, with null SAN from the first illegal move on. `formatScore(evalCp, evalMate)` lives in the same file.
- `TRAIN_LIVE_ALT_MIN_DEPTH = 10` is exported from `lib/trainArrows.ts`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pure preview model and first-move-only chip model (lib + unit tests)</name>
  <files>frontend/src/lib/trainRevealPreview.ts, frontend/src/lib/__tests__/trainRevealPreview.test.ts, frontend/src/lib/trainRevealLines.ts, frontend/src/lib/__tests__/trainRevealLines.test.ts, frontend/src/components/train/__tests__/TrainLineChips.test.tsx</files>
  <behavior>
    trainRevealPreview (new tests, written first and failing):
    - Seed guard: `chipPreviewSeed({ uci: 'e2e4', line: e2e4 e7e5 g1f3 })` gives ucis [e7e5, g1f3] with the line's eval. A line whose first move differs from the chip move, a null line, or a one-move line (empty tail) gives null.
    - `buildPreviewSeeds(chips, linePaths)` keys each seed by the chip's first-move node id (`linePaths[key][0]`). A chip with no node yet, or no seed, is skipped.
    - Anchor: a current leaf is its own anchor. At the root (current null), the anchor is the active chip's first-move node when that node is a leaf. A current node with children gives null, and so does the root when the chip node has children or no chip is active. An anchor whose FEN is checkmate or stalemate gives null.
    - Precedence: live beats stored, stored beats seed, seed beats inherited. `liveCandidate(pvLines)` returns null below depth TRAIN_LIVE_ALT_MIN_DEPTH (depth 9) and a line at depth 10. A live line whose first move is illegal from the anchor FEN falls through to stored/seed/inherited.
    - Inheritance: a leaf with no entry, one committed ply below a chip node with seed [m1..m6], shows [m2..]. Three plies below, it shows [m4..]. When the committed path diverges from every ancestor's line, the result is null. The nearest matching ancestor wins, and a nearer ancestor whose line mismatches is skipped, not fatal. Path comparison uses from-to squares (first four UCI chars), like `findChildBySquares`.
    - Display: steps are the legal prefix (a mid-line illegal move truncates), clipped to TRAIN_PREVIEW_MAX_PLIES (6) even when the stored or seeded tail is longer. Each step carries `{ uci, san }`.
    trainRevealLines (rewrite affected tests):
    - Chips no longer carry a pre-load UCI list. The `line`, `pending`, `quality`, `label` and `san` assertions keep passing unchanged.
    - `buildTreeListView` main line = the active chip's first-move node followed by the lowest-id child chain (first-added = main line). Later-added children render as sidelines, and with no active chip the main line is empty.
    - `resolveForwardTarget`: at the root it is the active chip's first node (no active chip: last-visited root fork, else the lowest id). Below the root it is the last-visited child, else the lowest-id child, else null.
    - `buildRevealTreeSnapshot` emits leaf paths in DFS pre-order with children visited in ascending id, skips chip-only leaves and stays capped. Round trip: graft the snapshot paths in order into a fresh child-reusing node map seeded with the chip first moves, and the `buildTreeListView` main-line UCIs come out identical (RESEARCH Pitfall 1 case: e5, Nf3, step back, Bc4, Nc6).
  </behavior>
  <action>
    Create `frontend/src/lib/trainRevealPreview.ts` as a pure module with no React. It exports:
    - The constant `TRAIN_PREVIEW_MAX_PLIES = 6` (CONTEXT Mobile fit; it caps only the displayed preview, never committed nodes, seed item 9).
    - Types `PreviewLine` `{ ucis: readonly string[]; evalCp; evalMate }` (white POV), `RevealPreviewStep` `{ uci; san }` and `ResolvedPreview` `{ anchorId: NodeId; steps: RevealPreviewStep[]; line: PreviewLine; source: 'live' | 'stored' | 'seed' | 'inherited' }`.
    - `chipPreviewSeed(chip)`, where chip is `Pick<ChipGroup, 'uci' | 'line'>`. Use the same guard the old pre-load cap used: the line must start with the chip's own move. The seed is `line.moves.slice(1)` with the line eval, or null when that tail is empty. This keeps every chip's line, Game included, as the seed (CONTEXT Game chip search kept).
    - `buildPreviewSeeds(chips, linePaths)`, which returns a `Map<NodeId, PreviewLine>`.
    - `liveCandidate(pvLines)`: top line present, `depth >= TRAIN_LIVE_ALT_MIN_DEPTH`, at least one move. Import the constant from `lib/trainArrows.ts`. Do NOT add a new depth constant (CONTEXT Preview replacement depth).
    - `resolvePreviewAnchor({ nodes, currentNodeId, activeChipFirstId })`. It follows the anchor rule in the behavior block (seed items 3/5, CONTEXT Preview at open) and returns null when `terminalPositionEval(anchorFen)` is non-null (seed item 9).
    - `resolvePreview({ nodes, anchorId, live, stored, seeds })`, which returns `ResolvedPreview | null`. Try candidates in order: live (the caller passes it only when the anchor is the current node), `stored.get(anchor)`, `seeds.get(anchor)`, then the inherited walk. The walk goes up `parentId` from the anchor. At each ancestor take its stored entry, else its seed. When that entry's ucis start with the from-to path from the ancestor down to the anchor, use the remaining tail. The walk ends at the root and is bounded by the path length. For each candidate, build steps by replaying from the anchor FEN with `replayPvLine` (reuse it, do not duplicate the chess.js loop) over at most `TRAIN_PREVIEW_MAX_PLIES` ucis, keeping the legal prefix. The first candidate with at least one step wins. Store full tails and clip only at display, so an inherited tail stays six long while the user steps through it.
    Keep every loop in a small helper so nesting stays at or below 4.

    Edit `frontend/src/lib/trainRevealLines.ts` (seed items 1, 2, 9):
    - Delete the 12-ply pre-load cap constant, the private capping helper and the `ChipGroup` field that held the pre-load UCI list, with their doc comments. Update the module doc comment that mentions the cap. The tree now seeds only `[chip.uci]` (Task 2).
    - Add a private `lowestIdChild(nodes, parentId)` helper and use it in both `resolveForwardTarget` (replacing its inline reduce) and `buildTreeListView`.
    - `buildTreeListView`: the main line is `[firstId, ...lowest-id chain to a leaf]` for the active chip (analysis-board semantics, seed item 2). Keep the node-filter logic.
    - `resolveForwardTarget`: delete the known-line loop. Below the root it returns `lastChild ?? first.id`. Keep `linePaths` only for the root case and rewrite the doc comment.
    - `buildRevealTreeSnapshot`: same shape, so the `trainRevealCache.ts` validator stays untouched. Emit leaves in DFS pre-order with children sorted by ascending id (an explicit stack or a recursive helper), skipping known (chip first-move) leaves and keeping the MAX_PATHS / MAX_PLIES caps. Rewrite the doc comments: every committed continuation persists as a path, and the preview never does because it is never in the tree.
    - `classifyTreeNodes`, `walkLinePath`, `nodeUci`, `pathToNode`, `buildChipGroups`, `resolveChipLine` and `resolveChipPending` keep their behavior.

    Tests: create `frontend/src/lib/__tests__/trainRevealPreview.test.ts`, with a local child-reusing graft helper modeled on the `addLine` helper in `trainRevealLines.test.ts` and a mate FEN such as fool's mate for the terminal case. Rewrite the affected `trainRevealLines.test.ts` cases (the pre-load list and cap assertions, `buildTreeListView`, `resolveForwardTarget`, snapshot order plus the new round trip). Drop the removed field from the chip fixtures in `TrainLineChips.test.tsx` (three occurrences).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/lib/__tests__/trainRevealPreview.test.ts src/lib/__tests__/trainRevealLines.test.ts src/components/train/__tests__/TrainLineChips.test.tsx && npx eslint src/lib/trainRevealPreview.ts src/lib/trainRevealLines.ts src/lib/__tests__/trainRevealPreview.test.ts src/lib/__tests__/trainRevealLines.test.ts</automated>
  </verify>
  <done>The new preview tests and the rewritten trainRevealLines tests pass, and eslint is clean on the touched lib files. `ChipGroup` has no pre-load list, the cap constant and helper are gone, the list's main line follows the lowest-id chain, the forward target below the root ignores chip lines, and snapshots are DFS-ordered with a passing round-trip test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Preview state hook and commit-on-step navigation (hooks + hook tests)</name>
  <files>frontend/src/hooks/useRevealPreview.ts, frontend/src/hooks/useTrainRevealTree.ts, frontend/src/hooks/__tests__/useTrainRevealTree.test.ts</files>
  <behavior>
    In the hook test, with the fixtures converted to `{ key, uci, line }` and the engine mock given configurable `pvDepth` (default 10) and `pvMoves` (default `[pvFirstMove]`):
    - Seeding: only the chip first moves exist as nodes (3 chips = 3 nodes). A late-arriving line adds no nodes but changes the preview steps. Nothing is seeded and no preview is returned while inactive (T-237-04).
    - At open (root, Move chip active): the preview is anchored at the chip's first-move node and its steps equal the seed (live is ignored because the anchor is not the current node). canGoForward is true.
    - Forward at the root moves to the chip node and commits nothing. Forward at that leaf commits preview step 0 as a new node, adding exactly one node. `commitPreview(2)` from the root plays the chip move plus 2 plies and lands on the second preview ply.
    - Inheritance: when live is illegal at the new leaf, the preview after a commit is the seed tail. With `pvDepth` 9 a legal live PV does NOT replace it, and with 10 it does. Stepping away and back to that leaf shows the stored live PV immediately.
    - Stepping back to a node with children shows no preview. A committed node's SAN never changes when the live PV changes.
    - Grading: a preview-committed node gets no moveListMarkers entry and no board marker, while a hand-played fork still gets its quality marker (existing grading tests stay green). Mutation check: temporarily drop the committed-id exclusion locally, confirm the ungraded test fails, then restore (do not commit the revert).
    - chipMove is set on a chip first-move node and null elsewhere. commitPreview fires onUserStep, never onUserMove. A board move equal to the preview's next move reports `forked: false`, a different move reports `forked: true`, and either one is graded.
    - Snapshot after commits holds the committed paths and never the preview. Restore keeps the main line and regenerates the preview. A terminal leaf has no preview and canGoForward is false there.
  </behavior>
  <action>
    Create `frontend/src/hooks/useRevealPreview.ts`, a sub-hook that keeps `useTrainRevealTree` from growing past guidance (RESEARCH Pitfall 8).
    - Inputs: `active`, `resetKey` (the tree's focusKey), `nodes`, `currentNodeId`, `activeChip`, `linePaths`, `chips` (`Pick<ChipGroup, 'key' | 'uci' | 'line'>[]`), the staleness-guarded `pvLines` and the `evalReading`.
    - It returns `preview: RevealPreviewView | null`, `committedIds: ReadonlySet<NodeId>` and `markCommitted(anchorId, ucis)`. `RevealPreviewView` is `{ anchorId; steps; evalCp; evalMate }`.
    - Seeds are a memo via `buildPreviewSeeds` and are never stored, so a late Move or Game line refreshes the preview without touching committed nodes.
    - The anchor comes from `resolvePreviewAnchor`, with `activeChipFirstId = linePaths[activeChip]?.[0] ?? null`. Live is `liveCandidate(pvLines)` only when the anchor is the current node.
    - Stored live PVs live in state shaped `{ key, map: Map<NodeId, PreviewLine> }`. Reset by key mismatch, the same pattern as `useTreeMoveGrading`'s qualityState.
    - One effect writes `stored[anchor]` whenever the resolved source is 'live', guarded by equality on the joined ucis plus both evals. No refs are read during render.
    - Badge eval (seed item 6, A3): when the anchor is the current node and `evalReading.depth > 0`, use `evalReading` (the eval bar's reading). Otherwise use the resolved line's own eval.
    - Inactive gives a null preview.
    - Committed ids (CONTEXT grading decision) mirror the existing `restoreTarget` pattern. `markCommitted` sets a pending `{ anchorId, ucis }` state in the same event as the board update. An effect on `[pending, nodes]` resolves `walkLinePath(nodes, ucis, anchorId)`, adds those ids to a keyed `{ key, ids }` state and clears the pending entry. Ids from `nextId` are monotonic and never reused, so a deleted then re-played path is graded again.

    Edit `frontend/src/hooks/useTrainRevealTree.ts`:
    - `RevealChipLine` becomes `Pick<ChipGroup, 'key' | 'uci' | 'line'>` (`ChipGroup` still satisfies it at the TrainSolveScreen call site). The seeding signature becomes `[key, uci]` only, so late line arrival no longer re-runs the graft. Seed with `graftLine([uci], null)` per chip (seed item 1). `linePaths` walks `[uci]`, and `knownIds` is now the chip first-move nodes (still guarding `deleteLine`).
    - Delete the step-info interface, its derive function and memo, the off-line flag and its return field, and the cap import. Add `chipMove: { line: RoleKey; uci: string } | null`, set when the current node is some chip's `linePaths[key][0]`, with `uci = nodeUci(node)`. Rewrite the module doc comment for the first-move model and the preview.
    - Move the engine block (`useEngineDisplaySettings`, `useStockfishEngine`, guarded `pvLines`, `evalReading`) above `canGoForward` and the `latestRef` declaration, then call `useRevealPreview`.
    - `canGoForward` = a forward target exists OR the preview is anchored at the current node with at least one step.
    - Add `preview` to `latestRef`.
    - New `commitPreview(plies)` (seed item 4, Pitfalls 3/6):
      - Read the SHOWN preview from `latestRef`. Bail when it is null, `plies < 1`, or it is stale, meaning the anchor is neither the current node nor (at the root) a root-level chip node.
      - Play via `boardPlayUciLine`. The ucis are the preview's step ucis up to `plies`, prefixed with `nodeUci(anchorNode)` in the root-anchor case.
      - Then call `markCommitted(anchorId, stepUcis)` and `onUserStepRef.current?.()`. No `onUserMove`, no fork event (A4).
    - `goForward` uses the forward target when there is one, else `commitPreview(1)` (seed item 5: with children it follows the last-visited child as today).
    - `playMove`: `forked` is false when an existing child matched OR the move's from-to equals the preview's next step at the current node (A5). It never marks a node as committed, so hand-played moves stay graded.
    - `isFreeNode(id)` = not a chip first-move node AND not in `committedIds`.
    - Return `preview`, `commitPreview` and `chipMove` in `TrainRevealTree`.
    - Keep the restore effects, `snapshot`, the engine options and `useBoardNavigationInput` wiring unchanged.

    Rewrite `frontend/src/hooks/__tests__/useTrainRevealTree.test.ts` to the behavior above. Delete the tests that asserted the removed step-info and off-line fields or the pre-loaded deep nodes, and keep every unrelated test (engine width, root MultiPV floor, fork grading, restore, telemetry) green with updated fixtures.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/hooks/__tests__/useTrainRevealTree.test.ts src/lib/__tests__/trainRevealPreview.test.ts src/lib/__tests__/trainRevealLines.test.ts && npx eslint src/hooks/useRevealPreview.ts src/hooks/useTrainRevealTree.ts src/hooks/__tests__/useTrainRevealTree.test.ts</automated>
  </verify>
  <done>The hook tests pass, including commit-on-forward, token-count commit from the root, inheritance, the depth-10 live replacement, no preview with children, stable committed nodes, ungraded preview commits (mutation-checked), chipMove, telemetry and the snapshot/restore round trip. eslint is clean. `TrainRevealTree` exposes `preview`, `commitPreview` and `chipMove`, and no longer exposes the step-info or off-line fields.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Preview render mode, Stockfish row, board pointer, graded-eval label, test updates, CHANGELOG, full gate</name>
  <files>frontend/src/components/board/HorizontalMoveList.tsx, frontend/src/components/analysis/VariationTree.tsx, frontend/src/components/analysis/__tests__/VariationTree.test.tsx, frontend/src/components/analysis/EngineLines.tsx, frontend/src/components/analysis/__tests__/EngineLines.test.tsx, frontend/src/components/train/TrainMoveTreeList.tsx, frontend/src/components/train/__tests__/TrainMoveTreeList.test.tsx, frontend/src/components/train/TrainSolveScreen.tsx, frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx, frontend/src/components/train/TrainLineChips.tsx, frontend/src/components/train/__tests__/TrainLineChips.test.tsx, frontend/src/lib/trainArrows.ts, frontend/src/lib/__tests__/trainArrows.test.ts, CHANGELOG.md</files>
  <behavior>
    - VariationTree (wrap): with no `preview` prop the output is unchanged (same tokens and testids).
    - Main-line leaf preview: dimmed tokens `variation-preview-0..n` follow the last main-line token, led by the `variation-preview-eval` pill showing the label. Clicking token i calls `onTokenClick(i)`, not `onNodeClick`. Preview tokens never carry aria-current.
    - Sideline-leaf preview: the tokens render inside the block's parentheses, before ")" and the delete x, and the x still deletes. A black-to-move preview labels token 0 "N...".
    - EngineLines `rankOffset={1}`: the first rendered row has the secondary badge color, the aria-label "Line 2: ..." and the testid `engine-line-1-move-0`. The default (0) is unchanged.
    - TrainMoveTreeList over the real hook: at open the list shows e4 as a node and e5/Nf3 as preview tokens. Tapping the e5 preview token moves the FEN to after e4 e5, and e5 becomes a `variation-node-*`. At a previewed leaf the row's badges start at "Line 2", and on a node with children they start at "Line 1".
    - TrainLineChips: the chip eval pill has `title="Graded eval"` and its textContent is unchanged.
    - TrainSolveScreen: the board's primary blue pointer at a previewed leaf is the preview's next move. A chip first-move node shows the chip quality badge and highlight. A preview-committed node shows no quality badge. The forward button/ArrowRight at a leaf adds a node. The Analyze snapshot carries committed paths.
  </behavior>
  <action>
    `frontend/src/components/board/HorizontalMoveList.tsx`: add three OPTIONAL fields to `HorizontalMoveItem`. This is additive, so the Openings/bots/TacticLineExplorer callers are untouched.
    - `onSelect?: () => void`: the button's click uses it instead of `onMoveClick(item.ply)`.
    - `leading?: ReactNode`: rendered before the number label.
    - `after?: ReactNode`: rendered as a sibling AFTER the button, not inside it (avoids a button nested in a button).

    `frontend/src/components/analysis/VariationTree.tsx`: export `VariationTreePreview` `{ anchorId: NodeId; sans: readonly string[]; evalLabel: string | null; onTokenClick: (index: number) => void }` and add an optional `preview` prop. Document it as honored only by the wrap/MobileTree renderer (Train is the only caller). DesktopTree ignores it, and the Analysis callers pass nothing.
    - Add a helper that turns the preview into `HorizontalMoveItem`s:
      - Keys `preview-${i}`, `dimmed: true`, `onSelect` calling `onTokenClick(i)`, testid `variation-preview-${i}` (index only, never SAN).
      - Numbering from `plyFromFen(anchor.fen)` with `moveLabel`. White moves get the "N." label, and token 0 gets the "N..." label when black is to move.
      - Token 0 gets `leading` = the eval pill: a span with testid `variation-preview-eval`, `text-sm` (never text-xs), white semibold text on the `BEST_MOVE_ARROW` background from `lib/theme.ts`. It is omitted when `evalLabel` is null.
      - An optional closing node goes on the last token's `after`.
    - Main-line anchor: in the MobileTree mainLine loop, push the preview items right after the anchor's own item. The anchor is a leaf, so no sibling block attaches there.
    - Sideline anchor (`block.chain.at(-1) === preview.anchorId`, root-fork blocks included): in `siblingBlockToChips` the last real item keeps only its quality marker, and the preview items follow, with the closing ")" and the delete x moved onto the last preview token's `after`. Extract the closing markup into a small helper used by both paths so the x keeps its testid, `stopPropagation`, `onDeleteLine` call and existing `trackFeature('board-tool', { target: 'line-delete' })`. Pass the preview through an options object if the parameter list gets long, and keep nesting at or below 4.
    - The existing HorizontalMoveList auto-scroll keeps the current node visible because preview tokens are never current (CONTEXT Mobile fit). No scroll code is needed.

    `frontend/src/components/analysis/EngineLines.tsx`: replace the all-secondary boolean prop with `rankOffset?: number` (default 0) on `EngineLines` and `PvLineRow`. `rank = lineIndex + rankOffset`: the badge is solid `BEST_MOVE_ARROW` only when `rank === 0`, the aria-label reads `Line ${rank + 1}: ...`, and the move/expand testids use `rank`. The React key, separator and `startPly` stay index-based. Rewrite the matching `EngineLines.test.tsx` case for `rankOffset`.

    `frontend/src/lib/trainArrows.ts`: delete the helper that filtered the line's next move out of the live lines (its only consumer was the Stockfish row) and its tests in `trainArrows.test.ts`. Keep `buildTrainStepOverlayArrows`, `stepLiveArrows`, `buildTrainStepArrows` and `buildTrainStepMarkers` with unchanged signatures, and reword their doc comments from "known line's next move" to "the preview's next move (what the forward button commits)".

    `frontend/src/components/train/TrainMoveTreeList.tsx`: pass `preview` to `VariationTree` from `tree.preview`:
    - `sans` = the step SANs.
    - `evalLabel` = `formatScore(evalCp, evalMate)`, or null when both are null.
    - `onTokenClick(i)` calls `tree.commitPreview(i + 1)`.
    Stockfish row rule (seed item 7):
    - A previewed leaf means `tree.preview` is anchored at `tree.currentNodeId`. There the row renders `tree.pvLines.slice(1, sfLines)` with `rankOffset={1}`. Otherwise it renders all lines with offset 0.
    - Keep `maxLines={sfLines}` so the reserved height never jumps, and keep the skeleton while `tree.pvLines` is empty.
    - Remove the removed-helper import and the all-secondary prop.
    - The row stays hidden at the root. Rewrite the doc comments.

    `frontend/src/components/train/TrainSolveScreen.tsx`: change the `RevealBoardOverlayInput.tree` Pick to `'isAtRoot' | 'currentNodeId' | 'chipMove' | 'preview' | 'activeChip' | 'lastMove' | 'boardMarkers' | 'lastMoveColor'`. Rewrite `resolveRevealBoardOverlay` and its doc comment:
    - The root branch is unchanged (`buildChipFocusOverlay`).
    - Below the root, `previewNext` is the first step's uci when the preview is anchored at the current node, else null. Arrows are `buildTrainStepOverlayArrows(previewNext, liveLines, liveArrowCount)` when `previewNext` exists, otherwise the existing free-play arrows memo.
    - Markers: on `chipMove`, use `buildTrainStepMarkers(chipMove.uci, chipQuality, true)` with `TRAIN_STEP_HIGHLIGHT[quality]`. Otherwise use `tree.boardMarkers` / `tree.lastMoveColor`. A preview-committed node is ungraded, so it shows a plain last-move highlight.
    - `lastMove` is `tree.lastMove`.
    - Remove the old step and off-line branches. Leave the Game-move search, the Analyze handoff (`revealTree.snapshot()`) and the eval bar untouched.

    `frontend/src/components/train/TrainLineChips.tsx` (seed item 1, A7): on the `ChipEval` pill add `title="Graded eval"` and an `aria-label` of the form `Graded eval <score>`, keeping the text content. Add a TrainLineChips test asserting the title.

    Tests:
    - Add the VariationTree preview cases.
    - Rewrite the `TrainMoveTreeList.test.tsx` tracer and the two quick 261009-por row cases for the new rule. Extend its engine mock to return N lines if needed. Keep the fork case.
    - Run `TrainSolveScreen.test.tsx` and fix each failure by asserting the replacement behavior, never by deleting or weakening an assertion into a no-op. The research breakage map lists the areas: stepped-line overlay ~1430-1600, sf-row/off-line arrows ~2584-2715, known-line non-fork telemetry ~2938-3060 and ~4384, ArrowRight ~3200, restored tree ~4463-4592.
    - The FakeWorker returns a constant depth-10 PV for every position, so live replaces the seed wherever that PV's first move is legal.
    - Also run `TrainReveal.test.tsx` and `TrainSolveScreen.restoredGameArrow.test.tsx`.

    CHANGELOG.md, under `## [Unreleased]` / `### Changed`:
    - Add one user-facing bullet. Content: each solution chip now gives only its first move (its eval is the graded eval), the rest is a faded live engine line at the end of the move list that improves while the engine searches, the forward button or right arrow adds its next move, tapping a faded move adds the line up to it, and engine moves added this way are not graded.
    - In the existing unreleased bullet about stepping through a solution line, replace its final sentence (about the line keeping the solid blue arrow and the row leaving out the repeated line) with a short one saying that at the end of a line the row leaves out the top engine line because the faded preview already shows it.
    - Use em-dashes sparingly.

    Finish with the full frontend gate. If the gate modifies nothing, that is expected. If eslint `--fix` style changes appear, stage them by path with the task.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/analysis/__tests__/VariationTree.test.tsx src/components/analysis/__tests__/EngineLines.test.tsx src/components/train/__tests__/TrainMoveTreeList.test.tsx src/components/train/__tests__/TrainLineChips.test.tsx src/lib/__tests__/trainArrows.test.ts && npm run lint && npm run build && npm test -- --run && npm run knip</automated>
  </verify>
  <done>The full frontend gate passes: lint (max-depth 4), build (tsc -b), the whole vitest suite and knip (no dead exports from the removed machinery). The reveal list shows the dimmed preview with a leading live eval pill, preview taps and the forward button commit, the Stockfish row shows lines 2..N at a previewed leaf, the board pointer follows the preview's next move, the chip eval reads "Graded eval" on hover, and CHANGELOG has the new bullet with the superseded sentence updated.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sessionStorage → reveal tree | The Analyze → Back snapshot (`RevealTreeSnapshot`) is replayed into the tree; a tab could tamper with it |
| browser engine → display | The live Stockfish PV is untrusted for legality (it can lag one position, Pitfall 2) |
| pre-verdict → post-verdict | Answer lines must not exist client-side before the solve verdict lands |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261011-lwy-01 | Information disclosure | `useRevealPreview` / chip seeds before the verdict | medium | mitigate | The preview is null while `active` is false. Seeds derive only from chips, which are empty before the verdict (T-237-07), and the tree still seeds nothing while inactive (T-237-04). A Task 2 hook test asserts no nodes and no preview while inactive |
| T-261011-lwy-02 | Tampering | snapshot replay (`buildRevealTreeSnapshot` + restore graft) | low | mitigate | The snapshot shape is unchanged, so the `trainRevealCache.ts` validator applies as is. The `REVEAL_TREE_SNAPSHOT_MAX_PATHS` / `_MAX_PLIES` caps are kept at build and replay (T-237-05), the chess.js-guarded graft keeps the legal prefix, and DFS ordering changes only the order |
| T-261011-lwy-03 | Tampering | live PV legality at the anchor | low | mitigate | Live is used only when the anchor is the current node and its first move replays legally from the anchor FEN. Every preview is replayed to its legal prefix, and `playUciLine` stops at an illegal move, so a stale or malformed PV cannot corrupt the tree |
| T-261011-lwy-04 | Repudiation / integrity | grading badges on engine-committed moves | medium | mitigate | Preview-committed node ids are excluded through `isFreeNode`, so engine moves never carry user-quality badges. Preview commits never reach the grading engine or the solve POST (the reveal tree is post-verdict client state). Covered by a mutation-checked hook test |
| T-261011-lwy-05 | Denial of service | stored live-PV map / re-render churn | low | mitigate | The stored map is keyed per tree (`resetKey`) and to node ids. Writes are equality-guarded on ucis plus eval, like `setEvalByFen`, and only the clipped display is replayed per render |
| T-261011-lwy-06 | Information disclosure | automation hooks / analytics | low | mitigate | Preview testids are index-based (no SAN), and no Umami event is added (stepping, D-06) |
| T-261011-lwy-SC | Tampering | npm/pip/cargo installs | high | accept | No package installs in this plan (no `package.json` change), so the package-legitimacy gate is not triggered |
</threat_model>

<verification>
- Task verifies pass in order. Task 3's full gate (`cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`) is the authoritative check.
- Source coverage:
  - Seed items 1-9 map to Task 1: 1, 2, 3, 9. Task 2: 1, 3, 4, 5, 8. Task 3: 1, 6, 7, 9.
  - CONTEXT Mobile fit maps to Tasks 1 and 3. Preview replacement depth maps to Task 1. Game chip search maps to Tasks 1 and 3 (kept untouched). Grading of preview-committed moves maps to Task 2. Preview at open maps to Tasks 1 and 2.
  - Research A3-A7 are applied in Tasks 2 and 3.
- Manual spot-check (optional, owner UAT): open a Train reveal, confirm the faded preview after the chip move, press the forward button repeatedly and confirm instant commits, pause and confirm the preview refines, and confirm the Stockfish row starts at line 2 at the leaf.
</verification>

<success_criteria>
- Chips seed only their first move, and the list's main line is the first-added continuation chain.
- The dimmed preview (at most 6 plies) shows at leaves only (including the active chip's first move at open). It is seeded from the graded line, inherits the ancestor tail, and is replaced by the live PV at depth 10 or more.
- The forward button / ArrowRight / a token tap commit instantly, committed nodes are stable, and preview commits are ungraded.
- The Stockfish row shows lines 2..N at a previewed leaf and all N elsewhere, and the board pointer equals the preview's next move.
- The chip eval is labelled "Graded eval", and a live eval pill leads the preview.
- The snapshot persists committed paths only, in DFS order, and restore preserves the main line.
- The full frontend gate is green, and the CHANGELOG [Unreleased] bullet is added with the superseded sentence updated.
</success_criteria>

<output>
Create `.planning/quick/261011-lwy-implement-seed-197-train-reveal-live-eng/261011-lwy-SUMMARY.md` when done.
</output>
