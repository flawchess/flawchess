---
phase: 239-library-stats-you-vs-opponents
plan: 09
subsystem: testing
tags: [pre-merge-gate, uat, changelog, smoke]

requires:
  - phase: 239-07
    provides: accepted zone registries
  - phase: 239-08
    provides: tactic tables
  - phase: 239-10
    provides: You vs. your opponents section
provides:
  - Green pre-merge gate on the phase branch
  - CHANGELOG [Unreleased] bullets for the Library Stats redesign
  - Live per-TC API smoke with latencies
  - Desktop + phone browser UAT record in 239-VALIDATION.md
affects: [release]

actuals:
  tasks: 2
  commits: 3

key-files:
  modified:
    - CHANGELOG.md
    - .planning/phases/239-library-stats-you-vs-opponents/239-VALIDATION.md
    - frontend/src/components/library/stats/TacticTables.tsx
    - frontend/src/components/library/stats/__tests__/TacticTables.test.tsx

key-decisions:
  - "Tactic table grid uses fr tracks (24fr/38fr/38fr) instead of percentages so the md:gap-4 gutters no longer overflow the card"

requirements-completed: []

duration: ~45min (inline, orchestrator)
completed: 2026-10-13
---

# Phase 239 Plan 09: Pre-merge gate, changelog, smoke and UAT Summary

**Gate green, one UAT layout bug found and fixed (tactic Allowed icon clipped), smoke matches the accepted registries.**

Run inline by the orchestrator, since the browser UAT needs the Chrome tools that executor subagents lack.

## Task 1: pre-merge gate, stale-reference sweep, CHANGELOG, validation map

- ruff format (530 files unchanged), ruff check, ty (app/tests/scripts and analysis/), nesting-depth gate (1,193 functions, no breaches): all clean.
- `uv run pytest -n auto -x`: 5390 passed, 19 skipped.
- Frontend: lint clean, build clean, 329 files / 5578 tests passed, knip clean.
- Stale-reference grep: the only hits are `tests/scripts/test_chapter5_sql.py:35` and `tests/services/test_flaw_delta_zones.py:37`, both negative tests that assert `hasty_miss` / `low_clock_miss` are absent. Kept on purpose (see Deviations).
- CHANGELOG: five Library Stats bullets under [Unreleased] → Changed. They say the tactic ranges are new and do not claim the flaw ranges moved (owner kept the live flaw bands at the 239-06 checkpoint).
- 239-VALIDATION.md: every map row points at an existing test file with its plan/task ID, all green.

Commit: 59a506250

## Task 2: live smoke and browser UAT

Smoke (`temp/239-uat/smoke.py`, read-only, exit 0):

```
user_id=28 analyzed_games=2864
accepted viable tactic set size=9
hasty rapid band=-0.28/0.18
flaw  tc=blitz     analyzed_n= 1000 below_gate=False bullets=12 low_sample=0
      hasty band=-0.28/0.18
flaw  tc=rapid     analyzed_n= 1841 below_gate=False bullets=12 low_sample=0
      hasty band=-0.28/0.18
tactic tc=blitz     analyzed_n= 1000 below_gate=False bullets=38 has_zone=9 low_sample=29
tactic tc=rapid     analyzed_n= 1841 below_gate=False bullets=38 has_zone=9 low_sample=26
trend tc=blitz     points=37
trend tc=rapid     points=89
latency flaw_comparison=424ms tactic_comparison=395ms flaw_stats=61ms
```

Browser UAT: steps 1-5, 7 and 8 pass (details in 239-VALIDATION.md). Step 6 (below-gate slot) could not be reached live, because no preset recency window gives 1-19 analyzed games for the owner's dev account; it stays covered by component tests.

## Deviations

- **[Rule 1] UAT bug fixed (d800d6838):** `TacticTables` used `md:grid-cols-[24%_38%_38%]` with `md:gap-4`, so rows were 32 px wider than the card and the card's `overflow-hidden` clipped the Allowed column's search icon at every desktop width. Switched to `24fr_38fr_38fr`; the class-pinning test was updated. jsdom cannot see layout, so this was verified in the browser (icon now inside the card).
- **Stale-reference acceptance grep:** two hits remain by design. They are negative tests guarding against the retired metrics coming back, and deleting them would weaken coverage.
- **Smoke script setup:** the script imports `app.main` so every ORM mapper is registered (importing the services alone fails on the `games.user_id → users` FK), and it runs with `PYTHONPATH=.`.
- **Phone viewport:** the Chrome window could not be resized, so the 375 px checks ran in a same-origin iframe.

## Self-Check: PASSED
