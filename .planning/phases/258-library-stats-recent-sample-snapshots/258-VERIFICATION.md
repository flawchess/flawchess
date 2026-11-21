---
phase: 258-library-stats-recent-sample-snapshots
verified: 2026-11-21T15:35:00Z
status: passed
score: 20/20 must-haves verified
covered_files:
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-01-PLAN.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-01-SUMMARY.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-02-PLAN.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-02-SUMMARY.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-03-PLAN.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-03-SUMMARY.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-04-PLAN.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-04-SUMMARY.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-05-PLAN.md"
  - ".planning/phases/258-library-stats-recent-sample-snapshots/258-05-SUMMARY.md"
  - "CHANGELOG.md"
  - "app/repositories/library_repository.py"
  - "app/routers/library.py"
  - "app/schemas/library.py"
  - "app/services/library_service.py"
  - "frontend/src/components/library/FlawTrendChart.tsx"
  - "frontend/src/components/library/stats/GapPopover.tsx"
  - "frontend/src/components/library/stats/LibraryStatsSections.tsx"
  - "frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx"
  - "frontend/src/hooks/tcSelectionStore.ts"
  - "frontend/src/hooks/useLibraryStatsTc.ts"
  - "frontend/src/lib/__tests__/flawComparisonMeta.test.ts"
  - "frontend/src/lib/flawComparisonMeta.ts"
  - "frontend/src/types/library.ts"
covered_digest: "v4:sha256:c195673afdc527e759d18d511fd6b04c3ad6e930728fdb5fe342306d17bb5988"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 19/19
  gaps_closed:
    - "G-258-3: quiet-TC message qualifier and hint wording (258-05)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open the dev app Stats tab as a user with a TC that has games but none in the last 36 months (user 7, Classic). Read the quiet message with default filters, then with Played as Black"
    expected: "Default filters: 'No classical games in the last 36 months.' With Played as Black: 'No classical games in the last 36 months in the current filters.' Both followed by 'Choose a longer period or a custom range under Recency to include older games.' Plain text, no button, Flaws Timeline below, no tiles or basis line"
    why_human: "Only the copy changed after the owner's UAT; the wording, wrap and placement of the reworded message were checked by string-equality unit tests, not looked at in a running app"
---

# Phase 258: Library Stats Recent Sample for Snapshot Charts Verification Report

**Phase Goal:** Make the Library Stats snapshot charts describe how the player plays now, while the timelines keep the whole career.
**Verified:** 2026-11-21T15:35:00Z
**Status:** human_needed
**Re-verification:** Yes, after gap closure 258-05 (UAT gap G-258-3)

## Goal Achievement

The code delivers the goal. The earlier verification (19/19 decisions, all code-backed) stands: gap closure 258-05 touched only four frontend files (`flawComparisonMeta.ts`, `LibraryStatsSections.tsx` and their two test files; `git diff a9a1c8657 HEAD --stat` over `app/`, `frontend/` and `CHANGELOG.md` shows nothing else), so no backend decision can have regressed. I re-read the 258-05 diff against its must_haves and re-ran the two targeted test files (72 passed). The orchestrator's full frontend run (lint, `tsc -b`, 6740 tests) and the earlier full backend run (7320 passed) were not repeated.

The owner's UAT results (258-UAT.md) cover the earlier human items: basis line variants passed (test 1), quiet TC page passed (test 2), prod performance passed (test 4), and the WR-02 owner decision (test 3) was resolved as "qualifier, with the hint reword", which 258-05 implements. The one remaining human item is a look at the changed quiet message in a running app.

### Gap closure 258-05 must-haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| G1 | With a non-recency sidebar filter active the quiet message reads "No blitz games in the last 36 months in the current filters."; with default filters it stays "No blitz games in the last 36 months." | VERIFIED | `libraryNoRecentGamesText(tc, windowMonths, otherFiltersActive)` builds `...months${samplePlaceText(false, otherFiltersActive)}.`; `samplePlaceText(false, true)` returns " in the current filters", `(false, false)` returns "". Unit tests pin both forms; the component test renders `{...DEFAULT_FILTERS, playedAs: 'black'}`, selects the quiet blitz TC and asserts both paragraphs by `toEqual`. |
| G2 | One `otherFiltersActive`, computed once in `FlawStatsSection`, read by the basis line and the quiet message | VERIFIED | `LibraryStatsSections.tsx:251` `const otherFiltersActive = !areFiltersEqual(filters, DEFAULT_FILTERS, BASIS_FILTER_FIELDS);` is the only `areFiltersEqual(` call in the file; line 279 passes it to `libraryNoRecentGamesText`, line 302 passes it (shorthand) to `librarySampleBasisText`. It sits outside `renderBody`, so no hook-order effect. |
| G3 | Hint reads "Choose a longer period or a custom range under Recency to include older games.", names no preset, plain text, no button, no filter-store write | VERIFIED | `NO_RECENT_GAMES_HINT` has exactly that text; `grep -c '5 years' flawComparisonMeta.ts` is 0. Quiet branch markup is two `<p>` in the `flaw-stats-no-recent` div; the existing component test still asserts no button inside it, and the branch only reads `filters`. |
| G4 | D-16 structure unchanged: one message block (two paragraphs) then the Flaws Timeline; tiles, basis line, "You vs. your opponents" and "Tactic motifs" not rendered for a quiet TC | VERIFIED | The diff leaves the quiet branch markup, testid and `VsOpponentsSection` / `TacticMotifsSection` hiding logic untouched; the 'quiet time control' component tests pass. |
| G5 | Mutation proof: the Played as Black test fails when the quiet branch passes `false` | VERIFIED (SUMMARY, plausible and consistent) | SUMMARY records 1 failed / 53 passed under the mutation, green after restore. I did not re-run the mutation; the test asserts the qualified sentence, which `false` cannot produce, since `samplePlaceText(false, false)` returns "". |

The hard-coded `false` for `recencyFiltered` inside `libraryNoRecentGamesText` is correct: `count_analyzed_by_tc` in `_fetch_flaw_comparison_inputs` runs over the same `filter_kwargs` (including an explicit recency), so a quiet TC (offered but zero window rows) can only occur under the default window. CHANGELOG.md is unchanged by 258-05, and its phase bullet ("keeps its timeline with a note on how to include older games") stays true.

### Observable Truths (decision set D-01..D-19)

Verified in the previous pass against the code and tests; none of the evidence files was touched by 258-05 except for D-13, D-16 and D-17 (re-checked below).

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| D-01 | Split by chart type, `recency: null` default unchanged | VERIFIED | Filter store not in the diff; `FilterPanel.defaults.test.ts` pins `DEFAULT_FILTERS.recency` / `customRange` null. |
| D-02 | Timelines keep full history | VERIFIED | `get_flaw_stats` / `/flaw-stats` untouched; `TestFlawStats::test_trend_full_history`. |
| D-03 | Snapshots always on the recent sample, constants reused | VERIFIED | `RECENCY_WINDOW_MONTHS`, `RECENT_GAMES_PER_TC_CAP` imported from `canonical_slice_sql`; `fetch_recent_window_rows` ranks per TC by `played_at DESC, id DESC`. |
| D-04 | Explicit recency replaces the 36-month bound, cap stays | VERIFIED | `recent_window_start` returns None for any explicit bound; `recency_filtered` in the response. |
| D-05 | Cap counts all filtered games, analyzed is a column | VERIFIED | `test_cap_counts_unanalyzed`. |
| D-06 | One shared windowed set for counts and three comparisons | VERIFIED | `_fetch_recent_window` is the single window entry, ids flow into the aggregates via `game_ids=`. |
| D-07 | No Recent / All games switch | VERIFIED | Router adds only `now_utc`; no toggle in the frontend diff. |
| D-08 | No default +-100 opponent strength | VERIFIED | Built on `_filtered_games_base`; default-filter regression test. |
| D-09 | Tile vs last timeline point difference accepted, no reconciling copy | VERIFIED | No such copy added. |
| D-10 | Facepalm on its own endpoint with JIT off; gates unchanged, applied to the window | VERIFIED | `disable_jit_for_transaction` awaited before the window statement; gate tests on windowed counts. |
| D-11 | Filter first, then cap, colour included | VERIFIED | `test_filter_first_color`. |
| D-12 | Coverage line becomes the single basis line above the tiles | VERIFIED | `CoverageBasisLine` rendered once in `FlawStatsSection`; basis line tests pass after 258-05 (the shared const replaced an identical inline expression). |
| D-13 | Four basis wordings, filter suffix only for non-recency filters | VERIFIED | `librarySampleBasisText` unchanged by 258-05; the quiet message now reuses the same `samplePlaceText` rule and `BASIS_FILTER_FIELDS`. UAT test 1 passed in the dev app. |
| D-14 | Timeline caption "All games in the current filters" | VERIFIED | `FlawTrendChart.tsx` caption plus test. |
| D-15 | TC with games but none in the window stays on the switch | VERIFIED | `counts` (unwindowed) decides offered TCs; `test_quiet_tc`; UAT test 2 passed. |
| D-16 | One message, snapshot sections hidden | VERIFIED | See G4. UAT test 2 passed. |
| D-17 | "All time" untouched; message names the real way out; no button | VERIFIED | Wording now owner-approved (UAT test 3); see G1 to G3. |
| D-18 | No slower than today on the largest prod account | VERIFIED (orchestrator-reported) | UAT test 4: PASS on user 95 and user 28, facepalm plan regression fixed in `e387a6fa3`. |
| D-19 | Measured on prod data, read-only; no index needed | VERIFIED (orchestrator-reported) | No migration in the diff; window EXPLAIN 139 ms / 175 ms using `ix_games_user_played_at`. |
| G-258-3 | Quiet message qualifier and hint (258-05) | VERIFIED | See the gap-closure table. |

**Score:** 20/20 truths verified (0 behavior-unverified, 0 overrides)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/flawComparisonMeta.ts` | three-argument `libraryNoRecentGamesText`, reworded `NO_RECENT_GAMES_HINT` | VERIFIED | Both present; doc comments updated, no em-dash in the strings. |
| `frontend/src/components/library/stats/LibraryStatsSections.tsx` | one `otherFiltersActive` for both lines | VERIFIED | Lines 251, 279, 302. |
| `frontend/src/lib/__tests__/flawComparisonMeta.test.ts` | pins for both forms and the new hint | VERIFIED | Present, pass. |
| `frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | Played as Black quiet-message test | VERIFIED | Present, pass. |
| Backend repository, service, schema, router, `useLibraryStatsTc.ts`, `tcSelectionStore.ts`, `FlawTrendChart.tsx`, `types/library.ts`, CHANGELOG | per 258-01..04 | VERIFIED | Unchanged since the previous verification. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `FlawStatsSection` quiet branch | `libraryNoRecentGamesText` | passes `otherFiltersActive` as third argument | WIRED |
| `FlawStatsSection` basis line | `librarySampleBasisText` | reads the same `otherFiltersActive` const | WIRED |
| router, service, repository, hook, store | as before | unchanged | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Quiet message | `tcStats.tc`, `comparison.data.window_months`, `otherFiltersActive` | API payload and the user's filter state | Yes (window_months comes from the backend constant, filters from the live store) | FLOWING |

Basis line, tiles, facepalm and tactic rows: unchanged from the previous pass, FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Quiet copy and sections | `npm --prefix frontend test -- --run src/lib/__tests__/flawComparisonMeta.test.ts src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | 2 files, 72 passed | PASS |

### Probe Execution

SKIPPED: no `probe-*.sh` is declared by this phase.

### Requirements Coverage

No REQUIREMENTS.md exists. D-01..D-19 from 258-CONTEXT.md are the requirement set; 258-05 declares D-13, D-16, D-17, all verified above. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| 258-05 diff (4 files) | | no TBD / FIXME / XXX / TODO, no new stubs | none | Debt-marker gate clear |

Remaining review items IN-01..IN-07 are info-level and were explicitly out of scope for 258-05; WR-01 and WR-02 are fixed.

### Human Verification Required

1. **Reworded quiet message in the running app.** Test: dev app, user 7, Classic selected on the Stats tab, default filters, then Played as Black. Expected: "No classical games in the last 36 months." (default) or "No classical games in the last 36 months in the current filters." (Played as Black), each followed by "Choose a longer period or a custom range under Recency to include older games." as plain text, no button, Flaws Timeline below, no tiles or basis line. Why human: after the owner's UAT only this copy changed, and no one has looked at it in a running app; the unit tests assert strings, not rendering or wrap.

### Gaps Summary

No gaps. The window is implemented once and shared by all three endpoints (D-01..D-19 verified in the previous pass, backend untouched since). Gap closure 258-05 implements the owner-approved G-258-3 fix exactly: the quiet message follows the basis line's single filter rule, the hint no longer names the five-year preset, the message stays button-free, and the Played as Black test would fail without the fix. The pre-merge gate (root CLAUDE.md) must still run once before the squash-merge to `main`, because the 258-04 run predates 258-05.

---

_Verified: 2026-11-21T15:35:00Z_
_Verifier: Claude (gsd-verifier)_
