# Phase 107: Games Subtab Frontend — Card Archive, Filters & Flaw-Stats Panel - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The Library **Games** subtab frontend — a filterable game-card archive plus a
**Flaw-Stats panel** above it, consuming the Phase 106 endpoints `GET
/api/library/games` and `GET /api/library/flaw-stats`. Becomes the
returning-user default subtab (Overview → Games for users with games).

The visual and interaction contract is fully specified in `107-UI-SPEC.md`
(sketch-validated, gsd-ui-checker-reviewed). That document is the design lock —
layout, colors, copy, `data-testid`/ARIA conventions, per-game/per-100 toggle,
pagination, empty/error states, and the returning-user redirect are all decided
there and are NOT re-opened here.

**Scope note — one deliberate expansion past the roadmap:** the ROADMAP entry
says "No backend work." During discussion we found the UI-SPEC's Zone 3 needs
rate fields the backend doesn't expose, and the user chose a small, contained
backend extension to deliver them (see D-01). This phase therefore includes a
narrow backend slice. This was flagged and explicitly approved.

</domain>

<decisions>
## Implementation Decisions

### Opportunity / Impact rates (spec-vs-backend gap)
- **D-01 (backend extension, approved scope expansion):** The UI-SPEC Zone 3
  "Tag distribution" requires Opportunity rates (miss, lucky-escape) and Impact
  rates (while-ahead) that the current `TagDistribution` schema does NOT expose
  (it has only `tempo`, `result_changing_rate`, `phase_histogram`). Resolution:
  **extend the backend**, not derive client-side.
  - Add **three flat float fields** to `TagDistribution` in
    `app/schemas/library.py`: `miss_rate`, `lucky_escape_rate`,
    `while_ahead_rate`. Each = `count / total M+B flaws`, `0.0` when there are
    no M+B flaws — exactly mirroring the existing `result_changing_rate` field
    (NOT nested `opportunity_rates`/`impact_rates` dicts; flat floats for
    consistency with the established precedent).
  - Add three counters in `_compute_tag_distribution`
    (`app/services/library_service.py:325`). The loop already walks every tag of
    every M+B flaw, so this is ~3 lines + the rate computations.
  - Update/extend the existing flaw-stats backend tests to cover the three new
    rates (including the `0.0`-when-no-flaws edge).
- **D-02 (client-side derivation rejected):** Do NOT derive these rates from the
  card `chips`. Card chips are game-deduped presence flags over only the current
  20-card page, which yields a different, page-limited metric ("% of this page's
  games with ≥1 miss") rather than the true `miss_count / total_mb_flaws`.
- **D-03 (frontend rendering):** Zone 3 renders the Opportunity sub-column
  (miss + lucky-escape, `FAM_OPPORTUNITY` cyan) and Impact sub-column
  (while-ahead + result-changing, `FAM_IMPACT` magenta) directly from the three
  new fields + the existing `result_changing_rate`. No placeholders, no
  "coming soon" scaffolding — the data is now real.

### Card + pagination reuse seam
- **D-04 (extract shared pagination):** Pull `getPaginationItems` + the
  prev/numbered/next pagination controls out of
  `frontend/src/components/results/GameCardList.tsx` into a shared `Pagination`
  component (or `usePagination` hook), consumed by both the existing
  `GameCardList` and the new `LibraryGameCardList`. The pagination logic is the
  only genuinely type-agnostic reusable part (~80 lines).
- **D-05 (LibraryGameCard is a separate component):** Do NOT make `GameCard`
  generic or shared at the body level. The Library card body differs
  fundamentally (full-width header, 3-column desktop body, flaw column, severity
  badges, family-colored chips, no-analysis state), so `LibraryGameCard` is a
  new component that borrows GameCard's metadata/board/platform patterns but is
  not a refactor of it. Rejected the generic `GameCardList<T>` render-prop
  approach as over-engineered for two callers.
- **D-06 (blast radius):** Extracting pagination modifies `GameCardList`, which
  is used by the Openings and Endgames game lists. The planner MUST keep those
  existing frontend tests green — this refactor must be behavior-preserving for
  the current callers.

### Tag chip interaction (carried from UI-SPEC, confirmed)
- **D-07:** Chips stay **display-only** in Phase 107: `cursor: pointer` +
  brightness/translate hover (future deep-link affordance) and honest ARIA
  (`aria-label="Tag: {tagName} (not yet linked)"`). No toast, no extra "coming
  soon" tooltip. The deep-link target (a Flaws view) does not exist yet — the
  planner must NOT assume any `/library/...` Flaws route.

### Claude's Discretion
- Trend chart implementation: Recharts `AreaChart` vs `LineChart` — follow the
  existing pattern in `EndgameScoreOverTimeChart.tsx` /
  `EndgameClockDiffOverTimeChart.tsx`. Either is acceptable per the UI-SPEC.
- Whether the extracted pagination lands as a component vs a hook — planner's
  call based on the cleanest fit with `GameCardList`'s current render.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design contract (locked)
- `.planning/phases/107-games-subtab-frontend-card-archive-filters-flaw-stats-panel/107-UI-SPEC.md`
  — the full visual/interaction contract: layout (desktop sidebar + mobile
  drawer mirroring Openings), color tokens + new `theme.ts` tag-family
  constants, typography, every copy string, all `data-testid`/ARIA conventions,
  per-game/per-100 toggle, pagination, empty/error states, returning-user
  redirect. This is the primary spec; do not re-derive these decisions.

### Backend contract (what the frontend consumes + the D-01 extension target)
- `app/schemas/library.py` — `LibraryGamesResponse` / `GameFlawCard` and
  `FlawStatsResponse` / `TagDistribution` / `SeverityRates` / `FlawTrendPoint`.
  **This is the file the D-01 extension edits** (add `miss_rate`,
  `lucky_escape_rate`, `while_ahead_rate` to `TagDistribution`).
- `app/services/library_service.py` §`_compute_tag_distribution` (line ~325) —
  the aggregation the D-01 counters are added to.
- `app/routers/library.py` — routes are `GET /library/games` and
  `GET /library/flaw-stats`. **NOTE:** the ROADMAP's name `mistake-stats` is
  STALE; the real endpoint is `flaw-stats` (matches the UI-SPEC).
- `app/services/flaws_service.py` (lines 75–88) — the `FlawTag` /
  `FlawSeverity` / `TempoTag` taxonomy. Tag → family mapping for chip coloring:
  Tempo (violet) = low-clock/impatient/considered; Opportunity (cyan) =
  miss/lucky-escape; Impact (magenta) = result-changing/while-ahead; Phase
  histogram = opening/middlegame/endgame.

### Tag naming
- `.planning/notes/flaw-tag-naming.md` — final tag taxonomy (low-clock,
  impatient, considered, miss, lucky-escape, while-ahead, result-changing,
  opening/middlegame/endgame) and the "tempo is optional" structural change
  (tempo counts sum to ≤ M+B flaws; show the unmeasured remainder).

### Reuse patterns (frontend)
- `frontend/src/components/results/GameCardList.tsx` — pagination logic to
  extract (D-04); existing Openings/Endgames caller to keep green (D-06).
- `frontend/src/components/results/GameCard.tsx` — metadata/board/platform
  patterns LibraryGameCard borrows (D-05).
- `frontend/src/lib/theme.ts` — where all new tag-family / severity / phase
  color constants MUST be defined (per UI-SPEC Color section + CLAUDE.md).
- Openings page — the desktop sidebar + mobile `Drawer` filter pattern to mirror.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GameCardList` pagination (`getPaginationItems` + prev/numbered/next controls)
  — extract into a shared `Pagination` component/hook (D-04).
- `GameCard` — metadata row, `LazyMiniBoard`, `PlatformIcon`, `Tooltip` link
  patterns reused by `LibraryGameCard` (D-05).
- `FilterPanel` — composed by `LibraryFilterPanel`; omit color/matchSide, add
  the boolean mistake-severity toggle (per UI-SPEC Filter Panel Extension).
- `Drawer`/`DrawerContent`/`DrawerHeader`, `Button`, `ToggleGroup`, `Select`,
  `Tooltip` — existing primitives, no new registries.
- `_compute_tag_distribution` (`library_service.py`) — already iterates all
  tags; D-01 counters drop in here.

### Established Patterns
- TanStack Query for both `library-games` and `library-flaw-stats`, sharing the
  same filter params object; both refetch on filter change; card list resets to
  page 1 (per UI-SPEC State Management). `isError` branch mandatory on every
  chain (CLAUDE.md).
- The mistake-severity filter (`('blunder'|'mistake')[]`) lives as local state
  in `GamesTab`, passed to BOTH endpoints as multi-value `severity[]`; it is NOT
  part of the shared `FilterState` interface (UI-SPEC).
- Recharts on charcoal, no grid lines — follow existing endgame chart components.

### Integration Points
- `LibraryPage.tsx` — add a third `TabsTrigger` ("Games") and flip the default
  redirect from `overview` to `games` for users with games (UI-SPEC Surface
  Architecture).
- Backend: `TagDistribution` schema + `_compute_tag_distribution` (D-01); no new
  routes, no migration (the new fields are computed, not stored).

</code_context>

<specifics>
## Specific Ideas

- New `TagDistribution` rate fields must be **flat floats** named exactly
  `miss_rate`, `lucky_escape_rate`, `while_ahead_rate`, semantics identical to
  `result_changing_rate` (count / total M+B flaws; `0.0` when none). This is the
  precedent-consistent shape the user explicitly chose over nested dicts.
- The endpoint is `flaw-stats`, never `mistake-stats` (correct the stale ROADMAP
  reference wherever it surfaces).

</specifics>

<deferred>
## Deferred Ideas

- **Tag-chip deep-link into a pre-filtered Flaws view** — deferred until the
  Flaws subtab exists (a later SEED-036 phase). Chips render display-only now.
- **Per-card eval sparkline** — explicitly deferred by the roadmap; out of scope.
- **"Coming soon" tooltip / placeholder scaffolding** for the Opportunity/Impact
  columns — not needed; the backend extension (D-01) makes the data real, so the
  columns render live rather than as placeholders.

</deferred>

---

*Phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel*
*Context gathered: 2026-06-05*
