# Phase 34: Theme Improvements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 34-theme-improvements
**Areas discussed:** Container styling, Filter button layout, Chart consistency, Subtab highlighting, Navigation header, Collapsible sections

---

## Container Styling

### Where to apply charcoal containers?

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar + main content | Both panels get charcoal containers | |
| Main content only | Only main content area gets containers | |
| Per-section cards | Individual sections get their own charcoal cards | |

**User's choice:** Custom — charcoal card containers on specific sections: endgame statistics sections, concept accordion, game cards, bookmark cards, subtab navigation, import page cards. Sidebar uses flat `#171513` background instead.
**Notes:** Sidebar doesn't get a card container, just a different background color.

### Implementation approach?

| Option | Description | Selected |
|--------|-------------|----------|
| CSS variable + utility class | Define in @theme inline, use as Tailwind utility | ✓ |
| Reusable component | Create a <CharcoalCard> wrapper | |
| You decide | Claude picks | |

**User's choice:** CSS variable + utility class

### Sidebar container?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, charcoal sidebar | Charcoal background on sidebar | |
| Keep sidebar as-is | Sidebar stays current | |

**User's choice:** Custom — sidebar uses `#171513` (dark brown) flat background, no card container

---

## Filter Button Layout

### Horizontal layout approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Equal-width grid | CSS grid with equal columns | |
| Flex with grow | Flex-wrap with flex-grow | |
| You decide | Claude picks best approach | ✓ |

**User's choice:** You decide

### Unify filter patterns?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, unify all | One consistent component pattern | |
| Keep separate | Leave two patterns, fix spacing only | ✓ |
| You decide | Claude judges effort | |

**User's choice:** Keep separate — just fix spacing

---

## Chart Consistency

### Corner style?

| Option | Description | Selected |
|--------|-------------|----------|
| Rounded everywhere | Match custom WDL bar style | ✓ |
| Square everywhere | Sharp corners on all WDL charts | |
| You decide | Claude picks | |

**User's choice:** Rounded everywhere

### Glass overlay on Recharts?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add glass overlay | Apply glass effect to Recharts bars | |
| No, colors only | Just corners and colors | ✓ |
| You decide | Claude judges feasibility | |

**User's choice:** No, colors only

---

## Subtab Highlighting

### Active tab style?

| Option | Description | Selected |
|--------|-------------|----------|
| Brand brown accent | #8B5E3C background or border | ✓ |
| Charcoal with highlight | Charcoal bg + colored border | |
| You decide | Claude picks | |

**User's choice:** Brand brown accent

### Background or underline?

| Option | Description | Selected |
|--------|-------------|----------|
| Background fill | Brand brown fill, white text | ✓ |
| Bottom border accent | Thin brown line under tab | |
| You decide | Claude picks | |

**User's choice:** Background fill

---

## Navigation Header

**User's choice:** (Provided directly, no options presented)
- Active main nav tab: lighter background spanning full header height
- Remove white border from header
- Logo + "FlawChess" text both link to homepage

---

## Collapsible Sections

### Header styling?

| Option | Description | Selected |
|--------|-------------|----------|
| Charcoal background | Match new container style, consistent everywhere | ✓ |
| Muted with border | Standardize on bg-muted/50 + border pattern | |
| You decide | Claude picks | |

**User's choice:** Charcoal background — entire collapsible (header + content) is one charcoal container with own padding

---

## Claude's Discretion

- Filter button layout approach (grid vs flex-grow)
- WDL bar height normalization (h-5 vs h-6)
- Exact charcoal color value

## Deferred Ideas

None
