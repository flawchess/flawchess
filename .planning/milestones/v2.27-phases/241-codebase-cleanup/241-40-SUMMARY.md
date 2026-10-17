---
phase: 241-codebase-cleanup
plan: 40
subsystem: frontend
tags: [cleanup, comments, typescript, jsx, tombstones, planning-tags]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (ts_scan.mjs, fe_support.py) used for scan, diff and apply-edits"
  - phase: 241-34
    provides: "the lib/botLineTrigger.ts clause of INV-L1288"
provides:
  - "pages/Analysis.tsx and pages/Bots.tsx free of planning tags, moved-to tombstones and stale references, with ledgers/241-40.txt covering all 13 INVENTORY rows"
affects: [241-58, 241-59, 241-65, 241-67, 241-70]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: ea962f4810faf6c06dd38e6b8ef66d15c588a6b9
plan_head_after: 0314e2b5ac5ad944f44a3ad308df25b24b894562

tech-stack:
  added: []
  patterns:
    - "Hand-edit batches built from a helper (temp/241-40/mk.py) that reads the old text from the file by line range, so only the new text is typed; applied bottom-up so earlier line numbers stay valid"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-40.txt
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/Bots.tsx

key-decisions:
  - "Bots.tsx got no codemod run: the dry run produced a '//, so the board ...' collapse and every other tag needed a hand edit anyway, so all 56 sites were hand edited"
  - "The pointer-style comments that say a component 'is extracted to <file>' (AnalysisTabs, AnalysisBoardStage, AnalysisDesktopCards) stay with their 215-06 tags dropped; only the 13 inventoried 'moved to / now comes from' tombstones were deleted, plus two same-shape siblings"

requirements-completed: [D-01, D-04, D-10, D-11, D-12, D-13, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 40: pages/Analysis and pages/Bots Comment Cleanup Summary

**Both largest pages read as current code: all 291 planning-tag matches are gone, 13 "moved to X" tombstones are deleted, and the token diff against PHASE_BASE is empty for both files.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 2
- **Files modified:** 3 (1 ledger created, 2 pages)

## Accomplishments

- `cleanup.py scan` listed 291 matches across the two pages before the work; the final `scan --gate` reports 0.
- Analysis.tsx: the codemod rewrote 75 lines, then 181 hand-edit spans (5 `apply-edits` batches) plus 3 direct edits covered everything it flagged and the non-scannable shapes (`171 UAT`, `Quick NNN`, `T-140-02b`, `162-REVIEW WR-02`, `(item 4)`, `~2,000 lines above`).
- Bots.tsx: 56 hand-edit spans in one `apply-edits` batch.
- All 11 + 2 INVENTORY rows re-verified against the current code (D-10) before applying; see Ledger.
- The two FEN-to-ply helpers stay separate (`fenToRootPly` here; D-04 seed candidate untouched); comments name current identifiers, including the ones 241-58, 241-59 and 241-65 rename later (`useWinCelebrationHold`, `celebrationHold`, `storedTierByPly`, `PlayerBar`, `onHoverPlyChange` are untouched).

## Task Commits

1. **Task 1: pages/Analysis.tsx** - `85af679fd` (`chore(comments): frontend pages/Analysis`, includes the 11-row ledger)
2. **Task 2: pages/Bots.tsx + gates** - `0314e2b5a` (`chore(comments): frontend pages/Bots`, adds the 2 Bots ledger lines)

`commits: 2` above is measured with `git rev-list --count PLAN_HEAD_BEFORE..HEAD` before this SUMMARY commit.

## Ledger (ledgers/241-40.txt)

- Analysis.tsx: INV-L1282, L1283, L1284, L1285, L1286 (APPLIED); L1287 (MOVED); L1332, L1333, L1355, L1366, L1367 (APPLIED)
- Bots.tsx: INV-L1263 (MOVED), INV-L1288 (APPLIED; the botLineTrigger.ts clause was applied by 241-34, already in its ledger as a `#` line, so no extra line is needed here)
- INV-L1366 removed all 13 inventoried tombstones, plus one non-inventoried sibling (the "board-arrow width constants live in useAnalysisBoardArrows" note) and the orphaned "Mobile board row" paragraph that sat above the 2128-2129 tombstone and described a `boardRow` that no longer exists in this file.
- Re-verifications worth naming: INV-L1285's `sm:max-desk3col:` was wrong against App.tsx (it uses `md:max-desk3col:`); INV-L1284's `< 640px` was stale (the constant is `MOBILE_BREAKPOINT_PX` = 768); INV-L1288's "AT its eslint ceiling" has no basis (eslint.config.js has only `max-depth` 4 and report-only cognitive complexity); INV-L1332's four hooks all have `RAPID_STEP_DEBOUNCE_MS = 150` with a `sinceLast > RAPID_STEP_DEBOUNCE_MS` branch and `FAST_FORWARD_STEP_MS` is 200.

## Non-inventoried fixes (STYLE-GUIDE 2.2, comments only)

- `gradeSummaryByFen` no longer exists; the "This replaces the old gradeSummaryByFen race" block became a rule ("Don't cache the C2 grade per FEN: ...").
- Two other history narrations became rules: the eval-chart scrub ("Don't add an off-line guard: ...") and the `perElo.length === 0` completeness proxy.
- File:line pointers (`useStockfishEngine.ts:41/:277-286`, `useGemSweep.ts:269/:428` etc.) and stale counts ("3,600-line page", "2-4 worker pool", "~1,000 lines below") were replaced by names or dropped.
- Glossary row 61: "Human column" / "Human card" in prose became "Maia column" / "column's top card" (testid `analysis-human-column` untouched).
- The corrupt `Quick` / `260714-rj5:` fragments the codemod left in a JSX comment ("keeps the footer visible. Quick collapsed ...") were reworded by hand.
- The codemod left "Phase NNN:" prefixes on about 45 lines (it only drops the parenthetical); all were removed by hand.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-40.txt` | exit 0 (0 blocking) |
| `cleanup.py diff --scope scopes/241-40.txt` | exit 0 (2 selected, 2 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-40.txt --ledger ledgers/241-40.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed (same as the untouched baseline) |
| Python half of `source_scan_tests.sh`, run serially (no `-n 4`) | 95 passed + 5 passed |
| `vitest run src/pages/__tests__/Analysis.test.tsx src/pages/__tests__/Bots.test.tsx` | 149 passed |
| Greps for leftover provenance (`Phase N`, `UAT`, `Quick`, quick-IDs, `NNN-NN`, `D-/WR-/CR-/T-/SC-` shapes, `RESEARCH`, `Pitfall`, `moved to`, `used to`) over both files | only generic words ("previously latched", "no longer legal") remain |
| Leading-punctuation grep `^\s*(#\|//\|\*)\s*[:;,]\s` | no matches |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed.

**2. [Rule 1 - Bug] One of my own apply-edits spans dropped two lines**
- The `Move-list header row content` edit replaced the wrong line range and left a duplicated line and a lost "unconditionally, including ?game_id= game mode" sentence. Found while reviewing `git diff -U0` and fixed in the same task before the Analysis commit.

### Environmental notes

- Per the parallel-execution instructions, the Python half of `source_scan_tests.sh` was run serially without `-n 4`, because sibling executors share the dev Postgres. Reported as environmental, not a plan failure.
- The plan text says "about 283 tagged lines"; the scan counts 291 matches (one per physical comment line).

**Total deviations:** 1 blocking env prep, 1 self-caused edit slip (fixed before commit).
**Impact on plan:** none; no code token, testid, Umami name, URL param or copy changed (the token diff is empty).

## Issues Encountered

- The codemod's "Phase NNN:" leftover shape and its mid-word capitalization (`Max-w-7xl`) needed a pass of hand edits; reading the full diff after each step caught all of them.
- The worktree sandbox rejects compound shell lines with `git` or `cd`; commands were issued one at a time.

## Known Stubs

None.

## Threat Flags

None. Comments only; `cleanup.py diff` compares every token (URL params `?line=`, `?fen=`, `?game_id=`, `?ply=`, testids, Umami attributes and copy are unchanged).

## Notes for downstream plans

- No seed candidates were created. Suspected-bug flags: none.
- The pointer comments saying a component "is extracted to src/components/analysis/..." remain in Analysis.tsx on purpose (they say where something lives, not where it used to live).

## Self-Check: PASSED

Files verified present: ledgers/241-40.txt, frontend/src/pages/Analysis.tsx, frontend/src/pages/Bots.tsx. Commits `85af679fd` and `0314e2b5a` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
