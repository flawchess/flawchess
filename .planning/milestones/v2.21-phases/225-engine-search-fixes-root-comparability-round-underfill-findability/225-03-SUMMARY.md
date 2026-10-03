---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 03
subsystem: engine-tooling
tags: [d02-measurement, root-guard-allowance, accept-rule, pre-registration, calibration]

# Dependency graph
requires:
  - phase: 225-01
    provides: "scripts/engine-dispatch-stop-rule.mjs --no-stop-rule/--root-trace/--guard-window (the D-02 measurement harness) and scripts/engine-move-quality.mjs (the move-quality runner referenced in accept-rule.md)"
  - phase: 225-02
    provides: "scripts/engine_search_fixes_verdict.py's frozen constants (THROUGHPUT_MAX_WALL_RATIO, MQ_REGRESSION_MARGIN, STOP_RULE_MAX_WALL_MS, STOP_RULE_MIN_EARLY_STOP_RETENTION, CALIBRATION_NEAR_MISS_FRACTION), which accept-rule.md transcribes verbatim, and its pinned per-arm data layout"
provides:
  - "reports/engine-search-fixes-225/d02-allowance.md: measured ROOT_GUARD_BOOST_ALLOWANCE A = 0.04, guard window W = 0.09, per-ELO table, method, caveats"
  - "reports/engine-search-fixes-225/accept-rule.md: the pre-registered decision contract for the whole gate (arms, exact commands, data layout, criteria in evaluation order, calibration branch table, item ship/hold decisions, prohibitions) — its add-commit is arm A0"
  - "reports/data/engine-search-fixes-225/d02/: 4 root-trace TSVs, 4 stop-rule TSVs, allowance.json (committed, method measured)"
affects: [225-04, 225-05, 225-06, 225-07, 225-08]

# Actuals (#2632)
actuals:
  tokens: 13380
  tasks: 3
  commits: 3
  plan_head_before: 21171aa296037d1a3371d2ee26421f7ac1fc6317
  plan_head_after: 1b5313b9648d9be1116bb519a1d51e8627f3ec15

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-02 design input measured and committed strictly before the accept rule, and the accept rule committed strictly before any gate arm — the plan's own two-gate ordering invariant (D-11), verified by acceptance checks that no reports/data/engine-search-fixes-225/{a0,a2,a21,final,calibration} path exists yet"
    - "Accept rule as a decision contract with grep-checkable numbers: every threshold in accept-rule.md is transcribed verbatim from scripts/engine_search_fixes_verdict.py's frozen constants, so a future reader (or a CI grep) can verify the doc and the twin never drifted apart"

key-files:
  created:
    - reports/engine-search-fixes-225/d02-allowance.md
    - reports/engine-search-fixes-225/accept-rule.md
    - reports/data/engine-search-fixes-225/d02/allowance.json
    - reports/data/engine-search-fixes-225/d02/engine-root-trace-round-elo1300-stopoff-2026-09-27T07-11-49-647Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-root-trace-round-elo1500-stopoff-2026-09-27T07-15-13-091Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-root-trace-round-elo1900-stopoff-2026-09-27T07-18-29-407Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-root-trace-round-elo2300-stopoff-2026-09-27T07-21-21-689Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-dispatch-stop-rule-round-elo1300-stopoff-2026-09-27T07-11-49-647Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-dispatch-stop-rule-round-elo1500-stopoff-2026-09-27T07-15-13-091Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-dispatch-stop-rule-round-elo1900-stopoff-2026-09-27T07-18-29-407Z.tsv
    - reports/data/engine-search-fixes-225/d02/engine-dispatch-stop-rule-round-elo2300-stopoff-2026-09-27T07-21-21-689Z.tsv
  modified: []

key-decisions:
  - "D-02 allowance is 0.04 (measured, not fallback): pooled p90 0.0344991 over 338 first-expansion deltas across ELO 1300/1500/1900/2300, rounded up to 0.01. Guard window W = 0.05 + 0.04 = 0.09 — the value every stop-rule gate command below passes via --guard-window and the value Plan 225-05 sets as FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance."
  - "accept-rule.md's calibration section operationalizes D-13 amended's fail-branch exactly per RESEARCH C-6: primary A21-vs-July fails/void routes to the 'decision' branch (run A0+A2, a0_vs_july decides baseline_drift, missing/void counts as not-holds); primary holds but near-miss (>75% of its own threshold in either family) routes to 'report-only' (attribution recorded, no gate effect); primary holds cleanly routes to 'none' (no further calibration runs needed)."
  - "Item 1 (root comparability guard) can only ship if item 2 (round underfill) also ships — A21 always includes item 2, so item 1 was never measured in isolation. Item 3 (findability fallback) ships independently of every bot gate once its own unit tests are green (D-14)."

requirements-completed: []

coverage:
  - id: D1
    description: "D-02 ROOT_GUARD_BOOST_ALLOWANCE measured (not fallback) at ELO 1300/1500/1900/2300 over the 16-position stop-rule set with no stop rule, recorded with method, per-ELO table, tooling commit SHA, and caveats in d02-allowance.md before the accept rule was written"
    requirement: null
    verification:
      - kind: other
        ref: "python3 -c \"import json;d=json.load(open('reports/data/engine-search-fixes-225/d02/allowance.json'));print(d['method'],d['allowance'])\" -> measured 0.04"
        status: pass
      - kind: other
        ref: "grep -E '^.*A = [0-9]+\\.[0-9]{2}' reports/engine-search-fixes-225/d02-allowance.md && grep -c 'W = ' reports/engine-search-fixes-225/d02-allowance.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "accept-rule.md committed before any gate data exists, is a decision contract (not narrative), and transcribes scripts/engine_search_fixes_verdict.py's frozen constants verbatim; its add-commit is arm A0 and changes only this one file"
    requirement: null
    verification:
      - kind: other
        ref: "git log --diff-filter=A --format=%H -- reports/engine-search-fixes-225/accept-rule.md -> exactly one SHA (1b5313b96); git show --stat -> 1 file changed"
        status: pass
      - kind: other
        ref: "grep -c pinned-threshold checks (12,100 / 1.05 / 0.75 / (225-04) / sweep-225-a21 / engine_search_fixes_verdict.py) all >=1"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/scripts/test_engine_search_fixes_verdict.py tests/scripts/test_engine_search_fixes_allowance.py -x (33 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "No file under frontend/src/, scripts/, or bin/ changed by this plan; no gate-data directory (a0/a2/a21/final/calibration) exists at A0"
    requirement: null
    verification:
      - kind: other
        ref: "git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src -> empty; ls reports/data/engine-search-fixes-225/ -> only d02/"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-09-27
status: complete
---

# Phase 225 Plan 03: D-02 Allowance Measurement and Pre-registered Accept Rule Summary

**Measured `ROOT_GUARD_BOOST_ALLOWANCE = 0.04` (guard window `W = 0.09`) from real Maia+Stockfish first-expansion deltas across four ELOs, then committed the full pre-registered A0/A2/A21/FINAL accept rule as arm A0 — before any gate arm has run.**

## Performance

- **Duration:** 22 min (this executor's Task 2 + Task 3; Task 1's D-02 measurement run was orchestrator-inline work completed before this dispatch)
- **Started:** 2026-09-27T07:22Z (approx, immediately after Task 1's data commit)
- **Completed:** 2026-09-27T07:38:52Z
- **Tasks:** 3 (Task 1 orchestrator-run; Tasks 2-3 this executor)
- **Files modified:** 11 (9 created by Task 1's data commit, 2 created by this executor)

## Accomplishments

- **Task 1 (orchestrator, checkpoint:human-action, already complete at dispatch):** ran the D-02 first-expansion root-trace measurement over 4 ELOs (1300/1500/1900/2300) x 16 positions x 50 nodes, no stop rule, `--maia-fifo`, and computed the allowance. Result: `METHOD measured`, `ALLOWANCE 0.04`, `pooled_n 338`, `pooled_p90 0.0344991`. Data (4 root-trace TSVs, 4 stop-rule TSVs, `allowance.json`) committed in `32a60e018`.
- **Task 2:** wrote `reports/engine-search-fixes-225/d02-allowance.md` — the recorded value (`A = 0.04`), guard window (`W = 0.09`), the exact reproduction command and tooling commit SHA (`6a69c8786`), the per-ELO p50/p90/max/n table plus the pooled row, and the selection-bias / ELO-shrinkage / RESEARCH C-1 caveats. Committed alone (`488b35a74`).
- **Task 3:** wrote `reports/engine-search-fixes-225/accept-rule.md` — the full pre-registered decision contract: the A0/A2/A21/FINAL stacked arms with content assertions and the detached-worktree procedure (Pattern 4); the D-02 design input (A=0.04, W=0.09); every pinned command (throughput, stop rule, move quality with the rerun-confirmation rule, calibration's five launch blocks and A0-cells converter); the seven criteria in evaluation order with their `engine_search_fixes_verdict.py` twin constant names (T-50/T-400 at `THROUGHPUT_MAX_WALL_RATIO` 1.05, MQ-2/MQ-1 at `MQ_REGRESSION_MARGIN` 0.05, S1 at `STOP_RULE_MAX_WALL_MS` 12,100, S2 at `STOP_RULE_MIN_EARLY_STOP_RETENTION` 0.5, the calibration branch at `CALIBRATION_NEAR_MISS_FRACTION` 0.75); the report-only D-04 exposure metric and item-3 table; the D-14 item ship/hold table; and the "what must not happen" prohibitions. Committed alone (`1b5313b96`) — that commit is arm A0, and it changes only this one file.

## Task Commits

Each task was committed atomically:

1. **Task 1: D-02 first-expansion root traces and measured allowance** - `32a60e018` (data) — *completed by the orchestrator before this executor was dispatched, per the checkpoint resolution.*
2. **Task 2: Record the D-02 allowance and its method** - `488b35a74` (docs)
3. **Task 3: Commit the pre-registered accept rule (arm A0)** - `1b5313b96` (docs)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified

- `reports/data/engine-search-fixes-225/d02/allowance.json` - measured allowance result (method, pooled_n, pooled_p90, per-ELO table)
- `reports/data/engine-search-fixes-225/d02/engine-root-trace-round-elo{1300,1500,1900,2300}-stopoff-*.tsv` - first-expansion delta rows, one file per ELO
- `reports/data/engine-search-fixes-225/d02/engine-dispatch-stop-rule-round-elo{1300,1500,1900,2300}-stopoff-*.tsv` - the matching main harness TSVs
- `reports/engine-search-fixes-225/d02-allowance.md` - the recorded D-02 value, method, per-ELO table, and caveats
- `reports/engine-search-fixes-225/accept-rule.md` - the pre-registered accept rule (arm A0's add-commit)

## Decisions Made

- The allowance is `0.04` via the `measured` method — the fallback (`0.10`) never fired; the run completed successfully on the first attempt for all four ELOs.
- The accept rule's calibration section follows RESEARCH C-6's three-way branch exactly (`none` / `report-only` / `decision`), matching `calibration_branch`'s and `calibration_item_decisions`'s implementation in `scripts/engine_search_fixes_verdict.py` verbatim rather than restating a simplified version — every number and code path in the document was checked against the source before being transcribed (frozen constants, `evaluate_throughput`, `evaluate_stop_rule`, `_verdict_holds`, `decide_items`).
- Included both the A21-first calibration launch and the conditional A0/A2 branch runs with their exact `cells-to-json` / `calibration_parity_verdict.py` command lines, even though the accept rule's own text says these branch runs are conditional — a future operator following this document needs the exact invocation the moment the branch fires, not a description of when it fires.

## Deviations from Plan

None - plan executed exactly as written. Task 1 was pre-completed by the orchestrator per the checkpoint resolution supplied at dispatch (its resume signal "d02 done: ALLOWANCE 0.04 (measured)" was treated as satisfied without re-running the measurement, per instruction). Tasks 2 and 3's `<action>`, `<verify>`, and `<acceptance_criteria>` blocks were implemented and verified exactly as specified. No Rule 1-4 triggers arose: no bugs found requiring a fix, no missing critical functionality, no blocking issues, no architectural changes needed. No file under `frontend/src/`, `scripts/`, or `bin/` was touched, per the plan's prohibition.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required beyond the orchestrator-run D-02 measurement (Task 1), which was already complete at dispatch. No packages were installed.

## Next Phase Readiness

- **For Plan 225-04 (item 2, round underfill):** the accept rule names its arm as "the last commit whose subject carries the `(225-04)` scope and touches `frontend/src/lib/engine`" — that plan's final commit becomes A2. Its content-assertion scope is limited to `mctsSearch.ts` and `__tests__/mctsSearch.roundFill.test.ts`.
- **For Plan 225-05 (item 1, root comparability guard):** must set `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance = 0.04` (from `d02-allowance.md`) and pass `--guard-window 0.09` in every stop-rule gate command it runs, per `accept-rule.md` §2 and §3.
- **For Plans 225-06..08 (item 3, gate arms, report):** `accept-rule.md` is now the single source of truth for every gate command, criterion, and decision — no further design decisions remain to be made before running arms. The document is committed and, per D-11, must not be edited once any gate data exists; a deviation is a separate dated override document.
- No blockers. `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` remains empty at this commit (A0), and no `reports/data/engine-search-fixes-225/{a0,a2,a21,final,calibration}` path exists yet — confirmed by this plan's own acceptance checks.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- All 11 key files found on disk (`ls` confirmed `reports/engine-search-fixes-225/d02-allowance.md`, `reports/engine-search-fixes-225/accept-rule.md`, and the 9 files under `reports/data/engine-search-fixes-225/d02/`).
- All 3 task commits (`32a60e018`, `488b35a74`, `1b5313b96`) found in `git log --oneline`.
- Re-ran plan-level `<verification>` and both `<acceptance_criteria>` gates: D-02 data + allowance committed and d02-allowance.md/accept-rule.md committed in that order (confirmed by commit timestamps and `git log --diff-filter=A`); no gate-data directory exists; `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` empty; `uv run pytest tests/scripts/test_engine_search_fixes_verdict.py tests/scripts/test_engine_search_fixes_allowance.py -x` — 33/33 passed; all 6 grep-based threshold/scope checks on `accept-rule.md` returned non-zero counts.
