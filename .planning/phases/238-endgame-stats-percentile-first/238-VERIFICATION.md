---
phase: 238-endgame-stats-percentile-first
verified: 2026-10-11T17:30:00Z
status: passed
score: 22/23 must-haves verified
covered_files:
  - app/routers/endgames.py
  - app/services/endgame_ranked_service.py
  - app/services/insights_llm.py
  - app/services/insights_service.py
  - frontend/src/components/endgames/EndgameStatsTab.tsx
  - frontend/src/components/endgames/stats/ComparedToPeersCard.tsx
  - frontend/src/components/endgames/stats/PercentileBar.tsx
  - frontend/src/components/endgames/useEndgameInsightsState.ts
  - frontend/src/pages/Endgames.tsx
covered_digest: "v3:sha256:69188fb202f0197bba7389a3a78633c809efa0f7ac0e79a90a0793e90ac7c177"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Generate a Shelly report on the Stats tab, switch to the Games tab, switch back to Stats (also try crossing the md breakpoint)"
    expected: "The just-generated report is still shown (D-00i: Shelly block unchanged)"
    why_human: "Code reading shows the report is dropped on remount until the 5-minute cached-query staleTime expires (FE-WR-01). Owner decides whether to fix before merge. Not exercised by any test or by the 238-09 UAT, which only checked reload."
  - test: "Decide whether the Time Pressure curve (ScoreGapByTimePressureChart) keeps its CI whiskers"
    expected: "Owner states keep or remove. SEED-196 locked decision 1 and the CONTEXT phase boundary say CI whiskers leave the visible UI; the ROADMAP criterion limits this to ranked metrics, and D-00f asks only for a grey band plus neutral line and dots."
    why_human: "Plan 238-05's own success criteria say no CI whiskers remain on the Stats tab, but the SUMMARY records a deliberate keep because the curve is not a ranked metric. A product call, not a code defect."
  - test: "Triage the five open review warnings (BE-WR-01, BE-WR-02, FE-WR-01, FE-WR-02, FE-WR-03) in 238-REVIEW-DISPOSITION.md"
    expected: "Each gets fix-now, follow-up, or accept. None breaks a stated must-have truth (see Review Warning Weighing)."
    why_human: "All 14 findings are still disposition 'open'."
---

# Phase 238: Endgame Stats Percentile-First Redesign Verification Report

**Phase Goal:** Make the Endgame Stats tab readable by giving every metric one verdict (peer percentile on the ranked sample), retiring zone-color, chip and z-test verdicts and the duplicate gauges.
**Verified:** 2026-10-11
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

The goal is achieved in the codebase. Every peer-ranked metric now has one verdict: a percentile bar on the ranked-sample value, with an uncolored value and one merged popover. Gauges, zone-colored numbers, the cross-TC chips and the z-test verdict are gone from the Stats tab. The Stats tab reads `GET /api/endgames/ranked-stats` and takes no filter state. No must-have truth is FAILED. The `human_needed` status is for one Shelly regression I confirmed by reading code (FE-WR-01), one product question (curve CI whiskers) and the open review-warning triage.

### Observable Truths (coverage contract D-00a..D-00i, D-01..D-14)

| #   | Decision | Truth | Status | Evidence |
| --- | -------- | ----- | ------ | -------- |
| 1 | D-00a | One percentile bar per ranked metric (25-75 band, median tick, red <25 / blue 25-75 / green >75), values uncolored | VERIFIED | `PercentileBar.tsx`, `percentileBandColor` in `rankedMetrics.ts`; `MetricsCard.tsx` renders the rate with no color class ("Uncolored on purpose"); `PercentileBar.test.tsx` passes |
| 2 | D-00b | Big number, WDL bar and percentile describe the same ranked games | VERIFIED | `MetricsCard.tsx` takes rate and `buckets` from one `RankedTcStats`; backend parity tests pass (`test_endgame_ranked_parity.py`, 353 targeted backend tests green) |
| 3 | D-00c | One merged popover: WHAT + sign, percentile statement, four disclosures, greyed n / CI / p footer | VERIFIED | `RankedMetricPopover.tsx` has cohort, recent-games basis, filter independence and anchor-composition bullets, then `<hr>` and an italic `text-background/60` footer. Old `MetricStatPopover`, `MetricStatTooltip` and `PercentileChip` have zero references in `frontend/src`, `app/`, `tests/`, `scripts/` |
| 4 | D-00d | Gauges removed; bracket under the WDL bar | VERIFIED | `EndgameGauge` has zero references. `MetricsCard.tsx` `Bracket` spans wins / wins+draws / score |
| 5 | D-00e | Type table with grey ranges, white tick, amber only below range, faded rows <100 games, stacked on mobile | VERIFIED | `TypeTable.tsx` (`TYPE_ROW_LOW_CONFIDENCE_GAMES = 100`, `PER_CLASS_TC_GAUGE_ZONES`, "no red and no green"); `TypeTable.test.tsx` passes; 238-09 UAT confirmed stacking at 375 px |
| 6 | D-00f | Clock Gap timeline and pressure curve: one grey band, neutral line and dots | VERIFIED | `EndgameClockDiffOverTimeChart.tsx` and `ScoreGapByTimePressureChart.tsx` use `TYPICAL_BAND_FILL` and `NEUTRAL_SERIES_COLOR`. Caveat: the curve keeps `ErrorBar` CI whiskers (see Human Verification) |
| 7 | D-00g | "Compared to similar-rated players" card, rows link to sections | VERIFIED | `ComparedToPeersCard.tsx`, `METRIC_SECTION_ID`, `findRenderedSection`. The G-1 mobile scroll bug was fixed in `554c945c4` with a mutation-checked regression test |
| 8 | D-00h | One synced TC switch per section; Overall per-TC with 2 cards; aggregated chips retired | VERIFIED | `useEndgameStatsTc.ts` is a shared `useSyncExternalStore`. `OverallSection.tsx` has `ScoreCard` + `EntryCard`. No `score_gap_percentile`, `achievable_score_gap_percentile`, `per_tc_breakdown` or `PerTcBreakdownOut` in `app/`. `/endgames/overview` returns 404 (router tests) |
| 9 | D-00i | Shelly block, per-section slots, Score Gap over Time and ELO Timeline unchanged | UNCERTAIN (WARNING) | Charts and section slots render as before (`EndgameStatsTab.tsx`; timeline files not modified in the diff). Regression: the generated report is lost on Stats to Games to Stats (FE-WR-01, confirmed below) |
| 10 | D-01 | Stats tab ignores filters | VERIFIED | `EndgameStatsTab` props are only `tier2` and `onCategorySelect`; `/ranked-stats` declares no params; no filter-store import under `components/endgames`; Games tab moved to filtered `/endgames/stats` |
| 11 | D-02 | Filter panel hidden on Stats, state preserved | VERIFIED | `Endgames.tsx`: `desktopPanels = activeTab === 'games' ? [filtersPanel] : []`; mobile filter UI gated on `activeTab === 'games'`; `Endgames.filterVisibility.test.tsx` passes; UAT confirmed a non-default filter survives a round trip |
| 12 | D-03 | Both timelines use the ranked sample and follow the TC switch | VERIFIED | Per-TC `score_gap_timeline` and ELO combos in `endgame_ranked_service.py`; `OverallSection.tsx` renders them for the selected TC |
| 13 | D-04 | Filter-free Shelly; one report per user; narrated numbers from the ranked sample | VERIFIED | `routers/insights.py` has no filter params and no 400 gate; cache key is `(user_id, prompt_version, model, "any")`; `_PROMPT_VERSION = "endgame_v48"`; `insights_service.py` builds findings from `build_ranked_stats`; `toInsightsFilters` and `_validate_full_history_filters` are gone. Live Shelly smoke matched page numbers |
| 14 | D-05 | Type table uses the ranked sample per TC | VERIFIED | `RankedTcStats` carries type categories; `TypeTable` takes `tcs`; tests pass |
| 15 | D-06 | Time pressure curve and Clock Gap use the ranked sample | VERIFIED | Per-TC quintile curve and `clock_diff_timeline` in the ranked payload; `TimePressureSection` consumes them |
| 16 | D-07 | Computed on read from the canonical slice; CDF-side SQL byte-identical | VERIFIED | `git diff main...HEAD` on `canonical_slice_sql.py` is additive only (`SUB_800_FLOOR`, `ranked_games_sql`); golden-hash and parity tests pass (re-run: 353 passed) |
| 17 | D-08 | No drift or "updating" state | VERIFIED | No "updating" or drift state in `components/endgames` code; `PercentileBar` has only the four statuses |
| 18 | D-09 | Below-floor TC shows "Not enough games to rank yet (N of 30)", no dot | VERIFIED | `rankStatusText` in `PercentileBar.tsx`; component tests pass. Not live-checked (the dev account has no below-floor TC) |
| 19 | D-10 | No TC above floor and empty-sample states | VERIFIED | `EndgameStatsTab.tsx` empty state names rated, human opponents, ±100 Elo, 36 months, links to the Games tab; peers card hides when unranked (tests) |
| 20 | D-11 | Pending and not-ranked-yet slots | VERIFIED | `COPY_PENDING` and `COPY_UNRANKED` in `PercentileBar.tsx`; `MetricsCard` hides the headline when `rate.status === 'pending'`; no new polling |
| 21 | D-12 | Default TC = most ranked games, ties to faster, prefers above-floor | VERIFIED | `pickDefaultTc` in `useEndgameStatsTc.ts`; hook tests pass |
| 22 | D-13 | Choice persisted in `localStorage` with try/catch and fallback | VERIFIED | `readStoredTc` / `setSelectedTc` guard storage and validate the value; UAT confirmed reload restore |
| 23 | D-14 | Switch lists only TCs with at least 1 ranked game, same list in every section | VERIFIED | Backend omits zero-game TCs (ordered bullet..classical); every `TcSwitch` reads `tcs` from the one payload |

**Score:** 22/23 decisions verified; 1 UNCERTAIN (D-00i, warning), 0 FAILED.

### Requirements Coverage (CONTEXT decisions)

No REQ-IDs are registered in REQUIREMENTS.md; the roadmap names D-00a..D-00i and D-01..D-14 as the contract. The union of `requirements:` across plans 01-09 is exactly D-00a..D-00i, D-01..D-14, with none missing and none orphaned. The union of `requirements-completed:` across the SUMMARYs is identical. Every ID has a row in the truth table above.

### Required Artifacts and Key Links

| Artifact / Link | Status | Details |
| --------------- | ------ | ------- |
| `app/services/endgame_ranked_service.py`, `app/repositories/endgame_ranked_repository.py`, `GET /api/endgames/ranked-stats` | VERIFIED | Present, wired in the router, user_id only from `current_active_user`, tested |
| `GET /api/endgames/stats` (filtered, Games tab) | VERIFIED | Router honours filters; router tests pass |
| `EndgameStatsTab.tsx` to `useEndgameRankedStats` | WIRED | Key link pattern present |
| `TcSwitch` to `useEndgameStatsTc` (shared store) | WIRED | |
| `RankedMetricRow` to `PercentileBar` inside `RankedMetricPopover` | WIRED | |
| Retired components (gauge, chip, stat popover/tooltip, old section components) | DELETED | Zero hits outside the gitignored `src/node_modules` vitest cache |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| -------- | ---- | ------ | --------- | ------ |
| `MetricsCard` rate, WDL bar, bracket | `tcStats.metrics`, `tcStats.buckets` | `/ranked-stats` to `fetch_ranked_inputs` (canonical ranked SQL) | Yes, parity-tested against the Stage A/B CTE | FLOWING |
| `PercentileBar` | `metric.percentile` | Persisted `user_benchmark_percentiles` row | Yes | FLOWING |
| Shelly findings | `build_ranked_stats(inputs)` | Same ranked inputs | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Ranked core, parity, golden, router, schema, insights router | `uv run pytest tests/services/test_canonical_slice_sql.py tests/services/test_endgame_ranked_service.py tests/services/test_endgame_ranked_parity.py tests/test_endgames_router.py tests/schemas/test_endgames_schema.py tests/test_insights_router.py -n auto` | 353 passed | PASS |
| Frontend endgames, hooks, pages, charts, lib | `npx vitest run src/components/endgames src/hooks src/pages src/components/charts src/lib` | 206 files, 3560 tests passed | PASS |
| Type-check | `npx tsc -b` | exit 0, no output | PASS |
| Retired-name grep over `frontend/src`, `app`, `tests`, `scripts` | `grep -rn` | Only the gitignored vitest cache matches | PASS |

I did not re-run the full pre-merge gate (the prompt establishes it green; the 238-VALIDATION rows and 238-09-SUMMARY record it). My targeted re-runs agree with it.

### Probe Execution

SKIPPED. The plans declare no probes (no `probe-*.sh`).

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| ---- | ------- | -------- | ------ |
| `useEndgameInsightsState.ts` | Generated report held only in component `useState`; the mutation result is never written to the cached query | Warning | FE-WR-01. Report disappears on remount |
| `PercentileBar.tsx:137` | `formatOrdinal(percentile)` on the unclamped value; backend returns tail values of exactly 0 or 100 | Warning | FE-WR-03. Bar reads "0th" while the dot sits at 1% and the popover says 1%. The `MIN_PERCENT` comment states the intent "no 0th or 100th" |
| `insights_llm.py` `_time_pressure_aggregate_lines` | Falls back to the ungated `RankedMetricOut.value` (can be n=1-2) | Warning | BE-WR-01. A below-floor value can be narrated as "no peer percentile yet" |
| `insights_llm.py` series filters | Keyed on `(metric, subsection_id)` and ignore the new per-TC dimension | Warning | BE-WR-02. One TC's series state can suppress or trim another TC's series in the prompt |
| debt markers (TBD/FIXME/XXX) | Not scanned file-by-file; the stale-reference and lint gates are clean, and the code review found none | Info | No blocker found |

### Review Warning Weighing

- **FE-WR-01 (confirmed by code):** the only warning that touches a stated decision (D-00i, Shelly block unchanged). On `main` the generated state lived in the page, so a Stats to Games round trip kept the report. Now `EndgameStatsTab` unmounts on a tab switch (Radix `TabsContent` plus the `SidebarLayout` tree change), and `useEndgameInsights` has no `onSuccess` cache write. The cached query then serves its pre-Generate value for 5 minutes. The backend report is not lost, so a reload or the staleTime expiry restores it. I rate it UNCERTAIN, not FAILED, because no must-have text asserts persistence across tab switches and the user-visible effect is recoverable. The review's one-line `setQueryData` fix looks sufficient.
- **FE-WR-02:** import completion on a non-Stats page leaves a stale cached report for up to 5 minutes. The server still answers 404 for stale reports on the next fetch. Does not break a truth.
- **FE-WR-03:** cosmetic and consistency, not a verdict contradiction. The same owner observation is in 238-09-SUMMARY. Does not break D-00a.
- **BE-WR-01 and BE-WR-02:** prompt-quality regressions in edge cases (thin below-floor values; multi-TC series). The "narrated numbers equal ranked values" truth still holds, and the live Shelly smoke matched the page. Do not defeat D-04.
- The nine info findings are advisory and break nothing.

### Human Verification Required

1. **Shelly report persistence across tab round trip (FE-WR-01).** Test: Generate on the Stats tab, go to Games, return to Stats. Expected: report still visible. Why human: not covered by any test or by the UAT; owner decides fix-now or accept.
2. **Pressure-curve CI whiskers.** Test: owner decides whether the curve keeps its whiskers. SEED-196 decision 1 and the CONTEXT boundary say whiskers leave the visible UI, the ROADMAP criterion limits it to ranked metrics, and plan 238-05's own success criteria say none remain. The SUMMARY documents a deliberate keep. A small follow-up in `ScoreGapByTimePressureChart.tsx` if removal is wanted (tests assert them today).
3. **Review-warning triage.** All 14 findings in `238-REVIEW-DISPOSITION.md` are still `open`.

Other owner-facing observations already listed in 238-09-SUMMARY: Shelly v48 wording on the 20-40% clock bucket, the Metrics rows repeating the rate next to the bar, no per-TC minimum-games floor on sections, the `knip.json` ignore hint, one serial `uv run pytest -x` before release, and the below-floor TC was never checked live in the browser.

### Gaps Summary

No blocking gaps. The phase goal is met: one percentile verdict per ranked metric on the ranked value, gauges, chips, z-test popover and cross-TC aggregates retired, filter-free Stats tab and Shelly, with the pre-merge gate and UAT recorded green. Resolve or accept the three human items above before the squash-merge. If the owner wants FE-WR-01 fixed, it is a small change (write the mutation result into `['endgame-insights','cached']` and invalidate on import completion in `App.tsx`).

---

_Verified: 2026-10-11_
_Verifier: Claude (gsd-verifier)_

## Owner Resolution (2026-10-11)

All three human items resolved before the squash-merge: FE-WR-01 and the other four warnings fixed (238-REVIEW-DISPOSITION.md), curve CI whiskers kept, owner UAT rounds done (commits baee04cbc..43cdbe723, which also dropped the "Compared to similar-rated players" card). See 238-UAT.md.
