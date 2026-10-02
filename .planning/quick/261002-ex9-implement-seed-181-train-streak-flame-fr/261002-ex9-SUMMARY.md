---
quick_id: 261002-ex9
status: complete
seed: SEED-181
branch: quick/seed-181-streak-flame (worktree ../flawchess-seed181)
commits: [c00aafce1, b85459c9d, 6b2799d7d]
---

# Quick 261002-ex9 Summary: Train streak flame + freezes (SEED-181)

## What shipped
- **Streak flame hero** (`TrainStreakCard`): the session streak inside a 3-layer concentric flame
  (sketch 005 A), grey outline at 0; "Session streak" heading with the explainer popover, the
  weekly tally, a "Freezes" row, and the Start/Resume button. On phones the button spans the card
  under the flame row; from `sm:` up it sits beside the flame (sketch 006 A).
- **Freezes** (`FreezeMeter`): the 0-7 `shield_level` buffer as lucide snowflakes in icy blue;
  explainer copy rewritten ("Every completed session earns a freeze (7 max)…"). API field and
  `train-shield-*` testids unchanged.
- **Arrival animations** (`lib/streakArrival.ts`): per-account (profile email), per-device
  localStorage snapshot diffed on landing mount: ignite + count-up on a streak tick, crack + frost
  on freezes used, pop-in on freezes earned, extinguish on a reset (the old lit flame gutters into
  its base after the last freeze cracks, then the grey 0 fades in; added at review), nothing on a
  first visit. Resolved in a layout
  effect (no flash) with a ref guard (StrictMode). Off under prefers-reduced-motion.
- **Puzzle pool** as stat tiles (Mastered, Parked, Points today when completed).
- **Schedule card** collapses to a disclosure header with a live summary ("Mo–Fr · 6 puzzles ·
  16:00"); save indicator and the next-session line stay visible while collapsed.

## Verification
- Frontend gate: `npm run lint`, `npm run build`, `npm test -- --run` (4488 + new tests), `npm run knip`: all clean.
- Mutation check: removing the quiet-reset guard fails both the unit and the card test.
- Browser (worktree Vite on :5174, local guest): hero at 375px (via same-origin iframe) and at
  desktop width; freeze-used path confirmed live (2 cracking halves, frost cool-down at 1.2s);
  found and fixed a 2px Start-label overflow at 375px.

## Deviations
- Planned and executed inline in the worktree rather than via planner/executor subagents
  (subagents start in the main checkout where phase 227 is active).
- Score tile reads "14/18 · Points today" instead of "Scored today 14 of 18 points"; tests updated.
- `Train.solveLoop` regression test now allows the streak snapshot key in localStorage (the test
  guards that the SCORE never comes from storage).
- `TrainStatRow` deleted (no remaining users). `ToggleChipButton` colors untouched (shared with
  FilterPanel; the screenshot's "all grey" days were simply all selected).
