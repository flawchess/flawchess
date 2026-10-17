---
phase: 242-openings-stats-insights-rework
verified: 2026-10-17T20:30:00Z
status: human_needed
score: 12/12 must-haves verified
covered_files:
  - .planning/phases/242-openings-stats-insights-rework/242-01-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-01-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-02-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-02-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-03-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-03-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-04-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-04-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-05-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-05-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-06-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-06-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-07-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-07-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-08-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-08-SUMMARY.md
  - .planning/phases/242-openings-stats-insights-rework/242-09-PLAN.md
  - .planning/phases/242-openings-stats-insights-rework/242-09-SUMMARY.md
  - app/repositories/stats_repository.py
  - app/services/opening_eval.py
  - app/services/opening_insights_service.py
  - app/services/openings_service.py
  - app/services/repertoire_recency.py
  - app/services/score_confidence.py
  - app/services/stats_service.py
  - frontend/src/components/charts/PositionResultsPanel.tsx
  - frontend/src/components/charts/ScoreChart.tsx
  - frontend/src/components/openings/stats/FindingCard.tsx
  - frontend/src/components/openings/stats/OpeningFindings.tsx
  - frontend/src/components/openings/stats/RepertoireExpandedRow.tsx
  - frontend/src/components/openings/stats/RepertoireTable.tsx
  - frontend/src/components/openings/stats/VerdictBar.tsx
  - frontend/src/components/openings/stats/VerdictPopover.tsx
  - frontend/src/lib/openingVerdict.ts
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/openings/StatsTab.tsx
covered_digest: "v3:sha256:c7c86f24ae09dce0adc3fd4fcfebb1d0320e204347c84a8571e2a866047df063"
behavior_unverified: 0
overrides_applied: 0
advisory:
  - finding: "WR-01: a bookmark on the SHALLOWER position of a duplicate pair leaves the deeper most-played twin visible (dedupe runs before the twin drop and the twin drop compares hashes only)"
    category: other
    reason: "Outside the letter of D-06 (position-equal twin), not present in the owner's data; no test covers it. Fix: drop twins first, then drop candidates whose game-set fingerprint equals a dropped twin's."
    evidence_status: "code-read (stats_service.py:377-386); not reproduced against data"
  - finding: "WR-02: eval verdict 20-game floor is applied to total games, not eval_n"
    category: other
    reason: "Matches the plan truth literally ('position has at least 20 games'); a 40-game opening with eval_n=11 can still get a green/red eval dot. Rare because backend confidence needs p<0.01."
    evidence_status: "code-read (RepertoireTable.tsx:173-178, FindingCard.tsx:131-136, RepertoireExpandedRow.tsx:105-110, PositionResultsPanel.tsx)"
  - finding: "WR-03: a finding at exactly 45.0% score renders grey ('typical') because |0.45-0.5| = 0.04999999999999999 <= 0.05, while exactly 55.0% is coloured"
    category: other
    reason: "Reproduced in node. Asymmetric at the exact band edge only; needs n of about 700+ with a score of exactly 0.45 to matter."
    evidence_status: "node -e: 0.45-0.5 = -0.04999999999999999 (typical), 0.55-0.5 = 0.050000000000000044 (coloured)"
  - finding: "Test-coverage gap: deleting the _dedupe_identical_sets call from _prepare_candidates passes the whole backend suite (the helper is unit-tested, the wiring is not)"
    category: other
    reason: "Mutation check by this verifier. The wiring is correct today (confirmed against the owner's dev data, see Behavioral Spot-Checks); add one DB-level get_most_played_openings test with two identical-game-set rows to lock it."
    evidence_status: "mutation run, 155 and 74 tests passed with the call removed"
human_verification:
  - test: "Open /openings/stats on desktop (1280 px), tablet (768 px) and phone (390 px). Scroll with the table taller than the viewport."
    expected: "The White | Black switch stays pinned (desktop: its own bar; phone: left of the Filters button, ONE sticky row, not two overlapping). On tablet/desktop the repertoire column header sticks directly under the switch with no gap or overlap. Switching colour swaps findings and table; reload resets to the Played-as colour."
    why_human: "Sticky positioning depends on ancestors not setting overflow and on real pixel offsets (REPERTOIRE_HEADER_STICKY_TOP_PX = 48); jsdom cannot lay it out."
  - test: "On the Stats tab click a finding card's Moves link, then its Games link."
    expected: "Moves opens the Move Explorer at the entry position with the candidate move's arrow/row pulsing for the pulse window; Games opens the Games tab filtered to the line. Visiting /openings/insights lands on /openings/stats."
    why_human: "The pulse is a CSS animation timed by useDeepLinkHighlight; automated tests cover the handlers but not the visible pulse."
  - test: "On the owner account (user 28) open the White table."
    expected: "Queen's Gambit (280 games, last played Oct 2023) is under the collapsed 'Played before (10)' group, not in the main table; the hint reads 'not played as White since 14 Feb 2026'; the Caro-Kann Advance / Botvinnik-Carls duplicate shows once under Black. (Backend output for this was confirmed by this verifier; the UI rendering was not seen.)"
    why_human: "Visual confirmation of the grouped table on real data."
  - test: "On a phone width, open the findings section and a repertoire row."
    expected: "Each findings section shows 2 cards and a 'Show more' button revealing up to 5; rows stack (name left, Score above Eval at top right, WDL bar with 'N games . last played' full width); expanded row stacks the Moves/Games/Bookmark links beside the 200 px board."
    why_human: "Responsive grid/hidden classes (max-md:hidden, max-md:grid) need a real viewport."
  - test: "Expand a repertoire row with several months of games, including one with a gap over 90 days."
    expected: "Score-over-time line on the ordinal axis with a palm-tree marker at the break, grey weekly bars with the tallest bar filling roughly the bottom 20% of the plot, readable tooltip ('Week of ... N games that week')."
    why_human: "Recharts rendering and visual proportion."
---

# Phase 242: Openings Stats + Insights Rework Verification Report

**Phase Goal:** Rework the Openings Stats and Insights tabs the way Phases 238/239 reworked the Endgame and Library Stats pages: simpler, more readable, no loss of information. Design from sketch 012 / SEED-204, 238/239 system decisions D-14..D-17 unchanged.
**Verified:** 2026-10-17
**Status:** human_needed
**Re-verification:** No, initial verification

All code-checkable must-haves hold. Remaining items are browser-layout and animation checks that the SUMMARYs themselves marked human_judgment. Three code-review warnings (WR-01..03) were weighed; none defeats a must-have (details below).

## Goal Achievement

### Observable Truths

Truths = ROADMAP success-criteria bullets (the contract) merged with the PLAN `must_haves`.

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Insights merged into Stats: Insights subtab (desktop + mobile) and route gone; `/openings/insights` redirects to `/openings/stats` | VERIFIED | `types/openingsTab.ts` union is `'explorer' \| 'games' \| 'stats'`; `Openings.tsx:87-90` `needsLegacyRedirect` includes `endsWith('/insights')` -> `<Navigate to="/openings/stats" replace />` (l.534); tab strips list only Moves/Games/Stats (desktop l.556-580, mobile l.680-700); grep for `OpeningInsightsBlock/OpeningFindingCard/OpeningStatsCard/OpeningStatsSection` finds only stale comments; `Openings.render.test.tsx` asserts `tab-insights` absent. `tsc -b` exit 0. |
| 2 | One sticky White \| Black switch, not persisted, starts from Played-as, phone shares the Filters row, tracked once per real change | VERIFIED (layout: human) | `OpeningColorSwitch.tsx` (aria-pressed, `if (color === selected) return` before `trackFeature('option-change', {target:'opening-stats-color'})`); `Openings.tsx:123` `useState(filters.color)` (plain state, no storage); `StatsTab.tsx` desktop bar `sticky top-0 z-20`, `Openings.tsx:714` mobile sticky row holds the switch + Filters button. Pixel behaviour: see human item 1. |
| 3 | Findings gate is 99% (backend `confidence=="high"`), top 5 per section, current before older, medium-only "Not clear yet" list (<=10, count = full medium count), low dropped | VERIFIED | `opening_insights_service._partition_section` (cards = high only, `[:FINDINGS_CARD_CAP=5]`; not_clear = medium sorted `(not is_current, p_value)`, `[:10]`, `not_clear_count=len(medium)`); mutation `high -> != "low"` fails `test_partition_not_clear_is_capped_sorted_and_counted_before_the_cap`. Live run on owner data: 4 white-strength cards all `high`, not-clear lists all `medium`. |
| 4 | Finding card: move-led, opening name without ECO + line, 120 px board with arrow, "You score X%" + score popover + WDL bar, baseline-centred Eval bar, eval-only why line, older-games chip, Moves/Games deep links; phone 2 cards + Show more, desktop all 5 in 2 columns | VERIFIED (phone layout: human) | `FindingCard.tsx` (BOARD_SIZE=120, `stripEcoSuffix`, `ScoreLine`, `MiniWDLBar`, `EvalLine` -> `VerdictBar` with `zeroTickDelta={-baseline}`, `whyLine`, `OlderGamesChip`); `OpeningFindings.tsx` (`INITIAL_VISIBLE_PHONE=2`, `max-md:hidden` beyond 2 until expanded, `md:grid-cols-2`, ShowMore testid + `opening-insights-more` event on expand only; empty state "Nothing clear yet as X." + lean text). 246 related vitest tests pass. |
| 5 | Repertoire table replaces the 4 old sections: bookmarks pinned, then most played, collapsed "Played before (n)"; columns Opening/Games/Results/Score/Eval after opening; no Trend, score bullet, spines, coloured fonts, CI whiskers; no ECO; rows <20 games faded and never coloured; stale bookmark chip | VERIFIED | `RepertoireTable.tsx` (COLUMN_HEADERS exact; `GroupRow` Bookmarks/Most played; `PlayedBeforeToggle`; `isFadedRow(row.games)` -> `UNRELIABLE_OPACITY`; `NOT_PLAYED_RECENTLY` chip for non-current bookmarks; no MiniBulletChart/whisker); `useRepertoireRows` uses `display_name` + `stripEcoSuffix` (never `label`); `openingVerdictReason` returns `too-few` below 20 games so the dot is neutral. Compact cell colours text only on better/worse, same rule as the 239 GapBar. |
| 6 | Score verdict uses the shared +/-5% band and the backend 99% confidence; eval verdict centred on the colour baseline with +/-0.30 band, faint 0 tick, red/green only at 99% | VERIFIED | `openingVerdict.ts` (`SCORE_VERDICT_BAND = SCORE_BULLET_NEUTRAL_MAX = 0.05`, `EVAL_VERDICT_BAND = EVAL_NEUTRAL_MAX_PAWNS`, reason precedence too-few -> typical -> chance -> sign, colour only when `confidence === 'high'`); `VerdictBar.tsx` draws band, dashed zero tick at `-baseline`, centre swatch. See WR-02/WR-03 for edge caveats. |
| 7 | Popovers carry greyed footer "99% CI a to b . p = x vs reference . n = N", no "pawns", no ECO | VERIFIED | `VerdictPopover.tsx` `footerText` / `scoreFooterText` ("vs 50%", "vs +0.25"), `italic text-background/60`; grep finds no "pawn" in user-facing strings; backend returns `score_ci99_*`, `eval_ci99_*`, p-values (D-18 server-side, `score_verdict_fields`). |
| 8 | Current/past cutoff per colour = earlier of the 200th most recent game and now-60d, computed under the active filters from `dev_now_utc`; drives Played-before rows, bookmark chip and findings chip | VERIFIED | `repertoire_recency.combine_cutoff` = `min(nth, now-60d)`, None when <200 games; `query_nth_recent_played_at` goes through `apply_game_filters(color=...)`; `now_utc` injected in `routers/stats.py:95`, `insights.py:117`, `openings.py:51`, no `datetime.now()` in services; mutation `min -> max` fails `test_recent_nth_game_falls_back_to_the_day_floor`. Live: owner cutoff W 2026-02-14 / B 2026-02-13; Queen's Gambit (280, last 2023-10-03) flagged past. |
| 9 | Most-played: fetch 60 -> dedupe identical game sets (deeper line) -> drop same-colour bookmark twins -> cutoff-restricted second fetch if <10 current -> 10 current + 10 past; bookmarks never capped | VERIFIED (test gap, see advisory) | `stats_service._most_played_for_color` / `_prepare_candidates` / `_split_and_cap` / `_merge_recent_nominees`; constants `MOST_PLAYED_FETCH_LIMIT=60`, `CURRENT_LIMIT=10`, `PAST_LIMIT=10`, `MIN_GAMES_FOR_OPENING=1`. Live owner data: 10 C + 10 P per colour, "Caro-Kann: Advance, Botvinnik-Carls" (172) appears once, the `vs. Caro-Kann: Advance` twin is gone. Note: removing the dedupe call in `_prepare_candidates` still passes all tests, so the wiring is not locked by a test (advisory). |
| 10 | Eval z-test and bar centred on the colour baseline (+0.25 W / -0.25 B) for Openings only (Stats, bookmarks, insights, Moves/Games); `avg_eval_pawns` raw; Endgames untouched | VERIFIED | `opening_eval.finalize_opening_eval` passes `baseline_cp`; used in `stats_service` (rows + `_bookmark_phase_entry_item`), `opening_insights_service._apply_eval_metrics_to_finding`, `openings_service.analyze`; `endgame_service.py` calls `compute_eval_confidence_bucket` with default `baseline_cp=0` and `git diff 70f536a1a -- app/services/endgame_service.py` is empty; mutation `baseline_cp -> 0.0` fails `test_white_mean_at_the_baseline_reads_as_typical`. Stale "H0 = 0 cp / only a tick" comments are gone (grep). |
| 11 | Moves/Games tabs show the new baseline-centred verdict bar (`opening-end`); Endgames (`endgame-entry`) keeps the old MiniBulletChart row | VERIFIED | `PositionResultsPanel.tsx`: `showVerdictBar` branch renders `OpeningEvalVerdictRow` (VerdictBar + EvalVerdictPopover, fixed `eval-bullet-popover-trigger` id); else `EvalBulletCells` with `MiniBulletChart` + `EvalConfidencePopover evalContext` unchanged for `endgame-entry`; `PositionResultsPanel.test.tsx` covers both contexts. |
| 12 | Expanded row: 200 px board, Moves/Games/Bookmark links, Score bar (45-55%), Eval bar, per-opening `ScoreChart` (single series, optional weekly volume bars bottom 20%, ordinal axis, palm-tree breaks); multi-line bookmark chart, `ScoreChart` multi mode and the per-bookmark include toggle (and its localStorage keys) retired; weekly counts from backend | VERIFIED (rendering: human) | `RepertoireExpandedRow.tsx` (BOARD_SIZE=200, ScoreBar/EvalBar, `BookmarkLink`, `ScoreChart series showVolume`); `ScoreChart.tsx` takes ONE `series`, bars on hidden axis `[0, barMax*5]`, `inactivityGapReferenceLines`; `useOpeningRowTimeSeries` fetches lazily (row.series null + expanded); backend `_build_bookmark_time_series` emits ISO-week Monday points with `per_week_games`; `retiredLocalStorage.removeRetiredBookmarkChartKeys` called once in `Openings.tsx:116`; no `bookmark-chart-enabled`/"Include in opening" strings remain; `['mostPlayedOpenings']` invalidated on bookmark create/delete. |

**Score:** 12/12 truths verified (0 present, behavior-unverified). Visual/responsive aspects of truths 2, 4, 12 are carried as human items.

### Decision Coverage (242-CONTEXT.md, no REQUIREMENTS.md for this milestone)

| ID | Decision | Status | Where |
| -- | -------- | ------ | ----- |
| D-00 / D-00b | SEED-204 locked design; score band stays +/-5% | SATISFIED | truths 1-7, 12; `SCORE_VERDICT_BAND` |
| D-01 | 200 games OR 60 days, whichever reaches further back | SATISFIED | `combine_cutoff`, constants |
| D-02 | Cutoff under active filters via `apply_game_filters` | SATISFIED | `query_nth_recent_played_at` |
| D-03 | Named constants; `now_utc` from `dev_now_utc` | SATISFIED | `CURRENT_REPERTOIRE_*`, router `NowUtc` |
| D-04 | Cutoff drives Played-before, stale-bookmark chip, older-games chip; backend returns cutoff + `is_current` | SATISFIED | `is_current` on rows/findings/series, `current_cutoff_*` in 2 responses |
| D-05 (+ clarified) | 10 current + 10 past; second cutoff-restricted query | SATISFIED | `_merge_recent_nominees`, `_needs_recent_fallback` |
| D-06 | fetch -> dedupe -> twin drop -> split -> cap; bookmarks never capped | SATISFIED (WR-01 edge) | `_prepare_candidates`, `useRepertoireRows` |
| D-07 | `MIN_GAMES_FOR_OPENING=1`, faded <20 | SATISFIED | constant, `isFadedRow` |
| D-08 | Phone 2 cards + Show more (testid + Umami) | SATISFIED | `OpeningFindings.tsx` |
| D-09 / D-10 / D-11 | Medium-only Not clear yet, <=10, sorted, empty-state count | SATISFIED | `_partition_section`, `NotClearYet`, `leanText` |
| D-12 | Backend wave first | SATISFIED | plans 01-03 wave 1-2 |
| D-13 | Centred z-test on all Openings call sites; endgame untouched; comments updated | SATISFIED | truth 10 |
| D-14 | ScoreChart multi mode retired | SATISFIED | truth 12 |
| D-15 | `/openings/insights` redirects to Stats | SATISFIED | truth 1 |
| D-16 | Per-bookmark include toggle + localStorage retired | SATISFIED | truth 12 |
| D-17 | Moves/Games get the new eval verdict bar; Endgames unchanged | SATISFIED | truth 11 |
| D-18 | Bookmark score p-value + 99% CI server-side in `/openings/time-series` | SATISFIED | `BookmarkTimeSeries` via `score_verdict_fields` |

### Required Artifacts / Key Links

All artifacts listed in the PLAN `must_haves` exist, are substantive and wired (checked by reading: `repertoire_recency.py`, `opening_eval.py`, `score_confidence.score_verdict_fields`, `stats_repository.query_nth_recent_played_at` / `game_id_sum` / `ply_count`, `OpeningColorSwitch`, `retiredLocalStorage`, `RepertoireTable`, `useRepertoireRows`, `OpeningFindings`, `FindingCard`, `VerdictBar`, `VerdictPopover`, `openingVerdict`, `RepertoireExpandedRow`, `ScoreChart`, `useOpeningRowTimeSeries`, `types/openingsTab.ts`). Key links confirmed: routers -> `dev_now_utc`; services -> `resolve_current_cutoffs` / `finalize_opening_eval` / `score_verdict_fields`; `PositionResultsPanel` -> `VerdictBar`; `StatsTab` -> `OpeningFindings` + `RepertoireTable`; `Openings.tsx` -> `/openings/stats` redirect; `RepertoireExpandedRow` -> `ScoreChart showVolume`; `useOpeningRowTimeSeries` -> `useTimeSeries`.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| -------- | ---- | ------ | --------- | ------ |
| RepertoireTable rows | `mostPlayedData`, `tsData` | `/stats/most-played-openings`, `/openings/time-series` -> SQL via `apply_game_filters` | Yes (owner dev data returned 10+10 rows per colour with scores/evals) | FLOWING |
| FindingCard | `useOpeningInsights` | `/insights/openings` -> `compute_insights` | Yes (4 cards + not-clear lists on owner data) | FLOWING |
| Expanded-row chart | `useOpeningRowTimeSeries` | `/openings/time-series` weekly points with `per_week_games` | Yes (backend unit tests; lazily fetched) | FLOWING |
| Moves/Games eval bar | `stats.avg_eval_pawns`, `eval_ci99_*` | `/openings/positions` -> `finalize_opening_eval` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend phase suites | `uv run pytest -n auto -q` on 13 phase test files | 281 passed | PASS |
| Frontend phase suites | `npx vitest run` on openings, charts, lib, pages, bookmarks tests | 18 files / 246 tests passed | PASS |
| Type check | `npx tsc -b` (frontend) | exit 0 | PASS |
| Mutation: cutoff `min -> max` | edit + run recency tests | fails (reverted) | PASS |
| Mutation: eval baseline -> 0 | edit + run eval tests | fails (reverted) | PASS |
| Mutation: 99% gate loosened to non-low | edit + run insights tests | fails (reverted) | PASS |
| Mutation: remove `_dedupe_identical_sets` from `_prepare_candidates` | edit + run stats tests | still passes (reverted) | GAP (advisory) |
| Live owner data (user 28), `get_most_played_openings` | script against dev DB (read-only) | 10 current + 10 past per colour; Queen's Gambit (280) past; Caro-Kann Advance / Botvinnik-Carls (172) once | PASS |
| Live owner data, `compute_insights` | script against dev DB | cards only `high`, not-clear only `medium`, current-first ordering | PASS |
| `/openings/insights` legacy redirect | `Openings.render.test.tsx` + code read | redirect present | PASS |

Working tree was left clean (all mutations reverted, scratch script removed).

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` declared in any PLAN/SUMMARY and none under `scripts/*/tests/`.

### Requirements Coverage

No REQUIREMENTS.md for this milestone; the D-ID table above is the coverage contract. All 18 decision IDs account for an implementation. No orphaned requirement IDs.

### Anti-Patterns Found

No `TBD/FIXME/XXX` markers in the changed files. Stale references only in comments (info, from the review): `eval_confidence.py:35-38`, `types/insights.ts:131`, `sanToSquares.ts`, `EvalCpuPlaceholder.tsx:6`, `ChessBoard.tsx:30`, `index.css:303`, `useReadiness.ts:42` still name deleted `OpeningFindingCard` / `OpeningInsightsBlock` / `OpeningStatsCard`; `EvalConfidencePopover`'s `'opening-end'` branch is now unreachable. None are blockers.

### Code-Review Findings Weighed (242-REVIEW.md, 0 critical, 3 warnings)

| Finding | Defeats a must-have? | Assessment |
| ------- | -------------------- | ---------- |
| WR-01 twin drop after dedupe | No | Plan truth and D-06 say "a row whose `full_hash` equals a same-colour bookmark's" is dropped; that holds. The bug is a bookmark on the shallower line of a duplicate pair, which D-06 does not literally cover and which does not occur in the owner data (both owner duplicates are most-played pairs and collapse correctly). Real but edge. Recommend fixing (the review's drop-twins-first patch is small) and adding the test. |
| WR-02 eval floor uses games not eval_n | No | Truth 6 is worded on game count and holds literally. Residual false-colour risk needs `eval_n < ~20` with p<0.01, which is rare. Recommend passing `eval_n` into the eval verdict input. |
| WR-03 float edge at +/-0.05 | No | Reproduced. Affects only a score of exactly 45.0% with a 99% finding (n about 700+); asymmetric vs 55.0%. Recommend rounding the delta in `openingVerdictReason`. |

These are recorded as `advisory:` items, not gaps. `242-REVIEW-DISPOSITION.md` still shows all 10 findings as `open`; triage (fix / defer) is the owner's call and does not change this verdict.

### Human Verification Required

See `human_verification` in the frontmatter (5 items): sticky switch and header at 390/768/1280 px, finding-card Moves pulse deep link and legacy-URL redirect, owner-data Queen's Gambit under "Played before" in the UI, phone stacking and Show more, and the score-over-time chart rendering (palm tree, weekly bars at bottom 20%).

### Gaps Summary

No gaps. Every locked decision (D-00..D-18) maps to working, wired code; targeted mutations of the cutoff, the baseline centring and the 99% gate are caught by tests, and a live run on the owner's dev data shows the expected current/past split and duplicate collapse. The one weak spot is test coverage of the dedupe wiring (advisory). The phase is held at `human_needed` only because the browser-layout checks (sticky behaviour at three widths, pulse animation, chart look) cannot be confirmed without a browser.

---

_Verified: 2026-10-17_
_Verifier: Claude (gsd-verifier)_
