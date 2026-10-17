---
phase: 241-codebase-cleanup
plan: 29
subsystem: frontend-hooks
tags: [cleanup, comments, stockfish, maia, flawchess-engine, gem-sweep]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (ts_scan.mjs, fe_support.py)"
  - phase: 241-03
    provides: "extras.py codemod"
provides:
  - "Eight engine hooks free of planning tags with an empty token diff against PHASE_BASE"
  - "ledgers/241-29.txt covering all 15 INVENTORY rows"
affects: [241-59]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 7dc02e259035727a1f11b80d843ca5d3dcaaedce
plan_head_after: 352a943736806d1c7be17121d57705c2e740e6a9

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-29.txt
  modified:
    - frontend/src/hooks/useStockfishEngine.ts
    - frontend/src/hooks/useStockfishGradingEngine.ts
    - frontend/src/hooks/useMaiaEngine.ts
    - frontend/src/hooks/useFlawChessEngine.ts
    - frontend/src/hooks/useGemSweep.ts
    - frontend/src/hooks/useMaiaEloDefault.ts
    - frontend/src/hooks/useEngineAssets.ts
    - frontend/src/hooks/useFastForward.ts

key-decisions:
  - "SEED-107 and SEED-108 pointers in the useGemSweep header were deleted rather than kept as (see SEED-NNN): they described past supersession of the sweep, not deferred work (both files are still in .planning/seeds/, not seeds/closed/, so a pointer would have looked like open work)"
  - "Bare FIX-N / 'Pitfall N' / 'Plan NN' / 'NNN UAT' labels the scan does not flag were removed too, since they point into .planning/ exactly like the flagged ones"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 29: Engine Hooks Comment Cleanup Summary

**Planning tags and stale references are gone from the Stockfish, Maia, FlawChess Engine, gem sweep and engine-asset hooks; the non-comment token diff against PHASE_BASE is empty.**

## Accomplishments

- First scan of scopes/241-29.txt listed 238 matches in 8 files; final `scan --gate` lists 0.
- All 15 INVENTORY rows have a ledger line (14 APPLIED, 1 MOVED), each re-verified against the code first (D-10).
- Comment-only: `cleanup.py diff` over the scope reports no residue and no directive changes, `eslint .` is clean, `vitest run src/hooks` passes (51 files, 836 tests).

## Task Commits

1. **Task 1: useStockfishEngine, useStockfishGradingEngine, useMaiaEngine (8 rows)** - `756dda058`
2. **Task 2: useFlawChessEngine, useGemSweep, useMaiaEloDefault, useEngineAssets, useFastForward (7 rows)** - `352a94373`

## Codemod vs hand edits

| | Count |
|---|---|
| Codemod (real run over the scope): lines rewritten | 80 in 8 files |
| Codemod: flagged "needs hand edit" | 165 |
| Hand edits via `apply-edits` batches (line-span replacements) | 186 spans |
| Hand edits via Edit/sed (small follow-ups) | 6 |

Every codemod rewrite was reviewed with `git diff -U0`; none had to be reverted. Hand edits overwrote the lines where the codemod left a leftover label that the scan does not flag (`FIX-6:`, `CR-03:`, `WR-02:`, `Item 2:`, `Hotfix 2026-09-06:`, `Phase 171 code review:`, `Quick 260811-u11:`), and the one bad rewrite (`useFlawChessEngine.ts` "//. The values themselves", a dangling period after a removed "(Pitfall 1)").

## Non-inventoried fixes (STYLE-GUIDE 2.2)

- useStockfishEngine: "rather than a bare `new Worker(ENGINE_PATH)`" became `new Worker(path)` (`ENGINE_PATH` no longer exists).
- useMaiaEngine: the dev-cache comment now points at `LIVE_EVAL_CACHE_MAX` in lib/gemMove (it is not in Analysis.tsx); "took ~4 s ... The hook now runs" rewritten in present tense.
- useStockfishGradingEngine: the cap-history sentence became a rule ("don't lower this cap"); the gem-sweep C2 wording was dropped from two comments.
- useFlawChessEngine: the module header no longer claims `pool.stopAll()` is required after an abort (the body comment already says it is redundant defense in depth); the bot-budget comment states the re-export is for the test only.
- useGemSweep: header rewritten as a fallback-only description; the stale `pendingFenRef` name (no longer in useMaiaEngine) became "single-FEN discipline"; the "bug fix" wording around `resolveCandidate` is present-tense.
- useMaiaEloDefault, useEngineAssets, useFastForward: history narration ("is now exported", "used to call", "per checkpoint feedback") turned into current-state wording.
- The directive checker flagged a prose mention of "eslint-disable" inside a comment; the original wording around it is kept so the directive heads match.

## Deviations from Plan

**1. [Rule 3 - Blocking, environmental] `source_scan_tests.sh` python half under `-n 4` collides with other worktrees**
- **Found during:** Step 0 baseline and again at the end.
- **Issue:** parallel wave-3 executors share one Postgres, and the xdist template clone names (`flawchess_test_gw0`) race; the script run failed with `database "flawchess_test_gw0" does not exist` (baseline: 95 errors, then 94 passed + 1 error on a rerun). The frontend half passes both before and after.
- **Fix:** none to the tree. The python half was run serially with the same test list: 95 + 5 passed, identical to the plan 04 baseline. Because `set -e` stops the script at the python failure, the frontend half was run on its own with `--fe` (9 files, 131 tests passed).
- **Files modified:** none.

No other deviations. No behavior, testid, Umami, Sentry, worker URL or storage-key text was touched.

## Known Stubs

None.

## Threat Flags

None. T-241-45 mitigated: `cleanup.py diff` reports zero residue and equal directive heads for all 8 files; lint and hook tests pass. No packages installed beyond the lockfile syncs (`uv sync --group maia-inference`, `npm ci`).

## Self-Check: PASSED

Files verified present: ledgers/241-29.txt and the 8 hooks. Commits `756dda058` and `352a94373` are ancestors of HEAD. `scan --gate`, `diff` and `ledger` exit 0 for scopes/241-29.txt.
