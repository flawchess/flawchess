# Phase 137: `useAnalysisBoard` Hook + Analysis Display Components - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the branching move tree and all analysis display components, each unit-testable in
isolation. Deliverables:

- `useAnalysisBoard.ts` — a NEW hook (independent of `useChessGame.ts`) holding a branching
  move tree where a mid-line move forks a new child node rather than truncating. Stores FEN
  per node for O(1) `goToNode`. Exposes `{ position, currentNodeId, nodes, mainLine, rootFen,
  lastMove, makeMove, goBack, goForward, goToNode, loadMainLine, isOnMainLine }` (ARCHITECTURE
  Pattern 3). Reads URL entry-point params only — no write-back.
- `EvalBar.tsx` — vertical sigmoid centipawn gradient, white-POV, mate label from depth 8+.
- `EngineLines.tsx` — top 1–2 PV lines, depth badge, "thinking" indicator; PV moves clickable.
- `VariationTree.tsx` — move list showing main line + the single active variation (flat).

**This phase ships NO `/analysis` route and NO page shell.** Routing, lazy-load boundary, page
composition, and on-device verification are Phase 138. `useChessGame.ts` is NOT modified.

Out of scope: tactic-mode overlay (Phase 139), full nested-tree display (v2), live URL
write-back of variation state (see D-01), any backend work (D-4 locked).
</domain>

<decisions>
## Implementation Decisions

### URL state scope (resolves a ROADMAP↔ARCHITECTURE conflict)
- **D-01:** **Read-only entry-point URL only** (ARCHITECTURE Pattern 5). The URL encodes where
  the user *arrived* (`game_id`/`flaw_ply`/`orientation`/`fen`); it is NOT written back as the
  user navigates or forks. Live navigation and user variations are **ephemeral** (D-4).
  - This explicitly reinterprets ROADMAP SC#4 / BOARD-04 ("variation state encoded in the URL,
    shareable/bookmarkable") as **"the *starting position* is shareable/bookmarkable"** — NOT
    the live variation tree. Chosen over live tree serialization to avoid history management and
    the confusing Back/Forward-changes-position behavior. Downstream agents must NOT build
    URL write-back or tree serialization in v1.
  - A future on-demand "copy position link" (encode current FEN when asked) is a deferred idea,
    not in this phase.

### VariationTree rendering
- **D-02:** **Responsive split, shared data contract:**
  - **Mobile:** lichess-style horizontal move list — extend the existing
    `frontend/src/components/board/HorizontalMoveList.tsx`; render the active variation inline
    in parentheses / indented at the fork point.
  - **Desktop:** a NEW vertical paired move list (`N. white black`), the active variation as an
    indented sub-line. Intended to sit beside the board — but **the placement beside the board
    is Phase 138's page-shell job**; Phase 137 delivers the component and its rendering only.
  - v1 is flat: main line + **single active variation** (BOARD-05). Full nested-tree display is
    v2. The vertical list's nesting payoff is therefore not realized yet — accepted.
  - Switching the active sibling: clicking a forked move makes it the active variation. Promote/
    delete-variation UX is out of scope for v1 (ephemeral tree).

### EvalBar + EngineLines behavior
- **D-03:** **EngineLines PV moves are clickable** — clicking a PV move plays it onto the board
  by calling `makeMove` (forks a variation node), like lichess/chess.com analysis.
- **D-04:** **EvalBar is white-POV fixed** — white end stays on top regardless of board flip.
  Sigmoid centipawn gradient; mate label shown from depth 8+ (locked upstream). EvalBar does
  NOT flip with board orientation.

### Verification surface (no route until 138)
- **D-05:** **Vitest hook + component tests only**, no visual harness (mirrors Phase 136
  D-01/D-02). Required gate:
  - `useAnalysisBoard` hook tests: mid-line fork creates a child (not truncation), `goBack` /
    `goForward` / `goToNode` navigation, O(1) `goToNode` (FEN read, no root replay),
    `loadMainLine` seeding + `isOnMainLine`.
  - Vitest + React Testing Library render tests for `EvalBar` / `EngineLines` / `VariationTree`
    against fixture props (eval/mate values, PV lines, a mainline + one variation).
  - On-device (iOS Safari / low-end Android) eyeballing of rendered engine output is **deferred
    to Phase 138** when the `/analysis` page first renders. No throwaway dev harness (136
    rejected that pattern).

### Claude's Discretion
- Internal tree representation details: NodeId allocation, `nodes` Map keying, sibling insertion
  order, exact `goForward` "first child" tie-break.
- EngineLines: plies-per-line shown before truncation, depth-badge / "thinking" indicator visual.
- VariationTree: exact parenthesis/indent styling, desktop column widths, auto-scroll-to-current.
- EvalBar: gradient stops, bar width, mate-label placement — within the white-POV + sigmoid +
  depth-8 mate constraints.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.29 milestone research
- `.planning/research/ARCHITECTURE.md` § Pattern 3 (branching move tree, `MoveNode` shape,
  fork/navigation, FEN-per-node), § Pattern 5 (URL entry-point, **no write-back** — D-01 anchor),
  and the component contract table (`useAnalysisBoard` / `EvalBar` / `EngineLines` returns/props)
- `.planning/research/PITFALLS.md` — Pitfall 3 (stale-eval race, relevant to EngineLines/EvalBar
  consuming engine output) and any tree/navigation pitfalls
- `.planning/research/SUMMARY.md` — Phase 137 section
- `.planning/research/STACK.md` — react-chessboard 5.x / chess.js usage notes

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — BOARD-01..05 (this phase); note BOARD-04/05 "flat single
  variation" + the D-01 reinterpretation of "URL shareable"
- `.planning/ROADMAP.md` § "Phase 137" — 5 success criteria (the acceptance bar); SC#4 reinterpreted per D-01

### Prior-phase context
- `.planning/phases/136-usestockfishengine-hook-wasm-setup/136-CONTEXT.md` — `useStockfishEngine`
  return contract (`evalCp`/`evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`) that
  EvalBar/EngineLines consume; D-01/D-02 verification-surface precedent

### Prior-art in the codebase (read before writing)
- `frontend/src/components/board/HorizontalMoveList.tsx` — shared SAN-chip shell to EXTEND for
  the mobile VariationTree (generic `HorizontalMoveItem` model)
- `frontend/src/components/board/MoveList.tsx` — current consumer of HorizontalMoveList (pattern
  reference for the flat-list mapping)
- `frontend/src/hooks/useChessGame.ts` — the hook NOT to modify; reference for chess.js
  move-making / replay conventions only
- `frontend/src/hooks/useTacticLine.ts` — Phase 135 hook; container-scoped keyboard handler
  pattern to mirror (NOT window-level); context for the Phase 139 subsume (not touched here)
- `frontend/src/lib/tacticDepth.ts`, `frontend/src/lib/moveNumberLabel.ts` — reused by tactic
  mode in Phase 139; not required here but inform the move-numbering shape
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HorizontalMoveList` (`board/HorizontalMoveList.tsx`) — presentational wrapping SAN-chip list
  with auto-scroll + click-to-jump, driven by a generic `HorizontalMoveItem` model. Direct base
  for the **mobile** VariationTree (D-02). Desktop vertical list is new.
- `react-chessboard@^5.10.0` + `chess.js@^1.4.0` already installed — board input (drag-drop +
  click-to-click) and move legality come from these; the ChessBoard component
  (`board/ChessBoard.tsx`) already exists.

### Established Patterns
- Hooks in `frontend/src/hooks/`, tests in `frontend/src/hooks/__tests__/`; components in
  `frontend/src/components/<area>/` with co-located `__tests__/`. New components live under a new
  `frontend/src/components/analysis/` dir.
- Container-ref-scoped keyboard handling (per `useTacticLine`), NOT window-level (per
  `useChessGame`) — avoids clashing with page shortcuts.
- CLAUDE.md frontend rules apply: `noUncheckedIndexedAccess` (narrow every PV/move array index),
  knip (no dead exports), `text-sm` floor, `data-testid` on interactive elements (move chips,
  PV-line moves, flip control), theme constants in `theme.ts` (eval gradient / WDL-style colors).

### Integration Points
- `useAnalysisBoard` consumes the Phase 136 `useStockfishEngine` output shape indirectly: the
  page (Phase 138) wires engine output into EvalBar/EngineLines; in 137 these components take
  that data as fixture props. Keep the prop types aligned with 136's return contract.
- No `/analysis` route, no `App.tsx` change, no router wiring in this phase (all Phase 138).
</code_context>

<specifics>
## Specific Ideas

- VariationTree desktop = chess.com / lichess desktop analysis convention (vertical paired move
  list beside the board). Mobile = lichess mobile convention (horizontal list, forked line in
  parentheses + indent). User explicitly anchored both to lichess/chess.com behavior.
- EngineLines clickability mirrors lichess/chess.com: clicking a PV ply walks the board into that
  line as a real variation node.
</specifics>

<deferred>
## Deferred Ideas

- **Live URL write-back / shareable variation tree** — out of v1 (D-01). A future "copy position
  link" that encodes the current FEN on demand could satisfy "shareable" without continuous
  write-back; revisit alongside the v2 nested-tree work.
- **Full nested-tree VariationTree display** (multiple variations, arbitrary depth) — v2
  (BOARD-05 caps v1 at flat main-line + single active variation).
- **Promote / delete / annotate variation UX** — not in v1; tree is ephemeral.
- **On-device (iOS Safari / low-end Android) verification of rendered engine output** — Phase 138
  (when `/analysis` first renders). Not lost; it is 138's verification gate.
- **Tactic-mode overlay, stored-PV seeding, entry points** — Phase 139 / 138 respectively.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>

---

*Phase: 137-useanalysisboard-hook-analysis-display-components*
*Context gathered: 2026-06-26*
