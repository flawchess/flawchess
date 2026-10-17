---
phase: 241-codebase-cleanup
plan: 32
subsystem: frontend-engine
tags: [cleanup, comments, typescript, engine, mcts, bot-style]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod / decision"
  - phase: 241-04
    provides: "TypeScript support (ts_scan.mjs, fe_support.py)"
provides:
  - "frontend/src/lib/engine search and bot-style modules (19 files) free of planning tags, with ledgers/241-32.txt"
affects: [241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 47fec5ebd794c5fa3495dfbd0007a2f962ddbc79
plan_head_after: 265420348fdcf96e9c2467af7b90b77480b7bab3

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-32.txt
  modified:
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/botStyleBundles.ts
    - frontend/src/lib/engine/botStyle.ts
    - frontend/src/lib/engine/treeCommon.ts
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/selectBotMove.ts
    - frontend/src/lib/engine/fallbackExpectimax.ts
    - frontend/src/lib/engine/botBudget.ts
    - frontend/src/lib/engine/botSampling.ts
    - frontend/src/lib/engine/openingBook.ts
    - frontend/src/lib/engine/deadlineSearch.ts
    - frontend/src/lib/engine/styleOpeningLines.ts
    - frontend/src/lib/engine/select.ts
    - frontend/src/lib/engine/findability.ts
    - frontend/src/lib/engine/backup.ts
    - frontend/src/lib/engine/policyTemperature.ts
    - frontend/src/lib/engine/leafScore.ts
    - frontend/src/lib/engine/guardrail.ts
    - frontend/src/lib/engine/rootSplit.ts

key-decisions:
  - "History narration became a rule where it prevents a regression: selectPath's 'Don't return null here' (collapses the whole fill pass), mctsSearch/botStyle lazy-accessor 'Don't spread a RankedLine', treeCommon hard-cap exemption rationale; 'Before Phase 196' narration was deleted (INV-L1372)"
  - "Closed-seed pointers (SEED-082/098/170/171) were dropped with their tags; no open seed is referenced from these files, so no (see SEED-NNN) pointer remains"
  - "mctsSearch 'claim (a)-(e)' labels (from the continuous-dispatch design) became 'invariant (a)-(e)' to match the (a)-(e) list in the module header instead of dangling into a design doc"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 32: Engine Search and Bot Style Comment Cleanup Summary

**All planning tags are gone from the FlawChess Engine search and bot-style modules (19 files, 485 scanned matches to 0), the 7 INVENTORY rows are applied after re-verification, and the token diff against PHASE_BASE is empty, so search constants, style bundles and budgets are untouched.**

## Accomplishments

- First `scan` over scopes/241-32.txt listed 485 matches in 19 files; final `scan --gate` lists 0.
- Codemod: 219 lines rewritten automatically (147 in the five core files, 72 in the other 14); 283 lines were flagged "needs hand edit". Hand edits: 154 `apply-edits` spans plus 101 single-line substitutions (see Deviations for the substitution helper) plus 9 `sed` one-liners for tags the scanner does not model (`8XN-3`, `Pattern 5`, `R2A-6`, `Y-8`, `quick 260709`, `L-2/L-3`).
- A second sweep with a wider regex (`[A-Z]{2,}-N`, `Pitfall`, `Pattern N`, `RESEARCH`, `Plan N`, `8XN`, `R2A-`, `D-/T-N`, `L-N`) over all 19 files finds nothing.
- Comments that named a stale thing were fixed against the code, not just stripped (see the ledger).

## Task Commits

1. **Task 1: mctsSearch, botStyleBundles, botStyle, treeCommon, types** - `6dc48dbf1` (`chore(comments): frontend lib/engine search and bot style (core)`)
2. **Task 2: the other 14 modules** - `265420348` (`chore(comments): frontend lib/engine search and bot style (rest)`)

`commits: 2` above is measured with `git rev-list --count 47fec5ebd..HEAD` before this SUMMARY commit.

## Ledger (ledgers/241-32.txt)

All 7 rows APPLIED, each re-verified against the code first (D-10):

- INV-L1267: treeCommon.ts hard-cap docblock moved from above `compareCandidateEntries` to directly above `applyRootCandidateHardCap`; the exemption-set bug-fix rationale is kept as a rule.
- INV-L1268: types.ts `RankedLine.objectiveEvalCp` doc now says "of the root candidate (the position after `rootMove`)" (it was "at the modal leaf"; `buildRankedLines` copies it from the root child).
- INV-L1304: botStyle.ts `contempt` doc now says `0.5 + contempt`; `botDrawGate.ts` computes `drawValue = 0.5 + contempt`.
- INV-L1310: openingBook.ts `BookWeightingFn`, `maiaPolicyWeighting` and the floor-check comment describe the shipped style seam (`styleBookWeighting` composes over `maiaPolicyWeighting`).
- INV-L1338: botStyle.ts header list is "Call sites that consume these exports" and `styleBookWeighting` points at `hooks/useBotGameEngineDispatch.ts`'s `resolveBookMove`.
- INV-L1356: rootSplit.ts header no longer says "landing in Plan 226-11" (`workerPoolDispatch.ts` imports and calls the helpers).
- INV-L1372: "Before Phase 196" sentences deleted at both sites in mctsSearch.ts.

Out-of-scope note (ledger `#` comment): `scripts/lib/stockfish-pool.mjs:379` still says "Plan 226-10 has not landed `rootSplit.ts` yet", stale for the same reason as INV-L1356. It is outside scopes/241-32.txt and was left alone.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-32.txt` | exit 0 (19 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-32.txt` | exit 0 (19 selected, 19 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-32.txt --ledger ledgers/241-32.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (also clean on the untouched baseline) |
| `source_scan_tests.sh` | py 95 + 5 passed, fe 9 files / 131 tests passed (same as baseline) |
| `npm --prefix frontend test -- --run src/lib/engine` | 790 passed |

`frontend/src/generated` was not touched. No test file, assertion or code token changed.

## Decisions Made

See key-decisions. Beyond those: the em-dash separators that the original authors used were kept (editing them away is not tag work), and short ragged first lines left by the codemod were left wrapped as the codemod produced them wherever a re-wrap would have touched untagged lines.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fresh-worktree environment prep**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates, which were green.

**2. [Rule 1 - Bug] Codemod produced a broken comment line**
- botStyleBundles.ts: a comment ending `contempt\n// (D-09): an attacker is...` became `contempt\n//: an attacker is...`. Rewritten by hand. `grep` for comment lines starting with punctuation over all 19 files finds none now. Other FE plans should grep for `^\s*(//|\*)\s*[:;,.)]` after running the codemod (the 241-03 summary lists a related guard for the Python side only).

**3. [Plan note] Single-line substitutions via a scratch helper**
- Long single-line JSDoc comments (botStyleBundles.ts) and multi-line wording changes were applied with a scratch `sub.py` and `mk.py` helper (in the gitignored `temp/241-32/`), which wraps `apply-edits` and enforces an exact-occurrence count. The toolkit files were not modified.

**4. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- botStyle.ts: "Task 3" / "added to this file by this phase" / "later plan tasks" provenance dropped; "DEVIATION from openingBook.ts" reworded as a present-tense contrast.
- botBudget.ts: dropped "See 168.5-04-SUMMARY.md" (a `.planning` pointer), kept the measured band numbers; D-19 note became "READ BEFORE RETUNING ANY CONSTANT HERE".
- botStyleBundles.ts: `useBotGame.ts wiring seam` now names `hooks/useBotGameEngineDispatch.ts`; "Plan 03's TRICKSTER_WHITE/BLACK_LINES" now names the real exports.
- types.ts: "frozen for the v2.0 milestone / Phases 154-157" preamble reworded; stale "Fabricated-in-tests-today, real-workers-in-Phase-154 provider surface" now reads as the current provider surface.
- mctsSearch.ts: removed `quick`/`8XN-N`/`R2A-6`/`Y-N` review ids.
- findability.ts: "UNCHANGED by this phase" paragraph rewritten as the standing fact (blend target independent of the curve).

None of these touch code, testids, Umami names, storage keys or URLs.

**Total deviations:** 1 blocking env prep, 1 codemod bug fixed by hand, 2 plan notes. No code behavior changed.

## Issues Encountered

- The worktree sandbox rejected compound shell lines (loops, `$(...)` with git, `&&` chains containing git); commands were issued one at a time.
- Several comments reference design docs that still exist (`reports/continuous-dispatch-227/design.md`, `reports/engine-search-fixes-225/d02-allowance.md`); those are repo files, not `.planning` ids, and were kept.

## Known Stubs

None.

## Threat Flags

None. No network, auth or schema surface was touched; T-241-48 (a search constant changed alongside its comment) is mitigated by the empty token diff (`cleanup.py diff` exit 0 over all 19 files, numeric literals included).

## Self-Check: PASSED

Files verified present: ledgers/241-32.txt and the 19 modified modules. Commits `6dc48dbf1` and `265420348` verified as ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
