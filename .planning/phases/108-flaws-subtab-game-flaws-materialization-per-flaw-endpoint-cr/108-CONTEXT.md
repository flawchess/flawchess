# Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter & Miniboard List - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The Library **Flaws** subtab — a paginable, one-row-per-flawed-position miniboard
list (miniboard + marked move + severity/tags), backed by a new per-flaw list
endpoint and a derived **`game_flaws`** table that materializes Phase 105's
on-the-fly classifier output. Plus a shared cross-tab **Flaw filter** (severity ×
tag families, single-flaw `EXISTS` semantics, family-aware OR-within / AND-across)
surfaced in BOTH the Games and Flaws tabs, and wiring Phase 107's display-only
Games-card tag chips into deep-links to a pre-filtered Flaws view.

**This phase also migrates the Games surface onto `game_flaws`** (a deliberate
expansion past a naive read of the roadmap, decided in discussion — see D-02):
Phase 106's on-the-fly `/library/games` + `/library/flaw-stats` endpoints move to
reading M+B flaws from `game_flaws` via the same shared predicate builder, so the
cross-tab unification is enforced in code, not convention.

**Schema, query semantics, and family logic are LOCKED by SEED-038** — do not
re-derive: the `game_flaws` typed-column schema + composite PK `(user_id,
game_id, ply)`, single-flaw `EXISTS` semantics, OR-within-family /
AND-across-family boolean logic, the shared WHERE-clause predicate builder reused
by both the Games `EXISTS` filter and the Flaws `SELECT f.*` list, and the
Openings-Insights miniboard reuse.

**Out of scope (separate later phase, per SEED-036):** the Analysis detail viewer
(`/library/analysis/{game_id}?ply={N}`) and the on-demand best-move endpoint.

</domain>

<decisions>
## Implementation Decisions

### Games-tab filter control (reconcile Phase 107)
- **D-01 (replace the boolean severity toggle):** Phase 107's boolean
  `('blunder'|'mistake')[]` severity toggle currently lives INSIDE
  `LibraryFilterPanel` (`frontend/src/pages/library/GamesTab.tsx:57-58`, separate
  local state, not in `FilterState`). It is **removed** and superseded by the new
  dedicated **Flaw-filter control** (severity × tag families), which SEED-038
  specs as distinct from the game-metadata `FilterPanel`. Concretely: pull
  severity OUT of `LibraryFilterPanel`; `LibraryFilterPanel` keeps
  platform / time-control / rated / recency / opponent only. The new control
  collapses severity into one family — severity-only filtering still works
  (select severity, no tags).

### Games-tab backend source-of-truth (migrate off on-the-fly)
- **D-02 (migrate M+B to `game_flaws`):** Phase 106's `/library/games` and
  `/library/flaw-stats` currently compute the `EXISTS` filter, per-game B/M/I
  counts, card chips, tag distribution and stats aggregates **on-the-fly** (SQL
  window-scan + re-calling the 105 kernel per query, `library_service.py`
  `classify_game_flaws` calls at lines ~112 / ~289). These migrate to read M+B
  flaws from `game_flaws` via the shared predicate builder: `EXISTS` filter, card
  chips, tag distribution, and M+B counts all source from `game_flaws`. Single
  source of truth, no kernel re-call per filtered query.
- **D-03 (inaccuracy counts stay an aggregate):** `game_flaws` is **M+B-only**
  (SEED-038 sub-decision #1 — recommendation accepted). Inaccuracy counts on the
  Games card / stats panel continue to come from the cheap SQL aggregate
  (`COUNT(*) FILTER (...)`) and/or the existing `games.white_/black_inaccuracies`
  oracle columns — never from `game_flaws` rows. Inaccuracies never appear as
  Flaws rows.
- **D-02 consequence (HARD prerequisite):** because the Games tab now reads
  `game_flaws`, existing users see an empty Games tab until the table is
  populated. Rollout is handled via D-09 (manual backfill), NOT a release-ops
  gate — see D-09 for the explicit decision that phase completion is NOT gated on
  a prod backfill run.

### Cross-tab Flaw-filter state & deep-linking
- **D-04 (shared state, URL-synced on Flaws):** Flaw-filter state is shared
  across both tabs (mirror the existing `useFilterStore` game-filter pattern) so
  switching Games↔Flaws preserves the selection. The **Flaws tab URL-syncs** the
  Flaw filter (`?tag=&severity=`) so a deep-link pre-populates the control. The
  Games tab need not URL-sync (Phase 107 precedent: severity was local-only).
- **D-05 (chip deep-link = all games, `game_id` dropped):** A Games-card tag chip
  deep-links to **`/library/flaws?tag={TAG}`** showing **every** flaw with that
  tag across **all** games (NOT scoped to the source game) — the chip is a broad
  doorway to "all my flaws of this kind." **This AMENDS SEED-038's locked URL
  shape**, which specified `/library/flaws?game_id={ID}&tag={TAG}`: `game_id` is
  removed from the chip deep-link entirely (it would be unused once results aren't
  game-scoped). Severity defaults to M+B on landing.

### Flaws subtab layout & UI-SPEC
- **D-06 (UI-SPEC scoped to the filter control only):** Run `/gsd-ui-phase 108`
  scoped to the NEW shared **Flaw-filter control** (severity × tag-family
  multi-select, surfaced in both tabs) — the only genuinely novel UX. The
  miniboard list itself is spec'd in-plan, reusing the Openings-Insights miniboard
  + marked move and Phase 107's `SeverityBadge` / `TagChip` / sidebar+drawer
  patterns. Do NOT run a full whole-subtab UI-SPEC.
- **D-07 (recent-first flat list):** Default order `ORDER BY g.played_at DESC,
  f.ply` (SEED-038's query pattern). Flat list of flaw rows; each row carries its
  own game metadata (opponent / date / result). Multiple flaws from one game
  appear as adjacent independent rows — NOT grouped under a per-game header.
- **D-08 (pagination & severity range):** Paginate **by flaw**, reusing the
  shared `Pagination` component Phase 107 extracted (D-04 of 107); page size 20
  unless the UI-SPEC dictates otherwise. The Flaws **severity filter is M+B-only**
  (forced by the M+B-only table); default severity = M+B.

### Materialization freshness & backfill ops
- **D-09 (script-only scope, manual prod ops):** Phase scope for ops is: build
  **`scripts/backfill_flaws.py`** with `--db {dev|benchmark|prod}` and an optional
  `--user-id` parameter (batched, mirroring `scripts/backfill_eval.py`'s pattern
  and `--db` switch — batching is MANDATORY given the project's OOM history on
  bulk classify passes), and **verify it on `--db dev --user-id 28`**. Prod
  backfill, reimport, and any all-users recompute are run **manually by the user
  out-of-band** — there is **NO tracked release-ops step and NO deploy-hook
  automation**. **Phase completion is NOT gated on a prod backfill run** (consistent
  with the project's "design verification to work against the existing dev DB"
  norm).
- **D-10 (freshness write paths — one classify path):**
  - **Import hook:** after `eval_cp` is stored for an analyzed game, call
    `classify_game_flaws` and bulk-insert the M+B rows into `game_flaws`.
  - **`reimport_games.py`:** gets it for free — delete+reimport CASCADE-drops
    `game_flaws` rows, and the import hook repopulates.
  - **`reclassify_positions.py`:** ALSO recomputes `game_flaws` (it already
    replays the PGN to refresh position metadata).
  - **`scripts/backfill_flaws.py`:** handles threshold-change recomputes
    (thresholds last changed 2026-06-05).
  - One classification path everywhere — no drift between the live read path and
    the materialization.

### Claude's Discretion (planner / researcher to settle)
- The per-flaw list **endpoint route name** (likely `GET /library/flaws`) and its
  pagination contract shape.
- The exact **`game_flaws` indexing** strategy: PK `(user_id, game_id, ply)`
  covers the `EXISTS` join; SEED-038 suggests adding `(user_id, severity)` —
  confirm via dev `EXPLAIN`/profiling, add per-boolean partial indexes only if
  profiling demands.
- The bulk-insert mechanism for the import hook (per-game vs per-batch) — choose
  to stay within the import pipeline's existing batch-size / memory envelope.
- Whether the shared predicate builder lives in `library_repository` /
  `query_utils` — pick the seam that lets `/library/games` (EXISTS wrapper) and
  the new Flaws list (`SELECT f.*`) share one WHERE-clause builder.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design / decisions (read first)
- `.planning/seeds/SEED-038-flaw-filter-and-game-flaws-materialization.md` —
  LOCKS the `game_flaws` schema (typed columns, composite PK), single-flaw
  `EXISTS` semantics, OR-within / AND-across family logic, the shared WHERE-clause
  predicate builder, the query patterns (Games EXISTS / Flaws SELECT / stats
  scan), and indexing guidance. **Note D-05 amends its deep-link URL shape**
  (`game_id` dropped from the chip link).
- `.planning/seeds/SEED-036-library-page-milestone.md` §"Flaws subtab" +
  phase-decomposition item 5 — the Flaws surface definition (row = one flawed
  position, reuse Openings miniboard), the "Flaws" umbrella naming rule
  ("1 blunder · 2 mistakes," never "3 flaws"), and the chip-as-teaser / deep-link
  model. Analysis detail viewer + best-move endpoint are explicitly deferred here.

### Phase 107 contract (the surfaces this phase modifies)
- `.planning/phases/107-games-subtab-frontend-card-archive-filters-flaw-stats-panel/107-CONTEXT.md`
  — Games-tab frontend decisions; D-04 extracted a shared `Pagination` component
  (reused by D-08 here); chips are display-only in 107 and this phase wires their
  deep-link (D-05).
- `.planning/phases/107-games-subtab-frontend-card-archive-filters-flaw-stats-panel/107-UI-SPEC.md`
  — the design lock for the Games subtab: `theme.ts` tag-family color tokens,
  `SeverityBadge` / `TagChip`, sidebar + mobile-drawer filter pattern, typography,
  `data-testid`/ARIA conventions. The Flaws list and the new Flaw-filter control
  inherit these tokens.
- `.planning/notes/flaw-tag-naming.md` — final tag taxonomy (low-clock /
  impatient / considered / miss / lucky-escape / while-ahead / result-changing /
  opening / middlegame / endgame) and the tag→family mapping.

### Backend (the migration targets)
- `app/services/flaws_service.py` — `classify_game_flaws` (line ~447) the
  materialization writes; `FlawRecord` / `FlawSeverity` / `FlawTag` / `TempoTag`
  taxonomy (lines 75–125); `count_*` count-only sibling (inaccuracy counts).
- `app/services/library_service.py` — the on-the-fly Games/flaw-stats service
  that D-02 migrates to `game_flaws` (kernel re-calls at lines ~112 / ~289;
  `_compute_tag_distribution` at ~325).
- `app/schemas/library.py` — `LibraryGamesResponse` / `GameFlawCard` /
  `FlawStatsResponse` / `TagDistribution`; add the new per-flaw response schema
  here.
- `app/routers/library.py` — `APIRouter(prefix="/library")`; routes `GET /games`,
  `GET /flaw-stats`; add the new per-flaw list route.
- `app/repositories/query_utils.py` (`apply_game_filters`) — shared game-filter
  path; Phase 106 added keyword-only `user_id` + `mistake_severity` for the EXISTS
  scope. The shared Flaw-filter predicate builder should integrate here / in
  `library_repository`.

### Backfill script precedent
- `scripts/backfill_eval.py` — the `--db dev|benchmark|prod` + batched
  async-session pattern `scripts/backfill_flaws.py` mirrors (D-09).
- `scripts/reimport_games.py`, `scripts/reclassify_positions.py` — coordinate
  freshness per D-10.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Openings-Insights miniboard + marked move** — the per-flaw row board
  (SEED-036; component family under `frontend/src/components/board/` —
  `MiniBoard` / `LazyMiniBoard` and the marked-move arrow pattern from
  `OpeningFindingCard.tsx`).
- **Phase 107 components** — `SeverityBadge`, `TagChip`, `theme.ts` family colors,
  `LibraryFilterPanel` (severity gets pulled out per D-01), the shared
  `Pagination` component (D-08), `Drawer` mobile pattern.
- **`classify_game_flaws`** (`flaws_service.py`) — the single classification
  kernel; the import hook, `reclassify_positions.py`, and `backfill_flaws.py` all
  call it (D-10) so the materialized output matches the (now-retired) live path.
- **`backfill_eval.py`** — batched `--db`-parameterized async backfill scaffold to
  copy for `backfill_flaws.py`.

### Established Patterns
- `useFilterStore` shared filter state across Library tabs (D-04 mirrors it for
  the Flaw filter); TanStack Query per endpoint with `isError` branch mandatory
  (CLAUDE.md); card list resets to page 1 on filter change.
- `apply_game_filters` is the single game-filter implementation; the new Flaw
  predicate builder must be the single shared builder for Games `EXISTS` + Flaws
  `SELECT` (SEED-038: unify in code).
- DB design rules: FK with `ondelete="CASCADE"`, composite PK, `SmallInteger`
  for ordered severity/tempo/phase (SEED-038 schema already follows these).
- Import batching / OOM discipline (`_BATCH_SIZE`, `_HASH_MB`) — `backfill_flaws.py`
  and the import hook must respect the memory envelope.

### Integration Points
- New Alembic migration creating `game_flaws` (composite PK, typed family columns,
  display payload `es_before` / `es_after` / `move_san`; indexes per SEED-038).
- Import pipeline (`import_service.py`, post-`eval_cp` storage) — new classify +
  bulk-insert hook.
- `LibraryPage.tsx` — add the **Flaws** `TabsTrigger` and the `/library/flaws`
  route (subtab order `Import · Games · Flaws · Overview`); the new Flaw-filter
  control surfaced in both Games and Flaws.
- `library_service.py` / `library_repository` — migrate Games endpoints to
  `game_flaws`; add the per-flaw list service + the shared predicate builder.

</code_context>

<specifics>
## Specific Ideas

- Chip deep-link is exactly `/library/flaws?tag={TAG}` — **no `game_id`** (D-05,
  amends SEED-038).
- `scripts/backfill_flaws.py` must accept `--db {dev|benchmark|prod}` AND an
  optional `--user-id`, and is verified specifically against `--db dev --user-id
  28` (D-09).
- `game_flaws` stores **mistakes + blunders only**; inaccuracy counts remain a
  cheap aggregate (D-03). The Flaws severity filter therefore offers M+B only.
- The Flaw-filter control is a **dedicated** control, separate from the
  game-metadata `LibraryFilterPanel` (SEED-038 decision 2); severity moves into
  it (D-01).

</specifics>

<deferred>
## Deferred Ideas

- **Analysis detail viewer** (`/library/analysis/{game_id}?ply={N}`) and the
  **on-demand best-move endpoint** — explicitly out of scope (SEED-036
  phase-decomp; separate later phase, also feeds SEED-037 Train).
- **`game_id`-scoped "this game only" Flaws view** — the chip shows all games
  (D-05); a per-game narrowing affordance was considered and dropped for this
  phase. Could return if users want per-game flaw drill-down.
- **Tracked release-ops automation for the prod backfill** (deploy-hook or
  CI-gated backfill) — explicitly rejected for this phase (D-09); the user runs
  prod backfill manually.
- **Per-boolean partial indexes on `game_flaws`** — only if profiling demands
  (SEED-038); start with PK + `(user_id, severity)`.

</deferred>

---

*Phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr*
*Context gathered: 2026-06-06*
