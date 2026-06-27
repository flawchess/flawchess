---
title: Full-Game Analysis Board refinement (v1.29 follow-on)
date: 2026-06-27
context: /gsd-explore session refining post-v1.29 analysis-board UX. Source of truth for the Phase 140 plan.
milestone: v1.29 Live-Engine Analysis Page
---

# Full-Game Analysis Board — refined design

Refines the v1.29 `/analysis` board (Phases 136–139). The board today has two
disjoint entry modes (free-play `?fen=` single position; tactic mode
`?game_id&flaw_ply` loading only the stored PV). The full-featured `EvalChart`
(with slider) lives in the **game card**, not the board. This refinement
collapses entry into one model and relocates the chart onto the board.

## Locked decisions

### Entry-point consolidation
- **Game card** (`LibraryGameCard.tsx`): `Explore` + `Analyze position` → a single
  **`Analyze`** button. Opens `/analysis?game_id=X&ply=Y` where `ply` is the
  eval-chart slider's currently-parked ply (`hoverPly`).
- **Flaw card** (`FlawCard.tsx`): `Explore` + `Game` → a single **`Analyze`** button.
  Opens the full game at `flaw.ply`. The flaw's missed/allowed tag is visible in
  the move list; the user clicks it to expand the PV (NO auto-expand).
  - The `Game` modal path (inline `LibraryGameCard` with `initialPly`) is **deleted**.
- **Openings "Analyze position"** (`?fen=`, free-play single position from Phase
  138-03) **stays as-is** — out of scope for this phase.

### Loading model
- New URL form `/analysis?game_id=X&ply=Y` fetches the **whole game** (moves ply
  0 → end, stored `eval_series`, flaw markers) — the same data `LibraryGameCard`
  already loads via its game-by-id fetch. Board loads the full mainline via
  `loadMainLine`, positioned at `ply`.
- This is a **new data dependency for the `/analysis` route** (today it only gets
  a FEN or the tactic-lines payload). Reuse the existing game-fetch hook/endpoint;
  no new backend (milestone D-4: no schema/endpoints).
- `?fen=` free-play and `?game_id&flaw_ply` tactic-only URLs may remain for
  backward compat, but the primary path becomes `?game_id&ply`.

### Layout (desktop)
- Board left; **eval chart with slider directly below the board**.
- Move list right, **height matched to the board**.
- **Board controls below the move list** (chess.com / lichess pattern), moved
  from their current location.

### Eval chart / slider behavior
- Chart plots the **game's stored per-ply evals** (whole-game shape). The slider
  scrubs the **main game line**, syncing the move-list highlight and the board.
- Entering a sideline **parks the slider at the fork point** (dimmed/inactive).
  Chart = the game; the live WASM engine (EvalBar + EngineLines) covers the
  actual current node. Clean source separation, matches lichess.
- The `EvalChart` component is reused on the board; it also remains in the game
  card as the inline preview + ply selector that seeds `Analyze`.

### Move list + tactics
- Flaw plies render **inline missed/allowed tags** in the move list. Requires the
  game's flaw markers (`missed_tactic_motif` / `allowed_tactic_motif`).
- Clicking a tag fetches that flaw's stored PV (`tactic-lines` endpoint,
  on-demand) and **unfolds it as a sideline** in the move list, navigable with
  the board controls like any other sideline.
- Within a PV sideline the user may branch a **sub-sideline** → the move tree must
  support **two nesting levels**: game line → PV line → PV sub-sideline. Today
  `VariationTree` renders only a single active variation (one level).
- `TacticModeOverlay` (Phase 139: motif badge, depth-to-punchline counter,
  missed/allowed, next/prev-tactic rail) **stays**, but becomes **contextual** —
  activated when a PV tag is clicked / while navigating that PV line — instead of
  being URL-driven at page load.

### Mobile (recommendation — confirm in UI spec)
- Stacking order: board → eval chart → live engine lines → move list → controls.
- Per CLAUDE.md, all changes apply to mobile too (drawer/stacked variants).

## Hardest parts (flag for planning)
1. **Two-level variation nesting** in `VariationTree` + `useAnalysisBoard`
   (fork-within-fork navigation + rendering).
2. **Contextual `TacticModeOverlay`** re-wiring (driven by active PV node, not URL).
3. **Game-by-id fetch on the `/analysis` route** — new for this page; wire the
   existing fetch + flaw markers + eval series into the board shell.

## Key files
- `frontend/src/pages/Analysis.tsx` — page shell, URL parsing, mode wiring
- `frontend/src/hooks/useAnalysisBoard.ts` — branching move tree (needs 2-level nesting)
- `frontend/src/components/analysis/VariationTree.tsx` — move list (inline tags + nesting)
- `frontend/src/components/analysis/TacticModeOverlay.tsx` — contextual activation
- `frontend/src/components/library/EvalChart.tsx` — relocated below board
- `frontend/src/components/results/LibraryGameCard.tsx` — unified `Analyze` button
- `frontend/src/components/library/FlawCard.tsx` — unified `Analyze`, drop `Game` modal
- `frontend/src/lib/analysisUrl.ts` — add `?game_id&ply` builder
- `frontend/src/hooks/useLibrary.ts` — `useTacticLines` (per-tag PV fetch)

## Next step
Run `/gsd-ui-phase 140` (or `/gsd-discuss-phase 140`) to plan against this note.
