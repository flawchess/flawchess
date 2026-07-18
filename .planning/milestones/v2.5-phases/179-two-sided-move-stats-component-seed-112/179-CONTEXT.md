# Phase 179: Two-sided Move Stats component (SEED-112) - Context

**Gathered:** 2026-07-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current per-card badge rows (severity badges + gem/great badges) on
the **Library game card** (`LibraryGameCard.tsx`) and the **analysis board tags
panel** (`AnalysisTagsPanel.tsx`) with a single shared **two-sided "Move Stats"
component**, and surface the data it needs onto the two payloads.

The component is: an **accuracy strip** on top (one cell per player; **cell
background encodes player color** — white bg = white, dark bg = black; player
always on the left) over a **7-row move-classification table** using FlawChess's
own categories (**Gem · Great · Best · Good · Inaccuracy · Mistake · Blunder** =
4 positive `best_move_tier`s + 3 severities) with **two per-player count columns**.

**In scope:**
- (a) **Backend/API surfacing** — attach both-color accuracy (Phase 178 canonical
  `white_accuracy` / `black_accuracy`) to `GameFlawCard` and the analysis payload.
  **NO new engine scoring.** Per-side per-category counts already ride in the
  existing payload (see D-05), so the backend delta is small.
- (b) **Frontend redesign** — extract a shared `MoveStats` component from
  `LibraryGameCard.tsx` + `AnalysisTagsPanel.tsx`, with cycling + filter wiring
  reworked around a per-cell **(category × side)** model (up to 14 clickable
  targets; `FlawRef` union gains a side/color dimension).

**Out of scope (deferred):**
- Any new engine scoring / new columns — the row-level data already exists
  (`best_move_tier` position-scoped; `game_flaws` covers both players).
- Recomputing/altering severity or tier definitions.
- Running the Phase 178 prod accuracy/ACPL backfill (separate operator step; this
  phase must render correctly whether or not it has run — see D-01).

</domain>

<decisions>
## Implementation Decisions

### Accuracy strip

- **D-01 — Canonical accuracy only, else "—" (no `_imported` fallback).** The
  strip shows a number **only** when we computed it uniformly (Phase 178 canonical
  `white_accuracy` / `black_accuracy`). When canonical accuracy is NULL, show a
  muted "—", never the platform-reported `*_accuracy_imported` value. Rationale:
  preserve 178's "one uniform, cross-platform metric" guarantee; do not mix two
  methodologies on the same surface. **Accepted consequence:** until the prod
  backfill runs (and for imported games we never full-analyze), many cards show
  "—". That is acceptable and honest.
- **D-02 — Accuracy % is the only headline number; ACPL is NOT surfaced.** ACPL
  (also computed in 178) stays a backend/validation signal. Keeps the tight
  ~225px desktop card uncluttered and matches the chess.com-style headline.

### Move-classification table

- **D-03 — All 7 rows render always; zero cells shown as a muted 0/"–".** Stable,
  scannable layout across cards (chess.com style), no per-game row reshuffling.
  Consistent with SEED-112's accepted tight desktop fit (7 rows × ~24px +
  accuracy header ≈ 210px).
- **D-04 — Best/Good get new circular badge icons** consistent with the
  chess.com-style mockup and with the existing Gem/Great icons + severity glyphs.
  Exact icon design is a plan/UI-phase detail (reuse category colors from
  `theme.ts`; do not hard-code). Gem = `GemIcon`, Great = `GreatMoveIcon`,
  severities = `lib/severityGlyph.ts`.

### Data shape (backend surfacing)

- **D-05 — Backend delta is minimal.** Add per-color accuracy to the payloads;
  derive the 14 counts client-side from existing fields. Confirmed during
  scouting: severities for **both** sides already ride in `flaw_markers`
  (`is_user` flag, all 3 severities incl. inaccuracy); positive tiers for **both**
  sides already ride in `eval_series[].best_move_tier` (side = ply parity vs
  `user_color`). So the API change is essentially adding `white_accuracy` /
  `black_accuracy` to `GameFlawCard` (schema `app/schemas/library.py`) and the
  analysis payload. **Do NOT add explicit per-side count objects to the API** unless
  the planner finds a concrete blocker — the client already has everything to
  compute (category × side) counts. (Planner/researcher: confirm the analysis
  payload carries the same `flaw_markers` + `eval_series` both-side data the
  library card does; if the analysis page sources these differently, adjust.)

### Mobile / empty states

- **D-06 — Mobile collapsed default = accuracy strip + the USER's 3 severity counts (I/M/B).**
  Tap to expand the full two-sided 7-row table. Keeps the
  scroll-list of cards scannable. (Analysis board always shows the full table —
  single focused view, per SEED-112.)
- **D-07 — Unanalyzed game shows only the existing on-demand analyze pill.**
  When `analysis_state === 'no_engine_analysis'`: no strip, no table — show the
  existing on-demand analyze pill (`active_eval_status`),
  exactly as today's badge rows behave. A game that is "analyzed" but has NULL
  canonical accuracy still renders the full table (counts exist) with a "—"
  accuracy strip per D-01.

### Carried forward from SEED-112 (locked, do NOT re-open)

- **D-08 — Opponent positive tiers are deliberately surfaced here**, reversing the
  user-scoped `isUserPly` badge behavior for **this surface only**. User-scoping
  stays intentional everywhere else (see memory `project_gem_great_user_scoping`).
- **D-09 — Cycling is per (category × side)**, up to 14 clickable targets. Extend
  the `FlawRef` discriminated union (currently declared locally in each of
  `LibraryGameCard.tsx` and `AnalysisTagsPanel.tsx`) with a `side`/`color`
  dimension. Click new cell → jump to first ply; re-click → advance + wrap;
  different cell → reset. Analysis board drives `goToNode`; library card drives
  miniboard + eval-chart tooltip. Hover a cell dims non-matching eval-chart
  markers (as today). Zero cells are inert.
- **D-10 — The global flaw filter (`useFlawFilterStore`) stays user-scoped** and
  emphasizes **only the player-side cell** of the matching row. Opponent cells are
  independently clickable for cycling but the global filter never targets them.
  `outlinedPlies` behaves as today. (Library only — `/analysis` has no filter store.)
- **D-11 — Tactic motif chips + context tags STAY** as a chip section (not dropped);
  desktop card sized to the miniboard height (~225px) beside the board.

### Claude's Discretion / for research

- Exact `FlawRef` union shape for the side dimension, and whether to finally
  **extract the shared `MoveStats` component** vs keep the two files' "trivially
  safe copies" convention. SEED-112 calls this the natural extraction point;
  the planner decides how far to push shared extraction (the current convention
  in `AnalysisTagsPanel.tsx` header is deliberate non-sharing — weigh it).
- Whether the analysis payload already exposes `flaw_markers` + `eval_series`
  identically to the library card (see D-05 caveat) — confirm before planning the
  frontend count derivation.
- `LibraryGameCard.tsx` is 1271 lines. Refactor-on-sight applies to any function
  touched, but scope the extraction to this phase's plan — flag, don't sprawl.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design intent (authoritative)
- `.planning/seeds/SEED-112-two-sided-move-stats-component.md` — the locked design
  decisions, the accuracy-strip / two-sided-table model, cycling + filter rework,
  desktop/mobile layout, current-code anchors, and the (now largely resolved)
  open unknowns.

### Accuracy data provenance (Phase 178, the strip's source)
- `.planning/phases/178-lichess-compatible-accuracy-acpl-computed-columns/178-CONTEXT.md`
  — D-01..D-05: canonical `white_accuracy`/`black_accuracy` = our uniform values;
  `*_accuracy_imported` = platform-reported (the value D-01 above deliberately does
  NOT fall back to); accuracy is NULL when the per-ply eval sequence is incomplete
  or the game wasn't full-analyzed by us; prod backfill is a separate operator step.
- `app/services/accuracy_acpl.py` §89–92, §326–328 — the `GameAccuracyAcpl` result
  shape (`white_accuracy` / `black_accuracy` per color).

### Backend integration points
- `app/schemas/library.py` §103 `GameFlawCard`, §32 `EvalPoint` (`best_move_tier`),
  §274 `SeverityCounts` — where per-color accuracy fields get added; note accuracy
  is NOT surfaced today.

### Frontend integration points (SEED-112 anchors)
- `frontend/src/types/library.ts` — `GameFlawCard`, `EvalPoint` (`best_move_tier`),
  `FlawMarker` (`is_user`, both sides), `SeverityCountsData`. Add per-color accuracy
  fields here once the API surfaces them.
- `frontend/src/components/results/LibraryGameCard.tsx` §180 (local `FlawRef`) —
  library card; separate mobile vs desktop bodies (apply changes to BOTH).
- `frontend/src/components/analysis/AnalysisTagsPanel.tsx` §34 (local `FlawRef`) —
  parallel copy; `onCyclePly` / `onHighlightChange` wiring lives in
  `frontend/src/pages/Analysis.tsx`.
- `frontend/src/components/library/SeverityBadge.tsx`, `GemGreatBadge.tsx` — the
  badges the table replaces (`GemGreatBadge` exports `BestMoveTier`).
- `frontend/src/hooks/useFlawFilterStore.ts` — global filter, `outlinedPlies`,
  `matchingFilterKeys` (stays user-scoped per D-10).
- `frontend/src/lib/theme.ts` — `SEV_*`, `MAIA_ACCENT` (gem), `GREAT_ACCENT`
  (great), `MOVE_HIGHLIGHT_*`. Reuse category colors; never hard-code.
- `frontend/src/lib/plyOwnership.ts` (`isUserPly`), `frontend/src/lib/severityGlyph.ts`.

### Behavioral memory (must respect)
- Memory `project_gem_great_user_scoping` — badges/dots/cycling are normally
  user-scoped via `isUserPly`; D-08 intentionally opts THIS surface out.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Both sides' raw data is **already in the payload**: `flaw_markers` (severities,
  `is_user`) + `eval_series[].best_move_tier` (tiers, side via ply parity). The 14
  counts are client-derivable with no new API count fields (D-05).
- `GemIcon` / `GreatMoveIcon`, `lib/severityGlyph.ts`, `theme.ts` category colors —
  the icon/color vocabulary; Best/Good add two new circular badges (D-04).
- `FlawRef` discriminated-union + cycle/highlight machinery already exists in both
  components — extend it with a side dimension rather than inventing a new model.

### Established Patterns
- Library card and analysis panel keep "trivially safe copies" of `FlawRef` /
  cycling today rather than a shared component. SEED-112 targets extraction; the
  planner weighs how far to unify (existing non-sharing is deliberate).
- Mobile vs desktop bodies are separate in `LibraryGameCard.tsx` — apply every
  change to both (CLAUDE.md).

### Integration Points
- API: add `white_accuracy` / `black_accuracy` to `GameFlawCard`
  (`app/schemas/library.py`) + the analysis payload (D-05). Source =
  `games.white_accuracy` / `black_accuracy` (Phase 178 canonical columns).
- Cycling: analysis → `goToNode` (via `pages/Analysis.tsx`); library → miniboard +
  eval-chart tooltip. Filter: `useFlawFilterStore` (library only).

</code_context>

<specifics>
## Specific Ideas

- Reference visual model is chess.com's game-review move-classification panel
  (Accuracy row + one row per class), but the **categories are FlawChess's own 7**,
  never chess.com's Book/Miss/Excellent/Okay.
- Cell background doubling as the color indicator (white bg = white player, dark
  bg = black) is why player names can be omitted from the card.

</specifics>

<deferred>
## Deferred Ideas

- **Surfacing ACPL** anywhere in the UI — computed in 178, intentionally NOT shown
  here (D-02). A future surface could add it.
- **Falling back to `*_imported` accuracy for coverage** — explicitly rejected for
  this phase (D-01); revisit only if the "one uniform metric" stance changes.
- **Running the Phase 178 prod accuracy/ACPL backfill** — operator step, not gated
  in this phase.

None of the above are scope creep introduced during discussion — discussion stayed
within the SEED-112 boundary.

</deferred>

---

*Phase: 179-two-sided-move-stats-component-seed-112*
*Context gathered: 2026-07-18*
