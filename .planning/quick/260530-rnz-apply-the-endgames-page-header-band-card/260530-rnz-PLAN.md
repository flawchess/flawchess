---
phase: quick-260530-rnz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/GlobalStatsCharts.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/components/charts/PositionResultsPanel.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/stats/OpeningStatsSection.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/pages/openings/StatsTab.tsx
  - frontend/src/components/charts/ScoreChart.tsx
autonomous: true
requirements: [QUICK-260530-rnz]

must_haves:
  truths:
    - "Overview page renders Chess.com Rating, Lichess Rating, Results by Time Control, and Results by Color each as its own card with a full-bleed header band (bg-black/20 + bottom separator)."
    - "Results by Color is a standalone card, no longer sharing a wrapper with Results by Time Control."
    - "The 'Results played as White/Black' card shows its label in a full-bleed header band on both the Openings Moves and Games subtabs."
    - "Openings Stats accent cards (OpeningStatsCard) and Insights accent cards (OpeningFindingCard) show the opening name in a full-bleed header band; the colored left border is applied to the content area only, not the header band."
    - "The 'Bookmarked Openings: Score over Time' card shows its title in a full-bleed header band."
    - "No card gains Accordion/chevron/expand-collapse behavior — the header bands are static (the existing 'show more' toggles on stats/insights sections are untouched)."
  artifacts:
    - path: frontend/src/components/stats/GlobalStatsCharts.tsx
      provides: "Per-card header bands for Results by Time Control and Results by Color, each as a standalone bordered card."
      contains: "bg-black/20 border-b border-border/40"
    - path: frontend/src/components/charts/PositionResultsPanel.tsx
      provides: "Header-band label for the position-results card."
      contains: "bg-black/20 border-b border-border/40"
    - path: frontend/src/components/stats/OpeningStatsCard.tsx
      provides: "Header-band opening name with left border on content only."
      contains: "bg-black/20 border-b border-border/40"
    - path: frontend/src/components/insights/OpeningFindingCard.tsx
      provides: "Header-band opening name with left border on content only."
      contains: "bg-black/20 border-b border-border/40"
    - path: frontend/src/components/charts/ScoreChart.tsx
      provides: "Header-band title for the Score over Time chart."
      contains: "bg-black/20 border-b border-border/40"
  key_links:
    - from: "frontend/src/components/charts/PositionResultsPanel.tsx"
      to: "ExplorerTab + GamesTab"
      via: "shared component used by both Openings subtabs"
      pattern: "PositionResultsPanel"
---

<objective>
Apply the Endgames-page header-band card STYLE (recessed full-bleed `<h3>`
header with `bg-black/20 border-b border-border/40 px-4 py-3 text-base
font-semibold`, content below in a padded div) to a set of cards across the
Overview, Openings (Moves/Games/Stats/Insights), and Bookmarks surfaces.

Purpose: visual consistency with the Endgames page, which already uses this
header-band grammar on every card (EndgameScoreOverTimeChart,
EndgameOverallCard, EndgameMetricsByTcCard, etc.).

Output: header bands on the targeted cards. STYLE ONLY — no Accordion,
chevron, expand/collapse, behavior, data, or API changes.

This is frontend-only and mechanically repetitive: the same structural-styling
transform applied per card. Grouped into 3 tasks by surface, each with its own
atomic commit.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

# THE canonical reference for the header-band pattern (see lines 144-170):
@frontend/src/components/charts/EndgameScoreOverTimeChart.tsx

# Additional in-repo examples of the same band (all plain inline Tailwind, no shared constant):
@frontend/src/components/charts/EndgameOverallCard.tsx
</context>

<pattern_reference>
The canonical band (verbatim classes — copy exactly, do NOT introduce a new
constant; the codebase repeats these inline by convention):

```
className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold"
```

Transform shape for a card that today is:
  <div class="charcoal-texture rounded-md p-4">  <!-- padded wrapper -->
    <h2 class="text-lg font-medium mb-3">Title <InfoPopover/></h2>
    ...body...
  </div>

becomes:
  <div class="charcoal-texture rounded-md overflow-hidden">  <!-- NO p-4; overflow-hidden so the band respects rounded corners -->
    <h3 class="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold" data-testid="...">
      Title <InfoPopover/>
    </h3>
    <div class="p-4">...body...</div>
  </div>

Rules that apply to EVERY card in this plan:
- The outer card wrapper must NOT pad around the header band: remove `p-4`
  (or equivalent) from the wrapper and move it to the content `<div className="p-4">`.
- Add `overflow-hidden` to the rounded wrapper so the band's `bg-black/20`
  does not spill past the rounded top corners.
- The heading element keeps a `data-testid` (the reference uses
  `data-testid="endgame-score-timeline-header"`). Use a `*-header` testid.
- Keep `text-base font-semibold` (NOT smaller — text-sm is the floor and
  this is above it).
- Any existing InfoPopover/icon in the title moves INTO the header band
  (the `flex items-center gap-2` already accommodates it).
- Do NOT add Accordion, AccordionTrigger, ChevronDown/Up, or any
  expand/collapse to these header bands. Static heading only.
- "Apply changes to mobile too": for components with separate desktop/mobile
  render branches, the band must appear in both. Search for duplicated markup
  before declaring a card done.
</pattern_reference>

<tasks>

<task type="auto">
  <name>Task 1: Overview cards + Results-by-Color split + position-results card</name>
  <files>frontend/src/components/stats/GlobalStatsCharts.tsx, frontend/src/pages/GlobalStats.tsx, frontend/src/components/charts/PositionResultsPanel.tsx</files>
  <action>
Apply the header-band pattern to the Overview page cards and the shared
position-results card.

GlobalStats.tsx — three card wrappers currently use `charcoal-texture
rounded-md p-4`:
  1. "Chess.com Rating" section (the inner `<section>` has an `<h2 class="text-lg
     font-medium">`). Convert: drop `p-4` from the outer wrapper, add
     `overflow-hidden`; replace the inner `<h2>` with the header-band `<h3>`
     carrying the title + its InfoPopover and `data-testid="rating-chess-com-header"`;
     wrap the RatingChart in `<div class="p-4">`. Keep the `<section
     data-testid="rating-section-chess-com">` element and its existing testid,
     but it no longer needs `space-y-3` around a separate heading — restructure
     so the band is flush to the top and the chart sits in the padded content div.
  2. "Lichess Rating" section — identical transform, `data-testid="rating-lichess-header"`.
  3. The WDL charts wrapper (`<GlobalStatsCharts .../>` inside a `charcoal-texture
     rounded-md p-4`). This wrapper currently holds BOTH WDL category charts. Per
     the task, Results by Color must become its OWN card. So in GlobalStats.tsx,
     remove this single shared wrapper and instead render GlobalStatsCharts'
     output as two independent cards (see GlobalStatsCharts.tsx change below);
     the simplest clean approach is to move the card-wrapping responsibility INTO
     GlobalStatsCharts so each WDLCategoryChart renders its own headered card, and
     have GlobalStats.tsx render `<GlobalStatsCharts .../>` directly (no outer
     `charcoal-texture` wrapper). Keep the outer `space-y-6` rhythm intact.

GlobalStatsCharts.tsx — currently `ChartTitle` renders `<h2 class="text-lg
font-medium mb-3">` and `WDLCategoryChart` returns a bare `<div>` (no card
shell). Restructure so each `WDLCategoryChart` (including its empty-data branch)
renders a standalone card: outer `<div class="charcoal-texture rounded-md
overflow-hidden">`, a header-band `<h3>` (replacing ChartTitle's `<h2>`) with the
title + InfoPopover and `data-testid="{testId}-header"`, then the WDL rows / "No
data available." inside a `<div class="p-4">`. Result: "Results by Time Control"
and "Results by Color" are now two separate headered cards. Wrap the two cards in
the existing `space-y-8` (or use `space-y-6` to match the page rhythm —
keep `space-y-8` unless it looks visually off, this is style-preserving). Keep
all existing `testId`s on the WDL row containers and the `-info` popover testids
unchanged.

Note `ChartTitle` may become unused after this change — if so, inline its
content into the band and remove the now-dead `ChartTitle` function so knip stays
green (knip runs in CI and fails on dead exports/locals).

PositionResultsPanel.tsx — the card root is `charcoal-texture rounded-md p-4
${className}` and the label renders as `<div class="text-sm font-medium
mb-2">{label}</div>`. Convert to the header band: drop `p-4` from the root, add
`overflow-hidden`; replace the label div with the header-band `<h3>` rendering
`{label}` and `data-testid="wdl-moves-position-header"`; wrap the three-row grid
in `<div class="p-4">`. NOTE: `label` is a ReactNode (the `positionResultsLabel`
JSX with the color square), so the band must accommodate inline flex content —
`flex items-center gap-2` already does. The `className` prop passed by callers
includes layout/order classes (`order-2 lg:order-1`, `charcoal-texture rounded-md
p-4`) — GamesTab passes `className="charcoal-texture rounded-md p-4"` and
ExplorerTab passes `className="order-2 lg:order-1"` while the component default is
`order-2 lg:order-1`. Reconcile: the component itself owns the `charcoal-texture
rounded-md overflow-hidden` shell, and callers should pass ONLY ordering classes.
Update GamesTab.tsx's PositionResultsPanel `className` to drop the now-duplicated
`charcoal-texture rounded-md p-4` (leave any ordering it needs, or empty). This
card is shared by both the Moves (ExplorerTab) and Games (GamesTab) subtabs, so
this single change covers both occurrences of the "Results played as" card.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && npm run lint && npm test -- --run src/components/stats/__tests__/OpeningStatsCard.test.tsx src/components/insights/OpeningInsightsBlock.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <done>
Overview shows 4 standalone headered cards (Chess.com Rating, Lichess Rating,
Results by Time Control, Results by Color). PositionResultsPanel renders its
label in a header band on both Moves and Games subtabs. `npx tsc --noEmit` and
`npm run lint` pass; no duplicated `charcoal-texture rounded-md p-4` left on the
PositionResultsPanel callers.
  </done>
</task>

<task type="auto">
  <name>Task 2: Openings Stats + Insights accent cards (left border on content only) + Score over Time</name>
  <files>frontend/src/components/stats/OpeningStatsCard.tsx, frontend/src/components/insights/OpeningFindingCard.tsx, frontend/src/pages/openings/StatsTab.tsx, frontend/src/components/charts/ScoreChart.tsx</files>
  <action>
Apply the header band to the left-border accent cards and the Score-over-Time
card.

OpeningStatsCard.tsx and OpeningFindingCard.tsx share an IDENTICAL card shell:
  <div data-testid={cardTestId} class="block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-4" style={cardStyle}>
    {headerLine}      <!-- opening display_name -->
    <div ...mobile block...>
    <div ...desktop block...>
  </div>
where `cardStyle` sets `borderLeftColor` (the score-zone accent) + optional
opacity. The NUANCE: the colored left border must apply to the CONTENT area
only, NOT the header band. Restructure each card to:
  <div data-testid={cardTestId} class="relative charcoal-texture border border-border/20 rounded overflow-hidden" style={mutingOpacityOnly}>
    <h3 class="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold" data-testid={`${cardTestId}-header`}>
      {headerLine content}   <!-- the opening name + ECO; reuse the existing inline markup -->
    </h3>
    <div class="border-l-4 px-4 py-4" style={{ borderLeftColor }}>
      ...mobile block...
      ...desktop block...
    </div>
  </div>
Key points:
  - Move `border-l-4` and the `borderLeftColor` style off the card root and onto
    the inner content `<div>`. The header band thus stays full-width / un-accented;
    the colored accent runs only down the content area.
  - The card root keeps `overflow-hidden` (so the band + the content's left
    border respect the rounded corners) and keeps the opacity muting (`isCardMuted`
    / `isUnreliable`) — split `cardStyle` so opacity stays on the root and
    `borderLeftColor` moves to the content div.
  - `headerLine` is currently `<div class="flex items-center gap-2 text-sm
    min-w-0"><span class="truncate ...">{display_name}...</span></div>`. Fold its
    inner `<span>` content into the header-band `<h3>` (the band already has `flex
    items-center gap-2`). Keep the `truncate min-w-0` on the name span so long
    names still ellipsize. The name was `text-sm`; inside the band it inherits
    `text-base font-semibold` — that is intentional (above the text-sm floor) and
    matches the band grammar.
  - Remove the now-unused `headerLine` local if you inline it; or keep it but
    have it render the band — pick whichever keeps the file clean and knip-green.
  - CRITICAL — preserve existing test contracts: the card root must keep
    `data-testid={cardTestId}` AND keep `style.opacity` set to UNRELIABLE_OPACITY
    when muted (OpeningStatsCard.test.tsx asserts `card.style.opacity` on the
    `[data-testid="opening-stats-card-N"]` ROOT). The border-left-color tests
    (S1a/S1b/S1c) assert `card.style.borderLeftColor` on that SAME root element —
    these tests WILL need updating since the border now lives on the inner content
    div. Update OpeningStatsCard.test.tsx: change the S1a/S1b/S1c assertions to
    query the inner content div for `borderLeftColor` (give the content div a
    stable selector, e.g. `data-testid={`${cardTestId}-content`}`, and update the
    three tests to read `borderLeftColor` from `${cardTestId}-content` while the
    opacity tests keep reading from the root). Also keep the S6 test passing
    (`.sm\:hidden` and `.hidden.sm\:flex` blocks must still exist inside the card).
  - Apply the SAME structural change to OpeningFindingCard.tsx (identical shell).
    There is no dedicated OpeningFindingCard.test.tsx asserting border placement,
    but OpeningInsightsBlock.test.tsx renders these cards — run it and fix any
    fallout.

StatsTab.tsx — the "Score over Time" card is `<div class="charcoal-texture
rounded-md p-4"><ScoreChart .../></div>`. The header band belongs to the
ScoreChart title, so handle it in ScoreChart.tsx (below) and adjust this wrapper:
drop `p-4`, add `overflow-hidden`, and since ScoreChart now owns its own band +
padded body, the wrapper is just `charcoal-texture rounded-md overflow-hidden`.
Leave the sibling loading/error wrappers (`mpo-loading`, `mpo-error`, "Loading
chart data...") AS-IS — those are status placeholders, not titled cards, and out
of scope.

ScoreChart.tsx — replace the `<h2 class="text-lg font-medium mb-3">` (with the
BookMarked icon + "Bookmarked Openings: Score over Time" + InfoPopover) with the
header-band `<h3>` carrying `data-testid="score-chart-header"`, and wrap the chart
(the `isMobile ? '' : 'flex items-stretch'` block) in a `<div class="p-4">`. Keep
the BookMarked icon and the existing `score-chart-info` InfoPopover inside the
band. The empty-state early return (`<div class="text-center text-muted-foreground
py-8">No game history...`) can keep its own minimal padding — but since the
wrapper no longer has `p-4`, give that empty-state branch a `p-4` so it isn't
flush to the edges.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && npm run lint && npm test -- --run src/components/stats/__tests__/OpeningStatsCard.test.tsx src/components/insights/OpeningInsightsBlock.test.tsx 2>&1 | tail -25</automated>
  </verify>
  <done>
OpeningStatsCard and OpeningFindingCard render the opening name in a full-bleed
header band, with the colored left border on the content div only (header band
un-accented). OpeningStatsCard.test.tsx border-left tests updated to read from
the content div; opacity tests still read from the root and pass. Score over Time
card shows its title in a header band. `npx tsc --noEmit`, `npm run lint`, and
the two test files pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify full frontend gate + fix any remaining test/knip fallout</name>
  <files>frontend/src/components/stats/OpeningStatsCard.tsx, frontend/src/components/insights/OpeningInsightsBlock.tsx, frontend/src/components/stats/OpeningStatsSection.tsx</files>
  <action>
Run the complete pre-PR frontend gate and resolve anything the per-task verifies
did not catch.

1. Run `cd frontend && npm run lint && npm test -- --run && npm run knip`.
2. knip: if folding `headerLine`/`ChartTitle` into bands left any unused local,
   import, or export, remove it. Common suspects: the `ChartTitle` function in
   GlobalStatsCharts.tsx (Task 1), an unused `headerLine` const in the two accent
   cards (Task 2), or a now-unused `ChevronDown`/`ChevronUp` import IF (and only
   if) you touched a section component — note the existing "show N more" toggles
   in OpeningStatsSection.tsx and OpeningInsightsBlock.tsx are OUT OF SCOPE and
   must NOT be removed; their chevrons stay.
3. Confirm the section-level headings are correctly scoped: OpeningStatsSection's
   `<h2>` and OpeningInsightsBlock's FindingsSection `<h3>` are SECTION titles
   ABOVE a grid of cards — they are NOT card header bands and must stay as plain
   headings (do not band them). The header bands in this plan are on the
   individual cards/charts, not the section headers. Verify the
   OpeningInsightsBlock.test.tsx assertion "does not render a block-level Opening
   Insights h2 (D-18)" and "renders an InfoPopover trigger on each of the four
   section headers" both still pass.
4. Visually reason about the band consistency: every card touched now matches the
   EndgameScoreOverTimeChart grammar (recessed band, separator, padded body, no
   chevron). No card gained collapse behavior.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run && npm run knip 2>&1 | tail -30</automated>
  </verify>
  <done>
`npm run lint`, `npm test -- --run`, and `npm run knip` all pass with zero
errors. No dead exports/locals introduced. Section headings remain plain (not
banded); only individual cards/charts gained header bands. Existing
expand/collapse toggles untouched.
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npm run lint && npm test -- --run && npm run knip` all green.
- Grep confirms the band appears on each targeted file:
  `grep -rl "bg-black/20 border-b border-border/40" frontend/src/components/stats/GlobalStatsCharts.tsx frontend/src/components/charts/PositionResultsPanel.tsx frontend/src/components/stats/OpeningStatsCard.tsx frontend/src/components/insights/OpeningFindingCard.tsx frontend/src/components/charts/ScoreChart.tsx`
  returns all five files.
- No `Accordion`, `AccordionTrigger`, or new `Chevron` import was added to any
  card touched (the header bands are static).
- Manual/human UAT (out of this plan's automated scope): open Overview, Openings
  Moves/Games/Stats/Insights, and Bookmarks; confirm bands render flush to rounded
  corners with no spill, on both desktop and mobile widths, and the left-border
  accent on Stats/Insights cards runs only down the content area.
</verification>

<success_criteria>
- All 5 surfaces (Overview cards incl. split Results-by-Color, "Results played
  as" card on both Openings subtabs, Openings Stats accent cards, Score over Time,
  Openings Insights accent cards) use the header-band style.
- Left-border accent on Stats/Insights cards is on the content area, not the band.
- STYLE-ONLY: no behavior/data/API change; no collapse behavior added.
- Pre-PR frontend gate (lint + test + knip) passes.
- Each task committed atomically with a `style(...)`-prefixed message.
</success_criteria>

<output>
Create `.planning/quick/260530-rnz-apply-the-endgames-page-header-band-card/260530-rnz-SUMMARY.md` when done.
</output>
