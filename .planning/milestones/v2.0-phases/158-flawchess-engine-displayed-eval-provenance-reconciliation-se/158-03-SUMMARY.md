---
phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se
plan: 03
subsystem: ui
tags: [react, typescript, chess, engine, eval-provenance]

# Dependency graph
requires:
  - phase: 158-01
    provides: measured GRADING_MOVETIME_SAFETY_CAP_MS=4000 + fixed searchmoves-clause-order bug that the shared grading run this plan promotes is built on
  - phase: 158-02
    provides: "engineEvalLookup.ts: buildEvalLookup/getByUci/getBySan, free-run-first-precedence, no pool-grade parameter"
provides:
  - "Analysis.tsx evalLookup memo — the single UCI-keyed eval source every displayed Stockfish eval on /analysis resolves through"
  - "Analysis.tsx reconciledRankedLines memo — parallel RankedLine-shaped display objects (objectiveEvalCp swapped only), RankedLine itself untouched"
  - "Reconciled qualityBySan (classifyMoveQuality fed a reconciled grade map) so the Maia chart's number and severity color agree at bucket boundaries"
  - "Promoted grading run: gated on maiaEnabled || flawChessEnabled, driven by the deduplicated sorted FC∪Maia SAN union"
  - "FC card + agreement verdict now consume reconciledRankedLines — the Qc7-class 'FC pick grades higher than SF best' misread is impossible by construction"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reconciliation lives entirely in Analysis.tsx's memo chain as parallel display objects (never mutating/extending a frozen core type) — the pattern this phase established for merging multiple engine sources without touching search-core contracts."

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "Task 1 and Task 2 committed as one combined commit (ce4c1274) — the memo chain they touch (shownSans -> unionSans -> grading -> evalLookup -> reconciledRankedLines -> qualityBySan -> engineTopLines) is a single interleaved rewrite; splitting it further would have meant editing the same lines twice. Mirrors the 155-04 precedent for interleaved-task commits."
  - "Discovered mid-execution: `git commit -m ... -- <pathspec>` bypasses the index and commits the pathspec's full WORKING-TREE state, not just what was staged via `git add -p`. This swept Task 3's FC-card/verdict JSX wiring (originally staged separately) into the Task 1+2 commit. Verified post-hoc (via `git show`) that no other unintended content leaked in; the final Task 3 commit (ea02c0f7) contains only the Analysis.test.tsx changes, documented honestly in its message rather than silently re-splitting via history rewrite."
  - "qualityBySan's reconciled grade map is built over grading.gradeMap's own SAN keyspace (not a fresh union) — preserves the exact same classification coverage as before reconciliation, just with reconciled values, so no behavior-visible SAN set change."

requirements-completed: [SEED-087]

coverage:
  - id: D1
    description: "The shared grading run is gated on maiaEnabled || flawChessEnabled (not the Maia switch alone) and its candidate set is the deduplicated sorted FC∪Maia SAN union"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Grading run gating (Phase 158, SEED-087 SC2) > runs the shared grading run whenever EITHER switch is on, and stops only when both are off"
        status: pass
    human_judgment: false
  - id: D2
    description: "A move present in both the free run and the grading run displays the free-run value everywhere (evalLookup free-run-first precedence, wired end-to-end through the FC card)"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Reconciled eval provenance (Phase 158, SEED-087) > a move graded by both the free run and the grading run displays the free-run value (SC1 precedence)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The agreement verdict's FC-pick eval and SF-best eval both resolve through evalLookup, so a stale/inflated raw RankedLine eval (the Qc7 +2.8-vs-+1.3 bug class) can never reach the verdict"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Reconciled eval provenance (Phase 158, SEED-087) > the verdict's FC-pick and SF-best evals both resolve through evalLookup, so a stale/inflated raw RankedLine eval never leaks through (SC4)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Maia chart move-quality classification (bucket colors) and the displayed eval number always agree at bucket boundaries, and RankedLine/practical scores/MCTS core remain untouched"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/moveQuality.test.ts (unedited — 0 diff, signature-compatibility proof) + frontend/src/pages/__tests__/Analysis.test.tsx full suite"
        status: pass
      - kind: manual_procedural
        ref: "158-03-PLAN.md <verification> Manual UAT: on /analysis, a move present on all three cards shows one identical number everywhere, including Maia chart line colors; evals settle monotonically without flapping"
        status: unknown
    human_judgment: true
    rationale: "The plan's own <verification> section marks the cross-card visual-consistency check as manual-only (phase gate, VALIDATION.md) — no automated screenshot/visual-diff harness exists for /analysis's live-engine surfaces; the wiring-level equivalent (SC1/SC4) is unit-covered above."

duration: 40min
completed: 2026-07-07
status: complete
---

# Phase 158 Plan 03: Analysis.tsx Displayed-Eval Reconciliation Summary

**Wired the plan-158-02 evalLookup into Analysis.tsx: promoted the shared grading run to gate on `maiaEnabled || flawChessEnabled` over the FC∪Maia SAN union, added `evalLookup`/`reconciledRankedLines` memos, reconciled `qualityBySan`, and threaded reconciled values into the FC card + agreement verdict — making the Qc7-class "FC pick grades higher than the objective best" misread impossible by construction.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-07-07T19:38:22Z (approx, immediately after 158-02's completion commit)
- **Completed:** 2026-07-07T19:52:54Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Exported `FlawChessEngineLines.tsx`'s `MAX_LINES` constant so `Analysis.tsx` sizes the FC-displayed SAN slice from a single source of truth instead of a duplicated literal.
- Promoted the shared Stockfish grading run: it now runs whenever `maiaEnabled || flawChessEnabled` (previously gated on the Maia switch alone), with `fen`/`enabled` always paired on the same OR'd condition (never alive-but-positionless), and its candidate set is `unionSans` — the deduplicated, sorted union of the Maia chart's `shownSans` and the FC card's own top-`MAX_LINES` displayed SANs (`flawChessDisplayedSans`), each gated on its own consumer's switch.
- Added `evalLookup` (`buildEvalLookup(engine.pvLines, grading.gradeMap, position)`) — the single UCI-keyed eval source every displayed Stockfish eval on `/analysis` now resolves through, with free-run-first precedence by construction.
- Added `reconciledRankedLines` — parallel `RankedLine`-shaped display objects (`flawChessEngine.rankedLines.slice(0, MAX_LINES)` with only `objectiveEvalCp` swapped for the `evalLookup` value). The frozen `RankedLine` type and the live MCTS-core snapshots it wraps are never mutated or extended (SC5 scope fence verified: `grep -c "reconciledEvalCp" engine/types.ts` returns 0).
- Reworked `qualityBySan` to classify from a reconciled SAN-keyed grade map (built via `getBySan(evalLookup, position, san)` over `grading.gradeMap`'s own keyspace) instead of the raw grading pass directly — so the Maia chart's move-quality bucket color and its displayed number can never disagree at a boundary (covers the chart line/SAN-label colors, the quality-bar segments, and `positionVerdict`, which all consume this same map).
- Relocated `engineTopLines` after `evalLookup`/`reconciledRankedLines`; its FlawChess-fallback branch (used only when standalone Stockfish is off) now reads `reconciledRankedLines` instead of the raw `flawChessEngine.rankedLines`.
- Threaded `reconciledRankedLines` into the FC card (`FlawChessEngineLines`'s `rankedLines` prop) and the agreement verdict (`FlawChessAgreementVerdict`'s `flawChessLine`/`flawChessRankedLines` props), while `stockfishLine={engine.pvLines[0] ?? null}` stays unchanged (SF side was already free-run-sourced). Both sides of the verdict now resolve through the same `evalLookup`, making the FC-pick-exceeds-SF-best misread structurally impossible.
- Added `Analysis.test.tsx` coverage: a call-capturing `vi.fn()` mock for `useStockfishGradingEngine` (`gradingCalls`), a new "Grading run gating" describe asserting `enabled` across all 4 `(maiaEnabled, flawChessEnabled)` toggle combinations, and a new "Reconciled eval provenance" describe covering SC1 (free-run wins over a stale grading value) and SC4 (a deliberately inflated raw `objectiveEvalCp` of 999 never reaches the verdict sentence — reconciliation always substitutes the `evalLookup` value).

## Task Commits

1. **Task 1 + Task 2 (combined — interleaved memo chain): Promote grading run + resolve evals through evalLookup** - `ce4c1274` (feat)
2. **Task 3: Grading-gating + SC1/SC4 reconciliation test coverage** - `ea02c0f7` (test)

Note: Task 3's `Analysis.tsx` JSX wiring (FC card / agreement verdict props → `reconciledRankedLines`) is included in commit `ce4c1274`, not `ea02c0f7` — see Deviations below.

## Files Created/Modified

- `frontend/src/components/analysis/FlawChessEngineLines.tsx` - exported `MAX_LINES` (was a local, unexported constant)
- `frontend/src/pages/Analysis.tsx` - `evalLookup`/`reconciledRankedLines`/`unionSans`/`flawChessDisplayedSans`/`gradingEnabled` memos, reworked `qualityBySan`, relocated `engineTopLines`, promoted grading call, FC card + verdict prop wiring to `reconciledRankedLines`
- `frontend/src/pages/__tests__/Analysis.test.tsx` - call-capturing grading-hook mock, new gating + SC1/SC4 reconciliation test coverage

## Decisions Made

- **Task 1+2 combined into one commit.** The memo chain they touch (`shownSans` → `unionSans` → `gradingEnabled`/`grading` → `evalLookup` → `reconciledRankedLines` → `qualityBySan` → `engineTopLines`) was written and edited as one contiguous, interleaved block — Task 2's `evalLookup`/`reconciledRankedLines` are built directly on top of Task 1's `unionSans`/`gradingEnabled`. Splitting further would require re-editing the same lines twice for no verification benefit; mirrors the 155-04 SUMMARY's precedent for this exact situation ("topLine/flawChessEngine's mount is inert until Task 2 consumes it, so a Task-1-only commit would fail its own tsc gate").
- **`qualityBySan`'s reconciled grade map is keyed by `grading.gradeMap`'s own SAN set**, not a fresh union — this preserves the exact same classification coverage the pre-reconciliation code had (no behavior-visible SAN-set change), with only the resolved eval values now reconciled.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written for all three tasks' code changes.

### Process Deviation (git commit granularity)

**1. `git commit -m ... -- <pathspec>` bypassed the staged index and committed the full working-tree state of `Analysis.tsx`**
- **Found during:** Committing Task 1+2 — deliberately staged only 4 of 5 `git diff` hunks via `git add -p` (leaving the Task-3-only FC-card/verdict JSX wiring hunk unstaged), then ran `git commit -m "..." -- frontend/src/components/analysis/FlawChessEngineLines.tsx frontend/src/pages/Analysis.tsx`.
- **Issue:** Git's `commit <pathspec>` form ignores the index for the named paths and commits their current *working-tree* content directly — it does not respect a prior partial `git add -p` staging for those same paths. The unstaged 5th hunk (Task 3's `rankedLines={reconciledRankedLines}` / `flawChessLine={reconciledRankedLines[0] ?? null}` / `flawChessRankedLines={reconciledRankedLines}` prop wiring) was swept into commit `ce4c1274` along with the intended Task 1+2 hunks.
- **Fix:** None applied to history — verified via `git show ce4c1274 -- frontend/src/pages/Analysis.tsx` that only the intended Task 1+2 content plus the Task 3 JSX-prop-wiring hunk landed (no other unintended content); the subsequent Task 3 commit (`ea02c0f7`) then correctly contains only the `Analysis.test.tsx` changes. Chose to document this honestly (this section) rather than rewrite history via `git reset`/`git commit --amend`, per the "never use destructive git operations to fix" guidance and "prefer new commits over amending."
- **Files affected:** `frontend/src/pages/Analysis.tsx` (JSX prop-wiring hunk landed one commit earlier than planned)
- **Verification:** `git diff --stat` at HEAD shows zero remaining changes; full `npm run lint && npm test -- --run && npx tsc -b` and `npm run knip` all green at HEAD; the code content itself is 100% correct and matches the plan exactly — only the commit boundary differs from the task-by-task plan.
- **Committed in:** `ce4c1274` (unintentionally includes Task 3's JSX wiring), `ea02c0f7` (Task 3's actual commit, test-file-only)

---

**Total deviations:** 1 process deviation (git commit-pathspec gotcha), 0 code deviations.
**Impact on plan:** None on correctness — all code changes match the plan exactly, full verification suite is green, and every acceptance-criteria grep in the plan passes. Only the git commit boundary between "Task 1+2" and "Task 3" shifted by one JSX hunk; documented transparently rather than papered over.

## Issues Encountered

None beyond the commit-granularity note above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SEED-087 (all 4 observable success criteria: SC1 free-run-first precedence, SC2 OR gating + union candidate set, SC3 reconciled quality classification, SC4 verdict comparability) is now fully wired end-to-end through `Analysis.tsx`; SC5 (scope fence — `RankedLine`/MCTS core untouched) verified via `grep -c "reconciledEvalCp" engine/types.ts` returning 0.
- The plan's own `<verification>` section marks the final cross-card visual-consistency check (a move showing one identical number everywhere, including Maia chart line colors, with evals settling monotonically) as **manual UAT only** (phase gate, VALIDATION.md) — no automated screenshot/visual-diff harness exists for this. This is the one remaining `human_judgment: true` item (D4 above) before Phase 158 can be considered fully closed.
- No blockers for the phase's manual UAT pass.

---
*Phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: `frontend/src/pages/Analysis.tsx`
- FOUND: `frontend/src/components/analysis/FlawChessEngineLines.tsx`
- FOUND: `frontend/src/pages/__tests__/Analysis.test.tsx`
- FOUND commit: `ce4c1274`
- FOUND commit: `ea02c0f7`
