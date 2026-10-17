---
phase: 238
review: 238-REVIEW.md
updated: 2026-10-11
---

# Phase 238: Review Disposition

One row per finding in 238-REVIEW.md. `open` = not yet triaged by the owner.

| Finding | Severity | Summary | Disposition | Note |
|---------|----------|---------|-------------|------|
| BE-WR-01 | warning | Time-pressure aggregate lines fall back to the ungated metric value (narrates below-floor values) | fixed | Fallback only for `ranked`/`unranked` status; regression test with a 2-game below_floor cell |
| BE-WR-02 | warning | Prompt series filters ignore the new time_control dimension of score_timeline | fixed (partial by design) | C2/C5 now key on (metric, subsection, dim_key); per-TC regression test. Stale-live-twin gate stays on (metric, subsection) on purpose: a stale combo keeps its [summary] + stale marker and drops only its raw series when another combo is live (prompt allows one historical clause), same as endgame_elo combos |
| FE-WR-01 | warning | Generated insights report lost on Stats tab remount (mutation result not written to the cached query) | fixed | Mutation onSuccess writes the cached-report query; local generatedInsights state removed |
| FE-WR-02 | warning | Import completion does not invalidate cached insights unless the Stats tab is mounted | fixed | App.tsx handleJobDone invalidates ['endgame-insights']; per-tab active-jobs edge effect removed |
| FE-WR-03 | warning | Percentile ordinal not clamped ("0th"/"100th"), disagrees with dot and popover | fixed | `displayPercentile` (round then clamp 1..99) drives dot, ordinal, color and popover. Same as the 238-09 UAT "0th" observation |
| BE-IN-01 | info | Dead retirement leftovers (categories_by_tc, ClockStatsRow, unused clock sums) | fixed | Removed categories_by_tc (backend + TS type), ClockStatsRow, _ClockAggregate, _bump_timeout_counts; iterate_clock_rows returns a 4-tuple |
| BE-IN-02 | info | Stale docstrings referencing retired components and plan numbers | fixed | Reworded; line-number citations removed |
| BE-IN-03 | info | Bare str for fixed sets in the ranked path | fixed | AnalyticsPlatform, Literal user_color / opponent_type / outcome keys; redundant cast dropped |
| BE-IN-04 | info | endgame_ranked_service imports private helpers from endgame_service | fixed | The eight shared helpers lost their underscore (repo-wide rename) |
| FE-IN-01 | info | Band color uses the unrounded percentile, contradicting the displayed ordinal at 25/75 | fixed | Folded into the FE-WR-03 fix |
| FE-IN-02 | info | Duplicate data-testids within one mount; duplicate ids reach aria-labelledby | fixed | Peers card uses `peer-ranked-metric-*` testids with the shared analytics key (new `analyticsKey` prop); type section uses aria-label |
| FE-IN-03 | info | Stats tab fires the Games tab's queries; tab switch remounts content | fixed (partial) | Games-tab stats + games queries gated on `tier2 && activeTab === 'games'`. SidebarLayout remount accepted: Radix already unmounts the inactive tab, and FE-WR-01 removed the state it lost |
| FE-IN-04 | info | Time Pressure curve shows an empty plot with no message when no clock data | fixed | Chart renders a muted empty-state line when no bin has games |
| FE-IN-05 | info | Un-chosen default TC can change on payload refetch | fixed | First D-12 default pinned in memory (module-level, set from an effect) until that TC leaves the payload |
