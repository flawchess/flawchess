---
phase: quick-260703-kyb
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useAnalysisBoard.ts
  - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
autonomous: true
requirements: [QUICK-260703-kyb]
must_haves:
  truths:
    - Every sideline the user creates (free-move fork or tactic PV) stays visible in the move list as a flat sibling; navigating away and back does NOT hide or delete it.
    - Two different tactic chips can be open simultaneously as sibling lines; clicking a chip again removes only that line.
    - Free-move sibling lines carry a per-line "×" delete control (both desktop and mobile); tactic lines close via their chip toggle only.
    - Deleting a sibling while the board is inside it recovers the board to that sibling's fork parent, not the mainline root.
    - The behavior is identical on the mobile move-list (MobileTree / HorizontalMoveList) and the desktop DesktopTree — one indent level, no recursive nesting, no promote-to-mainline.
  artifacts:
    - frontend/src/hooks/useAnalysisBoard.ts (multi-line state: pvNodeIds set, deleteSubtree, clearAllSidelines)
    - frontend/src/components/analysis/VariationTree.tsx (buildSiblingBlocks flat renderer + × affordance)
    - frontend/src/pages/Analysis.tsx (openLines map, focused-line overlays)
  key_links:
    - insertPvLine must UNION grafted ids into pvNodeIds (never clobber a prior open line)
    - deleteSubtree(rootId) is the single delete op behind both the free-move × and the tactic chip toggle-off
    - liveFlawActive gate ("not main, not PV") must still hold with multiple PV lines via pvNodeIds membership
---

<objective>
Fix the analysis-page move list so every line the user creates persists as a flat, always-visible sibling — matching chess.com/lichess — instead of the current singleton behavior where creating a new line silently deletes/hides the previous one and free-move forks vanish when you navigate away.

Scope is FLAT SIBLINGS ONLY: one indent level, no recursive nesting, no promote-to-mainline. Tactic PV lines become ordinary siblings toggled by their chip; free-move lines get a per-line "×" delete. Mobile parity is mandatory. Frontend only — no backend, no data-model change (the flat `Map<NodeId, MoveNode>` with `parentId` already stores unlimited branches; the singleton behavior is a rendering + tracking decision).

Purpose: The move list is the primary navigation surface of the analysis board; losing sidelines on navigation makes multi-line exploration impossible.
Output: Multi-line move tree rendering + toggle/delete affordances across desktop and mobile, with updated unit tests.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

@frontend/src/hooks/useAnalysisBoard.ts
@frontend/src/components/analysis/VariationTree.tsx
@frontend/src/components/board/HorizontalMoveList.tsx
@frontend/src/pages/Analysis.tsx
@frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
@frontend/src/components/analysis/__tests__/VariationTree.test.tsx
@frontend/src/lib/theme.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Multi-line state in useAnalysisBoard.ts (pvNodeIds set, deleteSubtree, clearAllSidelines)</name>
  <files>frontend/src/hooks/useAnalysisBoard.ts, frontend/src/hooks/__tests__/useAnalysisBoard.test.ts</files>
  <behavior>
    - insertPvLine grafts a line AND unions its node ids into a `pvNodeIds` membership set WITHOUT removing any previously grafted line's ids (open two lines off different forks → both remain in nodes and in pvNodeIds).
    - isOnPvLine(id) reflects `pvNodeIds.has(id)` and stays true for every open line's nodes simultaneously.
    - deleteSubtree(rootId) removes rootId and all its descendants from `nodes`, drops those ids from `pvNodeIds`, and if currentNodeId was inside the deleted subtree recovers currentNodeId to rootId's parentId (the fork parent), else leaves currentNodeId unchanged. Deleting only ONE of two open lines leaves the other intact.
    - clearAllSidelines() removes every node NOT in mainLine, empties pvNodeIds, and recovers currentNodeId to its nearest mainLine ancestor (or null at root).
    - makeMove off a PV node still creates a child NOT in pvNodeIds (a free-move sub-fork is a deletable sibling, not part of the tactic line).
    - goForward from a fork node steps INTO the sideline: prefer the lowest-id child that is in pvNodeIds; otherwise the lowest-id child overall.
  </behavior>
  <action>
Replace the single `pvLine: NodeId[]` in `AnalysisBoardState` and the public return with a `pvNodeIds: Set<NodeId>` membership set (initial empty set in makeInitialState and loadMainLine's reset). Keep `nextId` and ADD it to the public `AnalysisBoardReturn` so Analysis.tsx can snapshot the id that the next graft will assign to a line root (used for open-line tracking).

Rework `insertPvLine(pvSans, forkNodeId)`: keep the single-setState batch-build loop exactly as-is for grafting new nodes onto a copy of the map and parking currentNodeId at forkNodeId, but instead of REPLACING state with a fresh `pvLine`, UNION the newly created ids into a copy of `prev.pvNodeIds`. It must not touch or delete any pre-existing pvNodeIds. The line root is the node whose id equals `prev.nextId` at call time (first id assigned) — do not change that assignment order.

Replace `clearPvLine()` with two operations:
  1. `deleteSubtree(rootId: NodeId)`: in a functional setState, compute the deleted id set = rootId plus all transitive descendants (iterate prev.nodes following parentId membership, e.g. repeatedly collect nodes whose parentId is already in the deleted set until it stops growing). Build a new nodes Map without those ids, a new pvNodeIds without those ids. Recover currentNodeId: if prev.currentNodeId is in the deleted set, set it to `prev.nodes.get(rootId)?.parentId ?? null` (the fork parent — generalizes the old clearPvLine recovery to the deleted subtree's parent, per the explore finding); otherwise keep prev.currentNodeId. No-op (return prev) when rootId is absent.
  2. `clearAllSidelines()`: in a functional setState, keep only mainLine nodes, empty pvNodeIds, and if currentNodeId is non-null and not on mainLine walk parentId up to the nearest mainLine node (or null) exactly like the old clearPvLine recovery loop. Used by Reset.

Update `goForward`: drop the `pvLine[0]` special case. When the node has children, prefer the lowest-id child that is in `pvNodeIds` (step into an open sideline when parked at its fork); else fall back to `findFirstChild`. Keep the existing null/no-child no-ops.

Update `isOnPvLine` to read `stateRef.current.pvNodeIds.has(nodeId)`. Remove the now-dead `pvLine` field, `clearPvLine`, and the `pvLine`-based branch in goForward from the return contract and the interface doc comments. Update the file header comment bullets that describe pvLine to describe pvNodeIds + flat siblings.

Update the test file `useAnalysisBoard.test.ts`: rewrite the pvLine/clearPvLine/Level-2 behaviors (currently items 5–7) to the new API — assert insertPvLine unions ids (open two lines off two forks, both isOnPvLine true; mainLine unmutated), deleteSubtree removes exactly one line's ids and recovers currentNodeId to the fork parent when inside it, clearAllSidelines strips all non-mainLine nodes, goForward-into-sideline still holds, and makeMove off a PV node yields a node with isOnPvLine=false. Keep all unrelated existing tests passing.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/hooks/__tests__/useAnalysisBoard.test.ts</automated>
  </verify>
  <done>useAnalysisBoard exposes pvNodeIds, nextId, insertPvLine (unioning), deleteSubtree, clearAllSidelines; the hook test suite passes green with the rewritten multi-line behaviors and no reference to the removed pvLine/clearPvLine API.</done>
</task>

<task type="auto">
  <name>Task 2: Multi-line tracking + focused-line overlays in Analysis.tsx</name>
  <files>frontend/src/pages/Analysis.tsx</files>
  <action>
Replace the singleton `activePvFlaw` with a Map of open lines. Add state `openLines: Map<string, { rootNodeId: NodeId; ply: number; orientation: 'missed' | 'allowed' }>` keyed by `flawKey = \`${ply}:${orientation}\``, and a transient `pendingFlaw: { ply; orientation } | null` (the line currently being opened, awaiting its PV fetch — only one open action is in flight at a time since clicks are sequential).

Destructure the new hook API: `pvNodeIds`, `nextId`, `deleteSubtree`, `clearAllSidelines` (drop `pvLine`, `clearPvLine`).

Fetch: keep the single `useTacticLines(gameId, focusedOrPendingPly, enabled)`. Compute `fetchFlaw = pendingFlaw ?? focusedFlaw` (see below) and pass its ply; enabled when `fetchFlaw != null && isGameMode`. React-query caches per (gameId, ply), so re-focusing an already-opened line is a cache hit.

focusedFlaw: derive the open line the board is currently "in" — the entry in `openLines` (or `pendingFlaw`) whose subtree contains `currentNodeId`, OR whose fork node equals `currentNodeId` (so the depth arrow shows while parked at a just-opened line's fork). Prefer `pendingFlaw` when set. Fork node for a flaw is `mainLine[forkPlyForOrientation(ply, orientation)]` (unchanged helper). Subtree containment: walk parentId up from currentNodeId; if it reaches the line's rootNodeId it is inside. Null when the board is on the main line or a free move.

focusedPvLine: the ordered node array of the focused line — walk children from `focusedFlaw.rootNodeId` following the lowest-id child chain until it leaves pvNodeIds. This REPLACES the old `pvLine` array as the input to the existing overlay memos (`contextualCurrentPly = focusedPvLine.indexOf(currentNodeId) + 1`, `sidelineNodeColors` iterating `focusedPvLine[i]`, `pvSidelineArrows` using `focusedPvLine[stepIntoPv]`, `contextualOnStoredLine = isOnPvLine(currentNodeId)`). Rewire those memos to read `focusedFlaw` in place of `activePvFlaw` and `focusedPvLine` in place of `pvLine`. Behavior for the line you are in is unchanged; other open lines simply render in the list without a board arrow.

Open/graft effect: when `pendingFlaw != null` and `contextualTacticData` for it has arrived and the line is not already in `openLines`, compute `pvMoves` (missed → missed_moves; allowed → allowed_moves.slice(1)) and `forkNodeId` exactly as today. Snapshot `rootNodeId = nextId` BEFORE calling `insertPvLine(pvMoves, forkNodeId)` (the hook assigns the root that id). Then record the line: `setOpenLines(prev => new Map(prev).set(flawKey(pendingFlaw), { rootNodeId, ply, orientation }))` and clear `pendingFlaw`. Guard: only when `forkNodeId !== undefined && pvMoves.length > 0`.

handlePvChipClick(nodeId, flaw): compute key. If key ∈ openLines → toggle OFF: `deleteSubtree(openLines.get(key)!.rootNodeId)` and remove the key from openLines (no fetch needed — REMOVES the singleton "clear previous PV on chip switch" logic; other open lines are untouched). Else → toggle ON: set `pendingFlaw = flaw`, navigate to the fork node via goToNode. Do NOT clear other lines. Preserve the auto-open-on-entry effect (Quick 260702-fog) but route it through the same open-ON path (set pendingFlaw + goToNode; the graft effect records the line on arrival).

Multi-active chip highlight: replace the `activePvNodeId`/`activePvOrientation` singleton props with a set of active keys. Compute `activePvKeys = new Set([...openLines.keys(), ...(pendingFlaw ? [flawKey(pendingFlaw)] : [])])` and pass it to VariationTree as `activePvKeys`. A chip is "on" iff `\`${ply}:${orientation}\`` ∈ activePvKeys.

Free-move delete: pass `onDeleteLine={deleteSubtree}` to VariationTree (used by the × affordance; deleteSubtree already recovers the board to the fork parent).

Reset (`handleReset`, game mode): call `clearAllSidelines()` instead of `clearPvLine()`, then `setOpenLines(new Map())`, `setPendingFlaw(null)`, `setLiveFlawByNode(new Map())`, and navigate to the entry ply as today.

Update the `variationTree(...)` prop wiring: pass `pvNodeIds` (game mode) instead of `pvLine`, `activePvKeys` instead of activePvNodeId/activePvOrientation, and `onDeleteLine`. Keep `flawMarkerByNodeId={moveListMarkers}`, `onPvChipClick`, `decorations`, and pending/error props. The `moveListMarkers` merge already guards `if (!nodes.has(nodeId)) return;` — keep it; it stays valid after multi-line deletion. `liveFlawActive` already reads `isOnPvLine(currentNodeId)` (now pvNodeIds membership) so it still excludes every open PV line while grading free moves — no change needed beyond the destructure.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b</automated>
  </verify>
  <done>Analysis.tsx tracks open lines in a Map keyed by ply:orientation, opens/closes each tactic line independently via pendingFlaw + deleteSubtree, drives board overlays off the focused line, exposes onDeleteLine + activePvKeys to VariationTree, and Reset clears all sidelines. tsc -b passes with zero errors.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Flat sibling rendering + × affordance in VariationTree.tsx (desktop + mobile)</name>
  <files>frontend/src/components/analysis/VariationTree.tsx, frontend/src/components/analysis/__tests__/VariationTree.test.tsx</files>
  <behavior>
    - Given a tree with two sibling lines off two different mainLine fork nodes, BOTH lines render regardless of where currentNodeId sits (navigate onto the mainline and both sidelines remain in the DOM).
    - A free-move sibling line renders a delete button (data-testid `btn-delete-line-{rootId}`, aria-label "Delete variation") that calls onDeleteLine(rootId); a tactic sibling line (root ∈ pvNodeIds) renders NO × (it closes via its chip).
    - Multiple tactic chips render as "on" simultaneously when their `ply:orientation` keys are in activePvKeys.
    - Desktop and mobile both render all siblings at ONE indent level (no variation-subpv / Level-2 double-nesting).
  </behavior>
  <action>
Replace the single-chain renderer (`buildVariationChain`, `resolvePvDisplayChain`, the VariationChain `level`/`subChain` machinery, and the `variation-subpv-section` Level-2 blocks) with a flat sibling-block model.

Add a `buildSiblingBlocks(nodes, mainLine, pvNodeIds)` helper returning an ordered `SiblingBlock[]` where `SiblingBlock = { rootId: NodeId; forkParentId: NodeId; nearestMainIdx: number; chain: NodeId[]; isTactic: boolean; branchLabel: string | null }`. Enumeration rules (flat, one level, nothing hidden):
  - A non-mainLine node is a BRANCH ROOT iff its parent is on mainLine, OR its parent is off mainLine and it is NOT the lowest-id child of that parent (a secondary sub-fork). The lowest-id child of an off-mainLine node extends its parent's block (it is not a new block).
  - `chain` for a root = the root, then repeatedly append the lowest-id child of the tail while one exists (each higher-id child of any node on the chain becomes its own branch root via the rule above — so sub-forks surface as additional flat sibling blocks, never as nested indentation).
  - `nearestMainIdx` = index in mainLine of the nearest mainLine ancestor (walk parentId up from rootId). Blocks are grouped/placed under that mainLine row and ordered by rootId (fork-creation order).
  - `isTactic` = `pvNodeIds.has(rootId)`.
  - `branchLabel` = null when forkParentId is on mainLine; otherwise the fork parent's SAN (e.g. "(after Nf6)") so a sub-fork block shows where it diverges — since there is no second indent level to convey it.
  - Derive a block's starting ply from the fork parent node's `fen` (piece placement fullmove/side, same math as fenToRootPly) rather than mainLine index arithmetic, so sub-fork blocks label correctly. Add a small `plyFromFen(fen)` local helper.

DesktopTree: after rendering each mainLine row, render every SiblingBlock whose `nearestMainIdx` equals that row's fork index, each as its own indented block (`ml-8 border-l-2 border-muted/40 pl-2`, keep the zebra inheritance) using the existing `buildVariationRows`/`renderDesktopRow`/`renderMoveButton` for the block's chain and start ply. Keep `data-testid="variation-pv-section"` on tactic blocks; use `data-testid="variation-freemove-section"` on free-move blocks. For a free-move block, render a right-aligned delete button at the block header: lucide `X` icon, `data-testid={\`btn-delete-line-${block.rootId}\`}`, `aria-label="Delete variation"`, className using `text-muted-foreground hover:text-foreground` (neutral control — no hardcoded semantic color), `onClick` → `onDeleteLine?.(block.rootId)` with stopPropagation. Render `branchLabel` (when non-null) as a muted `text-sm` prefix above the block.

MobileTree: build the flat chip array by walking mainLine and, after each fork node's chip, splicing in each SiblingBlock (by nearestMainIdx, rootId order) as chips wrapped in single parens `( ... )` (drop the double-paren Level-2 case). Each block's last chip gets a `trailing` node: keep the existing severity glyph, and for a free-move block append an inline delete button (lucide `X`, same testid/aria-label/handler as desktop). HorizontalMoveList already renders `trailing` as arbitrary ReactNode and each chip's own `onMoveClick(ply=nodeId)` — the × button just needs `e.stopPropagation()` so tapping it deletes rather than navigates. HorizontalMoveList itself needs no change.

Props: replace `pvLine?: NodeId[]` with `pvNodeIds?: Set<NodeId>`; replace `activePvNodeId`/`activePvOrientation` with `activePvKeys?: Set<string>`; add `onDeleteLine?: (rootId: NodeId) => void`. Update `FlawChip` to compute `isActive = activePvKeys?.has(\`${ply}:${orientation}\`) ?? false` (drop the node/orientation singleton match). Update the component + `FlawChipProps` types and the header doc comment (describe flat siblings + × affordance, remove the two-level nesting description).

Update `VariationTree.test.tsx`: replace Fixture B's two-level pvLine fixture with a two-sibling fixture (two lines off two different mainLine forks, one grafted/tactic via pvNodeIds, one free-move). Rewrite the affected cases: assert both sibling sections render when currentNodeId is on the mainLine; assert `variation-freemove-section` + its `btn-delete-line-{rootId}` calls onDeleteLine with the root id; assert a tactic block has no × ; update the active-chip test to pass `activePvKeys` and assert the ring + collapse aria-label; delete the `variation-subpv-section` Level-2 assertions. Keep unrelated cases (main-line rows, flaw chips, severity glyphs) passing.

Watch CLAUDE.md limits: if DesktopTree/MobileTree grow past the logic-LOC/nesting limits, extract the block-rendering into a `renderSiblingBlock` helper (desktop) and a `siblingBlockToChips` helper (mobile) rather than inflating the existing functions.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/analysis/__tests__/VariationTree.test.tsx</automated>
  </verify>
  <done>VariationTree renders all sibling lines flat (one indent) on both desktop and mobile, free-move lines expose a working × (btn-delete-line-{rootId}, aria-label "Delete variation"), tactic lines omit it, multiple chips read active via activePvKeys, no Level-2 subpv rendering remains, and the component test suite passes.</done>
</task>

</tasks>

<threat_model>
Frontend-only change; no new packages, no new network input, no new trust boundary. `node.san` continues to originate from chess.js-validated moves (not user text) and React auto-escapes all JSX children, so the new sibling-block and × affordances introduce no injection surface. Existing FEN/URL guards (T-138-01, T-140-02a/b) are untouched. No STRIDE-actionable threats added by this quick task.
</threat_model>

<verification>
Full frontend pre-merge gate (CLAUDE.md), run from `frontend/`:

- `npm run lint`
- `npm test -- --run`
- `npx tsc -b`  (REQUIRED — VariationTree/hook props change shared types; lint+test do NOT type-check because esbuild strips types)
- `npm run knip`  (dead-export check — ensure removing pvLine/clearPvLine and the Level-2 helpers, and adding pvNodeIds/deleteSubtree/clearAllSidelines/buildSiblingBlocks, leaves no unused or dangling exports)

HUMAN-UAT (cannot be automated here — visually confirm on the Analysis page, in game mode with a game that has ≥2 flaw chips):
(a) two free-move lines off different game moves both persist and render;
(b) a free-move line survives navigating to another move and back;
(c) two tactic chips can be open simultaneously as siblings;
(d) clicking a tactic chip again toggles only its line off (others stay);
(e) the × removes a free-move line and returns the board to its fork;
(f) all of the above on a mobile viewport (< 640px) via the Moves tab.
</verification>

<success_criteria>
- Sidelines (free-move + tactic PV) render as flat, always-visible siblings; none are hidden on navigation or silently deleted on creating another line.
- Multiple tactic lines and free-move lines coexist; tactic chips toggle their own line; free-move lines delete via × (both desktop and mobile).
- One indent level only; no recursive nesting; no promote-to-mainline.
- All four frontend gate commands pass; both updated unit test suites are green.
</success_criteria>

<output>
Create `.planning/quick/260703-kyb-persistent-flat-sidelines-in-the-analysi/260703-kyb-SUMMARY.md` when done.
</output>
