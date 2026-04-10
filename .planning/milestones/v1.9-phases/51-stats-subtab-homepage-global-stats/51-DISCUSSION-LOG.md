# Phase 51: Stats Subtab, Homepage & Global Stats - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 51-stats-subtab-homepage-global-stats
**Areas discussed:** Homepage carousel structure, Homepage mobile behavior, Stats subtab layout (STAB-01/02), Global Stats filters & label (GSTA-01/02)

---

## Pre-locked decisions (from command argument)

User invoked `/gsd-discuss-phase 51 "We can have a carousel without auto-rotation. The main feature is the interactive explorer"`.

- **Carousel auto-rotation:** OFF (user locked in command arg)
- **Primary feature:** Interactive Opening Explorer (user locked in command arg)

These seeded the initial question framing around carousel variants.

---

## Homepage — initial framing (rejected)

Initial AskUserQuestion batch covered four carousel-specific questions:
1. Hero layout (split vs centered-with-carousel-below vs full-width carousel hero)
2. Slide content format (heading+image+bullets vs image-only+static bullets vs image-only)
3. Fate of existing alternating feature sections (keep / remove / compact)
4. Fate of callout pills (remove / move below carousel / move to footer)

**User rejected the batch** and pivoted: "How about dropping the carousel idea, and go with a split hero section, where the first feature (Opening Explorer) is on the right side (image on top, bullet points below)? The additional features are shown the same way as now, when scrolling down."

This pivot is the actual direction for Phase 51. The carousel is a deferred idea in CONTEXT.md.

---

## Homepage — revised direction (accepted)

### Right column content order

| Option | Description | Selected |
|--------|-------------|----------|
| Heading → image → bullets | Feature heading anchors the top, screenshot is the visual hook, bullets below expand on it. Standard top-down scan order. | ✓ |
| Image → heading → bullets | Screenshot leads, heading + bullets below. 'Show, don't tell' pattern. Less competition with left-column hero title. | |
| Image only, no heading/bullets in hero | Right column is just the screenshot. Heading/bullets stay in feature section below. | |

**User's choice:** Heading → image → bullets
**Notes:** Matches the user's pivot message ("image on top, bullet points below"); heading placement was the missing detail. Clarified by selecting the recommended option.

### Fate of existing Opening Explorer feature section below the hero

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it from the feature list below | Hero shows Opening Explorer; alternating scroll-through starts with Opening Comparison. Four features below instead of five. No duplication. | ✓ |
| Keep it duplicated below for scrolling users | Users who scroll past the hero still see the full Opening Explorer section. Some redundancy but guarantees content is seen either way. | |

**User's choice:** Remove it from the feature list below
**Notes:** Clean story over redundancy.

### Callout pills row fate

| Option | Description | Selected |
|--------|-------------|----------|
| Remove them | Pills consume above-fold space the hero needs. Content already covered by CTAs and FAQ. HOME-01 explicitly allows 'removing pills'. | ✓ |
| Keep under left column CTAs (smaller/tighter) | Pills stay as trust signals directly below Sign up / Guest buttons on the left. Compact row. | |
| Move to footer CTA section | Pills relocate to footer-CTA without eating above-fold space. | |

**User's choice:** Remove them
**Notes:** Consistent with the minimal-hero direction.

### Mobile hero behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Current centered hero, unchanged | Mobile has no fold problem — feature sections are already under the hero on small screens. HOME-01 is a desktop-only viewport issue. | ✓ |
| Same split, stacked vertically | Mobile mirrors desktop: hero then Explorer preview. Longer scroll to CTAs. | |
| Hero text only, no Explorer preview on mobile | Hero text + CTAs jump directly to feature sections. Desktop and mobile diverge. | |

**User's choice:** Current centered hero, unchanged
**Notes:** Acknowledges HOME-01 is a desktop-fold problem specifically.

---

## Stats Subtab — Bookmarked Openings: Results 2-col (STAB-01)

### Breakpoint

| Option | Description | Selected |
|--------|-------------|----------|
| lg (≥1024px) | Two columns only on larger desktops. Safer with Openings sidebar eating horizontal space. | ✓ |
| md (≥768px) | Two columns at standard desktop breakpoint. More aggressive — tight with sidebar open on tablets/small laptops. | |
| xl (≥1280px) | Two columns only on wide desktops. Very conservative. | |

**User's choice:** lg (≥1024px)

### 2-col flow direction

| Option | Description | Selected |
|--------|-------------|----------|
| Flow top-to-bottom, left column first | CSS columns-2 or grid with explicit col placement. Left column fills first, then right. Natural reading order. | ✓ |
| Alternate left/right (row-by-row) | Grid with row-flow — row 1 left, row 2 right, row 3 left, etc. | |

**User's choice:** Flow top-to-bottom, left column first

---

## Stats Subtab — Most Played Openings mobile (STAB-02)

### "Matching bookmarked style" interpretation

| Option | Description | Selected |
|--------|-------------|----------|
| Use full WDLChartRow rows (like Bookmarked Results) | Convert mobile Most Played to the same WDLChartRow component. Visual consistency at the cost of density. | ✓ |
| Keep current 3-col grid but stack row internals on mobile | MostPlayedOpeningsTable keeps its compact grid; each row stacks vertically on mobile. Denser, less change. | |
| Bigger bar + name, no games column | Mobile shows name + WDL bar, game count inlined. Compromise between density and consistency. | |

**User's choice:** Use full WDLChartRow rows

---

## Global Stats — GSTA-02 conflict resolution

Context: `/stats/global` and `/stats/rating-history` only accept `recency` + `platform` on the backend. The v1.9 milestone has "No backend API changes" in REQUIREMENTS.md Out of Scope, which blocks adding more filters.

| Option | Description | Selected |
|--------|-------------|----------|
| Narrow backend exception — add all four filter params to /stats/global & /stats/rating-history | Add time_control, rated, opponent_type, opponent_strength to both endpoints. Violates the 'no backend changes' rule narrowly but makes all filters functional. | |
| Frontend-only: add Most Played Openings section to Global Stats page | Most Played already supports all filters. New filters would affect new section only, not existing charts. Mixed-scope UX. | |
| Enable just opponent_type + opponent_strength (minimum backend change) | Add only the opponent filters to the backend. Smaller exception. Filter out bots, compare similar-rated opponents. | ✓ |
| Drop GSTA-02, defer to v1.10 | Mark blocked, move to next milestone. Phase 51 ships GSTA-01 only for Global Stats. | |

**User's choice:** Enable just opponent_type + opponent_strength (minimum backend change)
**Notes:** Minimum-blast-radius exception. Opponent filters have the most analytical value (exclude bot games, compare vs similar-strength humans). time_control and rated stay off in Phase 51 scope.

---

## Global Stats — GSTA-01 rename scope

| Option | Description | Selected |
|--------|-------------|----------|
| Nav labels + mobile page title + new h1 on the page | Change NAV_ITEMS, BOTTOM_NAV_ITEMS, ROUTE_TITLES, add new h1 to GlobalStats.tsx. Update nav-stats testids → nav-global-stats. | ✓ |
| Nav labels + mobile page title only (no new h1) | Minimal touch — fewer files changed. Section headings carry the page. | |
| Full rename including testids and route (breaking change) | Also rename URL route, requires redirect. Most thorough but breaks bookmarks. | |

**User's choice:** Nav labels + mobile page title + new h1 on the page
**Notes:** Route /global-stats stays unchanged — no breaking URL change.

---

## Claude's Discretion

Areas where exact implementation choices were deferred to Claude:

- Homepage left column sizing (mascot logo size, title/subtitle font sizes, padding, button sizes for the narrower desktop split column)
- Homepage right column image framing (border/shadow/rounded)
- Homepage column ratio (1fr_1fr vs 2fr_3fr vs 3fr_2fr)
- Homepage mobile Opening Explorer fallback (whether to keep the Opening Explorer feature section visible on mobile-only after removing it from the alternating sections)
- Stats 2-col technique (CSS columns-2 with break-inside: avoid vs explicit grid row placement)
- Stats 2-col odd-row balancing
- Most Played mobile branching technique (viewport branch at call site vs mobileMode prop on MostPlayedOpeningsTable)
- Most Played mobile MinimapPopover handling (keep, drop, or wire to tap)
- Global Stats h1 styling (font size/weight/margin)
- Global Stats h1 placement relative to sticky mobile filter button
- Behavior-change documentation for the opponent_type='human' default on Global Stats (today it includes bot games)

## Deferred Ideas

- Homepage carousel (dropped mid-discussion; user pivoted to static split hero)
- time_control and rated filters on Global Stats (excluded from the narrow backend exception; defer to v1.10 if requested)
- URL route rename /global-stats → something else (not in scope)
- Browser tab title (document.title) for Global Stats (not currently set; not added)
- Per-column proportional maxTotal for the 2-col Bookmarked Openings: Results (explicitly NOT done; maxTotal spans all rows for comparability)
- Opening Explorer feature section on mobile-only (may be kept via lg:hidden during planning; otherwise deferred)
