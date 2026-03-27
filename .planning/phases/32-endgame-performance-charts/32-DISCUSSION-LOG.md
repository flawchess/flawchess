# Phase 32: Endgame Performance Charts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 32-endgame-performance-charts
**Areas discussed:** Chart placement & layout, Strength gauge design, Timeline chart behavior, Backend data model, Conversion/Recovery chart

---

## Chart Placement & Layout

| Option | Description | Selected |
|--------|-------------|----------|
| New section on Statistics tab | Add 'Endgame Performance' section on existing Statistics sub-tab | ✓ |
| New 'Performance' sub-tab | Third sub-tab on Endgames page | |
| New top-level page | Dedicated /endgames/performance route | |

**User's choice:** New section on existing Statistics tab
**Notes:** Keeps everything in one scrollable view

---

| Option | Description | Selected |
|--------|-------------|----------|
| Side-by-side WDL bars | Two horizontal stacked WDL bars (endgame vs non-endgame) | ✓ |
| Grouped bar chart | Recharts grouped BarChart with W/D/L clusters | |
| Single bar with toggle | One WDL bar toggling between views | |

**User's choice:** Side-by-side WDL bars

---

| Option | Description | Selected |
|--------|-------------|----------|
| Above Results by Endgame Type | Overview first, then detail | ✓ |
| Below Results by Endgame Type | Familiar content first | |

**User's choice:** Above — top-down overview to detail

---

| Option | Description | Selected |
|--------|-------------|----------|
| Below both sections | Timelines at the bottom | ✓ |
| Inside Endgame Performance section | Bundled with WDL and gauge | |

**User's choice:** Below both sections

---

## Strength Gauge Design

Initial discussion about what metric to use. User raised concern that raw endgame vs non-endgame win rate comparison is misleading since non-endgame games are inflated by middlegame blunders. Three alternatives discussed:

1. Ratio to overall win rate (endgame_win_rate / overall_win_rate)
2. Conversion/Recovery composite score
3. Hybrid of both

**User's decision:** Implement BOTH as separate gauge charts.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Semicircle gauges | Two radial gauges side by side | ✓ |
| Horizontal bar gauges | Progress-bar style with labeled ranges | |
| You decide | Claude picks | |

**User's choice:** Semicircle gauges

---

| Option | Description | Selected |
|--------|-------------|----------|
| Weighted average (0.6 conv + 0.4 recov) | Conversion weighted higher as more impactful | ✓ |
| Simple average | Equal weight | |
| Show both separately | No composite, separate gauges | |

**User's choice:** Weighted average (60/40 split)

---

## Timeline Chart Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Game index | X-axis is game number, evenly spaced | |
| Date-based | X-axis is calendar date, uneven spacing | ✓ |
| You decide | Claude picks | |

**User's choice:** Date-based X-axis

---

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-line single chart | One chart with colored lines per type | ✓ |
| Small multiples | Separate mini-chart per type | |
| Tabs per type | Dropdown to switch types | |

**User's choice:** Multi-line single chart

---

| Option | Description | Selected |
|--------|-------------|----------|
| Use available games | Compute with whatever games exist, start from game 1 | ✓ |
| Hide the line | Don't render for < 50 games | |
| Show but dim/dashed | Visual cue for low confidence | |

**User's choice:** Use available games

---

| Option | Description | Selected |
|--------|-------------|----------|
| Separate chart above | Two distinct charts stacked | ✓ (modified) |
| Combined into one chart | All-endgames as bold line in per-type chart | |

**User's choice:** Separate chart above, but with TWO lines — endgame win rate and non-endgame win rate — not just one.

---

## Backend Data Model

| Option | Description | Selected |
|--------|-------------|----------|
| Backend aggregation | Pre-computed rolling series from database | ✓ |
| Frontend aggregation | Raw per-game data, JS computes window | |
| Hybrid | Backend returns limited raw data, frontend windows | |

**User's choice:** Backend aggregation

---

| Option | Description | Selected |
|--------|-------------|----------|
| Two new endpoints | /performance and /timeline | ✓ |
| One combined endpoint | Single response with everything | |
| Extend existing endpoint | Add to /stats | |

**User's choice:** Two new endpoints

---

## Conversion/Recovery Bar Chart (Added)

User requested an additional grouped vertical bar chart showing Conversion % and Recovery % side by side per endgame type. Uses existing data from stats endpoint.

| Option | Description | Selected |
|--------|-------------|----------|
| Between gauge and per-type | Groups comparative charts together | |
| Below Results by Endgame Type | Keeps existing chart position | ✓ |
| You decide | Claude picks | |

**User's choice:** Below Results by Endgame Type

---

## Claude's Discretion

- Semicircle gauge implementation approach
- Gauge color scheme and scale ranges
- Per-type timeline line colors
- Empty state design
- Mobile layout adaptation
- SQL windowing strategy

## Deferred Ideas

None
