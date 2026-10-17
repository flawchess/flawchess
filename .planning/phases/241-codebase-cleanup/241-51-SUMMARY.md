---
phase: 241-codebase-cleanup
plan: 51
subsystem: frontend-tests
tags: [cleanup, comments, test-titles]
requires: [241-01, 241-02, 241-03, 241-04]
provides: ["Component tests (outside components/train) free of planning tags in comments and describe/it titles"]
affects: [frontend/src/components, frontend/src/types/api.test.ts]
key-files:
  modified:
    - "90 test files under frontend/src/components (see scopes/241-51.txt)"
decisions: []
status: complete
commits: 2
plan_head_before: 52b5ce101ebe7d3e8b6979553b172102e1a46bb7
plan_head_after: b72d9a337278615b267810bf7a946b559baa12dd
actuals:
  tokens: 40000
  tasks: 2
  commits: 2
---

# Phase 241 Plan 51: Frontend component test comment and title cleanup Summary

Stripped planning tags (Phase/Plan/D-NN/quick-task/SEED/UAT/Pitfall references) from comments and describe/it titles in 90 component test files outside components/train, with test bodies, assertions, testid queries and vi.mock paths untouched.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | analysis, bots, board, charts component tests | 0ecfad0c9 | 41 files changed |
| 2 | library, results, insights, stats, endgames, filters, settings and remaining component tests | b72d9a337 | 49 files changed |

## Results

- `cleanup.py scan --gate --scope scopes/241-51.txt`: 100 files, 0 matches, 0 blocking.
- `cleanup.py diff --scope scopes/241-51.txt`: passes (only comments and normalized test titles differ).
- `npm --prefix frontend test -- src/components src/types`: 128 files, 1984 tests passed.
- `npm --prefix frontend run lint`: clean. `npm --prefix frontend run build` (tsc -b + vite): passes.
- `source_scan_tests.sh`: 95 + 5 backend and 131 frontend tests passed.
- The test count is unchanged: only title literals and comments were edited (enforced by `cleanup.py diff`); no `it`/`describe` was added or removed.

## Rewritten titles

About 225 describe/it/test titles lost a trailing or leading tag. The full old -> new list is the title lines of `git diff 52b5ce101..b72d9a337 -- frontend/src`. Pattern: the tag was removed and the behavior wording kept, e.g.

- `'shows the second hint line when the viewer finished #12 last week (D-03)'` -> `'shows the second hint line when the viewer finished #12 last week'`
- `'renders at most maxLines rows (Phase 228, D-16)'` -> `'renders at most maxLines rows'`
- `describe('Phase 77 - Troll-opening inline icon')` -> `describe('Troll-opening inline icon')`
- `describe('260508-r61 - Score cell info-icon popover')` -> `describe('Score cell info-icon popover')`
- `describe('MoveStats - D-01/D-02 accuracy strip')` -> `describe('MoveStats - accuracy strip')`
- `describe('Phase 129 D-11: orientation-prefixed dual-chip matrix (TACUI-07)')` -> `describe('orientation-prefixed dual-chip matrix')`

Comments that were provenance only (e.g. `// 260507-t4r: the proseLine with .toFixed(1) fallback is gone.`, trailing `// Phase 76 D-21`) were deleted; comments carrying a why were reworded without the tag.

## Deviations from Plan

**1. [Salvage] Task 2 resumed from a partial diff.** The previous executor died mid-Task 2 before committing. Its 49-file uncommitted diff was applied with `git apply` from `temp/241-51/task2-partial.patch` (read only), every hunk was reviewed against STYLE-GUIDE §2.1/§3.3, and the scope gate was then run over all 100 files: 0 matches remained, so no further Task 2 files needed edits. Task 1 (0ecfad0c9) was verified (scan clean, tests pass) and not redone. A few multi-line header comments remain with slightly short wrapped lines after tag removal; left as is (cosmetic, no Prettier).

**2. [Rule 3 - env]** Fresh worktree: ran `npm --prefix frontend ci` (lockfile reinstall, no new packages) because `ts_scan.mjs` could not load TypeScript.

Codemod vs hand-edit split was not tracked by the dead executor for Task 1; Task 2's patch was predominantly hand-edited comment/title rewrites (49 files, 475 changed diff lines).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- 0ecfad0c9 and b72d9a337 are ancestors of HEAD.
- scan --gate and diff exit 0 over scopes/241-51.txt; vitest, lint, build and source-scan tests pass.
