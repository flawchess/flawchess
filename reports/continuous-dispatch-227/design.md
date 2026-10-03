# Phase 227 design: continuous dispatch in `mctsSearch`

Status: reviewed. Round 1 (both reviewers NOT SOUND) was repaired, round 2 (both reviewers SOUND) was repaired for its
remaining findings, and every finding is dispositioned in section 7 (Plan 227-09 Task 2). No `mctsSearch.ts` edit
exists or may land before the review is closed (D-12, L-7); the closing lines are at the end of this file.

This document specifies the continuous dispatch loop, its harness, its expected win and the disposition of every
open Phase 198 finding. It is written to be attacked. Every load-bearing statement carries file:line evidence.
The six claims the review must try to break are in section 6.

## 0. Conventions and evidence base

- All `file:line` references are to commit `399780bf8`, which is `79b659766` plus the round-1 tooling fix (harness Maia
  FIFO abort, `whenMaiaIdle`; see section 3.2). Only `scripts/` files differ between the two commits, so every
  `frontend/` reference is unchanged. `frontend/src/lib/engine/mctsSearch.ts` has no commit in Phase 227 (its last
  change is `d0f5cb2ba`, the Phase 226 squash), so every `mctsSearch.ts:` reference below is to code this design has
  not touched.
- "Round mode" is the shipped A21S barrier loop (`mctsSearch.ts:650-745`). "Continuous mode" is the loop specified
  in section 2.
- Numbers are labelled. **Measured** means read from a committed data file. **Model** means derived from measured
  inputs by a formula stated in this document. **Assumption** means neither.
- Prior Phase 198 material is cited by finding ID only. `reports/continuous-dispatch/apply-order-design.md` §9b
  (X-1..X-12, lines 1082-1122) and §9d (Y-1..Y-14, lines 1177-1213) are the checklist. §9c (lines 1126-1175) holds
  Phase 198's own dispositions, which this document re-verifies rather than inherits.

## 1. Contract

### 1.1 What is being built

Remove the per-round `Promise.all` barrier (`mctsSearch.ts:723-725`) so that Maia policy inference and Stockfish
grading overlap across expansions. A slot freed by one settled expansion is refilled at once instead of waiting for
the slowest member of the round. Selection (`selectPath`), expansion (`dispatchExpansion`), apply
(`applyExpansion`) and the stop rule (`stopRuleSatisfied`) are reused as they are.

### 1.2 Guiding principle (D-00)

Round mode is a comparison arm, not a reference answer. Divergence from it is information, not failure. The ground
truth for move quality is the d20 Stockfish evaluation. A persona shift is something to refit. Pre-registration
stays, because it keeps the test honest, not because the old engine is sacred.

### 1.3 The contract, as numbered statements

- **C1. Round mode stays.** `SearchBudget.dispatchMode?: 'round' | 'continuous'` (`types.ts:100,125`). Omitted means
  round. The existing round loop is kept verbatim, so every existing unit test and fixture gate stays exact on the
  flag (D-11, 226 D-07). The round loop's behavior is kept, but its code is not literally verbatim: section 2.1
  extracts `applyAndReport` and `discoverDeadEnd` from it and moves its four loop locals (`mctsSearch.ts:636-648`:
  `nodesEvaluated`, `budgetExhausted`, `earlyStop`, `stopState`) into a shared counters object. That is a refactor, so
  the existing unit suites alone do not prove it. Plan 227-10 must also re-run the Plan 227-08 `--hash clear` parity
  check after the extraction and before any continuous code lands, with 0 differing rows against the committed
  `reports/data/continuous-dispatch-227/tripwire/parity-clear` (section 2.4, test obligations). The app constant
  `FLAWCHESS_DISPATCH_MODE` stays `'round'` (`botBudget.ts:76`) through the
  whole gate. Shipping is a one-line flip and rollback is flipping it back (L-5). Both app budgets already carry the
  constant (`useBotGame.ts:131`, `useFlawChessEngine.ts:383`), so bot and analysis flip together (D-13).
- **C2. No concurrency change (D-10).** The bot pins `FLAWCHESS_BOT_CONCURRENCY = 4` (`botBudget.ts:64`). Analysis
  uses `computePoolSize()` (`useFlawChessEngine.ts:369`, `workerPoolState.ts:509-513`), which is 2 to 4. This phase
  tunes no concurrency. The reason is scope (one variable at a time), not that 4 is right.
- **C3. Quality is judged against d20 truth, one-sided (D-01).** Continuous passes if it is not worse than round
  mode by more than a margin. Being better is a pass.
- **C4. Determinism, in three separate statements.**
  1. *Algorithm.* Round mode is behavior-identical to A21S (a refactor around shared helpers, proven by the
     pre-extraction goldens and the clear-hash parity re-run), so it is bit-identical to A21S for deterministic providers.
     That covers every existing unit and fixture gate. At `c = 1` continuous mode is byte-identical to round mode
     for providers that resolve after an abort, compared after quiescence (claim (c), section 2.4).
  2. *Harness, `--hash clear`.* Worker-thread Maia and main-thread Maia produce identical round-mode results
     (Plan 227-08 parity tripwire: 0 of 60 rows differ, both stop modes).
  3. *Real providers, warm hash.* **No run-to-run identity is claimed, for either mode, in the harness or in the
     browser.** See 1.4.
- **C5. Order can affect output in continuous mode, and that is accepted (D-11).** There is no ordering machinery and
  no claim that order cannot affect output. The mechanisms are:
  - M1. Results apply in arrival order, so which expansion applies first changes the values and visits that later
    selections read.
  - M2. Dead-end discovery runs inside fills that are interleaved with applies (X-3), so its visit bumps and
    closures happen against a different tree state than in round mode.
  - M3. The grade cache hit or miss is a settlement race (X-6, Y-2, Y-4). A subset grade differs in content from a
    full-set grade at matching depth (`workerPool.ts:330-353`).
  - M4. Which Stockfish worker serves which grade depends on arrival order, and the browser never clears the
    transposition table (Y-1, SEED-130), so a grade's content depends on that worker's earlier searches, within one
    search and across searches. The Node gate sees only the within-search part (section 3.6, hash row).
  - M5. Cancelled grades leave partial work in the stopped worker's hash, which the next search can read because the
    browser never clears it. Cancellation on abort exists in BOTH modes: round mode's pool also stops in-flight grades
    when the search signal aborts (`workerPoolDispatch.ts:297-308`), which happens at every timer-driven bot deadline cut
    (`deadlineSearch.ts:118-120`; an armed cut fires from `onSnapshot` after the round's barrier, so nothing is in flight) and at every analysis position change (`useFlawChessEngine.ts:351-352`). Cancellation
    on early stop is continuous-only, because round mode's early stop comes after the barrier, and it is routine for the
    bot, whose consecutive searches are two plies apart. So M5 is present in both arms and amplified in continuous
    mode. **The Node gate cannot measure M5 at all** (it sends `ucinewgame` before every position, section 3.6).
- **C6. Cancellation (L-2, D-09).** No result is applied after abort or early stop. Stale in-flight work is cancelled
  through an inner `AbortController`. There is no drain.
- **C7. Budget (D-10).** `applied + inFlight <= maxNodes` always.
- **C8. Not rebuilt (D-08).** No commit-ordered apply, ring buffer, window or slot-release-on-commit machinery.
  Those existed in Phase 198 only to keep bit-identity. In-flight leaves keep `isPending = true` and are excluded
  from selection, which is the infinite-penalty limit of virtual loss. A virtual-loss arm is a gap-closure decision
  that the accept rule's D-08 trigger governs, not part of this design.

### 1.4 Owner direction of 2026-10-02 (Plan 227-08), and what it changes

Plan 227-08's debug record (`227-08-TRIPWIRE-DEBUG.md`) found that round mode in the harness is no longer
bit-reproducible under `--hash warm`. The cause is Plan 227-01's move of harness Maia into a `worker_threads` worker
(D-18, finding N-1). Grades now finish while Maia infers, so pool engine assignment (first free engine by index) and
each engine's warm-hash history depend on timing. A grade's value depends on that history under warm hash. The 226
harness was reproducible only because the blocking main-thread Maia froze the event loop during inference. The
browser has the same timing-dependent property: in the owner's and this box's round-mode legs the same position
reports different node counts across rounds (Linux wasm `sharp` 15, 50, 15 nodes; `C50` 15, 14, 50;
`reports/data/continuous-dispatch-227/webgpu/local-wasm-round-leg.json`).

Measured (Plan 227-08, `reports/data/continuous-dispatch-227/tripwire/`):

| Check | Result |
|---|---|
| `--hash clear`, worker Maia vs `--maia-main-thread`, 60 rows, stop off and on | 0 differing rows in each (TRIPWIRE PASS), tooling commit `cef88fd87` |
| `--hash warm`, worker Maia vs 226 a21s, stop off (report-only) | 2 of 60 picks differ (`cBFTV`, `Mhfvi`); pass 49 (a21s) vs 48; mean `es_bot` 0.8079 vs 0.7995 |
| `--hash warm`, worker Maia vs 226 a21s, stop on (report-only) | 1 of 60 picks differs (`cBFTV`), 5 of 60 rows differ in pick or node count; pass 50 vs 49; mean `es_bot` 0.8196 vs 0.8101; mean nodes 9.28 vs 10.07 |
| Round repeats in-process (Plan 227-04), position `cBFTV`, stop on | minority pick in 14 of 130 repeats (10.8 percent); 9 of 120 with signal forwarding disabled (7.5 percent) |

The owner decided on 2026-10-02 that bit-identical results are not required with concurrent Maia inference. Very
similar is good enough. This document therefore:

- keeps round mode bit-identical **as an algorithm** (same code path, byte-identity with continuous at `c = 1`, and
  identical results at `--hash clear`);
- states that warm-hash round repeats in the harness are expected to differ slightly run to run, and cites the numbers
  above;
- does not claim warm-hash run-to-run identity anywhere.

CONTEXT D-11's wording "round mode at any c stays bit-identical to A21S" is therefore read as a statement about the
code path and about deterministic providers (the vitest mocks, the fixture gates), not about real-provider warm-hash
runs.

### 1.5 Consequences for the gate (notes for Plan 227-09 Task 3; this task edits no tooling)

- `_check_round_determinism` (`scripts/engine_dispatch_227_verdict.py:544-558`) raises INVALID on any round-repeat
  disagreement ("226: 0 of 60"). Under warm hash and worker Maia it would invalidate every judged cell. Task 3
  relaxes it (report the round-repeat disagreement rate instead of failing) and updates the twin's tripwire
  docstring, which still says "bit-identical to A21S", to point at the clear-hash parity check. This document does
  not edit the twin.
- The accept rule's exact-identity validity rows (round arm equal to 226 a21s on `bot_move`, `analysis_move`,
  `nodes_evaluated`, `stop_reason`, twin `:212,273-300`) become the clear-hash parity row plus report-only warm-hash
  similarity.
- The D-03 net is already fractional (`net = (cont_total - round_total) / MQ_REPEATS`, twin `:589`), so it accepts
  non-identical round repeats without a code change.
- RESEARCH Q1's null-model SD table assumed round mode's pick is one frozen draw per position. With round now also a
  timing-dependent draw averaged over R = 5 repeats, the SD of the signed metric D falls by roughly
  `sqrt((1/R + 1/R) / (1/R + 1)) = 0.58` (so its variance falls to about 0.33) under that section's own
  exchangeable-null assumption (A1). **Model, not measured.** The 0.0252 margin is unchanged (D-01 is locked); the
  table is an upper bound on the null SD.

## 2. The continuous loop

### 2.1 Structure: fill, await one settlement, drain in arrival order

`mctsSearch` selects the loop at its top: `budget.dispatchMode === 'continuous'` runs the loop below, anything else
runs the existing round loop unchanged. The two loops share `applyAndReport` (the body of today's apply loop,
`mctsSearch.ts:729-743`) and `discoverDeadEnd` (the dead-end branch, `:673-688`) as extracted helpers, plus the final
`buildSnapshot(...)` return (`:747`). The extraction also moves the round loop's four locals
(`mctsSearch.ts:636-648`) into a shared counters object (`SearchCounters` in the sketch). It must be
behavior-preserving for round mode, but it is a refactor of the round loop, not "verbatim" code. The existing
`mctsSearch.test.ts` and `mctsSearch.roundFill.test.ts` suites, one omitted-versus-explicit-`'round'` equality test,
pre-extraction golden captures and the `--hash clear` parity re-run in section 2.4 prove that.

Sketch (the semantics are the contract, the names are not):

```ts
type Settled = { kind: 'ok'; result: DispatchedExpansion } | { kind: 'rejected'; error: unknown };

async function runContinuous(ctx: SearchContext, st: SearchCounters, signal: AbortSignal): Promise<void> {
  const dispatchController = new AbortController();           // inner controller, section 2.6
  const settled: Settled[] = [];                               // arrival order
  let wake: (() => void) | null = null;                        // single-shot wake, section 2.7
  const notify = (): void => { const w = wake; wake = null; w?.(); };
  const onOuterAbort = (): void => { dispatchController.abort(); notify(); };
  if (signal.aborted) onOuterAbort(); else signal.addEventListener('abort', onOuterAbort, { once: true });
  let inFlight = 0;                                            // dispatched and not yet drained
  try {
    for (;;) {
      if (signal.aborted || st.earlyStop) return;
      inFlight += fillContinuous(ctx, st, inFlight, dispatchController.signal,
        (s) => { settled.push(s); notify(); });
      if (inFlight === 0 && settled.length === 0) return;      // nothing running, nothing selectable
      // R2B-2: a provider's synchronous prefix can abort during the fill, while `wake` is still null, so the
      // wake would be lost. Re-check before waiting; the loop-top test then returns.
      if (settled.length === 0 && !signal.aborted && !st.earlyStop) {
        await new Promise<void>((resolve) => { wake = resolve; });
      }
      while (settled.length > 0) {                              // drain EVERYTHING that has settled
        const s = settled.shift();
        if (s === undefined) break;
        inFlight -= 1;
        if (signal.aborted || st.earlyStop) continue;           // L-2, D-09: never apply after abort or stop;
                                                                // R2A-6: also drops a rejection that is drained after a stop
        if (s.kind === 'rejected') throw s.error;               // Y-8: fail loudly (only while the search is live)
        applyAndReport(ctx, st, s.result);                      // the ONLY apply call site
      }
    }
  } finally {
    signal.removeEventListener('abort', onOuterAbort);          // Pitfall 7: no listener accumulation
    dispatchController.abort();                                 // D-09: cancel stale work, no drain
  }
}

function fillContinuous(ctx, st, inFlight, dispatchSignal, onSettle): number {
  const blockedThisFill: EngineNode[] = [];
  let dispatched = 0;
  try {
    while (inFlight + dispatched < ctx.budget.concurrency &&
           st.nodesEvaluated + inFlight + dispatched < ctx.budget.maxNodes) {        // D-10 guard
      const path = selectPath(ctx.root, ctx.budget.maxPlies, blockedThisFill);
      if (path === null) break;
      const leaf = path[path.length - 1];
      if (leaf === undefined) break;
      if (leaf.isExpanded) { discoverDeadEnd(ctx, st, leaf, path); continue; }       // same body as :673-688
      leaf.isPending = true;
      dispatched += 1;
      dispatchExpansion(leaf, path, ctx.budget, ctx.providers, ctx.rootMover, dispatchSignal).then(
        (result) => onSettle({ kind: 'ok', result }),
        (error: unknown) => onSettle({ kind: 'rejected', error }),
      );
    }
  } finally {
    for (const node of blockedThisFill) node.isBlocked = false;                      // scope = one fill
  }
  return dispatched;
}
```

Seams (CLAUDE.md function-size rule): `runContinuous` (about 30 lines, nesting depth 3), `fillContinuous` (about 25
lines, depth 3), `applyAndReport` and `discoverDeadEnd` shared with the round loop. The outer-signal forwarding and the
`settled` queue are one cohesive unit and are not split further.

Termination of a fill is structural, by the same argument as the round loop (`mctsSearch.ts:657-663`): every
iteration either breaks, permanently closes a dead-end node (each node closes once), blocks a node (each node blocks
at most once per fill, because its parent's filter then excludes it), or dispatches (bounded by `concurrency`).

`dispatchExpansion` is an `async` function, so a provider that throws synchronously becomes a rejection, not a
synchronous throw out of the fill (`mctsSearch.ts:518-626`).

### 2.2 Per-fill block scoping, and why it is exact (claim (a))

`isBlocked` is the SEED-170 item 2 mechanism: a non-root node reached with zero selectable children is marked
blocked and the walk restarts from the root (`mctsSearch.ts:387-407`). Round mode scopes the mark to one round and
clears it after the fill (`:700-709`). Continuous mode scopes it to **one fill pass**: one synchronous top-up between
two awaits.

**Lemma 1 (monotone within a fill).** Between two `selectPath` calls inside one fill, the only tree mutations are:
(i) one leaf's `isPending` goes false to true (dispatch, `:696`); (ii) a dead end's `isExpanded` and `isClosed` go
false to true (`:377-380`) and `propagateClosure` closes ancestors whose children are all closed (`:337-343`);
(iii) `visits += 1` along a dead-end path (`:685`) and `budgetExhausted` may become true (`:683`). None of these makes
a pending or closed child selectable again. So the set of selectable children of any node is non-increasing within
a fill.

**Consequence (exactness).** A node blocked at time T has no selectable child at T. By induction on depth, a blocked
child has no selectable descendant, a pending child is not selectable, a closed child has no work. So a blocked node
has no selectable leaf below it, and by Lemma 1 it still has none for the rest of the fill. Blocking therefore never
hides a subtree that still has selectable work. The walk is PUCT over subtrees that still contain work, which is
what a perfect oracle would give. Pending nodes are always unexpanded leaves (set only on a leaf at `:696`, cleared at
apply `:446,477`), so no pending node has descendants to hide.

**Lemma 2 (staleness across fills).** `isPending` goes true to false only inside `applyExpansion` (`:446,477`), which
runs only in the drain, which runs between fills. So a block set in fill k can be stale in fill k+1: the leaf that
caused it may now be expanded and selectable. Clearing the marks at the end of every fill is therefore necessary.
It is sufficient because `isBlocked` has exactly three uses: the candidate filter (`:385`), the set (`:403`) and the
clear (`:708`), and `selectPath` is called only from the fill (`:668`). No reader exists outside a fill.

The clear lives in a `finally`, so a throw inside a fill cannot leak marks into the next one. This is the round
loop's argument with "round" replaced by "fill". It is also the reason the blocked-leak symptom of the 226 underfill
(a round that dispatched nothing still leaking blocks) cannot recur: a fill that dispatches nothing still runs its
`finally`.

One difference from round mode matters. At the start of a round fill nothing is pending, because the previous round
applied everything. At the start of a continuous fill up to `c - 1` leaves are pending. Blocks therefore arise more
often in continuous mode. That is the case the SEED-170 item 2 fix exists for.

### 2.3 Budget accounting (claim (b), D-10)

Let `A` be `nodesEvaluated` and `F` be `inFlight`, which counts every dispatched expansion until it is drained, so
it includes settled-but-undrained ones.

**Invariant I:** `A + F <= maxNodes`, at all times.

- Dispatch happens only when `A + F + dispatched < maxNodes` (the fill guard), so the sum rises by one only while
  it was strictly below the cap.
- A drain step lowers `F` by one and raises `A` by one (a non-degenerate apply) or leaves it (a degenerate apply or a
  discard). The sum never rises.

So `A <= maxNodes` always. Total dispatches equal `A` plus the number of degenerate expansions (plus, on a stopped
search, the cancelled ones). Provider calls can therefore exceed `maxNodes` by the degenerate count, exactly as
today (X-10).

**Consequence: `F = 0` when the budget is exhausted.** "Budget exhausted" here means `A = nodesEvaluated =
maxNodes`, not the `budgetExhausted` flag or `stopReason: 'budget'`. The flag is also set by a WR-05 `maxPlies` cut
(`mctsSearch.ts:679-684`) while expansions are in flight, so a later abort can return `stopReason: 'budget'` with
`F > 0` (round-2 findings R2A-7, R2B-7). The test keys on `A = maxNodes` (section 2.12). Suppose a drain step applies a non-degenerate expansion and
`A` becomes `maxNodes`. Before the step the sum was at most `maxNodes` and included this expansion in `F`, so
`F_before <= 1`, hence `F_after = 0`. No other settled-but-undrained result can exist, because it would be in `F`.
The next loop iteration dispatches nothing (the guard is false), sees `inFlight === 0 && settled.length === 0`, and
returns. So "cancel in-flight work on budget exhaustion" (D-09) is vacuous under D-10. Only early stop, abort and
rejection ever cancel live work.

A degenerate (empty-candidate) settlement lowers `F` without raising `A`, so it reopens a slot and the loop keeps
dispatching until a real expansion applies or the tree is exhausted (WR-04, `mctsSearch.ts:440-449,552-566,614-623`).
Round mode behaves the same way over rounds (`:664-666`).

### 2.4 `c = 1` byte-identity (claim (c), D-11, X-12)

**Definition and scope.** Byte-identical means, for every fixture and every provider timing: the ordered sequence of
`onSnapshot` payloads and the returned snapshot are deep-equal (compared as JSON), and the ordered lists of
`policy(fen, elo, side)` and `grade(fen, candidateUcis, ..., gradingDepth)` calls are equal. The `AbortSignal`
object handed to providers is excluded (it is the inner signal in continuous mode). Two scope limits (round-1
findings R1A-2 and R1B-3):

1. **Providers must resolve after an abort.** A provider that resolves (empty, as the app's do) when the search
   signal aborts, never rejects and never hangs. The app providers satisfy this with one pre-existing exception: the
   Maia queue resolves `{}` for a queued request on abort and for a pre-aborted signal (`maiaQueue.ts:279-285`,
   `:301`), and an in-flight inference completes (`:253-255`) unless the ONNX call itself wedges, because the Maia host
   has only init timeouts and no analyze watchdog (`maiaWorkerHost.ts:84-92`, `:735`; `maiaQueue.ts:174-201` waits on
   `lease.analyze` indefinitely; round-2 findings R2A-9, R2B-4). A wedged inference never settles in either mode, and
   an abort frees only the continuous loop (X-9). The pool resolves `new Map()` for a pre-aborted signal, a dequeued request and a stopped
   in-flight request (`workerPoolDispatch.ts:211`, `:286-312`) and `gradeRoot` for its group (`:377`, `:415-420`);
   the harness pool does the same (`stockfish-pool.mjs:293`, `:564-565`). For a provider that rejects or hangs after an
   abort the two modes legitimately differ: round mode awaits `Promise.all` (`mctsSearch.ts:723-725`), so it throws on
   a late rejection and hangs on a never-settling provider, while continuous returns the snapshot at once (X-9, and
   section 2.7). That divergence is accepted and pinned by a test, not hidden.
2. **Call lists are compared after quiescence**, meaning after every provider promise handed out during the search
   has settled. `dispatchExpansion` calls `grade()` after its policy resolves with no abort check between
   `mctsSearch.ts:533` and `:586`. When an external abort lands while an expansion is in flight, round mode makes
   that `grade()` call before it returns and continuous mode makes it after it returned. The call lists are equal once
   both have settled, not at the instant the search promise resolves.

**Argument.** At `c = 1` the fill guard `inFlight + dispatched < 1` is true only when `inFlight = 0`. When a result is
in flight the fill makes no `selectPath` call at all, so it makes no dead-end discovery and no visit bump (the one
state change a fill can make besides a dispatch). When `inFlight = 0`:

- Every earlier result has been applied or discarded, so the tree is in the state round mode's c = 1 fill sees at the
  start of a round.
- The fill performs the same sequence as the round fill: dead-end discoveries with their visit bumps and closures,
  ending in at most one dispatch. The guard `A + inFlight + dispatched < maxNodes` equals round's
  `nodesEvaluated + toExpand.length < maxNodes` (`:666`).
- No block can be set. With nothing pending, a non-root node with zero selectable children has only closed
  children, and every route that closes the last child closes the parent too (`allChildrenClosed` at apply
  `:482-485`, `propagateClosure` at `:448`, `:484` and `:686`). So `isBlocked` is never written at `c = 1`, and
  the per-fill versus per-round scoping difference cannot show.
- The drain applies the one result through `applyAndReport`, the same helper round mode uses, so the nodes-evaluated
  count, the stop-rule evaluation, the snapshot and the early-stop decision are identical. A degenerate result
  produces no snapshot in both loops.
- The exits agree: nothing selectable and nothing in flight returns (round: `toExpand.length === 0` break,
  `:711-718`); early stop and pre-aborted entry return before another dispatch; the common final `buildSnapshot`
  return is shared. A rejected provider throws in both when no abort precedes the rejection (continuous: the
  rejected settlement is the only item in its drain, nothing else is queued behind or ahead of it at `c = 1`, and
  no early stop can precede it because a stop needs an apply that is not in flight, so the stop-or-abort test before
  the throw is false and it throws exactly as `Promise.all` does). With an abort first, scope limit 1 applies.
- Timing cannot matter, because at most one expansion is ever in flight.
- **The one case where the control flow differs** is an external abort while that one expansion is in flight. Round
  mode is inside `await Promise.all(...)` (`mctsSearch.ts:723-725`) and waits for the provider to settle, then its
  apply loop breaks on `signal.aborted` (`:728`) and it returns. Continuous mode wakes on the abort
  (`onOuterAbort` calls `notify`), sees `signal.aborted` at the loop top and returns at once, and the `finally`
  aborts the inner controller. The observable results (snapshots, returned snapshot) are equal because neither
  mode applies the in-flight result. The timing differs by design: continuous does not wait. The fixture below pins
  exactly this.

**Test (obligation for Plan 227-10).** For fixtures covering a plain search, the stop rule on, dead ends and a
`maxPlies` cut, a degenerate empty candidate set, an 8XN-7 empty grade, `extraRootMoves`, `gradeRoot` present, a
deadline-style abort inside `onSnapshot`, and a pre-aborted signal, run both modes at `c = 1` with different
`withJitter` timings and assert the full equality above (call lists after quiescence). Two further fixtures:

- **External abort while an expansion is in flight** (a deferred provider, aborted from outside, then settled).
  Assert: snapshot sequences and returned snapshots deep-equal; the continuous search promise resolves before the
  deferred provider is settled while the round search promise is still pending until it is; call lists equal after
  the deferred provider settles and the loop drains.
- **Late rejection after abort.** The deferred provider rejects after the abort. Assert: continuous returns the
  snapshot and no unhandled rejection event fires; round mode throws. This documents the accepted divergence
  (scope limit 1) and the dropped late rejection of section 2.8.

Round mode is retained, so the golden for the live equality is computed live. That live golden is the post-extraction
round loop, so a defect in a shared helper would hit both arms equally and the equality test cannot see it (round-1
finding R1B-4). Two further obligations close that gap:

- **Pre-extraction goldens.** The first Plan 227-10 commit, which precedes the extraction, captures the fixtures'
  snapshot sequences, returned snapshots and call lists from the unrefactored round loop and commits them as vitest
  golden files. The round loop, before and after the extraction, and continuous at `c = 1` must all equal them. (The
  pre-rewrite goldens are not committed today; this obligation creates them.)
- **Clear-hash parity re-run.** After the extraction and before any continuous code, re-run the Plan 227-08
  `--hash clear` move-quality gate in round mode (worker Maia, stop off and on, 60 rows each) and require the twin's
  `tripwire` to report 0 differing rows against the committed
  `reports/data/continuous-dispatch-227/tripwire/parity-clear/worker` and `.../main` (Plan 227-08 summary, twin
  `tripwire --mq-dir ... --baseline-dir ...`). Those committed TSVs are pre-extraction, real-provider goldens.

### 2.5 Root guard base case (Y-9)

`selectPath` returns null while `root.isPending` or `root.isClosed` (`mctsSearch.ts:368`). The first fill therefore
dispatches exactly the root, and the loop then waits. The base case is one dispatch until the root applies, then up
to `c`, not `c` back-to-back dispatches. The root's one grade call is routed to `providers.gradeRoot` when present
(`:584`), which fans it across the idle workers, so continuous mode gains nothing during that first wait and loses
nothing either. A terminal root is created closed (`:163-169`), the first fill dispatches nothing, `inFlight` is 0,
and the loop returns.

### 2.6 Stop and abort handling (claim (d), D-09, L-2)

**The rule.** A settled result is applied only if, at the moment of the apply, `signal.aborted` and `st.earlyStop`
are both false. The check and the apply are consecutive statements with no `await` between them, in the one place
that calls `applyAndReport`. JavaScript runs them to completion on one thread, so nothing can flip either flag
between the check and the apply. Note what this does not rely on (round-1 finding R1A-6): `abort()` runs its
listeners synchronously inside the caller, so an abort is NOT always an event delivered between runs. It can land in
the middle of a drain. The deadline cut aborts from inside `onSnapshot` (`deadlineSearch.ts:97-103`,
`cutIfFloorMet` at `:91-95`), which runs inside `applyAndReport`. From there `onOuterAbort` runs
`dispatchController.abort()`, and the pool and Maia abort listeners (`workerPoolDispatch.ts:286-312`,
`maiaQueue.ts:279-285`) run synchronously inside that same `onSnapshot`. The guarantee holds anyway, for three
reasons: (1) the apply that called `onSnapshot` is already done, (2) `wake` is null mid-drain, so the `notify()` in
`onOuterAbort` is a no-op, and (3) the next statement that matters is the same check on the next drained item, then
the loop-top `signal.aborted` test, so every later result is discarded. The listeners only settle promises, and
settlement callbacks run later as microtasks, so none of them re-enters the loop's state. The only flips an apply
can cause are `earlyStop = true` (stop rule) and an abort from inside `onSnapshot`, and both only affect later
results, which the same check discards.

**Why this is needed.** An aborted grade settles `new Map()` (`workerPoolDispatch.ts:288-292,308`), and a missing
grade becomes `NEUTRAL_EXPECTED_SCORE` (`mctsSearch.ts:458-459`). Applying such a result would fabricate 0.5-valued
children, back them up and fire a snapshot (L-2, Y-3). Round mode guards the same hazard with `if (signal.aborted)
break` before each apply (`:728`).

**Early stop.** When the stop rule fires inside an apply, the remaining settled results of that pass are discarded
(the `continue` above), the next loop iteration returns before dispatching, and the `finally` aborts the inner
controller. That cancels in-flight work: an unstarted grade is dequeued and an in-flight one is sent `stop`
(`workerPoolDispatch.ts:285-313`), so stale grades do not hold Stockfish slots into the next search. Maia
requests still in the app queue's backlog are dropped and resolve `{}` (`maiaQueue.ts:265-290`).

**Three consequences that are stated, not hidden.**
1. An in-flight Maia inference cannot be interrupted (`maiaQueue.ts:60-69`, `:255-264`). After an early stop it can
   delay the next search's first `policy()` by up to one P **in the app**. Round mode never has this, because its
   early stop comes only after the whole round resolved. Queued, not yet dispatched Maia requests are dropped and
   resolve `{}` (`maiaQueue.ts:279-285`). Measured P: about 36 to 46 ms on wasm t=4 and 18 to 23 ms on WebGPU in
   Plan 227-08's legs, 83 ms in the Node harness. Report-only, well below the stop-rule wall gains. The harness now
   matches the app's queue behavior (round-1 findings R1A-1 and R1B-1, tooling commit `399780bf8`): its Maia FIFO
   forwards the search signal, drops queued requests on abort and lets the in-flight one finish, and every gate script
   awaits `whenMaiaIdle()` before `pool.whenIdle()`, the memo and stat resets and the timer. So the in-flight
   remainder (up to one P) is not charged to the next timed row in the harness, whereas the app can pay it. Before
   that fix the harness charged the whole stale backlog (about 1.9 of the 3 surviving slots by Little's law, roughly
   75 to 120 ms or 4 to 6 percent of a stop-p4 search per R1A-1; 1.5 to 2.5 points of the modelled win per R1B-1,
   model estimates both) to the next row, in continuous mode only. Parity re-run on `399780bf8`: see section 7.
2. The app does not write the grade cache for a stopped search. A stopped in-flight request's late `bestmove` is
   discarded under `stopPending` (`workerPoolDispatch.ts:128-144`), and the only cache write is the normal
   `bestmove` path (`:146-166`) plus the root split's group success path. D-09 allows a grade that completed anyway
   to write, because its content is correct for `fen|depth`, and a grade that finished before the stop reached it
   does write (`:162-164`). Neither can corrupt the cache.
3. A cancelled grade leaves partial work in that worker's hash (mechanism M5 in 1.3). This is inside the accepted
   SEED-130 warm-hash nondeterminism.

**A fourth in-flight state: the policy settles after the stop** (round-1 finding R1B-6). An expansion whose Maia
policy is still pending when the search stops is neither queued-and-dropped nor a cancelled grade. If its request was
still queued it resolves `{}`, which `dispatchExpansion` turns into an empty candidate set and returns before any
`grade()` (WR-04). If its inference was already in flight it completes with a real policy, `dispatchExpansion`
resumes, and it calls `grade()` (`mctsSearch.ts:586`) with the already-aborted inner signal. No abort check sits
between `:533` and `:586`, but every pool returns empty at once without enqueuing for an aborted signal
(`workerPoolDispatch.ts:211`, `:377`; `stockfish-pool.mjs:293`, `:564-565`), so no Stockfish slot is taken. The result
settles into a closure whose loop has returned and is dropped. The app's join on a chart request already in flight
(`maiaQueue.ts:311-312`) is deliberately not abort-aware (the chart owns that entry), so a continuous search can hold
that promise past the abort. If the chart's request resolves, the same path follows. If it rejects, the fallback
`inFlight.catch(() => requestPolicy(fen, elo, signal))` (`maiaQueue.ts:311-312`) calls `requestPolicy`, which has no
aborted-signal check (`maiaQueue.ts:265-292`): an `'abort'` listener added to an already-aborted signal never fires,
so a stale request is enqueued and runs one full inference after the search has ended (app only; round-2 finding
R2B-5). Nothing is applied in either branch, so claim (d) holds. The cost is one wasted inference. A one-line
`if (signal?.aborted) return Promise.resolve({})` at the top of `requestPolicy` would close it. That is a frontend
change, so it is flagged for Plan 227-10 and not made here. Test obligation (section 2.12): the policy settles after
a stop, `grade` is called with an aborted signal, returns empty, enqueues nothing, and nothing applies.

**Deadline path.** `createDeadlineSearch` hands `mctsSearch` an inner signal and aborts it from two places
(`deadlineSearch.ts:91-124`). If the deadline expires before the node floor is reached, it arms the cut
(`:118-121`), and the abort fires from the first `onSnapshot` that crosses the floor (`:97-103`), which in
continuous mode is inside the drain (the synchronous case above). If the floor is already met when the deadline timer
fires, which is the common case, the timer macrotask aborts directly (`:118-121` calling `cutIfFloorMet`), while the
loop is awaiting a settlement. That abort wakes the loop through `onOuterAbort`'s `notify()` (section 2.7). In both
cases the loop's next check sees `signal.aborted`, returns, and the `finally` cancels in-flight work. So "the cut
happens at the snapshot that crosses the floor" is true only for the first case; in the second the loop returns at
the abort, with any settled-but-undrained results discarded. Either way no result is applied after the abort. The
existing comment at `deadlineSearch.ts:36-44` ("overrun bounded by one dispatch batch ... `budget.concurrency`-sized
round") is wrong for continuous mode and is reworded in Plan 227-10. In continuous mode the overrun past the floor is
bounded by the time to apply one expansion (first case) or zero (second case).

### 2.7 No missing wakeup (claim (e), X-8)

The loop awaits in exactly one place, and the check that precedes it and the assignment of `wake` are in the same
synchronous run.

- Settlement callbacks run as microtasks, never in the middle of a synchronous run of the loop. So no settlement can
  land between the read of `settled.length` and the assignment `wake = resolve` inside the Promise executor, which
  runs synchronously. `onOuterAbort` is different (round-1 finding R1A-6): `abort()` runs its listeners synchronously
  in the caller, so `onOuterAbort` CAN run in the middle of a synchronous run, for instance inside `onSnapshot` during
  a drain, or at entry for a pre-aborted signal. That is still safe: at that moment `wake` is null, so `notify()` does
  nothing, and the flag it set (`signal.aborted`) is read by the next check, which always follows (the next drained
  item's check, then the loop-top test). The one place where "always follows" needed a guard is a synchronous abort
  during a FILL (round-2 finding R2B-2): a provider's synchronous prefix (`dispatchExpansion` calls `providers.policy`
  synchronously, `mctsSearch.ts:533`) can abort the signal while `wake` is null, and the loop would then reach its
  `await` with nobody left to call `notify()`. A provider that hangs after the abort would hang the search. The sketch
  therefore re-checks `!signal.aborted && !st.earlyStop` immediately before the wait, and the loop-top test returns.
  The shipped providers cannot trigger this (the synchronous part of `maiaQueue.ts:295-314` never aborts and deadline
  and cancel aborts are macrotasks, `deadlineSearch.ts:118-121`), so it is a guard on the loop's own contract, not a
  fix for an observed bug. When the abort comes from outside the loop (the deadline timer macrotask, a
  user cancel) the loop is awaiting, `wake` is set, and `notify()` resolves it.
- A settlement pushes to `settled` first and then calls `notify()`. If the loop is awaiting, `wake` is set and is
  resolved. If it is not awaiting, which can only be the gap between a resolved wake and the loop's continuation,
  `wake` is null and `notify()` does nothing. The item is already in `settled`, and the drain takes it.
- `notify()` clears `wake` before invoking it, so one wake resolves at most one await and a stale resolver is never
  called twice.
- The drain loop has no `await`, so settlements cannot interleave with a drain. Between the moment `notify()`
  resolves the wait and the moment the loop's continuation runs, other settlements can land. They find `wake` null,
  push to `settled`, and the continuation's `while (settled.length > 0)` drain takes them.
- Abort also calls `notify()`, so a loop waiting on slow work wakes at once, sees `signal.aborted` and returns. An
  abort raised during a fill is caught by the re-check before the wait. Round mode cannot do either: a stuck
  `Promise.all` is not freed by an abort (X-9).
- Already-resolved providers (a Maia policy cache hit is `Promise.resolve(cached)`, `maiaQueue.ts:297-298`; a grade
  cache hit is `Promise.resolve(hit)`, `workerPoolDispatch.ts:223-224`) settle through `.then` after the loop has
  reached its `await`, so the wake is installed before it is needed.

The `settled.length === 0` part of the guard before the `await` is, in the sketch's structure, always true, because a
drain runs to empty and settlements arrive as microtasks. It is kept so that a later change that adds an `await`
between the drain and the next fill cannot introduce the hazard silently. The `!signal.aborted && !st.earlyStop` part
is the one that carries weight (R2B-2).

**Test shape (obligation for Plan 227-10).** All providers return already-resolved promises and the search must
complete; a provider settles during the drain of another result; abort while waiting wakes the loop, including an
abort fired by a timer (a fake-timer deadline abort with several expansions in flight: the loop returns without
applying them and the in-flight work is cancelled); and a synchronous abort during a fill (a fixture whose `policy()`
aborts the search signal in its synchronous prefix and whose `grade` never settles: the search must return, not
hang; round-2 finding R2B-2).

### 2.8 Rejection propagation (Y-8)

A rejection is captured as a value (`.then(ok, err)`), so no unhandled rejection exists even after an early return.
When the drain reaches a rejected item and neither `signal.aborted` nor `st.earlyStop` is set, it throws. The
`finally` then aborts the inner controller, which cancels siblings. The caller sees the same rejection `Promise.all`
would have produced. **One rule, stated once (round-2 finding R2A-6):** the abort and early-stop test comes before
the rejection test, so every rejection that is drained after a stop or an abort is dropped, whether it was queued
behind the stopping item in the same drain or arrived a microtask later. Failing a search that already completed
correctly would be the wrong outcome (reason 1 below), and the earlier ordering (throw first) made the outcome depend
on whether the rejection happened to settle before or after the stopping apply. Claim (c) still holds, because at
`c = 1` nothing else is queued in the same drain: the rejection is the only item, no stop can precede it, and it
throws exactly as round mode does when no abort precedes it. With an abort first, a late rejection makes round mode
throw and continuous mode return the snapshot (section 2.4, scope limit 1). Two accepted differences at `c > 1`:
expansions that had already been applied before the rejection arrived stay applied and their snapshots were already
emitted, whereas round mode rejected before applying any member of the round; and a rejection queued behind an apply
that fires the stop rule is dropped, whereas round mode (`Promise.all`) rejects the whole round. The analysis
hook commits snapshots as they arrive and its `.catch` leaves them displayed (`useFlawChessEngine.ts:396-414`), in
both modes, so a partial snapshot is already visible to that caller either way.

**Late rejections, disposition (Y-8, round-1 finding R1A-2).** A rejection from work that settles after
`runContinuous` has returned goes to a dead closure and is dropped, with no log and no Sentry call. That is a
decision, not an oversight, for three reasons. (1) Such work was cancelled by the search itself, so its result is
unwanted by definition, and failing a search that already completed correctly would be the wrong outcome. (2) The
app providers do not reject: every failure path resolves empty, and the one that is a bug (Maia inference throws) is
already reported to Sentry at its source (`maiaQueue.ts:183-189`, `source: 'maia-queue'`), so no failure is lost
(`workerPoolWatchdog.ts:169,213`, `workerPoolLifecycle.ts:115,194,297,305,318,323` resolve empty for the pool).
(3) `mctsSearch.ts` has no Sentry or console use today and stays a pure module. Visibility is guaranteed where it
matters (a rejection before the stop is thrown by the drain), and the late case is pinned by the fixture in section
2.4 (no unhandled rejection event, the returned snapshot is intact).

### 2.9 Listener hygiene (Pitfall 7)

The outer signal gets exactly one listener, added once with `{ once: true }` and removed in the `finally`
(`workerPoolDispatch.ts:271-279` records the lesson: a 400-node search accumulated about 400 listeners). No
per-dispatch listener is ever attached to the outer signal. Every `dispatchExpansion` receives the inner signal, so
the pool's and the Maia queue's per-request listeners attach to a signal that dies with the search, and each is
removed when its request settles (`workerPoolDispatch.ts:277-281`, `maiaQueue.ts:273-276`).

### 2.10 Arrival order, pending exclusion, nothing rebuilt (D-08, D-11)

Results apply in the order they settle. A leaf stays pending until it applies, so no leaf is dispatched twice. A
cheap grade frees its slot at once, so there is no head-of-line wait (X-5). This design rebuilds none of: a commit
window, a ring buffer, `commitSeq`, slot release on commit, priority activation. `priority: 0, depth: 0` stays
(`workerPoolDispatch.ts:259-260`).

Order can affect output (C5, M1 to M5). That is the relaxed contract (226 D-05 read through D-01), and the gate
judges the effect statistically against d20 truth, not by identity. This document makes no claim to the contrary.

### 2.11 Text that Plan 227-10 must reword

- `mctsSearch.ts:40-44` and `:46-54` (module header: "applied ... via `Promise.all`'s order-preserving resolution"
  and "output is deterministic PER concurrency level ... bit-identical regardless of provider resolution jitter").
  True of round mode with deterministic providers, false of continuous mode.
- `mctsSearch.ts:720-722` ("Buffer-then-apply-in-canonical-order").
- Further comments that become false in continuous mode (round-2 finding R2A-8): `mctsSearch.ts:30-37` (module
  header: expansions "selected synchronously within one round", blocked "for the rest of the round"),
  `:298-309` (the stop rule "evaluated ... in the canonical apply-order loop"), `:491-499` ("same-round re-pick",
  "the invariant delivered is determinism per concurrency level"), `:514-516` ("`applyExpansion` performs all
  mutation once every concurrent dispatch has resolved") and `:735` ("SAME canonical apply-order loop").
- Comments that describe a "round", a "round barrier" or a bulk clear "before `Promise.all`" as the only shape
  (round-1 finding R1B-9): `mctsSearch.ts:113` (`isPending` "within a dispatch round"), `:126-136` (`isBlocked`
  "for the REST OF THE CURRENT dispatch round", "cleared ... before `Promise.all`"), `:345-360` (`selectPath` doc,
  "this round", `blockedThisRound`), `:575-583` ("The round barrier, selection ... apply order ... are all
  untouched"), `:602-603` ("the apply loop discards an aborted result entirely"; in continuous mode that is the
  drain's check).
- `maiaQueue.ts:259-263` ("the orchestrator's own apply loop breaks on `signal.aborted` before applying anything"):
  in continuous mode it is the drain's check.
- `deadlineSearch.ts:36-44` (section 2.6).
- `scripts/calibration-harness.mjs:405-406` ("Content-neutral for round mode"): true only at `--hash clear`
  (section 1.4). The path in the first draft was wrong.
- Tooling comments that claim quiescence the code does not give (round-1 finding R1B-9):
  `scripts/engine-dispatch-stop-rule.mjs:46-48` (header: "Every position starts from a quiesced pool") and the
  `whenIdle` docs (`scripts/lib/stockfish-pool.mjs:591-595`, `scripts/engine-dispatch-stop-rule.mjs:439`) cover
  Stockfish only. They must also name `whenMaiaIdle()` (`scripts/lib/calibration-providers.mjs`). This is a comment
  change in tooling, so it is not made in this repair step; Plan 227-09 Task 3 or Plan 227-10 makes it.
- `scripts/lib/node-engine-providers.mjs:120` (round-2 findings R2A-5, R2A-9): the comment "matches the browser
  worker's no-COOP/COEP posture" is stale, because the browser runs wasm Maia at `numThreads` 4 (section 3.6, first row).
  Tooling comment, same assignment as the previous item.
- `requestPolicy` in `maiaQueue.ts:265-292` has no aborted-signal check, so the `inFlight.catch` fallback at `:311-312`
  can enqueue a stale request after a stop (section 2.6, round-2 finding R2B-5). A one-line guard is flagged for Plan
  227-10. It is not a rewording and is not made here.

### 2.12 Verification obligations (for Plan 227-10), one mutation per guard

| Claim or rule | Test | Mutation that must fail it |
|---|---|---|
| (a) per-fill blocks | peaked-policy fixture: continuous keeps `c` in flight; a settle between fills makes a stale block observable | drop the end-of-fill clear |
| (b) budget | `nodesEvaluated <= maxNodes`, dispatches `<= maxNodes + degenerate`, `inFlight == 0` whenever `nodesEvaluated === maxNodes` (keyed on the count, never on `budgetExhausted` or `stopReason`, which a `maxPlies` cut also sets with `inFlight > 0`, R2A-7, R2B-7) | drop `+ inFlight` from the fill guard |
| (c) `c = 1` identity | section 2.4 fixtures, different jitter per mode, call lists after quiescence; pre-extraction goldens | make the fill run while a result is in flight |
| (c) `c = 1` external abort in flight | deferred provider aborted from outside: equal snapshots, continuous resolves before the provider settles, round after; equal call lists after quiescence | make the loop await in-flight work after an abort (drop the `notify()` in `onOuterAbort`) |
| (c) late rejection after abort | provider rejects after the abort: continuous returns the snapshot with no unhandled rejection, round throws (accepted divergence, pinned) | await the settled queue after abort, or rethrow a late rejection |
| (c) extraction safety | pre-extraction goldens equal; `--hash clear` parity re-run 0 diffs against `tripwire/parity-clear` | change round behavior inside `applyAndReport` or `discoverDeadEnd` |
| (d) abort and stop | settle-after-abort, settle-after-early-stop, abort inside `onSnapshot` with several results queued | remove the check before `applyAndReport` |
| (d) timer-driven deadline abort | fake-timer abort with several expansions in flight and the floor already met: the loop wakes, returns, applies none, cancels in-flight work | drop `notify()` from `onOuterAbort` |
| (d) policy settles after stop | the policy resolves after the stop: `grade` receives an aborted signal, returns empty, nothing enqueued, nothing applied | drop `dispatchController.abort()` from the `finally` |
| (e) wakeup | already-resolved providers; settle during drain; abort while waiting (including a timer abort) | assign `wake` after an `await` |
| (e) synchronous abort during a fill (R2B-2) | `policy()` aborts the signal in its synchronous prefix and `grade` never settles: the search returns | drop `!signal.aborted && !st.earlyStop` from the guard before the wait |
| Rejection after stop (R2A-6) | a rejected item queued behind an apply that fires the stop rule, or behind an abort inside `onSnapshot`, is dropped and the snapshot is returned; a rejection with no stop throws | check `kind === 'rejected'` before the abort and early-stop test |
| Rejection (Y-8) | rejection propagates, siblings' signals aborted, no unhandled rejection | swallow the rejection |
| Pitfall 7 | spy `addEventListener` and `removeEventListener` on the outer signal | drop the removal |
| Root guard (Y-9) | exactly one dispatch until the root applies | let the fill dispatch past the pending root |

## 3. Harness fidelity (claim (f))

Claim (f) is that the harness measures the same algorithm with app-faithful timing. "Same algorithm" is strict: the
gate scripts import the same `mctsSearch` module through the `@/` alias (`scripts/lib/frontend-alias-hook.mjs`) and
select the loop with the same `SearchBudget.dispatchMode`. "App-faithful timing" is structural, and its limits are
listed in 3.6. The claim is not that the harness reproduces the browser's absolute times.

### 3.1 N-1: Maia off the harness event loop (D-18, Plan 227-01)

Before: harness Maia was onnxruntime-web wasm on the Node main thread. One inference blocked the event loop for its
whole duration (about 94 ms), and FIFO-chained inferences let no macrotask run (0 timer ticks across a 373 ms
four-request burst), so Stockfish child-process output went unprocessed while Maia worked. Continuous mode would
have been measured crippled.

After: `createMaiaSession({ offThread = true })` runs the session in a `worker_threads` worker behind an unchanged
`run(feeds)` proxy (`scripts/lib/node-engine-providers.mjs:102-125`, `scripts/lib/maia-worker-thread.mjs`).
Measured in Plan 227-01 over the same four-request burst: max event-loop lag 6.3 to 15.4 ms on the worker session
(35 timer ticks) against 354.8 to 363 ms on the main-thread negative control (0 ticks), logits byte-identical on
14 of 14 (FEN, ELO) pairs. Plan 227-04 smokes read `loop_lag_max_ms` 1.5 to 9.7 ms.

Cost: the harness is now timing-dependent for warm-hash round mode too (section 1.4). That is the same property the
browser has, so it makes the harness more faithful, and the owner has accepted it.

### 3.2 N-2: pool abort (D-09, Plans 227-01 and 227-04)

The Node Stockfish pools used to ignore the abort signal (`stockfish-pool.mjs` documented it as "deliberately NOT
acted on"). After an early stop, stale grades ran into the next position's timing window and tripped the root-split
premise counter. `withEngine(pool, fn, signal, abortValue)` now mirrors the browser pool
(`scripts/lib/stockfish-pool.mjs:283-320`): a queued request is dropped, an in-flight one is sent `stop` and its
result discarded, the engine is released on `bestmove`. `grade` and `gradeRoot` honor it (`:521-541,564-588`),
`gradeRoot` resolves empty on abort and never a partial merge, and `whenIdle()` (`:591-596`) lets the gate scripts
quiesce the pool before every timed position. `createGradePool` in the stop-rule script and the depth-ab closures
forward the signal (Plan 227-04). `whenIdle()` covers Stockfish only.

**N-2b: Maia FIFO abort and `whenMaiaIdle` (round-1 findings R1A-1 and R1B-1, tooling commit `399780bf8`).** The
harness Maia FIFO (`--maia-fifo`, `scripts/lib/calibration-providers.mjs`) used to drop the search signal, so after a
continuous early stop its queued stale inferences ran into the next row's timed window and its stat resets, in
continuous mode only (round mode's early stop comes after the barrier, and a budget stop has `F = 0`, section 2.3).
It now mirrors `maiaQueue.ts`'s `requestPolicy`: a pre-aborted signal never enqueues, an abort drops a still-queued
request and resolves it `{}`, an in-flight inference runs to completion. `whenMaiaIdle()` resolves when no inference
is in flight and the FIFO is empty, and every gate script awaits it before `pool.whenIdle()`, the memo reset and the
timer (`engine-dispatch-stop-rule.mjs:735`, `engine-move-quality.mjs:644`, `engine-grading-depth-ab.mjs:745,817`,
`engine-search-trace.mjs:575`). `engine-search-trace.mjs` is an unjudged diagnostic, not a gate arm: it builds its
providers without `maiaFifo` or `gradeRoot` (`:580`), so Pitfall 4's "every gate arm" excludes it (round-2 finding
R2A-12). `resetMaiaInstrumentationStats` no longer zeroes the live in-flight gauge, which a
stale call's `finally` had driven to -1 so that a later real two-way overlap read 1 and passed the
`_MAIA_MAX_PEAK_INFLIGHT = 1` check. Check (f) in `scripts/lib/maia-instrumentation.check.mjs` covers it and was
mutation-tested (dropping the signal, and an always-idle `whenMaiaIdle`, each fail it). Parity re-run on
`399780bf8`: see section 7.

### 3.3 N-3: app queue FIFO (D-19, Plan 227-02)

`dequeueHighestPriority` used to break ties by the first candidate UCI, so on pool 2 with `c = 4` a queued grade could
lose repeatedly to newer requests with lexicographically smaller moves, an unbounded wait once dispatch is continuous.
It now serves equal `(priority, depth)` requests in arrival order (`workerPoolState.ts:450-475`), matching the
harness pool. This is a prerequisite for continuous mode on pool 2, and the Node pool-2 configs could not have seen
the defect.

### 3.4 N-4: grade-elapsed normalization bias (D-17, Plan 227-07)

226's "grade CPU" is per-grade wall elapsed (`engine-grading-depth-ab.mjs:329`, `engine-dispatch-stop-rule.mjs:345-350`),
not CPU time. Continuous mode runs Maia and Stockfish at once, so contention inflates per-grade elapsed and flatters
wall divided by grade elapsed. D-17 therefore judges **interleaved raw wall normalized by an external machine-speed
probe** (`scripts/engine-speed-probe.mjs`: fixed Stockfish node searches plus fixed Maia inferences, about 13.1 s,
two runs 0.99 percent apart), as the geometric mean over rounds of the per-round ratio
`(W_a1 / P_a1) / (W_a0 / P_a0)`. The driver `scripts/engine_interleave_227.py` interleaves both arms, rotates config
order, waits for a load average below `LOAD_GATE_MAX = 2.0` (`:95`) and probes before every step. Grade-elapsed
normalization stays as a report-only column.

### 3.5 What makes a label-only run impossible, and the tripwire

- Every gate script and the calibration harness call `assertDispatchModeLive` before any engine starts
  (`scripts/lib/dispatch-mode.mjs:163,207`; `scripts/calibration-harness.mjs:1736-1741`; `scripts/engine-move-quality.mjs:595-596`).
  It runs the real `mctsSearch` against mock providers with deferred grades and observes whether a new expansion is
  dispatched while another is still in flight. A requested mode the engine did not run exits 3 before any
  measurement. Today every `--dispatch-mode continuous` exits 3, because the loop does not exist yet.
- Every output row stamps `dispatch_mode`, and the verdict twin rejects a row whose mode differs from its arm
  (`engine_dispatch_227_verdict.py:530-533`), a judged MQ row without `maia_fifo` or without `hash_mode = warm`
  (`:534-537`).
- Pitfall 4: Maia runs through the app-faithful single-in-flight, abort-aware FIFO in every gate arm (`--maia-fifo` is
  in each pinned command, `engine_interleave_227.py:220-251`; the calibration harness hard-codes it,
  `calibration-harness.mjs:400-410`; the throughput manifest requires one peak in flight, twin `:740`).
- Pitfall 10: the calibration ledger carries `dispatch_mode` as its last column (`calibration-harness.mjs:1256-1258`),
  `--resume` refuses a different mode or a pre-227 ledger (`:1538-1542,1565-1568`), and the supervisor passes
  `PRESET_SUPERVISOR_DISPATCH_MODE` on every launch and crash-resume (`bin/preset-supervisor.sh:40-49,78,112`).
- Tripwire (Plan 227-08): the round-mode content of the new harness equals main-thread Maia at `--hash clear`
  (0 of 60, both stop modes) and is report-only similar to 226 a21s at `--hash warm` (section 1.4). That result is
  from tooling commit `cef88fd87`; the Maia FIFO change in `399780bf8` touches `calibration-providers.mjs`, so the
  check is re-run on it (result: see section 7).

### 3.6 What the harness does not reproduce (the limits of claim (f))

| Aspect | App | Harness | Effect on the gate |
|---|---|---|---|
| Maia per-inference time P | wasm t=4 about 36 to 46 ms, WebGPU about 18 to 23 ms (Plan 227-08 legs, measured) | onnxruntime-web `numThreads = 1`, P = 83.3 and 85.1 ms (a21s TSVs, measured; `node-engine-providers.mjs:120`) | The Node gate runs at about 2 times the browser's wasm P. Structure (one inference in flight, off the search thread) is the same, speed is not. Section 4 sizes the browser separately. The comment at `node-engine-providers.mjs:120` ("matches the browser worker's no-COOP/COEP posture") is stale (section 2.11). CPU contention is also not reproduced (round-2 finding R2A-5): the harness Maia runs one wasm thread on a 16-core box next to Stockfish child processes, so it sees almost no Maia-versus-Stockfish contention. Continuous mode overlaps the two more than round mode does, so on 4 to 8 core devices it is more exposed to that contention than the gate shows. The busy-P legs of Plan 227-08 (P measured while Stockfish runs) cover it only partly, and the row records speed only. |
| Stockfish | vendored wasm in Web Workers | the same vendored wasm in Node child processes (`node-engine-providers.mjs:433-451`) | Same engine, different host. Browser G is not measured in isolation. |
| Grade cache | `GradeCache` in the pool (`workerPool.ts:259`) | none in the gate providers (only `engine-root-injection.mjs` wraps it) | The gate cannot see the M3 settlement race or any cache hit effect. D-11 accepts the race. The browser bench page uses the real pool and covers it in the WebGPU leg. |
| Wall-clock deadline | `createDeadlineSearch` cuts a search mid-flight | none in the MQ and throughput scripts | The abort-under-deadline path is covered by unit tests only. |
| Main thread | React and UI share it with the search | the search has the process | Small; report-only. |
| Hash | never cleared: no `ucinewgame` and no `Clear Hash` anywhere in `frontend/src` (zero hits), so a worker's table lives across searches | `--hash warm` skips `Clear Hash` per grade, but every gate script calls `pool.resetAll()` before every position (defined in the scripts' `createGradePool`, `engine-dispatch-stop-rule.mjs:438` and `engine-grading-depth-ab.mjs:570`), and that calls `pool.newGameAll()` (`stockfish-pool.mjs:647-658`), which sends `ucinewgame` to every engine (`engine-dispatch-stop-rule.mjs:737`, `engine-move-quality.mjs:646`, `engine-grading-depth-ab.mjs:747,819`, `engine-search-trace.mjs:577`). Warm hash therefore lasts ONE search | **Does not match** (round-1 finding R1B-2; the first draft said "Matches"). The gate sees within-search warmth, the within-search part of M4. It cannot see the cross-search part of M4, and it cannot see M5 (cancelled partial work read by the next search) at all. M5 is present in both modes (cancellation on abort) and amplified in continuous mode (cancellation on early stop, section 1.3), so the gate is blind to an effect that is present in both arms and larger in continuous. The browser WebGPU leg uses the real, never-cleared pool, but only as D-07's "not slower" point. `--hash clear` runs are report-only. A report-only cross-search variant (no `resetAll` between the consecutive searches of one game) is a possible follow-up, not built here. |
| Hash in the calibration arms (D-15) | as above | the calibration harness builds `createStockfishPool({ size })` (`calibration-harness.mjs:394`) whose default is `clearHash = true` (`stockfish-pool.mjs:452`), so every grade sends `Clear Hash` (`calibration-providers.mjs:534`), and `pool.newGameAll()` runs per game (`calibration-game-loop.mjs:160`) | Persona refits in the D-15 arms run with a cold table on every grade, unlike the app. This is the 226 arrangement, unchanged by this phase. A continuous-mode refit inherits it, so M4 and M5 are absent from the calibration arms too. |
| Maia queue on abort | queued requests dropped and resolved `{}`, an in-flight inference completes (`maiaQueue.ts:279-285`), so the next search's first `policy()` can wait up to one P | since `399780bf8` the same: the FIFO forwards the signal, drops queued requests, lets the in-flight one finish; `whenMaiaIdle()` is awaited before each timed row | Matches for queue behavior. The harness does not charge the in-flight remainder (up to one P) to the next row, whereas the app can. Before the fix the harness charged the whole stale backlog to the next row in continuous mode (section 2.6). Round 3 (R3B-2): on an abort the harness FIFO checks `signal.aborted` before the memo (`calibration-providers.mjs:378`), while the app checks its policy cache first (`maiaQueue.ts:297-301`), so after a stop an app cache hit resolves a real policy and then makes an aborted (empty) grade call where the harness makes none; applied results and timing are unaffected, call counts differ. Round 3 (R3B-3): the harness pool can reject (`stockfish-pool.mjs:337`, gate `gradeRoot` rethrow), so under the section 2.8 rule a harness engine error drained after a stop is dropped silently in continuous mode; round mode cannot reach that state. |
| Maia policy cache across searches | the shared policy cache persists across searches (`maiaQueue.ts:12-15`, `:297-298`), so on consecutive searches many policies are cache hits | the gates reset the memo before every position (`resetMaiaRunMemo`: `engine-dispatch-stop-rule.mjs:738`, `engine-grading-depth-ab.mjs:748,820`, `engine-move-quality.mjs:647`) | Effective P is lower in the app on consecutive searches than in the gate. The effect on the win is **non-monotonic** (round-2 findings R2A-4, R2B-1). In the Maia-bound regime (P above `P* = G / (c - 1)`) the reduction is `(G/c) / (P + G/c)`, so a lower P RAISES the win, down to the peak at `P*`. Only below `P*`, in the `(P + G) / c` regime, does the reduction `(c - 1) P / (c P + G)` fall as P falls. Model check at G = 173.9, `c = s = 4`: P = 83.3 gives 34.3 percent (the Node baseline), P = 70 gives 38.3, P = 58 gives 42.9, P = 40 gives 35.9 and P = 30 gives 30.6. The app's win exceeds the Node baseline unless its effective P falls below about 36 ms. So no "upper estimate" claim is made for the gate's figures. Not measured. |
| No quiesce between searches | none: after an early stop or abort, slots can still be `stopping` until their `bestmove` arrives (`workerPoolDispatch.ts:128-139`, `:303-308`), and the next search's root `gradeRoot` counts only idle ready slots (`countIdleReadySlots`, `:345-352`; `k <= 1` falls back to a plain `grade`, `:384-385`) | `whenMaiaIdle()` and `pool.whenIdle()` before every timed position | The app's next search can see a reduced root fan-out (up to `c - 1` stopping slots after a continuous early stop, routine there) and a delayed first policy. The bot hides this behind the human's move time. The analysis path aborts and restarts on every position or `extraRootMoves` change (`useFlawChessEngine.ts:95-96,351-352,396`), so stopping slots and a reduced root fan-out are routine there in both modes (round-2 finding R2A-2). The gate hides all of it. Report-only, not measured. |
| Maia memo hits in the FIFO | a policy cache hit bypasses the queue entirely (`maiaQueue.ts:297-298`) | `maiaFifoPolicy` enqueues every request and the memo is consulted only once the request is dispatched (`calibration-providers.mjs:377-399`, `:231-232` via `nodePolicy` `:442`), so a memo-hit expansion waits behind up to `c - 1` inferences | Harness only, both arms. It touches the 2 to 10 percent of nodes that are memo hits (0.90 to 0.98 inferences per node, section 4.1) and matters only when the FIFO binds (pool 4). Report-only; making the FIFO check the memo before enqueueing would be a tooling change, not made here (round-2 findings R2A-3, R2B-6). |
| Other Maia traffic on /analysis | the shared Maia worker also serves the chart and the gem sweep, and chart requests are queued ahead of the search's (`maiaWorkerHost.ts:274-292`; `maiaQueue.ts:24-37`) | none | The app's effective P on /analysis can exceed the idle P. The harness has no such traffic. Report-only, not measured (round-2 finding R2B-6). |
| Root split | `gradeRoot` fans the root over idle workers | the same `gradeRoot` via the pool | Matches when the pool is quiet; see the previous row for the app's non-quiet case. |
| Pool size and `c` | pool 2 to 4; bot `c = 4`; analysis `c = computePoolSize()` (`useFlawChessEngine.ts:369`) so `c` equals the pool | `--pool-size` 4 and 2, same `c` | Matches by construction. Only the bot runs `c` above the pool (`t50-p2`). |

Claim (f), stated with its limits: the harness runs the same loop selection and the same dispatch code, with the same
concurrency model (single in-flight Maia off the search thread with the app's abort behavior, abort-aware FIFO
Stockfish pool of the same size, root split) and timing that is measured, not assumed. It does not reproduce browser
P and G in absolute terms, Maia versus Stockfish CPU contention, the grade cache, the deadline cut, the app's
cross-search Maia cache (and its memo-hit bypass of the FIFO), other Maia traffic on /analysis, the app's lack of
inter-search quiescence, or the app's never-cleared Stockfish hash (the gate clears it between searches, so it
cannot measure M5 or the cross-search part of M4). The D-04 ship bar is judged on the Node gate; the browser and
WebGPU effect is bounded by D-07's single "not slower" point and sized in section 4.

## 4. Throughput sizing

### 4.1 The model

Per-expansion cost, with `c` slots, a pool of `s` Stockfish workers, one serial Maia FIFO of per-inference time `P`
and a grade of time `G`:

```
continuous = max( P , G / s , (P + G) / c )        (slot occupancy is P + G because dispatchExpansion awaits
                                                     policy (mctsSearch.ts:533) and then grade (:586))
round      = P + G / c                (s >= c)     (c policies serial in the FIFO, then c grades in parallel: cP + G per round)
           = pipeline simulation      (s <  c)     (Appendix A `round_ms`; no closed form, see X-11)
reduction  = 1 - continuous / round
```

The first draft used `P + ceil(c / s) * G / c` for `s < c`. That ignores that later slots' policies run while earlier
grades are still searching, and it over-stated the t50-p2 round time by 33 percent (168.3 ms against a measured
131.2 ms per node; round-1 finding R1A-4). It is dropped.

This is the corrected X-2 form, `min(1/P, s/G, c/(P+G))` for throughput. At `c = 1` it gives exactly 0 percent, the
only possible answer, which is the algebraic twin of the byte-identity claim. The reduction is non-monotonic in `P`
(Y-12): at fixed `c` it peaks at `P* = G / (c - 1)` with peak value `(c - 1) / (2c - 1)`, which is 42.9 percent at
`c = 4`. A modestly faster policy raises the win up to that peak. A much faster policy lowers it, because the
`(P + G) / c` term then binds. In the `(P + G) / c` regime the reduction is `(c - 1) P / (c P + G)`, which rises with
`P` (it falls as P falls). In the Maia-bound regime (P above `P*`) it is `(G/c) / (P + G/c)`, which falls as P rises.
So a lower P helps down to `P*` and hurts below it (section 3.6, Maia policy cache row). Every number below is **model output** from the measured inputs named beside it.

Two corrections to the inputs (round-1 findings R1A-3, R1A-5):

- **Per-node Maia time, not per-inference.** `P = maia_cpu_ms / maia_inferences` is the cost of one inference, but the
  Maia memo answers some expansions without an inference: the 226 TSVs show 0.98, 0.91, 0.90 and 0.98 inferences per
  node (t50-p4, t400-p4, t400-p2, t50-p2). The Maia floor of the continuous loop is the per-node figure
  `Pn = maia_cpu_ms / nodes`. Both are listed below. For the browser, applying the same factor to P moves the modelled
  reduction by about 1 point (computed for wasm busy P and WebGPU busy P).
- **G is inflated in the 226 data.** `grade_cpu_ms` is the time from `go` until the `bestmove` line is processed in JS
  (`engine-grading-depth-ab.mjs:329-335`, `engine-dispatch-stop-rule.mjs:340-350`). The 226 runs used main-thread Maia,
  which section 3.1 says left Stockfish output unprocessed during inference, so G includes Maia blocking and is an
  upper bound. The direction of the bias differs by regime: a lower true G lowers the Maia-bound estimates
  (section 4.4 sensitivity) and raises the `(P + G) / c`-bound browser estimates (section 4.3).

### 4.2 Node gate configs (measured inputs, model output)

Inputs: `reports/data/engine-throughput-226/gate/a21s/throughput/{t50-p4,t400-p4,t50-p2,t400-p2}/*.tsv`, the 16
`depth = ladder` rows of each (800 nodes in the t50 configs, 6400 in the t400 configs). Per inference:
`P = sum(maia_cpu_ms) / sum(maia_inferences)`, `G = sum(grade_cpu_ms) / sum(grade_calls)`. Per node: `Pn =
sum(maia_cpu_ms) / sum(nodes_evaluated)`, `Gn = sum(grade_cpu_ms) / sum(nodes_evaluated)`, `W = sum(wall_ms) /
sum(nodes_evaluated)`. All of these were recomputed from the TSVs for this repair and reproduce the reviewers' values.

**Table 1, nominal model (per-inference P and G).** Model output.

| Config | `c` | pool | P (ms) | G (ms) | `c* = 1 + G/P` | `P* = G/(c-1)` | round (ms/exp) | continuous (ms/exp) | nominal reduction |
|---|---|---|---|---|---|---|---|---|---|
| t50-p4 | 4 | 4 | 83.3 | 173.9 | 3.09 | 58.0 | 126.7 | 83.3 | 34.3 percent |
| t400-p4 | 4 | 4 | 85.1 | 143.7 | 2.69 | 47.9 | 121.0 | 85.1 | 29.7 percent |
| t400-p2 | 2 | 2 | 83.1 | 75.5 | 1.91 | 75.5 | 120.9 | 83.1 | 31.2 percent |
| t50-p2 | 4 | 2 | 83.3 | 169.9 | 3.04 | 56.6 | 126.6 (simulation) | 85.0 | 32.9 percent (model only) |

**Table 2, validation against measured round wall (R1A-3).** The model's round time against the measured round wall
`W` of the same TSVs, and the corrected ceiling on the reduction. The ceiling takes `W` as the round time and the
continuous floor `max(Pn, Gn / s, (Pn + Gn) / c)` as the best the continuous loop can do. A floor on time is a ceiling
on the win: it assumes the pipeline reaches its bottleneck rate, ignores ramp-up and CPU contention between the Maia
worker and the Stockfish children, and uses the inflated G, so the real reduction is lower. Model output.

| Config | model round (ms/node) | measured `W` (ms/node) | model error | `Pn` | `Gn / s` | `(Pn + Gn) / c` | binding term | ceiling reduction |
|---|---|---|---|---|---|---|---|---|
| t50-p4 | 126.7 | 120.8 | +4.9 percent | 81.8 | 45.9 | 66.4 | `Pn` | 32.3 percent |
| t400-p4 | 121.0 | 98.4 | +23.0 percent | 77.2 | 36.2 | 55.5 | `Pn` | 21.5 percent |
| t400-p2 | 120.9 | 110.7 | +9.2 percent | 74.6 | 37.9 | 75.2 | `(Pn + Gn) / c` | 32.1 percent |
| t50-p2 | 126.6 | 131.2 | -3.5 percent | 82.0 | 86.7 | 63.8 | `Gn / s` | 33.9 percent |

Reading. (1) The nominal model is within 10 percent of the measured wall in three of four configs and 23 percent too
high on t400-p4, so its absolute error is about 25 percent and the t400-p4 estimate in Table 1 (29.7 percent) is not
supported. The measured-wall ceiling there is 21.5 percent. (2) The `t400-p4` ceiling is 6.5 points above D-04's 15
percent bar, so on that ship-bar config continuous must realise about 70 percent of the ideal pipeline win. This is
thin and is stated plainly. (3) The binding term is `Pn` (the serial Maia FIFO) in both pool-4 configs, so the
reduction there is `1 - Pn / W`. In t400-p2 (`c = 2`) the `(Pn + Gn) / c` term binds, and in t50-p2 `Gn / s` does.
(4) G inflation (section 4.1) enters the ceiling only through the floor, because `W` is measured. An inflated G can
only raise `Gn / s` and `(Pn + Gn) / c`, never `Pn`, so it leaves the two pool-4 ceilings untouched (`Pn` binds with
a wide margin) and can only understate the t400-p2 and t50-p2 ceilings (for t50-p2, 37.5 percent if `Pn = 82.0` bound
instead). All four ceilings are ceilings, not predictions.

The first draft's statement "about 30 percent on the Node analysis path" is withdrawn. The analysis path runs `c`
equal to the pool (`useFlawChessEngine.ts:369`), which are the `t400-p4` and `t400-p2` configs: ceilings 21.5 and
32.1 percent, nominal 29.7 and 31.2 percent, in a range of about 21 to 32 percent.

The judged bot-move config (`stop-p4`, stop rule on, 16 positions) takes its P and G from the stop-off `t50-p4` TSV,
because 226 recorded no grade-CPU column for the stop-rule run. That is a proxy. The 16 stop-on searches ended at 8, 8,
8, 8, 10, 10, 13, 15, 15, 15, 28, 50, 50, 50, 50, 50 nodes (mean 24.2;
`reports/data/engine-throughput-226/gate/a21s/stop/*stopon*.tsv`, 388 nodes in total; 11 early stops, 5 budget
stops). Unlike the throughput TSVs, that file does record `maia_cpu_ms` and `wall_ms`, so it validates the bot-path
model directly: measured round wall 55.4 s, measured Maia busy time 32.9 s (84.9 ms per node). Section 4.4 compares
this with the model.

### 4.3 Browser bot path (measured P from Plan 227-08, G from Node)

P is the idle and Stockfish-busy median batch-1 Maia latency of Plan 227-08's legs
(`reports/data/continuous-dispatch-227/webgpu/local-wasm-round-leg.json` for this box, `round-leg.json` for the
owner's machine). `c = 4`, pool 4 in both legs. `G` is the Node `t50-p4` value 173.9 ms (assumption A4: browser G
unmeasured) and, as a sensitivity, the Node `t400-p4` value 143.7 ms.

| Backend and machine | P idle / busy (ms) | `c*` at G = 173.9 (busy P) | reduction at G = 173.9, busy P | reduction at G = 143.7, busy P |
|---|---|---|---|---|
| wasm t=4, Linux, this box | 35.7 / 39.2 | 5.43 | 35.6 percent | 39.1 percent |
| wasm t=4, Windows, owner | 46.2 / 32.0 | 6.43 | 31.8 percent | 35.3 percent |
| WebGPU, Windows, owner | 17.8 / 23.2 | 8.49 | 26.1 percent | 29.4 percent |

At idle P the same rows give 33.8, 38.7 and 21.8 percent at G = 173.9. The ranges are 31.8 to 38.7 percent for browser
wasm and 21.8 to 26.1 percent for WebGPU. All of these are model output at nominal P (no memo hits). Using per-node P
(about 0.94 of P on average over the four 226 configs, section 4.1) lowers them by about 1 point. They depend on the
same formula that Table 2 shows is off by up to 23 percent in the Node data, in the other direction from the browser
inversion below (the model under-predicts the measured browser round wall), so read them as an order of magnitude.

**The Phase 198 prior is replaced in number and confirmed in direction.** The prior was about 18 percent at
P about 15 ms. With Phase 198's G (189.3 ms) the model at P = 15 ms does give 18.0 percent, so the arithmetic checks.
The measured WebGPU P (17.8 to 23.2 ms, 19 to 55 percent above 15 ms) and Node G give 21.8 to 26.1 percent. Direction
confirmed: WebGPU gains less than wasm, because P is far below `P*` and the `(P + G) / c` term binds.

**Sensitivity to browser G (crude inversion, model, low confidence).** The round legs' budget-bound positions run
127.3 ms per node on Linux wasm and 97.6 ms per node on Windows WebGPU (`middlegame`, 50 nodes, median of 3 rounds).
The round model at Node G predicts about 79 to 83 ms and 61 to 67 ms. Inverting `wall/node = P + G/4` gives an
implied browser G of about 350 ms (wasm) and 300 ms (WebGPU). That figure absorbs the root round, main-thread
work and apply costs, so it is an upper bound on G. At that G the model reduction is 21 to 23 percent for wasm and
14 to 18 percent for WebGPU. So the browser win is between about 14 and 39 percent depending on backend and on browser
G, and it sits close to the 15 percent line for WebGPU at the high end of G. D-04 is judged on the Node gate, so this
affects the owner's reading, not the verdict. The sizing of the 226 G inflation matters in the other direction here
(section 4.1): a lower true G raises the wasm and WebGPU estimates in the table above (39.1 and 29.4 percent at
G = 143.7) while it lowers the Node Maia-bound estimates (section 4.4).

**D-07 blocking point.** Continuous must not be slower than round on the WebGPU machine (ratio at most 1.03). The
model predicts a gain of 14 to 26 percent there, so a failure would be informative: it would mean the model is
missing a cost, for instance main-thread contention in the browser, which the Node gate cannot see.

### 4.4 Finite-N correction for the bot path (model)

The steady-state formula assumes a long search. A bot search that stops early has a ramp-up and a ramp-down: the root
round is a single expansion in both modes (section 2.5). A deterministic pipeline simulation (Appendix A: serial Maia
FIFO, `s` Stockfish workers, `c` slots, constant P and G, root grade `G/2` as an assumption, always-selectable tree)
runs the 16 stop-on node counts above, with the stop reason from the same TSV (round-1 finding R1A-5):

- **Early stop at node n.** Round mode dispatches a full round of `c` before it can apply and test any member
  (`mctsSearch.ts:664-666`, `:723-725`), waits on the barrier, and discards the rest at `:743`. So round mode pays for
  a full last round, `1 + c * ceil((n - 1) / c)` expansions capped at `maxNodes`. Continuous mode stops at the
  settlement of the n-th expansion.
- **Budget stop.** The last round is truncated to `maxNodes - nodesEvaluated` (`:666`), so it can run a single
  expansion alone. The first draft applied that truncation to every position, which understates round mode's time for
  early stops and so understates the reduction. "The last round can run a single expansion alone" is true for a
  budget stop only.

| Inputs | Modelled bot-path reduction (stop-on node mix, stop-reason aware) | First draft (truncated last round, lower bound) |
|---|---|---|
| Node: P = 83.3, G = 173.9 | 30.7 percent | 28.8 percent |
| wasm, this box: P = 39.2 (idle 35.7), G = 173.9 | 30.6 percent (29.1 percent) | 29.3 percent (27.7 percent) |
| WebGPU: P = 23.2 (idle 17.8), G = 173.9 | 22.3 percent (18.5 percent) | 21.2 percent (17.6 percent) |
| wasm, implied G = 350 | 19.7 percent | 18.7 percent |
| WebGPU, implied G = 300 | 15.0 percent | 14.2 percent |

**Validation against measurement (Node, stop-p4 proxy).** The 226 stop-on TSV gives a measured round wall of 55.4 s
over the 388 nodes. The stop-reason-aware model gives a round total of 52.7 s (-4.8 percent; the truncated variant
gives 51.3 s, -7.4 percent), so the model's round time is close to measurement on this node mix. The model's
continuous total is 36.5 s against a measured Maia busy time of 32.9 s, which is a hard floor for any serial Maia
loop, so the model's continuous time is consistent with that floor (ceiling `1 - 32.9 / 55.4 = 40.5` percent). The
simulation reduction relative to the measured round wall is `1 - 36.5 / 55.4 = 34.1` percent, but mixing a model
numerator with a measured denominator is not used as the estimate; the 30.7 percent figure compares model with model.

**Sensitivity to the inflated Node G (model).** At Node P and the same node mix, the bot-path reduction is 30.7
percent at G = 173.9, 27.2 at 140, 24.8 at 120, 22.2 at 100 and 19.4 at 80. The Node estimate falls as G falls, because
the Maia-bound continuous time stays at `P` while round time shrinks. G is an upper bound here (section 4.1), so
the Node bot-path estimate is 30.7 percent at the top of this range, and the range covers the plausible G inflation.

For fixed-length searches the same simulation gives 32.0 percent at 50 nodes and 33.9 percent at 400 nodes (Node P, G,
with a truncated last round, which is the correct shape for a budget stop). So the model expects roughly 20 to 31
percent on the Node bot path depending on how inflated G is, and, for the analysis path, the 21.5 (t400-p4) and 32.1
(t400-p2) ceilings of Table 2, against D-04's 15 percent bar. **These are model outputs. The measured interleaved wall
is the judge.** The model is a mean-throughput model and cannot see variance across a mixed-depth grade ladder (X-5).

### 4.5 What the sizing does not settle

- Browser G is not measured in isolation. The WebGPU leg's continuous half (Plan 227-12) measures wall directly.
- Node G is measured under main-thread Maia and is inflated by up to one Maia inference of bestmove-processing delay.
  Re-measuring G under worker Maia (the current harness) would fix that input; it was not done for this design. The
  sizing carries the inflation as a stated sensitivity (sections 4.2 to 4.4).
- The cross-search effects of section 3.6 (never-cleared hash, M5, the persistent Maia cache, no quiesce) are outside
  every number in section 4, which is a within-search model.
- The model ignores the stop rule's own effect on tree shape, which continuous mode changes (more breadth per
  unit time, M1).
- Higher `c` would raise the WebGPU win (`c* = 1 + G/P` is 8.5 at busy WebGPU P), but concurrency tuning is out of
  scope (D-10).

## 5. Disposition table

Dispositions are exactly one of: applies, moot under the relaxed contract (written "moot"), repaired. Each is
re-verified against the code at `399780bf8` (round-1 corrections to X-4, X-6, X-9, X-11, X-12, Y-1, Y-5 and Y-8 are
marked "round 1" in their rows). The first column is the Phase 198 ID (X: §9b, Y: §9d) or the Phase 227
finding (N). Line references into `mctsSearch.ts` are to the unchanged round loop and to the sketch in section 2.

| ID | 198 claim (one line) | Disposition | Reason with file:line |
|---|---|---|---|
| X-1 | Drain granularity is unspecified, so selection n sees a timing-dependent prefix. | moot | No commit window exists. The loop drains every settled result in arrival order (section 2.1). The invariant X-1 wanted is exactly the bit-identity that D-08 and D-11 drop. Round mode keeps input-order apply, `mctsSearch.ts:720-744`. |
| X-2 | Throughput formula inconsistent, and "WebGPU is a lower bound" inverted. | applies | Slot occupancy is `P + G`: `dispatchExpansion` awaits policy at `mctsSearch.ts:533` then grade at `mctsSearch.ts:586-591`. The corrected form and the non-monotonic reading are used in section 4; the measured WebGPU P (17.8 to 23.2 ms) replaces the 15 ms prior. |
| X-3 | Dead-end discovery mutates the tree at dispatch time, outside any commit. | moot | Accepted under D-11 (mechanism M2). `selectPath` closes the dead end (`mctsSearch.ts:377-380`), the fill bumps visits and propagates closure (`mctsSearch.ts:685-686`), may set `budgetExhausted` (`mctsSearch.ts:679-684`). Round mode already mutates during fill with same-round leaves pending. No induction claim is made. |
| X-4 | `c = 4` against a pool below 4 is live in production, not test-only. | applies | `FLAWCHESS_BOT_CONCURRENCY = 4` (`botBudget.ts:64`), `MOBILE_POOL_SIZE = 2` (`workerPoolState.ts:106`), `DESKTOP_POOL_MAX = 4` (`:100`), `computePoolSize` (`:509-513`). Round 1 (R1A-8, R1B-8): only the BOT runs `c` above the pool; the analysis path uses `c = computePoolSize()` (`useFlawChessEngine.ts:369`), so there `c` equals the pool. The bot on mobile, touch-pointer devices and low-core desktops runs `c = 4` on a pool below 4. X-4(c), the backlog that exists even at `c` equal to the pool: slots that are `stopping` or not ready shrink the idle set, and continuous mode makes `stopping` slots routine after every early stop (`workerPoolDispatch.ts:128-139`, `:303-308`). The app's root split then falls back to a plain `grade` whenever fewer than two slots are idle or anything is queued (`countIdleReadySlots`, `:345-352`, `k <= 1` at `:384-385`). The bot hides this behind the human's move time and the gate hides it with `whenIdle()`; it is a section 3.6 row, report-only. Gate: Node pool-2 configs (section 4.2). FIFO tie-break fixed (N-3). |
| X-5 | Ladder makes grade latency heterogeneous (d14 vs d10), so head-of-line stalls matter. | moot | The head-of-line stall exists only under commit-ordered release, which is not rebuilt: a worker frees when its `bestmove` arrives (`workerPoolDispatch.ts:146-167`) and the settled result is drained at once (section 2.10). The depth rung is chosen per leaf at `mctsSearch.ts:590` through `gradingDepthForTreeDepth` (`gradingLadder.ts:148`). The variance remains invisible to the mean model of section 4; the interleaved wall is the judge. |
| X-6 | The grade cache is an order-sensitive side channel; hit or miss becomes a settlement race. | moot | Accepted under D-11 (mechanism M3), stated in section 1.3. Read gate and merge write `workerPool.ts:278-305,316-354`; writes on `bestmove` (`workerPoolDispatch.ts:162-164`) and, for a root-split group, once on group success (`gradeRoot`, `:426`, round-2 finding R2B-8); root-split shards bypass the cache: the read gate is `workerPoolDispatch.ts:217-224` (`readCache !== false`) and the shard options are `readCache: false, writeCache: false` at `:403-404` (round 1, R1A-8: the first draft cited `:213-224` for `writeCache: false`). The gate has no grade cache (section 3.6). |
| X-7 | `selectPath` has three null returns, not two. | applies | Null sites at `mctsSearch.ts:368` (root guard), `:391` (root has no candidates), `:419` (defensive `!chosen`). With `inFlight > 0` the loop waits for a settlement, with `inFlight == 0` it returns. The loop wakes only on a settlement or an abort, so there is no busy spin. The defensive null behaves exactly as in round mode (`:669`), and is unreachable because `selectChild` returns a UCI from its own input (`:417-418`). Phase 198's throw is not adopted. |
| X-8 | Missing-wakeup hazard when a settlement lands with no waiter. | repaired | Section 2.7: settled queue, push before notify, single await, synchronous check and wake assignment in one run. Claim (e). Today's round loop has the same single-await shape (`mctsSearch.ts:723-725`); the new part is the explicit `wake` hand-off, tested by already-resolved providers (`maiaQueue.ts:297-298`, `workerPoolDispatch.ts:223-224`). Round 2 (R2B-2): an abort raised synchronously during a fill was not re-checked before the wait, so the sketch now guards the `await` with `!signal.aborted && !st.earlyStop` (section 2.7, test and mutation in section 2.12). |
| X-9 | A never-settling promise: continuous is not worse than round, and real providers settle. | applies (premise corrected) | Real providers settle, with one pre-existing exception (round 2, R2A-9 and R2B-4; Phase 198 §9c X-9 named it, `apply-order-design.md:1154`): the Maia host has only init timeouts and no analyze watchdog (`maiaWorkerHost.ts:84-92`, `:735`; `maiaQueue.ts:174-201` waits on `lease.analyze` indefinitely), so a wedged ONNX inference never settles. Without an abort both modes hang. With an abort, round mode still hangs and continuous returns. Everything else settles: the pool's grading watchdog and death paths resolve empty (`workerPoolWatchdog.ts:169,213`; `workerPoolLifecycle.ts:115,194,297,305,318,323`; round 1, R1A-8 and R1B-7: the first draft cited `workerPoolDispatch.ts:30,69`, an import and a timer arm) and the Maia queue resolves `{}` on a rejected lease and on a fatal worker (`maiaQueue.ts:198,214`) and, on abort, for a queued request (`:279-285`). Continuous is strictly better: an abort wakes a stuck loop (section 2.7), which `Promise.all` at `mctsSearch.ts:723-725` cannot. Round 1 (R1A-2, R1B-3): this is also the reason claim (c) is scoped to providers that resolve after an abort; a provider that rejects or hangs after an abort makes round mode throw or hang and continuous return, and that divergence is pinned by a test (section 2.4). |
| X-10 | WR-04 degenerate close under-dispatch claim does not hold. | applies | A degenerate settlement lowers `inFlight` without raising `applied`, which reopens a slot (section 2.3; `applyExpansion` at `mctsSearch.ts:440-449`, empty-candidate return `mctsSearch.ts:552-566`, 8XN-7 `mctsSearch.ts:614-623`). Provider calls can exceed `maxNodes` by the degenerate count, as today. The guard `applied + inFlight` leaves the window under-filled over the last `c - 1` nodes, as round's `nodesEvaluated + toExpand.length` does (`:666`). |
| X-11 | One grade per expansion; `G/c` assumes `pool >= c`, false on mobile. | applies | One `grade()` per expansion (`mctsSearch.ts:586-591`). The pool-below-`c` baseline is not the `c = 2` row, and it is not `P + ceil(c/pool) * G / c` either (round 1, R1A-4): that formula ignores that later slots' policies overlap earlier grades, and over-stated the t50-p2 round time by 33 percent (168.3 ms against a measured 131.2 ms per node, simulation 126.6). Section 4.1 now uses the pipeline simulation for `s < c`, the t50-p2 modelled reduction is 32.9 percent (not 49.5), still model only, and nothing is published for it; the Node pool-2 measurement is the evidence. |
| X-12 | At `c = 1` continuous must equal today's loop. | applies | Adopted as claim (c), section 2.4, against the retained round loop (`mctsSearch.ts:664-666,711-718,727-744`) as a live golden. Round 1 (R1B-4, R1A-8): the live golden is the post-extraction round loop (section 2.1 extracts `applyAndReport` and `discoverDeadEnd`), so it cannot catch a defect in a shared helper. X-12 is therefore not closed by the live golden alone: Plan 227-10 must also commit pre-extraction goldens (they are not committed today) and re-run the Plan 227-08 `--hash clear` parity check after the extraction with 0 diffs against `reports/data/continuous-dispatch-227/tripwire/parity-clear` (section 2.4). Claim (c) is scoped to providers that resolve after an abort, compared after quiescence. Model cross-check: reduction is exactly 0 at `c = 1` (section 4.1). |
| Y-1 | Browser grades are not bit-identical (warm hash), so the parity gate was blind to it. | applies | Split by half (round 2, R2A-10). The nondeterminism half is moot by contract: resolved by contract (226 D-05, SEED-130): the gate runs the warm-hash configuration (D-02). Plan 227-08 found the harness round mode now shares the property under worker Maia (section 1.4). Judged cells require `hash_mode = warm` (`engine_dispatch_227_verdict.py:536-537`). Round 1 (R1B-2): the first draft said warm "matches" the app, which is false. The app never clears the table (zero `ucinewgame` or `Clear Hash` hits in `frontend/src`); the gate's warm hash lasts one search, because every gate script sends `ucinewgame` before each position (`pool.resetAll()` calls `pool.newGameAll()`, `engine-dispatch-stop-rule.mjs:438`, `stockfish-pool.mjs:647-658`), and the D-15 calibration arms clear it on every grade (`stockfish-pool.mjs:452`, `calibration-providers.mjs:534`). So the gate sees only within-search warmth, cannot see M5 or the cross-search part of M4, and the contract resolves the nondeterminism, not the blindness. The blindness half applies as an accepted limit (the gate cannot see M5, which is present in both modes and amplified in continuous, or the cross-search part of M4), listed in section 3.6; a report-only cross-search variant is a possible follow-up. |
| Y-2 | "Queue order cannot affect output" contradicts the cache and warm-hash facts. | moot | No priorities are activated (`workerPoolDispatch.ts:259-260`), and this document makes no such claim: order can affect output through grade-cache timing and engine assignment (C5, M3, M4). FIFO tie-break at `workerPoolState.ts:457-475`. |
| Y-3 | Abort at the commit step applies one result after abort. | repaired | Section 2.6: the abort and early-stop check immediately precedes the single apply call site, plus an inner controller. Round mode's equivalent is `mctsSearch.ts:728`. Claim (d), with settle-after-abort and settle-after-early-stop tests. |
| Y-4 | The barrier is only half a barrier: intra-round cache hit or miss is already a race. | moot | Acknowledged (M3). Within one dispatch policy precedes grade serially (`mctsSearch.ts:533,586`), so a same-round grade read can already race a sibling's write. No ordering machinery is built. |
| Y-5 | X-5's mixture arithmetic does not reconcile with the measured G. | moot | X-5's head-of-line argument is moot, and this document does not use the 41/322 ms mixture. G is taken directly from 226's `grade_cpu_ms / grade_calls` (section 4.2; the column is defined at `engine-grading-depth-ab.mjs:329-335`). Round 1 (R1A-3): that G is measured under main-thread Maia and is inflated by bestmove-processing delay, and the model built on it was off by up to 23 percent against measured round wall. Section 4 now validates against the same TSVs' measured wall, uses per-node Maia time, and states the inflation as a sensitivity. |
| Y-6 | The refill guard stalls dispatch while the commit head is stuck. | moot | There is no commit head. A slot refills when its expansion settles: the fill guard is `inFlight + dispatched < concurrency` (section 2.1), the analog of the round guard at `mctsSearch.ts:664-666`. |
| Y-7 | A discriminated result inside `selectPath` is not achievable (no `inFlight`). | moot | The loop distinguishes the null causes by `inFlight` outside `selectPath` (section 2.1, X-7). `selectPath` is unchanged (`mctsSearch.ts:361-423`, signature takes no `inFlight`). |
| Y-8 | A `.catch` that prunes a subtree silently contradicts "fail loudly". | repaired | Section 2.8: no `.catch` swallowing. Rejection is captured as a value, thrown by the drain, and the `finally` cancels siblings. Matches `Promise.all` at `c = 1` (`mctsSearch.ts:723-725`) when no abort precedes the rejection. Round 1 (R1A-2): a rejection that settles after the loop returned is dropped on purpose, with the justification and the test in section 2.8; the app providers resolve empty and the Maia queue reports its one real failure to Sentry at source (`maiaQueue.ts:188`). |
| Y-9 | The base case "dispatches 1..c fire back to back" is false; the root guard allows one. | applies | `selectPath` returns null while the root is pending (`mctsSearch.ts:368`); section 2.5 states one dispatch until the root applies. The root grade is routed to `gradeRoot` (`:584`). |
| Y-10 | Phase 198's report text for the corrected model is stale. | moot | Closed-phase document. This design cites only the corrected model (`apply-order-design.md:272-453`, §3) and its own section 4. |
| Y-11 | A superseded R-5 disposition still says oversubscription is not shipped. | moot | This document states oversubscription is live (X-4 row, `workerPoolState.ts:106,509-513`, and section 4.2), and relies on no R-5 disposition. |
| Y-12 | "The truth is the reverse" overstates: the reduction is non-monotonic in `P`. | applies | The overstated wording is at `apply-order-design.md:370-373`. The wording in section 4.1 is "non-monotonic in P, peak at `P = G/(c-1)`", with peak value `(c-1)/(2c-1)`. Round 2 (R2B-1): the section 3.6 Maia-cache row and the section 4.1 `(P + G) / c` sentence contradicted this (they said the reduction falls with P and called the gate's figures an upper estimate). Both are repaired to the non-monotonic reading, so the disposition now holds throughout the document. |
| Y-13 | Recompute hygiene; the c = 8 and c = 16 rows assume a pool no configuration provides. | applies | Every derived number is labelled model (section 4); no `c > 4` row appears, because `DESKTOP_POOL_MAX = 4` (`workerPoolState.ts:100`). |
| Y-14 | `gradingLadder.ts:84-85` documents the grade-cache key wrongly. | repaired | The comment now states the key `${fen}\|${gradingDepth}` (`gradingLadder.ts:84-86`, Plan 227-02 commit `0edd4a7c6`), matching `workerPool.ts:274-276`. |
| N-1 | Harness Maia on the Node main thread starves Stockfish I/O and misorders arrival. | repaired | Plan 227-01: worker-thread Maia (`node-engine-providers.mjs:102-125`), lag 6.3 to 15.4 ms against 355 to 363 ms. Section 3.1. Side effect: warm-hash round mode is now timing-dependent in the harness (section 1.4), accepted by the owner. |
| N-2 | Harness Stockfish pools ignore the abort signal. | repaired | Plans 227-01 and 227-04: `withEngine` abort (`stockfish-pool.mjs:283-320`), grade and gradeRoot (`:521-541,564-588`), `whenIdle` (`:591-596`, Stockfish only), gate-script wrappers. Section 3.2. Round 1 (R1A-1, R1B-1): the harness Maia FIFO also ignored abort; fixed in `399780bf8` with `whenMaiaIdle()` (section 3.2, N-2b). |
| N-3 | The app pool breaks ties by candidate UCI, not arrival, risking starvation at pool below `c`. | repaired | Plan 227-02 (D-19): FIFO among equals, `workerPoolState.ts:450-475`, with a mutation-checked test. Section 3.3. |
| N-4 | Grade-elapsed normalization is biased toward continuous mode. | repaired | D-17: judged metric is interleaved raw wall normalized by the external probe (`engine-speed-probe.mjs`, `engine_interleave_227.py`); grade-elapsed normalization is report-only. Constants at `engine_dispatch_227_verdict.py:126-142`, load gate at `engine_interleave_227.py:95`. Section 3.4. |

## 6. Reviewer briefing

Claims to attack. Each is stated here verbatim, and each should be broken, if it can be, with `file:line` evidence.

- (a) blocks scoped per fill are exact
- (b) applied + inFlight <= maxNodes and inFlight == 0 at budget exhaustion
- (c) c = 1 byte-identity
- (d) no result is ever applied after abort or early stop
- (e) no missing wakeup
- (f) the harness measures the same algorithm with app-faithful timing

Where each is argued: (a) section 2.2, (b) section 2.3 (where "budget exhaustion" means `nodesEvaluated === maxNodes`,
not the `budgetExhausted` flag, which a `maxPlies` cut also sets), (c) section 2.4 with the definition of
byte-identical and its scope limits (providers that resolve after an abort, call lists after quiescence), (d)
section 2.6, (e) section 2.7, (f) section 3, whose scope is stated in section 3.6.

Also check that every disposition in section 5 is correct against the current code and against
`reports/continuous-dispatch/apply-order-design.md` §9b and §9d, and that the sizing in section 4 follows from its
named inputs.

## 7. Review dispositions

Round 1 (two independent reviewers, raw outputs `reviews/r1-a.md` and `reviews/r1-b.md`; findings numbered in their
listed order). All 17 findings were verified against the code before being dispositioned; none was rejected as wrong. One
sub-request inside R1A-2 (log or capture late rejections) is declined with a justification, stated in its row.

| Finding | Severity | Claim | Disposition |
|---|---|---|---|
| R1A-1 | High | (f), §2.6 consequence 1 | repaired: the harness Maia FIFO dropped the search signal (`calibration-providers.mjs` `makeNodeProviders`; app counterpart `maiaQueue.ts:279-288`). Fixed in tooling commit `399780bf8`: the FIFO forwards the signal, drops queued requests and resolves `{}`, the in-flight inference completes, `whenMaiaIdle()` is awaited before `pool.whenIdle()` in every gate script, check (f) added and mutation-tested. Design text: section 2.6 consequence 1 (the "up to one P" statement holds for the app; the harness matches queue behavior and does not charge the in-flight remainder), section 3.2 N-2b, section 3.5 Pitfall 4, section 3.6 "Maia queue on abort" row, section 5 N-2 row. Parity re-run on `399780bf8`: see the tooling re-verification note below this table. |
| R1A-2 | Medium | (c), §2.8, Y-8 | repaired: claim (c) is scoped to providers that resolve after an abort, with call lists compared after quiescence (section 2.4 scope limits 1 and 2, citing `maiaQueue.ts:279-285,301`, `workerPoolDispatch.ts:211,286-312,377,415-420`, `stockfish-pool.mjs:293,564-565`). The c = 1 external-abort-in-flight fixture and the late-rejection fixture are added to sections 2.4 and 2.12. The request to capture or log late rejections is declined with a justification (section 2.8, "Late rejections, disposition": cancelled work is unwanted, app providers resolve empty, the one real Maia failure already reaches Sentry at `maiaQueue.ts:188`, `mctsSearch.ts` has no Sentry or console use). Section 5 X-9 and Y-8 rows updated. |
| R1A-3 | Medium | §4.2 to §4.4 sizing, Y-5 | repaired: the model was validated against measured round wall from the same TSVs, recomputed here and reproducing the reviewer (t50-p4 120.8, t400-p4 98.4, t400-p2 110.7, t50-p2 131.2 ms per node). New section 4.1 input corrections (per-node Maia time with memo hits, G inflation under main-thread Maia with the cited `engine-grading-depth-ab.mjs:329-335` and `engine-dispatch-stop-rule.mjs:340-350`), section 4.2 Table 2 (model error, ceilings 32.3, 21.5, 32.1 and 33.9 percent, t400-p4 ceiling 21.5 as the reviewer computed), the withdrawn "about 30 percent on the Node analysis path", section 4.3 caveats, section 4.4 validation against the 226 stop-on TSV (model round 52.7 s against measured 55.4 s) and a G sensitivity. All derived numbers are labelled model output. Section 5 Y-5 row updated. |
| R1A-4 | Low | X-11, §4.2 t50-p2 row | repaired: the `P + ceil(c/s) G / c` formula is dropped for `s < c` (section 4.1) and replaced by the pipeline simulation (Appendix A `round_ms`); the t50-p2 round time is 126.6 ms per node against 131.2 measured, and the modelled reduction is 32.9 percent, not 49.5 (section 4.2 Table 1). Section 5 X-11 row updated. Reviewer's 126.5 and 32 percent reproduce. |
| R1A-5 | Low | §4.4 last-round wording and simulation | repaired: section 4.4 now simulates a full last round for early stops and a truncated one for budget stops (11 and 5 of the 16 positions), states the wording correctly ("a single expansion alone" is true for a budget stop only), and lists the first draft figures as a lower bound (Node 28.8 to 30.7 percent). Appendix A gains a `full_last` argument and the stop-reason-aware driver. |
| R1A-6 | Low | (d), (e) reasoning text | repaired: sections 2.6 and 2.7 no longer claim an abort is always delivered between synchronous runs. `abort()` runs its listeners synchronously (`deadlineSearch.ts:97-103` inside `applyAndReport`, then `onOuterAbort`, then the pool and Maia listeners at `workerPoolDispatch.ts:286-312` and `maiaQueue.ts:279-285`). The conclusions are re-derived without that premise (`wake` is null mid-drain, the next check reads `signal.aborted`, settlements arrive as microtasks). The timer path (`deadlineSearch.ts:118-121`) is stated. Timer-driven abort test added to sections 2.7 and 2.12. |
| R1A-7 | Low | (f), §3.6 missing rows | repaired: section 3.6 gains the "Maia policy cache across searches" row (app cache persists, `maiaQueue.ts:12-15,297-298`; gates reset the memo per position; direction: lower app P shrinks the win) and the "No quiesce between searches" row (stopping slots reduce the next search's root fan-out, `workerPoolDispatch.ts:345-352,384-385`). Section 4.5 notes the section 4 model excludes cross-search effects. |
| R1A-8 | Low | citations and wording | repaired: every item verified against the code and fixed. Section 2.11 path is `scripts/calibration-harness.mjs:405-406`; X-6 cites the read gate `workerPoolDispatch.ts:217-224` and the shard options `:403-404`; X-9 cites `workerPoolWatchdog.ts:169,213` and `workerPoolLifecycle.ts:115,194,297,305,318,323`; X-4 now says only the bot runs `c` above the pool (`useFlawChessEngine.ts:369`); section 1.5 says the SD ratio is 0.58 and the variance ratio about 0.33 (0.4/1.2); C1 no longer says "verbatim" (section 1.3, section 2.1) and a post-extraction parity check is an obligation (section 2.4). |
| R1B-1 | Medium | (f) | repaired: same defect and same repair as R1A-1 (tooling commit `399780bf8`, sections 2.6, 3.2 N-2b, 3.5, 3.6). The instrumentation side effect (live in-flight gauge zeroed, later peaks one low) is fixed in the same commit and described in section 3.2. R1B-1's magnitude (1.5 to 2.5 points of the win) is recorded as a model estimate in section 2.6. Parity re-run on `399780bf8`: see the tooling re-verification note below this table. |
| R1B-2 | Medium | (f), Y-1 | repaired: section 3.6 hash row corrected (the harness sends `ucinewgame` before every position, `stockfish-pool.mjs:647-658`; the app never clears, zero hits in `frontend/src`); a new row states the D-15 calibration arms run with `clearHash = true` (`calibration-harness.mjs:394`, `stockfish-pool.mjs:452`, `calibration-providers.mjs:534`). Sections 1.3 (M4, M5) and 3.6 state that the gate cannot measure M5 or the cross-search part of M4. Section 5 Y-1 row corrected. No tooling added; a report-only cross-search variant is listed as a possible follow-up. |
| R1B-3 | Medium | (c) | repaired: same scope limits and fixtures as R1A-2 (section 2.4, section 2.12, section 5 X-9). The reviewer's three-way divergence (late rejection, never-settling provider, call lists at return) is documented and pinned by the c = 1 abort-in-flight and late-rejection fixtures. |
| R1B-4 | Low to medium | (c), X-12, C1 | repaired: C1 and section 2.1 reworded (helper extraction and the locals moved to a counters object are a refactor, not verbatim). Section 2.4 makes two Plan 227-10 obligations: commit pre-extraction goldens before the extraction (not committed today), and re-run the Plan 227-08 `--hash clear` parity check after the extraction with 0 differing rows against `reports/data/continuous-dispatch-227/tripwire/parity-clear` (those TSVs are committed, pre-extraction, real-provider goldens). Section 2.12 row added; section 5 X-12 row updated. |
| R1B-5 | Low | §2.6 deadline path | repaired: section 2.6 "Deadline path" now separates the armed-cut case (abort from `onSnapshot` at the first snapshot crossing the floor) from the common case (the timer at `deadlineSearch.ts:118-121` aborts directly while the loop awaits, and the abort wake handles it). Timer-driven abort test added to sections 2.7 and 2.12. |
| R1B-6 | Low | §2.6 in-flight state | repaired: section 2.6 gains "A fourth in-flight state: the policy settles after the stop", with the code path (no abort check between `mctsSearch.ts:533` and `:586`; pools return empty for an aborted signal at `workerPoolDispatch.ts:211,377` and `stockfish-pool.mjs:293,564-565`) and the non-abort-aware chart join (`maiaQueue.ts:311-312`). Test added to section 2.12. |
| R1B-7 | Low | X-9 citation | repaired: section 5 X-9 row now cites `workerPoolWatchdog.ts:169,213` and `workerPoolLifecycle.ts:115,194,297,305,318,323`, verified against the files; the first draft's `workerPoolDispatch.ts:30,69` is an import and a timer arm. |
| R1B-8 | Low | X-4(c) | repaired: section 5 X-4 row now states X-4(c) (stopping and not-ready slots create a backlog even at `c` equal to the pool; routine after every continuous early stop; root split falls back to plain `grade`, `workerPoolDispatch.ts:128-139,303-308,345-352,384-385`). The same effect is a section 3.6 row. |
| R1B-9 | Low | §2.11 reword list | repaired: section 2.11 gains `mctsSearch.ts:113`, `:126-136`, `:345-360`, `:575-583`, `:602-603`, `maiaQueue.ts:259-263`, and the tooling comments at `engine-dispatch-stop-rule.mjs:46-48` and the `whenIdle` docs (`stockfish-pool.mjs:591-595`, `engine-dispatch-stop-rule.mjs:439`); the path error is fixed to `scripts/calibration-harness.mjs:405-406`; C2 cites `useFlawChessEngine.ts:369`. Every location was read and the claim confirmed. The tooling comment edits are not made in this step (no tooling edits allowed here) and are assigned to Plan 227-09 Task 3 or Plan 227-10. |

**Tooling re-verification (recorded by the orchestrator, not by this repair step).** Clear-hash parity re-run on
`399780bf8` (`--hash clear`, worker Maia against the committed `tripwire/parity-clear/main` data, 60-row fixture, stop
off and on), run 2026-10-02 11:36-11:43 UTC: **TRIPWIRE PASS, 0 of 60 rows differ in each stop mode** (verdict twin
`tripwire --mq-dir <rerun>/worker --baseline-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/main`,
exit 0). The FIFO abort fix leaves round-mode content unchanged.

Round 2 (two fresh independent reviewers, same brief, raw outputs `reviews/r2-a.md` and `reviews/r2-b.md`; both
returned SOUND with no high-severity finding, and findings are numbered in their listed order; R2B-8 is the
reviewer's closing "minor citation note"). All 20 items were verified against the code before being dispositioned;
none was rejected. The verdict is SOUND for both, so the repairs below were applied without a third review round,
which is the plan's closing rule (both SOUND in the same round after every finding is dispositioned and repaired).
Every repair is text in this document, except two items that are flagged for later plans and not fixed here (R2B-5's
`requestPolicy` guard for Plan 227-10, and the harness memo-before-FIFO check, which is report-only).

| Finding | Severity | Claim | Disposition |
|---|---|---|---|
| R2A-1 | Medium | (f), C5 M5, section 3.6 hash row | repaired: verified, round mode's pool also stops in-flight grades on every abort (`workerPoolDispatch.ts:297-308`), via the bot deadline cut (`deadlineSearch.ts:91-121`) and every analysis position change (`useFlawChessEngine.ts:95-96,351-352,396`). C5 M5 now says cancellation on abort exists in both modes, cancellation on early stop is continuous-only, and the gate is blind to an effect present in both arms and amplified in continuous. Section 3.6 hash row reworded to match. |
| R2A-2 | Low to medium | (f), section 3.6 "No quiesce" row | repaired: verified, the analysis path aborts and restarts on every `debouncedFen` or `extraRootMoves` change. The row now says stopping slots and a reduced root fan-out are routine there in both modes. |
| R2A-3 | Low | (f), undisclosed harness timing difference | repaired: verified at `calibration-providers.mjs:377-399` and `:231-232` against `maiaQueue.ts:297-298`. New section 3.6 row "Maia memo hits in the FIFO". The tooling change (check the memo before enqueueing) is declined for now: it affects both arms equally, only on the 2 to 10 percent of nodes that are memo hits, and the tooling is frozen at `399780bf8` for the gate. Report-only. |
| R2A-4 | Low | (f), section 3.6 Maia-cache row, section 4.1 wording | repaired: verified by arithmetic (Node t50-p4 sits at P = 83.3 above `P*` = 58.0; model values 34.3, 38.3, 42.9, 35.9 and 30.6 percent at P = 83.3, 70, 58, 40 and 30). Section 4.1 now says the `(P + G) / c` reduction rises with P and gives the Maia-bound form; the section 3.6 row is non-monotonic and the "upper estimate" claim is dropped. |
| R2A-5 | Low | (f), Maia thread-count contention | repaired: verified, `node-engine-providers.mjs:120` sets `numThreads = 1` with a stale comment. Contention is added to the section 3.6 first row and the comment to the section 2.11 list. |
| R2A-6 | Low | (d), section 2.8 | repaired: verified, the sketch threw on a rejected item before the abort and stop test. One rule chosen: test abort and early stop first, so every post-stop rejection is dropped. Sketch, section 2.8 (rule, claim (c) consistency at `c = 1`, the accepted `c > 1` difference), section 2.4 `c = 1` bullet and a section 2.12 row with its mutation. |
| R2A-7 | Low | (b) wording | repaired: verified, the WR-05 `maxPlies` cut sets `budgetExhausted` with expansions in flight (`mctsSearch.ts:679-684`). Section 2.3, section 6 and the section 2.12 test now key on `nodesEvaluated === maxNodes`. |
| R2A-8 | Low | section 2.11 reword list | repaired: added `mctsSearch.ts:30-37`, `:298-309`, `:491-499`, `:514-516` and `:735`, plus `node-engine-providers.mjs:120`. |
| R2A-9 | Low | section 5 X-9 | repaired: verified, no analyze watchdog in `maiaWorkerHost.ts` (init timeouts only, `:84-92`, `:735`). X-9 row and section 2.4 scope limit 1 now state the wedged-inference residual, and that an abort frees only the continuous loop. |
| R2A-10 | Low | section 5 Y-1 category | repaired: Y-1 is now "applies", split by half in its reason (nondeterminism moot by contract, blindness an accepted limit). |
| R2A-11 | Low | section 2.8 wording | repaired: the "no partial snapshot" sentence is replaced by the analysis hook's actual behavior (`useFlawChessEngine.ts:396-414`, both modes). |
| R2A-12 | Low | citations and scope | repaired: the hash row now cites `resetAll` at `engine-dispatch-stop-rule.mjs:438` and `engine-grading-depth-ab.mjs:570` calling `pool.newGameAll()` (`stockfish-pool.mjs:647-658`), also fixed in the Y-1 row. Section 3.2 states `engine-search-trace.mjs` is an unjudged diagnostic without `maiaFifo` or `gradeRoot` (`:580`), excluded from "every gate arm". |
| R2B-1 | Medium | (f), section 3.6, section 4.1, Y-12 | repaired: same defect and repair as R2A-4. The Y-12 row now records that the document is consistent with it. |
| R2B-2 | Low | (e), section 2.7, X-8 | repaired: verified, a synchronous abort inside a provider's synchronous prefix during a fill lands while `wake` is null and is not re-checked before the wait. The sketch guards the `await` with `!signal.aborted && !st.earlyStop`. Section 2.7, the X-8 row and a section 2.12 row (fixture: `policy()` aborts synchronously, `grade` never settles; mutation: drop the guard) are updated. Not reachable by the shipped providers, stated as such. |
| R2B-3 | Low | C5 M5, section 3.6 hash row | repaired: same as R2A-1. |
| R2B-4 | Low | section 5 X-9, section 2.4 scope limit 1 | repaired: same as R2A-9. |
| R2B-5 | Low | section 2.6 "fourth in-flight state" | repaired: verified, the `inFlight.catch(() => requestPolicy(...))` fallback (`maiaQueue.ts:311-312`) has no aborted-signal check in `requestPolicy` (`:265-292`). The reject branch is documented. The one-line `requestPolicy` guard is flagged for Plan 227-10 (section 2.11) and not made here. |
| R2B-6 | Low | (f), two missing section 3.6 rows | repaired: both rows added (memo hits queue in the harness FIFO; other Maia traffic on /analysis, `maiaWorkerHost.ts:274-292`, `maiaQueue.ts:24-37`). |
| R2B-7 | Low | (b) test obligation | repaired: same as R2A-7. |
| R2B-8 | Minor | section 5 X-6 citation | repaired: the X-6 row now names the second cache write site, the `gradeRoot` group success write (`workerPoolDispatch.ts:426`). |
| R3A-1 | Low | (d)/(e) §2.12 timer test | repaired: assigned to Plan 227-10 (forwarded during its execution): the timer-driven deadline fixture's grade records the abort but settles only after a later macrotask, and the test asserts the search resolves before any provider settles, so dropping `notify()` from `onOuterAbort` fails it. |
| R3A-2 | Low | X-9 category | repaired: section 5 X-9 disposition changed from moot to applies (premise corrected: the wedged-ONNX path is real). |
| R3A-3 | Low | C5 M5 wording | repaired: C5 M5 now says timer-driven deadline cuts (`deadlineSearch.ts:118-120`) and analysis restarts; an armed cut fires after the barrier. |
| R3A-4 | Low | citation drift | repaired: closing note below names the post-review commits that moved `scripts/` lines and completed listed items. |
| R3A-5 | Low | §2.11 list | repaired: assigned to Plan 227-10 (forwarded): `botBudget.ts:63`, `types.ts:66`, `mctsSearch.ts:55-65`. |
| R3B-1 | Low | (d)/(e) fill guard | repaired: assigned to Plan 227-10 (forwarded): the fill guard gains `!signal.aborted`, so an abort raised in a provider's synchronous prefix stops the rest of the fill; the R2B-2 fixture asserts no further `policy()` calls; c = 1 identity unaffected. |
| R3B-2 | Low | (f) §3.6 | repaired: section 3.6 Maia-queue row states the harness abort-before-memo order vs the app's cache-first order. |
| R3B-3 | Low | (f) §2.8 | repaired: section 3.6 Maia-queue row states that a harness engine rejection drained after a stop is dropped silently in continuous mode. |
| R3B-4 | Low | citation drift | repaired: same closing note as R3A-4. |
| R3B-5 | Low | §2.11 list | repaired: assigned to Plan 227-10 (forwarded): `mctsSearch.ts:362-367`, `types.ts:119-121`. |
| R3B-6 | Low | C4.1 wording | repaired: C4.1 now says behavior-identical, proven by pre-extraction goldens and the clear-hash parity re-run. |
| R3B-7 | Low | X-7 wording | repaired: X-7 row now says the loop wakes on a settlement or an abort. |
| R3B-8 | Nit | (b) precondition | repaired: assigned to Plan 227-10 (forwarded): a code comment states `maxNodes` is a positive integer. |

## Appendix A. Sizing recipe (reproducible in minutes)

Inputs are the committed TSVs and JSON named in section 4. Both functions are deterministic.

```python
import heapq
import math

def steady(P, G, c, s):
    """Closed form, valid for s >= c only. For s < c use round_ms (the old ceil form was wrong, R1A-4)."""
    cont = max(P, G / s, (P + G) / c)
    rnd = P + G / c
    return cont, rnd, 1 - cont / rnd

def round_ms(N, P, G, c, s, groot, full_last=False):
    """Round mode: root (policy, then the split root grade), then rounds of min(c, remaining) expansions.
    Policies queue serially in the Maia FIFO, each grade takes the first free engine, barrier at the last grade.
    full_last=True makes every round dispatch c expansions (an early stop dispatches a full round before it can
    apply any member); `done` still advances by the truncated count, so N is the number to be applied."""
    t = P + groot
    done = 1
    while done < N:
        k = min(c, N - done)
        maia_free, finish, engines = t, t, [t] * s
        for _ in range(c if full_last else k):
            maia_free += P
            j = min(range(s), key=lambda e: engines[e])
            engines[j] = max(maia_free, engines[j]) + G
            finish = max(finish, engines[j])
        t, done = finish, done + k
    return t

def continuous_ms(N, P, G, c, s, groot):
    """Continuous mode: after the root, c expansions are dispatched at once. Each settled grade refills one slot:
    its policy queues behind the Maia server and its grade takes the first free engine."""
    t0 = P + groot
    maia_free, engines, inflight, dispatched = t0, [t0] * s, [], 1

    def dispatch(now):
        nonlocal maia_free, dispatched
        maia_free = max(now, maia_free) + P
        j = min(range(s), key=lambda e: engines[e])
        engines[j] = max(maia_free, engines[j]) + G
        heapq.heappush(inflight, engines[j])
        dispatched += 1

    while dispatched < N and len(inflight) < c:
        dispatch(t0)
    last = t0
    while inflight:
        last = heapq.heappop(inflight)
        if dispatched < N:
            dispatch(last)
    return last
```

Stop-reason-aware driver used by section 4.4 (the stop reason and node count of each row come from the 226 stop-on
TSV, columns `stop_reason` and `nodes_evaluated_at_stop`):

```python
def bot_path_reduction(rows, P, G, c=4, s=4):
    groot = G / 2
    rnd = cont = 0.0
    for stop_reason, n in rows:
        # An early stop dispatched a full last round; a budget stop was truncated at maxNodes (50).
        dispatched = min(50, 1 + c * math.ceil((n - 1) / c)) if stop_reason == 'early-stop' else n
        rnd += round_ms(dispatched, P, G, c, s, groot)
        cont += continuous_ms(n, P, G, c, s, groot)
    return rnd, cont, 1 - cont / rnd
```

Table 2 of section 4.2 is not a simulation. Per config: `Pn = sum(maia_cpu_ms) / sum(nodes_evaluated)`,
`Gn = sum(grade_cpu_ms) / sum(nodes_evaluated)`, `W = sum(wall_ms) / sum(nodes_evaluated)` over the 16 `ladder` rows,
`floor = max(Pn, Gn / s, (Pn + Gn) / c)` and `ceiling = 1 - floor / W`.

Section 4.4 uses `groot = G / 2` (assumption: the root split makes the root grade about half a grade), `c = s = 4`,
and the 16 stop-on node counts listed in section 4.2. This script is not committed: the reviewed design must not
depend on a script that the accept rule does not pin, and the section 4.4 figures are corroborating context. Sections
4.2 and 4.3 carry the required model.

**Round 3 (confirmation, 2026-10-02).** Two fresh reviewers with the identical brief, at code commit `9f0b6be78`,
because two round-2 repairs changed the loop sketch. Both returned SOUND with low findings only (rows R3A and R3B
above; raw outputs `reviews/r3-a.md`, `reviews/r3-b.md`). Note on citations: `scripts/` line numbers in this document
are pinned to `399780bf8`; commits `012856e92` (twin round-repeat relaxation, which already replaced
`_check_round_determinism`) and `dcba1ba14` (harness comment rewording, already done) moved some of them afterwards.

REVIEW-A: SOUND (round 2)
REVIEW-B: SOUND (round 2)
REVIEW-A: SOUND (round 3)
REVIEW-B: SOUND (round 3)
