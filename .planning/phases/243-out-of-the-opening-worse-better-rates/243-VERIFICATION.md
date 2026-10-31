---
phase: 243-out-of-the-opening-worse-better-rates
verified: 2026-10-31T19:05:00Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-01-PLAN.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-01-SUMMARY.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-02-PLAN.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-02-SUMMARY.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-03-PLAN.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-03-SUMMARY.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-04-PLAN.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-04-SUMMARY.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-05-PLAN.md
  - .planning/phases/243-out-of-the-opening-worse-better-rates/243-05-SUMMARY.md
  - alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py
  - app/data/cohort_cdf.tsv
  - app/repositories/opening_out_repository.py
  - app/repositories/user_benchmark_percentiles_repository.py
  - app/routers/openings.py
  - app/schemas/opening_out.py
  - app/services/canonical_slice_sql.py
  - app/services/endgame_ranked_service.py
  - app/services/global_percentile_cdf.py
  - app/services/opening_insights_constants.py
  - app/services/opening_out_stats_service.py
  - app/services/user_benchmark_percentiles_service.py
  - frontend/src/components/openings/stats/OutOfOpeningPopover.tsx
  - frontend/src/components/openings/stats/OutOfOpeningSection.tsx
  - frontend/src/components/openings/stats/outOfOpeningCopy.ts
  - frontend/src/hooks/useOutOfOpeningStats.ts
  - frontend/src/pages/openings/StatsTab.tsx
  - frontend/src/types/openingOut.ts
  - scripts/gen_global_percentile_cdf.py
covered_digest: "v4:sha256:85058d745658ca2d8181cd1713a2e46d4e27d9a26b9121d01b45f60c9c4adbae"
behavior_unverified: 0
overrides_applied: 0
gaps: []
human_verification:
  - test: "Open /openings Stats tab on the dev stack as a user with a backfilled Stage B (opening rows present). Check the 'Out of the opening' heading and card sit correctly under the desktop sticky White | Black bar (the bar overlays the first heading row), then repeat at 375px width where the colour switch lives in the sticky Filters row."
    expected: "Heading is not clipped or double-stacked by the sticky bar; the worse row reads as primary and the better row as lesser; PercentileBar, hint line and Search popover trigger line up; switching colour swaps the card without layout jump."
    why_human: "243-05 Task 1 human-check, never run. Needs a logged-in dev user with persisted opening rows; the verifier has no dev credentials and will not mint a session. Purely visual alignment; all logic is covered by passing tests."
---

# Phase 243: Out of the Opening Worse/Better Rates Verification Report

**Phase Goal:** Answer "compared to players at my level, how solid am I out of the opening?" on the Openings Stats tab: rank the share of games left clearly worse (primary) and clearly better (secondary) against rating x TC peer CDFs per TC, one game-weighted value per colour.
**Verified:** 2026-10-31
**Status:** human_needed (no gaps; one visual check outstanding)
**Re-verification:** No, initial verification

## Goal Achievement

The goal is achieved end to end in code: a shared SQL builder defines the metric once, the CDF regen script, Stage B and the on-read path all compose it, 252 colour-pooled CDF cells are seeded in the committed TSV, a new authenticated endpoint collapses per-TC percentiles into a game-weighted headline with a 95% gate, and the Stats tab renders the card and popover as its first section. I ran the targeted backend suites (156 passed, including the three-path parity test and the 99%-vs-95% gate tests), the targeted frontend suites (118 passed), `tsc -b`, eslint on the new files, `ruff check` and `ty check` (all clean). I did not re-run the full gate; the orchestrator reports it green.

### Observable Truths (CONTEXT decisions D-01..D-12 as the coverage contract)

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| D-01 | Value = user-POV eval at first middlegame ply minus colour baseline; worse <= -1.0, better >= +1.0; mate by sign; cut is a named constant | VERIFIED | `canonical_slice_sql._opening_out_classified_cte`: DISTINCT ON first `phase = 1` ply, `eval_cp * colour_sign - (baseline)` against `_OPENING_OUT_CUT_CP` derived from `OPENING_OUT_THRESHOLD_PAWNS = 1.0`; baselines derived from `EVAL_BASELINE_PAWNS_WHITE/BLACK`; mate via `sign(eval_mate) * colour_sign`. Boundary cases pinned in `test_opening_out_rates_parity.py::test_counts_match_spec_per_color` (passes, oracle from seed specs, not re-implemented). |
| D-02 | Game ending before middlegame counts by result for resignation/checkmate/timeout; draws and abandoned excluded | VERIFIED | `me.game_id IS NULL` branch uses `_DECISIVE_EARLY_TERMINATIONS` and `result <> '1/2-1/2'`; win test `(result='1-0') = (color='white')`. Covered by the same parity/spec test. |
| D-03 | Copy says "eval", never "pawns" | VERIFIED | `grep -i pawn` over all new frontend files returns nothing; `whatCopy` reads "an eval 1.0 or more below a typical opening position for White". |
| D-04 | One CDF per TC per rate, pooled over colours; 2 new metric ids | VERIFIED | `CdfMetricId` gains `opening_worse_rate`/`opening_better_rate`; cohort key `(metric, anchor, tc)` has no colour; `_compute_and_upsert_opening_cells` ranks both colours against the same cell; TSV holds 252 opening cells x 99 breakpoints = 24,948 rows. ENUM flag from CONTEXT folded in (metric becomes TEXT + CHECK, `test_benchmark_metric_check.py` passes). |
| D-05 | Shared canonical-slice builder; 3000 games / 36 months per TC, rated, +-100, floor 30 per colour x TC for peers and user; filter-independent | VERIFIED | `per_user_cte_opening_out_counts/rate` compose `_recent_capped_per_tc_cte` and `selected_users_cte`; `OPENING_OUT_MIN_GAMES_PER_COLOR = 30` applied in the rate builder and in Stage B; endpoint takes no parameters (`test_openings_out_of_opening.py`: identical body for any query string, 401 unauthenticated). Same anchor/rating-mapping path as Endgames. |
| D-06 | Rank per TC, display collapsed over TC | VERIFIED | Stage B writes per-TC rows; `_ranked_card` collapses over contributing TCs. |
| D-07 | Headline = per-TC percentiles averaged weighted by qualifying games; below-floor TC dropped from headline and gate and listed as below floor | VERIFIED | `weights = e.n / n` over `contributes` entries (`n` = qualifying count from `count(side)`); a TC under the floor has no persisted row so its status is `below_floor` and it is excluded but still listed in `tcs`. Popover carries the averaging disclosure. |
| D-08 | 95% gate: Wilson CI of pooled count excludes weighted peer median, z passed in, Endgames 99% path not reused | VERIFIED | `_wilson_95` -> `wilson_bounds(..., z=OPENING_INSIGHTS_CI_Z_95)`; `peer_p50` weighted with the same weights; direction guard on raw values; orientation applied last. Endgames helpers untouched except two renames to public (`rank_status`, `is_anchor_game`). Below-floor colour state handled via `_unranked_card`. |
| D-09 | No histogram in the popover; follows `RankedMetricPopover` structure | VERIFIED | `OutOfOpeningPopover.tsx`: WHAT sentence, statement + disclosures, per-TC list, `<hr>`, greyed footer; no chart components. |
| D-10 | Per-TC breakdown list (rate, percentile, qualifying games; below-floor TCs listed) | VERIFIED | `tcLineCopy` handles ranked / below_floor / pending / unranked; popover test passes. |
| D-11 | Footer: pooled k of n, peer band, 95% CI | VERIFIED | `footerCopy` emits "k of n games", "95% CI a to b", "peers typically p25 to p75". |
| D-12 | Disclosures: not FlawChess users, ranked games only, filter independence, rating dependence | VERIFIED | `OUT_OF_OPENING_DISCLOSURES` has all four lines plus the averaging line; shown on every popover state. |

Plus the tests contract: three-path parity test (CDF path vs Stage B vs on-read counts) exists and passes; per-eval-source check is report-only (`scripts/opening_out_eval_source_report.py`, tested, not a gate).

**Score:** 12/12 (D-01..D-12) verified; 0 behavior-unverified.

### Required Artifacts / Key Links

| Artifact / Link | Status | Details |
|---|---|---|
| `canonical_slice_sql` builders -> CDF script, Stage B, on-read repo | WIRED | All three import and compose the same builder; parity test proves identical values. |
| `compute_stage_b` -> `_compute_and_upsert_opening_cells` | WIRED | Loops over anchored TCs after the 10 endgame families; cohort prefetch (`load_cohort_cells`, no metric filter) already returns opening cells. Failures captured per TC with Sentry context. |
| `/api/openings/out-of-opening-stats` -> service -> response | WIRED | Router registered; live dev backend answers 401 unauthenticated (route exists). `user_id` from `current_active_user` only. |
| `StatsTab` -> `OutOfOpeningSection(color)` -> hook -> `openingsApi` | WIRED | First section under the sticky bar; query gated on `tier2`; key invalidated on import completion, polling and delete-all. |
| `PercentileBar` significance | WIRED | Receives the server 95% verdict, so red/green requires the gate. |
| Data flow | FLOWING | Counts from `game_positions`/`games` via SQL; percentiles from persisted rows plus seeded CDF; no static fallbacks. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Builder spec, floor, Stage B, three-path parity, read-path matrix, router, CDF regen, seed artifact, CHECK constraint | `pytest -n auto` on 9 targeted files | 156 passed | PASS |
| Section, popover, Openings render, analytics, import invalidation | `vitest run` on 6 targeted files | 118 passed | PASS |
| Types / lint | `tsc -b`, eslint (new files), `ruff check`, `ty check app/ tests/ scripts/` | clean | PASS |

### Anti-Patterns Found

No TBD/FIXME/XXX markers or stubs in phase files. Code-review items below.

### Code Review Findings Assessed (243-REVIEW.md; none block the goal)

| ID | Verdict | Reasoning |
|---|---|---|
| WR-01 | Warning, not a blocker | Real but narrow: a TC is `ranked` from a persisted row while the CURRENT anchor has no CDF cell. Stage B reruns on every import and rewrites the row against the new anchor (percentile NULL gives `unranked`), so the mismatch exists only in the window between Stage A and Stage B or for a sparse cell. The consequence is a misleading "0 of 30" label on one card, never a wrong rank or colour. Recommended fix (treat ranked-but-bandless as `unranked` in `_tc_entry`) is 3 lines. |
| WR-02 | Warning, release-ordering hazard, not a goal gap | Confirmed: opening rows are written only in `compute_stage_b`, so existing users show "Not ranked yet" until their next import/drain. The required steps (migrate, `seed_cohort_cdf`, `backfill_user_percentiles --skip-anchors`) are written in the 243-05 SUMMARY but not in `docs/production-runbook.md` or `bin/deploy.sh`. Seeding is the same manual step prior CDF phases used. Must be done at release or the section is empty for everyone; recommend pinning the order in the runbook before deploy. |
| WR-03 | Warning, not a blocker | `OutOfOpeningSection` checks `isError` before `data`, so a failed background refetch replaces a rendered card with LoadError. UI robustness only; one-line fix (`isError && !data`). |
| IN-01..03 | Info | Confirmed as described (mirrored 1.0 literal with a wrongly named constant in a comment, stale prop doc and test name, `eval_mate = 0` treated as even). None affects the goal. |

Dispositions in `243-REVIEW-DISPOSITION.md` are all still `open`; the orchestrator should triage them (WR-01 and WR-03 are cheap to fix before merge).

### Human Verification Required

#### 1. Sticky-bar alignment and visual hierarchy (243-05 Task 1 human-check)

**Test:** On the dev stack, as a user with persisted opening rows, open the Openings Stats tab on desktop and at 375px. Confirm the "Out of the opening" heading sits correctly under the sticky White | Black bar (desktop) or the sticky Filters row (phone), the worse row reads as primary, and switching colour does not jump.
**Expected:** No clipping or overlap; hierarchy as in sketch 013 Variant A (collapsed).
**Why human:** Needs an authenticated dev session with backfilled opening rows. The dev stack is up (backend 8000, Vite 5173, route answers 401) but the verifier has no dev credentials and will not create a session to get around auth. Rendering logic is covered by passing component tests.

### Gaps Summary

No gaps. Every locked decision D-01..D-12 is honored in code and exercised by passing tests, and the three paths that must agree (CDF regen, Stage B, on-read) are proven identical by a parity test. Status is `human_needed` only because the one visual check from 243-05 was never run. Before releasing, handle WR-02 operationally (runbook ordering plus the manual prod seed and Stage B backfill), and consider fixing WR-01 and WR-03 first.

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_
