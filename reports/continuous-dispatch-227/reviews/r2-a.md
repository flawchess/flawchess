## Verdict: SOUND (no high-severity findings)

I checked `reports/continuous-dispatch-227/design.md` against the code at HEAD `de86e31ec`. The design pins its references to `399780bf8`, and no `frontend/` or `scripts/` file differs between the two. I could not break claims (a) through (e). Claim (f) holds as scoped, but its stated limits contain factual errors (findings 1 to 5). The §5 dispositions are correct apart from two category or overclaim nits (9, 10). The Table 1 and Table 2 inputs and the §4.4 stop-on mix reproduce exactly from the 226 TSVs.

### What held up
- **(a) Per-fill blocks are exact.** Lemma 1's mutation list is complete. `isBlocked` is only read and written at `mctsSearch.ts:385,403,708`. `isPending` is only cleared at `:446,477`. `dispatchExpansion`'s synchronous prefix does not touch the tree. Nothing makes a pending or closed child selectable again within a fill.
- **(b) Budget invariant.** The `A + F <= maxNodes` invariant holds, and so does the `F_before <= 1` argument. The only caveat is wording (finding 7).
- **(c) `c = 1` byte-identity.** The "no block at c=1" step holds. Even an expansion whose candidates are all illegal ends up childless, and `allChildrenClosed` is vacuously true for a childless node (`:229-235`), so that node gets closed and propagated. Every other close route also propagates. Exits, the guards, and degenerate, 8XN-7 and onSnapshot-abort handling all match the round loop.
- **(d) No apply after abort or stop.** The single check-then-apply site holds even for a synchronous abort from inside `onSnapshot`. The pools return empty for an already-aborted signal before enqueueing (`workerPoolDispatch.ts:211,377`; `stockfish-pool.mjs:293,565`).
- **(e) No missing wakeup.** `wake` is assigned synchronously, settlements always push before notifying, and `wake` is null during a drain.
- **Harness wiring.** `assertDispatchModeLive` runs before engine bring-up in all five scripts. `whenMaiaIdle` and `whenIdle` sit at the cited lines.

### Findings

1. **Medium, breaks C5 M5 and the §3.6 hash row (f).** The doc says partial work left in the hash by cancelled grades "exists only in continuous mode". That is false. Round mode cancels in-flight grades on every abort, because the search signal reaches the pool and it sends `stop` (`workerPoolDispatch.ts:297-308`). Two such aborts are routine:
   - bot deadline cuts (`deadlineSearch.ts:91-121`);
   - every analysis position change (`useFlawChessEngine.ts:95-96,351,396`).

   Only cancellation on early stop is continuous-only. **Repair:** restate M5 as "cancellation on early stop (bot) is continuous-only; cancellation on abort exists in both modes", and rephrase "gate blind to a continuous-only effect" to match.

2. **Low to medium, (f) §3.6 "No quiesce" row.** It says the analysis path "stops only on user cancel". In fact it aborts and restarts on every `debouncedFen` or `extraRootMoves` change (`useFlawChessEngine.ts:95-96,351,396`), so stopping slots and reduced root fan-out are routine in both modes. **Repair:** correct the row.

3. **Low, (f) undisclosed timing difference.** In the harness, a Maia memo hit still queues in the serial FIFO. `maiaFifoPolicy` enqueues everything (`calibration-providers.mjs:377-399`), and the memo is only consulted once the request is dispatched (`:231-232` via `nodePolicy` `:442`). In the app, a cache hit bypasses the queue entirely (`maiaQueue.ts:297-298`). With the FIFO binding on pool-4, a memo-hit expansion waits behind up to c-1 inferences in the harness only. This affects both arms and the 2 to 10 percent of nodes that are memo hits (0.90 to 0.98 inferences per node). **Repair:** add a §3.6 row, or make the FIFO check the memo before enqueueing (tooling change).

4. **Low, (f) §3.6 Maia-cache row and §4.1 wording.**
   - The conclusion "the gate's Maia-bound figures are an upper estimate for the app" does not follow. In the Maia-bound regime the reduction is `(G/c)/(P+G/c)`, which rises as P falls until `P* = G/(c-1)`. Node t50-p4 sits at P=83.3, above P*=58.0. It only falls below P*, which is where the browser P (about 39 ms) already sits.
   - §4.1 says `(c-1)P/(cP+G)` "falls with P". It is increasing in P (it falls as P falls).
   - **Repair:** scope the "upper estimate" claim to the §4.3 browser figures and fix the wording.

5. **Low, (f) Maia thread-count contention not listed.** Harness Maia runs `ort.env.wasm.numThreads = 1` (`node-engine-providers.mjs:120`). Its comment there ("matches the browser worker's no-COOP/COEP posture") is stale, since §3.6 itself records browser wasm at t=4. On this 16-core box, the gate sees almost no Maia-vs-Stockfish CPU contention. Continuous mode, with more overlap, is more exposed to that contention on 4 to 8 core devices. The P row records only speed. **Repair:** add contention to §3.6 (the busy-P legs cover it only partly) and list the stale comment in §2.11.

6. **Low, (d) and §2.8 inconsistency.** The drain throws on a `rejected` item before checking abort or early stop (sketch lines 177-178). So if a rejection is already queued when an earlier item in the same drain fires the stop rule (or aborts via `onSnapshot`), the search throws. One that arrives a microtask later is silently dropped. This contradicts §2.8's own reason (1): "failing a search that already completed correctly would be the wrong outcome". It is not worse than round mode, where `Promise.all` rejects the whole round. **Repair:** either check stop and abort first and drop post-stop rejections consistently, or state the asymmetry; add a §2.12 test either way.

7. **Low, (b) wording.** "inFlight == 0 at budget exhaustion" holds only for maxNodes exhaustion. A WR-05 maxPlies cut sets `budgetExhausted` (`mctsSearch.ts:679-684`) while expansions are in flight, and a later abort returns `stopReason: 'budget'` with `inFlight > 0`. **Repair:** the §2.12 test should assert at `nodesEvaluated === maxNodes`, not on `stopReason`.

8. **Low, §2.11 reword list incomplete.** Comments that become false in continuous mode and are missing from the list:
   - `mctsSearch.ts:298-309` (stop rule "evaluated ... in the canonical apply-order loop");
   - `:491-499` ("same-round re-pick", "determinism per concurrency level");
   - `:514-516` ("`applyExpansion` performs all mutation once every concurrent dispatch has resolved");
   - `:30-37` (header: "selected synchronously within one round", blocked "for the rest of the round");
   - `node-engine-providers.mjs:120`.

9. **Low, §5 X-9.** "Real providers settle" overclaims. The Maia host has no analyze watchdog (only init timeouts, `maiaWorkerHost.ts:84-92`), so a wedged ONNX inference never settles. Phase 198 §9c X-9 named exactly this residual. **Repair:** restate it; continuous mode is still strictly better here, because an abort wakes the loop.

10. **Low, §5 Y-1 category.** The nondeterminism half is moot under D-11. The blindness half (the gate cannot see M5 or the cross-search part of M4) is an open accepted limit, not moot. **Repair:** label it "applies (accepted limit)" or split the row.

11. **Low, §2.8 wording.** "Callers ... use no partial snapshot" is false for analysis. `handleSnapshot` commits snapshots as they arrive, and the `.catch` leaves them displayed (`useFlawChessEngine.ts:396-414`). This is true in both modes.

12. **Low, citations and scope.**
    - The §3.6 hash row cites `stockfish-pool.mjs:647-658` as `pool.resetAll()`. That range is `newGameAll`. `resetAll` is defined in `createGradePool` at `engine-dispatch-stop-rule.mjs:438` and `engine-grading-depth-ab.mjs:570`.
    - §3.2 counts `engine-search-trace.mjs` among the gate scripts, but it builds providers without `maiaFifo` or `gradeRoot` (`:580`). Pitfall 4's "every gate arm" should explicitly exclude this unjudged script.

### §5 spot-checks that passed
- X-7 null sites at `:368,391,419`, with `selectChild` never returning a missing UCI (`select.ts:114-139`).
- Y-14 at `gradingLadder.ts:84-86`.
- X-4 constants at `workerPoolState.ts:100,106,509-513`.
- FIFO tie-break at `:450-475`.
- Watchdog and lifecycle resolve-empty lines.
- Y-12 at `apply-order-design.md:370-373`.
- Twin `:530-537,544-558,589,740`.
- The parity-clear data directories exist.
