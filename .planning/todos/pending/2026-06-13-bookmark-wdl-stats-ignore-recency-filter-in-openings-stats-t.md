---
created: 2026-06-13T06:05:38.014Z
title: Bookmark WDL stats ignore recency filter in Openings Stats tab
area: frontend
files:
  - app/schemas/openings.py
  - app/services/openings_service.py:261-345
  - app/repositories/openings_repository.py (query_time_series)
  - frontend/src/pages/Openings.tsx:342-375
  - frontend/src/components/stats/OpeningStatsCard.tsx
---

## Problem

In the Openings → Stats tab, the bookmarked-position card's **WDL bar, "N Games" count, and Score %** do NOT respond to the recency (or any date) filter. Changing recency to e.g. "3 months" leaves them frozen at full-history values, while the Openings → Games tab correctly shows zero matching games. Confirmed by user (screenshot: "148 Games" unchanged after filtering; clicking through to Games shows none match).

**Root cause:** The bookmark card is a synthetic `OpeningWDL` row stitched from two sources that filter differently:
- **WDL bar + game count + Score %** come from `POST /openings/time-series` (`openings_service.get_time_series` → `openings_repository.query_time_series`). This path **intentionally omits date filtering** per decision **D-19** (the rolling-window chart needs full history for trailing-average context). `total_wins/draws/losses/total_games/last_played_at` are a byproduct of that full-history pass (`openings_service.py:299-341`), so they ignore recency.
- **End Eval row** comes from `POST /stats/bookmark-phase-entry-metrics`, which DOES go through `apply_game_filters` (dates included), so it updates correctly.

Reference correct behavior: **"Most Played Openings"** and the **Games tab** both use `apply_game_filters` and empty out properly (openings drop out when no games match).

## Solution

**User-confirmed desired behavior (two parts):**

1. **WDL bar / count / score must respect recency + all date filters.** When zero games match: WDL bar shows **"No matching games"** and the games count shows **"—"** (em dash) instead of frozen full-history numbers.

2. **The rolling time-series CHART LINE should ALSO be filtered to the recency window (amends D-19)** — BUT the rolling window must NOT be truncated at the start: keep computing the rolling average using **warm-up context** from games *before* the window start, then only **display** points inside the recency window. Match the warm-up pattern used in the other timeline chart implementations (do NOT restart the trailing window at zero at the window boundary).

**Recommended fix shape:**
- `app/schemas/openings.py` — add optional `from_date`/`to_date` to `TimeSeriesRequest` (update the existing D-19 schema comment that says the endpoint does not date-filter).
- `app/services/openings_service.py:261-345` (`get_time_series`) — the service already loads every matching game `(played_at, result, user_color)` in memory. Compute the **WDL totals from the date-filtered subset**; compute the **rolling-window `data` using full history for warm-up** but emit only points with `played_at` inside the window. `last_played_at` should reflect the filtered subset (→ `None`/"—" when empty).
- `app/repositories/openings_repository.py` (`query_time_series`) — still fetch full-history rows (needed for warm-up); the window bound is applied in the service, OR pass the window start so the repo returns full rows but the service knows the boundary. Keep all existing non-date filters.
- `frontend/src/pages/Openings.tsx:342-375` — pass the recency range into `timeSeriesRequest`; `wdlStatsMap` then reflects filtered totals.
- `frontend/src/components/stats/OpeningStatsCard.tsx` — add a `total === 0` empty state (WDL bar "No matching games", count "—"). Note this card is shared with Most Played, but those rows never reach `total === 0` (they drop out), so the branch is bookmark-only in practice.
- **Decision D-19** needs amending/annotating to reflect that the chart line IS now recency-filtered with warm-up context (totals filtered; rolling average warmed up from pre-window games).

**Recommended GSD entry point:** `/gsd-quick` — well-scoped bug fix with a known shape; the only real nuance is the warm-up rolling window (mirror existing timeline charts). Could also be a small phase if it should carry a CHANGELOG entry + D-19 amendment formally.
