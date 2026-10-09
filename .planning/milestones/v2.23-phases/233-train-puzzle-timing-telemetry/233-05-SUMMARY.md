---
phase: 233-train-puzzle-timing-telemetry
plan: 05
subsystem: ui
tags: [privacy, changelog, telemetry, vitest, pre-merge-gate]

requires:
  - phase: 233-train-puzzle-timing-telemetry
    provides: "plans 01-04: server telemetry column and review route, client think/review timing, engagement counters"
provides:
  - "Privacy page 'What we collect' item disclosing Train timing, solution engagement and device class (D-09)"
  - "Rendered-page Privacy test pinning the disclosure wording"
  - "CHANGELOG [Unreleased] Changed bullet for the telemetry"
  - "Phase-wide pre-merge gate green with plans 01-05 applied"
affects: []

actuals:
  tokens: 2600
  tasks: 2
  commits: 2
plan_head_before: 4cb21b10ae684e813e4acb52ec66a357e3e936f7
plan_head_after: 82efa6056dd15f4aedfee4bcbe8f86e5d5cb7f95

tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - frontend/src/pages/__tests__/Privacy.test.tsx
  modified:
    - frontend/src/pages/Privacy.tsx
    - CHANGELOG.md

key-decisions:
  - "D-08 and D-10 are confirmed by absence: TrainLeaderboardCard.tsx and frontend/src/lib/analytics.ts are untouched by the whole phase, and the existing tab-switch test covers the Points/Accuracy toggle"

requirements-completed: [D-08, D-09, D-10]

coverage:
  - id: E1
    description: "Privacy page names Train timing, solution engagement and the phone-or-computer class, and that hidden time is not counted"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Privacy.test.tsx#names the device class and that hidden time is not counted"
        status: pass
    human_judgment: false
  - id: E2
    description: "No leaderboard impression event and no Umami review event were added; the existing hand-switch tab-switch test passes"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#a hand switch sends tab-switch once with the leaderboard target"
        status: pass
      - kind: command
        ref: "git diff --stat f492f2b0a..HEAD -- TrainLeaderboardCard.tsx analytics.ts (empty); D08-D10-OK"
        status: pass
    human_judgment: false
  - id: E3
    description: "CHANGELOG [Unreleased] carries the user-facing telemetry bullet"
    requirement: "D-10"
    verification:
      - kind: command
        ref: "awk over [Unreleased] | grep 'Train now records how you work through each puzzle' (CHANGELOG-OK)"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-10-05
status: complete
---

# Phase 233 Plan 05: Privacy disclosure, CHANGELOG and phase gate Summary

**One Privacy "What we collect" item telling users Train records think time, solution study time (visible only), which solution parts they open and phone-or-computer class, pinned by a rendered-page test, plus the CHANGELOG bullet and a green full pre-merge gate across both stacks.**

## Performance

- **Duration:** ~7 min
- **Completed:** 2026-10-05
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 3 (1 created, 2 modified)

## Accomplishments

- Tracer (Task 1): the new `<li>` sits right after the Train leaderboard item in `Privacy.tsx`; "Last updated: October 2026" is unchanged. `Privacy.test.tsx` renders `PrivacyPage` under `MemoryRouter` and asserts both "whether you trained on a phone or a computer" and "only while the page is visible" in the `privacy-page` text. Mutation proof: changing the source phrase to "whether you used a device" turned the test red; restored, green.
- Task 2: D-08 and D-10 confirmed without code. The existing `TrainLeaderboardCard.test.tsx` (45 tests) passes, including "a hand switch sends tab-switch once"; no `IntersectionObserver` in the card, no `'train-review'` in `analytics.ts`, and `git diff --stat` of both files across all phase 233 commits is empty. CHANGELOG bullet added under `[Unreleased]` -> `### Changed`.

## Pre-merge gate (all run once, after plans 01-05)

| Step | Result |
| ---- | ------ |
| `ruff format app/ tests/ scripts/ analysis/` | 515 files unchanged |
| `ruff check . --fix` | All checks passed, no files modified |
| `ty check app/ tests/ scripts/` | All checks passed |
| `ty check analysis/` (analysis venv) | All checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1125 functions, no breaches |
| `pytest -n auto -x` | 5197 passed, 19 skipped |
| `npm run lint` | clean |
| `npm run build` (tsc -b + vite) | success |
| `npm test -- --run` | 5146 passed |
| `npm run knip` | clean (one pre-existing configuration hint about .css) |

No gate step modified files, so no style/chore commit was needed.

## Task Commits

1. **Task 1 (tracer): Privacy page discloses Train timing, engagement and device class** - `2b05e76d0` (feat)
2. **Task 2: CHANGELOG bullet and phase-wide gate** - `82efa6056` (docs)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. T-233-18 (no analytics duplication) and T-233-21 (undisclosed behavioral data) are mitigated as planned.

## Manual-only checks (not run here)

Per plan verification: on a dev build, close the tab on a reveal, switch tabs on a reveal, click a nav link away from a reveal, and leave via Analyze without returning; each should land `exit = 'pagehide'` in `drill_solves.telemetry`, and a return plus Next should overwrite it with `exit = 'next'`. Left for the phase verifier / human UAT.

## Self-Check: PASSED

- `frontend/src/pages/__tests__/Privacy.test.tsx` exists; commits `2b05e76d0` and `82efa6056` are on the branch; `commits:` measured from the plan ledger (2).
- PRIVACY-LINE-OK, D08-D10-OK, CHANGELOG-OK all printed.
