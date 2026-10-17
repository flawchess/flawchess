---
phase: 238-endgame-stats-percentile-first
plan: 09
subsystem: verification
tags: [pre-merge-gate, latency, browser-uat, shelly]

requires:
  - phase: 238-07
    provides: filter-free insights, Games tab on /endgames/stats, filter UI hidden on Stats
  - phase: 238-08
    provides: overview retired, zone codegen pruned, CHANGELOG
provides:
  - "Full CLAUDE.md pre-merge gate green on the phase branch"
  - "Final latency on dev users 7 and 14"
  - "Desktop + mobile browser UAT and live Shelly smoke recorded in 238-VALIDATION.md"
  - "G-1 fix: peer-row links scroll to the rendered section on mobile"
affects: []

actuals:
  tasks: 2
  commits: 3

key-files:
  created: []
  modified:
    - .planning/phases/238-endgame-stats-percentile-first/238-VALIDATION.md
    - frontend/src/components/endgames/stats/ComparedToPeersCard.tsx
    - frontend/src/components/endgames/stats/ComparedToPeersCard.test.tsx

requirements-completed: [D-00a, D-00c, D-00e, D-00h, D-02, D-04, D-07, D-09, D-12, D-13]

completed: 2026-10-11
---

# Phase 238 Plan 09: End-to-end verification

Run inline by the orchestrating session (Task 2 needs the Chrome extension).

## Task 1: Gate, latency, stale-reference grep

**Pre-merge gate:** every step exited 0 on the phase branch, and the formatter and autofix changed nothing.
- `ruff format` and `ruff check --fix` are clean.
- `ty` is clean on app/tests/scripts and on analysis.
- The depth-4 gate is clean.
- `pytest -n auto -x`: 5274 passed, 19 skipped.
- Frontend lint and build pass, and knip is clean.
- `npm test`: 318 files, 5337 tests.

**Stale-reference grep:** the final run without exclusions over frontend/src, app/, tests/ and scripts/ prints nothing.

**Latency** (`temp/238-perf/probe_ranked_stats.py`, recreated because the 238-02 original lived in its removed worktree):

```
user=7 runs_ms=951,441,433 median_ms=441
user=14 runs_ms=1878,1049,988 median_ms=1049
```

Both medians are under 2000 ms, so there is no latency flag.

**VALIDATION.md:** I ran each of the 31 automated rows' own commands. Each one selects at least one test and passes, and each row is marked green.

## Task 2: Browser UAT on the dev build plus live Shelly smoke

The account has two ranked TCs (blitz and rapid). Chrome's window would not resize, so the desktop pass ran at a 1576 px viewport. The 800 px and 375 px checks ran in a same-origin iframe of that width.

| Step | Result |
|------|--------|
| 1. Layout | Pass. Shelly first, then peers card, Overall (2 cards + Score Gap over Time + ELO Timeline), Metrics (bracketed WDL bars, no gauges), Time Pressure (grey band, neutral marks, 3 rows), Type table (grey ranges, white ticks, amber only below range, faded rows under 100 games). No horizontal overflow at 800 or 375 px. |
| 2. TC sync and reload | Pass. One click switches every section, and `endgame_stats_tc=blitz` survives a reload. |
| 3. Popover | Pass. WHAT + sign, "Better than 40% of ~1557-rated blitz players", four disclosures, greyed n / CI / p footer. Opens on hover (desktop) and tap (375 px). |
| 4. Below-floor TC | Not checked live: the account has no below-floor TC. Component tests cover it. |
| 5. Peer-row links | Desktop passes. Mobile failed with G-1, fixed in this plan. |
| 6. Filters | Pass. No filter strip or button on Stats. A non-default Games filter (591 of 615 games) is still applied after going to Stats and back. |
| 7. Mobile | Pass. Stacked type rows, tap popover, Filters button only on Games. |
| 8. Shelly | Pass. One Generate with the filter applied; the filter is untouched afterwards. The cached report shows after reload and with the filter active. The narrated rapid values match the page: 48% vs 57%, gap -9% at the 24th percentile, entry +0.37, 719 games, Clock Gap -22% at the 5th. |
| 9. Console | Only React unknown-prop warnings from the `EndgameEloTimelineSection` legend (`ChartLegend content={renderLegend()}`). That code predates this phase and is kept unchanged under D-00i. No errors are new in this phase. |

### G-1 (found and fixed)

**Bug:** peer-row links did not scroll at mobile width. The Stats tab mounts once per layout, so each section id exists twice. `getElementById` returned the desktop copy, which is `display:none` below md.

**Fix:** `jumpToSection` now targets the copy that has a layout box, falling back to the first match where no copy reports one (jsdom has no layout).

**Verification:**
- Added a regression test with a hidden copy and a rendered copy. It fails against the old lookup (mutation check) and passes with the fix.
- Re-verified in the browser at 375 px (3 rows, each reaches its rendered section) and at 1280 px.
- Frontend lint, build and knip are clean, and the full vitest run passes (318 files, 5338 tests).

## Task Commits

1. `4eb41ff7a` docs(238-09): full pre-merge gate green, automated validation rows marked
2. `82f9ed87c` docs(238-09): record browser UAT and live Shelly smoke results
3. `554c945c4` fix(238-09): peer-row links scroll to the rendered section on mobile (G-1)

## Deviations from Plan

- The G-1 fix was made inline at the owner's request ("fix G-1") rather than captured as a gap plan.
- The desktop width was 1576 px instead of 1280 px (window resize had no effect). The 800 px and 375 px checks used same-origin iframes.

## Observations for the owner (not fixed)

- A raw percentile of 0.00 renders as "0th" (blitz Clock Gap).
- Shelly v48 calls the 20-40% clock bucket the "lowest-time situation", though the 10% bucket is lower.
- Open points from 238-05:
  - The pressure curve still shows CI whiskers.
  - The Metrics rows repeat the rate next to the percentile bar.
  - There is no per-TC minimum-games floor on the sections.
- The top-nav logo overlaps "Library" at 800 px. This predates the phase.
- `frontend/knip.json` still ignores `src/generated/endgameZones.ts`, and knip now hints to remove that entry.
- Run one serial `uv run pytest -x` before release (CI runs serially).

## Self-Check: PASSED
