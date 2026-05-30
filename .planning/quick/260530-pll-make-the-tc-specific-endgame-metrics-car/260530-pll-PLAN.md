---
phase: quick-260530-pll
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/EndgameMetricsByTcCard.tsx
  - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx
  - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
autonomous: false
requirements: []

must_haves:
  truths:
    - "Each per-TC Endgame Metrics card is collapsible with a chevron, like the Endgame Type Breakdown cards"
    - "The primary-TC metrics card is expanded by default; all other metrics cards are collapsed"
    - "The Endgame ELO Timeline shows only the primary-TC series enabled by default; other-TC series start hidden"
    - "When the primary TC was played on both chess.com and lichess, both platform series are enabled by default in the timeline"
    - "Opening or closing one metrics card does not collapse another (independent accordion)"
    - "Changing filters resets the metrics accordion and the timeline default to the recomputed primary TC"
  artifacts:
    - path: "frontend/src/components/charts/EndgameMetricsByTcCard.tsx"
      provides: "Collapsible per-TC metrics card built on the shared Accordion primitive"
      contains: "AccordionItem"
    - path: "frontend/src/components/charts/EndgameMetricsByTcSection.tsx"
      provides: "Accordion orchestrator with primary-TC default-expand"
      contains: "computePrimaryTc"
    - path: "frontend/src/components/charts/EndgameEloTimelineSection.tsx"
      provides: "Primary-TC + both-platform default visibility for timeline series"
      contains: "computePrimaryTc"
  key_links:
    - from: "frontend/src/pages/Endgames.tsx"
      to: "EndgameMetricsByTcSection"
      via: "filterKey prop (JSON.stringify(appliedFilters))"
      pattern: "filterKey="
    - from: "EndgameMetricsByTcSection"
      to: "computePrimaryTc"
      via: "default-expand selection"
      pattern: "computePrimaryTc"
    - from: "EndgameEloTimelineSection"
      to: "computePrimaryTc"
      via: "default-visible series selection"
      pattern: "computePrimaryTc"
---

<objective>
Make the per-TC Endgame Metrics cards (Conversion / Parity / Recovery) collapsible using the same accordion pattern as the Endgame Type Breakdown cards (Phase 98). Expand the primary-TC card by default and collapse the others. In the Endgame ELO Timeline chart, default to enabling only the primary-TC series (both chess.com and lichess if both were played) and disable the rest. Reuse the existing `computePrimaryTc` heuristic and the shared `Accordion` primitive — do not invent new mechanisms.

Purpose: Consistency with the Phase 98 disclosure pattern and a cleaner default view that surfaces the user's main time control first across both the metrics cards and the timeline.

Output: Updated metrics card + section + timeline + page wiring, with tests updated to match the new default behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

@frontend/src/components/charts/EndgameTypeTcCard.tsx
@frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
@frontend/src/components/charts/EndgameMetricsByTcCard.tsx
@frontend/src/components/charts/EndgameMetricsByTcSection.tsx
@frontend/src/components/charts/EndgameEloTimelineSection.tsx
@frontend/src/lib/primaryTc.ts
@frontend/src/components/ui/accordion.tsx
@frontend/src/types/endgames.ts

Reference facts (already scouted — do not re-derive):
- `computePrimaryTc(categoriesByTc, minGames)` lives in `frontend/src/lib/primaryTc.ts`. It accepts `Record<string, { total: number }[]>` and returns `'bullet' | 'blitz' | 'rapid' | 'classical' | null`. It time-weights games via `NOMINAL_DURATION` so bullet's volume edge is neutralized.
- `MIN_GAMES_PER_TC_CARD = 20` is exported from `frontend/src/generated/endgameZones.ts`.
- `EndgameTypeBreakdownSection` is the reference accordion orchestrator: `<Accordion type="multiple" value={expandedTcs} onValueChange={setExpandedTcs}>`, seeded with `[primary]` via `computePrimaryTc`, reset on `filterKey` change via `useEffect`. Reuse this exact shape.
- `EndgameTypeTcCard` is the reference collapsible card: the charcoal header band IS the `AccordionTrigger` (with `data-[state=open]:border-b` so the bottom separator only shows when expanded), the body is `AccordionContent className="p-0"`. The shared `Accordion`/`AccordionTrigger` already renders the chevron and ARIA — no manual chevron needed.
- `EndgameMetricsByTcCard` currently renders a plain `<div data-testid="metrics-tc-card-{tc}">` with a header band `<div ... data-testid="metrics-tc-card-{tc}-header">` and a body `<div className="flex flex-col lg:flex-row p-4">`. The header band already uses `bg-black/20 border-b border-border/40`.
- `EndgameMetricsByTcSection` receives `data: EndgameMetricsCardsResponse` (`{ cards: EndgameMetricsTcCard[] }`, each card has `tc` and `total`) and renders cards in a plain `<div className="w-full mt-2 flex flex-col gap-4">`. The backend already pre-filters cards to eligible TCs in bullet→blitz→rapid→classical order.
- Endgames.tsx renders `<EndgameMetricsByTcSection data=... ratingAnchors=... />` around line 621 WITHOUT a filterKey, and renders `<EndgameTypeBreakdownSection ... filterKey={JSON.stringify(appliedFilters)} ... />` around line 681. The ELO timeline `<EndgameEloTimelineSection data={eloTimelineData} ... />` is around line 605.
- The ELO timeline currently default-hides via `computeDefaultHidden(combos)` using active-weeks ratio + `MAX_DEFAULT_VISIBLE = 1` ranking by total games. Combos are keyed by `combo_key` (e.g. `chess_com_blitz`) and each combo carries `time_control` ('bullet'|'blitz'|'rapid'|'classical') and `platform` ('chess.com'|'lichess'). Each point has `per_week_total_games`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make the per-TC Endgame Metrics cards collapsible with primary-TC default-expand</name>
  <files>frontend/src/components/charts/EndgameMetricsByTcCard.tsx, frontend/src/components/charts/EndgameMetricsByTcSection.tsx, frontend/src/pages/Endgames.tsx, frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx</files>
  <behavior>
    - The section renders an `<Accordion type="multiple">` (independent fold/unfold per UAT 98) wrapping one `EndgameMetricsByTcCard` per backend-provided card; the `metrics-tc-card-{tc}` root testids are preserved for every card.
    - On first render the card whose tc equals the primary TC is expanded; all other cards are collapsed. Primary TC is computed via `computePrimaryTc` using the cards' `total` values (build `Record<tc, [{ total: card.total }]>`), with `MIN_GAMES_PER_TC_CARD` as the floor.
    - When `filterKey` changes, the expanded set resets to just the recomputed primary TC.
    - The card header band remains the visible trigger (TC icon + label + "Games: x%" count) and carries a chevron supplied by the shared `AccordionTrigger`; the bottom separator only shows when expanded (`data-[state=open]:border-b`), matching `EndgameTypeTcCard`.
    - The trigger has `data-testid="metrics-tc-card-{tc}-trigger"` and an `aria-label` (e.g. "{TC label} endgame metrics"). The existing `metrics-tc-card-{tc}-header` testid stays on the header content.
    - Collapsed cards keep their `metrics-tc-card-{tc}` root in the DOM (accordion content is mounted/unmounted by Radix, but the AccordionItem root persists), so the existing section tests asserting card-root presence and DOM order still pass.
  </behavior>
  <action>
    Refactor `EndgameMetricsByTcCard` to render as an accordion item instead of a plain div, mirroring `EndgameTypeTcCard`: replace the outer `<div data-testid="metrics-tc-card-{tc}">` with `<AccordionItem value={card.tc} data-testid="metrics-tc-card-{card.tc}" className="charcoal-texture rounded-md overflow-hidden border-none">`. Convert the existing header band `<div>` into an `<AccordionTrigger data-testid="metrics-tc-card-{card.tc}-trigger" aria-label="{TC_LABELS[card.tc]} endgame metrics">` — port the existing header className but follow EndgameTypeTcCard's pattern: `border-0 rounded-none data-[state=open]:border-b data-[state=open]:border-b-border/40 text-left hover:no-underline [&>svg:last-child]:ml-0` and keep `bg-black/20 px-4 py-3`. Keep the inner header content (TimeControlIcon + TC label + the "Games: x%" total span) inside the trigger, retaining `data-testid="metrics-tc-card-{card.tc}-header"` on a wrapper. Wrap the three-metric body (`flex flex-col lg:flex-row p-4` block, including the divider logic) in `<AccordionContent className="p-0">` so the body keeps its own p-4. Do not add a manual chevron — the shared AccordionTrigger renders it. Import `AccordionContent, AccordionItem, AccordionTrigger` from `@/components/ui/accordion`.

    Refactor `EndgameMetricsByTcSection` to mirror `EndgameTypeBreakdownSection`: add a `filterKey?: string` prop. Split into an outer guard + inner component if needed to keep hooks unconditional (the type-breakdown section does this). Compute the primary TC by reducing `data.cards` into `Record<tc, [{ total: card.total }]>` and calling `computePrimaryTc(byTc, MIN_GAMES_PER_TC_CARD)`. Hold `const [expandedTcs, setExpandedTcs] = useState<string[]>(() => primary ? [primary] : [])` and a `useEffect` keyed on `filterKey` that resets to the recomputed primary. Replace the `<div className="w-full mt-2 flex flex-col gap-4">` wrapper with `<Accordion type="multiple" value={expandedTcs} onValueChange={setExpandedTcs} className="flex flex-col gap-4 mt-2">`. Keep the empty-state branch and the `endgame-metrics-tc-section` / `-empty` testids unchanged. Preserve the existing `grandTotal` and `ratingAnchors` plumbing into each card. Import `computePrimaryTc` from `@/lib/primaryTc`, `MIN_GAMES_PER_TC_CARD` from `@/generated/endgameZones`, and `Accordion` from `@/components/ui/accordion`.

    In `Endgames.tsx`, pass `filterKey={JSON.stringify(appliedFilters)}` to `<EndgameMetricsByTcSection>` (same expression already used for `EndgameTypeBreakdownSection`).

    Update `EndgameMetricsByTcSection.test.tsx`: existing assertions on the section wrapper testid, empty state, card-root presence, and DOM order should continue to pass (card roots persist). Add a test that the primary-TC card's `AccordionItem` is open by default (assert the trigger of the primary TC has `aria-expanded="true"` / `data-state="open"` and a non-primary trigger is `data-state="closed"`). Use cards whose `total` values make the primary TC unambiguous after time-weighting (e.g. a rapid card with enough games beats a smaller bullet card). Follow CLAUDE.md frontend rules: trigger has `data-testid` + `aria-label`; no `text-xs`; no magic numbers (reuse `MIN_GAMES_PER_TC_CARD`).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run EndgameMetricsByTcSection && npm run lint</automated>
  </verify>
  <done>The metrics cards are collapsible (chevron + click), the primary-TC card is expanded by default and others collapsed, opening one does not collapse another, and changing filters resets to the recomputed primary. EndgameMetricsByTcSection tests pass and lint is clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Default the Endgame ELO Timeline to the primary TC across both platforms</name>
  <files>frontend/src/components/charts/EndgameEloTimelineSection.tsx, frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx</files>
  <behavior>
    - On first render, only series whose `time_control` equals the primary TC are visible; all other combos start hidden (legend item dimmed + line-through, `aria-pressed="false"`).
    - The primary TC is chosen via the shared `computePrimaryTc` heuristic, summing `per_week_total_games` across BOTH platforms per time control (so bullet's per-game volume edge stays neutralized via NOMINAL_DURATION weighting).
    - When the primary TC was played on both chess.com and lichess, BOTH combo series for that TC are visible by default.
    - User legend toggles within a single dataset are still preserved; a new combo set (filter change / new data) resets the default to the recomputed primary TC.
    - Legend toggling, tooltip, gradient-uniqueness, and per-combo testid behavior are otherwise unchanged.
  </behavior>
  <action>
    Replace the visibility seeding logic in `EndgameEloTimelineSection`. Remove (or repurpose) `computeDefaultHidden` and its `MAX_DEFAULT_VISIBLE` / `MIN_ACTIVE_WEEKS_RATIO` constants; introduce a `computeDefaultHiddenByPrimaryTc(combos)` helper that: (1) builds per-TC summed game counts as `Record<tc, [{ total }]>` where `total` = sum of `per_week_total_games` across all combos of that `time_control` (both platforms), (2) calls `computePrimaryTc(byTc, MIN_GAMES_PER_TC_CARD)` to pick the primary TC, (3) returns a `Set<string>` of `combo_key`s whose `time_control !== primaryTc` (so all combos of the primary TC across both platforms stay visible). If `computePrimaryTc` returns null (no TC clears the floor), fall back to showing nothing hidden, OR keep the previous top-1-by-games fallback — pick the simpler option and note it in the SUMMARY. Seed the existing `hiddenKeys` state and the `comboSignature`-driven reset (the "adjust state during render" block) from this new helper instead of `computeDefaultHidden`. Import `computePrimaryTc` from `@/lib/primaryTc` and `MIN_GAMES_PER_TC_CARD` from `@/generated/endgameZones`. Do not change the legend rendering, tooltip, chart series, or testids. No magic numbers — reuse `MIN_GAMES_PER_TC_CARD`.

    Update `EndgameEloTimelineSection.test.tsx`: the existing default-visibility tests assume the OLD active-weeks/top-1-by-games heuristic and must be re-baselined to the primary-TC heuristic. Update fixtures so the expected primary TC is unambiguous and adjust the "default-visible" / "default-hidden" / aria-pressed assertions accordingly. Add a test proving that when the primary TC has combos on BOTH platforms (e.g. `chess_com_rapid` + `lichess_rapid` both clearing the floor and being the time-weighted winner), both are visible by default while other-TC combos are hidden. Keep the legend-toggle, gradient-uniqueness, and tooltip tests intact (adjust only the seed fixtures if their default-visible expectations shift).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run EndgameEloTimelineSection && npm run lint</automated>
  </verify>
  <done>The timeline defaults to the primary-TC series only (both platforms when both were played), other-TC series start hidden, legend toggles still work, and filter/data changes reset the default. EndgameEloTimelineSection tests pass and lint is clean.</done>
</task>

</tasks>

<verification>
- `cd frontend && npm run lint && npm test -- --run` passes (lint + full frontend suite).
- `cd frontend && npm run build` succeeds (no TS errors; `noUncheckedIndexedAccess` satisfied on all new index accesses).
- `cd frontend && npm run knip` reports no new dead exports (e.g. if `computeDefaultHidden` is removed, its constants are removed too).
- Manual (HUMAN-UAT): On the Endgames page with multi-TC data — the metrics cards collapse/expand with a chevron, the primary-TC card is open by default and others closed, and the ELO Timeline shows only the primary TC enabled (both platforms if played on both).
</verification>

<success_criteria>
- Per-TC Endgame Metrics cards use the same Accordion primitive and visual grammar as the Endgame Type Breakdown cards.
- Primary-TC metrics card expanded by default; others collapsed; folds are independent; filter change resets to recomputed primary.
- ELO Timeline enables only the primary-TC series by default (both platforms when both were played), others hidden, with toggling and reset behavior preserved.
- All frontend tests, lint, type-check (build), and knip pass.
</success_criteria>

<output>
Create `.planning/quick/260530-pll-make-the-tc-specific-endgame-metrics-car/260530-pll-SUMMARY.md` when done.
</output>
