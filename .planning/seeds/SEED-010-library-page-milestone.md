---
id: SEED-010
status: dormant
planted: 2026-05-01
planted_during: post-v1.14, /gsd-explore session on per-game review + new game filters
trigger_when: ready to start the next milestone after current calibration/insights work is shipped, OR when user invokes `/gsd-new-milestone` for "Library"
scope: milestone (multi-phase)
---

# SEED-010: Library — per-game review + game-level filters

> **Naming.** The page is named **Library** (top-level nav, alongside Openings, Endgames, Time Management). The working name during exploration was "Analysis page"; that name was rejected because it (a) conflicts with chess.com/lichess "Analysis" connotations (engine analysis of a position) and (b) collides with the existing "Games" subtab inside Openings/Endgames. **"Analysis" is reserved as a *subtab* within Library** — see "Subtab structure" below.

## Why This Matters

FlawChess today slices data by **position** (Openings) and by **type** (Endgames). There is no surface that operates on **whole games**: users cannot filter their game library by game-level conditions ("games where I was up material and lost"), nor replay a specific imported game inside FlawChess. They have to click out to chess.com / lichess to step through a game.

The Library page closes that gap. It introduces:

1. A new **game-level filter dimension** (material delta sustained over plies) that complements the existing position-level and endgame-level filters.
2. A **per-game viewer** with stepper, clock-per-ply, material/eval timeline, eval bar, and phase markers — so users stay inside FlawChess for the review step.
3. A **stats panel + WDL bar** above the filtered games list, so the filter itself answers questions like "in my bullet games over the last 365 days, how often did I fail to convert a +2 material lead?" — implicitly via filter+WDL, without needing separate conversion%/recovery% numbers.

The page also serves as the future home for tactical-pattern filters (missed forks, missed pins, blunder-driven losses) once Stockfish eval coverage or a client-side eval pipeline makes those reliable. v1 deliberately does not ship those.

## When to Surface

**Trigger options:**
- User invokes `/gsd-new-milestone` and signals readiness to start the Library milestone.
- During `/gsd-explore` follow-up if scoping changes (e.g. Stockfish eval coverage materially improves and the tactical filters become near-term).

Do NOT surface mid-milestone. The Library milestone is large enough (new page, new filters, new viewer, new stats endpoint) that it should not be folded into an unrelated milestone.

## v1 Scope (locked)

### New top-level page: Library

Sits alongside Openings, Endgames, Time Management. Mobile-friendly using the same drawer pattern as Openings (filter sidebar collapses into a drawer on small screens; bookmarks behavior TBD by milestone discuss-phase).

### Subtab structure

Library uses a tab/mode-switch model rather than a side-by-side list+viewer column. Each mode gets the full page width, which fits the asymmetric needs (the games list wants horizontal space for game-card columns; the viewer wants horizontal space for the chessboard plus indicators).

**v1 ships two subtabs:**

- **Games** — filter sidebar + filterable games list + stats panel above the list. Default landing subtab. The games list itself is the focus.
- **Analysis** — full-width chessboard + all per-game indicators (timeline, eval bar, clocks, phase markers). Loaded by clicking "Analyze" on any game card from the Games subtab. Swaps the page content; filters/list are not visible while a game is open.

Mental model: **Games subtab = "find a game"; Analysis subtab = "review this game"**. The Games-subtab name is consistent with the existing "Games" subtab inside Openings/Endgames (which lists position-scoped games), with no collision because they live under different parent tabs.

**Future subtabs (out of v1 scope, but the structure accommodates them):**
- "Tactics" subtab once tactical filters land (missed forks/pins — see Deferred extensions).
- "Bookmarked" subtab if Library inherits the existing bookmarks UX from Openings.
- Any future game-level filter dimension.

### Filterable games list (Games subtab)

Reuses every existing game filter via `app/repositories/query_utils.py::apply_game_filters()`:
time control, platform, rated, opponent type, recency, color.

Adds **one new filter** (see next section).

Each row in the list is a **game card**. Cards show the existing summary fields (date, opponent, opening, result, length, etc.) plus:
- Existing link out to the platform site (chess.com / lichess) where the game was played.
- New "Analyze" link → switches Library to the Analysis subtab with the selected game loaded.

### New filter: Material Delta

User picks a target material delta from a preset slider/button group, similar to the existing **opponent strength** filter:

```
≤ -3   -2   -1   0   +1   +2   ≥ +3
```

Semantics: from the **user's POV**, signed integer in standard piece values (P=1, N=B=3, R=5, Q=9).

- Positive selection (≥+1, ≥+2, ≥+3): "show games where I reached at least this material lead, sustained ≥4 plies, anywhere in the game." Combined with the result filter (loss/draw), this surfaces failed conversions.
- Negative selection (≤-1, ≤-2, ≤-3): "show games where I fell to at least this material deficit, sustained ≥4 plies." Combined with result=win, this surfaces successful recoveries.
- "0" or unset = no material-delta filter applied.

**Sustainment is fixed at 4 plies in v1.** Configurable sustainment is deferred (see "Deferred extensions" below).

**Phase scoping is "anywhere in the game" in v1.** No phase coupling. Going beyond this is deferred.

### Filtering: on-the-fly, no precompute

**Decision:** do NOT add `max_material_lead_4ply` / `min_material_lead_4ply` columns to the `games` table. Filter on-the-fly from `game_positions`.

Rationale:
- Keeps the data model clean. No migration, no reimport tied to this filter.
- Supports configurable sustainment and threshold tweaks later without a schema change.
- Avoids the "stat changed because we re-derived peaks differently" trap.

Add an index on `game_positions(game_id, ply)` if the query plan requires it (the planner should benchmark before adding indexes). The query is roughly: for each game in the user's filtered set, find any window of ≥4 consecutive plies where signed material balance from the user's POV ≥ threshold, then keep games with at least one such window.

**Open question:** is per-ply signed material balance already a column on `game_positions`, or computed at query time from board state? If computed, planner should evaluate whether to materialize it as a column for this filter's query path. See Q-002 below.

### Stats panel above games list

Locked to:
- **Game count** (matches the existing patterns).
- **WDL bar** across the filtered set, from user's POV.
- **(Optional, low priority)** Average opponent rating in the selection — useful for the scouting use case.

**Explicitly NOT included:** separate "failed conversion %" / "successful recovery %" numbers. These are redundant with WDL bar + material-delta filter (the bar literally is the conversion/recovery rate when the filter is applied), and adding them invites mismatched semantics if the conversion% definition drifts from the filter's sustainment/threshold defaults.

### Per-game viewer (Analysis subtab)

Full page width when active. Hosts:

- Chessboard, click/keyboard navigation through plies. Read-only — no move input from user. Reuses the existing chess board component if feasible (planner: confirm whether the Openings board can be wrapped, or whether a viewer-specific component is justified).
- Player names + colors (which side the user played).
- Per-ply remaining clock for both players.
- **Material balance timeline** (per-ply, always available — derivable from positions).
- **Stockfish eval timeline** (only when the import included Stockfish evals; today this is a minority of lichess games and zero chess.com games).
- **Eval bar** (same gating as eval timeline).
- **Phase markers** in the timeline: opening / middlegame / endgame transitions. Endgame transition already classified at import. Middlegame transition needs a definition — see Q-003.
- A "Back to Games" affordance to return to the filtered list state without losing filter state.

### Mobile

Drawer pattern from Openings on the Games subtab (filter sidebar collapses into a drawer on small screens). The Analysis subtab on mobile stacks the indicators below the chessboard rather than alongside (planner: confirm during UI design). Subtab switching uses the standard tab control already established in Openings/Endgames.

## Deferred extensions (separate seeds when triggered)

These were discussed during the explore session and are explicitly out of v1 scope. Capture them here so they aren't lost; promote to their own seeds if/when they become near-term.

### Tactical filters: missed forks, missed pins

**Why deferred:** meaningful detection requires Stockfish evals at every ply. Without engine validation, naive geometric fork/pin detection is high-noise (many "forks" lose to a stronger reply). Server-side Stockfish is permanently off the table. Imported lichess Stockfish evals exist on a minority of games.

**When to revisit:** when imported Stockfish eval coverage reaches a useful threshold (see Q-005 for sizing), OR when the client-side engine pipeline (next item) ships and provides per-ply evals on demand.

**Approach when revisited:** detect sudden eval drops (≥150 cp swing in one ply, from the side-to-move's POV) as "missed tactic" candidates. Optional follow-on: classify the motif via geometric pattern detection on the position before the drop.

### Client-side engine analysis (Stockfish, Maia, hybrid)

**Why deferred:** separate future milestone. Server-side Stockfish is permanently off the table (CPU cost, OOM history — see CLAUDE.md note from 2026-03-22). Client-side Stockfish is well-trodden (lichess does it). Maia is the human-likeness model from Lichess; a hybrid Stockfish/Maia engine is the user's longer-term interest and warrants its own discuss-phase.

**When to revisit:** after the Library milestone ships and there's a clear product reason to add live eval (e.g. users want to analyze a position from a game without imported evals; tactical filters need per-ply evals).

### Configurable sustainment N

**Why deferred:** v1 fixes N=4. Configurable 1-10 adds a knob nobody asks for unless they hit a specific use case. Defer until evidence (user feedback, internal use) shows the default doesn't fit.

**When to revisit:** if users explicitly ask for a different sustainment, or if internal use surfaces games that should-but-don't match the filter at N=4.

### Configurable phase scoping

**Why deferred:** v1 is "anywhere in the game". A phase-scoped variant ("entered endgame up ≥X material, lost") would overlap with the existing Endgame Analytics conversion stat. Defer until there's clear product reason to make the phase scope a user-controllable filter dimension.

## Out of Scope — permanently

- **Server-side Stockfish at import time.** Will not happen. CPU and memory cost is incompatible with the single-server Hetzner setup. Imported evals from lichess are the only ever server-stored eval source.
- **Tactical filters using only geometric pattern detection (no eval).** Too noisy to be a feature. Either eval-validated or not shipped.

## Phase Decomposition (rough sketch — planner refines during `/gsd-new-milestone`)

This is a milestone-sized seed. Likely 4-6 phases:

1. **Data layer prep.** Verify per-ply material balance availability (Q-002). Add index on `game_positions(game_id, ply)` if benchmarks show the new filter needs it. Define and persist middlegame_start_ply if missing (Q-003).
2. **Material-delta filter (backend).** Extend `query_utils.py::apply_game_filters()` with the new dimension. Window-function query over `game_positions` joined to `games`. Tests against benchmark DB.
3. **Library page shell + Games subtab (frontend).** New top-level route, subtab structure (Games/Analysis), Games-subtab layout (filter sidebar + games list), reuse existing filter UI primitives, add the new material-delta preset control. Mobile drawer.
4. **Analysis subtab — per-game viewer.** Chessboard + stepper + names/colors/clocks/material timeline. Phase markers in timeline. Reuse existing board component if feasible. "Back to Games" affordance preserves Games-subtab filter state.
5. **Eval bar + eval timeline (gated on import data).** Render only when the loaded game has imported Stockfish evals. Otherwise hide cleanly.
6. **Stats panel above games list.** Game count + WDL bar + optional avg opponent rating. Wire to filter state.

(May collapse 5 into 4 if eval data plumbing is small. May split 3 if the new layout is large.)

## Breadcrumbs

- `app/repositories/query_utils.py` — single source for game filtering. The new material-delta filter goes here.
- `app/models/game.py` and `app/models/game_position.py` — confirm material balance and clock columns; this seed assumes both are stored per-ply.
- `frontend/src/components/Openings/` — reference for chessboard component, mobile drawer pattern, filter sidebar layout, subtab control. Library page should reuse these primitives where feasible.
- `frontend/src/components/Endgames/` — reference for stats panel + WDL bar layout, subtab structure. Library's stats panel mirrors this structure.
- `app/services/import_service.py` — where per-ply data is populated at import. Touch only if Q-002/Q-003 require new fields.
- `scripts/reclassify_positions.py` — replays stored PGNs to backfill new fields, useful if any new per-ply column is added.
- `.planning/research/questions.md` — Q-002, Q-003, Q-004, Q-005 cover the open data-model questions for this seed.

## Source

`/gsd-explore` conversation 2026-05-01 between user and Claude. Key design decisions captured during that conversation:

- **Page name:** **Library** chosen over working name "Analysis page" because (a) "Analysis" overpromises engine analysis (the chess.com/lichess connotation) and (b) "Games" as a top-level name collides with the existing "Games" subtab inside Openings/Endgames. Library is the dimension-style name parallel to Openings/Endgames; "Analysis" is reserved as a subtab.
- **Subtab structure:** Library v1 has two subtabs — Games (filter+list+stats) and Analysis (full-width per-game viewer). Future subtabs (Tactics, Bookmarked) are accommodated by the structure but out of v1 scope.
- **Page positioning:** entry from both stat drill-downs and standalone game search ("C — both, equally weighted"). Game cards link to platform AND internal viewer.
- **Tactical filters split:** material-based filters (failed conversion / successful recovery) ship in v1; tactical filters (missed forks/pins) deferred behind Stockfish eval coverage. Server-side Stockfish permanently rejected.
- **Material-delta filter shape:** preset slider -3..+3, fixed sustainment 4 plies, phase-anywhere, user POV.
- **Stats panel:** WDL bar + count only; conversion%/recovery% rejected as redundant with filter+WDL.
- **Data model:** filter on-the-fly from `game_positions`; rejected the precomputed-columns approach for flexibility.
