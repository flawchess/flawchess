---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 01
subsystem: engine-tooling
tags: [mctsSearch, stockfish, maia, node-harness, d02-measurement, move-quality]

# Dependency graph
requires: []
provides:
  - "scripts/engine-dispatch-stop-rule.mjs --no-stop-rule/--root-trace/--guard-window: the D-02 root-trace measurement input and the D-04 report-only exposure metric"
  - "exported createGradePool from engine-dispatch-stop-rule.mjs, the single Stockfish-pool sendGo mirror other harnesses reuse"
  - "scripts/engine_search_fixes_allowance.py: the D-02 ROOT_GUARD_BOOST_ALLOWANCE calculator (measured p90 or 0.10 fallback)"
  - "scripts/engine-move-quality.mjs: the committed D-13 (amended) maia-blindness move-quality gate, single-arm, both selectors graded"
affects: [225-02, 225-03, 225-04, 225-05, 225-06, 225-07, 225-08]

# Actuals (#2632)
actuals:
  tokens: 13212
  tasks: 2
  commits: 2
  plan_head_before: 5e6164311cf055bfdee8cbcc9b74bb30efbe9a02
  plan_head_after: 6f4df18b5d823946258cecc7b1f90c06ab261288

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "onSnapshot root tracer over RankedLine visits/practicalScore (D-02): a root child's visits flips 0->1 exactly at its own first expansion, so comparing successive snapshots at that flip gives the first-expansion value delta without any engine hook"
    - "Report-only D-04 exposure metric is computed in the same tracer, gated by --guard-window, and never feeds a gate"
    - "createGradePool exported once and reused across measurement scripts instead of re-implementing sendGo"
    - "gradePair (single-selector grading unit) called once per selector so a change in one pick's grade can never leak into the other's MultiPV set"

key-files:
  created:
    - scripts/engine_search_fixes_allowance.py
    - tests/scripts/test_engine_search_fixes_allowance.py
    - scripts/engine-move-quality.mjs
  modified:
    - scripts/engine-dispatch-stop-rule.mjs

key-decisions:
  - "makeRootTracer is module-private in engine-dispatch-stop-rule.mjs (not exported) — only the harness itself needs it; engine-move-quality.mjs never touches the root trace"
  - "D-04 exposure metric reuses the shipped FLAWCHESS_BOT_STOP_RULE.minNodes as its eligibility floor regardless of whether --no-stop-rule is set, since the report question is 'would the guard matter here', not 'is the guard active here'"
  - "es_correct in engine-move-quality.mjs's output always comes from the bot-pick grading pair (never the analysis pair), per plan spec, so the two selectors' verdicts are comparable against one shared correct-move score"

requirements-completed: []

coverage:
  - id: D1
    description: "engine-dispatch-stop-rule.mjs writes a root-trace TSV of first-expansion deltas and a report-only D-04 exposure count, gated by --no-stop-rule/--root-trace/--guard-window"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test"
        status: pass
      - kind: integration
        ref: "real-engine smoke: --dispatch-mode round --no-stop-rule --root-trace --guard-window 0.15 --nodes 12 --elo 1500 over 1 FEN, produced 5 delta rows + exposure 4/5"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/engine_search_fixes_allowance.py turns root-trace TSVs into a per-ELO p50/p90/max table and a pooled-p90 allowance (rounded up to 0.01), falling back to 0.10 below 30 pooled deltas"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_search_fixes_allowance.py (7 tests)"
        status: pass
      - kind: integration
        ref: "uv run python scripts/engine_search_fixes_allowance.py allowance --trace-dir <smoke-dir> -> ALLOWANCE 0.10 (fallback, 5 pooled deltas < D02_MIN_SAMPLES)"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/engine-move-quality.mjs is a committed, self-testing single-arm move-quality runner scoring argmaxLine (judged) and rankedLines[0] (report-only) against fixtures/engine/maia-blindness.tsv, with a required --stop-rule on|off"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test"
        status: pass
      - kind: integration
        ref: "real-engine smoke: 1-row fixture, --arm smoke --stop-rule on --nodes 8, produced a contract-shaped TSV with verdict_bot/verdict_analysis"
        status: pass
    human_judgment: false
  - id: D4
    description: "A corrupted maia-blindness fixture row (illegal move) makes engine-move-quality.mjs refuse to run before any engine spawns (T-225-01)"
    verification:
      - kind: other
        ref: "self-test: temp fixture copy with correct_move corrupted to a1a1 -> validateFixtureIntegrity throws naming the row id, before Maia session/Stockfish pool creation"
        status: pass
    human_judgment: false
  - id: D5
    description: "No file under frontend/src/ changes in this plan"
    verification:
      - kind: other
        ref: "git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src -> empty"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-27
status: complete
---

# Phase 225 Plan 01: Engine Search Fixes Measurement Tooling Summary

**D-02 root-trace tracer + allowance calculator, D-04 exposure metric, and a committed maia-blindness move-quality runner — all engine-code-untouched harness tooling, so A0/A2/A21 share identical instruments.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-27T08:53Z (approx, prior commit)
- **Completed:** 2026-09-27T09:05Z
- **Tasks:** 2
- **Files modified:** 4 (1 modified, 3 created)

## Accomplishments

- `scripts/engine-dispatch-stop-rule.mjs` gained `--no-stop-rule` (omit the budget's stop rule entirely), `--root-trace` (writes `engine-root-trace-*.tsv`, one row per root-child first expansion with pre/post `practicalScore` and delta — the D-02 allowance calculator's input), and `--guard-window` (report-only D-04 exposure metric: an unvisited in-window root child at/after `minNodes`, never a gate). `createGradePool` is now exported so downstream measurement scripts reuse the single Stockfish-pool `sendGo` mirror instead of duplicating it.
- New `scripts/engine_search_fixes_allowance.py` (stdlib-only) turns a directory of root-trace TSVs into a per-ELO p50/p90/max table and computes the D-02 `ROOT_GUARD_BOOST_ALLOWANCE`: pooled p90 rounded up to 0.01 when at least 30 pooled deltas exist (`METHOD measured`), else the pre-registered `0.10` fallback (`METHOD fallback`). 7 pytest cases cover percentile semantics, the round-up float-artifact guard, both allowance branches, multi-ELO TSV loading, and the missing-column error.
- New `scripts/engine-move-quality.mjs`, the committed successor to the deleted 2026-07-31 `engine-wdl-leaf-quality.mjs` adaptation: scores the bot's `argmaxLine` pick (judged) and `rankedLines[0]` (report-only, the pick item 3 changes) per row of `fixtures/engine/maia-blindness.tsv`, each against an independent depth-18 MultiPV grade of the fixture's correct move. `--stop-rule on|off` is required and really switches the search budget. `validateFixtureIntegrity` throws (never `process.exit`) before any engine spawns, so a corrupted fixture row is caught pre-flight and observable from `--self-test`.
- Both harnesses' `--self-test` modes are green (parseArgs edge cases, a pure synthetic tracer check reproducing the plan's exact worked example, and fixture-integrity corruption detection), and both were additionally run end-to-end against real Stockfish/Maia engines to confirm the TSV outputs are contract-shaped, not just self-test-shaped.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end D-02 slice — stop-rule harness root trace to a printed allowance** - `6a69c878` (feat)
2. **Task 2: Committed maia-blindness move-quality runner with explicit selector and stop-rule mode** - `6f4df18b` (feat)

**Plan metadata:** committed alongside this SUMMARY (see below).

## Files Created/Modified

- `scripts/engine-dispatch-stop-rule.mjs` - added `--no-stop-rule`/`--root-trace`/`--guard-window`, `makeRootTracer`, exported `createGradePool`, extended TSV output (root-trace file + trailing columns on the main TSV)
- `scripts/engine_search_fixes_allowance.py` - new D-02 allowance calculator (stdlib-only, `allowance` subcommand)
- `tests/scripts/test_engine_search_fixes_allowance.py` - new pytest coverage (7 tests)
- `scripts/engine-move-quality.mjs` - new committed move-quality runner (D-13 amended)

## Decisions Made

- `makeRootTracer` stays module-private (not exported) — only `engine-dispatch-stop-rule.mjs` itself needs it; `engine-move-quality.mjs` never touches the root trace, only the exported `createGradePool`.
- The D-04 exposure metric's eligibility floor (`minNodes`) always reads the shipped `FLAWCHESS_BOT_STOP_RULE.minNodes`, independent of whether `--no-stop-rule` disabled the stop rule for this run — the report question is "would the guard's window matter at this node count", not "is the guard currently active".
- In `engine-move-quality.mjs`, `es_correct` in every output row is always the bot-pick grading pair's value (never the analysis pair's), per plan spec, so `delta_bot` and `delta_analysis` are directly comparable against one shared correct-move score rather than two independently-graded ones.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>`/`<acceptance_criteria>` blocks were implemented as specified; no Rule 1-4 triggers arose (no bugs found requiring a fix, no missing critical functionality, no blocking issues beyond normal implementation, no architectural changes needed).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. No packages were installed (T-225-SC: not applicable, everything is in-repo stdlib/existing deps).

## Next Phase Readiness

- Plan 225-02 (and later plans running the actual D-02 measurement pass, writing the accept rule, and running the A0/A2/A21 arms) can now use:
  - `scripts/engine-dispatch-stop-rule.mjs --no-stop-rule --root-trace --guard-window <W>` for the real D-02 measurement sweep across the four calibration ELOs.
  - `scripts/engine_search_fixes_allowance.py allowance --trace-dir <dir>` to turn that sweep into the pre-registered allowance value before the accept rule is written (D-02, D-11).
  - `scripts/engine-move-quality.mjs --arm <label> --stop-rule <on|off>` from each detached-worktree arm (A0/A2/A21) for the move-quality gate.
- No blockers. `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` remains empty — confirmed no engine code has moved yet, so A0 (this commit) is still a clean tooling-only baseline (D-12, RESEARCH Pitfall 3).

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- All 4 key files found on disk (`scripts/engine-dispatch-stop-rule.mjs`, `scripts/engine_search_fixes_allowance.py`, `tests/scripts/test_engine_search_fixes_allowance.py`, `scripts/engine-move-quality.mjs`).
- Both task commits (`6a69c8786`, `6f4df18b5`) found in git log.
- Re-ran plan-level `<verification>`: both harness self-tests PASSED, pytest 7/7 PASSED, `uv run ty check app/ tests/ scripts/` all checks passed, `ruff check`/`ruff format --check` clean.
- `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` empty — confirmed.
