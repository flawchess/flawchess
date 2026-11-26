# Phase 258: Library Stats Recent Sample for Snapshot Charts (SEED-261121-3ou) - Context

**Gathered:** 2026-11-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The Library Stats snapshot charts describe how the player plays now; the timelines keep the whole career.

1. `/library/flaw-comparison`, `/library/facepalm-comparison` and `/library/tactic-comparison` are computed on
   a recent sample: the most recent 1000 games per time control within the last 36 months, taken from the
   games the sidebar filters leave.
2. A basis line in the Stats tab states that sample, and the timeline is marked as full history.
3. A time control with games but no recent ones keeps its timeline and gets an explanatory empty state.
4. A performance check of the new query shape on the largest prod account.

Out of scope: any filter-default change; the Library Games and Flaws tabs; `/library/flaw-stats` (the
timeline) beyond a caption; the Results Breakdown and ELO sections of the Stats tab (they read other
endpoints and stay as they are); full-history timelines on Endgames Stats; the Endgames ranked sample.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (seed "Decided Shape" and roadmap, owner 2026-11-21; not re-discussed)
- **D-01: Split by chart type, no filter-default changes.** The shared filter store keeps `recency: null`.
- **D-02: Timelines keep full history.** Sidebar filters, including an explicit recency choice, crop them as
  today.
- **D-03: Snapshot charts always use the recent sample** (`RECENT_GAMES_PER_TC_CAP` = 1000,
  `RECENCY_WINDOW_MONTHS` = 36, both in `app/services/canonical_slice_sql.py`; reuse the constants, do not
  redefine them).
- **D-04: An explicit recency filter replaces the 36-month bound; the 1000-game cap stays.**
- **D-05: The cap counts all filtered games, then the analyzed subset is shown.** The window is defined by
  time, not by analysis coverage. Thin coverage gives a small sample, never a silently older one.
- **D-06: One shared windowed game set** for the counts and all three comparisons, so the basis line, the
  tiles and the cards always agree.
- **D-07: No "Recent / All games" switch.** The lifetime snapshot is deliberately unreachable.
- **D-08: No default opponent strength of ±100.** The filter stays available and off by default.
- **D-09: Accepted:** the last timeline point (trailing 100 games, `FLAW_TREND_WINDOW`) and the snapshot tile
  (up to 1000 games) show different numbers.
- **D-10: Facepalm rows stay on their own endpoint** with JIT off (257 D-21). The existing analyzed-game
  gates (`FLAW_COMPARISON_GATE`, `TACTIC_COMPARISON_GATE`) and the facepalm low-coverage rule are unchanged;
  they now apply to the windowed set.

### Cap vs colour filter
- **D-11: Filter first, then cap.** With "Played as: White", the sample is the most recent 1000 White games
  per time control. Colour is treated like platform, rated, opponent type and opponent strength: every
  sidebar filter is applied before the ranking. One code path, no colour special case. Accepted consequence:
  a colour view reaches about twice as far back as the unfiltered view.

### Basis line
- **D-12: The existing coverage line becomes the basis line, shown once.** `CoverageBasisLine` in the Flaw
  Stats section (currently "1,768 of 1,790 rapid games analyzed in the current filters.") is replaced by the
  basis line, above the tiles. It keeps its analysis-progress icon and hint (updating / low coverage). It is
  not repeated under "You vs. your opponents" or "Tactic motifs", and it does not move into the sticky TC
  bar.
- **D-13: Wording names the bound that actually cut the sample.** Four variants (exact wording may be
  polished, the structure is locked):
  - At the cap, default window: "Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed."
  - Under the cap, default window: "Based on your 412 blitz games from the last 36 months, 300 analyzed."
  - At the cap, recency filter set: "Based on your most recent 1,000 blitz games in the selected period
    (since Aug 2026), 640 analyzed."
  - Under the cap, recency filter set: "Based on your 212 blitz games in the selected period, 180 analyzed."
  - "in the current filters" is appended only when a sidebar filter other than recency is active.
  - The API returns what the line needs per time control: the window start date, the number of games in the
    window, the analyzed count, and whether the cap was reached.
- **D-14: The timeline gets a short muted caption at its title: "All games in the current filters".** No
  added popover sentence about the tile-versus-last-point difference.

### No recent games
- **D-15: A time control with games but none in the window stays on the TC switch,** so its full-history
  timeline remains reachable. The switch therefore has to list time controls from the unwindowed filtered
  set, not only from time controls with snapshot data (today it reads `/flaw-comparison` `tcs`).
- **D-16: One message, snapshot sections hidden.** For such a time control the basis-line slot carries the
  message, and the tiles, "You vs. your opponents" and "Tactic motifs" are not rendered. The page is the
  message plus the timeline.
- **D-17: "All time" stays the untouched default and reads as 36 months for the snapshots.** No filter-store
  change and no relabelled option. The empty-state message names the real way out, for example: "No blitz
  games in the last 36 months. Choose Past 5 years or a custom range under Recency to include older games."
  No button that changes the filter for the user (it would alter the shared filter store).

### Performance bar
- **D-18: Pass criterion: no slower than today.** Each of the three endpoints is timed before and after on
  the largest prod account, and none may regress. A regression is fixed before merge.
- **D-19: Measured on prod data before the squash-merge,** read-only (`EXPLAIN ANALYZE` of the new query
  shape over the prod tunnel). If an index turns out to be needed, it is measured the same way before any
  migration is written.

### Claude's Discretion
- API field names and schema shape for the window metadata, and whether it rides on `FlawComparisonTc` or a
  shared response field.
- How the windowed set is shared in SQL between counts and the three comparisons (CTE, subquery helper, or
  a repository-level builder).
- Which clock anchors the 36 months: `dev_now_utc` per the project rule, or SQL `NOW()` as the Endgames
  ranked sample does (a documented dev-clock exception there). Prefer `dev_now_utc` unless it breaks plan
  caching or parity with Endgames.
- Which time control is selected by default when the remembered one has no recent games.
- Ties on `played_at` at the cap boundary (a deterministic tiebreak such as game id).
- `data-testid` names and Umami targets (follow the existing library-stats patterns).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-261121-3ou-library-stats-recent-sample-snapshots.md` — decided shape, rejected
  alternatives, accepted consequences, breadcrumbs
- `.planning/ROADMAP.md` (Phase 258 entry) — goal and scope bullets

### Prior decisions that still bind
- `.planning/phases/257-facepalm-rate-library-stats/257-CONTEXT.md` — D-11 to D-13 and D-21 (the facepalm
  card, its own endpoint, JIT off), D-18 (scored-coverage gate)

### Window definition
- `app/services/canonical_slice_sql.py` — `RECENT_GAMES_PER_TC_CAP`, `RECENCY_WINDOW_MONTHS`, and
  `_recent_capped_per_tc_cte` (the benchmark's ranked-window shape the zones are calibrated on)
- `app/services/endgame_ranked_service.py`, `app/routers/endgames.py` (`/ranked-stats`) — the Endgames
  precedent for a recent ranked sample

### Operating constraints for the performance check
- `docs/production-runbook.md` — prod DB access and tuning values
- `docs/dev-tooling.md` — the read-only DB MCP servers and `bin/prod_db_tunnel.sh`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `library_repository.count_analyzed_by_tc` (with `analyzed_only=False` for totals), `fetch_flaw_comparison`,
  `fetch_facepalm_comparison`, `fetch_tactic_comparison`, `_analyzed_game_ids_subquery`
  (`app/repositories/library_repository.py`): the three comparisons and the counts already share one filter
  kwargs set; the window slots in at that shared point.
- `apply_game_filters` (`app/repositories/query_utils.py`): the single filter implementation; the window
  ranks the rows it leaves.
- `CoverageBasisLine` and `libraryCoverageBasisText` (`frontend/src/components/library/stats/LibraryStatsSections.tsx`,
  `frontend/src/lib/flawComparisonMeta.ts`): the line to replace, with the progress icon and hint to keep.
- `outOfOpeningCopy.ts` and `RankedMetricPopover.tsx`: existing frontend copy that mirrors the two window
  constants and phrases a recent-sample basis.

### Established Patterns
- `get_flaw_comparison` returns `analyzed_n` and `total_n` per time control plus a page-level `total_n`; a
  fresh import with nothing analyzed still returns totals so the page can show "0 of N analyzed".
- The TC switch is client-side and never part of a query key; `LibraryStatsTcSwitch` and every section read
  `useLibraryFlawComparison(...).data.tcs`.
- Routers stay thin; the from/to date validation is repeated per endpoint.
- Sequential awaits on one `AsyncSession`, never `asyncio.gather`.

### Integration Points
- `app/routers/library.py`: the three comparison endpoints (unchanged signatures expected; `from_date` /
  `to_date` already tell whether a recency filter is explicit).
- `app/services/library_service.py`: `get_flaw_comparison`, `get_facepalm_comparison`,
  `get_tactic_comparison`.
- `frontend/src/components/library/stats/LibraryStatsSections.tsx`: `FlawStatsSection` (basis line, tiles,
  timeline under one heading), `VsOpponentsSection`, `TacticMotifsSection`, `LibraryStatsTcSwitch`.
- `/library/flaw-stats` `trend_by_tc` is the unwindowed per-TC source that already exists on the page.

</code_context>

<specifics>
## Specific Ideas

- Page shape the owner picked:
  ```
  Flaw stats
  Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed.
  [ tiles ]

  Flaws timeline · all games in the current filters
  [ chart ]

  You vs. your opponents
  [ cards ]

  Tactic motifs
  [ cards ]
  ```
- Quiet time control:
  ```
  Flaw stats
  No blitz games in the last 36 months.
  Choose Past 5 years or a custom range under Recency to include older games.

  Flaws timeline · all games in the current filters
  [ chart ]
  ```
- Recency presets are week, month, 3 months, 6 months, year, 3 years, 5 years and all; only "5 years" and a
  custom range reach past 36 months.

</specifics>

<deferred>
## Deferred Ideas

- Full-history timelines on Endgames Stats with the same split (seed follow-on, a separate decision).
- Treating an actively chosen "All time" as an explicit recency choice (needs the filter store to tell an
  untouched default from a chosen value; rejected for this phase).
- Recent-sample treatment for the Results Breakdown section of the Stats tab (not in the roadmap's list).

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-08-29-variation-tree-nested-button.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`:
  keyword-only matches, unrelated to this phase.

</deferred>

---

*Phase: 258-library-stats-recent-sample-snapshots*
*Context gathered: 2026-11-21*
