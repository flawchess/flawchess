# Review round 1, reviewer A (raw output)

**Verdict: NOT SOUND.** The loop design holds up: claims (a), (b), (d) and (e) survive the code. Claim (f) breaks on a concrete harness defect on a ship-bar config. Claim (c) is overstated. The §4 sizing does not reconcile with its own input data. Each break has a cheap repair, and none requires changing the continuous loop.

**What I verified as holding:**
- **(a)** `isBlocked` has exactly three uses (`mctsSearch.ts:385`, `:403`, `:708`), plus the initialisations at `:156` and `:197`. `isPending` is cleared only at `:446` and `:477`. Lemma 1 (selectable sets only shrink within a fill) and Lemma 2 hold, and a restart after a block replays the same PUCT choices at the ancestors.
- **(b)** Invariant I and `F == 0` at node-budget exhaustion both hold.
- **(d)** Check-then-apply is sound.
- **(e)** The `wake` hand-off is sound.
- **Data inputs:**
  - P and G reproduce exactly from the 226 TSVs (83.3/173.9, 85.1/143.7, 83.3/169.9, 83.1/75.5).
  - The browser-leg numbers reproduce, including 127.3 and 97.6 ms/node.
  - The clear-hash tripwire reproduces at 0 of 60 differing rows, for both stop modes.
  - All §4.1 and §4.3 arithmetic checks out.
- **§5:** dispositions are correct apart from items 3, 4 and 8 below.

**Findings**

1. **High. Breaks (f) and §2.6 consequence 1: the harness Maia FIFO ignores abort.**
   - **Evidence:**
     - `scripts/lib/calibration-providers.mjs:364-366`: `policy: maiaFifo ? (fen, elo, side) => maiaFifoPolicy(...)` drops the 4th `signal` argument that `mctsSearch.ts:533` passes.
     - `maiaFifoPolicy` and `maiaFifoProcess` (around `:311-340`) have no abort path. The app's `maiaQueue.ts:278-288` drops its not-yet-dispatched backlog on abort.
     - After a continuous early stop, queued stale inferences keep running. `engine-dispatch-stop-rule.mjs:733-737` waits only for Stockfish (`pool.whenIdle()`), then resets the Maia memo and stats and starts the next position's timer.
     - So the next position's first `policy()` queues behind the stale work. The stale inferences also land in that row's `maia_inferences` and `maia_cpu_ms`.
   - **Who pays:** only continuous mode. Round mode's early stop happens after the barrier, and a budget stop has F = 0 (§2.3).
   - **Size (Little's law at Node P = 83.3, G = 173.9, c = 4):** about 1.9 of the 3 surviving slots are in the Maia stage, so roughly 1 in service plus 1 queued. That is about 75 to 120 ms charged to each following position, or about 4 to 6 percent of a ~2 s stop-p4 search.
   - **Why it matters:** stop-p4 is in `SHIP_BAR_CONFIGS` (`engine_dispatch_227_verdict.py:135`). It also falsifies "up to one P", which holds for the app only.
   - **Repair:**
     - Forward `signal` in `makeNodeProviders`.
     - On abort, splice pending FIFO entries and resolve them `{}`, mirroring `maiaQueue.ts:279-287`.
     - Add a Maia-FIFO idle await next to `pool.whenIdle()` in every gate script before the timer starts, and add a per-row stale-inference tripwire.

2. **Medium. Breaks (c), and the §2.8 claim of the same observable at c = 1.**
   - **Evidence:** at c = 1 with an external abort while an expansion is in flight, round mode awaits `Promise.all` (`mctsSearch.ts:723-725`). In the sketch, continuous returns at once (`onOuterAbort` → `notify` → loop-top return), and a late rejection is dropped (§2.8). This gives three divergences:
     1. A provider that rejects after the abort makes round throw while continuous returns a snapshot.
     2. A never-settling provider hangs round while continuous returns. §2.7 and X-9 admit this.
     3. `dispatchExpansion` calls `grade()` after the policy resolves with no abort check between `:533` and `:586`. Round makes that call before returning and continuous after, so call lists compared at return differ.
   - **Gap in the tests:** the §2.4 fixture list has no abort-mid-flight case, so the obligation would not catch this. Separately, Y-8 asked for Sentry visibility, yet late rejections from cancelled work are dropped silently.
   - **Repair:**
     - Scope (c) to "no external abort while an expansion is in flight", or define call-list equality after quiescence.
     - Add a c = 1 abort-mid-flight fixture that pins the actual behaviour: equal snapshots, and continuous does not wait.
     - Capture or log late rejections.

3. **Medium. §4.2–4.4 sizing and the Y-5 disposition.**
   - **G is inflated:**
     - `grade_cpu_ms` is measured from `go` to `bestmove` processed in JS (`engine-grading-depth-ab.mjs:327-335`, `engine-dispatch-stop-rule.mjs:345-350`).
     - The 226 data was taken under main-thread Maia, which §3.1 itself says left Stockfish output unprocessed during inference. So G includes Maia blocking.
   - **The model fails against measured round wall in the same TSVs:**

     | Config | Measured round wall (ms/node) | Model (ms/node) |
     |---|---|---|
     | t50-p4 | 120.8 | 126.7 |
     | t400-p4 | 98.4 | 121.0 |
     | t400-p2 | 110.7 | 120.9 |
     | t50-p2 | 131.2 | 168.3 |

   - **P ignores memo hits:** Maia inferences per node are 0.98, 0.91, 0.98 and 0.90.
   - **Corrected ceilings:** using per-node Maia time as the continuous floor against measured round wall, t400-p4 (a ship-bar config) tops out at about 1 − 77.2/98.4 = 21.5 percent, not 29.7. "About 30 percent on the Node analysis path" is overstated.
   - **Repair:** validate the model against `wall_ms`, use measured round wall per node and `maia_cpu_ms` per node, and state the G inflation (or re-measure G under worker Maia).

4. **Low. X-11 / t50-p2.**
   - **Evidence:** the round formula `P + ceil(c/s)·G/c` ignores policy/grade pipelining. Appendix A's own `round_ms` gives about 126.5 ms/exp, matching the measured 131.2; the formula gives 168.3. The modelled win is therefore about 32 percent, not 49.5.
   - **Repair:** fix the formula or drop the row. It is already labelled model-only.

5. **Low. §4.4 simulation.**
   - **Evidence:** `round_ms` truncates the last round to `N − done`. A stop-rule round dispatches a full c-round and waits on the barrier (`mctsSearch.ts:664-666`, `723-725`, discards at `:743`). Round time is understated, so the reduction is understated (the conservative direction). "Last round can run a single expansion alone" is true only for a budget stop.
   - **Repair:** fix the wording, or simulate a full last round.

6. **Low. Reasoning text behind (d) and (e).**
   - **Evidence:**
     - §2.6's "an abort is delivered as an event on the event loop, never in the middle of a synchronous run" and §2.7's matching claim about `onOuterAbort` are false. `abort()` dispatches its listeners synchronously.
     - `deadlineSearch.ts:91-104` aborts inside `onSnapshot`, which is inside `applyAndReport` mid-drain. So `onOuterAbort` → `dispatchController.abort()` → the pool and Maia listeners (`workerPoolDispatch.ts:283-310`, `maiaQueue.ts:279-285`) run synchronously there.
     - The deadline can also fire from the timer macrotask (`deadlineSearch.ts:118-121`).
   - **Why the conclusions still hold:** `wake` is null mid-drain, the next check reads `signal.aborted`, and settlements still arrive as microtasks.
   - **Repair:** restate both passages.

7. **Low. Missing rows in the §3.6 limits table (f).**
   - **Evidence:**
     - The app's Maia policy cache persists across searches (`maiaQueue.ts:12-15`, `:297-298`), while the gates reset the memo per position (`engine-dispatch-stop-rule.mjs:736`, `engine-grading-depth-ab.mjs:746`, `engine-move-quality.mjs:646`). So effective P is lower in the app on consecutive searches, which shifts it toward the `(P+G)/c` regime.
     - The app has no inter-search quiesce. Slots still `stopping` after a continuous early stop reduce the next search's `gradeRoot` fan-out (`countIdleReadySlots`, `workerPoolDispatch.ts:345-352`). The gates hide this with `whenIdle()`.
   - **Repair:** add both as rows.

8. **Low. Citations and wording.**
   - §2.11 cites `calibration-providers.mjs:401-408` for "Content-neutral for round mode". The text is at `calibration-harness.mjs:401-406`.
   - X-6 cites `workerPoolDispatch.ts:213-224` for `writeCache: false`. That range is the cache-read gate; `writeCache: false` is at `:404`.
   - X-9 cites `workerPoolDispatch.ts:30,69` for the resolve-empty paths. Those are an import and the timer arm. The resolve-empty sites are `workerPoolWatchdog.ts:169,213` and `workerPoolLifecycle.ts:115,194,297-323`.
   - The X-4 row says devices run c = 4 on a pool below 4. That is bot only; analysis uses c = `computePoolSize()` (`useFlawChessEngine.ts:367`).
   - §1.5 says "variance falls by 0.58". That figure is the SD ratio; variance falls to about 0.33.
   - C1 says the round loop is "kept verbatim", but §2.1's helper extraction must move the `mctsSearch.ts:636-642` locals into a shared counters object. That is a refactor, not verbatim.
