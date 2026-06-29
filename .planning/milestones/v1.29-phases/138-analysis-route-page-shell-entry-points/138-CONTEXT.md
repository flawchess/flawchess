# Phase 138: `/analysis` Route + Page Shell + Entry Points - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the standalone `/analysis` page into the app and compose the already-built pieces
(Phase 136 `useStockfishEngine`; Phase 137 `useAnalysisBoard`, `EvalBar`, `EngineLines`,
`VariationTree`) into a responsive page shell, plus the **opening-position** free-play entry
point. Deliverables:

- `src/pages/Analysis.tsx` — NEW lazy-loaded page shell. Reads URL entry-point params
  (`fen`; tactic params `game_id`/`flaw_ply`/`orientation` are parsed but tactic-mode chrome is
  Phase 139), composes the hooks + display components into a responsive layout, shows the
  "Loading engine…" state in the eval area while WASM initializes (board + move stepper stay
  interactive).
- `src/App.tsx` — add `const AnalysisPage = React.lazy(() => import('./pages/Analysis'))`
  (the **first** `React.lazy` boundary in the app), one `<Route path="/analysis">` inside
  `ProtectedLayout` wrapped in `<Suspense>`, and `'/analysis': 'Analysis'` in `ROUTE_TITLES`.
- **Opening-position entry point only** — an "Analyze position" action on the Openings page that
  navigates to `/analysis?fen=<url-encoded current Explorer position>`.

**Descoped from this phase (was in the ROADMAP title / ROUTE-02): the game-review-ply entry
point.** See `<decisions>` D-03 and `<deferred>`. The `?game_id=&ply=` reader is NOT built here.

Out of scope: tactic-mode overlay + chrome + stored-PV seeding (Phase 139), retiring
`TacticLineExplorer`/`useTacticLine` (Phase 139), the game-review-ply entry point (folded into
Phase 139), URL write-back / live variation serialization (D-01, Phase 137), any backend work
(D-4 locked), paste-a-FEN box (v2, BOARD-V2-01).
</domain>

<decisions>
## Implementation Decisions

### Entry points (the one discussed area)
- **D-01 (carried, Phase 137):** URL is **read-only entry-point encoding** — no write-back; live
  navigation/forks are ephemeral. The opening-position entry encodes only the *starting* FEN.
- **D-02:** **Opening-position entry is in scope for 138.** Surface: an "Analyze position" action
  on the Openings page (Explorer tab) that carries the **current Explorer board position** (the
  `position` FEN already held by `pages/Openings.tsx` / `ExplorerTab`) to `/analysis?fen=…`.
  Button placement/label is Claude's discretion (see below), but it lives where the user is
  already looking at a position. Reuses the v1 `fen` param — no new reader, no backend (D-4).
- **D-03:** **Game-review-ply entry point is DESCOPED from Phase 138 and folded into Phase 139.**
  Rationale: the simple `?fen=<scrubbed ply FEN>` shortcut was available (the game viewer already
  reconstructs a per-ply FEN client-side in `LibraryGameCard`), but the user chose to defer the
  whole game-review entry rather than ship a half-context version now. Phase 139 already touches
  the game/library surfaces and carries `game_id`/`ply` plumbing for tactic mode, so the
  game-review entry rides along there (planner for 139 should fold it in; note this expands 139's
  scope slightly beyond pure tactic-mode subsume).
- **D-04:** **ROADMAP Phase 138 title and ROUTE-02 wording are left untouched** ("game-review
  ply" still appears). The descope is recorded here only — no unrequested ROADMAP/REQUIREMENTS
  edits. Flag for adjustment at milestone close / when 139 absorbs the entry.

### Page shell, reachability, defaults (not selected for discussion — locked by ARCHITECTURE + discretion)
- **D-05:** **No nav-bar "Analysis" item** (ARCHITECTURE: contextual destination, not primary
  nav). `/analysis` is reachable via entry points and by typing the URL; a blank-board free-play
  (no params) is a valid, reachable state (empty `fen` → standard start position).
- **D-06:** **Engine on by default** on page mount; the "Loading engine…" / "analyzing" state
  shows in the eval area during WASM init while the board/stepper stay interactive (ROADMAP
  SC#3). Toggle-off available per ENGINE-04 (already built in 136/137).
- **D-07:** **Lazy-load boundary is the acceptance spine** (ROADMAP SC#1): `React.lazy` page split
  keeps the stockfish JS/WASM off every other route. Verify via Network tab — no stockfish fetch
  on `/library`, `/openings`, `/endgames`. `window.crossOriginIsolated === false` on `/analysis`;
  Google OAuth flow completes from any page (SC#4, PLAT-01 — already CI-guarded in 136).

### Claude's Discretion
- **Page shell layout** — responsive composition (lichess/chess.com convention: eval bar beside
  the board on desktop, stacked below on mobile; EngineLines + VariationTree placement; board
  sizing). Reuse existing `ChessBoard` (`id`/`data-testid="analysis-board"`), `theme.ts` tokens,
  `text-sm` floor, `data-testid` on interactive elements.
- **"Analyze position" button** — exact placement on the Openings Explorer tab, label, icon,
  and `Button` variant (`brand-outline` per CLAUDE.md secondary-action rule unless it reads as
  the primary CTA there). Apply to mobile + desktop surfaces (CLAUDE.md parity rule).
- **Suspense fallback copy** and the engine-loading indicator wording/visual.
- Whether the blank free-play state needs any onboarding affordance, or just renders the start
  position silently (lean: silent, no extra chrome).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.29 milestone research
- `.planning/research/ARCHITECTURE.md` — § Pattern 5 (URL entry-point params; v1 = `fen` + tactic
  only; **no write-back**), § Pattern 6 (code-split / `React.lazy` lazy-load boundary, public
  WASM placement), the `App.tsx` minimal-change note (route + `ROUTE_TITLES`, **no nav item**),
  and the "Phase 3 — `/analysis` page + router wiring + entry points" build-sequence section
- `.planning/research/PITFALLS.md` — engine/worker lifecycle on a lazy-mounted page, stale-eval
  race (EngineLines/EvalBar consuming live engine output on the shell)
- `.planning/research/SUMMARY.md` — Phase 138 section
- `.planning/research/STACK.md` — react-chessboard 5.x / chess.js + Vite lazy-import notes

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — ROUTE-01, ROUTE-02 (note the game-review-ply descope per D-03/D-04
  is NOT reflected in REQUIREMENTS yet)
- `.planning/ROADMAP.md` § "Phase 138" — 4 success criteria (the acceptance bar); SC#2's
  game-review-ply clause is descoped per D-03

### Prior-phase context (the pieces this phase composes)
- `.planning/phases/137-useanalysisboard-hook-analysis-display-components/137-CONTEXT.md` —
  `useAnalysisBoard` return contract + EvalBar/EngineLines/VariationTree props + D-01 read-only
  URL anchor
- `.planning/phases/136-usestockfishengine-hook-wasm-setup/136-CONTEXT.md` — `useStockfishEngine`
  return shape (`evalCp`/`evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`) wired into the
  shell; PLAT-01 COOP/COEP CI guard already in place

### Prior-art in the codebase (read before writing)
- `frontend/src/App.tsx` — routing (`ProtectedLayout`, `<Routes>`, `ROUTE_TITLES`); no page is
  currently lazy-loaded, so this introduces the `React.lazy` + `<Suspense>` pattern
- `frontend/src/pages/Openings.tsx` + `frontend/src/pages/openings/ExplorerTab.tsx` +
  `frontend/src/components/move-explorer/MoveExplorer.tsx` — the `position` FEN source for the
  opening-position entry
- `frontend/src/components/board/ChessBoard.tsx` — board to embed (`id`/`data-testid`,
  drag-drop + click-to-click already supported)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 136/137 deliverables (`useStockfishEngine`, `useAnalysisBoard`, `EvalBar`, `EngineLines`,
  `VariationTree`) are built and unit-tested — 138 only composes them; no new hooks/components
  beyond `Analysis.tsx` and the Openings entry button.
- `ChessBoard` (`components/board/ChessBoard.tsx`) — drag-drop + click-to-click + flip already
  supported; embed with `id="analysis-board"` / `data-testid="analysis-board"`.
- Openings Explorer already holds a live `position` FEN (`pages/Openings.tsx` → `ExplorerTab`
  `position` prop → `MoveExplorer`) — the opening-position entry just URL-encodes it.

### Established Patterns
- React Router v6 with `ProtectedLayout` wrapper; `ROUTE_TITLES` map drives the page title.
  `/analysis` goes inside `ProtectedLayout` (authenticated users — ROADMAP SC#1).
- Vite built-in code-split via `React.lazy` + dynamic `import()` — no `manualChunks` change
  needed; the `analysis/` components ride inside the Analysis chunk automatically.
- WASM stays in `public/` (unprocessed); the worker is created in `useStockfishEngine`'s effect,
  so WASM fetch is deferred to first hook mount on `/analysis` (Layer B isolation).
- CLAUDE.md frontend rules: `noUncheckedIndexedAccess`, knip (no dead exports), `text-sm` floor,
  `data-testid` on interactive elements, theme constants in `theme.ts`, `tsc -b` before
  integrating (shared-type/prop changes), mobile+desktop parity for any entry-point button.

### Integration Points
- `App.tsx`: one `React.lazy` import + one `<Route>` + one `ROUTE_TITLES` entry. No nav item.
- Openings page: one "Analyze position" action → `navigate('/analysis?fen=…')`.
- Engine output (136) wired into EvalBar/EngineLines inside `Analysis.tsx`; board state from
  `useAnalysisBoard` (137) drives the board + VariationTree.
- This phase finally renders the engine output on a real route — it carries the **on-device
  verification gate deferred from Phase 137** (iOS Safari / low-end Android eyeballing of rendered
  EvalBar/EngineLines/VariationTree).
</code_context>

<specifics>
## Specific Ideas

- Layout convention anchored to lichess/chess.com analysis pages (board centered, eval bar
  adjacent, engine lines + move list in a side/below panel) — consistent with the Phase 137
  desktop/mobile VariationTree intent.
- Opening-position entry should feel like a natural "take this position to the analysis board"
  affordance from where the user is already exploring openings.
</specifics>

<deferred>
## Deferred Ideas

- **Game-review-ply entry point** — descoped from 138 (D-03), **folded into Phase 139**. Implement
  there alongside tactic-mode entry repointing. Decision still open for 139: carry the scrubbed
  ply's already-reconstructed FEN via `?fen=` (cheap, no game context), or build the deferred
  `?game_id=&ply=` reader (replays game on the Analysis side, carries move numbering). The
  `LibraryGameCard` game viewer (per-ply `{fen,to}` reconstruction + scrub slider) is the host
  surface; one shared "Analyze" button covers FlawCard + GamesTab.
- **ROADMAP/ROUTE-02 wording cleanup** — "game-review ply" still appears in Phase 138's title and
  ROUTE-02; adjust at milestone close or when 139 absorbs the entry (D-04).
- **On-demand "copy position link"** (encode current FEN when asked) — satisfies "shareable"
  without continuous write-back; v2, alongside the nested-tree work (carried from Phase 137).
- **Paste-a-FEN / paste-PGN entry box** — BOARD-V2-01, v2.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>

---

*Phase: 138-analysis-route-page-shell-entry-points*
*Context gathered: 2026-06-26*
