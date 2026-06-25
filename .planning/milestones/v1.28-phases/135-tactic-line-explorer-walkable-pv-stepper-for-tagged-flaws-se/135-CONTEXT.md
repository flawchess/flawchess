# Phase 135: Tactic Line Explorer — walkable PV stepper for tagged flaws - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A full-screen Dialog that turns each **tagged** flaw into a walkable lesson: a large board +
linear SAN ladder + `BoardControls` preloaded with the stored Stockfish PV, stepping through
the **missed** line (engine PV the player should have played) and the **allowed** line (the
punishment the opponent could have played). A depth counter ticks down to the tactic punchline
(depth-0 move highlighted), then a few payoff plies show the material/mate landing. New
`tactic-lines` endpoint surfaces `game_positions.pv` (today only `best_move` is exposed).
Entry points: an `Explore` secondary button on the flaw card and on the game card, gated on
the flaw being tagged.

**Locked by SEED-065 (not re-discussed):** the full-screen Dialog surface; Missed/Allowed
toggle (enabled only when BOTH lines exist, default = missed); the depth mechanic (decrement
forward / increment back, floor 0, depth-0 highlighted, payoff plies past the tactic); the
linear SAN ladder anchored to the **real game ply** (not 1) with click-to-jump + keyboard nav;
sourcing missed line from `positions[n].pv` and allowed line from `positions[n+1].pv`; reusing
`tacticDepth.ts` for the allowed +1 decision-anchor offset.

**Out of scope:** new motifs / detector changes (frozen at 134); any new Stockfish/eval
(PVs already stored); the Openings candidate-move table (a tactic line has no branches);
prod re-backfill.
</domain>

<decisions>
## Implementation Decisions

### Entry-point UX (discussed)
- **D-01 (modal stacking):** Explore launched from the game-card context opens as a **second
  Dialog stacked on top** of the Game modal. Closing Explore **returns** the user to the Game
  view exactly where they were (not a replace/close-underneath). Per SEED-065's "modal-on-modal
  acceptable" note. Verify nested-dialog focus/scroll-trap behavior on mobile (SEED-065 risk).
- **D-02 (game-card disabled state):** The game-card Explore button is **always visible** and
  **disabled (greyed)** when the eval chart's currently-parked position is **not** a tagged
  flaw, with a tooltip/`aria-label` explaining why (e.g. "Select a tagged flaw to explore").
  Stable layout, discoverable. Matches SEED-065's "disabled when not a tagged flaw."
- **D-03 (game-card placement):** Place Explore **below the eval chart, adjacent to the
  flaw-marker navigation** the user already interacts with — keeps the action next to the
  flaw it targets. Honor mobile parity.
- **D-04 (flaw-card button row):** Pull "Game" out of the flaw-card header into a **dedicated
  button row** for **all** flaw cards (tagged and untagged). Untagged flaws show a row with
  **just the "Game" button** (Explore omitted); tagged flaws show **Explore + Game**, both
  `brand-outline` (secondary). One consistent card layout, no two-variant maintenance. Apply
  to mobile too.
- **D-05 (mobile surface — full-screen Dialog on desktop, drawer on mobile):** The explorer
  uses the **full-screen Dialog on desktop**, but on **mobile it renders as a drawer** (reusing
  the project's existing drawer pattern) so it takes the **full width of the screen** rather than
  a width-constrained modal. This directly resolves the SEED-065 mobile risk flagged in D-01
  (nested-dialog focus/scroll-trap behavior on mobile). The stacking/return-to-Game behavior from
  D-01 still applies on both surfaces; the drawer must restore the user to the Game view on close.

### Claude's Discretion (record the seed's leans; planner/researcher finalize)
- **Explore gating & single-line flaws:** Explore appears for **any tagged flaw with ≥1 line**.
  A "tagged" flaw already passes the chip gate (`_TACTIC_CHIP_CONFIDENCE_MIN = 70`,
  `library_repository.py:60`), so no extra trust bar is needed — gating on "tagged" already
  means trustworthy. When only one orientation is tagged (missed-only or allowed-only), Explore
  **opens with that single line and the toggle is hidden** (toggle requires both lines per
  SEED-065). No motif families excluded beyond the existing suppression list.
- **Payoff length & short PVs:** Walk the tactic move + **~2–4 payoff plies** past the depth-0
  punchline, then truncate the noisy ~12-ply PV tail (tactic usually fires at depth 2–6).
  Handle PVs **shorter than the tactic depth gracefully** — no negative counters, no crash
  (SEED-065 risk). Exact payoff count is the executor's call within this band.
- **Backend contract:** A **dedicated lazy-fetch endpoint** (lean: e.g.
  `GET /library/flaws/{game_id}/{ply}/tactic-lines`) returning **both PVs + display depths +
  motif + tactic-move index**. UCI→SAN conversion location (server-side display-ready SAN vs
  raw UCI converted client-side with chess.js) left to research/planning — pick the cleaner
  contract; tests must cover the n vs n+1 PV anchoring and the allowed +1 offset.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec / source of truth
- `.planning/seeds/SEED-065-tactic-line-explorer.md` — the full locked design (surface, toggle,
  depth mechanic, ladder, entry points, data sourcing, codebase map, risks). Primary spec.

### Prior-phase decisions that constrain this phase
- `.planning/phases/129-tactic-filter-ui/129-CONTEXT.md` — tactic depth conventions, chip
  gating, orientation semantics (missed/allowed), `_TACTIC_CHIP_CONFIDENCE_MIN = 70`.

### Depth / display conventions (MUST reuse, do not recompute)
- `frontend/src/lib/tacticDepth.ts` — `toDisplayDepth`, `toDisplayDepthForOrientation`,
  `ALLOWED_DECISION_DEPTH_OFFSET`, `DEPTH_DISPLAY_OFFSET`. Explorer depth labels MUST match the
  miniboard via these helpers.
- `app/repositories/library_repository.py` — `ALLOWED_DECISION_DEPTH_OFFSET` (mirror of the TS
  helper), `_TACTIC_CHIP_CONFIDENCE_MIN` (line 60), `best_move=pos_at.best_move` PV-surfacing
  site (line ~854 — where `pv` would be added).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/hooks/useChessGame.ts` — `position`, `moveHistory`, `currentPly`, `goForward`,
  `goBack`, `goToMove`, `loadMoves`, `lastMove`, keyboard arrows, `replayTo`. Clone into a new
  `useTacticLine` hook fed the PV converted to SAN.
- `frontend/src/components/board/ChessBoard.tsx` — big board + custom `ArrowOverlay`
  (`react-chessboard` v5, `allowDrawingArrows:false`). Reuse for the explorer board.
- `frontend/src/components/board/BoardControls.tsx` — back/forward/reset/flip + `infoSlot` for
  the depth readout.
- `frontend/src/components/board/MiniBoard.tsx` + `arrowGeometry.ts` (`squareToCoords`,
  `buildArrowPath`) — arrow + depth-badge rendering convention to mirror at the root position.
- `frontend/src/lib/arrowColor.ts`, `frontend/src/lib/sanToSquares.ts` (`sanToSquares`,
  `uciToSquares`, `fenAfterMove`), `frontend/src/components/library/TacticMotifChip.tsx`,
  `frontend/src/lib/tacticMotifDefinitions.ts`.

### Established Patterns
- Flaw-card Dialog entry already exists: `FlawCard.tsx` has the in-header "Game" `Swords`
  button → Dialog with `LibraryGameCard initialPly={flaw.ply}`. D-04 moves "Game" into a row
  and adds Explore beside it.
- Endpoint shape: existing `app/routers/library.py` GETs (`/flaws`, `/games/{game_id}`,
  `/tactic-comparison`) are the pattern for the new `tactic-lines` route (relative paths under
  the `/library` prefix, `response_model=...`).
- Button variants: secondary = `variant="brand-outline"` (never hand-rolled `bg-*`).

### Integration Points
- Backend PV surfacing: `app/repositories/library_repository.py` (~line 854) + `FlawListItem` /
  schemas in `app/schemas/library.py`; `game_positions.pv` (space-joined UCI, ~12 plies),
  `game_positions.move_san`, `eval_cp/mate`. Tactic logic: `app/services/tactic_detector.py`
  (`_parse_pv`), `app/services/flaws_service.py` (`_detect_tactic_for_flaw`).
- Frontend entry points: `FlawCard.tsx` (rendered from `pages/library/FlawsTab.tsx`) and
  `components/results/LibraryGameCard.tsx` (eval chart + per-ply nav + flaw markers).

</code_context>

<specifics>
## Specific Ideas

- "Explore + Game as two secondary (`brand-outline`) buttons" in a dedicated flaw-card row.
- Depth counter ticks down to the punchline; depth-0 move highlighted so the user can't miss
  the tactic; payoff plies blue + label-less.
- Game-card Explore targets whatever flaw the eval chart is cycled/parked on — marker-click is
  NOT used (clicking the flaw tag already cycles flaws in the chart).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Cross-referenced todos were all keyword-noise
matches unrelated to the tactic line explorer; none folded or carried.)

</deferred>

---

*Phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se*
*Context gathered: 2026-06-24*
