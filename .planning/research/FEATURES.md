# Feature Research

**Domain:** Live-engine chess analysis board (browser WASM Stockfish, branching move tree, URL-encoded state)
**Milestone:** v1.29 — Live-Engine Analysis Page
**Researched:** 2026-06-26
**Confidence:** HIGH (analysis-board patterns well-established across lichess/chess.com; WASM Stockfish API stable and verified; reuse map grounded in direct codebase inspection)

---

> This file covers features for v1.29: the standalone `/analysis` page.
> All prior FlawChess features (v1.0–v1.28) are already shipped and are NOT re-researched here.
> Focus: what the live-engine board needs to feel complete, what sets it apart, and what to explicitly omit.

---

## Context: What Users Expect From a Chess Analysis Board

Any credible analysis board is benchmarked mentally against lichess.org/analysis. Users who have played chess online have internalized that interface. The bar is high but clear: engine eval is shown live as you navigate, you can make any move and the board follows, and you can share the position with a link. Falling below that bar at launch will feel like a downgrade from what FlawChess already links out to.

The deliberate trim from lichess is the right call. Lichess has evolved 10+ years of features (opening book overlays, tablebase lookups, PGN comments, annotation symbols, study system, engine match mode). A "trimmed" board that does the core three things well — eval, free-play, shareable URL — beats an imitation of the full set shipped half-finished.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a user expects from any live chess analysis board. Missing these makes the product feel unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Live engine eval bar** | The vertical graphical bar (white/black advantage slider) is the most recognizable visual affordance of any analysis board. Absence breaks the "analysis" contract. | LOW | Derived from the `cp` score in UCI `info` lines. Show as ±pawn-unit float (+1.5, –0.3). Mate overrides show as M+N / M–N. Bar height maps eval through a sigmoid (same Lichess k=0.00368208 already used in backend). |
| **Numeric eval display** | Users read the +/– number to judge position severity. Needed alongside the bar. | LOW | Cap display at ±20 (beyond that the bar is pegged anyway). Mate-in-N shows "M3" not "+9999". |
| **Depth / nodes indicator** | Users need to know the engine is thinking and how far it has searched. "Depth 18" or "thinking…" | LOW | Pull from UCI `info depth N`. Show the latest completed depth. "thinking…" spinner during the first few hundred ms. |
| **Top 1–2 PV lines (MultiPV)** | Seeing the best move and one alternative is the minimum for understanding why a move is good or bad. | MEDIUM | UCI `setoption name MultiPV value 2`. Parse `info multipv 1` and `info multipv 2` from engine output. Display as SAN move sequences (convert from UCI using chess.js). Clicking a PV move navigates the board to that position. |
| **Engine start / stop toggle** | Users need to pause engine analysis (low-battery awareness, navigating quickly without re-triggering). Standard on all analysis boards. | LOW | Single icon button toggles `go`/`stop` UCI commands. Engine does not re-start on position change when stopped. |
| **Drag-drop + click-to-click moves** | Both interaction modes are expected. Click-to-click is essential on mobile. | LOW | `react-chessboard` v5 already supports both. The existing `ChessBoard.tsx` wraps it. New board needs the same `onPieceDrop` + `onSquareClick` pattern. |
| **Flip board** | Standard control. Missing it breaks analysis for Black positions. | LOW | Existing `BoardControls.tsx` has the Repeat2 button. Reuse without change. |
| **Back / forward navigation** | Navigate ply by ply through the move tree. Arrow keys are expected by power users. | LOW | Existing `BoardControls.tsx` + keyboard handler in `useChessGame.ts`. The branching variant must keep this. |
| **Reset to root** | Return to the entry position (not necessarily the chess starting position — for tactic mode, root is the flaw FEN). | LOW | Already in `BoardControls.tsx` (SkipBack button). Logic in `useChessGame.ts reset()`. The branching hook must reset to `rootFen`, not `STARTING_FEN`. |
| **Branching move tree (fork on deviation)** | Making a move that is NOT the next move in the current line should fork into a side variation, not be rejected. This is the core difference between a replay board and an analysis board. | HIGH | The existing `useChessGame.ts` has no branching — it appends to a flat `moveHistory`. The new `useChessAnalysis` hook must maintain a tree structure (node graph where each node has a list of child moves). See Feature Dependencies. |
| **URL-encoded position state** | Sharing and bookmarking the analysis position. "Paste this URL to share the position" is table stakes on all modern analysis boards. | MEDIUM | FEN encodes position only; PGN (compact) encodes the move tree. v1 scope: encode the current FEN + the linear move sequence as a URL query param. Full variation-tree serialization is v1.x. See URL State section below. |
| **Debounced engine re-analysis on position change** | Engine must restart search on every position change, but not on every intermediate navigation step (rapid back/forward through moves). | LOW | 150–300ms debounce window. If the user moves again within the window, cancel the pending restart. Already a named watch-out in SEED-066. |
| **Engine node / time budget** | Single-thread WASM SF on a mid-range phone will spin indefinitely if uncapped, warming the device and draining battery. Users expect analysis to "settle" in a few seconds. | MEDIUM | Cap at `nodes 1000000` (Lichess parity for server eval; the existing backend uses this budget). On position change restart from scratch. A `movetime 5000` fallback prevents infinite loops if node count is slow to accumulate. Show the current depth so users can see progress. |
| **Eval arrow on board** | A colored arrow from source to destination square highlighting the engine's best move is universal on analysis boards. | LOW | Existing `ArrowOverlay` + `arrowGeometry.ts` already renders arrows. Use the PV[0] best move. |
| **Last-move highlight** | The most-recently-played move squares are highlighted (standard board UX). | LOW | Already in `useChessGame.ts` via `lastMove` state. Carry into the branching hook. |

### Differentiators (FlawChess-Specific Value)

Features that go beyond a generic analysis board and leverage FlawChess's unique data or context.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Stored PV as initial mainline (D-5)** | FlawChess already has Stockfish-evaluated PVs stored in `game_positions.pv`. Loading the tactic or game-review position opens the board with that PV as the mainline — users immediately see the engine's top line without waiting for WASM to compute it from scratch. The live engine then takes over and may confirm or deepen the line. | MEDIUM | `loadMoves(pv_moves)` seeds the mainline from the API response (Phase 135's `tactic-lines` endpoint already surfaces this). The live engine runs in parallel. On deviation from the stored line, the live engine becomes the sole authority. On navigating PAST the end of the stored PV, the live engine extends it automatically. |
| **Tactic mode overlay** | The TacticLineExplorer (Phase 135) becomes a mode of the shared board. Opening from a tactic card auto-loads the flaw position with the stored PV, shows the motif badge, missed/allowed orientation label, and depth-to-punchline counter. Next/prev tactic navigation rail lets users drill multiple tactics without leaving the board. | MEDIUM | Re-homes `useTacticLine` logic into the analysis board as a mode. The existing Phase 135 UX (depth-0 highlight, +1 offset for `allowed`, real-game-ply numbering) is the acceptance bar. No Phase 135 behavior may regress. |
| **Context-aware entry points** | Opening the board from a tactic card pre-loads the tactic position; from a game ply it pre-loads that game position; from an opening it pre-loads the opening hash. The board is always seeded with relevant context, not an empty starting position. Users never have to manually recreate the position they care about. | LOW-MEDIUM | Entry-point wiring. Each entry encodes the context (FEN, move sequence, tactic metadata) in the URL. The `/analysis` route reads URL params and initializes accordingly. `useAnalysisParams` hook parses URL state. |
| **FlawChess position context panel** | When loading from a game ply or tactic, show a compact header: the game (opponent, date, platform icon), the ply number, and the flaw chip (Blunder/Mistake + motif). Gives the analysis board meaning beyond a blank position. | LOW | Read from URL params passed by the entry point. Display-only; no API call needed. |
| **Engine on/off with visible "analyzing" state** | Users on mobile or slow devices appreciate explicit control. The existing `EvalCoverageHeader` pattern (live pulsing indicator) sets the tone. Apply the same "analyzing… / stopped" language to the engine status. | LOW | Pair engine state with a status chip next to the eval display. |

### Anti-Features (Explicitly Omit to Stay "Trimmed of Bloat")

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Paste-a-FEN / PGN input box** | Seems like the obvious entry point for "analyze any position" | Explicitly deferred from v1 scope (SEED-066 milestone kickoff). Adds surface area, copy-paste UX on mobile is poor, and FlawChess's three entry points (tactic, game-ply, opening) cover 100% of the in-product use case. Users who want to paste an arbitrary FEN have lichess. | Three typed entry points: tactic, game-ply, opening. FEN-only entry via URL param is sufficient for power users. |
| **Multi-thread WASM (SharedArrayBuffer)** | Faster search, deeper analysis | Locked out (D-3): requires COOP/COEP cross-origin isolation, which breaks Google OAuth popup and is unreliable on iOS Safari. Single-thread at depth 20–24 is far beyond what a human needs to understand a position. | Single-thread SF18 (or SF18-lite for bandwidth-constrained users). Multi-thread is a future deferred progressive enhancement on a separately hard-loaded document. |
| **Cloud eval API (chessdb.cn / lichess cloud eval)** | Instant evals for popular positions, no WASM load | FlawChess's stored PVs already fill the "precomputed half" for positions in the user's game history. Adding an external cloud eval API introduces a third-party dependency, rate limits, and CORS complexity for marginal gain on positions the user hasn't played. | Stored PVs for known positions; WASM for everything else. |
| **Server-side analysis persistence (save analyses to DB)** | Users want to save named analyses | Locked out (D-4): ephemeral state, no schema, no auth coupling. Keeps the feature near-100% frontend. URL encodes all state; a bookmark in the browser is the save mechanism. | URL-encoded state; users copy/bookmark the URL. Revisit only if users explicitly request named saved analyses. |
| **PGN annotation / comment system** | Desktop analysis tools (ChessBase, lichess studies) support textual comments on moves | Heavy editorial UI, no clear user demand within FlawChess's analytics-first context. Comments require a rich text editor or at minimum a text input wired to each node in the variation tree. | Omit entirely in v1. The eval and PV lines carry the analysis signal; prose annotation is not part of the MVP. |
| **Promote / demote variation** | Expected in desktop PGN editors (ChessBase) | Power-user feature; adds tree-manipulation UI that is hard to make touch-friendly. Rarely needed for the "understand a tactic or game position" use case. | Navigation suffices — users can re-play both lines. Promote/demote is a v1.x addition if demand surfaces. |
| **Delete node / variation from tree** | Cleaning up an exploration tree | Same as above — tree-editing on touch is poor UX. | Reset to any node by clicking in the move list and branching again. |
| **Opening book overlay (ECO names, percentages)** | Lichess shows opening name and move frequency | FlawChess's Opening Explorer already serves this. Duplicating it on the analysis board creates inconsistency. | The analysis board shows the existing `openingName` from `useChessGame.ts` (derived from local lichess DB) as a text label — one line, no click-through. That's sufficient. |
| **Tablebase integration** | Precise WDL for endgame positions with ≤7 pieces | Third-party API dependency, mobile data cost, and overkill for the typical user. The WASM engine handles endgames well at depth 20+. | WASM engine eval is sufficient. Tablebase is a future differentiator, not MVP. |
| **Engine vs engine self-play / best-play mode** | Interesting to watch Stockfish play itself | No user value in a post-game analytics context. Increases complexity with no analytics ROI. | Not planned. |
| **Social sharing (tweet, embed code)** | Shareable position links | URL copy covers the sharing need. Social share buttons add noise and require tracking pixel implications. | Copy URL button. |
| **Real-time multiplayer analysis / study rooms** | Collaborative analysis | Requires WebSocket infrastructure, user presence, write conflicts. Completely out of scope for a single-user analytics tool. | Not planned. |
| **Move quality annotation symbols (!, ?, !!, ??)** | Standard in PGN editors | FlawChess already annotates flaws via the materialized `game_flaws` table (Blunder, Mistake, Inaccuracy). Showing those on the board is sufficient. Re-implementing a click-to-annotate system is scope creep. | Flaw chip (Blunder/Mistake) inherited from entry context. No interactive annotation in v1. |

---

## Feature Dependencies

```
[useStockfishEngine hook]  ← foundational; everything engine-related depends on this
    └──enables──> [Live eval bar]
    └──enables──> [Numeric eval + mate display]
    └──enables──> [Depth indicator]
    └──enables──> [PV lines (MultiPV 1-2)]
    └──enables──> [Eval arrow on board]
    └──enables──> [Debounced re-analysis on position change]
    └──requires──> [WASM Stockfish build vendored as public asset]
    └──requires──> [Web Worker wrapper (UCI postMessage protocol)]

[useChessAnalysis hook]  ← branching variant of useChessGame; the game-state layer
    └──requires──> [chess.js move validation]
    └──enables──> [Branching move tree (fork on deviation)]
    └──enables──> [Back/forward navigation]
    └──enables──> [Reset to root]
    └──enables──> [Click PV move → navigate]
    └──enables──> [URL state serialization/deserialization]
    └──note──> Does NOT replace useChessGame.ts on the Openings page (different concerns)

[/analysis route + page]
    └──requires──> [useStockfishEngine hook]
    └──requires──> [useChessAnalysis hook]
    └──requires──> [Lazy-loaded WASM bundle (code-split on /analysis route)]
    └──enables──> [EvalBar component]
    └──enables──> [PvLines component]
    └──enables──> [URL-encoded position state]
    └──enables──> [Tactic mode overlay]
    └──enables──> [Entry-point wiring (tactic cards, game-ply, opening)]

[Tactic mode overlay]  ← refactor of Phase 135 TacticLineExplorer
    └──requires──> [/analysis route]
    └──requires──> [useTacticLine logic (existing Phase 135)]
    └──requires──> [Stored PV as initial mainline (D-5)]
    └──preserves──> [All Phase 135 acceptance criteria (depth-0, +1 offset, move numbering, next-tactic nav)]
    └──retires──> [Standalone TacticLineExplorer modal (Phase 135 component, at parity)]

[Stored PV as initial mainline (D-5)]
    └──requires──> [Phase 135 tactic-lines API endpoint (already live)]
    └──requires──> [useChessAnalysis hook loadMoves() equivalent]
    └──enables──> [Live engine takes over on deviation or past PV end]

[URL-encoded position state]
    └──requires──> [useChessAnalysis hook]
    └──enables──> [Shareable links]
    └──enables──> [Context-aware entry points (FEN + moves encoded)]
```

### Dependency Notes

- **`useStockfishEngine` is the novel risk.** Every other piece is either existing infrastructure (ChessBoard.tsx, BoardControls.tsx, ArrowOverlay) or a known extension of existing hooks. The WASM Web Worker UCI wrapper has no prior art in the codebase.
- **`useChessAnalysis` must NOT break `useChessGame.ts`.** The Openings board and tactic modal stepper use the existing hook. The branching analysis variant is a new export, not a modification. Rename clearly.
- **Tactic mode is a refactor, not a rewrite.** Phase 135's acceptance criteria are the UAT bar. Every detail of `useTacticLine` and `TacticLineExplorer` must be preserved before the standalone modal is retired.
- **WASM bundle lazy-loading is a hard requirement.** The PWA's initial load must not be taxed. Use React `lazy()` / dynamic `import()` + Vite code-splitting on the `/analysis` route. Show a "Loading engine…" state.
- **Node budget drives correctness.** Single-thread SF18-lite at 1M nodes reaches depth 20–24 in ~1–3 seconds on a modern phone. Cap at `nodes 1000000` (matching the backend budget for consistency) with a `movetime 5000` safety valve. Never let the engine run unbounded on mobile.

---

## Mobile-First Lens (PWA, Touch, Single-Thread Performance)

Every feature decision below is filtered through the mobile-first constraint. FlawChess is a PWA installed on iOS/Android.

| Concern | Decision |
|---------|----------|
| **WASM bundle weight** | Vendor `stockfish-18-lite-single` (~7MB) as the v1 default. The full SF18 single-thread net is ~85MB — unacceptable as a mobile first-load. The lite net is meaningfully weaker in pure engine strength but still superhuman for human analysis (depth 20+ in seconds on mid-range phones). Power users on desktop who want the full net can get it from lichess's own board. |
| **NNUE download caching** | The .wasm + .nnue files must be served with long-cache headers and included in the Vite build output so the PWA service worker can precache them. After first load, re-analysis on `/analysis` is instant. |
| **Lazy-load on route entry** | Stockfish workers must NOT be instantiated until the user navigates to `/analysis`. Vite dynamic `import()` on the route component boundary handles this. |
| **Touch move input** | Click-to-click (two taps: source square then destination) is already implemented in `ChessBoard.tsx`. Drag-drop works but is secondary on mobile. Confirm both paths work in the analysis board context. |
| **Eval bar orientation** | On mobile, the eval bar should render BELOW the board or as a narrow strip above it — never overlapping the board. On desktop, the vertical bar beside the board is the lichess convention. Use responsive layout (Tailwind breakpoints). |
| **PV lines display** | On mobile, the PV line(s) render in a collapsible/scrollable area below the board. On desktop, a fixed panel beside or below the board. The move list must not overflow horizontally — wrap or scroll. |
| **Board size** | Reuse the existing board sizing patterns from the Openings page (square board, constrained to viewport width on mobile). No special sizing logic needed. |
| **44px touch targets** | All interactive elements (engine toggle, flip, back/forward, reset, PV move clicks) must meet the 44px minimum. `BoardControls.tsx` already enforces this for nav buttons. PV move spans need explicit padding. |
| **"Loading engine" state** | Show a spinner or "Loading engine…" message while the WASM worker initializes. On a cold load this may take 2–5 seconds. Never show a blank eval bar — show a clear loading state. |
| **Engine on mobile background** | When the user switches away from the `/analysis` tab, the Web Worker continues running. Add a `visibilitychange` listener to stop the engine when the page is hidden and restart when it returns. Prevents battery drain on mobile. |
| **Single-thread perf cap** | `nodes 1000000` + `movetime 5000` caps are non-negotiable for mobile. Do not remove them in v1 even if power users on desktop request depth-unlimited mode. |

---

## URL State Design

URL-encoded state is the v1 persistence mechanism. No server storage, no auth coupling.

| Scenario | URL Shape | Notes |
|----------|-----------|-------|
| Entry from tactic card | `/analysis?mode=tactic&game_id=<id>&ply=<n>&orientation=missed` | The page fetches tactic data from Phase 135's `tactic-lines` API, loads stored PV as mainline |
| Entry from game-review ply | `/analysis?game_id=<id>&ply=<n>` | Loads the game's position FEN at that ply; stored PV if available |
| Entry from opening position | `/analysis?moves=<san_sequence_encoded>` | Replays the SAN sequence from starting position |
| Mid-analysis shareable link | `/analysis?fen=<encoded_fen>&moves=<encoded_move_sequence>` | Encodes root FEN + moves made so far (linear, not full tree) |
| Reset / start fresh | `/analysis` (bare) | Starting position, no pre-load |

**Encoding:** FEN contains spaces and slashes — encode with `encodeURIComponent()` or use base64. Moves as a `+`-separated SAN string (e.g., `e4+e5+Nf3`). Keep URLs human-readable where feasible; base64 is acceptable for FEN. Do NOT encode the full variation tree in v1 — only the current "main" sequence.

**State reading:** `useAnalysisParams` hook parses URL on mount, initializes the game state and engine accordingly. URL is updated (via `history.replaceState`, not `navigate`) as the user makes moves, so the URL always reflects current position.

---

## D-5 Handoff: Stored PV → Live Engine

The stored PV from `game_positions.pv` is the initial mainline when the board is opened from a tactic or game context. The live engine runs concurrently.

| Scenario | Behavior |
|----------|----------|
| User navigates within the stored PV | Board shows the stored moves. Live engine eval supplements (may agree or show deeper line). |
| User makes a move NOT in the stored PV | Board forks into a variation. Live engine immediately re-evaluates the new position. The stored PV is now a branch; the user's deviation is the new "current line." |
| User navigates PAST the end of the stored PV | Live engine automatically extends the analysis. No stored PV below this point; engine eval is the sole source. |
| Stored PV is null (no PV for this position) | Board opens at the position. Live engine starts immediately. No initial mainline. |

---

## MVP Definition

### Launch With (v1.29)

Minimum viable product — what's needed to close the gap vs. "go to lichess for free analysis."

- [ ] `useStockfishEngine` hook — WASM SF18-lite-single Web Worker, UCI protocol, `go nodes 1000000`, MultiPV=2, start/stop, debounce
- [ ] `EvalBar` component — graphical bar (sigmoid), numeric eval, mate-in-N, depth indicator
- [ ] `PvLines` component — top 1–2 lines as clickable SAN sequences, eval score per line
- [ ] `useChessAnalysis` hook — branching variant of `useChessGame`: fork on mid-line move, back/forward/reset, root-FEN seeding, URL sync
- [ ] Eval arrow on board — highlights engine's best move (PV[0] first move)
- [ ] `/analysis` route — standalone page, lazy-loads WASM on entry, `data-testid` on all interactive elements
- [ ] Entry-point wiring — tactic cards, game-review ply, opening positions each navigate to `/analysis` with correct URL params
- [ ] URL state encoding/decoding — root FEN + move sequence; `useAnalysisParams` hook
- [ ] Tactic mode overlay — motif badge, missed/allowed framing, depth-to-punchline counter, next/prev tactic nav; retires standalone `TacticLineExplorer` modal at parity
- [ ] Mobile layout — eval bar below board on mobile, PV lines scrollable, 44px touch targets, "Loading engine…" state, visibilitychange engine pause

### Add After Validation (v1.29.x)

- [ ] Full SF18 single-thread option (opt-in or auto-selected on desktop) — add after the lite net ships and user bandwidth is observed
- [ ] Variation tree display (inline in move list) — show fork points as indented sub-lines, clickable navigation
- [ ] "Copy FEN" / "Copy PGN" buttons — power-user convenience
- [ ] Paste-a-FEN / paste-PGN entry — once the board surface is stable, add this entry point; lower priority because the three typed entry points cover in-product use cases

### Future Consideration (v2+)

- [ ] Multi-thread WASM on an isolated desktop document — gated on resolving COOP/COEP vs. OAuth tradeoff; deferred per D-3
- [ ] Promote / demote variation in tree — tree-editing UI, mobile-hostile; defer until demand surfaces
- [ ] Tablebase integration for ≤7-piece endgames
- [ ] Save named analyses (requires schema, auth coupling, contradicts D-4)
- [ ] Annotation symbols (!, ?, !!) with click-to-annotate UI

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `useStockfishEngine` hook (WASM + Web Worker + UCI) | HIGH (blocks everything) | HIGH | P1 |
| `EvalBar` component | HIGH | LOW | P1 |
| `PvLines` component (MultiPV 1–2, clickable) | HIGH | MEDIUM | P1 |
| `useChessAnalysis` branching hook | HIGH | HIGH | P1 |
| Engine start/stop toggle | HIGH | LOW | P1 |
| `/analysis` route + lazy WASM load | HIGH | MEDIUM | P1 |
| Entry-point wiring (3 entry points) | HIGH | LOW | P1 |
| URL state encoding/decoding | HIGH | MEDIUM | P1 |
| Tactic mode overlay (Phase 135 refactor) | HIGH (regression risk) | MEDIUM | P1 |
| Eval arrow on board | MEDIUM | LOW | P1 |
| Mobile layout (eval bar below board, scrollable PV) | HIGH | MEDIUM | P1 |
| Stored PV as initial mainline (D-5) | MEDIUM | LOW | P1 |
| "Loading engine…" state | MEDIUM | LOW | P1 |
| visibilitychange engine pause | MEDIUM | LOW | P1 |
| Full SF18 (non-lite) option | MEDIUM | LOW | P2 |
| Variation tree display | MEDIUM | MEDIUM | P2 |
| Copy FEN / Copy PGN buttons | LOW | LOW | P2 |
| Paste-a-FEN entry | MEDIUM | MEDIUM | P2 |

**Priority key:**
- P1: Must have for v1.29 launch
- P2: Add post-launch when core board is stable
- P3: Defer to v2+

---

## Competitor Feature Analysis

| Feature | Lichess | Chess.com | FlawChess v1.29 Plan |
|---------|---------|-----------|----------------------|
| Engine build | Multi-thread WASM SF16+, NNUE ~85MB; single-thread fallback | Proprietary server-side (no browser WASM) | Single-thread SF18-lite-single (~7MB); multi-thread deferred |
| Eval bar | Yes, vertical beside board | Yes, with evaluation cloud | Yes, graphical + numeric |
| MultiPV lines | Up to 5 | Up to 3 | 2 (1 line + 1 alternative) |
| Variation tree | Full branching, inline in move list, promote/demote | Full branching, click in notation | v1: simple fork, no promote/demote |
| Paste FEN/PGN | Yes (prominent) | Yes | v1: NO — entry from 3 typed entry points only |
| Cloud eval (precomputed) | Yes, cloud-eval API covers popular positions | Yes, server-side | Yes — stored PVs in game_positions ARE the precomputed half |
| URL state | FEN in path (`/analysis/FEN`) | FEN + PGN in URL hash | FEN + move sequence as query params |
| Opening name | Yes (from lichess DB) | Yes | Yes (reusing existing `findOpening` from lichess DB) |
| Tablebase | Yes (for ≤7 pieces) | Yes | No (v1) |
| Tactic context | No — separate study/puzzle system | No | YES — unique: auto-loads tactic context with motif badge, depth counter, PV line |
| Save analysis | Yes (studies, requires account) | Yes (requires account) | No server persistence — URL is the save mechanism |
| Mobile support | Decent but not primary | Mobile app separate | Mobile-first PWA, touch-optimized |

FlawChess's genuine differentiator vs both competitors: the board opens pre-seeded with the user's tactic or game context (stored PV, motif badge, flaw chip). Neither lichess nor chess.com integrate analysis with a user's personal game flaw history in this way.

---

## Sources

- [lichess.org/analysis](https://lichess.org/analysis) — feature reference (eval bar, variation tree, URL state, MultiPV display)
- [lichess-org/stockfish.js (GitHub)](https://github.com/lichess-org/stockfish.js) — archived single-thread WASM build; confirmed ~1.4MB uncompressed, Web Worker postMessage/UCI pattern
- [stockfish npm package](https://www.npmjs.com/package/stockfish) — nmrugg's SF18; `stockfish-18-single` and `stockfish-18-lite-single` (~7MB) confirmed; no CORS headers required for single-thread
- [lichess-org/stockfish-web (GitHub)](https://github.com/lichess-org/stockfish-web) — multi-thread build, confirms PTHREAD_POOL_SIZE=8 and multi-thread header requirements
- [chess.com/analysis](https://www.chess.com/analysis) — feature comparison (server-side engine, MultiPV up to 3, variation tree)
- [Creating a React-based Chess Game with WASM Bots (eddmann.com)](https://eddmann.com/posts/creating-a-react-based-chess-game-with-wasm-bots-in-typescript/) — confirmed Web Worker + React hook UCI integration pattern
- [chess.com analysis help center](https://support.chess.com/en/articles/8583825-how-do-i-use-the-analysis-board) — promote variation, delete variation, navigation arrow keys behavior
- Direct codebase inspection: `frontend/src/hooks/useChessGame.ts`, `useChessGame.ts`, `useTacticLine.ts`, `frontend/src/components/board/BoardControls.tsx`, `ChessBoard.tsx`, `arrowGeometry.ts`, `arrowColor.ts`, `TacticLineExplorer.tsx`, `tacticDepth.ts` — reuse map verified against actual implementation
- SEED-066 locked design decisions (D-1 through D-5) — sourced from project

---

*Feature research for: FlawChess v1.29 — Live-Engine Analysis Page*
*Researched: 2026-06-26*
