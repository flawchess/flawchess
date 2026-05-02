---
title: Custom date range filter — design direction
date: 2026-05-02
context: Pre-discuss-phase design notes for adding a custom start/end date filter alongside the existing recency presets. Targeted for the milestone after the current one.
related_files:
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/types/api.ts
  - app/repositories/query_utils.py
  - frontend/src/types/position_bookmarks.ts
---

# Custom date range filter — design decisions

Captured during `/gsd-explore` on 2026-05-02. Feeds the eventual `/gsd-discuss-phase`
so we don't relitigate the UX or API contract.

## Goal

Add a custom start/end date filter to the existing filter panel. Users currently
have 8 trailing-window recency presets ("All time", "Past week" → "5 years")
but no way to pick a specific historical window (e.g. a tournament range,
a month before a coaching change, exclude a recent slump).

## Use cases (in scope)

- Specific tournament or event window (e.g. "March 1–15")
- Before/after a coaching change or rating drop
- Excluding recent games (everything except the last month)

## Out of scope

- Comparing two time periods side-by-side. Park as a future idea — revisit if
  users start asking for "before/after" comparisons.

## UX direction — Option A: "Custom range…" as a 9th item in the existing dropdown

Selected over Option B (separate collapsible disclosure) because:

- 95% of users will use presets — Option A keeps the panel visually unchanged
  for them
- Custom is a power-user feature, naturally less prominent (one extra click +
  a popover) without extra UI weight
- Single control = no precedence question between preset and custom
- Idiomatic: Stripe, Google Analytics, Shopify all use this exact pattern

### Behaviour

- Add a "Custom range…" item at the bottom of the existing `Select` in
  `FilterPanel.tsx:173-195`
- Selecting it opens a popover with two date inputs (start, end)
- Once set, the dropdown trigger displays the resolved range, e.g.
  `"Mar 1 – Apr 1, 2026"`
- Picking any preset clears the custom range
- Mobile: popover must work inside the filter drawer

### Why "label is enough" for presets

We considered showing the resolved dates ("Past month → Apr 2 – May 2") to
give users insight into what each preset means. Decided against — the preset
labels are self-explanatory, and surfacing date inputs to the 95% case adds
noise for no benefit.

## API contract — drop `recency`, send `from`/`to` dates only

Current `Recency` is a closed string union in `frontend/src/types/api.ts:38`
crossing the API boundary. Replace with two optional date params on the wire.
Frontend computes dates for presets locally.

### Why date-only is cleaner than a discriminated union

- One API shape for presets and custom — backend just does
  `WHERE played_at BETWEEN start AND end`, no preset translation logic
- Frontend owns "now" — correct, since it knows the user's timezone
- Cache keys honestly reflect that "past week" today ≠ "past week" tomorrow
- No discriminated-union complexity in either direction

### Gotchas to handle in the implementation phase

1. **Canonicalize to day boundaries in the user's timezone.** Don't compute
   from raw `Date.now()` per render — TanStack Query keys would change every
   millisecond and cache-bust constantly. Round start to `00:00` and end to
   `23:59:59` in user-local TZ, memoized to today's date string.
2. **"All time" = omit both params.** Don't send a sentinel like
   `1970-01-01`. Null/missing on both ends = no date filter.
3. **LLM insight prompts** (`useEndgameInsights`, `useOpeningInsights`) —
   check whether prompts currently reference "past month" in human terms.
   If so, either compute a human label from the date span
   (`endDate - startDate ≈ 30 days → "past month"`) or pass absolute dates.
   Make a deliberate decision rather than regress.
4. **URL params** (if any expose `recency`) switch to `from`/`to`. Slightly
   uglier but consistent.
5. **`Recency` becomes a UI-only type** — rename to `RecencyPreset` or move
   into FilterPanel-local types so it's clear it no longer crosses the API
   boundary.

## Affected surfaces

Backend: `app/repositories/query_utils.py` (the `apply_game_filters()` shared
implementation per CLAUDE.md). All consumers (openings, endgames, stats,
insights) inherit the change for free.

Frontend hooks that pass recency through today:
`useOpenings`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`,
`useStats`, `useNextMoves`.

## Related cleanup (separate todo)

`TimeSeriesRequest` in `frontend/src/types/position_bookmarks.ts:52` accepts
a `recency` filter for the bookmark time-series chart. Applying recency to a
chart that already plots performance over time was unintentional — the chart
itself is the time axis. Remove from the request shape and the backend
endpoint before or alongside this work, so we don't end up extending it to
`from`/`to` for no reason. See pending todo
`2026-05-02-remove-recency-from-bookmark-timeseries.md`.
