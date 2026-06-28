---
quick_id: 260627-jqk
title: "UAT phase 140 — analysis board: tactic tags, best-move arrows, eval bar, sideline PV, board overlay"
status: ready
mode: quick
---

# Quick Task 260627-jqk — Phase 140 UAT polish (full-game analysis board)

Five UAT items on the `/analysis` **game mode** (`?game_id=&ply=`). Tactic mode
(`?flaw_ply=`) behavior is unchanged.

## Context (verified against code)

- `pages/Analysis.tsx` — composes board, EvalBar, EngineLines, VariationTree,
  TacticModeOverlay. Game-mode `boardArrows` are **never built** today (the arrow
  block is gated `if (isTacticMode …)`). EvalBar is fed purely by the live engine.
- `TacticModeOverlay` renders the motif chips **above** EngineLines — these are the
  "tactic badges on top of the engine lines" (item 1).
- `VariationTree.renderFlawChip` renders the literal text `Missed` / `Allowed`
  (item 2). `FlawMarkerEntry` carries no depth.
- Item-3 root cause: `insertPvLine` (useAnalysisBoard) parks `currentNodeId` at the
  fork node (on the main line) and `handlePvChipClick` navigates there too;
  `buildVariationChain` returns an empty chain when current is on the main line, so
  the grafted PV never renders.
- The miniboard (`LibraryGameCard` + `MiniBoard`) is the model for items 4/5: it
  builds a blue best-move arrow from `eval_series[ply].best_move`, a severity-colored
  flaw arrow from the played move, depth labels via `tacticDepthBadge`, all keyed by
  ply (= mainLine index = eval_series `ply`), independent of any loaded PV.

## Tasks

### Task 1 — Move-list tactic tags: name + depth (item 2)
- `components/analysis/VariationTree.tsx`:
  - Extend `FlawMarkerEntry` with `missedDepth: number | null`, `allowedDepth: number | null`.
  - `renderFlawChip`: accept a `depth` arg; render
    `tacticMotifLabel(motif)` + (` ${tacticDepthBadge(motif, depth, orientation)}` when non-null)
    instead of `'Missed'`/`'Allowed'`. Keep the missed/allowed color split.
  - Pass the matching depth at both call sites.
- `pages/Analysis.tsx`: populate `missedDepth`/`allowedDepth` in the
  `flawMarkerByNodeId` builder from `fm.missed_tactic_depth` / `fm.allowed_tactic_depth`.
- `verify`: desktop move list shows e.g. `checkmate 4`, `hanging-piece 2`; mate
  motifs collapse to `checkmate`; no `Missed`/`Allowed` literal remains.

### Task 2 — Show PV as a sideline on chip click (item 3)
- `components/analysis/VariationTree.tsx` (DesktopTree + MobileTree): when
  `pvLine` is non-empty and the user has NOT forked off it (buildVariationChain
  `level !== 2`), render the **full `pvLine`** as the Level-1 variation, deriving the
  fork parent from `nodes.get(pvLine[0]).parentId`. Leaves Level-2 sub-forks as-is.
- `verify`: clicking a tactic chip inserts and **displays** the PV sideline in the
  move list (desktop indented block + mobile parens) while parked at the fork.

### Task 3 — Precomputed best-move arrow + eval bar + board tactic overlay; drop overlay chrome (items 1, 4, 5)
- New hook `hooks/useGameOverlay.ts`: given gameData eval_series/flaw_markers,
  mainLine, nodes, currentNodeId, isOnMainLine, lastMove, engine pvLines + eval,
  returns `{ boardArrows, evalCp, evalMate, evalDepth }`:
  - maps keyed by ply: `bestMoveByPly`, `evalByPly`, `severityByPly`, depth labels.
  - `k = mainLine.indexOf(currentNodeId)`; `onMain` via isOnMainLine.
  - On main line with precomputed best move at `k`: blue arrow (best, missed-depth
    label) shown immediately; grey arrow = engine `pvLines[1]` (2nd best); flaw arrow
    (severity color, allowed-depth label) from `lastMove` when `severityByPly` has `k`.
    Eval bar = precomputed `evalByPly[k]` (synthetic depth so mate displays).
  - Off main line / no precomputed: blue = engine `pvLines[0]`, grey = engine
    `pvLines[1]`; eval = live engine. (sideline exploration)
  - de-dupe grey vs blue identical squares.
- `pages/Analysis.tsx`:
  - Use the hook; in game mode set `boardArrows` from it and feed EvalBar with its
    eval values (tactic/plain modes unchanged).
  - Stop rendering `TacticModeOverlay` in game mode (item 1) — render only when
    `isTacticMode`. Keep `activePvFlaw` + contextual fetch + `insertPvLine` effect
    (item-3 PV load path).
- `verify`: game-mode board shows a blue best-move arrow + depth overlay immediately
  on navigation/scrub (no PV needed); grey 2nd-best appears when engine returns;
  eval bar tracks precomputed eval; no motif-chip block above the engine lines.

## Gate
- `cd frontend && npm run lint && npm test -- --run && npx tsc -b`
- Fix any failures before commit.

## Must-haves
- truths: game-mode move list shows motif+depth; chip click renders the PV sideline;
  game-mode board shows precomputed blue best-move arrow + tactic depth overlay
  immediately; eval bar precomputed-driven; engine supplies only the grey 2nd line;
  no tactic-chip overlay above engine lines in game mode.
- artifacts: VariationTree.tsx, Analysis.tsx, hooks/useGameOverlay.ts.
- key_links: eval_series[].best_move, FlawMarker.*_tactic_depth, insertPvLine/pvLine,
  buildVariationChain, tacticMotifLabel/tacticDepthBadge.
