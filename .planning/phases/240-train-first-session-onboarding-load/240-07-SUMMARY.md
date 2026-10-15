---
phase: 240-train-first-session-onboarding-load
plan: 07
subsystem: release
tags: [changelog, pre-merge-gate, uat, funnel, train, onboarding]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "plans 01-06 (reveal_tour_stage, first-session order, split tour, two-bubble intro, score bubble, shared spotlight)"
provides:
  - "CHANGELOG [Unreleased] bullets for the lighter first Train session"
  - "Full pre-merge gate green on the integrated phase"
  - "240-FUNNEL-BEFORE.md: prod clean-cohort funnel before the migration ships, plus the adapted after-query"
  - "End-to-end browser walkthrough of a first-ever session (phone 390x844 and 375x667, desktop opening)"
affects: [release, SEED-200 post-deploy read]

requirements-completed: [D-10, D-13]

actuals:
  tasks: 2
  commits: 2
plan_head_before: d3f05e27e
plan_head_after: 9179bb0bd

key-files:
  created:
    - .planning/phases/240-train-first-session-onboarding-load/240-FUNNEL-BEFORE.md
  modified:
    - CHANGELOG.md

key-decisions:
  - "Walkthrough used fresh guests instead of reset_train_state.py on the dev account: a new guest is a genuine first-ever session and the dev account's spaced-repetition state stays intact"
  - "Funnel snapshot read through the query-only flawchess-prod-db MCP (tunnel was already up); aggregate counts only"

status: complete
completed: 2026-10-15
---

# Plan 240-07 Summary: changelog, gate, browser walkthrough, funnel baseline

## Task 1: CHANGELOG and pre-merge gate (c0a001f3d)

Three `### Changed` bullets under `[Unreleased]`, user-facing, no internal names.

Gate, one clean run, no autofix changes:

| Command | Result |
|---|---|
| ruff format app/ tests/ scripts/ analysis/ | 536 files unchanged |
| ruff check . --fix | clean |
| ty check app/ tests/ scripts/ | clean |
| ty check analysis/ | clean |
| check_function_size.py --fail-over-depth 4 | 1223 functions, no breaches |
| pytest -n auto -x | 5490 passed, 19 skipped |
| npm run lint / build / test / knip | clean / clean / 5645 passed / exit 0 (two pre-existing knip.json hints) |

## Task 2: Funnel snapshot (9179bb0bd, orchestrator)

`240-FUNNEL-BEFORE.md` holds the SEED-200 Measure SQL result from prod (alembic head 778c806092fb,
release #424), pulled 2026-10-15: 81 first sessions, 36 abandoned (44%), guest-origin 45% vs
registered 44%; "1 solved, never finished the tour" = 8. Identical to the seed's numbers. The
after-query swaps the old column for `reveal_tour_stage` (`tour_part1_unfinished`, `tour_unfinished`).

## End-to-end browser walkthrough (orchestrator, Chrome, fresh guest)

Phone 390x844 (same-origin iframe), full first session (6 warm-ups):

- Intro: exactly two bubbles (welcome, then "Decide first, then play. Your turn. You play black. Is there only one good move, or several?") before the guess buttons. Pass.
- Order: puzzle 1 `sharp`, puzzle 2 `herring` ("several"), rest sharp. Pass (D-13).
- Reveal 1: part 1, "1 / 2" result strip ("Here only one move was good...") then "2 / 2" Next on the phone bar; pulsing bronze glow (`train-tour-spotlight-pulse`) on each target. Stage -> 1. Pass.
- Reveal 2: part 2, chips then stepping ("1 / 2", "2 / 2"), glow on chips row then move list. Stage -> 2. Pass.
- Reveal 3: part 3, sidelines (board row), understand (`train-lines-tour-target`), Analyze (action bar), "1 / 3".."3 / 3". Stage -> 3. Pass.
- Reveals 4-6: no tour, no spotlight. Pass.
- Score screen: line 1 "Strong session. Practice teaches you when to calculate and when a quick good move is enough." then the warm-up line and the unchanged guest sign-up ask; no returning counts. Pass.
- After: GET /api/train/settings shows `reveal_tour_stage` 3, `sr_explained_at` and `intro_seen_at` set. Pass.
- Phone bar glow: top and sides fully visible; only the outermost halo at the very bottom edge is clipped by the viewport. Readable, pass.

Desktop 1280 wide, opening only (second fresh guest): same two intro bubbles; part 1 desktop variant ("Your result is in the highlighted bubble...") with the glow on `train-verdict-card`. Pass.

Reduced motion: the static `.train-tour-spotlight` override exists inside the `prefers-reduced-motion: reduce` block in the served CSS; not visually emulated.

Screenshots: `temp/uat240/` (gitignored).

## UAT gap

- **375x667 score screen:** for a guest's first warm-up session (green band) the bubble (first line 179 chars plus the guest sign-up ask) pushes "Points: 18/18" (`train-score-total`, y 607-635) under the fixed mobile bottom nav (y 605-666); the 100% badge stays visible. At 390x844 the points line is visible (bottom 635 of 842). The 240-05 worst case (guest with games, red band, 230-char line 1) was not reproduced and would be at least as tight. Whether this was already the case before Phase 240 was not checked. Owner call: accept, or trim/condense the bubble at short viewports.

## Deviations

- The walkthrough used fresh guests, not `reset_train_state.py --user-id N` (see key-decisions).
- SUMMARY written by the orchestrator after the executor's checkpoint return (small job, no continuation agent).
