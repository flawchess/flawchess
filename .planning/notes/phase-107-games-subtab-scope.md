---
title: Phase 107 scope — Games subtab frontend (card archive + Flaw-Stats panel)
date: 2026-06-05
context: /gsd-explore session scoping the next phase after the Phase 106 Games-surface backend shipped
seed: SEED-036
requirements: LIBG-01, LIBG-03
---

# Phase 107 — Games subtab frontend

Scoping decisions from the 2026-06-05 `/gsd-explore` session. Phase 107 turns the already-built
Phase 106 backend (`GET /api/library/games`, `GET /api/library/mistake-stats`) into the Library
**Games** subtab — the milestone's headline user-facing surface.

## Decisions

- **Scope = one cohesive surface.** Games subtab card archive + filters **and** the Flaw-Stats
  panel ship together in 107 (not split), because both consume Phase 106 endpoints that already
  exist. Rejected alternatives: panel-later split (fragments one surface); best-move endpoint first
  (independent backend, slot it as a later phase).
- **Why 107 and not Flaws/Analysis next:** the Games subtab is the *only* remaining SEED-036
  frontend surface whose backend is fully built. Flaws needs a per-flaw list endpoint; Analysis
  needs the best-move endpoint (LIBG-05). Both are more backend work → later phases.
- **Panel name = "Flaw-Stats panel"** (user, 2026-06-05), not "Mistake-Stats panel" — consistent
  with the seed's "Flaws" umbrella rule. The surface/category is named *Flaws*; the panel's own
  per-severity numbers still read in precise terms ("1 blunder · 2 mistakes", never "3 flaws").
- **Card tag chips are display-only in 107.** The seed specs chips that deep-link into a
  pre-filtered Flaws view, but Flaws is a later phase and that route does not exist yet. In 107 the
  chips render (family-colored per `theme.ts`) but are not yet clickable destinations; the
  deep-link target is wired when the Flaws subtab ships. **Planner must not assume a Flaws route.**
- **Eval sparkline deferred.** The seed's "optional mini eval-progression sparkline" on cards is
  cut from 107. It would need a backend addition (the 106 games-list endpoint returns
  counts/chips, not the per-ply eval series). Deferring it keeps 107 a pure frontend phase with
  **no backend work** and confirms the 106 contract is sufficient.
- **Returning-user default subtab flips Overview → Games.** Phase 104 set the has-games default to
  Overview as a placeholder; 107 makes Games the headline surface, so the state-dependent landing
  becomes zero games → Import, has games → **Games**.
- **No chessboard, no opening/position filter** on this surface — that is the Openings page's job;
  adding it here would duplicate Openings → Games. Filters = existing metadata filters + the
  boolean mistake-severity filter only.

## Design path

`/gsd-sketch` (analyzed game card + Flaw-Stats panel, desktop + mobile) → `/gsd-ui-phase`
(UI-SPEC contract) → `/gsd-plan-phase 107`. The seed explicitly flagged a sketch for the card
layout (chip count/cap, placement, mobile wrapping).

## Reuse anchors

- Game card / filter sidebar / mobile drawer / Games-subtab pagination: `frontend/src/components/Openings/`
- Stats-panel + WDL-bar layout reference: `frontend/src/components/Endgames/`
- Tag-family semantic colors: `frontend/src/lib/theme.ts` (families: severity / tempo / opportunity / impact)
