# Phase 227: Browser Engine Continuous Dispatch Against a Relaxed Determinism Target (SEED-171) - Research

**Researched:** 2026-10-02
**Domain:** Async MCTS scheduling in the browser FlawChess engine (`mctsSearch.ts`), Node measurement harness fidelity, pre-registered statistical gates
**Confidence:** MEDIUM-HIGH. The code facts are HIGH (read this session, cited by line). The statistical sizing is MEDIUM: it rests on simulations with an assumed fragile-position model, calibrated against committed 226 data. The browser/WebGPU throughput figures are model-only (LOW-MEDIUM) until the D-06 measurement exists.

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

*(Copied verbatim from `227-CONTEXT.md` `<decisions>`.)*

#### Guiding principle (owner, 2026-10-02, restated for this phase)
- **D-00: The current engine (A21S round mode) is not gospel.** Decisions are made from first
  principles and from what the tests show, not by how closely the new code reproduces today's
  output.
  - Round mode is a **comparison arm**, not a reference answer.
  - Divergence from it is information, never a failure by itself.
  - The ground truth for move quality is the d20 Stockfish evaluation, not the old engine's pick.
  - A persona shift is something to refit, not a reason to hold.
  - Every "keep today's behavior" choice below must justify itself on its merits (simplest
    change, best measured result), not on fidelity to the current engine.
  - Pre-registration stays: the accept rule is still committed before data, because it keeps the
    test result honest rather than the old engine sacred. The owner makes the final call from the
    evidence, as in 226's override.

#### Carried forward (locked in Phase 226; D-05 re-read through D-00)
- 226 D-05: the picked move's d20 expected score, checked statistically over a fixture at c = 4,
  plus move-quality regressions. Same top move and `rankedLines` order are not the contract.
  **Under D-00 this is read as one-sided non-inferiority on absolute move quality (see D-01), not
  as "stay close to round mode".** A continuous mode that picks better moves passes.
- 226 D-07: round mode is retained behind a budget flag as the bit-identical path (unit and fixture
  gates, the A0 arm, rollback). This narrows Phase 198 D-11.
- 226 D-04: mobile gating is the Node harness with the pool forced to 2; a real phone is
  report-only.
- 226 D-10: powered calibration checks against a same-session A0, never the July-21 curves.
- L-2 (abort applies zero results) and L-4 (pool 2 vs c = 4, size from live idle slots) still
  bind. L-7 (independent review) applies, see D-12.
- **Owner principle (226 override, 2026-10-02):** the pre-226 engine is not a gold standard.
  Playing slightly differently is acceptable for a substantial performance gain. The accept rule
  is still committed before data; owner overrides stay separate documents, never rule edits.

#### Quality criterion and ship bar
- **D-01: Non-inferiority on absolute quality, not closeness to round mode.**
  - **What is judged.** The blocking metric is the paired **signed** difference in the picked
    move's d20 expected score, continuous minus round mode, on the widened move-quality fixture
    (226 D-14, ≥ 50 positions).
    - Each arm's pick is scored against the d20 ground truth.
    - Continuous passes if it is **not worse by more than a margin** (one-sided). Being better is
      a pass.
  - **The margin.**
    - The D-06 "k × round-mode floor" anchor is unusable: 226 measured that floor at **0 of 60
      plies differing**, because round mode is deterministic in the harness even with a warm
      hash, so k × 0 = 0.
    - The margin is anchored instead to the **0.0168 content-instrument floor** (mean |Δes|
      between differently warmed single-call grades). That floor is the noise the shipped browser
      already lives with.
    - **k = 1.5, so the margin is about 0.025 mean es per move.** This matches 226's warm
      `CONTENT_MAX` (0.025206).
    - The accept rule records k and the margin before any data.
  - **Report-only.** Unsigned divergence (mean |Δes| between the arms) is reported, never judged.
  - **Reversibility:** costly. The gate and the ship decision are built on this margin; changing
    it after data means an override document.
- **D-02: Measurement conditions.**
  - Use the shipped-like warm-hash configuration (226 D-03 no-Clear-Hash arm).
  - Continuous dispatch is timing-dependent, so each position runs **≥ 3 repeats** and the
    metric pools over repeats.
  - Round mode in the warm arm is deterministic but still gets the same treatment, so the arms
    are comparable.
  - The accept rule fixes the repeat count.
  - The Clear-Hash variant is report-only, because the browser never clears the hash.
- **D-03: Move-quality regressions count in both directions.**
  - A regression is a position where an arm's pick is clearly bad by d20 ground truth (226's
    move-quality definition).
  - The criterion is the **net** count: continuous regressions minus round-mode regressions.
  - The allowance comes from continuous-vs-continuous repeat flips; the research step sizes it.
  - Positions where continuous fixes a round-mode regression count in its favor.
  - This gate is blocking, because it is evidence about real move quality rather than fidelity.
- **D-04: Throughput ship bar ("substantial").** Ship if **either** the bot-move path (stop rule
  on, pool 4) **or** analysis at 400 nodes (pool 4) improves by **≥ 15% in CPU-normalized wall**,
  and **neither** regresses by more than 3%. The Node pool-2 configuration must not regress beyond
  its measured noise. All throughput arms are **interleaved** in one session (≥ 3 rounds, order
  rotated, load-average wait), and raw wall is reported alongside wall per grade-CPU. The cause:
  226 measured raw wall drifting about ±12% between runs, and its non-interleaved gate failed the
  underfill on drift. The 25% build line from Phase 198 is not reused; it was set for a much larger
  rewrite, under the stricter owner stance at the time. The mechanical verdict (D-01, D-03, D-04
  and D-15) is the evidence; the owner decides ship or hold from it, as in 226.

#### WebGPU measurement (prerequisite; keep WebGPU)
- **D-05: WebGPU stays.** The owner considered dropping it (2026-10-02) and decided to keep it and
  proceed as planned. Arguments recorded in the DISCUSSION-LOG.
- **D-06: Who and how.** Claude builds a **dev-only measurement tool** that runs in a real browser
  and reports: (a) Maia per-inference latency at batch 1 on wasm (t = 4) vs WebGPU, both idle and
  while the SF pool is busy (CPU-contention check), and (b) bot-move wall time over a few fixture
  positions, round mode vs continuous mode, labeled with the active backend. The tool is gated so
  it never reaches production users. The **owner runs it on a machine with a WebGPU adapter** (a
  hardware leg; this Linux Chrome has none). Claude automates everything else (memory: run
  human-action checkpoints yourself; defer only hardware legs). Remove the tool at phase end unless
  it is a few lines.
- **D-07: The result sizes and reports; it does not gate the build.** wasm Maia populations (iOS,
  every coarse-pointer or low-power device on pool 2, desktops without `shader-f16`) benefit
  regardless, so the build decision rests on the D-04 Node gate. The WebGPU run is **blocking on
  one point only**: continuous mode must not be slower than round mode on the WebGPU machine. The
  measured round-mode leg runs early, before the design sizes its expected desktop win. Phase 198's
  X-2 model (about 18% at P ≈ 15 ms) is the prior to confirm or replace.

#### In-flight work semantics
- **D-08: Start with hard pending exclusion; let the data argue for virtual loss.**
  - **Default.** In-flight leaves keep `isPending = true` and are filtered from selection as
    today. The reason is not fidelity to the current engine. Exclusion has no tunable, needs no
    new code path, and is the standard limit case of virtual loss.
  - **When to try virtual loss.** A Leela-style virtual-loss arm runs only if the D-01/D-03
    results or a tree trace show exclusion hurting quality at c = 4. One example would be forced
    breadth on peaked positions starving the best line. The arm is judged on the same criteria.
  - **Apply order.** Results apply in **arrival order**. The commit-ordered apply, ring buffer and slot-release machinery from
  Phase 198 existed only to keep bit-identity and are explicitly not rebuilt.
- **D-09: Stop handling.**
  - Abort: zero results apply after abort (L-2, Y-3). A unit test covers a result settling after
    abort.
  - Early stop and budget exhaustion: stop dispatching. In-flight results are **not applied**, and
    their requests are cancelled through an inner `AbortController` so stale grades do not hold SF
    slots into the next search. Latency first, no drain.
  - A grade that completes anyway may still write the grade cache, because its content is correct
    for `fen|depth`.
- **D-10: Budget accounting.** Dispatch only while `applied + inFlight < maxNodes`, so
  `nodesEvaluated` never overshoots `maxNodes`. Degenerate (empty-grade) closes keep today's WR-04
  semantics. Concurrency stays **c = 4** in this phase. The reason is scope (one variable at a time),
  not that c = 4 is right. Other c values are a deferred, test-driven question.
- **D-11: Determinism tripwires that survive.**
  - At c = 1, continuous mode must be **byte-identical** to round mode (Phase 198 X-12; cheap and
    falsifiable).
  - Round mode at any c stays bit-identical to A21S, so every existing c = 4 unit and fixture gate
    stays exact on the flag.
  - The grade-cache settlement race (X-6, Y-2, Y-4) and dead-end discovery at dispatch time (X-3) are
    accepted under the relaxed contract and need no ordering machinery. The design states this
    explicitly, with no claim that order cannot affect output.
- **D-12: Design review (L-7).** Write a design doc under `reports/<dir>/`. Disposition every
  Phase 198 finding in `apply-order-design.md` §9b (X-1..X-12) and §9d (Y-1..Y-14) as **applies**,
  **moot under the relaxed contract** or **repaired**. Then get **two independent-context
  reviewers**, each told to attack named load-bearing claims with file:line evidence and not told
  about earlier rounds. Re-review after repairs. No `mctsSearch.ts` edit lands before both return
  SOUND, or before their findings are dispositioned and repaired.

#### Rollout and calibration
- **D-13: Both callers.** The bot and analysis search both use continuous dispatch when it ships.
  The budget flag (for example `dispatchMode: 'round' | 'continuous'` on `SearchBudget`; the exact
  name is up to the planner) defaults to continuous in the app. Round mode is the test/A0/rollback
  path. Rollback is a flag flip (L-5).
- **D-14: Harness parity.** The calibration harness runs the same dispatch code as the app
  (algorithm parity). Persona calibration and the bot-strength curves run in continuous mode.
  Same-seed games are no longer byte-reproducible, which is expected.
- **D-15: Calibration gate and refit.** Arms are A0 = A21S in round mode and A1 = continuous mode,
  in the same session. Reuse 226's powered calibration machinery (`CALIBRATION_THRESHOLD_MAIA`
  85.0, `CALIBRATION_THRESHOLD_SF` 53.54, or re-derived from a fresh same-session null if the
  research step finds the harness conditions changed). On a powered shift: **ship plus one
  refit** of the strength curves and the blend>0 persona labels (as in 226 D-11/D-20, about one day
  of sweeps). The refit is skipped if there is no shift. Long sweeps run inline from the
  orchestrator (setsid nohup + Monitor) under the resume-on-crash supervisor, never in a
  backgrounded executor.
- **D-16:** If it ships: add a CHANGELOG `[Unreleased]` bullet ("faster bot moves and analysis
  search") and update `docs/flawchess-engine-explained-2026-07-06.md` (dispatch model).

### Claude's Discretion
The owner answered "no preference" on all four gray areas (tolerance and ship bar, WebGPU
measurement, in-flight semantics, rollout and calibration). They then set D-00 (first principles,
test-driven, the current engine is not gospel). D-01..D-04 and D-06..D-16 are Claude's recommended
defaults, revised to follow D-00, and recorded as decisions so planning can proceed. The owner may
edit any of them before `/gsd-plan-phase 227`. **D-01 (one-sided non-inferiority, margin about
0.025) and D-04 (≥ 15% bar) are the two most consequential.** The research step should check that
the 0.025 margin is sensible against the measured noise of the *signed* metric. It was derived from
an unsigned floor, and signed paired noise is smaller.

### Deferred Ideas (OUT OF SCOPE)
- **Dropping WebGPU Maia:** considered and rejected by the owner 2026-10-02. Revisit only if the D-06 measurement shows WebGPU is not clearly faster than wasm at batch 1 (would be a separate quick task).
- **Other concurrency levels** (for example above 4, to keep the Maia FIFO saturated at WebGPU-like P, `c* = 1 + G/P`): a test-driven question for its own phase, judged on quality against ground truth and on throughput.
- **Maia success telemetry** (backend share, per-inference latency in the field): would size L-6 from real users; not in scope.
- Still out of scope: cross-FEN Maia batching (revisit only with WebGPU numbers), Rust/WASM port, multithreaded SF, fp32/int8 Maia, Maia WDL leaf values (rejected), depth ladder / MultiPV tuning, server-side Maia (SEED-172).

#### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-08-29-variation-tree-nested-button.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`: keyword-match noise, unrelated (same set Phases 225/226 reviewed).

</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (`phase_req_ids` null). Coverage is driven by the CONTEXT decisions:

| Decision | Research support (section of this doc) |
|---|---|
| D-01 margin and test | Q1 "Signed-metric noise and the D-01 test" |
| D-02 repeats | Q3 "Repeat count" |
| D-03 net-regression allowance | Q2 "D-03 allowance, frozen as a formula" |
| D-04 throughput bar | Q8 "Throughput harness"; Pitfalls 1, 2, 5 |
| D-06/D-07 WebGPU tool | Q7 "Dev-only WebGPU measurement tool" |
| D-08..D-11 loop semantics | Q5 "Concrete code design" |
| D-12 review checklist | Q6 "Phase 198 findings: draft dispositions" |
| D-13/D-14 flag and parity | "Flag design and harness parity" |
| D-15 calibration | Q4 "Do the calibration thresholds need re-derivation?" |
| D-16 docs | "Rollout checklist" |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Pre-merge gate** before squash-merging to `main`: `ruff format`, `ruff check --fix`, `ty check app/ tests/ scripts/`, `ty check analysis/`, `check_function_size.py app/ --fail-over-depth 4`, `pytest -n auto -x`, and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`.
- **Nesting depth ≤ 4** in any function (eslint `max-depth` gates `npm run lint`). Soft target ≤ 100 logic lines and cognitive complexity ≤ 15. The continuous loop must be split along real seams (fill / await / drain), not with a state object threaded through helpers that always run together.
- **No magic numbers.** Named constants for every threshold (margin, repeat count, allowance formula inputs, bench sample counts).
- **Type safety.** `dispatchMode` must be a `Literal`-style union (`'round' | 'continuous'`), never a bare `string`. Python verdict twin uses `Literal[...]`, explicit return types, and passes `ty check scripts/`.
- **Comment bug fixes** at the fix site (applies to the harness abort fix and the Maia FIFO yield).
- **No `npm` package installs without a plan-scoped reason.** This phase needs none.
- **GSD scope.** Do not add unplanned features. Flag out-of-scope items (for example the pool tie-break, Pitfall 6) instead of silently implementing them.
- **Frontend rules** (`frontend/CLAUDE.md`): `data-testid` on every interactive element of the dev tool; semantic HTML; `text-sm` minimum; `noUncheckedIndexedAccess`; knip clean (a dev-only module must still be imported, and removed with its route at phase end); run `npm run build` (`tsc -b`) when shared types change (`SearchBudget` changes).
- **Memory rules in force:** engine is not gospel (judge vs d20, one-sided non-inferiority, net MQ); interleave throughput arms in one session; long operator runs go inline from the orchestrator (`setsid nohup` + Monitor), never backgrounded inside an executor; prove gap fixes by reverting them (mutation check); calibration sweeps run under `bin/preset-supervisor.sh` (resume-on-crash); no Stockfish 19 and no onnxruntime-web bump; no Maia WDL leaf values; run human-action checkpoints yourself and defer only hardware legs.

## Summary

The core change is small and well-bounded. `mctsSearch.ts`'s round loop (`:650-745`) dispatches up to `c` expansions, awaits `Promise.all` (`:723-725`), then applies results in input order with `signal.aborted` / `earlyStop` breaks (`:727-744`). Continuous mode keeps every primitive: `selectPath`, `dispatchExpansion`, `applyExpansion`, `stopRuleSatisfied`, the pending marks. It replaces only the barrier with a fill → await-one-settlement → drain-in-arrival-order loop, guarded by `applied + inFlight < maxNodes`, plus an inner `AbortController` that cancels stale work on stop. A `dispatchMode` field on `SearchBudget`, absent meaning `'round'`, keeps round mode byte-identical. That is the same "omitted = unchanged" pattern `stopRule` and `gradeRoot` already use. The relaxed contract makes 11 of the 26 Phase 198 findings moot outright, because they existed only to defend bit-identity.

The bigger risks sit in the **measurement harness**, not the engine. Three findings from this session matter most:
1. **The Node harness cannot observe overlap faithfully.** Its Maia is onnxruntime-web wasm with `numThreads = 1` on the main thread (`node-engine-providers.mjs:95`). Each inference blocks the event loop for its full duration (measured: max timer lag 94 ms at about 86-108 ms per inference). Worse, back-to-back FIFO inferences chain through microtasks only, so **no macrotask (timer or Stockfish stdout I/O) runs while the Maia FIFO is non-empty**: 0 timer ticks across a 373 ms, 4-request FIFO burst. In continuous mode, Stockfish completions would be starved until the FIFO drains, so the Node gate would measure a degraded continuous mode.
2. **The harness Stockfish pools ignore the abort signal** (`stockfish-pool.mjs:419-421`; `createGradePool` likewise). D-09's cancellation would not happen in Node. After an early stop, stale grades keep running into the next search's timing window, and they trip the root-split premise counter.
3. **CPU normalization as 226 defined it (wall ÷ Σ grade elapsed) is biased in continuous mode's favor.** `grade_cpu_ms` is per-grade wall-clock elapsed, not CPU time. Continuous mode makes Maia and Stockfish run at the same time, so contention raises grade elapsed and flatters the ratio. Interleaving already cancels machine drift. The judged throughput number should therefore be interleaved raw wall, with normalization against an external machine-speed probe, not the arm's own grade time.

On the statistics: on the 60-position fixture the signed metric is **quantized by move flips**. One flip of size about 0.45 moves the mean by about 0.0075. Round-vs-round noise is exactly 0 (A0a vs A0b, and A2 vs its fresh-process rerun: 0 of 60 positions differ). Under an exchangeable null, the signed metric's SD is 0.0075-0.0167, dominated by round mode's own frozen single draw on "fragile" positions, not by continuous-mode timing noise. The 0.025 margin (about 3.3 net full flips) is therefore 1.5-3.3 SD. Judge it as a **point estimate**: about 0.5-3% false-fail at 6-10 fragile positions. Do not judge it on a CI lower bound, which fails a genuinely neutral change 30% or more of the time. For D-03, the frozen allowance `max(1, ceil(max over repeat pairs |net flips|))` has about a 4-5% null false-fail at **R = 5** (about 8-10% at R = 3), so use R = 5.

**Primary recommendation:** Land harness fidelity first, in the A0 tooling commit: Maia off the Node event loop (or at minimum a macrotask yield), abort support in both Node SF pools, `--dispatch-mode` as a real switch in every gate script, a committed interleave driver with a machine-speed probe, `--repeats` for MQ, and `--ladder-only` for depth-ab. Prove round-mode content is unchanged by re-running round-mode MQ and diffing it byte-for-byte against 226's committed `a21s` TSVs. Then write the design doc and run the two independent reviews. Commit the accept rule before **any** continuous-mode run on the MQ fixture. Only then implement continuous mode behind `dispatchMode`, with the app constant still `'round'`. Run both arms from one checkout via the flag, and ship by flipping one constant.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Continuous dispatch loop (fill / await / drain, stop and abort semantics) | Browser main thread (`mctsSearch.ts`) | Node harness (same module via `@/` alias) | One `SearchRunner` shared by app and harness (algorithm parity, D-14) |
| Dispatch-mode selection | Shared config (`botBudget.ts` constant + `SearchBudget.dispatchMode`) | App hooks (`useBotGame.ts:123-128`, `useFlawChessEngine.ts:365-379`) | A single definition imported by app and harness prevents an app/harness desync (T-168.5-04-01 pattern) |
| Grade cancellation on stop | Browser SF `WorkerPool` (`workerPoolDispatch.ts:285-313`, already implements `stop`) | Node `stockfish-pool.mjs` / `createGradePool` (must gain it) | Cancellation lives below the `EngineProviders` boundary |
| Maia serialization | Browser Maia worker (`maiaQueue.ts`, one inference in flight) | Node `maiaFifo` (`calibration-providers.mjs:283-373`) | The harness must mirror the app's single in-flight inference *and* its off-main-thread execution |
| WebGPU measurement | Browser dev-only page (Vite dev server) | none | Needs a real GPU adapter, a secure context and cross-origin isolation |
| Verdict computation | Python verdict twin (`scripts/engine_dispatch_227_verdict.py`, new) | pytest (`tests/scripts/`) | Precedent: `engine_throughput_226_verdict.py` freezes the thresholds as constants |
| Calibration sweeps | Node harness + `bin/preset-supervisor.sh` | `scripts/calibration_parity_verdict.py` (reused) | Unchanged machinery; only the dispatch mode changes |

## Standard Stack

No new libraries. Everything needed exists in the repo.

### Core (existing, versions verified this session)
| Component | Version | Purpose | Note |
|---|---|---|---|
| onnxruntime-web | 1.27.0 `[VERIFIED: frontend/package.json:37]` | Maia in browser and harness (wasm) | **Do not bump** (owner decision, memory) |
| onnxruntime-node | 1.29.0 `[VERIFIED: scripts/package.json:6]` | Optional native Maia backend in the harness | Also blocks the event loop (measured, see Pitfall 1); not app-faithful |
| Stockfish | vendored 18 lite single wasm `[CITED: memory/SEED-171]` | Grades | **No Stockfish 19** |
| vitest | 5.0.0 `[VERIFIED: npx vitest --version]` | Engine unit tests | Existing patterns: `withJitter`, `makeFixedPolicy`, `makeVariedGrade` in `mctsSearch.test.ts` |
| Node | v24.19.0 `[VERIFIED: node --version]` | Harness runtime | `worker_threads` available |
| Python + uv + pytest | repo standard | Verdict twin + tests | Copy the `engine_throughput_226_verdict.py` shape |

**Installation:** none.

## Package Legitimacy Audit

Not applicable. This phase installs no external packages. **Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram (continuous mode)

```
             SearchBudget{dispatchMode:'continuous'}            outer AbortSignal (cancel / deadline cut)
                         │                                                  │ forwards
                         ▼                                                  ▼
  ┌──────────────── mctsSearch (main thread) ─────────────────┐   inner dispatchController
  │  FILL (sync): while inFlight<c && applied+inFlight<max:    │        │ aborts on: outer abort,
  │     selectPath(root, blockedThisFill) ─┬─ null → stop fill │        │ early stop, loop exit
  │                                        ├─ dead end → visit │        ▼
  │                                        │   bump + closure  │   cancels stale grades (SF `stop`)
  │                                        └─ leaf → isPending │   + drops queued Maia requests
  │                                            dispatch ───────┼──► dispatchExpansion(leaf, dispatchSignal)
  │  clear blockedThisFill (finally)                           │        │ policy() ─► Maia FIFO (1 in flight)
  │  if inFlight==0 && settled empty → done                    │        │ grade()  ─► SF WorkerPool (pool 2..4)
  │  AWAIT: one wake (sync check, single await)  ◄─────────────┼── .then(push settled; wake())
  │  DRAIN (arrival order): for each settled:                  │
  │     inFlight--; rejected → throw (finally cancels rest)    │
  │     aborted or earlyStop → discard (L-2 / D-09)            │
  │     applyExpansion → nodesEvaluated++ → stopRule → onSnapshot
  └────────────────────────────────────────────────────────────┘
                         │ final snapshot (return immediately, no drain of in-flight)
                         ▼
          selectBotMove / useFlawChessEngine / harness scripts
```

### Recommended file layout
```
frontend/src/lib/engine/
├── mctsSearch.ts                      # round loop kept verbatim; add continuous loop + shared apply helper
├── types.ts                           # SearchBudget.dispatchMode?: DispatchMode ('round' | 'continuous')
├── botBudget.ts                       # FLAWCHESS_DISPATCH_MODE constant (app + harness import it)
├── deadlineSearch.ts                  # doc-comment update only (overrun bound wording)
├── gradingLadder.ts                   # Y-14 comment fix (cache key)
└── __tests__/mctsSearch.continuous.test.ts   # new: D-08..D-11 tests
frontend/src/dev/engineBench/          # D-06 dev-only tool (removed at phase end unless tiny)
scripts/
├── lib/stockfish-pool.mjs             # abort → `stop` support (mirror workerPoolDispatch)
├── lib/calibration-providers.mjs      # maiaFifo off-main-thread / macrotask yield
├── engine-move-quality.mjs            # --dispatch-mode, --repeats, --maia-fifo, --grade-depth 20
├── engine-dispatch-stop-rule.mjs      # --dispatch-mode becomes a real switch; grade-time column; abort
├── engine-grading-depth-ab.mjs        # --dispatch-mode, --ladder-only
├── calibration-harness.mjs            # budget.dispatchMode from botBudget (override flag for arms); resume key
├── lib/calibration-determinism.check.mjs  # pin round for bit-identity + parity assertion
├── engine_dispatch_227_verdict.py     # verdict twin (frozen constants)
└── (driver) bin/engine_interleave_227.sh or scripts/engine_interleave_227.py  # committed interleave driver
reports/continuous-dispatch-227/       # design.md, accept-rule.md, report.md, overrides
tests/scripts/test_engine_dispatch_227_verdict.py
```

### Pattern 1: Flag with "omitted = round" (byte-identical default)
**What:** `dispatchMode?: 'round' | 'continuous'` on `SearchBudget`; `undefined` means round. The app call sites pass `FLAWCHESS_DISPATCH_MODE` (from `botBudget.ts`). The harness passes the same constant by default and accepts `--dispatch-mode` to select an arm.
**Why:** Every existing test, fixture gate and harness caller stays on round mode with zero edits, which discharges D-11 for free. This precedent is established at `types.ts:107` (`stopRule?: BotStopRule;`, "omitted/undefined = today's unchanged full-budget behavior") and `types.ts:61` (`gradeRoot?`). `selectBotMove` already spreads `settings.budget` into the search budget (`selectBotMove.ts:141-147`), so the field flows through without new plumbing.
**Ship mechanics:** The implementation commit sets `FLAWCHESS_DISPATCH_MODE = 'round'` (nothing ships yet). Both gate arms run from that one checkout via `--dispatch-mode`, so there are no per-arm worktrees and no content assertions on arm diffs. The ship commit flips the constant (one line) and rollback flips it back (L-5).

### Pattern 2: Settled queue + single-shot wake (no missing-wakeup)
**What:** Each dispatch's promise is wrapped with `.then(ok → push, err → push)` into a `settled` array and calls `wake`. The loop checks `settled.length` synchronously and only then creates a fresh `Promise<void>` whose resolver is stored in `wake`, with no other `await` in the loop body.
**Why:** It gives arrival order and drain-all for free. JS is single-threaded, so a settlement cannot land between the synchronous check and the resolver assignment, which closes X-8's missing-wakeup hazard by construction. Rejections are captured as values, so no unhandled rejection exists even after early return.

### Pattern 3: Inner dispatch controller
**What:** `const dispatchController = new AbortController()`. The outer `signal` forwards to it (`{ once: true }`, removed in `finally`), and **every** `dispatchExpansion` receives `dispatchController.signal`. On early stop, abort, rejection or loop exit, `dispatchController.abort()` runs in `finally`.
**Why:** This reuses the existing cancellation paths. On abort, `WorkerPool` dequeues an unstarted request, posts `stop` to an in-flight one, and settles `new Map()` (`workerPoolDispatch.ts:285-313`). A stopped search's partial accumulator is never written to the grade cache: the stale `bestmove` is discarded under `stopPending` (`:128-142`), and the only write site is the normal `bestmove` path (`:146-163`). `maiaQueue` drops unstarted requests and resolves `{}`, but cannot interrupt an in-flight ONNX inference (`maiaQueue.ts:60-69`). The pattern follows `deadlineSearch.ts:83-124` (two distinct signals). It also makes `dispatchExpansion`'s own `!signal.aborted` checks (`mctsSearch.ts:614`) see the inner signal, so a cancelled non-root grade is not mistaken for an 8XN-7 empty grade.

### Anti-Patterns to Avoid
- **Rebuilding commit-ordered apply, a ring buffer, or slot-release-on-commit.** These are explicitly not rebuilt (D-08). They existed only for bit-identity.
- **`Promise.race` over the in-flight set without tagging.** It works, but loses "drain all settled" and invites the R-3 accumulation argument. The settled queue is simpler.
- **Applying a result after `dispatchSignal.aborted`.** An aborted grade settles `new Map()`, and a missing grade becomes `NEUTRAL_EXPECTED_SCORE` (`mctsSearch.ts:459`). Applying it would fabricate 0.5-valued children (L-2).
- **Draining in-flight work before returning** ("no drain", D-09). Return immediately; the stale promises settle into a dead closure.
- **A silent `.catch` that drops a rejected dispatch** (Y-8). Rejections must propagate out of `mctsSearch`, as `Promise.all` does today.
- **Judging continuous MQ from a run that overlaps a calibration sweep.** Continuous content is now timing-dependent, so MQ is no longer "node-deterministic and safe to overlap" as 226 accept-rule §3 allowed.

## Q5: Concrete code design (cite file:line)

### Today's round loop (A21S, read this session)
- Fill loop `mctsSearch.ts:664-698`, guarded by `toExpand.length < budget.concurrency && nodesEvaluated + toExpand.length < budget.maxNodes`.
- Block flags cleared after fill `:708-709` (`for (const node of blockedThisRound) node.isBlocked = false;`).
- Barrier `:723-725` (`await Promise.all(toExpand.map(... dispatchExpansion(leaf, path, budget, providers, rootMover, signal)))`).
- Apply loop `:727-744`: `if (signal.aborted) break;` → `applyExpansion` → skip degenerate (`candidateMap.size === 0`) → `nodesEvaluated += 1` → `budgetExhausted` → stop rule → `onSnapshot` → `if (earlyStop) break;`.
- Root guard `:368` (`if (root.isPending || root.isClosed) return null;`). Blocking `:403-407`. Defensive null `:419`.

### Continuous loop (sketch, for the design doc and the reviewers)
```typescript
// Sketch only. Names are the planner's; semantics are the contract.
type Settled = { kind: 'ok'; result: DispatchedExpansion } | { kind: 'rejected'; error: unknown };

async function runContinuous(ctx: SearchContext /* root, budget, providers, rootMover, onSnapshot */,
                             st: SearchCounters /* nodesEvaluated, budgetExhausted, earlyStop, stopState */,
                             signal: AbortSignal): Promise<void> {
  const dispatchController = new AbortController();
  const settled: Settled[] = [];
  let wake: (() => void) | null = null;
  const notify = (): void => { const w = wake; wake = null; w?.(); };
  const forwardAbort = (): void => { dispatchController.abort(); notify(); };   // wake promptly on cancel
  if (signal.aborted) forwardAbort(); else signal.addEventListener('abort', forwardAbort, { once: true });
  let inFlight = 0;
  try {
    for (;;) {
      if (signal.aborted || st.earlyStop) return;
      inFlight += fillContinuous(ctx, st, inFlight, dispatchController.signal, (s) => { settled.push(s); notify(); });
      if (inFlight === 0 && settled.length === 0) return;          // tree fully searched / root closed
      if (settled.length === 0) await new Promise<void>((r) => { wake = r; });   // sole await; sync check above
      while (settled.length > 0) {                                  // arrival order, drain all
        const s = settled.shift()!;
        inFlight -= 1;
        if (s.kind === 'rejected') throw s.error;                   // Y-8: fail loudly (finally cancels siblings)
        if (signal.aborted || st.earlyStop) continue;               // L-2 / D-09: never apply after abort/stop
        applyAndReport(ctx, st, s.result);                          // SAME helper the round loop uses
      }
    }
  } finally {
    signal.removeEventListener('abort', forwardAbort);              // WR-02 lesson: no listener accumulation
    dispatchController.abort();                                     // D-09: cancel stale in-flight; no drain
  }
}
```
`fillContinuous` is the round fill loop body (`:664-698`) with three differences. (1) The guard is `inFlight + dispatched < concurrency && nodesEvaluated + inFlight + dispatched < maxNodes` (D-10). (2) Each leaf is dispatched immediately: `isPending = true`, then `dispatchExpansion(...).then(ok, err)`. (3) `blockedThisFill` is cleared in a `finally`.

### Scoping rule for `isBlocked` (state in the design doc)
**Blocks are scoped to one fill pass** (one synchronous top-up between two awaits). Justification: a node is blocked when every child is pending or closed (`:387-407`). The only events that un-pend a child are applies, and applies only happen in the drain phase, never inside a fill. A block set during fill *k* is therefore exact for the rest of fill *k* and possibly stale by fill *k+1*. Clearing at the end of every fill is both necessary and sufficient. This is the same argument as today's "round-scoped" clearing (`:700-709`), with "round" replaced by "fill". `isBlocked` is read only by `selectPath`, which is called only inside fill.

### Budget accounting (D-10) and a consequence the design must state
Invariant: `applied + inFlight ≤ maxNodes` at all times (dispatch increments `inFlight`; a settlement decrements it and increments `applied` only if non-degenerate). Consequence: **when `applied` reaches `maxNodes`, `inFlight` is already 0**, so "cancel in-flight on budget exhaustion" (D-09) is vacuous under D-10. Only early stop, abort and rejection ever cancel live work. A degenerate settlement (WR-04) lowers `inFlight` without raising `applied`, which reopens a slot, exactly as today (X-10's corrected reading). Total provider calls can exceed `maxNodes` by the degenerate count, unchanged from today.

### c = 1 byte-identity (D-11, X-12): why it holds, and the test
At c = 1, fill runs only when `inFlight === 0`, so it sees exactly the state round mode's c = 1 fill sees (every prior result applied). It dispatches at most one leaf, preceded by the same dead-end discoveries, in the same order. No block can be set at c = 1, because with nothing pending a node with zero selectable children has only closed children, and `propagateClosure` (`:337-343`, called at `:448`, `:484`, `:686`) has already closed it. The drain applies that one result with the shared helper, so snapshots, stop-rule evaluations and the final result are identical. **Test:** for several fixtures (plain, stop rule on, dead ends / `maxPlies` cut, degenerate empty candidate set, 8XN-7 empty grade, `extraRootMoves`, `gradeRoot` present), run both modes at c = 1 with *different* `withJitter` timings and `expect(continuous).toEqual(round)` on the full `onSnapshot` sequence and the final result. Because round mode is retained, the "golden" is computed live; no pre-rewrite fixture capture is needed (this simplifies X-12's operational consequence).

### Root guard (Y-9)
`selectPath` returns `null` while `root.isPending` (`:368`). In continuous mode the first fill dispatches only the root, then waits. The first wait is therefore always for the root alone, and the root split (`gradeRoot`, `:584`) already covers that grade. The design doc must state the base case this way (1 dispatch, then up to c), not as "c back-to-back dispatches".

### Things that change elsewhere (small)
- `deadlineSearch.ts:36-44` claims "overrun bounded by one dispatch batch ... inside a `budget.concurrency`-sized round". In continuous mode the cut still happens synchronously inside `onSnapshot` (`:97-104`), the next drain iteration sees `signal.aborted`, and in-flight work is cancelled. Reword the comment; the behavior is fine.
- After an early stop, an in-flight Maia inference (not interruptible) can delay the *next* search's first `policy()` by up to one P (about 63 ms wasm t=4 `[CITED: SEED-171 microbench]`). Round mode never has this, because an early stop only happens after the whole round resolved. Report-only; well under the stop-rule wall gains.
- `gradingLadder.ts:84-85` says the cache "keys on `(fen, candidateUcis, gradingDepth)`", but the actual key is `` `${fen}|${gradingDepth}` `` (`workerPool.ts:274-276`). This is Y-14, a one-line comment repair.

## Flag design and harness parity (D-13, D-14)

| Call site | Today (verified) | Change |
|---|---|---|
| `useBotGame.ts:123-128` `BOT_SEARCH_BUDGET` | `maxNodes: FLAWCHESS_BOT_MAX_NODES, maxPlies: ..., concurrency: FLAWCHESS_BOT_CONCURRENCY, stopRule: FLAWCHESS_BOT_STOP_RULE` | add `dispatchMode: FLAWCHESS_DISPATCH_MODE` |
| `useFlawChessEngine.ts:365-379` analysis budget | `concurrency: computePoolSize()` | add `dispatchMode: FLAWCHESS_DISPATCH_MODE` |
| `calibration-harness.mjs:594-603` bot budget | `concurrency: FLAWCHESS_BOT_CONCURRENCY, stopRule: FLAWCHESS_BOT_STOP_RULE` | add `dispatchMode` from botBudget (override only via explicit arm flag); **add it to the `--resume` compatibility check (`:1065-1070`)** so a resumed sweep cannot mix modes |
| `engine-move-quality.mjs:463-468`, `engine-grading-depth-ab.mjs:686-690,751-755`, `engine-dispatch-stop-rule.mjs` | no field (stop-rule's `--dispatch-mode` is label-only, `:36-46`) | real `--dispatch-mode round\|continuous` switch; stamp the mode into every TSV row |
| `calibration-determinism.check.mjs:430-440` | bot budget at `FLAWCHESS_BOT_CONCURRENCY` | pin `dispatchMode: 'round'` for the bit-identity assertion; add a parity assertion that the harness budget's mode `=== FLAWCHESS_DISPATCH_MODE` |

**Harness parity is about algorithm, but the timing model matters for content in continuous mode.** Continuous content depends on arrival order, and arrival order depends on how Maia and Stockfish interleave. That makes Pitfalls 1 and 2 parity issues, not only throughput issues. The calibration harness also uses `maiaFifo: false` (`calibration-harness.mjs:390`; `calibration-providers.mjs:364-365` `const { maiaFifo = false, gradeRootFn } = options;`), so Maia calls are not serialized the way the app's are. For continuous mode, the harness must use the app-faithful FIFO. This is content-neutral for round mode, which is timing-independent; prove it with the round-mode diff tripwire.

## Q1: Signed-metric noise and the D-01 test

**Measured from committed 226 MQ TSVs** (`reports/data/engine-throughput-226/{step0/mq,gate/*}/mq-{off,on}/*.tsv`, 60 positions, column `es_bot`, grade depth 18) `[VERIFIED: computed this session]`:

| Paired comparison | mean signed Δes | SD | SE (n=60) | positions differing |
|---|---|---|---|---|
| A0b − A0a (off / on) | 0.0000 / 0.0000 | 0 | 0 | 0 / 0 |
| A2 rerun − A2 (fresh process) | 0.0000 | 0 | 0 | 0 |
| A2 − A0a (off) | −0.0095 | 0.0737 | 0.0095 | 1 (cBFTV −0.571) |
| A21S − A21 (off) | +0.0084 | 0.0743 | 0.0096 | 2 (cBFTV +0.571) |
| A21S − A21 (on) | +0.0083 | 0.0556 | 0.0072 | 2 (Dj8iG +0.426) |

Readings:
- **Round-vs-round signed noise is exactly 0.** So the anchor really is the content-instrument floor, as D-01 says.
- **The metric is quantized by flips.** On this puzzle fixture (one clear best move, d20 gap ≥ 150 cp), a changed pick is typically a 0.4-0.6 es swing. One flip moves the 60-position mean by about 0.0075. **The 0.025 margin ≈ 3.3 net full-size flips over 60 positions (about 5.6% of the fixture).** The accept rule should state the margin in this unit too, so the owner reads it correctly.
- **The 0.0168 anchor is unit-mismatched** (candidate-weighted grade-content |Δes| vs picked-move es). It is a defensible order of magnitude, not a derived noise SD. Keep 0.025 as locked; do not present it as "k × measured noise of this metric".

**Null model and simulation** `[ASSUMED model; simulation run this session]`. Assume continuous mode is round mode with randomized tree shape. Then on K "fragile" positions the pick flips with probability about 0.5, and round mode's deterministic pick is one frozen draw of the same distribution. Pooled over R repeats:

| K fragile positions | SD of signed mean (R=3 / R=5) | P(mean < −0.025) under null | P(fail) if continuous truly adds +0.3 regression prob on fragile positions |
|---|---|---|---|
| 3 | 0.0075 / 0.0071 | 0.000 | ~0 (true mean −0.007) |
| 6 | 0.0107 / 0.0102 | 0.005 | 0.10-0.13 (true mean −0.0135) |
| 10 | 0.0137 / 0.0130 | 0.028 | 0.40-0.43 (true mean −0.0225) |
| 15 | 0.0167 / 0.0160 | 0.06 | 0.68-0.72 (true mean −0.034) |

The evidence on K: 226's tree-shape perturbations flipped 1-2 of 60 positions each, and the root argmax flip rate under warm content was 7.9% (`design-inputs.md` §6). That puts K plausibly in the 3-10 range.

**Answer:** 0.025 is sensible. It is about 1.5-3.3 SD of the null signed metric for plausible K, and ≥ 4 SD of the pure continuous timing component (which R averages down). **R barely changes the SD**, because the dominant term is round mode's own frozen draw, which cannot be repeated away. That is an important, non-obvious result.

**Recommended test (freeze in the accept rule):**
- **Decision statistic:** the point estimate `D = mean_i [ mean_r es_cont(i,r) − mean_r es_round(i,r) ]` over the 60 fixture positions, bot selector (`argmaxLine`). **Pass iff D ≥ −0.025.**
- **Do not use a CI lower bound as the decision rule.** A bootstrap 95% one-sided LCB over positions passes a neutral change only about 70% of the time at K = 10, R = 3 (simulated this session), which is unacceptable as a blocking rule.
- **Report-only:** bootstrap LCB (resample positions, repeats kept together), K = number of positions whose continuous picks disagree across repeats, the unsigned mean |Δes|, the McNemar p, and the analysis selector (`rankedLines[0]`).
- **Cells:** judged at 50 nodes c4 pool 4, **stop on** (the shipped bot path) **and stop off** (226 precedent, which isolates search quality from the stop rule). The 400-node analysis cell is report-only with R = 3; it costs about 23 min per repeat per arm.
- **Grade depth:** the MQ script defaults to `DEFAULT_GRADE_DEPTH = 18` (`engine-move-quality.mjs:92`), but D-01 says d20. Pass `--grade-depth 20` explicitly and record it in the rule. `nodeGrade` already clears hash per call (`calibration-providers.mjs:435`, `{ clearHash = true } = {}`), so grading is a pure function of `(fen, {pick, correct}, depth)`.
- **Fixture power:** widening the fixture halves the flip quantum and cuts the between-position error; repeats do not. If the owner wants more power, rebuild with a larger quota using the same deterministic SHA-1-ordered rule (`build-move-quality-fixture.mjs:91` `export const PER_BAND_QUOTA = 8;`). Raising the quota keeps the first 60 rows (first-N-in-SHA-1-order) `[ASSUMED: rule text says "first PER_BAND_QUOTA keepers per band in SHA-1 order"]`. Optional; the locked default is the 60-row fixture.

## Q2: D-03 allowance, frozen as a formula (no peeking)

**Why a formula, not a pre-measured number:** round-mode MQ for A21S is already known. It is deterministic and committed in 226 (`gate/a21s/mq-{off,on}`). Any continuous-mode run on the fixture before the accept rule is committed would reveal the verdict to the rule's author. So the rule must be committed **before any continuous-mode run on the MQ fixture**, and the allowance must be computed mechanically from the gate's own continuous repeats.

**Definitions (freeze in the rule and its verdict twin):**
- Per position *i*, `reg_round(i)` ∈ {0,1} (stable across round repeats; a nonzero round-repeat difference invalidates the run), and `ρ_cont(i)` = fraction of the R continuous repeats where `verdict_bot == "regression"` (`delta_bot < −REGRESSION_MARGIN`, `REGRESSION_MARGIN = 0.05` at `engine-move-quality.mjs:95`).
- **Net** = `Σ_i ρ_cont(i) − Σ_i reg_round(i)`. Fractional is fine. Fixes count in continuous's favor (D-03).
- **Allowance** `A = max(1, ceil( max over repeat pairs r<s of |N_rs| ))`, where `N_rs` = (pass→regression) − (regression→pass) between continuous repeats r and s.
- **Pass iff Net ≤ A.**

**Sizing** `[ASSUMED model; simulated this session, 20k sims]`: under the exchangeable null, with K fragile positions at π = 0.5:

| K | R=3: null false-fail (mean A) | R=5: null false-fail (mean A) |
|---|---|---|
| 3 | 0.081 (1.5) | 0.048 (1.9) |
| 6 | 0.100 (2.1) | 0.044 (2.8) |
| 10 | 0.102 (2.7) | 0.042 (3.6) |

A "median over pairs" allowance gives 12-16% null false-fail; reject it. With R = 5 (10 pairs), the max-pair allowance is about a 2-SD band, which matches 226's "no-effect change fails ≤ ~5%" sizing philosophy (D-10).

## Q3: Repeat count (D-02)

**Recommend R = 5** for continuous mode, in both judged cells. Reasons:
- D-03's allowance is well calibrated at R = 5 (about 4-5% null false-fail) and too tight at R = 3 (about 8-10%).
- D-01 is insensitive to R (the round-draw term dominates), so R = 3 would do for D-01 alone.
- Cost is small. 226's MQ took about 10.2 min search wall per stop-off pass and about 2.8 min per stop-on pass (computed from the `wall_ms` column). R = 5 × (off + on) is about 65 min per arm plus d20 grading.

Round mode also gets R repeats (D-02). This is a free determinism tripwire: any round-repeat difference marks the run **invalid** (a harness leak), not noise. Run all continuous MQ on an **idle box** (load < 2.0, no sweeps, no `remote_eval_worker`), because continuous content is timing-dependent (Pitfall 8).

## Q4: Do the calibration thresholds need re-derivation (D-15)?

**No re-derivation needed; reuse `CALIBRATION_THRESHOLD_MAIA` 85.0 and `CALIBRATION_THRESHOLD_SF` 53.542812708469995** `[VERIFIED: reports/engine-throughput-226/accept-rule.md §2 table, values "85.0" and "53.542812708469995"]`. Evidence:
- **Harness code unchanged since the null was taken.** `git log --since=2026-09-27` over `scripts/calibration-harness.mjs`, `scripts/lib/`, `bin/preset-supervisor.sh`, `bin/run_persona_calibration_sweep.sh`, `scripts/package.json` and `frontend/package.json` shows only `d0f5cb2ba` (the 226 squash, which *contains* the tooling the A0a/A0b null ran on). Engine content changed (A0 → A21S), but the null measures sampling noise, not engine identity.
- **The null was already unpaired.** A0b ran on seed 2 vs A0a on seed 1 (226 D-19), giving pooled se Maia 26.14 and SF 27.32 (`design-inputs.md` §3). Continuous mode destroys same-seed pairing (Maia-anchor games no longer byte-identical, D-14), so A1-vs-A0 noise approaches the *unpaired* null. That is exactly what the thresholds were sized on. 226's paired arm comparisons had about the same se (27.0-27.4), so losing pairing costs little.
- **Caveat if the 227 harness changes land:** the Maia FIFO change and the SF abort change alter timing only. Round-mode content is timing-independent (proven by the MQ diff tripwire), so they do not move the null for A0.
- **The null-control cell (human1100, blend 0) is untouched by search changes** (226: `a21s human1100: calls=0`, structural). It still validates each comparison.

**Run plan:** same-session A0 (round, A21S) and A1 (continuous), seed 1, 50 games per (cell, anchor), five runbook cells, pinned `PRESET_SUPERVISOR_ANCHORS`, under `bin/preset-supervisor.sh`. Budget: 226's ten cells took about 12.7 h (`226-07-SUMMARY.md:37`), so two arms take about 13 h. **Optional cost saver (owner call):** 226's committed `a21s-cells.json` is A21S content from about 2026-09-30 with identical harness code. Using it as A0 would save about 6.5 h but breaks "same session"; D-15 says same session, so keep it unless the owner overrides. Each new arm needs a powered verdict via `calibration_parity_verdict.py` plus the 226 `powered_verdict` logic (reuse `engine_throughput_226_calibration.py`'s reducer).

## Q6: Phase 198 findings, draft dispositions (for the design doc)

| ID | Draft disposition | Reason / repair (file:line) |
|---|---|---|
| X-1 drain granularity | **Moot** | No commit window. Arrival-order drain-all-settled is allowed; no claim that selection *n* sees a fixed prefix at c > 1 |
| X-2 throughput formula, WebGPU retraction | **Applies** | Prior = `min(1/P, poolSize/G, c/(P+G))`. Slot occupancy is still P+G because `dispatchExpansion` awaits policy (`:533`) then grade (`:586`). Reduction peaks at `P = G/(c−1)`; WebGPU P lowers it. D-06/D-07 measures it |
| X-3 non-commit tree mutation (dead ends) | **Moot under relaxed contract (D-11)** | Dead-end visit bumps / closure (`:679-687`) happen in fill as today. No induction claim needed. Correctness unchanged: round mode already mutates during fill with same-round leaves pending |
| X-4 pool < c live in prod | **Applies** | `MOBILE_POOL_SIZE = 2` (`workerPoolState.ts:106`), `DESKTOP_POOL_MAX = 4` (`:100`), `computePoolSize` returns 2 on low-power/coarse-pointer and `min(4, max(2, cores−2))` otherwise (`:502-506`). The bot pins `FLAWCHESS_BOT_CONCURRENCY = 4` (`botBudget.ts:64`). Gate: Node pool-2 configs (D-04). See Pitfall 6 for the dequeue order |
| X-5 heterogeneous latency, head-of-line | **Moot (HOL)** / applies (variance) | No commit order, so a cheap d10 grade frees its slot immediately. The mean model still cannot see variance; the measured wall is the judge |
| X-6 grade-cache settlement race | **Moot under relaxed contract (D-11)** | State it explicitly: order may change cache hit/miss and therefore content. Root-split shards bypass cache reads and writes (`workerPoolDispatch.ts:213-224`, `:158-163`) |
| X-7 three `selectPath` null sites | **Applies, semantics preserved** | null with `inFlight > 0` means wait; with `inFlight == 0` means done. The defensive `!chosen` (`:419`) behaves exactly as in round mode (break → complete); no busy spin, because the loop awaits a settlement. No new code; optional dev assertion |
| X-8 missing wakeup | **Repaired by construction** | Pattern 2: synchronous `settled.length` check immediately before the single `await`; no other await in the loop. Unit test settles during drain |
| X-9 stuck promise | **Moot** | Real providers foreclose it (WorkerPool watchdog/onerror resolve empty; `maiaQueue` resolves `{}`). Continuous is never worse than round here |
| X-10 WR-04 under-dispatch claim | **Applies (corrected form)** | Degenerate closes reopen slots; the window under-fills only over the last c−1 nodes; provider calls can exceed maxNodes by the degenerate count (unchanged). See D-10 consequence above |
| X-11 one grade per expansion; pool<c baseline | **Applies** | `G/min(c,pool)`; baseline `⌈c/pool⌉·G`. Mobile figures are measured (Node pool 2), never asserted from the model |
| X-12 c=1 byte-identity | **Applies, adopted (D-11)** | Live golden via the retained round mode; test list above |
| Y-1 browser not bit-identical | **Moot (resolved by contract, 226 D-05)** | The gate runs the warm-hash configuration (D-02) |
| Y-2 "queue order cannot affect output" | **Moot** | No priority activation in 227 (`priority: 0, depth: 0` stays, `workerPoolDispatch.ts:255-262`); the doc makes no such claim |
| Y-3 abort applies a result | **Applies → repaired** | Check `signal.aborted` / `earlyStop` before every apply; inner controller; unit tests (settle-after-abort, settle-after-early-stop) |
| Y-4 barrier is only half a barrier | **Moot** | Acknowledged; no ordering machinery |
| Y-5 X-5 arithmetic | **Moot** | X-5's HOL argument is moot |
| Y-6 refill stalls on stuck commit head | **Moot** | Slots free on resolution |
| Y-7 discriminated result inside `selectPath` | **Moot** | Loop distinguishes by `inFlight`, outside `selectPath` |
| Y-8 `.catch` silently prunes | **Applies → repaired** | Rejection propagates (as `Promise.all` today) after the inner abort cancels siblings; rejections are captured as values so there is no unhandled rejection |
| Y-9 root guard base case | **Applies** | First wait is the root alone; covered by `gradeRoot` |
| Y-10 stale 198 report text | **Moot** | Closed-phase doc; 227 cites the corrected model only |
| Y-11 superseded R-5 disposition | **Moot** | 227 states oversubscription is live (X-4) |
| Y-12 "the truth is the reverse" overstated | **Applies (wording)** | Say "non-monotonic in P, peak at `P = G/(c−1)`" |
| Y-13 recompute hygiene; c=8/16 rows | **Applies (hygiene)** | Label recomputed numbers as model; no c > 4 rows (`DESKTOP_POOL_MAX = 4`) |
| Y-14 wrong cache-key comment | **Repaired** | `gradingLadder.ts:84-85` → key is `` `${fen}\|${gradingDepth}` `` (`workerPool.ts:274-276`) |

**New items the reviewers should also see:**
- **N-1 (harness event-loop starvation, Pitfall 1).** Load-bearing for D-04 and D-14.
- **N-2 (harness pools ignore abort, Pitfall 2).**
- **N-3 (app pool dequeue tie-break, Pitfall 6).**
- **N-4 (CPU-normalization bias, Pitfall 5).**

**Reviewer briefing:** name the claims to attack:
- (a) blocks scoped per fill are exact;
- (b) `applied + inFlight ≤ maxNodes` and `inFlight == 0` at budget exhaustion;
- (c) c = 1 byte-identity;
- (d) no result is ever applied after abort or early stop;
- (e) no missing wakeup;
- (f) the harness measures the same algorithm with app-faithful timing.

## Q7: Dev-only WebGPU measurement tool (D-06)

**Where:** `frontend/src/dev/engineBench/EngineBenchPage.tsx` (+ small helpers). Mount it in `App.tsx` as a route **outside** the auth wrappers, inside `{import.meta.env.DEV && <Route path="/dev/engine-bench" ... />}` with a `lazy()` import, following the existing compile-time gate pattern (`lib/devClock.ts:26-27`: `export const DEV_CLOCK_ENABLED = import.meta.env.DEV;`; `pages/Admin.tsx:43-48`). Verify the tree-shaking: after `npm run build`, grep `dist/` for a unique marker string from the page, and expect zero hits.

**What it measures and reports** (a copy-to-clipboard JSON plus an on-page table):
1. **Environment:** UA, `navigator.hardwareConcurrency`, `computePoolSize()`, `isSecureContext`, `crossOriginIsolated`, `navigator.gpu` present, adapter `shader-f16` (the same probe as `ortRuntimeSource.ts` `probeOrtBackend`), the backend and `numThreads` reported in the worker's `ready` message (`maiaWorkerHost.ts:135`).
2. **Maia batch-1 latency per backend.** Construct a dedicated `Worker(ENGINE_PATH)` per backend (wasm via `fetchWasmOnlyOrtRuntime()`; webgpu via the asyncify runtime `ORT_RUNTIME_ASYNCIFY_PATH`) with the same init message shape as `constructWorker` (`maiaWorkerHost.ts:525-540`). This leaves the shipped singleton untouched. Warm up 5, then measure 30 single-FEN analyzes: median, p90.
   - **Idle** vs **SF-busy:** a `WorkerPool` with `computePoolSize()` slots kept saturated with long fixed-depth grades on a fixed FEN.
3. **Bot-move wall, round vs continuous:** `selectBotMove` with the real `maiaQueue` + `WorkerPool` (+ `gradeRoot`) and `BOT_SEARCH_BUDGET` with `dispatchMode` set per arm. About 6 fixture positions × 3 interleaved rounds, rotated order, labeled with the active backend. This leg exists only once continuous mode is implemented. Per D-07, the round-mode leg (1 + 2 + round-only 3) runs **early**.
4. **Refuse to run** (show a red banner) if `!isSecureContext || !crossOriginIsolated`.

**How the owner runs it** (hardware leg only): either a checkout on the WebGPU machine with `cd frontend && npm ci && npm run dev`, or an SSH tunnel to this box's dev server (`ssh -L 5173:localhost:5173 <this-box>`, then open `http://localhost:5173/dev/engine-bench`). Vite dev already sends COOP/COEP on every response (`vite.config.ts:43-44`, plus the middleware at `:57-71`). **Do not** open `http://<LAN-IP>:5173`: it is not a secure context, so `navigator.gpu` and `SharedArrayBuffer` are unavailable and the page would silently measure single-thread wasm (Pitfall 9).

**D-07 blocking point (freeze in the rule):** on the WebGPU machine, continuous/round bot-move wall ratio ≤ **1.03** (the same 3% no-regression tolerance as D-04), median over ≥ 3 interleaved rounds. Phase 198's prior predicts a gain (see the model table below), so failure would be informative.

**Removal:** delete the page and route at phase end (it will be more than a few lines); knip will then flag any orphaned helper.

## Q8: Throughput harness (D-04): what exists, what to add

| Arm | Existing script | Status | Must add |
|---|---|---|---|
| Bot-move path (stop on, 50 nodes, c4, pool 4, 16 positions) | `engine-dispatch-stop-rule.mjs` (accept-rule §3 command) | `--dispatch-mode` is **label-only** (`:36-46`); no grade-time column (226 report: "the stop-rule run carries no grade-CPU column") | Real switch; grade-busy-time column; Node pool abort (Pitfall 2); per-position quiesce |
| Analysis (400 nodes, c4, pool 4) | `engine-grading-depth-ab.mjs --nodes 400 --depths 14 --ladder --procs 4 --pool-size 4 --maia-fifo --openings 12` | Judged rows are `depth == "ladder"` only, but the script also runs a full flat-d14 pass (why 226's t400-p2 re-test took about 50 min/run) | `--dispatch-mode`; **`--ladder-only`** to skip the flat pass |
| Node pool-2 (t50-p2: c4/pool 2; t400-p2: c2/pool 2) | same depth-ab script | — | same as above |
| Interleaving driver | **not committed** (only `reports/data/engine-throughput-226/retest-2026-10-02/driver.log` exists: load-average gate < 2.0, rotated order) | — | A committed driver (bash or Python) that runs A0/A1 alternately per config with rotated order, ≥ 3 rounds, logs `/proc/loadavg` before each step, and runs a **machine-speed probe** (fixed Stockfish `bench` or a fixed-depth grade set, about 15 s) before each step |

**Model prior from 226's committed throughput TSVs** `[VERIFIED: computed this session from gate/a21s/throughput/*]` (Node, Maia FIFO, single-thread wasm Maia):

| Config | P (ms) | G (ms) | c* | modelled reduction (corrected X-2 form) |
|---|---|---|---|---|
| t50-p4 | 83.3 | 173.9 | 3.09 | 34% |
| t400-p4 | 85.1 | 143.7 | 2.69 | 30% |
| t50-p2 (c4 pool2) | 83.3 | 169.9 | 3.04 | ~50% (model only; X-11 says do not publish) |
| t400-p2 (c2 pool2) | 83.1 | 75.5 | 1.91 | 31% |

Browser prior `[ASSUMED: P from SEED-171 microbench, G from Node]`: bot wasm t=4 (P≈63, G≈174) ≈ 41%; analysis (G≈144) ≈ 36%; WebGPU at P≈15 ≈ 19% (bot) and 22% (analysis). All of these are above D-04's 15% on paper. **The Node numbers are only reachable if Pitfall 1 is fixed;** otherwise Stockfish completions are starved while Maia works.

**Judged metric: recommend amending D-04's wording** (Claude's-discretion default, owner may confirm). Judge **interleaved raw wall**: the geometric mean over rounds of the per-round A1/A0 ratio. Report wall ÷ external-probe time and wall ÷ Σ grade-elapsed alongside. Reason: Pitfall 5.

**Pool-2 noise (freeze as formula):** `noise = max over rounds |A0_r / median(A0) − 1|`, from the same interleaved session; pool-2 passes iff the median A1/A0 ratio ≤ 1 + max(noise, 0.03). t400-p2 cost: about 12 min per ladder-only run, so 3 rounds × 2 arms is about 75 min.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Grade cancellation in the app | A new cancel path | `dispatchController.signal` into the existing `grade(..., signal, depth)` → `workerPoolDispatch.ts:285-313` | Already handles queued vs in-flight, stop watchdog, and no cache write on abort |
| Maia request dropping | Queue surgery | `policy(fen, elo, side, signal)` (`maiaQueue.ts:69`) | Drops unstarted requests and resolves `{}` |
| Deterministic apply ordering | Ring buffer / commit window | Nothing (D-08) | Only needed for bit-identity |
| Powered calibration verdict | New statistics | `calibration_parity_verdict.py` + 226 `powered_verdict` reducer | Thresholds and z-guard already frozen and tested |
| MQ fixture | New position set | `fixtures/engine/move-quality-226.tsv` (60 rows) | Committed; selection rule frozen |
| Verdict twin | Ad hoc notebook | Copy `scripts/engine_throughput_226_verdict.py` structure (constants, `gates`, `design-inputs` and `reruns` subcommands, pytest) | Grep-verifiable frozen constants |
| Interleaving | Manual reruns | One committed driver | The 226 driver was ad hoc and is lost (only the log is committed) |
| Root fan-out in continuous mode | Any change | Existing `gradeRoot` (root only, live idle slots) | The root is always the first and only dispatch (Y-9) |

## Runtime State Inventory

Not a rename or migration phase. **Stored data:** none, since no DB schema or keys change; the grade cache and Maia policy cache are in-memory per tab. **Live service config:** none. **OS-registered state:** none. **Secrets/env vars:** none. **Build artifacts:** the vendored engine assets are unchanged, so no Cloudflare purge is needed. One caveat: if the dev tool were ever served from prod, it must not be; it is tree-shaken. Verified by reading the call sites and the asset list above.

## Common Pitfalls

### Pitfall 1: Node harness Maia starves Stockfish I/O (event-loop blocking)
**What goes wrong:** In continuous mode the harness applies Stockfish results late, so it measures a crippled continuous mode and an unfaithful arrival order.
**Why:** The harness Maia is onnxruntime-web wasm with `ort.env.wasm.numThreads = 1` on the main thread (`node-engine-providers.mjs:95`). Measured this session:
- One inference blocks the event loop (max timer lag 94.2 ms at about 86-108 ms per inference).
- Four FIFO-queued `policy()` calls ran back-to-back with **0 timer ticks over 373 ms**: the FIFO chains the next inference in a `.then` (`calibration-providers.mjs:316-331`), so no macrotask (including child-process stdout) runs until the FIFO drains.
- onnxruntime-node also blocks (max lag 178.8 ms).
- In the browser, Maia runs in a worker and the main thread stays free.
**How to avoid:** Move harness Maia into a Node `worker_threads` worker (faithful), or at minimum `await new Promise(r => setImmediate(r))` before each FIFO dispatch (lets Stockfish I/O through between inferences; still blocked during each one). Add a check that records max event-loop lag during a search. Prove round-mode content unchanged with the MQ round-repeat diff against 226's `a21s` TSVs.
**Warning signs:** continuous t50-p4 gain far below the model's about 34%; `maia_peak_inflight` fine but SF utilization flat.

### Pitfall 2: Harness Stockfish pools ignore the abort signal
**What goes wrong:** After an early stop (MQ stop on, stop-rule throughput, calibration bot moves), stale grades keep engines busy into the next position's timing window. `newGameAll`'s `ucinewgame` lands mid-search. The root-split tripwire (`freeCount() !== size`) fires, and 226's validity rule (0 premise violations) would mark continuous runs invalid.
**Why:** `stockfish-pool.mjs:419-421`: "`signal` is accepted but deliberately NOT acted on: the Node pool has no abort path today". `createGradePool.grade` (`engine-dispatch-stop-rule.mjs:340-343`) ignores it too.
**How to avoid:** Implement abort in `withEngine`/`runOneGo`/`nodeGrade`, mirroring `workerPoolDispatch.ts:285-313`: unstarted means drop from waiters; in-flight means send `stop`, discard the result, and release the engine on `bestmove`. The scripts also await pool quiescence before starting each position's timer. The 227 rule must not require 0 premise violations for the continuous arm; record them report-only.

### Pitfall 3: Running the accept rule after seeing continuous MQ data
**What goes wrong:** Round-mode MQ is deterministic and already committed (226 `a21s`). Any continuous run on the fixture reveals the D-01 and D-03 verdicts.
**How to avoid:** Commit the rule and the twin before any continuous-mode MQ run. Unit tests and the D-06 round-only leg are fine before it.

### Pitfall 4: Harness Maia not app-faithful in MQ and calibration
**What goes wrong:** `engine-move-quality.mjs:462` and `calibration-harness.mjs:390` build providers without `maiaFifo`, so Maia calls run unserialized. That is harmless in round mode and wrong for continuous mode, where arrival order shapes the tree.
**How to avoid:** `maiaFifo: true` everywhere a continuous arm runs (after the Pitfall 1 fix). Verify round content unchanged.

### Pitfall 5: CPU normalization flatters continuous mode
**What goes wrong:** 226's "grade CPU" is per-grade wall-clock elapsed (`engine-grading-depth-ab.mjs:316-326`, `performance.now()` around `go`…`bestmove`). Continuous mode runs Maia and Stockfish at the same time, so contention inflates per-grade elapsed and wall ÷ Σ elapsed improves even when raw wall does not.
**How to avoid:** Interleave (drift cancels) and judge raw interleaved wall. Normalize by an external machine-speed probe, not by the arm's own grade time. Report both.

### Pitfall 6: App pool dequeue is not FIFO, which risks starvation at pool < c
**What goes wrong:** `dequeueHighestPriority` breaks ties by ascending `candidateUcis[0]`, "NEVER by insertion/arrival order" (`workerPoolState.ts:443-468`). Every request is `priority: 0, depth: 0`. In continuous mode at pool 2 / c 4, a queued grade can repeatedly lose to newer requests with lexicographically smaller first UCIs; round mode bounds the wait to one round. The Node harness pool is FIFO (`stockfish-pool.mjs:81,104`), so the pool-2 gate **cannot see this**.
**How to avoid:** The design decides. Recommended: add a monotonic enqueue sequence as the final tie-break (FIFO among equals) so app and harness agree. This touches `workerPoolState.ts` and its tests, so flag it to the planner as an in-scope prerequisite for continuous mode on mobile. Alternatively, add a unit test that bounds the wait.

### Pitfall 7: Listener and closure leaks on the outer signal
Forward the outer abort with `{ once: true }` and **remove** it in `finally` (lesson from `workerPoolDispatch.ts:271-279`, "a 400-node analysis search accumulated ~400 of them"). Late settlements push into a dead closure, which is fine. Never attach per-dispatch listeners to the outer signal.

### Pitfall 8: Continuous MQ is timing-dependent, so it is no longer safe to overlap
226's accept rule allowed MQ to overlap sweeps because MQ was node-deterministic (accept-rule §3 "Sequencing"). Continuous MQ must run on an idle box and never overlap a sweep or test suite. Round repeats must show 0 diffs, or the run is invalid.

### Pitfall 9: WebGPU tool opened over LAN HTTP
Without a secure context there is no `navigator.gpu` and no cross-origin isolation, so the page silently measures single-thread wasm. The tool refuses to run unless `isSecureContext && crossOriginIsolated`; use localhost or an SSH tunnel.

### Pitfall 10: Calibration resume mixing modes
`--resume` checks only `maxNodes`/`maxPlies` (`calibration-harness.mjs:1065-1070`). Add `dispatchMode` to the resume key and to the ledger rows, or a resumed A1 sweep could include A0 games.

### Pitfall 11: Long runs inside executors
Every gate run (MQ, throughput, sweeps, the WebGPU round leg's automation) runs inline from the orchestrator (`setsid nohup` + Monitor; sweeps under `bin/preset-supervisor.sh`). Executors die on long runs (memory).

## Code Examples

### Fill pass with per-fill block scoping (derived from `mctsSearch.ts:657-709`)
```typescript
// Returns how many leaves were dispatched in this fill.
function fillContinuous(ctx: SearchContext, st: SearchCounters, inFlight: number,
                        dispatchSignal: AbortSignal, onSettle: (s: Settled) => void): number {
  const blockedThisFill: EngineNode[] = [];
  let dispatched = 0;
  try {
    while (inFlight + dispatched < ctx.budget.concurrency &&
           st.nodesEvaluated + inFlight + dispatched < ctx.budget.maxNodes) {      // D-10
      const path = selectPath(ctx.root, ctx.budget.maxPlies, blockedThisFill);
      if (path === null) break;
      const leaf = path[path.length - 1];
      if (leaf === undefined) break;
      if (leaf.isExpanded) { discoverDeadEnd(ctx, st, leaf, path); continue; }   // same body as :673-688
      leaf.isPending = true;
      dispatched += 1;
      dispatchExpansion(leaf, path, ctx.budget, ctx.providers, ctx.rootMover, dispatchSignal).then(
        (result) => onSettle({ kind: 'ok', result }),
        (error: unknown) => onSettle({ kind: 'rejected', error }),
      );
    }
  } finally {
    for (const node of blockedThisFill) node.isBlocked = false;   // scope = one fill pass
  }
  return dispatched;
}
```

### Settle-after-abort unit test shape (vitest, deferred providers)
```typescript
// Source: pattern from mctsSearch.test.ts (withJitter/makeFixedPolicy); deferreds instead of timers.
it('continuous: a grade that settles after abort is never applied (L-2/Y-3)', async () => {
  const gate = deferred<Map<string, MoveGrade>>();
  const controller = new AbortController();
  const snapshots: EngineSnapshot[] = [];
  // root grade resolves immediately; the first non-root grade is held on `gate`
  const run = mctsSearch(FEN, { ...budget, concurrency: 4, dispatchMode: 'continuous' },
    providersHoldingSecondGrade(gate), (s) => snapshots.push(structuredClone(s)), controller.signal);
  await flushUntil(() => snapshots.length === 1);
  controller.abort();
  gate.resolve(realLookingGrades());          // settles AFTER abort
  const final = await run;
  expect(snapshots.length).toBe(1);            // nothing applied post-abort
  expect(final.nodesEvaluated).toBe(1);
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Round barrier, input-order apply (bit-identical per c) | Async tree search: pending exclusion + arrival-order apply (relaxed, statistical contract) | 227 | Overlaps Maia and SF; output timing-dependent at c > 1 |
| Phase 198 commit-ordered window | Not rebuilt | 226 D-05 / 227 D-08 | About half of 198's complexity removed |
| Raw-wall gates per arm on different days | Interleaved arms, rotated, load-gated | 226 override re-test | ±12% drift cancels |

Leela-style engines use virtual loss with tunable penalties; hard pending exclusion is its infinite-penalty limit `[ASSUMED: training knowledge]`. D-08 defers a virtual-loss arm to data.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Exchangeable null: continuous ≈ round with randomized tree shape; K fragile positions at π≈0.5; flip size ≈0.45 | Q1, Q2 | False-fail and power figures shift; the formulas stay valid, but the SD and allowance numbers move |
| A2 | K is in 3-10 (from 226 flip counts and the 7.9% argmax flip) | Q1 | At K ≥ 15 the point-estimate rule's null false-fail rises to about 6% |
| A3 | Raising `PER_BAND_QUOTA` keeps the first 60 rows | Q1 | Fixture widening would not nest; needs a fresh A0 MQ (it is re-run anyway) |
| A4 | Browser P≈63 ms (wasm t=4) and Node G carry over to the browser | Q8 model | Desktop win size; the D-06 tool replaces it |
| A5 | WebGPU batch-1 P≈15 ms (Phase 198 prior) | Q8, D-07 | The D-06 measurement replaces it |
| A6 | `setImmediate` yield is enough to restore SF I/O interleaving; `worker_threads` Maia is feasible in the harness (one 45.7 MB session per process) | Pitfall 1 | Without a fix, the Node gate under-measures continuous mode |
| A7 | Hard pending exclusion is the infinite-penalty limit of virtual loss | State of the Art | Wording only |
| A8 | Using `a21s-cells.json` as A0 would be statistically comparable (same harness code) | Q4 option | Only matters if the owner overrides "same session" |

## Open Questions

1. **D-04 judged metric (raw interleaved vs CPU-normalized).**
   - Known: grade-elapsed normalization is biased toward continuous (Pitfall 5); interleaving cancels drift.
   - Recommendation: the accept rule judges interleaved raw wall plus external-probe-normalized wall, and reports grade-elapsed-normalized. Owner confirmation needed, since D-04's text says "CPU-normalized".
2. **Pool dequeue tie-break (Pitfall 6).**
   - Recommendation: FIFO tie-break as an in-scope prerequisite, mutation-tested. Planner or owner to confirm scope.
3. **Harness Maia fix depth (Pitfall 1): `worker_threads` vs `setImmediate`.**
   - Recommendation: `worker_threads` if it fits one plan; else `setImmediate` plus a recorded fidelity caveat (the Node gate is then conservative for throughput).
4. **400-node analysis MQ cell: judged or report-only.**
   - Recommendation: report-only (R=3), because of cost. D-13 ships continuous to analysis too, so the owner may want it judged.
5. **WebGPU machine OS and browser.** Unknown. The tool must report the adapter and backend; the owner supplies the hardware.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Node | harness, vitest | ✓ | v24.19.0 | — |
| uv / Python / pytest | verdict twin | ✓ (repo standard) | — | — |
| onnxruntime-web (harness Maia) | all harness runs | ✓ | 1.27.0 | onnxruntime-node 1.29.0 (not app-faithful) |
| Vendored Stockfish wasm | grades | ✓ | 18 lite single | — |
| Idle box (load < 2.0, no `remote_eval_worker`) | all wall-clock and continuous MQ runs | ✓ now (no worker process found) | Ryzen 7 7840HS, 16 threads, 30 GB | — |
| WebGPU adapter | D-06/D-07 | ✗ on this Linux Chrome | — | **Owner hardware leg**; no fallback (D-07's WebGPU point needs it) |
| Real phone | report-only | n/a | — | Node pool-2 gate (226 D-04) |

**Missing with no fallback:** a WebGPU-capable browser (owner leg; blocking only for D-07's "not slower" point).

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | vitest 5.0.0 (frontend); pytest (verdict twin); Node `*.check.mjs` scripts (harness) |
| Config file | `frontend/vite.config.ts` test block; `pyproject.toml` |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.continuous.test.ts` |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`; `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py` |

### Decision → Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| D-11 | c=1 continuous ≡ round (snapshots + result, jittered, 7+ fixtures) | unit | `npx vitest run .../mctsSearch.continuous.test.ts -t "c=1"` | ❌ Wave 0 |
| D-11 | round mode unchanged when `dispatchMode` omitted vs `'round'` | unit | existing `mctsSearch.test.ts`, `mctsSearch.roundFill.test.ts` + one omitted-vs-explicit equality test | ✅ / ❌ (one new) |
| D-09 / L-2 | settle-after-abort not applied | unit (deferreds) | `-t "after abort"` | ❌ Wave 0 |
| D-09 | early stop: inner signal aborted, stale result not applied, grade received aborted signal | unit | `-t "early stop"` | ❌ Wave 0 |
| D-10 | `nodesEvaluated ≤ maxNodes`; dispatches ≤ maxNodes + degenerate; `inFlight==0` at exhaustion | unit | `-t "budget"` | ❌ Wave 0 |
| D-08 | no leaf dispatched twice while pending; arrival-order apply (later dispatch settling first is applied first) | unit | `-t "arrival order"` | ❌ Wave 0 |
| D-08 | per-fill blocks: on a peaked policy, continuous keeps c in flight (round-fill analogue) | unit | `-t "fill"` | ❌ Wave 0 |
| Y-9 | exactly one dispatch until the root is applied | unit | `-t "root guard"` | ❌ Wave 0 |
| Y-8 | rejection propagates, siblings' signals aborted, no unhandled rejection | unit | `-t "rejection"` | ❌ Wave 0 |
| X-8 | settlement during drain / with no waiter still wakes | unit | `-t "wakeup"` | ❌ Wave 0 |
| Pitfall 7 | outer-signal listener removed after search | unit (spy add/removeEventListener) | `-t "listener"` | ❌ Wave 0 |
| Pitfall 2 | Node pool abort → `stop`, engine released, no stale result | check script | `node scripts/lib/stockfish-pool.check.mjs` | ✅ (extend) |
| Pitfall 1 | harness event-loop lag bounded during FIFO bursts | check script | new `maia-fifo-yield.check.mjs` or extend `maia-instrumentation.check.mjs` | ❌ Wave 0 |
| D-14 | harness budget mode === `FLAWCHESS_DISPATCH_MODE`; round bit-identity still PASS | check script | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` | ✅ (extend) |
| Tooling tripwire | round-mode MQ under new harness == 226 `a21s` TSVs (es_bot, bot_move) | orchestrator run + diff | MQ `--dispatch-mode round --repeats 1` then a diff script | ❌ Wave 0 |
| D-01/D-03/D-04/D-15 | verdict arithmetic, frozen constants, rerun/invalid states | pytest | `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py` | ❌ Wave 0 |
| D-06 | dev page absent from prod bundle | build + grep | `npm run build && ! grep -r "<marker>" dist/` | ❌ Wave 0 |
| Pitfall 6 (if adopted) | equal-priority grades served FIFO | unit | `npx vitest run .../workerPool.test.ts -t "FIFO"` | ❌ |

**Mutation checks (required, memory rule):** for each guard (apply-after-abort check, early-stop check, per-fill block clearing, D-10 budget guard, listener removal, harness abort), revert it and confirm the named test fails. Record this in the SUMMARY.

### Sampling Rate
- **Per task commit:** the continuous test file + `mctsSearch.test.ts` (under 30 s).
- **Per wave merge:** full frontend gate + verdict pytest + harness check scripts.
- **Phase gate:** full CLAUDE.md pre-merge gate, then the gate runs (orchestrator inline).

### Wave 0 Gaps
- [ ] `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts`
- [ ] `tests/scripts/test_engine_dispatch_227_verdict.py` + `scripts/engine_dispatch_227_verdict.py`
- [ ] Harness: Node pool abort, Maia FIFO yield / worker, `--dispatch-mode` switches, MQ `--repeats`, depth-ab `--ladder-only`, stop-rule grade-time column, interleave driver + machine-speed probe, resume-key mode
- [ ] Round-mode MQ diff tripwire against 226 `a21s` TSVs

## Security Domain

Low exposure: there are no new endpoints, auth or data paths.

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (dev tool only) | Compile-time `import.meta.env.DEV` gate; verified absent from the prod bundle |
| V5 Input Validation | no (no user input; harness flags validated by existing `parseArgs` patterns) | — |
| V6 Cryptography | no | — |
| V14 Configuration | yes | No dev route in prod; no new headers (reuses Vite's COOP/COEP) |

| Pattern | STRIDE | Mitigation |
|---|---|---|
| Dev benchmark route shipped to prod (resource abuse, info disclosure of device/GPU details) | Information disclosure / DoS | Tree-shaken DEV gate + dist grep in the gate; removed at phase end |
| Runaway CPU from uncancelled stale grades on user devices | DoS (self) | D-09 inner abort; unit tests |

## Sources

### Primary (HIGH, read or computed this session)
- `frontend/src/lib/engine/mctsSearch.ts` (full), `types.ts`, `botBudget.ts`, `deadlineSearch.ts`, `workerPoolDispatch.ts:100-330`, `workerPoolState.ts:100-106,425-506`, `workerPool.ts:274-276`, `maiaQueue.ts:1-120`, `maiaWorkerHost.ts:140-560`, `ortRuntimeSource.ts:112-216`, `gradingLadder.ts:84-85`, `hooks/useBotGame.ts:110-128`, `hooks/useFlawChessEngine.ts:350-386`, `selectBotMove.ts:130-160`, `vite.config.ts:39-71,208-227`
- `scripts/engine-move-quality.mjs`, `scripts/engine-dispatch-stop-rule.mjs:30-60,327-375`, `scripts/engine-grading-depth-ab.mjs:60-100,300-350`, `scripts/lib/calibration-providers.mjs`, `scripts/lib/stockfish-pool.mjs:336-525`, `scripts/lib/node-engine-providers.mjs:60-98`, `scripts/calibration-harness.mjs:360-400,580-630`
- `reports/engine-throughput-226/{report,accept-rule,design-inputs,override-2026-10-02-owner-ship-decision,analysis-2026-10-01-cpu-normalized-throughput}.md`; `reports/continuous-dispatch/apply-order-design.md` §3, §9-§9d
- Committed 226 data: `reports/data/engine-throughput-226/{step0,gate}/**` (MQ TSVs, throughput TSVs), `retest-2026-10-02/driver.log`
- Probes run this session: harness Maia event-loop blocking (wasm and native), FIFO macrotask starvation, paired-metric statistics, Monte Carlo of the D-01/D-03 rules

### Secondary (MEDIUM)
- `.planning/seeds/SEED-171-browser-engine-throughput.md` (microbench P values, L-1..L-7)

### Tertiary (LOW)
- Virtual-loss / Leela background (training knowledge)

## Metadata

**Confidence breakdown:**
- Code design and flag: HIGH (every primitive read; semantics follow from cited lines)
- Harness pitfalls 1/2/4/6: HIGH (measured or read)
- Statistical sizing: MEDIUM (assumed null model, checked against 226 data)
- Throughput expectations: MEDIUM for Node (from committed P/G), LOW-MEDIUM for browser and WebGPU (model only)

**Research date:** 2026-10-02
**Valid until:** 2026-11-01 (stable code area; re-check if `mctsSearch.ts` or the harness changes first)
