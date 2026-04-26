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

### Bullet Content & Rendering

- **D-04:** **Each bullet renders as a two-row card with an inline 64–80px chessboard thumbnail on the left.** Row 1: `display_name (opening_eco)` in `text-sm font-semibold` (e.g. "Sicilian Defense, Najdorf (B90)"). Row 2: prose sentence including the trimmed move sequence and `n_games` (see D-05, D-06). Last row of the bullet: a deep-link button/anchor labeled "open in Move Explorer →" (see D-13). Bullet uses `flex gap-3 items-start` so thumbnail and text sit side-by-side.
  - When `display_name` is the `<unnamed line>` sentinel (per Phase 70 D-23 / D-34, this case should be already dropped, but defensively handle), render `display_name` as italicized muted text.
  - The minimap thumbnail is **always-visible inline**, NOT a hover popover — explicit user request (rejected the existing `MinimapPopover` hover pattern in favor of always-visible). Use `react-chessboard` `Chessboard` set to non-interactive (`allowDragging={false}`, no click handlers) at fixed size, with `boardOrientation` matching `finding.color` so the user views the position from the side they actually played as.
- **D-05:** **Move-sequence trim = "last 2 entry plys + the candidate move", with leading ellipsis.** For `entry_sequence = ["e4", "c5", "Nf3", "d6", "d4", "cxd4"]` and `candidate = "Nxd4"`, render `"...3.d4 cxd4 4.Nxd4"`. Move numbering is preserved (white plys keep their `N.` prefix; if the trim starts on a black ply, use `N...` Black-on-move notation). Fewer than 3 plys total (entry-sequence shorter than 2 plys) → render the whole sequence without ellipsis. The trimmer is a pure helper function in `frontend/src/lib/openingInsights.ts` (or near `arrowColor.ts`), unit-tested for the edge cases (3+ plys, 2 plys, 1 ply, white-on-move, black-on-move start).
- **D-06:** **Bullet prose template:**
  ```
  You {lose|win} {rate}% as {White|Black} after {trimmed_san_seq} (n={n_games}) → [open in Move Explorer]
  ```
  - `{lose|win}` = "lose" for weaknesses, "win" for strengths.
  - `{rate}` = `Math.round(loss_rate * 100)` for weaknesses, `Math.round(win_rate * 100)` for strengths.
  - `{White|Black}` = capitalized `finding.color`.
  - `(n={n_games})` is rendered inline, no W/D/L breakdown chip (explicit user choice — full counts are not surfaced anywhere in the bullet UI).
- **D-07:** **Severity → text color shade.** The whole bullet's accent color (or the rate-percent number, planner picks) maps to the existing arrow color thresholds:
  - `severity = "major"` (rate ≥ 60%) → dark green for strengths / dark red for weaknesses.
  - `severity = "minor"` (55% < rate < 60%) → light green for strengths / light red for weaknesses.
  - Color values come from `frontend/src/lib/theme.ts` (must use the existing WDL semantic color constants — no hard-coded hexes per CLAUDE.md "theme constants in theme.ts" rule). If the existing constants don't have light/dark variants, planner adds them in `theme.ts` referencing `arrowColor.ts` `LIGHT_COLOR_THRESHOLD = 55` / `DARK_COLOR_THRESHOLD = 60` semantics. No severity badge, no icon — color shade is the entire severity treatment.
- **D-08:** **Cap rendering matches Phase 70 backend caps.** Backend already returns at most 5 weaknesses and 3 strengths per color. Frontend renders all returned findings without further trimming. No "show more" affordance needed in v1 (the visible ceiling is 5+5+3+3 = 16 bullets).

### Loading, Error, Empty States

- **D-09:** **Empty section copy** (per section): `"No {weakness|strength} findings cleared the threshold under your current filters."` muted small text. The block heading also surfaces the threshold once via an `InfoPopover` next to the block title: "Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%."
- **D-10:** **Empty block** (all four sections empty): single muted message at block level, replacing the four section headers — `"No opening findings cleared the threshold under your current filters. Try widening filters (longer recency window, more time controls) or import more games."` Same threshold copy as D-09.
- **D-11:** **Loading state** = animated skeleton matching the eventual layout (4 section headers, 2-3 placeholder bullets each, 64–80px square placeholder where the minimap will be). Use `animate-pulse` with `bg-muted/30` per existing `EndgameInsightsBlock` skeleton (see `frontend/src/components/insights/EndgameInsightsBlock.tsx:170-189`). No spinner-only state — opening insights take measurable time on first load (~ a few hundred ms) and a skeleton conveys progress better.
- **D-12:** **Error state** = inline `role="alert"` block: `"Failed to load opening insights. Something went wrong. Please try again in a moment."` + a "Try again" button (variant `brand-outline`) that calls `query.refetch()`. Pattern mirrors `EndgameInsightsBlock` `ErrorState` (line 322-352) but without the rate-limit / retry-minutes branch (no LLM rate limiting on this endpoint). Error capture goes through the global TanStack Query `QueryCache.onError` handler — do NOT add a duplicate `Sentry.captureException` in the component (per CLAUDE.md frontend Sentry rules).

### Deep-link to Move Explorer

- **D-13:** **Deep-link click handler reuses the `handleOpenGames` pattern (Openings.tsx:492-498) but routes to `/openings/explorer` instead of `/openings/games`.** Sequence:
  1. Replay `entry_sequence` SAN array onto `chess` instance: `chess.loadMoves(sanSequence)`. Reconstruct the SAN sequence by parsing back from `entry_fen` (initial position → entry_fen) — Phase 70's payload exposes `entry_fen` but not the SAN sequence directly. **Planner must verify whether to derive the SAN sequence from `entry_fen` (chess.js can replay if we expose moves) or have the backend extend the payload to return the SAN sequence directly. The latter is preferable: a small `entry_pgn: str` or `entry_san_sequence: list[str]` field on `OpeningInsightFinding` saves frontend work and avoids ambiguity. Decide during planning — if added, this is the single backend contract amendment Phase 71 may request from Phase 70.**
  2. `setBoardFlipped(finding.color === 'black')`.
  3. `setFilters(prev => ({ ...prev, color: finding.color, matchSide: 'both' }))` — match `handleOpenGames` exactly. Recency / timeControls / platforms / rated / opponentType / opponentStrength preserved from current state.
  4. `navigate('/openings/explorer')`.
  5. `window.scrollTo({ top: 0 })`.
- **D-14:** **No candidate-move highlight on arrival.** The user clicked the bullet; they know which move they intend to look at. The trimmed SAN sequence on the bullet plus the entry position is enough context. The Move Explorer's existing red/green arrows already render the candidate via `getArrowColor` — no additional emphasis is added. (Explicit user choice — rejected `hoveredMove` sticky-set, dedicated pinned arrow style, and pulse-on-arrival options.)
- **D-15:** **Deep-link element = `<a>` styled as a button-link** with `data-testid="opening-finding-deeplink-{idx}"` (per CLAUDE.md browser automation rules). Use `<a>` because the destination is a navigable URL (semantic correctness: it's a navigation, not an action). Click handler calls `e.preventDefault()` then runs the D-13 sequence (we still want React Router-style client navigation, not a full page load). `aria-label` describes the target: `"Open {finding.display_name} ({finding.candidate_move_san}) in Move Explorer"`.

### Fetch / Data Layer

- **D-16:** **Auto-fetch via TanStack Query**, NOT a Generate-button mutation. Hook lives in `frontend/src/hooks/useOpeningInsights.ts`. Query key includes the full filter object (debounced — reuse the existing `debouncedFilters` from `Openings.tsx`). `staleTime` matches existing patterns (~30s) so tab switches don't refetch unnecessarily. No imperative `refetch()` in the happy path — purely filter-driven.
- **D-17:** **The block is filter-aware exactly like `Most Played Openings` already is** (`Openings.tsx:377-384` — passes `recency`, `timeControls`, `platforms`, `rated`, `opponentType`, `opponentStrength` from `debouncedFilters`). The block additionally always sends `color="all"` per D-02, regardless of `filters.color`.
- **D-18:** **Block hides itself entirely when the user has zero imported games**, mirroring how `Most Played Openings` is hidden via `mostPlayedData && mostPlayedData.white.length > 0`. The "import games to see insights" prompt is already handled at page level by existing onboarding affordances; the block doesn't duplicate that copy.

### Block Placement on Stats Subtab

- **D-19:** **Block renders at the top of the Stats tab content**, above the existing Bookmarks white/black sections, the Win Rate Chart, and the Most Played Openings sections. It's the primary insight surface (per INSIGHT-STATS-01 and SEED-005), so top placement is required. The block sits inside the existing `flex flex-col gap-4` container that wraps Stats content.
- **D-20:** **Block heading** = `Opening Insights` (matches `Endgame Insights` parallel naming on the Endgames page) with a `Lightbulb` icon (lucide-react) on the left and an `InfoPopover` on the right. The InfoPopover copy explains: scan domain (your candidate moves with ≥ 20 games), threshold (> 55% win or loss rate), filter scope (this block ignores the active color filter so both colors always render), and that strengths show high-confidence wins / weaknesses show high-confidence losses.

### Mobile / Accessibility

- **D-21:** **Mobile = same single-column rendering**, no separate desktop/mobile paths. The bullet's `flex gap-3` thumbnail-plus-text layout works at 375px width. The 64–80px thumbnail is small enough to leave readable line length on mobile. `data-testid` per CLAUDE.md frontend rules: `data-testid="opening-insights-block"` on the card, `data-testid="opening-finding-{idx}"` per bullet, `data-testid="opening-insights-section-{section_key}"` per section. Section keys: `white-weaknesses`, `black-weaknesses`, `white-strengths`, `black-strengths`.
- **D-22:** **Touch targets ≥ 44px** for the deep-link element (per CLAUDE.md). The whole bullet card is also click-targetable as a deep-link (no nested interactive elements other than the `InfoPopover` trigger and the explicit deep-link anchor — minimap board has all interaction disabled).

### Claude's Discretion

- File layout: `frontend/src/components/insights/OpeningInsightsBlock.tsx` (alongside existing `EndgameInsightsBlock.tsx`). Hook in `frontend/src/hooks/useOpeningInsights.ts`. Helpers in `frontend/src/lib/openingInsights.ts` (move-sequence trim function, severity-color map). Type definitions in `frontend/src/types/insights.ts` extending the existing file (don't make a new types file).
- Exact thumbnail size between 64px and 80px (planner picks based on visual balance once rendered). Consider 64px on mobile if 80px crowds the row at 375px width.
- Whether the bullet is a `<li>` inside an `<ul>` per section (semantic correctness, recommended) or a flat `<div>` list (simpler styling). Lean toward `<ul>` + `<li>` since it's structurally a list of findings.
- Whether to memoize the SAN-sequence trim and `getArrowColor`-derived class lookups (likely not needed — 16 bullets × cheap function calls).
- Exact `staleTime` / `gcTime` for the TanStack Query hook. 30s staleTime is the existing convention; pick what's consistent.
- Whether to share the threshold copy ("≥ 20 games per move, > 55% win or loss rate") via a top-level constant in `frontend/src/lib/openingInsights.ts` to keep wording in sync between the InfoPopover (D-20) and the empty-state messages (D-09 / D-10). Recommended yes.

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
- `frontend/src/components/stats/MinimapPopover.tsx` — existing minimap (hover popover). **Phase 71 does NOT use this component** — D-04 mandates always-visible inline minimaps. But the underlying `react-chessboard` rendering with `BOARD_DARK_SQUARE` / `BOARD_LIGHT_SQUARE` from `theme.ts` is the right reference.
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

- **`frontend/src/lib/arrowColor.ts`** — exports `getArrowColor(winPct, lossPct, gameCount, isHovered)` plus `LIGHT_COLOR_THRESHOLD = 55` and `DARK_COLOR_THRESHOLD = 60`. The same thresholds drive Phase 70's classifier and Phase 71's bullet shading. Severity-shade mapping logic should derive from these constants (or live alongside them in the same module) so a future arrow-color tweak updates both surfaces.
- **`frontend/src/components/insights/EndgameInsightsBlock.tsx`** — visual chrome: `charcoal-texture rounded-md p-4` card, `Lightbulb` heading icon, `animate-pulse` skeleton, `ErrorState` with try-again button, `MaybeBlockedTooltip`, `InsightsCard` sub-component (rounded inner card with icon + title). Reuse the chrome patterns; skip the Generate-button / cache / mutation infrastructure.
- **`frontend/src/components/ui/InfoPopover`** — already used throughout the Stats tab for column / section explanations. Use for the block heading explainer (D-20).
- **`react-chessboard` `Chessboard` component** — used in `Openings.tsx` and `MinimapPopover.tsx`. Configure for the inline thumbnail with `allowDragging={false}`, no click handlers, fixed `boardWidth={64..80}`, `customDarkSquareStyle` / `customLightSquareStyle` from `theme.ts`. `boardOrientation = finding.color`.
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

- **Roadmap exemplar for the bullet copy:** "You lose 62% as Black after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (n=18) → [open in Move Explorer]" — Phase 71's bullet is a trimmed variant of this exemplar (3-ply trim per D-05).
- **Always-visible inline minimap** — explicit user request, in contrast to the existing `MinimapPopover` hover pattern. The user wants the position visible at a glance without interaction.
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
