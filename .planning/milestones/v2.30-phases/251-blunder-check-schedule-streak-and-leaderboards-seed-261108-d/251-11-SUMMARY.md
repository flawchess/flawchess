---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 11
subsystem: release
tags: [pre-merge-gate, changelog, validation, launch]

requires:
  - phase: 251-01 through 251-10, 251-12, 251-13
    provides: the whole phase tip the gate ran against
provides:
  - "Green full pre-merge gate on the phase tip (backend 7094 passed, frontend 373 files / 6605 tests, lint, build, knip, ruff, ty, nesting depth)"
  - "CHANGELOG [Unreleased] bullets for the all-users blunder check launch, with the beta label dropped"
  - "251-VALIDATION.md with row statuses, dated Gate Results, Follow-ups and the Human Checks list"
affects: [verify-work, ship]

plan_head_before: 4d80b6ae1178c0cbfd97fb4b2aa6ff6b3178bf7d
plan_head_after: 7d7ab954eb9b1d181c5ab116652f7081b98cf2b8

actuals:
  tokens: 6000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - CHANGELOG.md
    - .planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-VALIDATION.md

key-decisions:
  - "Removed the (beta) label from every blunder check bullet in [Unreleased], not only the Added one, so the section no longer contradicts the all-users launch"
  - "Validation rows marked green on the strength of each plan's own recorded run plus the full backend and frontend suites on the phase tip; every -k filter was re-collected and still selects tests"

requirements-completed: []

duration: 25 min
completed: 2026-11-19

coverage:
  - deliverable: "Full pre-merge gate green on the phase tip"
    verification:
      - kind: command
        ref: "uv run ruff format/check, ty (app/tests/scripts and analysis), check_function_size --fail-over-depth 4, uv run pytest -n auto -x (7094 passed, 19 skipped), npm lint/build/test/knip"
        status: pass
    human_judgment: false
  - deliverable: "CHANGELOG [Unreleased] entries for the launch"
    verification:
      - kind: command
        ref: "grep -n 'Blunder check' CHANGELOG.md shows the new bullets in [Unreleased]; grep '(beta)' finds only a v-release line far below"
        status: pass
    human_judgment: false
  - deliverable: "251-VALIDATION.md statuses, Gate Results and Follow-ups"
    verification:
      - kind: command
        ref: "grep -c '^## Gate Results' 251-VALIDATION.md returns 1"
        status: pass
    human_judgment: false
  - deliverable: "D-18 browser launch walk and serial pytest run"
    human_judgment: true
    rationale: "Needs the browser MCP and a long serial run; both belong to the orchestrator and are listed under Human Checks in 251-VALIDATION.md"
---

# Phase 251 Plan 11: Pre-merge gate, CHANGELOG and validation record Summary

**Full pre-merge gate green on the phase tip with no fixes needed, launch CHANGELOG bullets written, and the validation map updated with dated gate results, follow-ups and the orchestrator's human-check list.**

## Performance

- **Duration:** about 25 min (the backend suite alone is 3 min)
- **Tasks:** 2 (tracer gate plus CHANGELOG, validation record)
- **Files modified:** 2

## Accomplishments

- Ran the whole CLAUDE.md pre-merge gate in a fresh worktree (`uv sync --locked --group maia-inference`, `uv sync --project analysis`, `npm ci`). Every step passed on the first run, so no formatter, lint or code fix was needed and no file outside this plan's two was touched.
- CHANGELOG `[Unreleased]`: three new Added bullets (blunder check for everyone including guests, the Puzzles / Blunder check leaderboards with medals, the one-time level choice) and three Changed bullets (two-mode Today card and streak with per-mode sizes and the 7-day cross-mode rest, the Blunder check tab moving to Today with the score-screen hand-off, medal window grouped by week). The old "Blunder check (beta)" Added bullet is replaced, and the beta label is gone from the other blunder check bullets in the section.
- 251-VALIDATION.md: all task rows green, Wave 0 items ticked (`wave_0_complete: true`), new `## Gate Results`, `## Follow-ups` and `## Human Checks` sections. `nyquist_compliant` and `status` are left for `/gsd-validate-phase`.

## Task Commits

1. **Task 1 (tracer): gate green, CHANGELOG** - `1d4657c76` (docs)
2. **Task 2: validation record** - `7d7ab954e` (docs)

## Gate results

| Step | Result |
|------|--------|
| `ruff format app/ tests/ scripts/ analysis/` | 629 files unchanged |
| `ruff check . --fix` | clean |
| `ty check app/ tests/ scripts/` | clean |
| `ty check analysis/` (analysis project) | clean |
| `check_function_size.py app/ --fail-over-depth 4` | 1628 functions, no breaches |
| `uv run pytest -n auto -x` | 7094 passed, 19 skipped, 184 s |
| `npm run lint` / `npm run build` | clean |
| `npm test -- --run` | 373 files, 6605 tests passed |
| `npm run knip` | exit 0 (two pre-existing configuration hints) |
| generated files | no registry behind `scripts/gen_*.py` was touched this phase, so no drift check was needed |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The per-plan commit ledger was written to the worktree git dir at the start of the first commit (`plan_head_before` is the spawn base). `commits: 2` counts the two task commits; the SUMMARY commit follows it.

## Follow-ups (also listed in 251-VALIDATION.md)

- 251-03: `drill_sessions` has no `(user_id, session_date)` index (low urgency). Dev-DB foreign supply at levels 1000 and 2000 is 0 of 18 windows, but a prod probe found about 3.8k to 4.9k evaluated games per +-150 band in a 2% sample, so it is a dev artifact; keep `FOREIGN_SAMPLE_PERCENT`.
- 251-04: an extension can place a second, non-overlapping window on a game already used in the same session (D-01 still holds).
- 251-12: accepted assumption A8: users with a sparse weekday mask who split modes across days can lose that day (about 3.6% of prod). The owner should be aware.
- 251-05 and 251-08: the Phase 249 D-19 analytics-import scan now exempts `BlunderCheckEndScreen.tsx`, `BlunderCheckTab.tsx` and `__tests__`.
- Visual layouts (launcher rows, settings grid, medal dialog weeks, level step, notice, continue button) are human-judgment items for the launch walk.

## For the orchestrator (not done here)

- Launch walk in the browser at 390x844 and 1440 wide with the dev clock, plus a fresh-guest Start path; screenshots to `temp/251-uat/`.
- Serial `uv run pytest` run from its own shell before the release.
- Both are spelled out under "Human Checks" in `251-VALIDATION.md`.

## Known Stubs

None.

## Threat Flags

None. T-251-30 is mitigated by the green gate above; the serial suite remains outstanding for the orchestrator. T-251-SC: no packages were added (the environment setup only synced locked dependencies).

## Self-Check: PASSED

- `CHANGELOG.md` and `251-VALIDATION.md` exist and carry the changes; `grep -c "^## Gate Results"` returns 1.
- Commits `1d4657c76` and `7d7ab954e` are ancestors of HEAD.
