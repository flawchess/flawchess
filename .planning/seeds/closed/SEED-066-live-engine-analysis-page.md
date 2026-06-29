---
id: SEED-066
status: dormant
planted: 2026-06-25
planted_during: /gsd-explore session 2026-06-25 (this file is the distilled output)
trigger_when: when interactive free-analysis is prioritized for a milestone, OR when users ask to "explore the position freely" / want a live engine beyond the stored line, OR right after SEED-065's Tactic Line Explorer (Phase 135) proves out and consolidation onto one board surface is wanted. Shares client-WASM groundwork with [[SEED-012-client-side-stockfish-tactics]] — coordinate if both go near-term.
scope: Medium-Large — mostly frontend (WASM engine worker + React hook + shared analysis board + entry-point wiring); near-zero backend (ephemeral, no schema)
---

# SEED-066: Live-engine Analysis page (subsumes the Tactic Line Explorer)

## Why This Matters

SEED-065 (Phase 135) shipped a **Tactic Line Explorer**: a modal that steps through the
*precalculated* Stockfish PV stored in `game_positions.pv`. It's a walkable lesson, but the
line is fixed — the user can't deviate, make their own move, or ask "what if I'd played
this instead?". For that they currently have to leave FlawChess and click out to
lichess/chess.com, where a live engine lets them explore freely.

This seed closes that gap **inside** FlawChess: a standalone analysis surface where the user
makes any legal move from any position (branching off the stored line) and a **live
in-browser Stockfish** evaluates the current position (eval + top 1–2 lines) as they go.
It's lichess's analysis board, deliberately trimmed of bloat.

The framing insight: FlawChess already owns the *server-side* half of lichess's design.
Lichess splits analysis into (a) a server **cloud-eval cache** of precomputed evals and
(b) **browser WASM** for live computation of arbitrary positions. FlawChess's precomputed
PVs in `game_positions` / `game_flaws` **are** the cloud-eval half. The genuinely new piece
is the browser-side live engine for free-play positions.

## How lichess actually does it (the factual unknown that prompted this)

- Stockfish runs **in the browser** via WebAssembly (`lila-stockfish-web`, NNUE). No server
  CPU is spent on the analysis board.
- Default build is **multi-threaded** (Web Workers + `SharedArrayBuffer`), which requires
  the page to be **cross-origin isolated** (`COOP: same-origin` + `COEP:
  require-corp/credentialless`). When `SharedArrayBuffer` is unavailable it falls back to a
  weaker **single-threaded** build needing no special headers.
- "Stockfish 18 dev · 85MB NNUE" = the NNUE network file, downloaded once and cached. The
  85MB is the net weight, not per-position traffic.
- The server **cloud-eval cache** (`/api/cloud-eval`) returns stored evals for popular
  positions instantly; on a miss, the local WASM engine computes live. So it's "both," with
  a clean split: server = precomputed-eval cache, browser = live computation.

## Locked Design Decisions (from the explore session)

**D-1 — Standalone `/analysis` destination, reachable from anywhere.** Entry points: tactic
cards, game-review ply, opening positions, and a paste-a-FEN/PGN box. Not buried inside a
single feature.

**D-2 — Subsume the Tactic Line Explorer as a *tactic mode*, not delete it.** The analysis
board becomes the single shared surface. A "tactic" stops being its own component and becomes
**one seeded entry mode**: open the board at the flaw position with the stored PV loaded as
the initial mainline, and overlay the tactic-specific chrome (motif badge, missed/allowed
framing, next/prev-tactic rail) on top. From there the live engine lets the user step *past*
the stored line. Collapses the SEED-065 modal's duplicate board/stepping UI onto one
component; nothing of tactic value is lost.

**D-3 — Live engine: single-threaded WASM Stockfish for v1; multi-thread deferred.**
Reasoning (the "how difficult" crux):
- Single-threaded WASM SF16/17 NNUE still reaches ~depth 20–25 in a few seconds on desktop —
  wildly superhuman, far past what a human needs to *understand* a position. The multi-thread
  advantage is engine-vs-engine ELO (faster time-to-depth, deeper tactics), not comprehension.
- Three things make multi-thread expensive specifically for FlawChess:
  1. **iOS Safari undercuts it.** Mobile-first PWA; `COEP: credentialless` (the forgiving
     variant that lets cross-origin avatars load) isn't reliably supported on iOS Safari,
     which only honors `require-corp`. SharedArrayBuffer + WASM threading on iOS has also
     been memory-constrained. Mobile users fall back to single-thread regardless — so
     multi-thread is effectively a desktop-only perk.
  2. **Collides with Google OAuth popup.** Cross-origin isolation needs `COOP: same-origin`,
     but popup OAuth needs `same-origin-allow-popups` to keep the `window.opener` channel —
     and that value does **not** grant isolation. Can't have both on the same document.
  3. **SPA documents don't isolate per-route.** Isolation is a property of the *document* set
     at HTML load; client-side routing reuses the same document, so you can't toggle
     isolation for one React Router route. Multi-thread would require `/analysis` to be a
     **separately hard-loaded document** that does no OAuth and proxies/avoids cross-origin
     assets.
- **v1 = single-thread:** zero header risk, identical desktop/iOS behavior, simplest engine
  code, strong enough that users won't feel shortchanged. Multi-thread is a **deferred,
  desktop-only, feature-detected progressive enhancement** on an isolated hard-loaded
  `/analysis` document — not v1. (This is the interactive-analysis counterpart to
  [[SEED-012-client-side-stockfish-tactics]] Prerequisite 1, which already researched the
  COOP/COEP + iOS Safari mechanics for the *bulk-eval* use case.)

**D-4 — Ephemeral, no persistence.** Board/variation state lives in the **URL (FEN/PGN
encoded)** so a link is bookmarkable/shareable, but **nothing is stored server-side**. No
saved-analyses table, no schema, no auth coupling. Keeps the feature near-100% frontend.
(Considered and rejected for v1: saved analyses in Postgres, and tying into the existing
bookmarked-positions feature — revisit only if users ask to save named analyses.)

**D-5 — Stored PVs are the initial mainline; the live engine extends them.** Missed line =
`game_positions[n].pv`; allowed line = `positions[n+1].pv` (flaw move pushed) — same anchoring
as SEED-065. The live engine takes over the moment the user deviates from or walks past the
stored PV.

## Scope boundary (what v1 is NOT)

- **No DB persistence** of analyses (D-4).
- **No multi-thread / cross-origin isolation** in v1 (D-3) — and therefore no site-wide
  header changes, no avatar-proxy/OAuth-flow audit.
- **No real-time play** — FlawChess is post-game analytics, consistent with SEED-012's
  non-goals.
- **No cloud-eval API** (chessdb.cn / lichess cloud eval) — the stored PVs already serve as
  the precomputed half; external eval APIs are a later optimization, not v1.

## Existing pieces to build on (reuse map)

The chess plumbing already exists — the novel risk is wiring a WASM engine worker behind a
clean React hook. Reuse:

- **Shared board + arrow overlay:** `frontend/src/components/board/ChessBoard.tsx`
  (react-chessboard v5, custom `ArrowOverlay`), arrow geometry in
  `frontend/src/components/board/arrowGeometry.ts`, colors `frontend/src/lib/arrowColor.ts`.
- **Board controls:** `frontend/src/components/board/BoardControls.tsx` (back/forward/reset/
  flip, `infoSlot` for eval/depth readout).
- **Navigation hook to clone/extend:** `frontend/src/hooks/useChessGame.ts` (`position`,
  `moveHistory`, `currentPly`, `goForward/goBack/goToMove`, `loadMoves`, keyboard arrows).
  The new analysis board needs a *branching* variant — making a move mid-line forks the
  history rather than being rejected.
- **Tactic-mode pieces (from SEED-065 / Phase 135):** `TacticLineExplorer`, `useTacticLine`,
  `frontend/src/lib/tacticDepth.ts`, `TacticMotifChip` — these become the tactic-mode overlay
  on the shared board rather than a standalone modal.
- **PV source:** `app/models/game_position.py` (`pv`, `eval_cp/mate`, `best_move`,
  `move_san`); the `tactic-lines` endpoint added in Phase 135 already surfaces the PVs.
- **NEW — the live engine:** a `useStockfishEngine` hook wrapping a single-threaded
  `stockfish.wasm` (or `lila-stockfish-web` single-thread build) in a Web Worker; UCI
  message protocol (`position fen ...`, `go nodes/depth ...`, parse `info`/`bestmove`);
  debounced re-analysis on position change; MultiPV=1–2 for the top lines.

## Suggested phase shape (when promoted)

1. **Frontend — live engine hook:** vendor a single-thread WASM Stockfish build, wrap it in
   a Web Worker + `useStockfishEngine` hook (eval, best line(s), depth, start/stop, debounce).
2. **Frontend — branching analysis board:** a `useChessGame` variant that forks history on a
   mid-line move; eval bar + PV display; FEN/PGN URL (de)serialization.
3. **Frontend — `/analysis` page + entry points:** the standalone route, wired from tactic
   cards / game review / openings / paste-a-FEN. `data-testid`s per browser-automation rules.
4. **Refactor — fold the tactic explorer in:** re-home SEED-065's `TacticLineExplorer` as a
   tactic *mode* of the analysis board (badge + missed/allowed + next-tactic rail overlay);
   retire the standalone modal once parity is verified.
5. **Backend:** effectively none for v1 (PVs already surfaced; ephemeral state). Only touch if
   a paste-a-FEN entry needs a position-lookup convenience endpoint.

## Risks / watch-outs

- **WASM bundle weight on mobile:** the NNUE net is tens of MB. Lazy-load the engine only on
  `/analysis` (code-split), cache aggressively, and show a clear "loading engine" state so the
  PWA's initial load isn't taxed.
- **Single-thread perf on low-end phones:** cap nodes/time so a weak device doesn't spin; a
  depth/time budget with a visible "thinking" indicator beats an unbounded search.
- **Subsume-without-regression:** the tactic-mode overlay must preserve every SEED-065
  behavior (depth-0 highlight, missed/allowed +1 offset via `tacticDepth.ts`, real-game-ply
  move numbering, next-tactic navigation). Treat it as a refactor with the Phase 135 UX as the
  acceptance bar.
- **Don't drift into multi-thread by accident:** if v1 ever needs `SharedArrayBuffer`, that's
  the deferred-enhancement boundary (D-3) — stop and reopen the COOP/COEP/OAuth/iOS analysis,
  don't slip headers in site-wide.

## Cross-References

- **[[SEED-065-tactic-line-explorer]]** (closed, Phase 135) — the static-PV modal this seed
  subsumes into a live-engine *tactic mode*.
- **[[SEED-012-client-side-stockfish-tactics]]** — shares the client-WASM groundwork; its
  Prerequisite 1 already researched COOP/COEP + iOS Safari for the bulk-eval pipeline, and its
  D-8 pluggable-worker model is the *data-collection* counterpart to this seed's *interactive*
  engine. Coordinate if both go near-term (one WASM-Stockfish integration could serve both).
