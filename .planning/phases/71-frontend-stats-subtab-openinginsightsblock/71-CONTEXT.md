# Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning
**Requirements:** INSIGHT-STATS-01, INSIGHT-STATS-02, INSIGHT-STATS-03, INSIGHT-STATS-04, INSIGHT-STATS-05, INSIGHT-STATS-06

<domain>
## Phase Boundary

Frontend-only. Build the `OpeningInsightsBlock` React component on the Openings → Stats subtab. The block consumes Phase 70's `POST /api/insights/openings` endpoint, renders the four-section response (white/black × weakness/strength) as ranked bullets with inline minimaps, and provides deep-links into the Move Explorer at the entry FEN.

No new backend, no schema changes — Phase 70's `OpeningInsightFinding` payload is the wire contract. The block lives at the top of the existing Stats tab content stream (above bookmarks / Most Played sections) and uses TanStack Query for fetching, with the same filter sources the rest of the openings page already uses.

The block is **templated-only** (no LLM, no Generate CTA) — auto-fetches on filter change, in contrast to the v1.11 `EndgameInsightsBlock` which requires an explicit Generate button because of LLM cost/rate-limits.

</domain>

<decisions>
## Implementation Decisions

### Section Layout & Color Filter Behavior

- **D-01:** **Layout = stacked vertical sections inside one `charcoal-texture rounded-md p-4` card.** Order: ⚠ White Opening Weaknesses → ⚠ Black Opening Weaknesses → ★ White Opening Strengths → ★ Black Opening Strengths. Section subheadings render as `<h3>` (`text-base font-semibold`) with a leading icon and the side's piece-color square swatch (mirrors the existing `bg-white` / `bg-zinc-900` square swatch pattern from `Openings.tsx:877-878`). Empty sections render with a one-line muted message (see D-09).
- **D-02:** **The block ignores the global `color` filter.** It always sends `color="all"` to `POST /api/insights/openings` regardless of what the user has selected as the active color filter for the rest of the openings page. Rationale: the four sections are the entire value of the block — filtering one out hides actionable signal. The filter difference between this block and the rest of the page is intentional and is documented in the InfoPopover for the block heading.
- **D-03:** **Deep-link click updates the global `color` filter.** When the user clicks a finding's deep-link, the active color filter is set to `finding.color` as part of the navigation flow (see D-13). The block continues to render all four sections after the navigation completes (because filter is purely the block's input — the block keeps sending `color="all"`).

### Finding Card Content & Rendering

- **D-04:** **Each finding renders as an `OpeningFindingCard`, modeled directly on `GameCard` (`frontend/src/components/results/GameCard.tsx`).** Card chrome: `border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3`, with the `border-l-4` left accent colored by severity per D-07. Layout mirrors `GameCard`:
  - **Desktop (`hidden sm:flex gap-3 items-center`):** `LazyMiniBoard` on the left (~100px), then a right-side `flex flex-col gap-2` containing: (a) header line with `display_name (opening_eco)` + deep-link affordance on the right, (b) prose sentence with trimmed move sequence + `(n=18)`, (c) optional metadata row (severity icon/label, candidate-move SAN chip — planner picks if useful).
  - **Mobile (`flex flex-col gap-2 sm:hidden`):** header line on top full-width, then board + content row below (`LazyMiniBoard` ~105px on the left, content stacked on the right).
  - When `display_name` is the `<unnamed line>` sentinel (per Phase 70 D-23 / D-34, normally dropped, but defensively handle), render in italicized muted text.
  - Card is a single click target — clicking anywhere on the card triggers the deep-link (D-13). The card is a semantic `<a>` (or `<button>` styled as a card) with `data-testid="opening-finding-card-{idx}"`. The `LazyMiniBoard` inside has all interaction disabled (per D-21).
- **D-04a:** **Reuse `LazyMiniBoard` from `GameCard.tsx`** — extract it into a shared module (`frontend/src/components/board/LazyMiniBoard.tsx` or similar) so both `GameCard` and `OpeningFindingCard` consume the same component. Configure it with `flipped={finding.color === 'black'}` so the user views the entry position from the side they actually played as, and `fen={finding.entry_fen}`. `IntersectionObserver` lazy-render keeps perf safe even with 16 cards rendered.
- **D-05:** **Move-sequence trim = "last 2 entry plys + the candidate move", with leading ellipsis.** For `entry_sequence = ["e4", "c5", "Nf3", "d6", "d4", "cxd4"]` and `candidate = "Nxd4"`, render `"...3.d4 cxd4 4.Nxd4"`. Move numbering is preserved (white plys keep their `N.` prefix; if the trim starts on a black ply, use `N...` Black-on-move notation). Fewer than 3 plys total (entry-sequence shorter than 2 plys) → render the whole sequence without ellipsis. The trimmer is a pure helper function in `frontend/src/lib/openingInsights.ts` (or near `arrowColor.ts`), unit-tested for the edge cases (3+ plys, 2 plys, 1 ply, white-on-move, black-on-move start).
- **D-06:** **Card prose template** (rendered on the second/third row of the card body):
  ```
  You {lose|win} {rate}% as {White|Black} after {trimmed_san_seq} (n={n_games})
  ```
  - `{lose|win}` = "lose" for weaknesses, "win" for strengths.
  - `{rate}` = `Math.round(loss_rate * 100)` for weaknesses, `Math.round(win_rate * 100)` for strengths.
  - `{White|Black}` = capitalized `finding.color`.
  - `(n={n_games})` is rendered inline, no W/D/L breakdown chip (explicit user choice — full counts are not surfaced anywhere in the card UI).
  - The "→ open in Move Explorer" call-to-action is NOT inline in the prose — it's the deep-link affordance on the card header (e.g. an `ExternalLink` icon on the right of the header line, mirroring `GameCard`'s `platformIconAndLink` pattern). The whole card is also click-targetable per D-04.
- **D-07:** **Severity → `border-l-4` accent color + (optional) rate-percent text shade.** The card's left-border accent maps to the existing arrow color thresholds, mirroring `GameCard`'s `BORDER_CLASSES` pattern:
  - `severity = "major"` (rate ≥ 60%) + `classification = "weakness"` → dark red border-left.
  - `severity = "minor"` (55% < rate < 60%) + `classification = "weakness"` → light red border-left.
  - `severity = "major"` + `classification = "strength"` → dark green border-left.
  - `severity = "minor"` + `classification = "strength"` → light green border-left.
  - Color values come from `frontend/src/lib/theme.ts` (must use the existing WDL semantic color constants — no hard-coded hexes per CLAUDE.md "theme constants in theme.ts" rule). If the existing constants don't have light/dark variants, planner adds them in `theme.ts` referencing `arrowColor.ts` `LIGHT_COLOR_THRESHOLD = 55` / `DARK_COLOR_THRESHOLD = 60` semantics. The rate-percent number in the prose MAY also be color-shaded (planner picks based on visual balance) but the `border-l-4` is the primary severity indicator. No severity badge, no icon.
- **D-08:** **Cap rendering matches Phase 70 backend caps.** Backend already returns at most 5 weaknesses and 3 strengths per color. Frontend renders all returned findings without further trimming. No "show more" affordance needed in v1 (the visible ceiling is 5+5+3+3 = 16 cards). The card stack inside each section uses `space-y-3` (matching `GameCardList`).

### Loading, Error, Empty States

- **D-09:** **Empty section copy** (per section): `"No {weakness|strength} findings cleared the threshold under your current filters."` muted small text. The block heading also surfaces the threshold once via an `InfoPopover` next to the block title: "Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%."
- **D-10:** **Empty block** (all four sections empty): single muted message at block level, replacing the four section headers — `"No opening findings cleared the threshold under your current filters. Try widening filters (longer recency window, more time controls) or import more games."` Same threshold copy as D-09.
- **D-11:** **Loading state** = animated skeleton matching the eventual layout (4 section headers, 2-3 placeholder cards each — each placeholder card uses the `border-l-4` chrome with a muted neutral accent and a square ~100px placeholder where the `LazyMiniBoard` will render). Use `animate-pulse` with `bg-muted/30` per existing `EndgameInsightsBlock` skeleton (see `frontend/src/components/insights/EndgameInsightsBlock.tsx:170-189`). No spinner-only state — opening insights take measurable time on first load (~ a few hundred ms) and a skeleton conveys progress better.
- **D-12:** **Error state** = inline `role="alert"` block: `"Failed to load opening insights. Something went wrong. Please try again in a moment."` + a "Try again" button (variant `brand-outline`) that calls `query.refetch()`. Pattern mirrors `EndgameInsightsBlock` `ErrorState` (line 322-352) but without the rate-limit / retry-minutes branch (no LLM rate limiting on this endpoint). Error capture goes through the global TanStack Query `QueryCache.onError` handler — do NOT add a duplicate `Sentry.captureException` in the component (per CLAUDE.md frontend Sentry rules).

### Deep-link to Move Explorer

- **D-13:** **Deep-link click handler reuses the `handleOpenGames` pattern (Openings.tsx:492-498) but routes to `/openings/explorer` instead of `/openings/games`.** Sequence:
  1. Replay `entry_sequence` SAN array onto `chess` instance: `chess.loadMoves(sanSequence)`. Reconstruct the SAN sequence by parsing back from `entry_fen` (initial position → entry_fen) — Phase 70's payload exposes `entry_fen` but not the SAN sequence directly. **Planner must verify whether to derive the SAN sequence from `entry_fen` (chess.js can replay if we expose moves) or have the backend extend the payload to return the SAN sequence directly. The latter is preferable: a small `entry_pgn: str` or `entry_san_sequence: list[str]` field on `OpeningInsightFinding` saves frontend work and avoids ambiguity. Decide during planning — if added, this is the single backend contract amendment Phase 71 may request from Phase 70.**
  2. `setBoardFlipped(finding.color === 'black')`.
  3. `setFilters(prev => ({ ...prev, color: finding.color, matchSide: 'both' }))` — match `handleOpenGames` exactly. Recency / timeControls / platforms / rated / opponentType / opponentStrength preserved from current state.
  4. `navigate('/openings/explorer')`.
  5. `window.scrollTo({ top: 0 })`.
- **D-14:** **No candidate-move highlight on arrival.** The user clicked the bullet; they know which move they intend to look at. The trimmed SAN sequence on the bullet plus the entry position is enough context. The Move Explorer's existing red/green arrows already render the candidate via `getArrowColor` — no additional emphasis is added. (Explicit user choice — rejected `hoveredMove` sticky-set, dedicated pinned arrow style, and pulse-on-arrival options.)
- **D-15:** **Whole card is the deep-link**, rendered as an `<a href="/openings/explorer">` (or `<button>` if a route-without-true-href is preferable) with `data-testid="opening-finding-card-{idx}"` (per CLAUDE.md browser automation rules). Click handler calls `e.preventDefault()` then runs the D-13 sequence (we want React Router-style client navigation, not a full page reload). `aria-label` describes the target: `"Open {finding.display_name} ({finding.candidate_move_san}) in Move Explorer"`. An `ExternalLink` (or similar) icon sits on the right of the card header as a visual affordance, mirroring `GameCard`'s `platformIconAndLink` pattern. Hover style: subtle `hover:bg-muted/30` + cursor-pointer to make the card feel actionable.

### Fetch / Data Layer

- **D-16:** **Auto-fetch via TanStack Query**, NOT a Generate-button mutation. Hook lives in `frontend/src/hooks/useOpeningInsights.ts`. Query key includes the full filter object (debounced — reuse the existing `debouncedFilters` from `Openings.tsx`). `staleTime` matches existing patterns (~30s) so tab switches don't refetch unnecessarily. No imperative `refetch()` in the happy path — purely filter-driven.
- **D-17:** **The block is filter-aware exactly like `Most Played Openings` already is** (`Openings.tsx:377-384` — passes `recency`, `timeControls`, `platforms`, `rated`, `opponentType`, `opponentStrength` from `debouncedFilters`). The block additionally always sends `color="all"` per D-02, regardless of `filters.color`.
- **D-18:** **Block hides itself entirely when the user has zero imported games**, mirroring how `Most Played Openings` is hidden via `mostPlayedData && mostPlayedData.white.length > 0`. The "import games to see insights" prompt is already handled at page level by existing onboarding affordances; the block doesn't duplicate that copy.

### Block Placement on Stats Subtab

- **D-19:** **Block renders at the top of the Stats tab content**, above the existing Bookmarks white/black sections, the Win Rate Chart, and the Most Played Openings sections. It's the primary insight surface (per INSIGHT-STATS-01 and SEED-005), so top placement is required. The block sits inside the existing `flex flex-col gap-4` container that wraps Stats content.
- **D-20:** **Block heading** = `Opening Insights` (matches `Endgame Insights` parallel naming on the Endgames page) with a `Lightbulb` icon (lucide-react) on the left and an `InfoPopover` on the right. The InfoPopover copy explains: scan domain (your candidate moves with ≥ 20 games), threshold (> 55% win or loss rate), filter scope (this block ignores the active color filter so both colors always render), and that strengths show high-confidence wins / weaknesses show high-confidence losses.

### Mobile / Accessibility

- **D-21:** **Mobile and desktop card layouts mirror `GameCard` exactly** (Mobile: header full-width on top, then board + content row; Desktop: board on the left, content stacked on the right). `LazyMiniBoard` size: 105px on mobile, 100px on desktop (matches `GameCard`'s `MOBILE_BOARD_SIZE` / `DESKTOP_BOARD_SIZE`). All card interactions disabled on the `LazyMiniBoard` (it's a non-interactive thumbnail). `data-testid` per CLAUDE.md frontend rules: `data-testid="opening-insights-block"` on the outer block card, `data-testid="opening-finding-card-{idx}"` per finding card, `data-testid="opening-insights-section-{section_key}"` per section. Section keys: `white-weaknesses`, `black-weaknesses`, `white-strengths`, `black-strengths`.
- **D-22:** **Touch targets ≥ 44px** for the deep-link card (per CLAUDE.md). The card body is fully click-targetable; the only nested interactive is the block-heading `InfoPopover` trigger (sits outside the card stack). `LazyMiniBoard` has no click handlers and no drag affordance.

### Claude's Discretion

- File layout: `frontend/src/components/insights/OpeningInsightsBlock.tsx` and a new `frontend/src/components/insights/OpeningFindingCard.tsx` (alongside existing `EndgameInsightsBlock.tsx`). Hook in `frontend/src/hooks/useOpeningInsights.ts`. Helpers in `frontend/src/lib/openingInsights.ts` (move-sequence trim function, severity-color map). Type definitions in `frontend/src/types/insights.ts` extending the existing file (don't make a new types file). `LazyMiniBoard` extracted from `GameCard.tsx` into a shared module (`frontend/src/components/board/LazyMiniBoard.tsx` — planner picks the exact path) and consumed by both `GameCard` and `OpeningFindingCard`.
- Whether sections render as `<ul>` + `<li>` (semantic correctness, recommended) or flat `<div>` lists. The existing `GameCardList` uses `<div>` with `space-y-3` — match that pattern for consistency.
- Whether to memoize the SAN-sequence trim and severity-class lookups (likely not needed — 16 cards × cheap function calls).
- Exact `staleTime` / `gcTime` for the TanStack Query hook. 30s staleTime is the existing convention; pick what's consistent.
- Whether the rate-percent number in the prose gets its own color shade or inherits the muted-foreground default. Likely yes for emphasis, but pick based on visual balance against the `border-l-4` accent.
- Whether to share the threshold copy ("≥ 20 games per move, > 55% win or loss rate") via a top-level constant in `frontend/src/lib/openingInsights.ts` to keep wording in sync between the InfoPopover (D-20) and the empty-state messages (D-09 / D-10). Recommended yes.
- Whether the card is rendered as `<a href>` (true link semantics) or `<button>` (action semantics). The destination IS a route, so `<a>` with `e.preventDefault()` + React Router navigation is preferred.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/REQUIREMENTS.md` §INSIGHT-STATS-01..INSIGHT-STATS-06 — locked frontend requirements for this phase.
- `.planning/ROADMAP.md` Phase 71 (lines 213-224) — success criteria. Note success-criterion 2 wording specifies "[open in Move Explorer]" deep-link copy and red/green semantic theme colors.
- `.planning/seeds/SEED-005-opening-weakness-insights.md` §"Phase B: Frontend — Stats subtab integration" — original UX intent. The "Why Self-Referential Is Sufficient" section is informational only; Phase 71 doesn't touch the algorithm.
- `.planning/PROJECT.md` §"v1.13 Opening Insights" — milestone scope.

### Phase 70 Backend Contract (locked)
- `.planning/phases/70-backend-opening-insights-service/70-CONTEXT.md` — Phase 70 decisions, especially D-01 / D-02 (4-section response shape), D-03 (`color` field on findings), D-04 / D-05 (classification + severity tiers mapping to `arrowColor.ts`), D-12 (always returns all 4 sections regardless of `color` filter), D-25 (`entry_fen` + `candidate_move_san` are flat fields), D-22 (`display_name` includes "vs. " prefix where applicable), D-23 / D-34 (`<unnamed line>` sentinel handling — usually dropped).
- `app/schemas/opening_insights.py` — final wire schema. `OpeningInsightFinding` fields: `color`, `classification`, `severity`, `opening_name`, `opening_eco`, `display_name`, `entry_fen`, `entry_full_hash`, `candidate_move_san`, `resulting_full_hash`, `n_games`, `wins`, `draws`, `losses`, `win_rate`, `loss_rate`, `score`. Note that `entry_pgn` / `entry_san_sequence` is **NOT currently in the payload** — see D-13 for the question of whether Phase 71 requests this addition.
- `app/routers/insights.py::generate_openings_insights` — `POST /api/insights/openings` route, body = `OpeningInsightsRequest`.

### Existing Frontend (read-only inputs / reuse points)
- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — visual conventions parallel: `charcoal-texture rounded-md p-4` card, `<Lightbulb>` heading, skeleton block (`animate-pulse` lines 170-189), `ErrorState` (lines 322-352), `InsightsCard` sub-component (lines 297-320). Phase 71 mirrors these patterns where applicable but has NO Generate button / no LLM rate-limit branch.
- `frontend/src/pages/Openings.tsx` — host page. Stats tab content lives around lines 670-1008; deep-link target tab is `explorer` (lines 504, 616). `handleOpenGames` (line 492-498) is the prototype for the deep-link click handler (Phase 71's handler routes to `/openings/explorer` instead of `/openings/games`).
- `frontend/src/components/results/GameCard.tsx` — **Phase 71's `OpeningFindingCard` is modeled directly on this component** (D-04). Reuse: card chrome (`border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3`), `LazyMiniBoard` IntersectionObserver lazy-render pattern (lines 14-42), `BORDER_CLASSES` color-coding via classification+severity, mobile vs desktop layouts (vertical stack on mobile, horizontal on desktop), `platformIconAndLink`-style header affordance.
- `frontend/src/components/results/GameCardList.tsx` — list wrapper pattern (`space-y-3`); reuse for the section-internal card stack.
- `frontend/src/components/stats/MinimapPopover.tsx` — existing minimap (hover popover). **Phase 71 does NOT use this component** — D-04 mandates always-visible cards with `LazyMiniBoard`. The underlying `react-chessboard` rendering with `BOARD_DARK_SQUARE` / `BOARD_LIGHT_SQUARE` from `theme.ts` is the right reference for board styling.
- `frontend/src/lib/arrowColor.ts` — `LIGHT_COLOR_THRESHOLD = 55`, `DARK_COLOR_THRESHOLD = 60`, `getArrowColor`. The bullet severity colors must match these arrow-color shades exactly so the bullet color and the on-board arrow color align after deep-link.
- `frontend/src/lib/theme.ts` — WDL semantic colors. Add light/dark variants here if missing (per D-07).
- `frontend/src/hooks/useStats.ts::useMostPlayedOpenings` — pattern reference for the `useOpeningInsights` hook (filter-driven TanStack Query, debounced filter input).
- `frontend/src/lib/queryClient.ts` — global `QueryCache.onError` / `MutationCache.onError` Sentry capture. Phase 71 relies on this — no per-component Sentry calls.
- `frontend/src/components/filters/FilterPanel.tsx` `FilterState` / `DEFAULT_FILTERS` — filter shape consumed by the hook.
- `frontend/src/types/insights.ts` — extend with the Phase 71 types (don't create a new file). Mirror Phase 70 schema as a TS type — likely re-export with renamed fields where convention differs.

### Anti-Patterns to Avoid
- `frontend/src/pages/Endgames.tsx::handleGenerateInsights` — DO NOT copy this pattern. Phase 71 has no Generate button and no insights cache by-filter — the TanStack Query layer handles caching and refetching declaratively.
- Hard-coded color hexes — every WDL color comes from `theme.ts` (CLAUDE.md frontend rule, see "Theme constants in theme.ts").

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`frontend/src/lib/arrowColor.ts`** — exports `getArrowColor(winPct, lossPct, gameCount, isHovered)` plus `LIGHT_COLOR_THRESHOLD = 55` and `DARK_COLOR_THRESHOLD = 60`. The same thresholds drive Phase 70's classifier and Phase 71's `border-l-4` shading. Severity-shade mapping logic should derive from these constants (or live alongside them in the same module) so a future arrow-color tweak updates both surfaces.
- **`frontend/src/components/results/GameCard.tsx`** — primary visual reference for `OpeningFindingCard`. Reuse: card chrome, `LazyMiniBoard`, `BORDER_CLASSES` pattern, mobile/desktop responsive layout, header affordance pattern.
- **`frontend/src/components/results/GameCardList.tsx`** — `space-y-3` stack wrapper. Mirror for section-internal card lists.
- **`frontend/src/components/insights/EndgameInsightsBlock.tsx`** — visual chrome for the OUTER block: `charcoal-texture rounded-md p-4` card, `Lightbulb` heading icon, `animate-pulse` skeleton, `ErrorState` with try-again button. Reuse the OUTER chrome; skip the Generate-button / cache / mutation infrastructure. INNER cards follow `GameCard`, not `InsightsCard`.
- **`frontend/src/components/ui/InfoPopover`** — already used throughout the Stats tab for column / section explanations. Use for the block heading explainer (D-20).
- **`MiniBoard` (or whatever `LazyMiniBoard` wraps)** — used by `GameCard`. Configure for `OpeningFindingCard` with `flipped={finding.color === 'black'}`, `fen={finding.entry_fen}`, size 100/105 (desktop/mobile per D-21). Lazy-rendered via IntersectionObserver to keep perf safe with 16 cards.
- **`useDebounce` / `debouncedFilters`** — already wired in `Openings.tsx`. The Phase 71 hook should consume the same `debouncedFilters` so a filter sweep doesn't fire 5 requests.
- **`Openings.tsx::handleOpenGames`** — prototype pattern for deep-link click: load PGN, set boardFlipped, update filters, navigate. Phase 71's handler is a near-copy retargeted to `/openings/explorer`.

### Established Patterns

- **Stats tab section card** = `<div className="charcoal-texture rounded-md p-4" data-testid="...">` with an `<h2>` heading containing icon + title + InfoPopover. Mirror exactly.
- **Filter awareness** = pass `debouncedFilters` fields explicitly to a TanStack Query hook (don't pass the whole filter object — the hooks file shows explicit field passing in `useMostPlayedOpenings`).
- **Loading/error/empty ternary chain** = `isLoading ? Skeleton : isError ? ErrorBlock : data?.length ? Render : EmptyState` (per CLAUDE.md frontend Sentry rule: "always handle isError in data-loading ternary chains" — never let errors fall through to "no data" empty state).
- **Mobile-first responsive layout** = single-column flex stacks; no separate mobile component for D-21 (block is identical at all breakpoints, only the inline thumbnail size adjusts via Tailwind responsive classes if needed).
- **`data-testid` and ARIA** = mandatory on every interactive element per CLAUDE.md "Browser Automation Rules". Naming: `btn-`, `nav-`, `filter-`, `{component}-{element}-{id}` patterns.

### Integration Points

- **Stats tab content stream** in `Openings.tsx` (around line 800–1007) — Phase 71 inserts the `OpeningInsightsBlock` at the top of this stream, before the bookmarks section.
- **`debouncedFilters`** flows from `Openings.tsx` into the new hook — passed as a prop to the block, then forwarded to the hook.
- **TanStack Query global error handler** in `frontend/src/lib/queryClient.ts` — handles Sentry capture; no per-component capture.
- **No new backend route, no schema change** — Phase 71 is pure frontend assembly. **Possible exception:** D-13 flags whether to ask Phase 70 to add `entry_san_sequence: list[str]` (or `entry_pgn: str`) to `OpeningInsightFinding` so the frontend doesn't have to derive the SAN sequence from `entry_fen`. Planner decides during planning; if added, it's a tiny additive change at the schema/service boundary in Phase 70 code.

</code_context>

<specifics>
## Specific Ideas

- **Roadmap exemplar for the prose copy:** "You lose 62% as Black after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (n=18) → [open in Move Explorer]" — Phase 71's card prose is a trimmed variant of this exemplar (3-ply trim per D-05); the deep-link is a card-level affordance, not inline in the prose.
- **Render findings as cards, not bullets — modeled on `GameCard`** — explicit user request mid-discussion. `border-l-4` severity accent + `LazyMiniBoard` + mobile/desktop responsive layout.
- **No candidate-move highlight on arrival in Move Explorer** — explicit user choice; the trimmed SAN + the entry position is enough context.
- **Block ignores the global `color` filter** — explicit user choice; deep-link click updates the color filter.

</specifics>

<deferred>
## Deferred Ideas

- **Move sequence with full PGN context (4+ plys)** — D-05 locks 3-ply trim. Some users may want longer context; revisit after Phase 71 telemetry / user feedback.
- **W/D/L breakdown chip per bullet** — D-06 locks `(n=18)` only. If users routinely want the breakdown, add as a hover tooltip in a polish pass.
- **Severity badge / icon (e.g. ⚠ for major weaknesses)** — D-07 locks color-shade-only severity. Visible severity badges are deferred unless arrow-color shading proves insufficient on greyscale displays.
- **`hoveredMove` sticky-set on deep-link arrival** — D-14 says no highlight on arrival. If users miss the candidate move on arrival, revisit with the sticky-hovered-arrow approach.
- **Aggregate / meta-recommendation bullet at the top of the block** — explicitly Phase 73 (stretch, INSIGHT-META-01); not in Phase 71.
- **Inline bullets on Openings → Moves (Move Explorer view)** — explicitly Phase 72; not in Phase 71.
- **Bookmark badge on findings** — explicitly Phase 74 (stretch); not in Phase 71.

</deferred>

---

*Phase: 71-frontend-stats-subtab-openinginsightsblock*
*Context gathered: 2026-04-27*
