# Phase 175: Board & Filter — Gem/Great Consumption - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-16
**Phase:** 175-board-filter-gem-great-consumption
**Areas discussed:** Sweep fate + off-mainline, "Great" marker display, EvalPoint delivery shape, Filter scoping + layout

---

## Sweep fate + off-mainline behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Demote to fallback | Retire sweep from analyzed mainlines (stored rows drive those); keep live-engine path ONLY for positions with no stored analysis (off-mainline, free-play, un-analyzed bot games). Closes mainline-sweep bugs. | ✓ |
| Full retirement | Delete `useGemSweep.ts` entirely; markers appear only where stored rows exist; off-mainline/free-play show nothing. | |

**User's choice:** Demote to fallback
**Notes:** BOARD-02 resolves as "demoted", SEED-107 superseded. Mainline no longer sweeps → WR-01/03/05 mooted; fallback path still needs WR-06 + IN cleanups.

---

## "Great" marker display

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct icon + color | Great gets its own lucide icon + accent, distinct from gem. | |
| Same icon, different color | Reuse Gem icon, tint great a second color. | |
| Board gem-only, great in chart/list | Board badge gem-only; great in move-list/chart/popover. | |
| **Custom SVG (user-specified)** | Blue circle with a white "!" (chess.com Great Move); appears on every surface gem does. | ✓ |

**User's choice:** Free-text — "For great moves use a blue circle with a white exclamation point (create an svg icon)"; then confirmed "Everywhere" for surfaces.
**Notes:** Blue → `GREAT_ACCENT` theme constant; `GREAT_GLYPH` record mirrors `GEM_GLYPH`; gem unchanged (lucide Gem, `MAIA_ACCENT`). Surfaces: board badge, move-list glyph, eval-chart dot, popover.

---

## EvalPoint delivery shape

| Option | Description | Selected |
|--------|-------------|----------|
| Tier string + maia_prob | `EvalPoint` gains `best_move_tier: 'gem'\|'great'\|null` (backend `classify_best_move`) + `maia_prob` (popover). Board renders tier; board+filter share one classifier. | ✓ |
| Raw floats, frontend classifies | `EvalPoint` gains raw `maia_prob`+cps; frontend re-derives tier (dup of backend filter logic, ships sigmoid, retune needs frontend deploy). | |

**User's choice:** Tier string + maia_prob
**Notes:** FILT-01 forces backend classification anyway, so reusing it for the board makes board+filter agree by construction. Frontend `classifyGem`/new `classifyGreat` retained only for the live fallback path.

---

## Filter scoping + layout

| Option | Description | Selected |
|--------|-------------|----------|
| User's own moves | `EXISTS` scoped to plies where ply-parity == `user_color` (like flaw filter); "games where I found a brilliancy". | ✓ (scope) |
| Any move in the game | Position-scoped; any gem/great by either player (opponent-scouting). | |
| Two independent toggles | Separate has-gem / has-great booleans; both-on = union; FilterPanel + MobileFilterDrawer. | ✓ (layout) |
| Single 3-state control | One Off/Gem/Great cycle; can't express both; new interaction pattern. | |

**User's choice:** User's own moves (scope) + two independent toggles (layout)
**Notes:** Consistent with existing user-scoped flaw/tactic filters; composes with all other filters via `apply_game_filters()`.

---

## Claude's Discretion

- Great popover copy, eval-chart dot styling for great, exact `GREAT_ACCENT` hex,
  `GreatMoveIcon` component name/markup, filter request-param names, and whether a
  supporting partial index on `game_best_moves` is warranted.

## Deferred Ideas

- Gem/Great threshold calibration against real per-game frequency (GEMS-07, post-pipeline).
- Opponent-scouting (any-move-scope) gem/great filter — considered, rejected for FILT-01.
- Corpus backfill of existing analyzed games → Phase 176 (BACK-01).
