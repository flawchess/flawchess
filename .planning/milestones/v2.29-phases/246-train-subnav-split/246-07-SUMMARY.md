---
phase: 246-train-subnav-split
plan: 07
subsystem: docs
tags: [changelog, readme, pre-merge-gate]
status: complete

requires:
  - phase: 246-train-subnav-split
    provides: "246-06 browser walk evidence and CLEANUP line"
provides:
  - "CHANGELOG [Unreleased] entries for the three Train tabs and the Archive"
  - "README puzzle-training bullet mentions the Archive tab"
  - "Green full pre-merge gate"
affects: []

key-files:
  modified:
    - CHANGELOG.md
    - README.md

requirements-completed: [D-01, D-02, D-04, D-10, D-12]

actuals:
  tokens: 1200
  tasks: 2
  commits: 1
plan_head_before: b07980c18e02f083448c09e28db060a60ea6a160
plan_head_after: 7a86a26f23f817860e829021adeeb4b689e60974
---

# Phase 246 Plan 07: Changelog, README and pre-merge gate

User-facing entries for the Train tabs and Archive are recorded, and the full pre-merge gate is green with no files modified by the formatter or autofix.

## What was done

- **Evidence checks (Task 1 verify)** passed against `246-06-SUMMARY.md` by the measured lines, no owner override was on record: `CLEANUP | seeded=25 deleted=25 remaining=0`, and the API line plus exactly one line for each of STEP 1 to 8 with consistent values (STEP 2 is a recorded FINDING, which the gate accepts). The entries claim nothing about tab position stability, so the open D-15 finding (6.82px tab shift when a long Archive list shows a page scrollbar) is not contradicted.
- **CHANGELOG.md** `[Unreleased]`: an Added bullet (Archive tab, newest first, Analyze opens the game on that position) and a Changed bullet (three tabs, rank one tap from the streak card, schedule card shown in full).
- **README.md**: one sentence appended to the "Personalized puzzle training" bullet saying mastered and parked puzzles stay browsable in an Archive tab.

## Pre-merge gate

| Step | Result |
|------|--------|
| `uv run ruff format app/ tests/ scripts/ analysis/` | 556 files left unchanged |
| `uv run ruff check . --fix` | All checks passed |
| `uv run ty check app/ tests/ scripts/` | All checks passed |
| `uv run --project analysis --with ty ty check analysis/` | All checks passed |
| `scripts/check_function_size.py app/ --fail-over-depth 4` | OK, 1282 functions, no breaches |
| `uv run pytest -n auto -x` | 5694 passed, 19 skipped (85s) |
| `npm run lint` | clean |
| `npm run build` | passed (tsc -b + vite build) |
| `npm test -- --run` | 350 files, 5931 tests passed |
| `npm run knip` | no unused findings (two pre-existing configuration hints only) |

No gate step modified files, so no style/chore commit was needed.

## Deviations from Plan

None - plan executed as written.

Notes, not deviations:
- The evidence gate was run through GNU grep (`PATH=/usr/bin:/bin bash`) because the shell `grep` is `ugrep`, which rejects the backreferences. The regexes were not edited.
- `npm ci` was run in a fresh worktree via `npm ci --prefix frontend`, and `uv sync --group maia-inference` for the backend.
- `vite build` prints two CSS optimizer warnings (`max-w-[var(...)]`, `desk3col:h-[var(...)]`). They come from code comments Tailwind scans (`Analysis.tsx:2697`, `TrainSolveScreen.tsx:1769`, the latter from phase 200), not from this phase. The build succeeds.
- No real-Stockfish flake occurred; the full pytest run passed first time.

## Known Stubs

None.

## Self-Check: PASSED

- CHANGELOG.md: 1 "Archive tab" match under `[Unreleased]`; README.md: exactly 1 match.
- Commit 7a86a26f2 is an ancestor of HEAD.
