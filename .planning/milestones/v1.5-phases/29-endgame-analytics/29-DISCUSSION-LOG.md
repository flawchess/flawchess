# Phase 29: Endgame Analytics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 29-endgame-analytics
**Areas discussed:** Tab layout & structure, Endgame categories, Conversion/recovery display, Navigation & routing

---

## Tab Layout & Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Two-section page | Top: endgame W/D/L, Bottom: conversion/recovery. Shared filters. | |
| Tabbed sub-pages | Sub-tabs within Endgames page: Statistics and Games. Shared filters. Mirrors Openings pattern. | |
| Single unified view | All stats in one scrollable page. | |

**User's choice:** Tabbed sub-pages (user clarified before options were presented — preferred consistency with Openings page pattern)
**Notes:** User specified: Statistics sub-tab with WDL charts per endgame category, Games sub-tab working same as Openings Games tab. Filter sidebar on left but no chessboard. Some filters reused from Openings, but not all.

### Filters

| Option | Description | Selected |
|--------|-------------|----------|
| Time Control | Bullet/Blitz/Rapid/Classical toggle | |
| Color | White/Black/Both | |
| Platform | Chess.com/Lichess filter | |
| Recency | Last 3/6/12 months or all time | |

**User's choice:** Time Control, Platform, Recency. Plus "More filters" section with Rated and Opponent Type.
**Notes:** User initially questioned color filter relevance for endgames. After discussion, agreed to drop it — player color (white/black) is less relevant for endgame performance than for opening performance. Claude initially argued for keeping it but conflated player color with whose move it is; user correctly pointed this out.

### Games Sub-Tab

| Option | Description | Selected |
|--------|-------------|----------|
| Click category to filter | User clicks endgame category in Statistics, selection persists to Games tab | |
| Category dropdown in Games tab | Independent dropdown selector in Games tab | |
| All endgame games | Always shows all endgame games regardless of category | |

**User's choice:** Click category to filter
**Notes:** None

---

## Endgame Categories

| Option | Description | Selected |
|--------|-------------|----------|
| WDL bar per category | Horizontal WDL bars per category row, sorted by game count | |
| Card grid | 6 cards in 2x3 or 3x2 grid with compact WDL | |
| Data table | Traditional sortable table with Win%/Draw%/Loss% columns | |

**User's choice:** WDL bar per category — but specifically requested it use the same chart type as the "Results by Opening" WDLBarChart (stacked bars with game count outline bar)
**Notes:** User asked about whether 6 coarse categories are sufficient vs Wikipedia's finer-grained endgame types. Agreed that 6 categories are a good starting point since material_signature already supports finer drill-down in future (MATFLT-01).

### Sort Order

| Option | Description | Selected |
|--------|-------------|----------|
| By game count | Most played endgame type first | |
| Fixed order | Always same order regardless of distribution | |
| By win rate | Best-performing first | |

**User's choice:** By game count
**Notes:** None

### Category Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| All always visible | All 6 categories shown; selection only affects Games tab | |
| Drill-down mode | Clicking expands one category, collapses others | |

**User's choice:** All always visible
**Notes:** None

---

## Conversion/Recovery Display

| Option | Description | Selected |
|--------|-------------|----------|
| Two grouped bar charts by game phase | Conversion and recovery each broken down by opening/middlegame/endgame | |
| Per endgame type inline | Conversion and recovery shown inline below each endgame category's WDL bar | |

**User's choice:** Per endgame type inline
**Notes:** User initially questioned whether conversion/recovery belongs in Endgames tab or Global Stats, and whether game phase breakdown makes sense. Claude agreed game phase breakdown adds complexity without insight. User then proposed a better framing: conversion/recovery per endgame type (e.g., "when I enter a rook endgame ahead, how often do I convert?"). This uses material imbalance at the endgame transition point. Both agreed this is more actionable than game phase breakdown.

### Display Style

| Option | Description | Selected |
|--------|-------------|----------|
| Inline below each category row | Compact metrics below each WDL bar | |
| Separate section below chart | Two visual sections on the page | |
| Claude decides | Claude picks layout during implementation | |

**User's choice:** Inline below each category row
**Notes:** Format: "Conversion: X% (n/m)" and "Recovery: Y% (n/m)" below each bar

---

## Navigation & Routing

| Option | Description | Selected |
|--------|-------------|----------|
| After Openings | Import, Openings, Endgames, Statistics (4 nav items) | |
| Under Statistics | Sub-section within Global Stats page | |

**User's choice:** After Openings
**Notes:** None

### Route Path

| Option | Description | Selected |
|--------|-------------|----------|
| /endgames/* | Top-level with /endgames/statistics and /endgames/games | |
| /endgame-stats/* | More descriptive but longer | |

**User's choice:** /endgames/*
**Notes:** Mirrors /openings/* pattern

---

## Claude's Discretion

- Endgame class derivation logic (SQL vs Python)
- Game phase thresholds
- Generic vs specific WDL chart component
- Empty state design
- Mobile layout for inline conversion/recovery metrics
- Endgame transition point detection

## Deferred Ideas

- MATFLT-01: Material signature drill-down within endgame categories
- Aggregate conversion/recovery on Global Stats page
