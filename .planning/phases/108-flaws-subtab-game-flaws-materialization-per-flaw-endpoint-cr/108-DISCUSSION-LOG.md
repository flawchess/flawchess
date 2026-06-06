# Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter & Miniboard List - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
**Areas discussed:** Games tab filter control + backend source-of-truth, Games tab migration to game_flaws, Flaws subtab layout & UI-SPEC, Freshness & backfill ops

Areas offered: Games filter reconcile, Inaccuracies in table, Flaws layout & UI-SPEC, Freshness & backfill ops. User selected the first, third, and fourth, and ADDED a fifth (Games-tab migration to game_flaws). "Inaccuracies in table" was not selected for deep discussion but was resolved as a consequence of the migration decision (M+B-only table → inaccuracy counts stay an aggregate).

---

## Games tab — filter control (reconcile Phase 107)

| Option | Description | Selected |
|--------|-------------|----------|
| Replace it | New Flaw filter (severity × tag families) becomes the single mistake-filter control; 107 boolean toggle removed, severity collapses as one family | ✓ |
| Coexist | Keep boolean toggle AND add richer Flaw filter alongside — two overlapping severity controls | |
| Replace, Games = severity-only subset | Single control, but Games exposes only the severity family; full tag multi-select only in Flaws | |

**User's choice:** Replace it.
**Notes:** Concretely means pulling severity OUT of `LibraryFilterPanel` into a new dedicated Flaw-filter control (SEED-038: distinct from the game-metadata FilterPanel). Severity-only filtering still works.

---

## Games tab — backend source-of-truth (migration, user-added area)

| Option | Description | Selected |
|--------|-------------|----------|
| Migrate M+B to game_flaws | EXISTS filter, chips, tag distribution, M+B counts read game_flaws via shared predicate builder; inaccuracy counts stay a cheap SQL aggregate; single source of truth; prod backfill becomes a hard prerequisite | ✓ |
| Leave 106 on-the-fly | Only the new Flaws endpoint uses game_flaws; Games keeps recomputing — two divergent paths, drift risk | |
| You decide at plan time | Defer to planner to benchmark and choose | |

**User's choice:** Migrate M+B to game_flaws.
**Notes:** Makes the prod backfill a hard prerequisite (Games tab empty until populated) — resolved by the manual-ops decision below (D-09), so the phase is not gated on a prod backfill run.

---

## Cross-tab Flaw-filter state & behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Shared store + URL on Flaws | Shared across both tabs; Flaws tab URL-syncs for deep-linking; Games need not URL-sync | ✓ |
| URL-synced on both tabs | Both tabs read/write the filter to the URL — more wiring | |
| Per-tab local state | Each tab owns its own state; switching resets it | |

**User's choice:** Shared store + URL on Flaws.

---

## Chip deep-link scope

| Option | Description | Selected |
|--------|-------------|----------|
| That game's flaws, tag pre-filtered | Scope to game_id=ID + tag pre-set | |
| Tag pre-filtered, all games | Pre-fill TAG, ignore game_id, show all games with that tag | ✓ |
| You decide at plan time | Defer | |

**User's choice:** Tag pre-filtered, all games.
**Notes:** The chip becomes a broad doorway to "all my flaws of this kind."

---

## game_id in the chip deep-link URL (follow-up to the all-games choice)

| Option | Description | Selected |
|--------|-------------|----------|
| Drop game_id | Chip → /library/flaws?tag=TAG only; amends SEED-038's URL shape | ✓ |
| Keep game_id for highlight/scroll | Pass game_id, scroll/highlight that game's flaw within the all-games list | |
| Keep game_id, add 'this game only' affordance | Pass game_id + a one-click narrow-to-game toggle | |

**User's choice:** Drop game_id. AMENDS SEED-038's locked `/library/flaws?game_id={ID}&tag={TAG}` to `/library/flaws?tag={TAG}`.

---

## Flaws subtab — UI-SPEC scope

| Option | Description | Selected |
|--------|-------------|----------|
| UI-SPEC for the Flaw-filter control only | /gsd-ui-phase scoped to the new shared filter control; list spec'd in-plan reusing Openings miniboard + 107 components | ✓ |
| Full UI-SPEC for the whole subtab | Sketch-validated UI-SPEC for the entire surface | |
| No UI-SPEC — spec in-plan | Skip /gsd-ui-phase entirely | |

**User's choice:** UI-SPEC for the Flaw-filter control only.

---

## Flaws subtab — default sort & multi-flaw layout

| Option | Description | Selected |
|--------|-------------|----------|
| Recent-first, flat list | ORDER BY g.played_at DESC, f.ply; flat rows each with own game metadata; adjacent rows per game | ✓ |
| Worst-first (by eval drop) | Sort by severity then ES-drop magnitude | |
| Grouped by game | Flaws nested under a per-game header | |

**User's choice:** Recent-first, flat list. Paginate by flaw (reuse 107 Pagination). Severity filter M+B-only (locked by the M+B-only table, not asked).

---

## Freshness & backfill ops — prod rollout sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Migrate + backfill before serving, tracked ops step | Build batched script + dev-test; prod backfill a tracked release ops step | |
| Run backfill inside the deploy/migration step | Auto-run in entrypoint.sh — OOM risk | |
| Ship empty, backfill async after | Visible empty-tab regression window | |
| CUSTOM (user) | Build scripts/backfill_flaws.py with --db and --user-id; verify on --db dev --user-id 28; everything else manual, no tracked release ops step | ✓ |

**User's choice (free text):** "Create the scripts/backfill_flaws.py script with --db and --user-id parameters, and test it for --db dev --user-id 28. Everything else will be done manually, no tracked release ops step."
**Notes:** Phase scope = build + dev-test the script only. Prod backfill / reimport run manually out-of-band. Phase completion is NOT gated on a prod backfill run.

---

## Freshness — write paths that populate game_flaws

| Option | Description | Selected |
|--------|-------------|----------|
| Import hook + backfill_flaws.py + reclassify refresh | Import hook + standalone script + reclassify_positions.py recomputes; reimport gets it free via CASCADE | ✓ |
| Import hook + backfill_flaws.py only | Don't wire reclassify_positions.py — staleness risk | |
| You decide at plan time | Defer | |

**User's choice:** Import hook + backfill_flaws.py + reclassify refresh. One classify path, no drift.

---

## Claude's Discretion

- Per-flaw endpoint route name (likely `GET /library/flaws`) + pagination contract.
- `game_flaws` indexing strategy beyond PK + `(user_id, severity)` — confirm via dev EXPLAIN/profiling.
- Import-hook bulk-insert mechanism (per-game vs per-batch) within the memory envelope.
- Where the shared predicate builder lives (`library_repository` / `query_utils`).

## Deferred Ideas

- Analysis detail viewer + on-demand best-move endpoint — out of scope (separate later phase).
- A `game_id`-scoped "this game only" Flaws drill-down — dropped for this phase (chip shows all games).
- Tracked release-ops automation for the prod backfill — rejected; prod ops are manual.
- Per-boolean partial indexes on `game_flaws` — only if profiling demands.
