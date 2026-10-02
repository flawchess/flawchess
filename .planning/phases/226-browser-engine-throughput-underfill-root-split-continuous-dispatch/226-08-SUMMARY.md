---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 08
subsystem: engine-measurement
tags: [design-inputs, accept-rule, cBFTV, D-13, D-16, D-17, calibration-null, tdd]

requires:
  - phase: 226-07
    provides: "committed step-0 data (design-inputs.json, calibration nulls, cBFTV traces, throughput/content/stop-rule TSVs, widened MQ fixture)"
provides:
  - "reports/engine-throughput-226/design-inputs.md (measured step-0 inputs, D-13 cBFTV classification: side effect)"
  - "reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md (dated override, pending owner ratification)"
  - "scripts/engine_throughput_226_verdict.py: ten design-input constants frozen from design-inputs.json"
  - "reports/engine-throughput-226/accept-rule.md (pre-registered decision contract; its add-commit is arm A0)"
affects: [226-09, 226-10, 226-11, 226-12]

actuals:
  tokens: 16837
  tasks: 3
  commits: 5
  plan_head_before: a66db406ef35c50b61b862301947171a5e0b3dec
  plan_head_after: 6160808fc3c5a34d0c85e610f87c7a28c458aee5

tech-stack:
  added: []
  patterns:
    - "Frozen design-input constants pinned by a test reading the committed JSON they were transcribed from (never hand-verified equality)"
    - "Dated override document (not an edit to the frozen protocol) when a pre-registered rule's literal text would misattribute evidence"

key-files:
  created:
    - reports/engine-throughput-226/design-inputs.md
    - reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md
    - reports/engine-throughput-226/accept-rule.md
  modified:
    - scripts/engine_throughput_226_verdict.py
    - tests/scripts/test_engine_throughput_226_verdict.py

key-decisions:
  - "D-13 cBFTV classified as a tree-shape side effect, not a bug: cBFTV itself has zero duplicate-expansion anomalies in any of the four traces; every TRACE-ANOMALY line belongs to three pre-existing control positions present identically at A0 (before any A2 code exists); the e4c6-below-e2g4 crossover traces to the identical leaf FEN and Stockfish grades in both A0 and the A2 candidate, only re-timed by the underfill fix's denser round-fill"
  - "Because step0-protocol.md section 6 reads any TRACE-ANOMALY line as a literal bug signature, and applying it literally here would misattribute pre-existing A0 behaviour to item 2, a dated override document records the evidence and the classification actually applied, marked pending owner ratification per this plan's autonomy instruction"
  - "Item 2 (round underfill) proceeds to gate measurement in Plan 226-09 with no additional D-13 code fix in mctsSearch.ts beyond the three cherry-picked Phase 225 commits"

requirements-completed: []

coverage:
  - id: D1
    description: "design-inputs.md records every design-input value, provenance, calibration null, D-13 explanation, D-17 shares, D-16 content/throughput inputs, D-08 app premise, and the Phase 227 warm-arm handoff"
    verification:
      - kind: other
        ref: "Task 1 <automated> verify: all required sections + D-13 classification present"
        status: pass
    human_judgment: false
  - id: D2
    description: "Verdict CLI's ten design-input constants frozen and pinned by test_design_input_constants_match_committed_json"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py::test_design_input_constants_match_committed_json"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py (full file, 35 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "accept-rule.md committed as arm A0, before any gate data, with every threshold matching the twin constants"
    verification:
      - kind: other
        ref: "Task 3 <automated> verify + acceptance-criteria checks (A0 commit resolution, empty frontend/src diff vs merge-base)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-13 override document classification (side effect vs bug) is a defensible autonomous judgment call"
    verification: []
    human_judgment: true
    rationale: "Involves interpreting step0-protocol.md section 6 against trace evidence and deciding the literal bug-signature text does not apply here; the reasoning is laid out in full in the override document, but the classification itself is a judgment call the owner should ratify (see Owner review required)."

duration: 95min
completed: 2026-09-29
status: complete
---

# Phase 226 Plan 08: Design Inputs, Frozen Constants & Accept Rule Summary

**Design-inputs.md, frozen verdict-twin constants and a pre-registered accept-rule.md (arm A0) — cBFTV classified as a tree-shape side effect via a dated override, since every TRACE-ANOMALY line traces to three pre-existing control positions and never to cBFTV itself.**

## Performance

- **Duration:** 95 min
- **Started:** 2026-09-29T (session start)
- **Completed:** 2026-09-29T (session end)
- **Tasks:** 3
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- `reports/engine-throughput-226/design-inputs.md`: every design-input value transcribed
  verbatim from the committed `design-inputs.json`, with the protocol formula and, for the three
  derived constants, the underlying arithmetic recomputed directly from the committed step-0
  TSVs (P=0.05856, G floored at 0.03; the shared warm noise floor 0.0168 driving both content
  bounds). The calibration-null section reports the A0b-vs-A0a in-session null (`holds`) and the
  void A0a-vs-July-21 comparison, plus a reasoned paragraph on whether Phase 225's own July drift
  is explained by measured noise.
- D-13 `cBFTV` explanation: recomputed `detectAnomalies`' duplicate-expansion counts directly
  from the committed expansions TSVs and confirmed they match 226-07-SUMMARY's original stdout
  counts exactly (16/17/12/14 across a0-c1/c2/c4/a2cand-c4); every duplicate group belongs to
  three specific repetition-prone control positions, never to `cBFTV`. Traced the `e4c6`-below-
  `e2g4` crossover to the identical leaf FEN and near-identical Stockfish grades appearing in
  both A0 (round 12/50 nodes) and the A2 candidate (round 9/50 nodes) — the underfill fix's
  denser round-fill (round-size sequences `1,4,2,1,3,4,4,3,3,4,3,4,1,4,4,1,4` at A0-c4 vs
  `1,4,4,4,4,4,4,4,4,4,4,4,4,1` at the A2 candidate) merely re-times an identical expansion, never
  changes its content.
- `reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md`: dated override
  document recording why step0-protocol.md section 6's literal "any TRACE-ANOMALY line" bug
  signature does not apply here (it fires at A0 before any A2 code exists, on positions unrelated
  to `cBFTV`), the classification applied instead (side effect, checked against the remaining two
  bug signatures), and a separate owner-information note describing the pre-existing
  duplicate-expansion pattern as a possible small throughput inefficiency, unfixed and unseeded.
- `scripts/engine_throughput_226_verdict.py`: the ten design-input constants set from `None` to
  the exact `design-inputs.json` values (RED-GREEN TDD: `test_design_input_constants_match_committed_json`
  added first and confirmed failing on the target assertion, then the constants frozen to make it
  pass). Confirmed the pinning test fails when a constant is edited (temporarily changed
  `EXPECTED_MQ_POSITIONS` 60->61, saw the assertion fail with the exact mismatch message, restored
  it, confirmed green again). `gates` on the repository's own committed data now exits 2 because
  gate-arm TSVs are missing, not because constants are unset.
- `reports/engine-throughput-226/accept-rule.md`: the full decision contract — arm definitions
  and content assertions, all ten design inputs, exact command lines for every gate step (four
  throughput pool/concurrency configs, stop rule, move quality against the widened 60-row
  fixture, the root-split content instrument in pool-source mode, the D-08 determinism check, the
  D-03 warm-arm report-only measurement, and the five calibration cells at 50 games/anchor/seed-1),
  every criterion in `run_gates`' own evaluation order with its twin constant name, report-only
  signals, `decide_items`'/`refit_decision`'s stacked rules restated, and prohibitions. Committed
  as its own commit, which is arm A0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write design-inputs.md, including the D-13 cBFTV explanation** - `116c7b7ec` (docs)
2. **Task 2: Freeze the design-input constants in the verdict twin** - RED `84e26f7f3` (test), GREEN `1771e1dcb` (feat), style fix `6160808fc` (style)
3. **Task 3: Commit the pre-registered accept rule (its add-commit is arm A0)** - `3fe340ce9` (docs)

**Plan metadata:** (this commit, to follow)

## Files Created/Modified

- `reports/engine-throughput-226/design-inputs.md` - measured step-0 design inputs, calibration-null analysis, D-13 cBFTV explanation and classification, D-17/D-16/D-08 sections, Phase 227 handoff
- `reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md` - dated override for the D-13 TRACE-ANOMALY literal-text misattribution
- `reports/engine-throughput-226/accept-rule.md` - the pre-registered gate decision contract (arm A0)
- `scripts/engine_throughput_226_verdict.py` - ten design-input constants frozen from `None` to the committed values
- `tests/scripts/test_engine_throughput_226_verdict.py` - new pinning test + unset-constants test updated to explicitly monkeypatch `None`

## TDD Gate Compliance

Task 2 (`tdd="true"`):

- **RED** (`84e26f7f3`, `test(226-08): ...`): `test_design_input_constants_match_committed_json`
  added, confirmed failing on the target assertion (`AssertionError: EXPECTED_MQ_POSITIONS: module
  has None, committed JSON has 60`) — an intentional failure on the planned behavior, not an
  import/fixture error. The pre-existing `test_gates_with_every_design_input_unset_exits_incomplete_and_lists_names`
  test was updated in the same commit to explicitly monkeypatch every constant to `None` (a no-op
  at RED time, since the module default was still `None`), so it stays testable once GREEN removes
  that default.
- **GREEN** (`1771e1dcb`, `feat(226-08): ...`): all ten constants set to the `design-inputs.json`
  values; full test file (35 tests) passes; `ty check` clean.
- **REFACTOR**: none needed (a data-literal change, no structural cleanup available).
- **Note on RED-evidence tooling:** `gsd_run check tdd-red-evidence` was not available in this
  worktree's shell (`gsd_run: not found`). RED evidence was instead verified manually by reading
  pytest's own failure output: the target test (`test_design_input_constants_match_committed_json`)
  failed on its planned assertion with a clear expected-vs-actual message, not a collection error,
  syntax error, or unrelated test failure — satisfying the #3770 intentional-RED definition by
  direct inspection rather than the automated verdict tool.
- A follow-on `style(226-08)` commit (`6160808fc`) applied `ruff format` to the new test code
  (a line-wrap change only, verified tests still pass after).

## Decisions Made

- **D-13 classification: side effect, not a bug.** See "Deviations from Plan" below — this
  required departing from step0-protocol.md section 6's literal text, so it is recorded as a
  dated override rather than a plan deviation.
- **Reused the exact commit-marker convention the plan specified** (`(arm A2)`, `(arm A21)`,
  `(arm A21S)`, found via `git log -F --grep`) for arm lookups in accept-rule.md, rather than
  Phase 225's `(225-04)`-style scope-number convention — this is a NEW convention for this phase
  that Plans 226-09/226-10/226-11 must follow exactly in their commit subjects, or the accept
  rule's arm lookup will not find them (flagged under Owner review required).
- **No refit, no gate run, no code fix** were made in this plan — strictly measurement-and-
  documentation as scoped, per the plan's own prohibitions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ruff format` reflowed a long assertion line in the new pinning test**
- **Found during:** Task 2 (post-GREEN cleanup, before finalizing the plan)
- **Issue:** `uv run ruff format --check` flagged one over-length `assert` line in
  `test_design_input_constants_match_committed_json`
- **Fix:** Ran `uv run ruff format` on the touched test/script files; only the one line wrapped
- **Files modified:** `tests/scripts/test_engine_throughput_226_verdict.py`
- **Verification:** Re-ran the full test file (35 passed) and `ruff format --check` (clean)
- **Committed in:** `6160808fc` (separate `style(226-08)` commit, per CLAUDE.md convention)

---

**Total deviations:** 1 auto-fixed (1 blocking/formatting)
**Impact on plan:** Purely mechanical; no logic or content change. No scope creep.

## Owner review required

Per the orchestrator's autonomy instructions, every autonomous judgment call made while executing
this plan is listed here explicitly:

1. **D-13 classification (side effect, not a bug) — pending ratification.** The full evidence
   trail is in `reports/engine-throughput-226/design-inputs.md` §4 and the dated override
   `reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md`. Summary: `cBFTV`
   itself has zero duplicate-expansion anomalies in any of the four committed traces; every
   `TRACE-ANOMALY` line belongs to three pre-existing control positions (`WwKKM`, `g687537-p48`,
   `I3vZ1`) present identically at A0 concurrency 1/2/4 (before any A2 code exists) and at the A2
   candidate; the `e4c6`-below-`e2g4` crossover traces to the identical leaf FEN and Stockfish
   grades in both A0 (round 12) and the A2 candidate (round 9), only re-timed by the underfill
   fix's denser round-fill. **Consequence if ratified:** Plan 226-09 lands item 2 (A2) with no
   additional D-13 code fix in `mctsSearch.ts` beyond the three cherry-picked Phase 225 commits.
   **If NOT ratified:** the override document should be marked void and D-13 re-escalated before
   Plan 226-09 defines arm A2.

2. **The A0a-vs-July-21 "is Phase 225's own -81.4 SF drift noise?" paragraph (design-inputs.md
   §3) is a reasoned interpretation, not a pure transcription.** It argues the July-21 comparison
   method itself is unreliable (this session's own null-control cell, on unmodified code,
   drifted −177.4 against a 149-Elo threshold), so Phase 225's −81.4 drift is *most plausibly*
   attributable to the same cross-session non-comparability rather than a real strength effect —
   but explicitly does not claim this proves −81.4 was pure single-session sampling noise. Worth
   a read before treating it as settled.

3. **Finding 1 (prototype content already exceeds the Clear-Hash bound) is carried forward
   unresolved, as instructed** — recorded in `design-inputs.md` §6 and restated as accept-rule.md
   criterion 10's own caveat. This is a real risk to Plan 226-10/226-11's A21S content criterion;
   nothing was done about it here per this plan's own scope (measurement/documentation only, no
   gate run).

4. **The pre-existing `duplicate-expansion` pattern (§4a of design-inputs.md, and the override
   document's closing note) is described but neither fixed nor seeded**, per the orchestrator's
   explicit instruction to describe rather than act. It is a candidate for a future seed if the
   owner judges it worth the CPU.

5. **TDD RED-evidence tooling gap:** `gsd_run check tdd-red-evidence` is not available in this
   worktree's shell. RED evidence was verified by direct inspection of pytest's failure output
   instead (see TDD Gate Compliance above) — flagging in case the harness expects the automated
   check to have run.

6. **New arm-marker commit convention** (`(arm A2)`/`(arm A21)`/`(arm A21S)`/`(arm A21SC)`,
   transcribed verbatim from this plan's own Task 3 action text) must be used literally in the
   commit subjects of Plans 226-09/226-10/226-11 (whichever lands each arm), or
   `accept-rule.md`'s `git log -F --grep` arm lookup will not resolve that arm.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 226-09 can define and land arm A2 (the round underfill re-land) directly against this
  accept rule's Section 1/3/4, with D-13 resolved (no additional code fix needed, per the
  override above, pending ratification).
- The frozen verdict-twin constants and accept-rule.md are ready for `run_gates` once gate data
  exists; `gates` currently exits 2 (incomplete) purely on missing `gate/` data, confirming the
  wiring is live.
- Blocker/risk carried forward: accept-rule.md criterion 10 (Clear-Hash content bound) is likely
  to fail based on the prototype measurement — Plan 226-10/226-11 (root split) should budget for
  investigating the pool-source implementation's own content delta before assuming this criterion
  will pass.

## Self-Check: PASSED

- All 6 created/modified files confirmed present on disk with `[ -f ]`.
- All 5 task commits (`116c7b7ec`, `84e26f7f3`, `1771e1dcb`, `3fe340ce9`, `6160808fc`) confirmed
  in `git log --oneline --all`.
- Task 1 `<automated>` verify (all required strings + `side effect|bug` classification present):
  PASSED.
- Task 2 `<automated>` verify (both test files pass, `ty check` clean, `gates` on repo data exits
  2 for missing gate data): PASSED.
- Task 3 `<automated>` verify (all required strings present, no `gate/` dir exists, file is
  tracked): PASSED.
- Acceptance criteria re-verified: `EXPECTED_MQ_POSITIONS` constant line no longer reads `None`;
  the pinning test was confirmed to fail on a temporary edit and pass once restored; every
  numeric threshold in `accept-rule.md` spot-checked against the frozen constant of the same
  name; `git log --diff-filter=A --format=%H -1 -- accept-rule.md` resolves to HEAD, and
  `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` is empty at that commit.
- Plan-level `<verification>`: commit order confirmed (design-inputs.md -> frozen constants ->
  accept-rule.md -> SUMMARY), no `reports/data/engine-throughput-226/gate/` directory exists.

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-29*
