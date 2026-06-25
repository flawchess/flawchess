---
id: SEED-065
status: promoted
promoted_to: Phase 135 (v1.28) on 2026-06-24
planted: 2026-06-24
planted_during: v1.28 Tactic Tagging
trigger_when: ready to promote to a phase in the CURRENT milestone (user intends to convert this seed into a phase next). Depends on tactic tags being trustworthy enough to walk through line-by-line — coordinate with SEED-064 (tactic precision hardening); a low-precision tag walked move-by-move is worse than a chip.
scope: Medium-Large (frontend modal + new explorer hook + board reuse + one backend PV-surfacing change)
source: /gsd-explore session 2026-06-24 (this file is the distilled output). Codebase map captured inline below.
---

# SEED-065: Tactic Line Explorer

## Why This Matters

Today a flaw card shows the *decision position* as a static miniboard: a red arrow for the
move played and a blue arrow for the engine's best move, each with a tactic-depth number on
the target square. That tells the user a tactic existed and how deep it was — but not *what
it was*. The user cannot step through the line and watch the fork/pin/mate actually land.

The Tactic Line Explorer turns each tagged flaw into a walkable lesson: a large board with
forward/back controls and a move list, preloaded with the Stockfish PV, that steps the user
through the missed tactic (the line they should have played) and the allowed tactic (the
punishment the opponent could have played). The depth counter ticks down to the punchline so
the user sees *why* the move was a mistake. Goal: comprehension, not just a label.

## Locked Design Decisions (from the explore session)

**Surface — full-screen Dialog modal** (same pattern as the existing flaw "Game" modal).
- Desktop: board left, SAN move ladder right, `BoardControls` + depth readout under the board.
- Mobile: stacked (board → ladder → controls). Mobile-first PWA rules apply.

**Two lines, toggle stepper:**
- A Missed / Allowed toggle at the top. **Toggle is enabled only when BOTH lines exist;**
  default selection = **missed**.
- **Missed line** = the line the player should have played. Walk the engine PV (the blue
  branch). At the root (decision position) show BOTH arrows like the miniboard: blue
  best-move arrow (label = missed depth) and red played-move arrow (label = allowed depth).
  First forward step follows the BLUE move; subsequent steps follow the engine PV.
- **Allowed line** = the punishment the opponent could have played. The PV is anchored AFTER
  the flaw move, so the first move you walk forward is the RED flaw move, then the blue
  opponent PV takes over. At the root show both arrows but **only the red flaw move carries a
  depth label**; the blue best-move arrow is reference-only (no label). Same logic as the
  miniboard.
- After the root, every ply is pure engine PV → **blue arrow only**, depth number on its
  target square.

**Depth mechanic:**
- The depth number = plies remaining until the tactic motif fires. **Decrements going
  forward, increments going back, floors at 0.**
- The **depth-0 move is highlighted** as the tactic punchline (don't let the user miss it).
- Walk a few plies **past** the tactic into the payoff (so the user sees the material won /
  mate landed); these payoff arrows are blue and label-less. Truncate before the noisy PV
  tail (full stored PV is ~12 plies; tactic usually fires at depth 2–6). Suggested:
  tactic move + ~2–4 payoff plies.

**Move list — linear SAN ladder** (NOT the Openings WDL/candidate-move table; a tactic line
has no branches, so candidate-move statistics don't apply).
- Move numbers **anchor to the real game ply**, not 1 (e.g. `23. Nf5  23… Qd7  24. Nxe7+`),
  so it lines up with the score sheet. For the allowed line, the ladder's first entry is
  literally the move the player played (the red move), then the opponent's punishment.
- Current ply highlighted; click-to-jump to any ply; keyboard arrow navigation (the
  `useChessGame` pattern already has ArrowLeft/ArrowRight built in).

**Entry points — secondary (`brand-outline`) buttons:**
- **Flaw card:** pull the existing "Game" button OUT of the card header into a dedicated
  button row, and add an **Explore** button next to it (Explore + Game as two secondary
  buttons). Explore renders **only when the flaw is tagged** (has a missed and/or allowed
  tactic motif). Untagged flaws show no Explore button.
- **Game card:** an **Explore** secondary button alongside the eval chart. It targets the
  **currently selected flaw** (whatever the eval chart is cycled/parked on) and is
  **disabled when the current position isn't a tagged flaw**. (Marker-click is NOT used —
  clicking the flaw tag already cycles through flaws in the eval chart.)

**Preload / data sourcing:**
- The PV already exists in the DB: `game_positions.pv` (space-joined UCI, ~12 plies). Missed
  line = `positions[n].pv` (flaw_ply PV, no flaw move pushed). Allowed line =
  `positions[n+1].pv` (flaw_ply+1, flaw move pushed). **No endpoint surfaces `pv` today** —
  the flaw payload only carries the single `best_move`. This feature needs `pv` (+ tactic
  depths) surfaced.
- **Open sub-decision (lean: lazy-fetch):** include the PV in the flaw-list payload vs. a
  small dedicated endpoint hit on modal open. Recommend **lazy-fetch on open** — flaw lists
  can be large and the PV is only needed on demand. A dedicated endpoint like
  `GET /library/flaws/{game_id}/{ply}/tactic-lines` returning both PVs (UCI + SAN) and the
  display depths is the clean shape.
- Reuse `frontend/src/lib/tacticDepth.ts` (`toDisplayDepthForOrientation`,
  `ALLOWED_DECISION_DEPTH_OFFSET`) for the +1 allowed-line decision-anchor offset so the
  explorer's depth labels match the card's.

## Existing Pieces To Build On (codebase map, 2026-06-24)

- **Miniboard + arrow/depth rendering:** `frontend/src/components/board/MiniBoard.tsx`
  (arrows carry `label`/`labelColor`; depth badge is an SVG `<text>` on the target square).
  Shared geometry `frontend/src/components/board/arrowGeometry.ts`
  (`squareToCoords`, `buildArrowPath`).
- **Big board + own arrow overlay:** `frontend/src/components/board/ChessBoard.tsx`
  (`react-chessboard` v5, `allowDrawingArrows:false`, custom `ArrowOverlay` via the same
  geometry). Arrow colors `frontend/src/lib/arrowColor.ts`.
- **Board controls:** `frontend/src/components/board/BoardControls.tsx`
  (back/forward/reset/flip; `infoSlot` for the depth readout).
- **Navigation hook to clone:** `frontend/src/hooks/useChessGame.ts`
  (`position`, `moveHistory`, `currentPly`, `goForward`, `goBack`, `goToMove`, `loadMoves`,
  `lastMove`; keyboard arrows; `replayTo`). A new `useTacticLine` hook can feed `loadMoves`
  the PV converted to SAN.
- **Openings explorer (reference for feel only):** `frontend/src/pages/Openings.tsx`,
  `frontend/src/components/move-explorer/MoveExplorer.tsx` (candidate-move table — do NOT
  reuse for the ladder), `frontend/src/pages/openings/ExplorerTab.tsx`.
- **Flaw card (entry point + miniboard usage):** `frontend/src/components/library/FlawCard.tsx`
  (currently has the in-header "Game" `Swords` button → Dialog with
  `LibraryGameCard initialPly={flaw.ply}`). Rendered from
  `frontend/src/pages/library/FlawsTab.tsx`.
- **Game card + eval chart slider:** `frontend/src/components/results/LibraryGameCard.tsx`
  (embeds the EvalChart with per-ply navigation + flaw markers).
- **Flaw data model / schema:** `app/models/game_flaw.py` (`GameFlaw`,
  `missed_/allowed_tactic_motif|piece|confidence|depth`, `fen` = pre-flaw decision board);
  `app/models/game_position.py` (`best_move`, **`pv`**, `eval_cp/mate`, `move_san`);
  `app/schemas/library.py` `FlawListItem` (mirror `frontend/src/types/library.ts`);
  `app/repositories/library_repository.py` (`best_move=pos_at.best_move`, ~line 849 — where
  `pv` would be surfaced); tactic logic in `app/services/tactic_detector.py` (`_parse_pv`)
  and `app/services/flaws_service.py` (`_detect_tactic_for_flaw`).
- **Helpers:** `frontend/src/lib/sanToSquares.ts` (`sanToSquares`, `uciToSquares`,
  `fenAfterMove`), `frontend/src/lib/tacticDepth.ts`,
  `frontend/src/lib/tacticMotifDefinitions.ts`, `frontend/src/components/library/TacticMotifChip.tsx`.

## Suggested Phase Shape (when promoted)

1. **Backend:** surface the two PVs (+ display depths, motif, tactic-move index) for a flaw —
   dedicated `tactic-lines` endpoint; convert UCI→SAN server-side or send UCI and convert
   client-side with chess.js. Tests for the n vs n+1 PV anchoring and the allowed +1 offset.
2. **Frontend hook:** `useTacticLine` (PV → positions/arrows/depths, missed/allowed toggle,
   payoff truncation, depth-0 highlight).
3. **Frontend modal:** `TacticLineExplorer` Dialog (board + SAN ladder + controls + toggle),
   desktop and mobile layouts; `data-testid`s per the browser-automation rules.
4. **Entry points:** flaw-card button row (Explore + Game out of header); game-card Explore
   button wired to the eval chart's selected flaw with the tagged/disabled rule.

## Risks / Watch-outs

- **Tag precision (couples to SEED-064):** walking a wrong tag move-by-move is worse than a
  wrong chip. Don't ship the explorer on top of the low-precision geometric motifs without
  the precision hardening, or gate which motifs get an Explore button by confidence.
- **PV may not reach the tactic / may be short** for some positions — handle PVs shorter than
  the tactic depth gracefully (no negative counters, no crash).
- **Modal-on-modal** when Explore is opened from inside the game "Game" modal — acceptable
  (close returns to the game view), but verify focus/scroll trap behavior on mobile.
- **Two miniboard depth conventions** (missed vs allowed +1 offset) must stay consistent
  between card and explorer — reuse `tacticDepth.ts`, don't recompute.
