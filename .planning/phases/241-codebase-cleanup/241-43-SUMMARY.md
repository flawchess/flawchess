---
phase: 241-codebase-cleanup
plan: 43
subsystem: frontend
tags: [cleanup, comments, typescript, jsx, recharts, planning-tags]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (ts_scan.mjs, fe_support.py) used for scan, diff and the ledger"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "components/charts, components/endgames, components/insights and components/stats free of planning tags and stale provenance, with ledgers/241-43.txt covering all 28 INVENTORY rows"
affects: [241-61, 241-62, 241-67, 241-70]

actuals:
  tokens: 15000
  tasks: 2
  commits: 2
plan_head_before: c4aa38f68df8a0f730a3d3d7674ac4b5a0f5d7bc
plan_head_after: a93c28a369b8406747e61afc6d4c1d6d7b5faee0

tech-stack:
  added: []
  patterns:
    - "Hand edits via a tiny exact-match replace helper (temp/241-43/ed.py) that aborts the whole file if any old string does not match exactly once"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-43.txt
  modified:
    - "34 files under frontend/src/components/{charts,endgames,insights,stats} (comments only)"

key-decisions:
  - "Recharts direct-child rules (series must be direct children of ComposedChart, no wrapping <g>/Fragment) stay as rules; only their UAT/version history and the 2.15.x mechanism were dropped, because the installed recharts is 3.10.1 and whether v3 still drops wrapped series is unverified"
  - "INV-L1012: the source path was fixed to reports/benchmark/benchmarks-latest.md §3.3.3; the value claim ('all 20 cells cap') was not touched, see the report finding below"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~60min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 43: Chart, Endgame, Insights and Stats Components Comment Cleanup Summary

**All 103 planning-tag matches in 41 component files are gone and the charts now state their Recharts rules and data sources without UAT history; the token diff against PHASE_BASE is empty, so no rendering, testid, Umami attribute or copy changed.**

## Accomplishments

- `cleanup.py scan` listed 103 matches in 41 files before the work; the final `scan --gate` reports 0 (and 7 files were found clean, so they stay untouched: ScoreChart.tsx, BracketedWdlBar.tsx, rankedFixtures.ts, EvalCpuPlaceholder.tsx, MiniWDLBar.tsx, RatingChart.tsx, StickyTcBar.tsx).
- 34 files changed. The scan regex also missed 13 further tag lines in the same files (`(post-UAT 88.4)` x4, `Post-UAT (88.4)` x1, `(238 UAT)` x7 incl. ShellyQuote.tsx / EndgameInsightsBlock.tsx / TcSwitch.tsx, `(SC-4)`); they were found by a broad grep and fixed too.
- All 28 INVENTORY rows re-verified against the code and recorded as APPLIED (see Ledger).

## Task Commits

1. **Task 1: components/charts (21 rows)** - `3ab9f5755` (`chore(comments): frontend charts`, includes the ledger with the 21 chart rows)
2. **Task 2: endgames, insights and stats components (7 rows) + gates** - `a93c28a36` (`chore(comments): frontend endgames, insights, stats components`, appends the 7 rows)

`commits: 2` is measured with `git rev-list --count c4aa38f68..HEAD` before this SUMMARY commit.

## Ledger (ledgers/241-43.txt)

APPLIED: INV-L966..L976, L1002, L1003, L1009..L1012, L1016, L1022..L1030, L1040 (28 rows; none MOVED, SKIPPED, LEFT or DEFERRED). Re-verifications worth naming:

- INV-L975: the tab renders four sections (OverallSection, MetricsSection, TimePressureSection, TypeTable); the codemod's intermediate "five" and the original "five" were wrong, now "four".
- INV-L1009: `computeDefaultHidden` no longer exists; the comment now names `computeDefaultHiddenByPrimaryTc`.
- INV-L1011: neither `EndgamePerformanceSection` nor `EndgameScoreGapSection` exists any more.
- INV-L971: MiniBulletChart is used by openingStatsZones/scoreBulletConfig, PositionResultsPanel, OpeningFindingCard, OpeningStatsCard and EvalCpuPlaceholder; no Material Breakdown table.
- INV-L969: the `dates` / `formatDateTick` lines are plain computations, so the "rules-of-hooks" comment was deleted rather than reworded.

## INV-L1012 report finding (for the owner, nothing changed)

`reports/benchmark/benchmarks-latest.md` has `#### 3.3.3 Chess score per pressure bin (per-(TC x quintile))` but no §3.3.3.b. Its recommendation (line 619) says "The cap activates at 14/20 cells (extreme quintiles)", while the code comment in `ScoreGapByTimePressureChart.tsx` (~line 63) still says "all 20 (TC, quintile) cells cap at ±0.06". The path was fixed; the claim and the constants `PRESSURE_SCORE_GAP_NEUTRAL_MIN/MAX` were left alone.

## Codemod vs hand edits

- Codemod (real run over the scope): 29 lines changed in 18 files; 76 lines flagged "needs hand edit". Dry run first; no `//: ...` or leading-punctuation collapses appeared (`grep -nE '^\s*(#|//|\*)\s*[:;,]\s'` over the scope is empty).
- Hand edits: about 75 flagged sites plus the 13 scan-missed lines and the inventoried rewrites, as exact-match replacements (no apply-edits batches; the helper aborts a file on any non-unique match). `git diff -U0` was read in full per task. Two codemod outputs needed fixing by hand ("Phase 238 review: ..." and "238 UAT: ..." stubs, a prop-doc wrap, and a doubled "so" in MetricsCard.tsx).

## Non-inventoried fixes (STYLE-GUIDE 2.2, comments only)

- EndgameClockDiffOverTimeChart.tsx header said the Y-axis label is "Clock diff %"; the JSX renders "Clock Gap". Fixed. Also removed the "legacy bug from the pre-deletion implementation" and "Mirrors the pre-deletion chart" provenance.
- EndgameEloTimelineSection.tsx: swatch comment said "all three PR/Actual lines"; now "all three ELO lines". The `.planning/notes` pointer and the "PR on endgame games" wording were dropped (INV-L967 / L1023).
- EndgameScoreOverTimeChart.tsx, EndgameEloTimelineSection.tsx: the four `(Pattern 3 in 57.1-RESEARCH.md)` pointers and `Recharts Pitfall 1` references were dropped; the rules they supported (bars pinned to the bottom 20%, `x` must match a date) stay.
- ScoreGapByTimePressureChart.tsx: "do not re-flag" text-xs note became "User-directed: keep `text-xs` here"; the Recharts 3 hidden-axis explanation is kept as behavior.
- MiniBulletChart.tsx: `invertColors` doc says "bullets where a negative delta = better performance (e.g. flaw deltas)" (no non-test consumer passes it).
- `legacy [-domain, +domain] mapping` became `[-domain, +domain] mapping`.
- Left on purpose: `WHY (FLAWCHESS-AG)` in EndgameInsightsBubble.tsx (a Sentry issue id on a bug-fix comment, not a planning tag).

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-43.txt` | exit 0 (41 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-43.txt` | exit 0 (41 selected, 34 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-43.txt --ledger ledgers/241-43.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline also clean) |
| `npm --prefix frontend run check:activity-layout` | OK at 320/360/390/414px |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed (baseline identical) |
| Python half of `source_scan_tests.sh`, run serially without `-n 4` | 95 passed + 5 passed |
| `vitest run src/components/{charts,endgames,insights,stats}` | 23 files, 314 tests passed |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed.

**2. [Plan note] scan misses some tag shapes**
- See Accomplishments: 13 extra lines were found by a broad grep and fixed in scope. No identifier, testid, copy or code token changed.

### Environmental notes

- Per the parallel-execution instructions the Python half of `source_scan_tests.sh` ran serially (no `-n 4`) because sibling executors share the dev Postgres. Reported as environmental, not a plan failure.
- The worktree sandbox rejects compound shell lines with `git` or `$(...)` file lists; the charts-only gate used a scope file (`temp/241-43/charts.txt`) instead of command substitution.

**Total deviations:** 1 blocking env prep, 1 plan note. **Impact on plan:** none; the token diff is empty.

## Known Stubs

None.

## Threat Flags

None. Comments only; `cleanup.py diff` compares every JSX/TS token (Recharts structure, `mpo-*` / `clock-diff-*` testids, `data-window`, Umami attributes and copy are unchanged).

## Notes for downstream plans

- No identifier renamed: `BulletConfidencePopover`, `WdlConfidenceTooltip`, `hasMgEval` (241-61), `matchingInsights`, `rendered`, `window`, `barChartData`, `MIN_PERCENT`, `vsEngineValue` (241-62) are untouched; comments use the current names.
- The test files beside these components (`*.test.tsx`, e.g. `Phase 238 validation row D-00a` headers and titles) are not in this scope and still carry tags; they belong to the test-cleanup plans.

## Self-Check: PASSED

Files verified present: ledgers/241-43.txt, this SUMMARY. Commits `3ab9f5755` and `a93c28a36` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
