---
id: SEED-112
status: promoted
promoted_to: Phase 179 (v2.5 Move Statistics), 2026-07-18
planted: 2026-07-18
planted_during: /gsd-explore session during Phase 178 (lichess-compatible accuracy/ACPL computed columns). User wants to replace the current move-stat badge row on the library game card and the analysis board tags panel with a single two-sided "Move Stats" component modeled on chess.com's game-review move-classification table (accuracy strip on top + per-category counts for both players). Reference mockup: chess.com game review panel with an Accuracy row and one row per move class.
trigger_when: After Phase 178 ships and lichess-compatible accuracy/ACPL is available as a per-game, per-player (both-color) value that can be surfaced on the game-card payload. Also gated on confirming the per-player, per-category counts (severities + best_move_tier) can be aggregated per side (see "Open unknown" below).
scope: phase (1-2 plans) — a backend/API surfacing task (accuracy + per-player per-category counts onto GameFlawCard and the analysis payload; NO new engine scoring) plus a frontend redesign extracting a shared two-sided MoveStats component used by both LibraryGameCard.tsx and AnalysisTagsPanel.tsx, with cycling + filter wiring reworked around a per-cell (category × side) model.
depends_on: Phase 178 (accuracy/ACPL). The accuracy strip is the headline of the new component and cannot render without both players' accuracy.
---

# SEED-112: Two-sided Move Stats component (accuracy + per-category counts, both players)

## The product idea

Replace the current per-card badge row (severity badges + gem/great badges) with a single
**two-sided "Move Stats" card** modeled on chess.com's game-review move-classification table.
It merges two things that are currently separate (or missing):

- **An accuracy strip on top** — one big cell per player. **The cell background encodes player
  color** (white background = white player, dark background = black player), so the accuracy
  badge doubles as the color indicator. This is why player names can be omitted from the card.
- **A move-classification table below** — one row per category, a centered category icon, and
  **two count columns (one per player)**. The player's stats are **always on the left**.

Used in two places with a single shared component: the **library game card** and the
**analysis board tags panel** (`AnalysisTagsPanel.tsx`). These already share the `FlawRef`
cycle model but the code is duplicated — this is the natural extraction point.

## Locked design decisions (from the explore session)

1. **7 FlawChess categories, both players:** Gem · Great · Best · Good · Inaccuracy · Mistake ·
   Blunder. **Not** chess.com's Book/Miss/Excellent/Okay — the reference mockup was a visual
   model, the categories are FlawChess's own (4 positive `best_move_tier`s + 3 severities).
2. **Accuracy strip on top;** player always left; **cell background = player color**
   (white bg = white, dark bg = black).
3. **Data already exists for both players** — `best_move_tier` is position-scoped and
   `game_flaws` covers both players, so the opponent's counts are a **surfacing** task, not new
   engine scoring. Note: showing the **opponent's positive tiers** (gem/great/best/good) in this
   table **deliberately reverses** the current user-scoped badge behavior (`isUserPly`). That
   user-scoping stays intentional elsewhere (see memory `project_gem_great_user_scoping`); this
   new surface opts into showing both sides on purpose.
4. **Desktop layout:** the Move Stats card is sized to **match the miniboard height (~225px)**
   and sits beside the board. This is a **tight fit** (7 rows × ~24px + accuracy header ≈ 210px)
   — expect small icons and tight row heights. The **tactic motif chips + context tags stay**
   (decision (b), not dropped) as a chip section filling the gap below the eval chart.
5. **Mobile layout:** **full table, collapsible.** Default state shows the accuracy strip + a
   compact severity summary; tap to expand the full 7-row two-sided table. This keeps the
   vertical scroll-list of game cards scannable. The **analysis board always shows the full
   table** (single focused view, height is fine).
6. **Cycling:** every **non-zero count cell** is a clickable cycle target, scoped by
   **(category × side)** — up to 14 targets. Extends the existing `FlawRef` discriminated union
   with a `side`/`color` dimension. Clicking a new cell jumps to its first ply; re-clicking
   advances and wraps; clicking a different cell resets. On the analysis board this drives
   `goToNode`; on the library card it drives the mini-board + eval-chart tooltip. **Hover a cell**
   dims non-matching markers on the eval chart (same as today). Zero cells are inert.
7. **Filter highlighting (library only):** the global flaw filter (`useFlawFilterStore`) stays
   **user-scoped** and **emphasizes only the player-side cell** of the matching row. Opponent
   cells remain independently clickable for cycling, but the global filter never targets them.
   Persistent board outlines (`outlinedPlies`) behave as today.

## Open unknown (must resolve before planning)

- **Per-player accuracy from Phase 178:** confirm Phase 178 produces accuracy (and ACPL) **per
  player / both colors**, not just for the importing user, and that it can be attached to the
  `GameFlawCard` payload. The accuracy strip needs both numbers.
- **Per-player per-category counts surfacing:** today `severity_counts` is a single object and
  `best_move_tier` counts are user-scoped in the UI (`eval_series[].best_move_tier` filtered by
  `isUserPly`). Need the cleanest way to expose **per-side** counts for all 7 categories on both
  the library payload and the analysis payload. Likely a small API/aggregation change, not a new
  column, since the row-level data exists.
- **Icons for Best/Good:** Gem/Great have `GemIcon`/`GreatMoveIcon`; severities have glyphs
  (`lib/severityGlyph.ts`). Best/Good need icon treatment consistent with the chess.com-style
  circular badges in the mockup.

## Current-code anchors (starting points for the eventual plan)

- `frontend/src/components/results/LibraryGameCard.tsx` — the library card (standalone per D-05;
  do not import from `GameCard.tsx`). Mobile vs desktop bodies are separate; apply changes to both.
- `frontend/src/components/analysis/AnalysisTagsPanel.tsx` — parallel copy; the shared-component
  extraction target. `onCyclePly`/`onHighlightChange` wiring lives in `pages/Analysis.tsx`.
- `frontend/src/components/library/SeverityBadge.tsx`, `GemGreatBadge.tsx` — current badges the
  table replaces.
- `frontend/src/hooks/useFlawFilterStore.ts` — global filter, `outlinedPlies`, `matchingFilterKeys`.
- `frontend/src/lib/theme.ts` — `SEV_*`, `MAIA_ACCENT` (gem/violet), `GREAT_ACCENT` (great/blue),
  `MOVE_HIGHLIGHT_*`. Category colors already defined; reuse, don't hard-code.
- `frontend/src/types/library.ts` — `GameFlawCard`, `FlawMarker`, `severity_counts`. Will need an
  accuracy field + per-side counts added here once the API surfaces them.
