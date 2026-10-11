# Quick 261011-lwy: SEED-197 Train reveal live engine preview - Research

**Researched:** 2026-10-11
**Domain:** Frontend integration (React 19 hooks, `useAnalysisBoard` tree, `VariationTree` wrap renderer)
**Confidence:** HIGH for the code map (every symbol read this session in the worktree), MEDIUM for the design recommendations marked `[ASSUMED]`

## Summary

All three chip lines are pre-loaded into the `useAnalysisBoard` tree today, and chip ownership comes from walking `ChipGroup.lineUcis` through the tree (`walkLinePath` gives `linePaths`, `classifyTreeNodes` gives `owners`). Shrink each chip's pre-load to its first move (`[chip.uci]`) and most of the ownership machinery keeps working unchanged: `linePaths[key]` becomes the one-node path, `classifyTreeNodes` hands every free node to its nearest chip-owned ancestor, and the restore graft is untouched. The parts that must change are the list's main line, which has to follow the lowest-id child chain past the first move (analysis-board semantics), forward navigation, the step overlay, the Stockfish row filter and the snapshot leaf order.

The preview is new, ephemeral, display-only state. The cleanest model is a pure resolver in `lib/` fed by three inputs: **seeds** (each chip line's moves after the first, keyed by the chip's first-move node), **stored** (the last deep live PV seen per leaf, kept in hook state) and **live** (the current leaf's PV once `pvLines[0].depth >= TRAIN_LIVE_ALT_MIN_DEPTH`). With no entry of its own, a node inherits from its nearest ancestor that has a preview, as long as the committed path matches that preview's prefix. This makes "inherit the previous preview's tail" correct for ›, for a token tap that commits several plies, and for a board move that matches the preview, all without tracking node ids at commit time.

`VariationTree` is only rendered with `variant="wrap"` from Train, and that variant always goes through `MobileTree` → `HorizontalMoveList`, which already auto-scrolls the current token (`HorizontalMoveList.tsx:70-73`). The preview is an opt-in `preview` prop that only `MobileTree` reads, so the Analysis callers (`AnalysisTabs.tsx:111`, the `VariationTreePanel` callers) are unaffected.

**Primary recommendation:** Three tasks: (1) pure preview and model helpers in `lib/` with unit tests, (2) the hook rework (a new `useRevealPreview` sub-hook plus forward/commit navigation in `useTrainRevealTree`), (3) the `VariationTree` preview mode, the Stockfish row, the board overlay, the chip "graded eval" label, and rewriting the affected tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
#### Seed design (locked, from SEED-197 "Design" items 1-9)
- Chip owns only its first move; chip eval stays frozen with a "graded eval" label/tooltip.
- Everything after the first move is a free node (analysis-board semantics: first-added child = main line, later = sidelines).
- Dimmed live preview at a leaf only; seeded from the grading PV at open; inherits the previous preview's remaining tail until the live search is deep enough.
- › / ArrowRight at a leaf commits the preview's next move instantly; tapping a preview token commits up to it. Committed nodes never change.
- No preview when the current node already has children (› follows last-visited child as today).
- Live eval badge (`formatScore` styling) leads the preview.
- Stockfish row: at a leaf shows lines 2..N only; elsewhere all N. Replaces `dropLineMove` / `allSecondary`.
- Playing a different move just commits it; previews are ephemeral and never persisted.
- No preview at mate/stalemate; `MAX_LINE_PLIES` caps only the preview, not committed nodes; snapshot / Analyze handoff persist committed paths only.

#### Mobile fit (open question 1)
- Clip the preview to ~6 plies on all viewports (named constant, e.g. `TRAIN_PREVIEW_MAX_PLIES = 6`) AND auto-scroll the move list so the current node stays visible.

#### Preview replacement depth (open question 2)
- Reuse the existing `TRAIN_LIVE_ALT_MIN_DEPTH = 10` (`frontend/src/lib/trainArrows.ts`) as the minimum live depth before a node's own PV replaces the inherited preview tail. No new depth constant.

#### Game chip search (open question 3)
- Keep the Game chip's reveal-time full-line search: it supplies the first-move eval and seeds the initial preview.

### Claude's Discretion
- How the preview render mode is added to `VariationTree` (prop shape, dim styling via existing theme tokens).
- Module seams for the preview state (pure helpers in `lib/` with unit tests preferred over hook-internal logic).
- Which Phase 237 known-line machinery to delete vs adapt, as long as the locked behavior holds and no dead code remains (knip must pass).

### Deferred Ideas (OUT OF SCOPE)
None listed in CONTEXT.md. Work happens only in the worktree `/home/aimfeld/Projects/Python/flawchess-seed197` (branch `quick/seed-197-live-engine-preview`). Frontend only, no backend change.
</user_constraints>

## Project Constraints (from CLAUDE.md / frontend/CLAUDE.md)

- No magic numbers: `TRAIN_PREVIEW_MAX_PLIES` must be a named constant; reuse `TRAIN_LIVE_ALT_MIN_DEPTH` (`lib/trainArrows.ts:171`, `export const TRAIN_LIVE_ALT_MIN_DEPTH = 10;`) [VERIFIED: lib/trainArrows.ts:171].
- `max-depth` 4 is enforced by `npm run lint` (`eslint.config.js:31`, `'max-depth': ['error', 4]`); cognitive complexity 15 is soft (`npm run lint:cognitive`).
- knip runs in CI: delete the exports you remove (see the deletion table below).
- `noUncheckedIndexedAccess`: narrow every `moves[i]` / `pvLines[0]`.
- `npm run lint` / `npm test` do not type-check. Run `npm run build` (tsc -b).
- `data-testid` goes on every interactive element (preview tokens are buttons). No SAN in test ids.
- `text-sm` is the minimum font size. The preview's eval badge must not use `text-xs` (EngineLines' `text-xs` is a scoped exception for that surface only).
- Theme colors come from `lib/theme.ts` (`BEST_MOVE_ARROW`, `STOCKFISH_BADGE_SECONDARY` already exist).
- Umami: skip high-frequency stepping (D-06), and never fire from an effect. Preview commits are stepping, so add **no new event** (`[ASSUMED]`, consistent with D-06).
- react-hooks 7 recommended config is on with `set-state-in-effect` off (`eslint.config.js:27`). Do not read refs during render. Use state plus an equality-guarded effect, the pattern `useTreeMoveGrading` already uses.
- Pre-merge gate (frontend part): `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|---|---|---|---|
| Preview resolution (seed / stored / live / inherit, clip, legality, terminal) | Browser, pure lib (`lib/trainRevealPreview.ts`, new) | — | Pure and unit-testable (CONTEXT discretion: pure helpers in lib) |
| Preview state + commit navigation | Browser hook (`hooks/useRevealPreview.ts` new, wired in `useTrainRevealTree`) | `useAnalysisBoard.playUciLine` | Hook owns ephemeral state; tree mutation via existing board API |
| Preview rendering | `VariationTree` (wrap / `MobileTree`) + `HorizontalMoveList` | `TrainMoveTreeList` (adapter) | Opt-in prop; Analysis callers untouched |
| Board arrows/markers | `TrainSolveScreen.resolveRevealBoardOverlay` | `lib/trainArrows.ts` | Existing single resolver |
| Persistence | `buildRevealTreeSnapshot` → sessionStorage cache | — | Committed nodes only; preview never in tree |

## Current Architecture: What Changes (symbol map)

All line numbers are in the worktree and were read this session.

### `frontend/src/lib/trainRevealLines.ts`

| Symbol | Lines | Today | Action |
|---|---|---|---|
| `MAX_LINE_PLIES = 12` | 45 | pre-load cap | **Delete/rename** → `TRAIN_PREVIEW_MAX_PLIES = 6` (display clip). Locked: caps only the preview. Store full PV tails, clip only at display, so the preview stays 6 long while you step through an inherited tail. Update the test at `trainRevealLines.test.ts:146`. |
| `ChipGroup.lineUcis` + `capLineUcis` | 75-77, 132-137, 225 | capped pre-load list | **Delete both.** The tree seeds `[chip.uci]`. The preview seed is `chip.line.moves.slice(1)` when `chip.line.moves[0] === chip.uci` (the same guard as `capLineUcis:135`). Tests at `trainRevealLines.test.ts:83,98,145-160,182,203,236,242` assert `lineUcis`; rewrite them. |
| `resolveChipLine`, `resolveChipPending`, `buildChipGroups` | 146-231 | chip model | Keep (chips still need `line` for the eval pill and the seed). |
| `walkLinePath`, `nodeUci`, `pathToNode` | 240-278 | | Keep (used by restore, `linePaths`, inheritance). |
| `classifyTreeNodes` | 306-322 | owner per node | Keep unchanged. With one-node `linePaths` it hands every continuation to its chip. |
| `buildTreeListView` | 341-354 | `mainLine = linePaths[active]` (whole pre-loaded line) | **Adapt:** `mainLine = [firstId, ...lowest-id child chain]`. Reuse the same "lowest id = first added" rule as `VariationTree.findLowestIdChild:393-402` (private there; add a lib twin or export it). |
| `resolveForwardTarget` | 375-412 | root → active chip's first node; below root → last-visited, then known-line next (`405-410`), then lowest id | **Adapt:** drop the `linePaths` known-line loop (405-410). Below the root it is `lastChild ?? first.id`. Remove the `linePaths` param except for the root case (`linePaths[activeChip]?.[0]`). |
| `RevealTreeSnapshot`, `buildRevealTreeSnapshot` | 430-467 | leaves not in `known`, iterated in `nodes.values()` (id) order | **Adapt leaf ORDER** (see Pitfall 1). The shape is unchanged, so the `trainRevealCache.ts:151-162` validator is untouched. `known` is now just the chip first-move nodes, so every committed continuation is persisted as a sideline path. That is the locked behavior. |

### `frontend/src/hooks/useTrainRevealTree.ts`

| Symbol | Lines | Action |
|---|---|---|
| `RevealChipLine { key; lineUcis }` | 74-77 | → `Pick<ChipGroup, 'key' \| 'uci' \| 'line'>` (`ChipGroup` still satisfies it at the `TrainSolveScreen.tsx:891-894` call site). |
| `RevealTreeStepInfo` + `deriveStepInfo` | 86-97, 223-245, 379-382 | **Delete.** Replace with `chipMove: { line: RoleKey; uci: string } \| null` (true when the current node is a chip's first move), which is all the overlay still needs for the first-move quality badge. |
| `chipsSignature` / `specs` | 287-290 | Sign `[key, uci]` only, so late line arrival no longer re-runs the graft. Seeds are derived separately from `chip.line`. |
| seeding effect | 325-328 | `graftLine([uci], null)` per chip. |
| restore effects | 335-362 | Keep. |
| `linePaths`, `owners` | 364-369 | Keep (one-node paths). |
| `knownIds` | 370-373 | Keep as "chip first-move nodes": `deleteLine` guard (502) and `isFreeNode` (553). See Open Question 1 for grading. |
| `listView` | 375-378 | Uses the adapted `buildTreeListView`. |
| `canGoForward` | 391-398 | `forwardTarget !== null \|\| previewIsCommittable` (the › button must be enabled at a leaf with a preview; the mobile bar reads `canGoForward` at `TrainSolveScreen.tsx:1434-1445`). |
| `latestRef` | 402-405 | Add `preview` (the currently SHOWN preview) and `nextId` is not needed (see the inheritance design). |
| `goForward` | 471-483 | `target ?? commit preview[0]` (see Commit-on-step). |
| `isOffLine` | 527, 158, 582 | **Delete** (its only consumer is `resolveRevealBoardOverlay`, plus tests). |
| engine block | 528-552 | Keep. Expose `pvLines` (already staleness-guarded) to the preview sub-hook. |
| new return fields | — | `preview: RevealPreviewView \| null`, `commitPreview(plies: number)`, `chipMove`. |

### `frontend/src/components/train/TrainMoveTreeList.tsx`

- `TrainStockfishRow` (48-86): `dropLineMove` (24, 65) and `allSecondary={step !== null}` (77) go. New rule: when `tree.preview` is shown at the current node, `rows = pvLines.slice(1, sfLines)` rendered as ranks 2..N, else `pvLines` (all N). If `sfLines <= 1` at a leaf, render no row content.
- `allSecondary` is a prop on `EngineLines` (`EngineLines.tsx:240,252,265,280,411,443`). **Replace it with `rankOffset?: number`** (default 0). Then the badge is solid only when `lineIndex + rankOffset === 0`, `aria-label` reads the true rank (`Line ${lineIndex + rankOffset + 1}`), and testids can stay index-based. Rewrite `EngineLines.test.tsx:327`.
- `VariationTree` call (103-113): add the `preview` prop.
- The row stays hidden at the root (`!tree.isAtRoot`, line 115).

### `frontend/src/components/train/TrainSolveScreen.tsx`

- `RevealBoardOverlayInput.tree` Pick (296-299) drops `isOffLine` and `stepInfo` and adds `chipMove` and `preview`.
- `resolveRevealBoardOverlay` (321-362), new branch order:
  1. Root: unchanged (`buildChipFocusOverlay`, 355-361).
  2. Below the root, arrows = `previewNext !== null ? buildTrainStepOverlayArrows(previewNext, pvLines, sfArrows) : buildTrainFreePlayArrows(pvLines, sfArrows)`, where `previewNext` = the shown preview's first move when its anchor is the current node. The solid blue pointer is then always "what › commits". Once the preview is live, `previewNext === pvLines[0].moves[0]` and `stepLiveArrows` filters it, so the result equals free-play arrows.
  3. Markers: on `chipMove`, `buildTrainStepMarkers(uci, chipQuality, true)` plus `TRAIN_STEP_HIGHLIGHT[quality]` (today's first-move branch, 343-349, kept). Otherwise `tree.boardMarkers` / `tree.lastMoveColor` (today's off-line branch, 331-337). The fallback at 352-354 disappears.
- `offLineArrows` memo (1535-1538) stays (it is the non-preview arrow set).
- Analyze handoff `revealTree.snapshot()` (1653) is unchanged.

### `frontend/src/lib/trainArrows.ts`

- `dropLineMove` (291-298): **delete** along with its tests (`trainArrows.test.ts:10,616-638`). It has no other consumer (grep).
- `buildTrainStepOverlayArrows` / `buildTrainStepArrows` / `stepLiveArrows` (274-350): **keep**, now keyed on the preview's next move. Update the doc comments ("known line" → "preview").
- `buildTrainStepMarkers` (394-403): keep (chip first move).

### `frontend/src/hooks/useTreeMoveGrading.ts`

There is no structural change. It grades every node where `isFreeNode(id)` is true (`currentQuality`, ~lines 219-262) and persists per node. Committed preview moves would therefore be graded and badged unless they are excluded (Open Question 1).

## Preview Model (recommended design)

### Data

```ts
// lib/trainRevealPreview.ts (new) — pure
export const TRAIN_PREVIEW_MAX_PLIES = 6;
export interface PreviewLine { ucis: string[]; evalCp: number | null; evalMate: number | null } // white-POV
export interface RevealPreviewView {
  anchorId: NodeId;                 // node the preview hangs from
  steps: { uci: string; san: string }[]; // legal prefix, clipped to TRAIN_PREVIEW_MAX_PLIES
  evalCp: number | null; evalMate: number | null;
  isLive: boolean;
}
```

`TrainEngineLine` is `{ moves: string[]; evalCp; evalMate }` with white-POV evals (`hooks/trainGradingSupport.ts:124-128`) [VERIFIED]. `PvLine` is `{ multipv; depth; moves; evalCp; evalMate }`, also white-POV (`hooks/uciParser.ts:14-24`) [VERIFIED]. So seeds and live lines map directly onto `PreviewLine`.

### Anchor rule (`resolvePreviewAnchor`)

- If the current node is a leaf (no children), the anchor is the current node.
- If the current node is the **root** (puzzle position) and the active chip's first-move node is a leaf, the anchor is that chip node. This is the "at open it is seeded, so the reveal looks as full as today" case: the board sits on the puzzle position while the list shows `1. e4 (dim: e5 2. Nf3 …)`. `[ASSUMED]`: the seed (items 3 and 5) does not spell out the root case. Without it the list at open would show a lone first move, which contradicts item 3.
- Otherwise (the current node has children) there is no preview (item 5).
- There is no preview when `terminalPositionEval(anchorFen) !== null` (`lib/liveFlaw.ts:53-68`, which returns non-null for checkmate and any draw) [VERIFIED: lib/liveFlaw.ts:53-68].

### Resolution order (`resolvePreviewLine`)

1. **live**: only when `anchorId === currentNodeId`, `engineIsCurrent`, `pvLines[0]` exists, `pvLines[0].depth >= TRAIN_LIVE_ALT_MIN_DEPTH`, **and** its first move is legal from the anchor FEN. Use the line's own `depth`, as `buildTrainLiveAlternatives` does (`trainArrows.ts:619`).
2. **stored[anchor]**: the last deep live PV recorded for this node.
3. **seed[anchor]**: when the anchor is a chip's first-move node and `chip.line.moves[0] === chip.uci`, use `{ ucis: line.moves.slice(1), eval: line eval }`.
4. **inherited**: walk up the parents to the nearest ancestor A that resolves (by steps 2-3, applied recursively) and check that the UCI path from A down to the anchor (`nodeUci`) is a prefix of A's `ucis`. If it is, use `ucis.slice(pathLength)`. Bound the walk by the path length.
5. Otherwise null (until live reaches depth 10).

Then replay from the anchor FEN to get SANs, keep the **legal prefix**, and clip to `TRAIN_PREVIEW_MAX_PLIES`. Reuse `replayPvLine` (`components/analysis/EngineLines.tsx:60`, exported for reuse; `lib/trainArrows.ts` already imports from components). Store full tails and clip only at display.

### State (`hooks/useRevealPreview.ts`)

- `stored: Map<NodeId, PreviewLine>`, keyed to the tree like `qualityState` in `useTreeMoveGrading` (`{ key: resetKey, map }`, reset per puzzle by key mismatch).
- One effect: when step 1 (live) qualifies at the current leaf, write `stored[current]`, guarded by equality on `ucis.join()` plus the eval. Depth ≥ 10 updates arrive about 5-10 times per 1.5 s search, the same churn as `setEvalByFen`.
- Seeds are derived at render from the chips plus `linePaths` and are never stored, so a late-arriving Move or Game line updates the preview without touching committed nodes.
- **Why this gives "inherit the previous preview's tail" for free:** after › commits `m1`, the new node has no entry, so its parent (which has the stored or seeded preview `[m1, m2, …]`) is matched and the node shows `[m2, …]`. That holds until its own live PV reaches depth 10. When you jump elsewhere, a leaf with no stored entry and a non-matching path shows nothing until live. A revisited leaf shows its last stored live PV at once. Committed nodes never change; only the derived display does.

### Eval badge

- If the anchor is the current node, show the eval bar's reading, i.e. `resolveTrainEvalBarReading(fen, evalReading)` (`TrainSolveScreen.tsx:272-278`). Fall back to the preview's own eval while the engine is at depth 0.
- At the root anchor case (the engine is on the puzzle position, not the anchor), show the preview's own (seed) eval.
- Render with `formatScore` (`EngineLines.tsx:185-200`) in a pill with `BEST_MOVE_ARROW` background and white text, **`text-sm`**, testid `variation-preview-eval`.
- The chip pill uses the same color (`TrainLineChips.tsx:49-55`). Give `ChipEval` `title="Graded eval"` and `aria-label={`Graded eval ${score}`}` so the two are not confused (locked item 1). A Radix tooltip inside the chip `<button>` would nest an interactive element, so prefer `title` plus `aria-label` [ASSUMED].

## Commit-on-step Navigation

- `useAnalysisBoard.playUciLine(uciMoves)` (`useAnalysisBoard.ts:661-701`) plays relative to `prev.currentNodeId` inside a functional `setState`, reuses existing children by from/to, lands on the end and sounds through the move-sound effect. `graftLine` (713-747) is non-navigating. `nextId` is exposed (810). [VERIFIED]
- **`commitPreview(plies)`** (in the hook):
  1. Read `latestRef.current.preview` (the preview **currently shown**).
  2. Guard: bail if it is null, or if `anchorId !== live.currentNodeId` and this is not the root-anchor case.
  3. `prefix = anchorId === currentNodeId ? [] : [nodeUci(anchor)]` (root case: the chip move first).
  4. Call `boardPlayUciLine([...prefix, ...preview.steps.slice(0, plies).map(s => s.uci)])`.
  5. Call `onUserStepRef.current?.()`. It is stepping, not a fork: count it like today's known-line steps (`review_line_steps`) and do not send `train-sideline-fork`.
- `goForward` = `resolveForwardTarget(...)` if non-null, else `commitPreview(1)`. A token tap calls `commitPreview(i + 1)`.
- **Rapid ›:** React flushes discrete-event renders and their passive effects synchronously, so the after-commit `latestRef` sync is fresh by the next keydown. This is the same assumption today's `goForward` already relies on [ASSUMED: React 18+ discrete-event effect flushing]. The anchor guard makes a stale ref a no-op rather than a wrong move. `playUciLine` breaks on an illegal UCI (683), so the worst case is a no-op.
- ArrowRight / ArrowLeft / Home already route to the hook's `goForward` / `goBack` / `goToRoot` through `useBoardNavigationInput` (`useTrainRevealTree.ts:567-572`). The mobile bar uses `revealGoForward` (`TrainSolveScreen.tsx:917, 1439-1444`). No wiring change is needed beyond `canGoForward`.
- `playMove` (423-441) and `playLine` (443-452) are unchanged. Optional: report `forked: false` when a board move equals `preview[0]`, mirroring today's "a move onto a known line is not a fork" (test `TrainSolveScreen.test.tsx:2938, 2988`) [ASSUMED].

## VariationTree Preview Mode

- `variant="wrap"` → `MobileTree` (`VariationTree.tsx:1107-1118`, 717-782) → `HorizontalMoveList`. `DesktopTree` is never used by Train, so implement the prop only in `MobileTree` and document that it is wrap-only.
- **Auto-scroll already exists:** `HorizontalMoveList.tsx:70-73` calls `scrollIntoView({block:'nearest', behavior:'smooth'})` keyed on the current item. Preview tokens are never `isCurrent`, so the current node stays in view and only the preview may clip, which is the locked behavior. Note: `scrollIntoView` can also scroll ancestors, a known issue the DesktopTree fixed (`VariationTree.tsx:159-184`). This is existing behavior and out of scope.
- `HorizontalMoveItem` already has `dimmed` (31-32, which adds `text-muted-foreground` when not current, line 112). **Add two optional fields** (additive, so the `board/MoveList.tsx` and `bots/MoveListPanel.tsx` callers are unaffected):
  - `onSelect?: () => void`: a per-item click override. Preview tokens are not nodes; `onMoveClick(ply)` passes node ids.
  - `after?: ReactNode`: rendered as a sibling **after** the `<button>`. Today `trailing` renders **inside** the button (118-119), and a sideline's `×` delete button is already nested inside a move button (`VariationTree.tsx:678-697`). Moving the closing `)` and `×` behind a preview needs a non-button slot.
  - `leading?: ReactNode` before the number label, for the eval badge. Alternatively, render the badge as part of the first preview item's `numberLabel` slot.
- Prop shape:
  ```ts
  preview?: { anchorId: NodeId; sans: string[]; evalLabel: string | null; onTokenClick: (index: number) => void } | null;
  ```
- Insertion:
  - Main-line anchor: in `mainLine.forEach` (747-771), after pushing the anchor's item, push the preview items. The anchor is a leaf, so no sibling block attaches after it.
  - Sideline anchor: the anchor is necessarily the **tail of its block's chain** (the chain follows the lowest-id child to a leaf, 456-461). In `siblingBlockToChips` (657-715), when `block.chain.at(-1) === preview.anchorId`, give the last real item only its marker and give the last preview item `after = ')' + ×`. Put the preview items in a helper (`previewToChips(preview, startPly, closing)`) to respect max-depth 4.
  - Numbering: `startPly = plyFromFen(anchor.fen)` (382-390), with labels from `moveLabel(startPly, i)` (`lib/moveNumberLabel.ts:10-15`). A black-first preview needs the `N...` label on token 0. `moveLabel` already returns `N...` for black; `MobileTree` passes `null` for black moves, so give preview token 0 an explicit label when black.
  - Test ids: `variation-preview-${i}` (index, no SAN) and `variation-preview-eval`. Existing `[data-testid^="variation-node-"]` queries (e.g. `TrainSolveScreen.test.tsx:157` `tapListMove`) then never see preview tokens.

## Analyze Handoff / Restore

- `buildRevealTreeSnapshot` persists `currentPath` plus every leaf not in `known`. With `known` reduced to the chip nodes, **all committed paths persist**, and the preview is never in `nodes`, so it is never persisted. The cache (sessionStorage, `trainRevealCache.ts:12, 63`) validates the shape with caps; no change is needed.
- Restore grafts paths in array order (`useTrainRevealTree.ts:344-348`). After a restore the preview regenerates: seeds at chip nodes, inheritance down matching paths, live at the current leaf.
- `analyzeTo` carries no tree (`TrainSolveScreen.tsx:951-957`). `currentPathUcis` has no non-test consumer.

## Common Pitfalls

### Pitfall 1: Restore flips the main line (snapshot leaf order)
**What goes wrong:** `buildRevealTreeSnapshot` emits leaves in leaf-id order (`nodes.values()`, 460-465). Example: commit `e5`(1) and `Nf3`(2), step back to `e5`, play `Bc4`(3), return and commit `Nc6`(4). The snapshot then holds `[e4,e5,Bc4]` before `[e4,e5,Nf3,Nc6]`, so on restore `Bc4` gets the lower id under `e5` and becomes the main line. Today this is masked because the main line was pre-loaded.
**Avoid:** Emit leaves in DFS pre-order with children visited lowest id first. Add a unit test: round-trip a snapshot through a fresh tree and assert the `buildTreeListView` main line is identical.

### Pitfall 2: Live PV from the wrong position, or illegal
**What goes wrong:** `useStockfishEngine.currentFen` lags `fen` by one render (`useStockfishEngine.ts:87-97`). The test FakeWorker returns the same `pv` for every position at depth 10 (`TrainSolveScreen.test.tsx:339, 349-372`), and the hook test mock returns `moves: ['a7a6']` at depth 10 (`useTrainRevealTree.test.ts:69-84`).
**Avoid:** Use the already-guarded `pvLines` (`useTrainRevealTree.ts:539-540`). Use live only when anchor = current node **and** the first move is legal. If it is not legal, fall back to stored, seed or inherited.

### Pitfall 3: Flicker and stale preview on fast ›
Commit from the **shown** preview (`latestRef.preview`), never from recomputation. Committed nodes are real tree nodes, so stepping back shows them unchanged. The preview only appears at leaves, so step-back never flickers a preview.

### Pitfall 4: Committed engine moves get graded and badged
`useTreeMoveGrading` badges every free node (list icon plus board badge). Fast stepping grades with shallow parent and child evals and persists the result. See Open Question 1.

### Pitfall 5: Stockfish row rank colors and labels
Slicing `pvLines.slice(1)` makes rank 2 render as `lineIndex 0`, drawn solid blue and labelled "Line 1" (`EngineLines.tsx:279-290`). Use `rankOffset`.

### Pitfall 6: Root-anchor commit must include the chip move
At the root, the anchor is the chip node, so a tap on preview token i must play `[chipUci, ...preview[0..i]]`. `playUciLine` reuses the existing chip child.

### Pitfall 7: Mate and stalemate
There is no preview at a terminal anchor. A PV can also end in mate: replay stops naturally (the legal prefix).

### Pitfall 8: knip, max-depth and complexity
Delete `MAX_LINE_PLIES` (or rename it), `capLineUcis`, `ChipGroup.lineUcis`, `RevealTreeStepInfo`, `deriveStepInfo`, `isOffLine`, `dropLineMove`, and the `allSecondary` prop. `useTrainRevealTree` (606 lines) is already over guidance, so put the preview in `useRevealPreview` (new file) rather than inline. Keep `MobileTree` and `siblingBlockToChips` additions in helpers.

### Pitfall 9: Board arrows when `sfArrows === 0`
`buildTrainStepOverlayArrows` always pushes the primary pointer, whatever `count` is (`trainArrows.ts:344-350`). That matches today's stepped-line behavior. Keep it (the pointer is the › target) [ASSUMED].

## Existing Tests: Breakage Map

| File | Lines (approx.) | Impact |
|---|---|---|
| `lib/__tests__/trainRevealLines.test.ts` (583) | 83-160, 182-242 (`lineUcis`, `MAX_LINE_PLIES`), 360-404 (`buildTreeListView`), 405+ (`resolveForwardTarget`), snapshot tests | Rewrite: first-move-only chips, lowest-id main line, forward without the known-line rule, DFS snapshot order |
| `hooks/__tests__/useTrainRevealTree.test.ts` (1180) | 92-94 fixtures (`lineUcis`), 133-272 seeding/late lines/cap, 273-321 forward, 359/413/724/1007-1084 `isOffLine`, 586-626 `stepInfo`, 691+ restore, 1133+ fork counting | Heavy rewrite. Fixture becomes `{key, uci, line}`. Add preview and commit tests. Mock engine: add configurable `depth` and `pvMoves` fields (default depth 10 plus `a7a6` means live instantly replaces a seed wherever `a7a6` is legal) |
| `components/train/__tests__/TrainMoveTreeList.test.tsx` (184) | 107-131 tracer (mostly still valid: `e5`/`Nf3` become preview tokens, and a tap commits up to them), 133-167 (`dropLineMove` behaviour) | Rewrite 144-167 for the lines-2..N rule. Keep 169-183 |
| `components/train/__tests__/TrainSolveScreen.test.tsx` (4992) | ~1431-1600 stepped-line overlay/pointer/secondaries, ~2322-2335 and 2584-2715 sf-row/off-line arrows, ~2938-3060 known-line "not a fork", ~3200-3220 ArrowRight steps, ~4463-4592 restored tree | Update the expectations. FakeWorker returns a constant `pv` at depth 10, so live replaces seeds when legal |
| `components/analysis/__tests__/EngineLines.test.tsx` | 327 (`allSecondary`) | Rewrite for `rankOffset` |
| `lib/__tests__/trainArrows.test.ts` | 10, 616-638 (`dropLineMove`) | Delete. Keep 535-611 (`buildTrainStepOverlayArrows`) |
| `components/analysis/__tests__/VariationTree.test.tsx` (764) | 239 (wrap) | Add preview-mode tests: main-line end, inside sideline parens, token click, no preview prop means unchanged output |
| `TrainReveal.test.tsx`, `TrainSolveScreen.restoredGameArrow.test.tsx` | — | Likely unaffected (chip render / root overlay); run them |

New pure tests (`lib/__tests__/trainRevealPreview.test.ts`):
- the anchor rule (leaf, root+chip leaf, has-children → null, terminal → null)
- resolution precedence (live depth 9 vs 10, live illegal → fallback, stored over seed)
- inheritance after 1 and after 3 committed plies, and a mismatched path → null
- clip to 6 and legal prefix
- the DFS snapshot order round trip

## Code Examples

```ts
// Seed guard reused from capLineUcis (trainRevealLines.ts:134-137)
function chipSeed(chip: { uci: string; line: TrainEngineLine | null }): PreviewLine | null {
  if (chip.line === null || chip.line.moves[0] !== chip.uci) return null;
  return { ucis: chip.line.moves.slice(1), evalCp: chip.line.evalCp, evalMate: chip.line.evalMate };
}

// Live candidate (TRAIN_LIVE_ALT_MIN_DEPTH = 10, trainArrows.ts:171)
const top = pvLines[0];
const live = top !== undefined && top.depth >= TRAIN_LIVE_ALT_MIN_DEPTH
  ? { ucis: top.moves, evalCp: top.evalCp, evalMate: top.evalMate } : null;
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | At the puzzle position the preview hangs from the active chip's first move while that node is a leaf | Anchor rule | If the owner wants no preview at the root, the list at open shows only the first move (contradicts "looks as full as today") |
| A2 | Committed preview moves are not graded (see OQ1) | Open Questions | Badge noise or spurious mistake marks on engine moves, or a loss of grading the owner wanted |
| A3 | The badge shows the eval-bar reading when anchor = current, else the seed eval | Eval badge | A badge at the root that mirrors the chip eval could confuse users |
| A4 | A preview commit counts as a step (`onUserStep`), with no Umami event | Commit | Telemetry semantics for `review_line_steps` / `explored` |
| A5 | A board move equal to `preview[0]` reports `forked: false` | Commit | Fork-count telemetry, and tests at ~2988 |
| A6 | React flushes passive effects of discrete events synchronously (`latestRef` is fresh per keypress) | Commit | Rare dropped ›. The guard makes it a no-op |
| A7 | `title`/`aria-label` on the chip eval satisfies the "graded eval" label | Eval badge | No hover on phones; may need visible text |

## Open Questions

1. **Grade committed preview moves?**
   - Known: today, known-line continuations are ungraded and get a neutral 'good' highlight (`TrainSolveScreen.tsx:341-349`), while user moves and Stockfish-row clicks are graded (`useTreeMoveGrading`).
   - Unclear: the spec says "everything after the first move is a free node", but grading engine-committed moves puts a `best` icon on nearly every main-line move, and a fast-› step can persist a shallow-eval "mistake" on an engine move.
   - Recommendation: do not grade preview commits. Keep a `previewCommittedIds: Set<NodeId>` in hook state (keyed to the tree); `commitPreview` computes the landing ids from `findChildBySquares` or `nextId + k` on the latest nodes; `isFreeNode` excludes them. The trade-off: after a restore those nodes are graded on visit, which is acceptable. Confirm with the owner.
2. **Tour copy:** "Step through the focused line with ‹ ›…" (`lib/trainBotCopy.ts:647-650`) still reads correctly. A mention of the dimmed engine preview is optional and not required by the seed.

## Environment Availability

Step 2.6 skipped: there are no external dependencies. The work is frontend code and tests only (node v24.19.0 and `frontend/node_modules` are present, and a baseline `vitest run` of two affected files passed 43/43 this session).

## Validation Architecture

| Property | Value |
|---|---|
| Framework | vitest 5 (`frontend/package.json` `"test": "vitest run"`) |
| Quick run | `cd frontend && npx vitest run src/lib/__tests__/trainRevealPreview.test.ts src/lib/__tests__/trainRevealLines.test.ts src/hooks/__tests__/useTrainRevealTree.test.ts src/components/train/__tests__/TrainMoveTreeList.test.tsx src/components/analysis/__tests__/VariationTree.test.tsx` |
| Full suite | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

| Behavior | Test type | Where |
|---|---|---|
| Anchor, precedence, inheritance, clip, terminal | unit (pure) | `trainRevealPreview.test.ts` (new, Wave 0) |
| Lowest-id main line, forward target, DFS snapshot order | unit | `trainRevealLines.test.ts` |
| › commits `preview[0]`; token tap commits N plies; root-anchor commit includes the chip move; stepping back shows committed nodes; no preview with children | hook | `useTrainRevealTree.test.ts` (mock depth/pv configurable) |
| Preview tokens render dimmed after the main-line leaf and inside sideline parens; click → `onTokenClick(i)`; no prop → identical | component | `VariationTree.test.tsx` |
| Row shows lines 2..N at a leaf with a preview, all N elsewhere | component | `TrainMoveTreeList.test.tsx`, `EngineLines.test.tsx` |
| Board pointer = preview next; chip first-move badge | integration | `TrainSolveScreen.test.tsx` |

Wave 0 gaps: `src/lib/__tests__/trainRevealPreview.test.ts` (new), plus configurable `depth`/`pvMoves` in the `useTrainRevealTree.test.ts` engine mock.

## Security Domain

Minimal. There is no new input surface. The snapshot shape is unchanged and still cap-validated (`trainRevealCache.ts:144-162`, T-237-05/T-237-16). The preview never reaches grading, scoring or the solve POST. Before the verdict, chips are empty (`TrainSolveScreen.tsx:829-833`, T-237-07), so no seed exists pre-verdict.

## Recommended Seam Split

1. **Task 1, pure lib + tests:** new `lib/trainRevealPreview.ts` (`TRAIN_PREVIEW_MAX_PLIES`, `resolvePreviewAnchor`, `resolvePreviewLine`, `previewSteps` through `replayPvLine`). `trainRevealLines.ts`: drop `lineUcis`/`capLineUcis`/`MAX_LINE_PLIES`, adapt `buildTreeListView` (lowest-id chain) and `resolveForwardTarget`, DFS snapshot order. Delete `dropLineMove`. Write the unit tests.
2. **Task 2, hooks:** new `useRevealPreview` (stored-map state, live-store effect, seeds, resolved view). `useTrainRevealTree`: first-move seeding, `chipMove` in place of `stepInfo`, delete `isOffLine`, `commitPreview`, `goForward` fallback, `canGoForward`, optional grading exclusion (OQ1). Rewrite the hook tests.
3. **Task 3, UI:** `HorizontalMoveItem` (`onSelect`/`after`/`leading`), the `VariationTree` `preview` prop (MobileTree only), the `TrainMoveTreeList` row rule plus `EngineLines` `rankOffset`, `resolveRevealBoardOverlay`, the chip "graded eval" label. Update the component/integration tests and run the full frontend gate.

## Sources

Primary (HIGH, read this session in the worktree): `lib/trainRevealLines.ts`, `hooks/useTrainRevealTree.ts`, `components/train/TrainMoveTreeList.tsx`, `components/analysis/VariationTree.tsx`, `components/board/HorizontalMoveList.tsx`, `components/train/TrainSolveScreen.tsx` (270-362, 800-940, 1400-1660), `lib/trainArrows.ts` (160-410), `hooks/useTreeMoveGrading.ts`, `hooks/useAnalysisBoard.ts` (225-424, 655-827), `hooks/useStockfishEngine.ts` (60-98, 697), `hooks/uciParser.ts` (14-24), `hooks/trainGradingSupport.ts` (117-128), `components/analysis/EngineLines.tsx` (40-100, 175-330), `components/train/TrainLineChips.tsx`, `lib/liveFlaw.ts` (53-68), `lib/trainRevealCache.ts` (140-162), `lib/trainBotCopy.ts` (595-700), test harnesses in `useTrainRevealTree.test.ts`, `TrainSolveScreen.test.tsx`, `TrainMoveTreeList.test.tsx`.

## Metadata

- Code map: HIGH. Design recommendations: MEDIUM (A1-A7 need confirmation, A2 most of all).
- Valid until: the next change to `useTrainRevealTree` / `VariationTree`.
