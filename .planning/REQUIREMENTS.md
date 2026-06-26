# Requirements: FlawChess — v1.29 Live-Engine Analysis Page

**Defined:** 2026-06-26
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report. v1.29 extends this with a free-play analysis surface so users can explore any position with a live engine without leaving FlawChess.

**Source:** SEED-066 (distilled from a 2026-06-25 `/gsd-explore` session; locked decisions D-1..D-5). Domain research in `.planning/research/` (SUMMARY.md, STACK/FEATURES/ARCHITECTURE/PITFALLS).

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase. Almost entirely frontend; no backend schema or new endpoints (D-4 — the Phase 135 `tactic-lines` endpoint already surfaces stored PVs).

### Live Engine (ENGINE)

- [ ] **ENGINE-01**: User sees a live evaluation (eval bar + numeric centipawn/mate) of the current board position, computed in-browser by a single-thread WASM Stockfish
- [ ] **ENGINE-02**: User sees the engine's top 1–2 candidate lines (MultiPV) as clickable SAN sequences with a depth indicator
- [ ] **ENGINE-03**: User sees the engine's best move rendered as an arrow on the board
- [ ] **ENGINE-04**: User can toggle the engine on/off, with a visible "loading engine" / "analyzing" state; the board and move stepper stay interactive while the WASM engine initializes
- [ ] **ENGINE-05**: Engine re-analyzes automatically (debounced) when the position changes, bounded by a movetime/node cap so low-end devices stay responsive

### Analysis Board (BOARD)

- [ ] **BOARD-01**: User can make any legal move from any position; a mid-line move forks the line into a variation rather than being rejected
- [ ] **BOARD-02**: User can navigate the move tree (back/forward, jump to any move, reset to start) and flip the board
- [ ] **BOARD-03**: User can input moves by drag-drop and by click-to-click (touch)
- [ ] **BOARD-04**: Board/variation state is encoded in the URL so a position is shareable/bookmarkable, with no server-side persistence
- [ ] **BOARD-05**: User sees the move list and can click any move to jump to it; the v1 display shows the main line plus the single active variation (flat — full nested-tree display deferred to v2)

### Route & Entry Points (ROUTE)

- [ ] **ROUTE-01**: User can reach a standalone `/analysis` page, lazy-loaded so the engine bundle is fetched only on this route
- [ ] **ROUTE-02**: User can open the analysis board pre-loaded from a tactic card, a game-review ply, and an opening position, carrying the relevant position and context

### Tactic Mode (TACTIC)

- [ ] **TACTIC-01**: In tactic mode the board opens at the flaw position with the stored PV as the initial mainline (D-5); the live engine takes over the moment the user deviates from or walks past the stored line
- [ ] **TACTIC-02**: Tactic mode shows the motif badge, missed/allowed framing, depth-to-punchline counter, and next/prev-tactic rail — preserving every Phase 135 behavior (depth-0 highlight, missed/allowed +1 offset via `tacticDepth.ts`, real-game-ply move numbering, tactic-rail state)
- [ ] **TACTIC-03**: The standalone Tactic Line Explorer modal is retired once tactic-mode parity is verified (regression-gated); all former entry points are repointed to `/analysis`

### Platform Hardening (PLAT)

- [ ] **PLAT-01**: The live engine runs single-thread WASM with no site-wide cross-origin-isolation (COOP/COEP) headers, so Google OAuth and iOS Safari stay unaffected; the absence of isolation headers is CI-guarded
- [ ] **PLAT-02**: Engine WASM/NNUE assets load efficiently on mobile (lite ~7 MB build, iOS Cache-API-limit safe, PWA service-worker `*.wasm` handling verified), and the engine pauses when the tab is hidden

## v2 Requirements

Deferred to a future release. Tracked but not in this roadmap.

### Analysis Board (BOARD)

- **BOARD-V2-01**: Paste-a-FEN / paste-PGN entry box (the three typed entry points cover all in-product use cases for v1)
- **BOARD-V2-02**: Full nested variation-tree display with all fork points shown inline in the move list
- **BOARD-V2-03**: Promote / demote / delete variation

### Live Engine (ENGINE)

- **ENGINE-V2-01**: Multi-thread WASM engine as a desktop-only progressive enhancement on a hard-loaded, cross-origin-isolated `/analysis` document (D-3 — explicitly deferred; reopens the COOP/COEP + OAuth + iOS analysis)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep. Anti-features carried from research (PITFALLS.md / SUMMARY.md) and SEED-066's scope boundary.

| Feature | Reason |
|---------|--------|
| `SharedArrayBuffer` / site-wide COOP+COEP cross-origin-isolation headers | Breaks Google OAuth popup (`window.opener`) and is unreliable on iOS Safari; SPA documents can't toggle isolation per-route (D-3) |
| Cloud-eval API (chessdb.cn / lichess cloud eval) | The stored PVs already serve as the precomputed-eval half; external eval APIs are a later optimization, not v1 |
| Server-side persistence of analyses (saved-analyses table) | Ephemeral by design — state lives in the URL (D-4); no schema, no auth coupling |
| Full SF18 single-thread build (HCE, no NNUE) | ~30–100 MB and paradoxically weaker than the ~7 MB lite-single NNUE build |
| Real-time play | FlawChess is post-game analytics (consistent with SEED-012 non-goals) |
| PGN annotation / comment system, tablebase integration, social-share buttons beyond copy-URL | Bloat against the "trimmed of bloat" goal; not core to the analysis use case |

## Traceability

Populated during roadmap creation by the roadmapper.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENGINE-01 | TBD | Pending |
| ENGINE-02 | TBD | Pending |
| ENGINE-03 | TBD | Pending |
| ENGINE-04 | TBD | Pending |
| ENGINE-05 | TBD | Pending |
| BOARD-01 | TBD | Pending |
| BOARD-02 | TBD | Pending |
| BOARD-03 | TBD | Pending |
| BOARD-04 | TBD | Pending |
| BOARD-05 | TBD | Pending |
| ROUTE-01 | TBD | Pending |
| ROUTE-02 | TBD | Pending |
| TACTIC-01 | TBD | Pending |
| TACTIC-02 | TBD | Pending |
| TACTIC-03 | TBD | Pending |
| PLAT-01 | TBD | Pending |
| PLAT-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition for v1.29 Live-Engine Analysis Page*
