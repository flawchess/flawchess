---
created: 2026-05-02T00:00:00.000Z
title: Remove recency filter from bookmark time-series request
area: frontend / backend
files:
  - frontend/src/types/position_bookmarks.ts
  - app/schemas/openings.py
related_notes:
  - .planning/notes/custom-date-range-filter.md
---

## Why

Bookmark time-series charts plot WDL performance over time — the chart itself
is the time axis. Applying a `recency` filter on top is conceptually wrong
(it crops the chart instead of filtering the underlying games in any useful
way) and was unintentional in the original implementation.

This needs to come out before the custom date range filter work
(see `.planning/notes/custom-date-range-filter.md`), otherwise we will end
up extending it to `from`/`to` for no good reason.

## What

1. Remove `recency` from `TimeSeriesRequest` in
   `frontend/src/types/position_bookmarks.ts:52`.
2. Remove the matching `recency` field from the time-series request schema
   in `app/schemas/openings.py` (line ~181 — there are three `recency`
   declarations in that file; only the time-series one goes).
3. Drop the filter from any time-series service / repository call site.
4. Verify no UI surface currently exposes recency on the bookmark
   time-series chart (it likely doesn't — this was an unused param).

## Out of scope

- The other two `recency` usages in `app/schemas/openings.py` (the regular
  openings and next-moves requests) — those stay until the date-range
  refactor lands.
