# Phase 227: Browser Engine Continuous Dispatch Against a Relaxed Determinism Target (SEED-171) - Context

**Gathered:** 2026-10-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the round `Promise.all` barrier in `frontend/src/lib/engine/mctsSearch.ts` so Maia and
Stockfish overlap: asynchronous tree search with pending marks (SEED-171 item 5). It is built
against the relaxed determinism contract from Phase 226 (D-05), with round mode retained behind a
budget flag (D-07), and shipped behind a pre-registered measurement gate. "Measured, not worth
shipping" is a first-class outcome.

**Baseline is arm A21S** (underfill fix, root guard and root split, all shipped by the
2026-10-02 owner override in `d0f5cb2ba`). It is not pre-226 `main`.

Prerequisite inside this phase: the desktop WebGPU Maia measurement (226 D-02, SEED-171 item 3,
L-6).

</domain>

<decisions>
## Implementation Decisions

### Guiding principle (owner, 2026-10-02, restated for this phase)
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

### Carried forward (locked in Phase 226; D-05 re-read through D-00)
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

### Quality criterion and ship bar
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

### WebGPU measurement (prerequisite; keep WebGPU)
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

### In-flight work semantics
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

### Rollout and calibration
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

### Post-research amendments (owner, 2026-10-02, at plan-phase; before any data)
Answers to the four open questions in `227-RESEARCH.md`. They amend the decisions above and are
fixed before any arm runs, so they are not override documents.
- **D-17 (amends D-04): judge raw wall, interleaved.** The ≥ 15% bar and the 3% no-regression bar
  are judged on **interleaved raw wall**, normalized by an external machine-speed probe. 226-style
  CPU-normalized wall (per-grade elapsed time) is **report-only**: it rises when Maia and SF contend,
  which biases it toward continuous mode. All other D-04 terms stand (interleaved, ≥ 3 rounds,
  rotated order, load-average wait, Node pool-2 must not regress beyond its noise).
- **D-18: harness Maia moves to `worker_threads`.** Harness Maia currently runs on the Node main
  thread and blocks the event loop for about 94 ms per inference, so SF results go unprocessed. It
  moves into a worker thread, matching the browser's Maia worker. This lands in the tooling commit
  before any arm runs. Round-mode results must stay byte-identical to 226's `a21s` files, which is
  checked.
- **D-19: fix the app SF queue tie-break in this phase.** The app's Stockfish queue breaks ties by
  move name, not arrival order, which can starve a queued grade on pool 2 with c = 4. It becomes
  arrival-order (FIFO), matching the harness, as a prerequisite to continuous mode. Round mode must
  stay bit-identical under the existing c = 4 unit and fixture gates. If it cannot, the plan says so
  explicitly.
- **D-20: analysis-400 move quality is report-only.** D-01 and D-03 are judged on the bot-move path
  only. Analysis at 400 nodes gets one move-quality run per arm, for information. Analysis-400
  throughput is still a D-04/D-17 ship-bar arm.

### Claude's Discretion
The owner answered "no preference" on all four gray areas (tolerance and ship bar, WebGPU
measurement, in-flight semantics, rollout and calibration). They then set D-00 (first principles,
test-driven, the current engine is not gospel). D-01..D-04 and D-06..D-16 are Claude's recommended
defaults, revised to follow D-00, and recorded as decisions so planning can proceed. The owner may
edit any of them before `/gsd-plan-phase 227`. **D-01 (one-sided non-inferiority, margin about
0.025) and D-04 (≥ 15% bar) are the two most consequential.** The research step should check that
the 0.025 margin is sensible against the measured noise of the *signed* metric. It was derived from
an unsigned floor, and signed paired noise is smaller.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed, roadmap, prior phase
- `.planning/seeds/SEED-171-browser-engine-throughput.md`: L-1..L-7, item 5, "Phase 226 outcome" and "Owner override" sections
- `.planning/seeds/SEED-130-browser-grade-nondeterminism-uncleared-stockfish-hash.md`: Q1 (answered by 226 D-05), Q2 (226 D-03 arm)
- `.planning/ROADMAP.md`, Phase 227 entry
- `.planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-CONTEXT.md`: D-04..D-07, D-10, D-14, D-18
- `reports/engine-throughput-226/report.md`: D-06 noise floor numbers (0 of 60, 0.0168), stop-rule data
- `reports/engine-throughput-226/accept-rule.md`: accept-rule template, frozen constants, CONTENT_MAX, calibration thresholds
- `reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md`: owner principle, interleaved re-test protocol
- `reports/engine-throughput-226/analysis-2026-10-01-cpu-normalized-throughput.md`: CPU-normalized wall method (D-04)

### Phase 198 (the previous continuous-dispatch attempt)
- `reports/continuous-dispatch/apply-order-design.md` §3 (throughput model, X-2 corrected form `min(1/P, c/(P+G))`), §9b (X-1..X-12), §9c, §9d (Y-1..Y-14): the checklist for D-12
- `reports/continuous-dispatch/report.md`: 34.8% / 28.6% measured win (pre-225 baseline), WebGPU retraction
- `reports/continuous-dispatch/accept-rule.md`: accept-rule precedent

### WebGPU
- `.planning/seeds/closed/SEED-158-maia-webgpu-fails-on-capable-devices.md`: iOS WebGPU history; desktop per-GPU failures still open
- `frontend/src/lib/engine/ortRuntimeSource.ts`: `probeOrtBackend` (`shader-f16`, high-performance adapter)

### Harness and gate tooling
- `scripts/lib/calibration-determinism.check.mjs`: no-Clear-Hash warm arm (226 D-03)
- `scripts/engine-move-quality.mjs`, `scripts/engine-dispatch-stop-rule.mjs`, `scripts/calibration-harness.mjs`, `bin/run_persona_calibration_sweep.sh`, `bin/preset-supervisor.sh`
- `scripts/engine_throughput_226_verdict.py`: verdict twin pattern to copy
- `.planning/research/perf-profiling-2026-09-28/`: `profile_search.mjs`, `split_root.mjs`
- Widened MQ fixture from 226 D-14 (location in `226-02-SUMMARY.md` / `226-07-SUMMARY.md`)

### Documentation to update
- `docs/flawchess-engine-explained-2026-07-06.md`
- `CHANGELOG.md` `[Unreleased]`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mctsSearch.ts` round loop (`mctsSearch` at ~632-748): fill loop → clear `blockedThisRound` → `Promise.all(dispatchExpansion…)` → apply in input order with `signal.aborted` and `earlyStop` breaks. Continuous mode replaces the barrier and apply loop. Selection (`selectPath`, `isPending`, `isBlocked`), `dispatchExpansion`, `applyExpansion` and `stopRuleSatisfied` are reused as is.
- `isBlocked` / `blockedThisRound` are round-scoped (the 226 underfill fix). Continuous mode needs a scoping rule for them (per fill attempt). The design must state it.
- `WorkerPool.grade` settles an aborted request with an empty Map; a missing grade becomes `NEUTRAL_EXPECTED_SCORE` (L-2). This is the reason for D-09's "never apply after abort or stop".
- Root split (`EngineProviders.gradeRoot`, 226 D-18) already covers the single-expansion first round. Continuous dispatch gains nothing there (root guard Y-9: one dispatch until the root commits).

### Established Patterns
- Accept rule committed before data and never edited; overrides are separate docs; verdict twin script; arms from detached worktrees with content assertions (Phases 225/226).
- Interleaved throughput arms with CPU normalization (226 override re-test).
- Bot concurrency pinned (`botBudget.ts` `FLAWCHESS_BOT_CONCURRENCY = 4`); the analysis pool comes from `computePoolSize()` (`workerPoolState.ts`) and can be 2.
- Gap-fix tests are mutation-checked by reverting the fix.

### Integration Points
- `SearchBudget` in `frontend/src/lib/engine/types.ts` (gets the dispatch-mode flag), `botBudget.ts`, `useFlawChessEngine.ts`, `deadlineSearch` (inner abort on deadline cut), Maia FIFO `maiaQueue.ts`, `workerPoolDispatch.ts` `dispatchNext`.
- Harness providers (`scripts/lib/calibration-providers.mjs`) must pick up the same flag.

</code_context>

<specifics>
## Specific Ideas

- Sentry, last 30 days, WebGPU-backend failures after the iOS fix: Android Chrome inference ×5 (since 09-27), Android page-killed ×1, Windows Chrome inference ×1. There is no success telemetry, so the share of WebGPU users is unknown.
- Model prior from Phase 198 §3 (corrected): throughput `min(1/P, c/(P+G))`. The gain peaks near `P = G/(c−1)`; wasm sits near the peak for the bot budget, and WebGPU-plausible P lowers it.
- Stop the local `remote_eval_worker` before any measurement (idle box).

</specifics>

<deferred>
## Deferred Ideas

- **Dropping WebGPU Maia:** considered and rejected by the owner 2026-10-02. Revisit only if the D-06 measurement shows WebGPU is not clearly faster than wasm at batch 1 (would be a separate quick task).
- **Other concurrency levels** (for example above 4, to keep the Maia FIFO saturated at WebGPU-like P, `c* = 1 + G/P`): a test-driven question for its own phase, judged on quality against ground truth and on throughput.
- **Maia success telemetry** (backend share, per-inference latency in the field): would size L-6 from real users; not in scope.
- Still out of scope: cross-FEN Maia batching (revisit only with WebGPU numbers), Rust/WASM port, multithreaded SF, fp32/int8 Maia, Maia WDL leaf values (rejected), depth ladder / MultiPV tuning, server-side Maia (SEED-172).

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-08-29-variation-tree-nested-button.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`: keyword-match noise, unrelated (same set Phases 225/226 reviewed).

</deferred>

---

*Phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi*
*Context gathered: 2026-10-02*
