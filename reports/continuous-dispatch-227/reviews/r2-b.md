## Review of reports/continuous-dispatch-227/design.md (round 2, independent)

**Verdict: SOUND.** I found no high-severity defect. Claims (a), (b), (c) within its stated scope, and (d) all hold when checked line by line against `mctsSearch.ts` at HEAD (`mctsSearch.ts` and the pool and queue files are unchanged since the design's base). Claim (e) has one narrow hole that the shipped providers cannot reach. Claim (f)'s list of limits has one statement whose direction is wrong (medium) and a few omissions. Two §5 dispositions need a small fix (X-9 is incomplete; Y-12 is contradicted by §3.6). Nothing was edited or run, apart from read-only greps and seds.

### What I tried and could not break
- **(a)** Within one fill, the only state changes are a leaf going pending (`mctsSearch.ts:696`), dead-end closure (`:377-380`, `:686`) and visit bumps (`:685`). None of them can make a child selectable again. `isPending` is cleared only by apply (`:446`, `:477`), and apply runs only in the drain. `isBlocked` is read only at `:385`, set at `:403` and cleared at `:708`, apart from its false initialisation at creation. Blocked nodes have no reachable work, so exactness holds.
- **(b)** The fill guard plus the drain accounting give `A + F <= maxNodes`. Discards happen only after an abort or early stop, and the loop top returns after those. So dispatches minus degenerate expansions stay at or below `maxNodes`, and `F_after = 0` when `A` reaches the cap.
- **(c)** At c = 1:
  - No fill runs while a result is in flight.
  - No block can be set: every route that closes a node's last child also closes the node (`:448`, `:482-485`, `:686`).
  - The exits, rejection order and the abort-inside-`onSnapshot` path all match round mode.
  - The inner signal is aborted only by an outer abort or by the `finally`, so the 8XN-7 check (`:614`) behaves the same.
  - `buildSnapshot` has no timing field (`treeCommon.ts:506-514`).
- **(d)** The check sits immediately before the only apply call, with no `await` between them. Rejections caused by an abort arrive as microtasks after the synchronous drain, so the loop-top check returns first.
- **§5 citations:** I checked every cited line in the pool, watchdog, lifecycle, maiaQueue, deadlineSearch, workerPoolState, gradingLadder, verdict twin and harness files. All point at what they claim.

### Findings

**1. Medium. Breaks (f)'s limits (§3.6 "Maia policy cache across searches" row), the §4.1 wording, and the Y-12 disposition.**
- `design.md:704` says the reduction `(c-1)P/(cP+G)` "falls with P". Its derivative is `(c-1)G/(cP+G)^2 > 0`, so it rises with P.
- `:668` concludes that a lower app P makes "the gate's Maia-bound figures an upper estimate for the app". The Node gate sits in the Maia-bound regime: P = 83.3 against a peak at P* = 58.0 (t50-p4) and 47.9 (t400-p4), Table 1 `:732-733`. Lowering P there raises the win until P* is reached.
- Model check at G = 173.9, c = s = 4: P' = 70 gives 38.3%, P' = 58 gives 42.9%, P' = 40 gives 35.9%, P' = 30 gives 30.6%. The baseline at P = 83.3 is 34.3%. The app's win is higher unless its effective P falls below about 36 ms.
- The design's own §4.3 table (`:782`: wasm P 39.2 gives 35.6%, above Node's 34.3%) contradicts the row.
- This is the same monotonic overstatement Y-12 retracts, so marking Y-12 "applies" is undercut by §3.6.
- **Repair:** say the effect is non-monotonic (lower P raises the win down to P* and lowers it only below that), drop "upper estimate", and change the §4.1 wording to "rises with P".

**2. Low. Breaks (e) (§2.7 at `:460-462` and `:472`) and the X-8 "repaired" row.**
- An abort that fires synchronously during a fill is not re-checked before the `await` (sketch `:167-172`).
- Order of events: the loop-top check passes, then the fill calls `providers.policy` synchronously (`mctsSearch.ts:533`, through `dispatchExpansion`), then `if (settled.length === 0) await`.
- If a provider's synchronous part aborts the signal, `onOuterAbort` runs while `wake` is null, so `notify()` does nothing. The loop then waits for an in-flight settlement. A provider that hangs after the abort hangs the search. This contradicts "the next check always follows" and "wakes at once".
- The shipped providers cannot trigger this: the synchronous part of `maiaQueue.ts:295-314` never aborts, and deadline and cancel aborts arrive as macrotasks (`deadlineSearch.ts:118-121`).
- **Repair:** guard the wait with `!signal.aborted && !st.earlyStop`. Add a fixture where `policy()` aborts synchronously and `grade` never settles. The mutation to test against is removing that guard.

**3. Low. Breaks C5 M5 (`:77-80`) and the §3.6 hash row (`:665`): "M5 exists only in continuous mode" is false.**
- Round mode also stops in-flight grades on every abort, which leaves partial work in that worker's hash.
- The bot's deadline cut aborts while a round is in flight (`deadlineSearch.ts:118-121`; pool stop at `workerPoolDispatch.ts:297-308`).
- The analysis path does this on every position change (`useFlawChessEngine.ts:351-352`: `abort()` plus `pool.stopAll()`).
- Continuous mode adds M5 on early stops, which are routine for the bot. The gate is therefore blind to an effect present in both arms and amplified in continuous, not to a continuous-only one.
- **Repair:** reword both places.

**4. Low. §5 X-9 ("Real providers settle") and §2.4 scope limit 1 are incomplete.**
- Phase 198 §9c (`apply-order-design.md:1154`) named a residual path: a wedged in-flight ONNX inference has no policy-side watchdog.
- That is still true. `maiaWorkerHost.ts` has only init timeouts (`:84-92`, `:735`), and `maiaQueue.ts:174-201` waits on `lease.analyze` indefinitely.
- Without an abort, both modes hang. With an abort, round still hangs and continuous returns.
- **Repair:** state this pre-existing path in the X-9 row and qualify "an in-flight inference completes" (`:297`).

**5. Low. §2.6 "fourth in-flight state" (`:433-435`) misses a branch.**
- The chart-join fallback `inFlight.catch(() => requestPolicy(fen, elo, signal))` (`maiaQueue.ts:311-312`) calls `requestPolicy`, which has no aborted-signal check (`:265-292`).
- An `'abort'` listener added to an already-aborted signal never fires. So if the chart's pending request rejects after the stop, a stale request is enqueued and runs one full inference after the search has ended (app only).
- Nothing gets applied, so (d) still holds. The paragraph only covers the case where the join resolves.
- **Repair:** document the reject branch, and flag a one-line `if (signal?.aborted) return Promise.resolve({})` in `requestPolicy` for Plan 227-10 (do not fix it unscoped).

**6. Low. §3.6 is missing two harness/app differences under (f).**
- (i) In the harness, Maia memo hits still queue in the FIFO behind an in-flight inference: the memo is checked only inside `nodePolicy`/`runMaia` (`calibration-providers.mjs:229-231`), after the FIFO (`:377-400`). In the app, cache hits bypass the queue entirely (`maiaQueue.ts:297-298`). This affects about 2 to 10% of nodes (0.90 to 0.98 inferences per node, §4.1).
- (ii) On /analysis, the shared Maia worker also serves chart and gem-sweep requests, and chart requests are queued ahead of the search's (`maiaWorkerHost.ts:274-292`; `maiaQueue.ts:24-37`). The harness has no such traffic.
- **Repair:** add two rows to §3.6.

**7. Low. The (b) test obligation in §2.12 is ambiguous.**
- `budgetExhausted` is also set by a `maxPlies` cut (`mctsSearch.ts:679-684`) while `F > 0`.
- **Repair:** the "`inFlight == 0` at exhaustion" assertion must key on `nodesEvaluated === maxNodes`, not on `snapshot.budgetExhausted`.

**Minor citation note.** The X-6 row says the cache "writes only on bestmove (`:162-164`)". The `gradeRoot` group-success write at `workerPoolDispatch.ts:426` is the second write site, which §2.6 mentions but the row does not.

### §5 dispositions
All are correct against the code and against §9b/§9d except:
- **X-9:** incomplete (finding 4).
- **Y-12:** contradicted by the §3.6 row (finding 1).

The X-7 decision not to adopt Phase 198's throw is justified: the null return is unreachable (`mctsSearch.ts:417-419`) and identical to round mode.
