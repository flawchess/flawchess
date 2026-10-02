---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 10
subsystem: engine
tags: [mcts, root-split, gradeRoot, stockfish-pool, arm-A21S]

requires:
  - phase: 226-09
    provides: "Arm A21 (frontend/src/lib/engine/mctsSearch.ts boost-aware clear-winner guard, types.ts BotStopRule.rootGuardBoostAllowance) — the base this plan's arm A21S stacks on"
provides:
  - "Arm A21S engine half (D-18): frontend/src/lib/engine/rootSplit.ts (partitionCandidates, mergeShardGrades, ROOT_SPLIT_MAX_SHARDS), types.ts EngineProviders.gradeRoot?, mctsSearch.ts dispatchExpansion provider-selection routing line"
  - "The Node harness's dormant scripts/lib/stockfish-pool.mjs gradeRoot fan-out (and scripts/engine-grading-depth-ab.mjs's gradeRootAtDepth/gradeRootAtLadder, tooling-committed earlier this phase) now activates for real — stockfish-pool.check.mjs --root-split exits 0 instead of 3"
affects: [226-11, 226-12]

actuals:
  tokens: 4670
  tasks: 2
  commits: 2
  plan_head_before: 4304334a46bc0ddcaaa36402423328e6be559cd7
  plan_head_after: aa77ad1aace608c155287b52f861d945f27f52a3

tech-stack:
  added: []
  patterns:
    - "Optional provider member (EngineProviders.gradeRoot?) selected by a single ternary-then-nullish-coalesce line at the ONE call site that knows leaf.isRoot — every existing/absent-gradeRoot provider stays structurally assignable and byte-identical, matching the grade `signal` optional-param precedent already in this interface"
    - "Fan-out/merge lives entirely BELOW the EngineProviders boundary (rootSplit.ts's pure helpers), so the search orchestrator (mctsSearch.ts) never sees shard count, pool size, or engine identity — only the provider selection"

key-files:
  created:
    - frontend/src/lib/engine/rootSplit.ts
    - frontend/src/lib/engine/__tests__/rootSplit.test.ts
  modified:
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts

key-decisions:
  - "partitionCandidates clamp formula taken verbatim from 226-RESEARCH.md's Code Examples (Math.max(1, Math.min(shardCount, candidateUcis.length))) rather than a hand-derived variant — it already satisfies every Task 2 edge case (k > n, k <= 0, k === n, n === 1, empty input) without a special-cased branch, confirmed by table-walking each case before writing code"
  - "rootSplit.ts imports DESKTOP_POOL_MAX from workerPoolState.ts (a pure module with zero browser-API imports — verified by reading its own header) rather than hardcoding 4, so the harness's ROOT_SPLIT_MAX_SHARDS tracks the app pool's own ceiling if that constant ever changes"
  - "The mctsSearch.ts module-header addition and the dispatchExpansion routing-line comment are the ONLY changes to that file (re-verified via git diff -U0 against the arm A21 commit after both tasks), matching this plan's acceptance criterion and accept-rule.md section 1's A21->A21S content boundary"

requirements-completed: []

coverage:
  - id: D1
    description: "EngineProviders gains optional gradeRoot; dispatchExpansion routes the root's one grade call to it when present, else grade — round barrier, selection, apply order and stop rule untouched"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts 'mctsSearch — gradeRoot routing (Phase 226 D-18)' (3 tests: exactly-once root routing with extraRootMoves union, routing transparency vs a delegating gradeRoot, empty-Map degrade parity)"
        status: pass
      - kind: other
        ref: "git diff -U0 <arm A21 sha> HEAD -- mctsSearch.ts — touches only the module-header note and dispatchExpansion's provider-selection line + comment"
        status: pass
    human_judgment: false
  - id: D2
    description: "rootSplit.ts holds the pure partition/merge helpers shared by the app pool (226-11) and every harness pool, with correct clamping and no-fabrication merge semantics"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/rootSplit.test.ts (11 tests: disjoint round-robin cover + order-restoring merge, k>n/k<=0/k===n/n===1/empty edge cases, missing-candidate no-fabrication, duplicate-key first-shard-wins)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Node harness splits the root grade for real through the same helpers and routing the app will use: stockfish-pool.check.mjs --root-split exits 0, and a real depth-ab smoke records at least one split with zero premise violations per search"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs --root-split (was exit 3/ROOT_SPLIT_ABSENT_MESSAGE before this plan, exit 0/4-of-4-checks-pass after)"
        status: pass
      - kind: other
        ref: "scripts/engine-grading-depth-ab.mjs --nodes 8 --depths 14 --ladder --procs 4 --pool-size 4 on a real 8-legal-move middlegame FEN: root_split_calls=1, root_split_splits=1, root_split_premise_violations=0 on both the d14 and ladder TSV rows"
        status: pass
    human_judgment: false
  - id: D4
    description: "Three mutation checks prove the routing line and merge helper are load-bearing, not just present"
    verification:
      - kind: other
        ref: "Working-tree mutations (a) routing selection deleted, (b) every leaf routed to gradeRoot, (c) mergeShardGrades fabricating a neutral grade for a missing candidate — each reverted, each confirmed to fail its target test before restore, restored file byte-identical (diff exit 0) after"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-29
status: complete
---

# Phase 226 Plan 10: Root Grade Routing and Split Helpers (Arm A21S) Summary

**Optional `EngineProviders.gradeRoot` plus round-robin `partitionCandidates`/`mergeShardGrades` helpers, wired through the one `dispatchExpansion` routing line, activating the Node harness's dormant root-split fan-out end to end.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-09-29T01:12:00Z (approx, session start)
- **Completed:** 2026-09-29T01:52:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- **Task 1** (`feat(226-10): root grade routing and split helpers (arm A21S)`, commit `2f5c4aad3`):
  created `frontend/src/lib/engine/rootSplit.ts` with `ROOT_SPLIT_MAX_SHARDS` (imported from
  `workerPoolState.ts`'s `DESKTOP_POOL_MAX`), `partitionCandidates` (round-robin, `k` clamped to
  `[1, candidateUcis.length]`), and `mergeShardGrades` (original candidate order, never fabricating a
  missing grade). Added `EngineProviders.gradeRoot?` to `types.ts` with a doc comment following the
  `grade`/`signal` optional-param precedent. Changed exactly one line's worth of logic in
  `mctsSearch.ts`'s `dispatchExpansion`: the provider selection becomes `(leaf.isRoot ?
  providers.gradeRoot : undefined) ?? providers.grade`, plus a module-header sentence noting harness
  bit-identity is now per (concurrency, pool size). Before this commit,
  `stockfish-pool.check.mjs --root-split` exited 3 with `ROOT_SPLIT_ABSENT_MESSAGE` (the module didn't
  exist); after, it exits 0 with all 4 checks passing (key-set match, bit-identical manual
  round-robin merge comparison, `rootSplitStats().splits === 1`, zero premise violations). A real
  `engine-grading-depth-ab.mjs` smoke on an 8-legal-move middlegame FEN recorded
  `root_split_calls=1, root_split_splits=1, root_split_premise_violations=0` on both the fixed-depth
  and ladder rows.
- **Task 2** (`test(226-10): gradeRoot routing and split helper tests (arm A21S)`, commit `aa77ad1aa`):
  added `rootSplit.test.ts`'s edge-case coverage (k>n, k<=0, k===n, n===1, empty input for
  `partitionCandidates`; missing-candidate no-fabrication and duplicate-key first-shard-wins for
  `mergeShardGrades`) and a new `mctsSearch.test.ts` describe block proving the routing line is
  load-bearing: a `gradeRoot` spy called exactly once for the root fen with the full root candidate
  set (organic candidates unioned with an injected `extraRootMoves` move); routing transparency
  (identical final snapshot with vs. without `gradeRoot` when it delegates straight to `grade`); and
  an empty non-aborted `gradeRoot` Map degrading exactly like today's empty root `grade()` Map. Three
  mutation checks were performed on the working tree and reverted (details below). `npm run build`
  (tsc -b + vite) and `npm run lint` both clean after the `types.ts` change.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end root split through the harness — helpers, optional provider, routing line** - `2f5c4aad3` (feat)
2. **Task 2: Routing and helper edge-case tests with mutation checks; type-check** - `aa77ad1aa` (test)

**Plan metadata:** (this commit, to follow)

_Note: TDD tasks may have multiple commits (test → feat → refactor). Task 2 carried `tdd="true"` but
per this plan's own `<action>` text the RED/GREEN cycle was test-then-mutation-prove against
already-landed Task 1 code — a single `test(...)` commit, not a separate RED-then-GREEN pair, since
no production code changed in Task 2 (mutation checks were applied and reverted on the working tree
only, never committed)._

## Files Created/Modified

- `frontend/src/lib/engine/rootSplit.ts` - `partitionCandidates` (round-robin partition), `mergeShardGrades` (order-preserving, no-fabrication merge), `ROOT_SPLIT_MAX_SHARDS`
- `frontend/src/lib/engine/__tests__/rootSplit.test.ts` - 11 tests: disjoint round-robin cover + order-restoring merge, all clamp edge cases, no-fabrication and duplicate-key semantics
- `frontend/src/lib/engine/types.ts` - `EngineProviders.gradeRoot?(fen, candidateUcis, signal?): Promise<Map<string, MoveGrade>>`
- `frontend/src/lib/engine/mctsSearch.ts` - `dispatchExpansion`'s provider-selection line + module-header note (D-18/D-08)
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` - new "gradeRoot routing (Phase 226 D-18)" describe block (3 tests)

## Decisions Made

- Used the `partitionCandidates` clamp formula verbatim from `226-RESEARCH.md`'s Code Examples
  (`Math.max(1, Math.min(shardCount, candidateUcis.length))`) after table-walking every Task 2 edge
  case by hand and confirming it satisfies all of them without a special-cased branch — no `|| 1`
  guard needed for the empty-input case, since `Math.min(shardCount, 0)` is never positive.
- Imported `DESKTOP_POOL_MAX` from `workerPoolState.ts` for `ROOT_SPLIT_MAX_SHARDS` rather than a
  hardcoded `4`, after confirming that module has zero browser-API imports (only `type { MoveGrade }
  from './types'`) and is therefore safe to import into a module the Node harness lazy-imports.
- Placed the new `mctsSearch.test.ts` describe block after the existing `ENGINE-07 determinism`
  block (end of file) rather than interleaving it with the `8XN-7` empty-grade block it structurally
  resembles, to keep Task 2's diff a pure append and avoid disturbing surrounding line numbers other
  reviewers/tools might reference.

## Deviations from Plan

None - plan executed exactly as written for both tasks' `<action>` and `<verify>` blocks.

## Issues Encountered

None. The precondition check (arm A21 committed, harness check exits 3) passed on the first read; all
three `<verify>` commands passed on the first run for Task 1; all mutation checks failed their target
test on the first attempt and restored byte-identical on the first revert.

## Owner review required

None. This plan carried no genuine judgment call — every acceptance criterion is either a literal
command output (exit codes, TSV column values) or a `git diff` content-boundary check, and all
resolved unambiguously in the plan's favor.

## Next Phase Readiness

- Arm A21S's engine half is live on this branch: `rootSplit.ts`, `EngineProviders.gradeRoot?`, and the
  one `dispatchExpansion` routing line, all mutation-proven and content-boundary-verified against
  `accept-rule.md` section 1's A21→A21S allowed-file list.
- The Node harness (`stockfish-pool.mjs`, `engine-grading-depth-ab.mjs`) now actually exercises the
  split for real — `--root-split` exits 0 and a depth-ab smoke shows `root_split_calls/splits >= 1`
  with zero premise violations.
- Plan 226-11 (per `226-CONTEXT.md`/`accept-rule.md`'s stacked-arm chain) can now wire the APP side:
  `WorkerPool.gradeRoot` on `workerPoolDispatch.ts`/`workerPool.ts`, and the two hooks
  (`useFlawChessEngine.ts`, `useBotGameEngineDispatch.ts`) that build the app's own `EngineProviders`.
- No gate measurement (throughput, calibration, move quality) was run in this plan — out of scope per
  the plan's own task list; measurement happens once arm A21S is complete on both the engine and app
  sides (accept-rule.md section 3).

## Self-Check: PASSED

- `frontend/src/lib/engine/rootSplit.ts` and `frontend/src/lib/engine/__tests__/rootSplit.test.ts`
  confirmed present on disk with `[ -f ]`.
- Commits `2f5c4aad3` and `aa77ad1aa` confirmed in `git log --oneline --all`.
- `git log -F --grep='(arm A21S)' --format=%s` returns both commit subjects, both containing the
  literal `(arm A21S)` marker.
- `git diff -U0 <arm A21 sha> HEAD -- frontend/src/lib/engine/mctsSearch.ts` re-verified after Task 2:
  still touches only the module-header note and `dispatchExpansion`'s provider-selection line/comment
  (Task 2 added zero production-code lines to this file).
- `npx vitest run` on `rootSplit.test.ts` + `mctsSearch.test.ts` + `mctsSearch.roundFill.test.ts`:
  50/50 passed at HEAD. `npm run build` and `npm run lint` clean at HEAD.
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs
  --root-split`: exit 0, 4/4 checks pass, re-confirmed at HEAD (post-Task-2).
- All three mutation checks (routing-selection deletion, every-leaf-to-gradeRoot, merge fabrication)
  re-confirmed to fail their target test and restore to a `diff`-exit-0 byte-identical state.

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-29*
