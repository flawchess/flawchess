## Verdict: SOUND

I reviewed `reports/continuous-dispatch-227/design.md` at commit 9f0b6be78, read-only. I made no edits and ran no measurements. None of the six claims breaks within the scope the document states. Every disposition in §5 checks out against `mctsSearch.ts` and the other cited files, and against `apply-order-design.md` §9b (lines 1105-1118) and §9d (1187-1213). What I found is low-severity hygiene, consistency and harness-fidelity gaps, not correctness defects.

## Claims I tried to break, and why they held

- **(a) Per-fill blocks are exact.** `isBlocked` is only read at `mctsSearch.ts:385`, set at `:403` and cleared at `:708`. The only other occurrences are initializations at `:156` and `:197`. Pending and closed are monotone within a fill: `isPending` is cleared only at `:446` and `:477`, which run only in the drain. Block-and-restart reaches the same leaf a work-aware PUCT would, because blocks do not change PUCT scores between restarts.
- **(b) `applied + inFlight <= maxNodes`, and `inFlight == 0` at exhaustion.** The guard admits a dispatch only below the cap. A drain step never raises the sum. When `A` reaches `maxNodes` the arithmetic forces `F_before <= 1`. Keying the test on `nodesEvaluated` rather than the flag is correct, since `:679-684` sets the flag mid-flight.
- **(c) `c = 1` byte-identity.** At `c = 1` the fill makes no `selectPath` call while anything is in flight. Its guard equals `:666`. No block can arise, because every route that closes a last child also closes the parent (`:448`, `:482-485`, `:686`). Pre-aborted entry, a stop from inside `onSnapshot`, a rejection and the exits all match. The abort-while-in-flight case is correctly scoped to "after quiescence".
- **(d) No apply after abort or stop.** There is a single apply site, guarded synchronously. Abort listeners only settle promises (`workerPoolDispatch.ts:286-312`, `maiaQueue.ts:279-285`). Grades run after a stop see the aborted inner signal and return empty without queuing (`:211`, `:377`; `stockfish-pool.mjs:293`).
- **(e) No missing wakeup.** `wake` is assigned in the same synchronous run as the check. Settlements arrive as microtasks. `notify()` clears `wake` before calling it. The R2B-2 re-check covers an abort raised during a fill. I found no path where `wake` is non-null while the loop is not awaiting.
- **(f) Harness fidelity.** Every gate script imports the real `mctsSearch` and passes `dispatchMode`: `engine-move-quality.mjs:657`, `engine-dispatch-stop-rule.mjs:755`, `engine-grading-depth-ab.mjs:761,833`, `calibration-harness.mjs:635`. The dispatch-mode probe would detect continuous dispatch correctly (`dispatch-mode.mjs:163-201`). Harness Stockfish is the same vendored build with the same go shape (`node-engine-providers.mjs:438-441`, `engine-dispatch-stop-rule.mjs:336-342` against `workerPoolDispatch.ts:51-53`). The §3.6 limits table is honest.

## Findings

1. **Low, against (d)/(e).** The fill guard in the §2.1 sketch (design.md ~201-202) has no `signal.aborted` term. In the R2B-2 case (an abort inside a provider's synchronous prefix, `mctsSearch.ts:533`), the rest of that fill keeps selecting and dispatching up to `c` leaves on the already-aborted inner signal, and keeps bumping visits and closing dead ends (`:679-686`). That can include setting `budgetExhausted`, so the aborted search can report `stopReason: 'budget'`. Nothing is applied, so (d) holds as worded, and round mode makes the same selection mutations. §2.7 says the loop-top check "always follows" but does not mention the post-abort dispatches.
   - Repair: add `&& !signal.aborted` to the fill guard. This does not affect `c = 1` identity, because the one dispatch is the fill's last action. Alternatively, state the behaviour and have the R2B-2 test assert the extra policy calls.

2. **Low, against (f), missing §3.6 row.** On an abort, the harness Maia FIFO checks `signal.aborted` before it checks the memo (`calibration-providers.mjs:378`). The app checks the policy cache first and the abort second (`maiaQueue.ts:297-301`). So after a stop, an app cache hit resolves a real policy and then calls `grade()` with an aborted signal. The harness instead returns `{}` and makes no grade call. Applied results and timing are unaffected, but the "policy settles after stop" fixture (§2.12) and any call-count instrumentation behave differently in app and harness.
   - Repair: add one line to the §3.6 Maia-queue row or to §2.6's "fourth in-flight state".

3. **Low, §2.8 justification (2) covers the app only.** The harness pool can reject: `stockfish-pool.mjs:337` (`settle(reject, err)`), and the gate's `gradeRoot` rethrows at `engine-dispatch-stop-rule.mjs:428`. Under the R2A-6 rule, a real harness engine error that settled just before a stop but is drained after it is dropped silently in continuous mode. Round mode can never be in that state.
   - Repair: note this in §2.8 or §3.6, or have the gate wrapper log rejections.

4. **Low, citation and status staleness at 9f0b6be78.** The document pins its line references to 399780bf8. Commits 012856e92 and dcba1ba14 have since moved scripts lines and completed work the document still lists as pending.
   - Verdict twin: §3.5 `:530-537` is now `:553-560`, `:740` is now `:885`, and the Y-1 row's `:536-537` is now `:559-560`. §1.5's description of `_check_round_determinism` (`:544-558`) is already replaced by the report-only `round_repeat_disagreement_*` (`:495-510`, `:567`).
   - `stockfish-pool.mjs`: `whenIdle` `:591-596` is now `:598-603`, and `newGameAll` `:647-658` is now `:649-661`.
   - `engine-dispatch-stop-rule.mjs`: `:735,737,738` are now `:740,742,743`.
   - The tooling-comment items in §2.11 landed in dcba1ba14. However, the stale trailing comment on `node-engine-providers.mjs`'s `numThreads = 1` line was annotated, not reworded.
   - Repair: add a closing note naming those two commits, or refresh the references.

5. **Low, §2.11 reword list is incomplete.** Two comments that become false in continuous mode are missing:
   - `mctsSearch.ts:55-64`: "a harness's bit-identity claim for a gradeRoot-splitting run is now scoped per (concurrency, pool size) pair".
   - `mctsSearch.ts:362-367`: the root-guard comment's "two concurrent dispatch slots in the very first round".

6. **Low, internal wording contradiction.** C4.1 says "Round mode is the same code as A21S". C1 and §2.1 themselves say the extraction is a refactor, not verbatim code. `types.ts:119-121` still calls round mode "the byte-identical A21S barrier loop".
   - Repair: say "behavior-identical, proven by pre-extraction goldens and the clear-hash parity re-run".

7. **Low, §5 X-7 row.** "The loop wakes only on a settlement" contradicts §2.7: an abort also wakes it. The "applies" disposition itself is correct, since the `:419` null is unreachable (`select.ts:114-139` always returns a UCI from its input).

8. **Nit, (b) precondition.** `maxNodes` is typed as plain `number` (`types.ts:105`). With a non-integer value the guard lets `A + F` reach `ceil(maxNodes)`, and "`A = maxNodes`" never occurs. Both modes behave the same and the app constants are integers.
   - Repair: state that `maxNodes` is a positive integer.

## §5 dispositions

Every row is correct against the code at 9f0b6be78:
- **X-4:** `workerPoolState.ts:100,106,509-513`, `useFlawChessEngine.ts:369`, `workerPoolDispatch.ts:345-352,384-385`.
- **X-6:** `:162-164,217-224,403-404,426`, `workerPool.ts:274-276`.
- **X-9:** `workerPoolWatchdog.ts:169,213`, `workerPoolLifecycle.ts:115,194,297,305,318,323`, `maiaQueue.ts:198,214`, and the absence of any analyze watchdog in `maiaWorkerHost.ts`.
- **X-7:** null sites at `:368`, `:391`, `:419`.
- **Y-2:** `:259-260`.
- **Y-12:** `apply-order-design.md:370-373`.
- **Y-14:** `gradingLadder.ts:84-86`.

The moot, applies and repaired categories match the §9b/§9d findings. X-1, X-5 and Y-6 depend on commit-ordered machinery that this design does not rebuild.
