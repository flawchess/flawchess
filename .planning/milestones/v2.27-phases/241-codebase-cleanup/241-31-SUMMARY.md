---
phase: 241-codebase-cleanup
plan: 31
subsystem: frontend-hooks
tags: [cleanup, comments, typescript, hooks, tanstack-query]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "extras.py codemod/decision"
  - phase: 241-04
    provides: "fe_support.py + ts_scan.mjs (TypeScript scan and token diff)"
provides:
  - "48 hook files (hooks/analysis/*, board and navigation hooks, data/filter/overlay/misc hooks) free of planning tags, with ledgers/241-31.txt covering all 37 INVENTORY rows"
affects: [241-48, 241-59, 241-60, 241-61, 241-64]

actuals:
  tokens: 21000
  tasks: 2
  commits: 3
plan_head_before: 5315c9f925c06fabf30afe4e213f1312ef7d88df
plan_head_after: e7da163451bf01b856d91d5cadd5519fa75b7966

tech-stack:
  added: []
  patterns:
    - "FE comment plan loop: codemod --dry-run, read the before/after pairs, codemod, scan, hand edit the rest, diff (token stream) + ledger"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-31.txt
  modified:
    - frontend/src/hooks/analysis/useAnalysisBoardArrows.ts
    - frontend/src/hooks/analysis/useAnalysisEngineLines.ts
    - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
    - frontend/src/hooks/analysis/useAnalysisRouteParams.ts
    - frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts
    - frontend/src/hooks/analysis/useBoardStageSize.ts
    - frontend/src/hooks/useAnalysisBoard.ts
    - frontend/src/hooks/useBoardNavigationInput.ts
    - "plus 28 data, filter, overlay and misc hooks under frontend/src/hooks (see files_modified of the plan)"

key-decisions:
  - "INV-L1250 uses the current name storedTierByPly (not storedGemGreatByPly); 241-59 updates the mention when it renames"
  - "Header comments of the analysis hooks were rewritten as present-tense 'why this is a separate hook / what stays in Analysis.tsx and why', not deleted: the ordering constraints (grading/sweep hook call positions) are real design reasons"
  - "useAnalysisBoard.ts no longer mentions the retired Train free-play hook; the silentNavRef rationale is stated as the same-batch loadMainLine + navigating-command case, which the id-keyed claim still serves"

patterns-established: []

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 31: Analysis and Data Hooks Comment Cleanup Summary

**Planning tags, phase narration and stale pointers are gone from 36 hook files under frontend/src/hooks (48 in scope, 12 already clean), all 37 INVENTORY rows are APPLIED with re-verification notes, and the token diff against PHASE_BASE is empty.**

## Accomplishments

- Initial scan of scopes/241-31.txt: 299 matching lines in 48 files. `codemod` rewrote 120 lines (67 in Task 1, 53 in Task 2); the remaining ones and about 25 neighboring provenance lines ("UAT item 4", "Quick 260628-xxx" restated without brackets, "(155 UAT)") were rewritten by hand with the Edit tool.
- Analysis hooks: headers no longer say "Phase 215 Plan 04/05, second of three hooks", "at this point in the phase", or cite 215-04-SUMMARY / 215-PATTERNS / read_first notes. They keep the reasons (why `grading` must be passed in, why `unionSans`, `storedTierByPly`, `fenAtPly` etc. stay in Analysis.tsx, why `BOARD_*_LOCK_MIN_PX` live in useBoardStageSize.ts).
- Data hooks: the flaw-filter doc states what `isFlawFilterNonDefault` checks today; `buildLibraryParams` doc states what it drops and sends; the useLibraryFlaws comment no longer says orientation is omitted when 'either' (the code always sends it); the useGameOverlay header describes the current arrows and glyph overlay.
- Scan --gate, diff and ledger all exit 0 for scopes/241-31.txt; `scan --advisory --gate` also reports 0.

## Task Commits

1. **Task 1: hooks/analysis/*, useAnalysisBoard.ts, useBoardNavigationInput.ts (18 rows)** - `2a37abf26` (`chore(comments): frontend hooks analysis`, includes the ledger with the 18 Task 1 rows)
2. **Task 2: data, filter, overlay and misc hooks (19 rows)** - `aa58a4ec4` (`chore(comments): frontend hooks data and filters`, ledger completed to 37 rows)
3. **Advisory leftovers** - `e7da16345` (two "UAT 179" / "191 UAT" provenance comments that `scan --advisory` flagged)

`commits: 3` above is measured with `git rev-list --count PLAN_HEAD_BEFORE..HEAD` before the SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-31.txt` | exit 0 (48 files, 0 matches) |
| `cleanup.py scan --advisory --gate --scope scopes/241-31.txt` | 0 matches |
| `cleanup.py diff --scope scopes/241-31.txt` | exit 0 (48 selected, 36 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-31.txt --ledger ledgers/241-31.txt` | exit 0, 37 `INV-L` lines |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed (same as untouched baseline) |
| python source-scan tests (listed in the script, run serially) | 95 passed + 5 passed |
| `npm --prefix frontend test -- --run src/hooks` | 51 files / 836 tests passed |

Step 0 baseline (untouched tree): lint and the FE source-scan tests passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates.

**2. [Plan note] Python half of source_scan_tests.sh run serially**
- Run with `-n 4`, the first baseline attempt errored in all 95 tests at database setup (parallel worktrees share the dev Postgres template, a fixture-setup collision, not a test failure). The same test files passed when run serially (95 + 5 passed). This plan changes no Python file; the python half is only relevant because some tests read frontend source text, and none of them reads hooks/.

**3. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- useAnalysisBoardArrows.ts: "the live engine still supplies the grey 2nd" and "gameOverlay.boardArrows ... no longer drawn" narration dropped (INV-L1201 covered the first).
- useGameOverlay.ts header: the first bullet claimed the blue arrow carries the missed-tactic label; the code puts the allowed label on the crimson response arrow and the missed label on the teal should-have-played arrow. Header now matches the code.
- useLibrary.ts useLibraryFlaws: "orientation (omit when 'either')" contradicted the code (always sent); now says it is always sent (INV-L1171).
- useBoardStageSize.ts: the "Checked FIRST against useFitBoardToViewport per the plan's own instruction" provenance was rewritten as the plain reason the hook is not a duplicate.
- useFitBoardToViewport.ts and useBoardStageSize.ts "191 UAT" / "UAT 179" advisory leftovers.
- useEvalCoverage.ts, useGameCount.ts: INV-prescribed deletions of history paragraphs.

**Total deviations:** 1 blocking env prep, 1 plan note, 1 group of stale-content fixes; none touch code, query keys, API params, Umami event names or runtime strings.

## Codemod vs hand edits

| Step | Lines |
|---|---|
| Matching lines at start (scan, 48 files) | 299 |
| Rewritten by `codemod` (Task 1 / Task 2) | 67 / 53 |
| Left for hand edit after codemod | 47 in Task 2 files, about 160 in Task 1 files |
| Hand-edited blocks (Edit tool, one per comment block) | about 150 |

The codemod output was read line by line (dry run first, FE files for the first time); none of the 120 rewrites needed reverting. It leaves residual "Phase 172" / "Phase 238 review" fragments when a tag is the sentence subject, which is why all of those were hand edited.

## Ledger (ledgers/241-31.txt)

37 lines, all APPLIED, each with a one-line re-verification. No row was SKIPPED, MOVED or LEFT. No `#` comment lines for other plans' rows were needed. Notable re-verifications: `NO_GAME_PLY` is no longer defined in Analysis.tsx (its own comment says it moved), `useTacticLine`/Train free-play hooks no longer exist, `MoveListPanel.tsx` still casts `e.target as HTMLElement`, App.tsx uses exactly three user flags.

## Known Stubs

None.

## Threat Flags

None. No package installs beyond the lockfile sync; the TanStack query keys, API param names and Umami events are unchanged (token diff empty, T-241-47).

## Self-Check: PASSED

Files verified present: ledgers/241-31.txt, this SUMMARY, and the 36 modified hook files. Commits `2a37abf26`, `aa58a4ec4`, `e7da16345` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
