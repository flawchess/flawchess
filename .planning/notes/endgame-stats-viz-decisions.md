---
title: Endgame Stats viz refinement decisions
date: 2026-05-18
context: gsd-explore session — reviewed all charts on /endgames/stats for visual-representation and chart-type quality; resolved four threads
---

# Endgame Stats Visualization — Decisions

Four threads were explored after a full visual review of `/endgames/stats`. Decisions and rationale below so a future planner does not relitigate.

## 1 & 7. Gauges (Conversion / Parity / Recovery + per-type grid)

**Decision: keep gauges for now.** Capture a forward-looking seed to replace them with bullet charts later (see [[../seeds/SEED-021-gauges-to-bullet-charts]]).

Rationale:
- Gauges are an inferior statistical encoding: no CI, no hypothesis test, low data-ink, poor for cross-comparison, and they redundantly print the number they draw.
- But the "can't compare gauges" critique is **weakest exactly where they are used as headliners**: Conversion / Parity / Recovery are *not commensurable* (different denominators and meaning), so nobody reads them against each other. The salience + visual-variety argument legitimately holds there.
- The critique is **strongest in the Endgame Type Breakdown** (same metric repeated across 5 types — comparison is the whole point — rendered as 10 tiny needles).
- Net: not worth churning now; revisit as a single encoding refactor (ideally bundled with the colour-blind-mode work, which touches the same components). Bullet bars with a CI whisker + significance marker, sized/positioned for headline emphasis, are the eventual target.

## 2. Non-linear time axis on the "over time" charts

**Decision: keep the ordinal-by-activity x-axis; add visible, mobile-sized inactivity-gap annotations.** (In scope for the inserted phase.)

Rationale:
- A true calendar scale would burn most of the chart width on whitespace for players with long inactive stretches (this account has >3y of inactivity inside a ~5y span) and lose the resolution that makes the chart worth showing.
- Honesty fix without losing resolution: an axis-break glyph (standard zigzag / double-slash convention) at each inactivity gap, plus a compact label like "≈3.1y inactive". Must be small enough to read and not crowd the axis on mobile.

## 3. ELO Timeline series overload (2 platforms × 4 TCs = 8 combos)

**Decision: default to the most-active series only; user can toggle the rest. No tabs for now.**

Rationale:
- Series are already toggleable. Tabs (per-platform or per-combo) were considered — per-platform would also help the y-axis-compression problem (chess.com vs lichess scales differ) — but deemed unnecessary complexity for now. Defaulting to the single most-active series + toggle is enough.

## 6. "Endgame Overall Performance" flow-diagram layout

**Decision: replace the arrow-flow + empty flanking boxes with one responsive 2-column card.**

Layout:
- One bordered card. Desktop: two columns separated by a vertical divider. Mobile: stacked with horizontal dividers.
- **Column 1:** "Games without Endgame" / "Games with Endgame" — stacked, divider-separated sections.
- **Column 2:** "Eval at Endgame Entry" / "Endgame Score Differences" — stacked, divider-separated sections.
- Both columns then carry exactly 2 section titles and 4 charts → equal height by construction (this specific arrangement was chosen precisely to balance heights; the earlier "game-based vs eval-based" split produced two uneven cards that worked on mobile but not desktop).
- Drop the arrow metaphor and the empty black flanking boxes entirely — they add cognitive load and read as broken content.

Status: design decided here; destination (own phase vs Phase 89 Polish vs todo) TBD at crystallization.

## Settled without change

- **Time Pressure "Average Clock Gap over Time"** chart: current solution is fine, no change.
- **Colour-blind mode** (heavy red/green semantic load across WDL bars, zone bands, gauges): real concern, acknowledged, but out of scope for now — already on the user's separate to-do list.
