---
quick_id: 260612-bdr
slug: flaws-timeline-default-off-innac-games-a
date: 2026-06-12
---

# Quick Task 260612-bdr

Three Library / Global Stats tweaks:

1. **Flaws Timeline — Inacc. off by default.** Initialize `hiddenKeys` with
   `inaccuracy_rate` so the inaccuracy line starts hidden (it dominates the
   y-axis and buries blunders/mistakes). User can toggle it back on via the
   legend.

2. **Games-analyzed badge → "🖥 x of y Games" + coverage popover.** Replace the
   "📊 31% analyzed · N = 124" pill with a CPU-icon "analyzed of total Games"
   badge plus an `InfoPopover` explaining that full-game Stockfish analysis is
   currently Lichess-only.
   - **Bug found during review:** `total_n` always equalled `analyzed_n`. Cause:
     `count_filtered_and_analyzed` passed the default `flaw_severity`
     (`['blunder','mistake']`) into the base, so the flaw EXISTS restricted the
     denominator to flawed (⇒ analyzed) games. Fix: the coverage badge omits
     `flaw_severity` (true whole-set denominator); the you-vs-opponent
     comparison gate keeps passing it. `analyzed_n` now uses a cheap
     `Game.is_analyzed` hybrid (`white_blunders IS NOT NULL`) instead of the
     expensive per-ply eval-coverage subquery.

3. **Sentry issue 127384361 — eval-chart slider crash.** Pending: needs Sentry
   MCP auth to pull the stack trace before fixing.

## Verification
- Backend: `ruff`, `ty`, full `pytest -n auto` (2520 passed).
- Frontend: `eslint`, `tsc`, `knip`, `vitest` (901 passed).
- Real dev DB confirms analyzed ≪ total per user (e.g. 521/22519).
