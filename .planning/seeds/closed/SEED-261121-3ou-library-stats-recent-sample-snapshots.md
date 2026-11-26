---
id: SEED-261121-3ou
status: closed. Milestone v2.31.
closed: 2026-11-22
closed_reason: shipped as Phase 258 (recent 1000 games per TC within 36 months for the three comparison endpoints, basis line; release #497)
promoted_to: Phase 258 (2026-11-21)
planted: 2026-11-21
planted_during: /gsd-explore session after the 2026-11-20 release (no active phase)
trigger_when: when planning the next milestone or phase that touches Library Stats or the stats filter behaviour
scope: medium, one phase (backend sample window for three comparison endpoints, a basis line in the Stats tab, tests). No filter-default or Games/Flaws tab changes.
---

# SEED-261121-3ou: Library Stats recent sample for snapshot charts, full history for timelines

Make the Library Stats snapshot charts describe how the player plays now, while the timelines keep
showing the whole career.

**Promoted 2026-11-21 to Phase 258** (`.planning/ROADMAP.md`, Active Phases).

## Why This Matters

Library Stats defaults to all time (`recency: null` in `DEFAULT_FILTERS`), so the you-vs-opponents
flaw, facepalm and tactic comparisons lump a whole career into one average. That is misleading for
anyone who has improved or changed over the years. Endgames Stats already shows a recent ranked
sample, so the same account reads as "how I play now" on one page and "lifetime average" on the
other.

The flaw zones the user is graded against are built on the benchmark basis of the most recent
1000 games per time control in 36 months, so today a lifetime average is compared with bands
calibrated on recent games.

Endgames solved this by dropping the filters and the full timeline for consistency. That trade is
wrong for Library Stats: very active bullet players reach 1000 games in a few months, so a capped
timeline would show only a few months, and the long-term progress view is one of the page's main
attractions.

## Decided Shape (explore session 2026-11-21)

Split by chart type. Do not change filter defaults.

1. **Timelines keep full history.** Sidebar filters, including an explicit recency choice, still
   crop them as today.
2. **Snapshot charts use a recent sample, always.** `/library/flaw-comparison`,
   `/library/facepalm-comparison` and `/library/tactic-comparison` are computed on the most recent
   1000 games per time control within the last 36 months (`RECENT_GAMES_PER_TC_CAP` and
   `RECENCY_WINDOW_MONTHS` in `app/services/canonical_slice_sql.py`), taken from the games the
   sidebar filters leave.
3. **An explicit recency filter replaces the 36-month bound.** The 1000-game cap stays, so a custom
   older date range still shows data.
4. **The cap counts all filtered games, then the analyzed subset is shown.** The window matches
   Endgames and stays time-defined. A player with thin recent analysis coverage gets a small sample
   rather than a silently older one.
5. **A basis line under the snapshot section header**, for example "Based on your most recent 1000
   blitz games (since Mar 2025), 640 analyzed".
6. **No "Recent / All games" switch.** The lifetime snapshot is deliberately unreachable. The
   timeline tells the long-term story.
7. **No default opponent strength of ±100.** The flaw zones are already calibrated at equal
   footing, and by benchmark convention the user's own value stays unfiltered. The filter remains
   available.
8. **Library Games and Flaws tabs are untouched.** The shared filter store keeps its defaults.

## Rejected Alternatives

- **A "Recent n games" filter defaulting to 1000.** It lives in the shared filter state, so the
  Games tab would list only 1000 games, and it would cut the timelines.
- **A 3-year recency default.** Same timeline cut.
- **Opponent strength ±100 by default.** Would hide games outside the range on the Library Games
  tab, and is not needed (point 7).
- **Copying Endgames wholesale (fixed sample, no filters).** The colour, platform and opponent
  strength filters answer real questions on flaw data.

## Accepted Consequences

- The last timeline point (trailing 100 games, `FLAW_TREND_WINDOW`) and the snapshot tile (up to
  1000 games) show different numbers. The basis line covers this.

## Open Points for Planning

- Whether the cap is applied per time control before or after the "played as" colour filter
  (same period for both colours, or the most recent 1000 games of that colour).
- Possible follow-on, a separate decision: restore full-history timelines on Endgames Stats using
  the same split.

## Breadcrumbs

- `app/routers/library.py` (flaw-stats, flaw-comparison, facepalm-comparison, tactic-comparison)
- `app/services/library_service.py` (`get_flaw_comparison`, `FLAW_TREND_WINDOW`)
- `app/services/canonical_slice_sql.py` (window constants)
- `app/routers/endgames.py` (`/ranked-stats`, the Endgames precedent)
- `frontend/src/pages/GlobalStats.tsx` (the Library Stats tab body)
- `frontend/src/components/filters/FilterPanel.tsx` (`DEFAULT_FILTERS`)
