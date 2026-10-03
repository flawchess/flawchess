---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 09
subsystem: testing
tags: [engine, design-review, accept-rule, continuous-dispatch, pre-registration, verdict-twin]

requires:
  - phase: 227-03
    provides: "verdict twin scripts/engine_dispatch_227_verdict.py and its frozen constants"
  - phase: 227-07
    provides: "interleave driver and speed probe (pinned throughput commands, probe constants)"
  - phase: 227-08
    provides: "clear-hash parity PASS, round-mode legs, owner direction on round determinism"
provides:
  - "reports/continuous-dispatch-227/design.md: reviewed continuous-loop design, X/Y/N disposition table, sizing, review record, closing lines REVIEW-A / REVIEW-B SOUND (round 2)"
  - "reports/continuous-dispatch-227/reviews/r{1,2}-{a,b}.md: raw reviewer outputs"
  - "reports/continuous-dispatch-227/accept-rule.md: pre-registered gate, constants table pinned to the twin"
  - "Verdict twin: round-repeat disagreement is a report-only rate, not an INVALID"
  - "Harness comment rewording the design flagged (comments only)"
affects: [227-10, 227-11, 227-12, 227-13]

plan_head_before: 79b6597661e63fab3a19ba7aeec6e0f1de5b1cd3
plan_head_after: dcba1ba146bc7a8c09025b1a3556d6d3f7e7e98e

actuals:
  tokens: 55000
  tasks: 3
  commits: 12

tech-stack:
  added: []
  patterns:
    - "Pre-registered accept rule whose constants table is machine-pinned to the verdict twin by name (test_accept_rule_matches_twin_constants)"
    - "Two independent-context reviewers per round with an identical claim-attack brief, raw outputs committed, every finding a numbered row in design section 7"

key-files:
  created:
    - reports/continuous-dispatch-227/design.md
    - reports/continuous-dispatch-227/accept-rule.md
    - reports/continuous-dispatch-227/reviews/r1-a.md
    - reports/continuous-dispatch-227/reviews/r1-b.md
    - reports/continuous-dispatch-227/reviews/r2-a.md
    - reports/continuous-dispatch-227/reviews/r2-b.md
  modified:
    - scripts/engine_dispatch_227_verdict.py
    - tests/scripts/test_engine_dispatch_227_verdict.py
    - scripts/lib/calibration-providers.mjs
    - scripts/lib/maia-instrumentation.check.mjs
    - scripts/engine-dispatch-stop-rule.mjs
    - scripts/lib/stockfish-pool.mjs
    - scripts/calibration-harness.mjs
    - scripts/lib/node-engine-providers.mjs

key-decisions:
  - "Round 1 (both reviewers NOT SOUND) and round 2 (both SOUND) are closed; round-2 repairs were applied without a third round"
  - "Round-repeat agreement is report-only (owner, 2026-10-02: very similar is good enough); validity rests on clear-hash parity, not on round-repeat identity or equality with 226 a21s"
  - "Tooling commit T = 399780bf8; the harness-content evidence is the clear-hash parity PASS (cef88fd87) re-verified on T, plus Plan 227-10's post-extraction re-run as a precondition for the gate"
  - "Drain order rule: abort and early-stop are tested before a rejection, so every rejection drained after a stop is dropped (R2A-6)"

requirements-completed: []

coverage:
  - id: D1
    description: "Design reviewed SOUND by two independent reviewers, every finding dispositioned"
    verification:
      - kind: other
        ref: "Task 2 automated verify (SOUND lines for the same round, no undispositioned R-rows, 4 committed raw reviews)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Accept rule committed before any gate data, constants pinned to the twin"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_accept_rule_matches_twin_constants"
        status: pass
      - kind: other
        ref: "git ls-files reports/data/continuous-dispatch-227/gate prints nothing; accept-rule.md tracked"
        status: pass
    human_judgment: false
  - id: D3
    description: "Round-repeat disagreement is valid data and appears in the report-only rate"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_round_repeat_disagreement_is_valid_and_report_only"
        status: pass
    human_judgment: false

duration: 90min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 09: Design review and accept rule Summary

**The continuous-dispatch design survived two review rounds (round 1: both NOT SOUND, round 2: both SOUND) and the gate is pre-registered in `accept-rule.md` (commit `7fb704a65`) with its constants pinned to the verdict twin by test, before any continuous-mode data exists.**

## Scope of this dispatch

Task 1 (the design) and the two review rounds were produced in earlier dispatches. This dispatch closed Task 2 (repairs for
every round-2 finding), relaxed the verdict twin per the owner's direction, committed the accept rule (Task 3), reworded
the flagged harness comments, and wrote this summary. No engine measurement was run, nothing exists under
`reports/data/continuous-dispatch-227/gate/`, `STATE.md` and `ROADMAP.md` were not touched, and no frontend file changed.

## Reviewer brief (identical for every reviewer, quoted once)

"Review reports/continuous-dispatch-227/design.md against the code. Attack these claims and try to break each with
file:line evidence: (a) blocks scoped per fill are exact; (b) applied + inFlight <= maxNodes and inFlight == 0 at budget
exhaustion; (c) c = 1 byte-identity; (d) no result is ever applied after abort or early stop; (e) no missing wakeup; (f)
the harness measures the same algorithm with app-faithful timing. Also check that every disposition in section 5 is
correct against the current code and reports/continuous-dispatch/apply-order-design.md §9b/§9d. Return: verdict SOUND or
NOT SOUND; a numbered findings list, each with severity (high/medium/low), the claim it breaks, file:line evidence, and a
suggested repair." The brief names no other reviewer, earlier round or earlier finding. Fresh agents were used per round.

## Rounds and verdicts

| Round | Reviewer A | Reviewer B | Findings | Outcome |
|---|---|---|---|---|
| 1 | NOT SOUND (8 findings, 1 high) | NOT SOUND (9 findings) | 17, all repaired, none rejected | Tooling fix `399780bf8`, design repair `a5a208def` |
| 2 | SOUND (12 findings, none high) | SOUND (7 findings plus 1 minor note, none high) | 20 (R2A-1..12, R2B-1..8), all verified against the code, all repaired, none rejected | Repairs in `7bb93b943` |

Raw outputs are `reports/continuous-dispatch-227/reviews/r1-a.md`, `r1-b.md`, `r2-a.md`, `r2-b.md`. Design section 7 has one
row per finding. `design.md` ends with `REVIEW-A: SOUND (round 2)` and `REVIEW-B: SOUND (round 2)`.

Round-1 tooling consequence: the harness Maia FIFO ignored the abort signal (R1A-1 high, R1B-1), which would have charged
a stale Maia backlog to the next timed row in continuous mode only. Fixed in `399780bf8` (FIFO forwards the signal, drops
queued requests, lets the in-flight inference finish, `whenMaiaIdle()` awaited before `pool.whenIdle()` in every gate
script, check (f) added and mutation-tested). The clear-hash parity tripwire was re-run on that commit: **PASS, 0 of 60
rows differ in each stop mode** (recorded in `de86e31ec`).

Round-2 substance: the Maia-cache effect on the win is non-monotonic (the first draft said lower P always shrinks it, and
called the gate's figures an upper estimate; both withdrawn); M5 (cancelled grades leaving partial hash work) exists in
both modes and is amplified in continuous, not continuous-only; the sketch now guards the single `await` with
`!signal.aborted && !st.earlyStop` (a synchronous abort during a fill lost its wake); a rejection drained after a stop is
dropped under one stated rule; X-9 records the wedged-ONNX residual; Y-1 is split into a moot nondeterminism half and an
accepted blindness half; four new or corrected rows in design section 3.6.

## Accept rule (the pre-registration point)

- **Commit `7fb704a65`**: `docs(227-09): accept rule (pre-registered before any continuous data)`. Everything under
  `reports/data/continuous-dispatch-227/gate/` must descend from it; none exists.
- Sections 1 to 10 as planned: arms A0/A1 from one checkout `I`, content assertions, frozen constants table (31 rows,
  `| NAME | value | decision |`), pinned commands (judged MQ, Clear-Hash MQ, analysis-400 MQ, the interleaved throughput
  driver with probe constants, the owner's WebGPU leg, the ten-cell calibration launch blocks and conversions, the
  composed `gates` command), data layout, sequencing, criteria in evaluation order, report-only, the D-08 virtual-loss
  trigger, the owner clause and what must not happen.
- Tooling commit `T` = `399780bf8`; parity flag commit `cef88fd87`; twin relaxation `012856e92`; reviewed design `7bb93b943`.
  The implementation commit `I` is recorded by Plan 227-11 in run metadata and its SUMMARY, never in the rule.
- `test_accept_rule_matches_twin_constants` parses section 2 and asserts every row equals `repr()` of the twin constant of
  that name and that every public UPPER_CASE twin constant (bar four path constants) is in the table. Mutation check: a
  table value changed from 0.15 to 0.16 fails it (reverted).

## Sizing headline numbers (design section 4, all model output from measured inputs)

- Node gate, nominal reduction: t50-p4 34.3 percent, t400-p4 29.7, t400-p2 31.2, t50-p2 32.9 (model only). Against the
  measured round wall (Table 2) the ceilings are lower: 32.3, **21.5**, 32.1, 33.9. On the t400-p4 ship-bar config the
  ceiling is 6.5 points above D-04's 15 percent bar, so continuous must realize about 70 percent of the ideal pipeline win.
- Browser bot path (measured P from Plan 227-08, Node G): wasm 31.8 to 38.7 percent, WebGPU 21.8 to 26.1. With the implied
  browser G (about 350 ms wasm, 300 ms WebGPU, an upper bound) the range is 21 to 23 wasm and 14 to 18 WebGPU. Finite-N
  correction for the stop-on bot path: Node 30.7, wasm 30.6, WebGPU 22.3 (15.0 at implied G).
- The Phase 198 prior (about 18 percent at P about 15 ms) is **replaced in number** (21.8 to 26.1 percent at the measured
  WebGPU P of 17.8 to 23.2 ms) and **confirmed in direction** (WebGPU gains less than wasm). The model is within 10 percent
  of measured round wall in three of four Node configs and 23 percent too high on t400-p4.

## Deviations from Plan

### 1. [Owner direction, 2026-10-02] Verdict twin: round-repeat determinism check removed

- **Found during:** Task 3 preparation (flagged in `227-08-SUMMARY.md` and `227-08-TRIPWIRE-DEBUG.md`).
- **Issue:** `_check_round_determinism` raised `InvalidDataError` on any round-repeat disagreement. Under `--hash warm`
  with worker-thread Maia (Plan 227-01) round repeats legitimately differ (Plan 227-04: minority pick on `cBFTV` in about
  8 to 11 percent of repeats), so every judged cell would have been INVALID.
- **Fix:** replaced by `round_repeat_disagreement_positions`, carried in each cell's `report` as
  `round_repeat_disagreement_positions` and `round_repeat_disagreement_rate` and printed on the `MQ-REPORT` line. The
  tripwire docstring, usage and CLI help now point at the clear-hash parity check; the subcommand stays strict. The D
  and D-03 math needed no change (D averages over repeats, the net is fractional).
- **Tests:** `test_invalid_round_repeats_differ` became `test_round_repeat_disagreement_is_valid_and_report_only`, plus
  `test_round_repeat_disagreement_is_in_the_cell_report`. Mutation proof: restoring the raise fails both (checked, reverted).
- **Files:** `scripts/engine_dispatch_227_verdict.py`, `tests/scripts/test_engine_dispatch_227_verdict.py`. **Commit:** `012856e92`.

### 2. [Owner direction] Accept rule validity differs from the plan text

Plan Task 3 step 6 listed "round repeats identical, round arm equal to 226 a21s". Both dropped (item 1). The rule keeps
the dispatch_mode, maia_fifo, rc, column and completeness checks, and rests harness-content validity on the committed
clear-hash parity PASS re-verified on `T` plus Plan 227-10's post-extraction re-run as a gate precondition. RESEARCH
Pitfall 8's "round repeats must show 0 diffs" is explicitly superseded in section 6.

### 3. [Rule 3 - blocking] `npm ci` in the fresh worktree

The worktree had no `node_modules`. `npm ci` (lockfile install, no package added) in `frontend/` and `scripts/` was needed
to run the four gate `--self-test`s and `stockfish-pool.check.mjs`. Nothing was added to any manifest.

### 4. Content assertion allows the comment-only commit

The accept rule was committed before the comment rewording, as ordered. Its content assertion 2 therefore allows, besides
Plan 227-10's six files, the comment-only changes made by the commit whose subject begins
`docs(227-09): reword harness comments` (checked comment-only: `git diff -U0` over `scripts/` shows no non-comment line).

### 5. Not reviewed again

Both round-2 reviewers returned SOUND, so the plan's closing rule was met and no third round ran. Two round-2 repairs
change the design's sketch (the guard before the `await`, and the rejection-after-stop rule). Neither was seen by a
reviewer. They are small and each has a test and a mutation in section 2.12, but the project's memory says self-review
misses load-bearing defects. If the owner wants a fresh look, it is cheap to run one more pair before Plan 227-10.

## Known Stubs

None.

## Handed to Plan 227-10 (frontend, not done here)

- First commit, before the extraction: pre-extraction golden captures of the round loop (design 2.4), committed as vitest
  goldens. Then extract `applyAndReport` / `discoverDeadEnd` and re-run the clear-hash parity check, requiring TRIPWIRE
  PASS with 0 differing rows against `reports/data/continuous-dispatch-227/tripwire/parity-clear`. **Record that PASS in
  227-10's SUMMARY: the accept rule makes it a precondition of the gate.**
- Implement the sketch as reviewed: guard `!signal.aborted && !st.earlyStop` before the `await`; abort/early-stop test
  before the rejection test in the drain.
- Every test row of design 2.12 with its mutation, including the new ones (synchronous abort during a fill; rejection
  after a stop; the (b) test keyed on `nodesEvaluated === maxNodes`, not `budgetExhausted` or `stopReason`).
- Reword frontend comments (design 2.11): `mctsSearch.ts` `:30-37`, `:40-44`, `:46-54`, `:113`, `:126-136`, `:298-309`,
  `:345-360`, `:491-499`, `:514-516`, `:575-583`, `:602-603`, `:720-722`, `:735`; `maiaQueue.ts:259-263`;
  `deadlineSearch.ts:36-44`.
- `requestPolicy` in `maiaQueue.ts` has no aborted-signal check, so the `inFlight.catch` fallback can enqueue a stale
  request after a stop. A one-line `if (signal?.aborted) return Promise.resolve({})` is flagged (R2B-5), not made.

## Handed to Plans 227-11 and 227-12

- **227-11-PLAN.md Task 1 step 4 and its automated verify still run `tripwire --mq-dir .../gate/mq/round` against 226
  a21s and require TRIPWIRE PASS.** That is superseded: under warm hash with worker Maia the round arm will not equal
  a21s. Replace it with the accept rule's validity (the twin's `mq` exiting 0 plus the round-repeat disagreement
  rate in the report). The plan was not edited here.
- Plan 227-11 must refuse to start unless 227-10's SUMMARY records the post-extraction parity PASS, must record `I` and
  assert accept-rule content assertions 1 to 3, and must check that the accept-rule commit is an ancestor before each
  gate-data commit.
- Open, report-only: the harness checks the Maia memo only after the FIFO (memo hits wait in the harness, bypass the queue
  in the app, R2A-3); the gate cannot see M5 or the cross-search part of M4 (never-cleared browser hash).

## Self-Check: PASSED

- Task 1 automated verify (every X/Y/N row dispositioned, claims a-f present): pass.
- Task 2 automated verify (matching SOUND lines for round 2, no undispositioned finding row, 4 committed raw reviews): pass.
- `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py -q`: 93 passed. `-k "accept_rule or frozen"`: 5 passed.
- `ruff format --check` and `ruff check` on the touched Python files: clean. `uv run ty check scripts/ tests/scripts/`: clean.
- `accept-rule.md` tracked; `git ls-files reports/data/continuous-dispatch-227/gate` empty; no `mctsSearch.ts` commit in Phase 227.
- Four gate scripts' `--self-test` and `scripts/lib/stockfish-pool.check.mjs` (rc 0): pass after the comment rewording.
- Commits found: `7bb93b943`, `012856e92`, `7fb704a65`, `dcba1ba14` (this dispatch), plus `781cd3fb6`, `6a1af2cbd`, `399780bf8`,
  `a5a208def`, `de86e31ec`, `b9dfdf85b` from earlier dispatches.
