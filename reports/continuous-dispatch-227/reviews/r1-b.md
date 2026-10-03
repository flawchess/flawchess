# Review round 1, reviewer B (raw output)

## Verdict: NOT SOUND as written. The loop itself holds up; claims (c) and (f) do not.

Claims (a), (b), (d) and (e) survive an adversarial read against the code at HEAD. Every `mctsSearch.ts` line reference in the doc matches the file (748 lines, last touched `d0f5cb2ba`). Claims (c) and (f) are false as stated. None of the findings needs the loop sketch changed. The repairs are: narrow the scope of (c), fix one harness file (the Maia FIFO), correct the §3.6 table and the Y-1 row, and add three test fixtures. I re-ran the §4 sizing and it reproduces from the named TSVs: P/G of 83.3/173.9, 85.1/143.7, 83.3/169.9 and 83.1/75.5, the stop-on node mix, and Appendix A's 28.8 / 29.3 / 21.2 / 18.7 / 14.2 percent and 32.0 / 33.9 percent.

## How each claim held up

- **(a) holds.** `isBlocked` has exactly three uses (`mctsSearch.ts:385,403,708`), and `selectPath` is called only from the fill. Lemma 1 holds: nothing that happens inside a fill re-opens a pending or closed child. A node with zero candidates has no work below it, by induction. Lemma 2 also holds: `isPending` is cleared only at `:446,477`, and that runs only in the drain.
- **(b) holds.** The fill guard and the drain step keep `A + F <= maxNodes`, so `F_after = 0` when A reaches the cap. A throw inside the fill drops the `dispatched` increment, but the search throws anyway, so that case is harmless.
- **(d) holds.** The check and the apply run with no `await` between them. Late settlements go to a dead closure. Expansions whose policy is still pending at cancel time call `grade()` later with an already-aborted signal, and every pool returns empty at once (`workerPoolDispatch.ts:211`, `:377`; `stockfish-pool.mjs:293`, `:561`). The doc does not name this case (finding 6).
- **(e) holds.** The executor runs synchronously, results are pushed before `notify`, `notify` clears `wake` before calling it, and an abort calls `notify`. Already-resolved providers and settlements arriving mid-drain are both handled.

## Findings

**1. Medium. Breaks (f). The harness Maia FIFO ignores abort; the app's queue does not.**
- **Evidence:**
  - `maiaFifoPolicy(session, ort, fen, elo, side)` takes no signal (`scripts/lib/calibration-providers.mjs:335-340`), and `makeNodeProviders` drops the 4th argument (`:367-369`).
  - The app drops its backlog on abort and resolves `{}` (`maiaQueue.ts:279-285`, `:301`).
  - `pool.whenIdle()` covers Stockfish only (`stockfish-pool.mjs:102-106`, `:596-601`).
  - The per-position loops start the timer right after it: `engine-dispatch-stop-rule.mjs:734-737,769-777` and `engine-move-quality.mjs:644-646,663-665`.
- **What happens:** after a continuous early stop, the in-flight inference plus any queued stale requests run inside the next row's timed window. Round mode never leaves stale Maia work: every round member has settled before apply, and `F = 0` at the budget cap. So this is a mode-asymmetric artifact on the judged stop-p4 config, where 11 of 16 positions stop early.
- **Magnitude (model):** roughly 0.5 to 1 P per early-stopped position against a modelled continuous total of about 36.5 s, so about 1.5 to 2.5 percentage points off the 28.8 percent. It is larger if requests queue behind the FIFO. The bias runs against continuous. In the app the in-flight remainder is hidden behind the human's move time.
- **Instrumentation side effect:** `resetMaiaInstrumentationStats()` (`calibration-providers.mjs:199-203`) zeroes `maiaInflightStats.current` while a stale inference is still running. Its `finally` decrement (`:269`) then takes `current` to -1, so later peaks read one low. A real two-way overlap would read 1 and pass `_MAIA_MAX_PEAK_INFLIGHT = 1` (verdict twin around `:741`). The stale `maiaCpuStats` time also lands in the next row.
- **Not disclosed:** §3.6 doesn't mention this, and §2.6 describes only the app's behaviour.
- **Repair:** make `maiaFifoPolicy` abort-aware (remove the request from `maiaFifoPending` and resolve `{}`), forward the signal, and add a Maia-idle wait next to `whenIdle()`. Add both effects to §3.6.

**2. Medium. Breaks (f) and the Y-1 disposition. The harness resets the Stockfish hash; the app never does.**
- **Evidence:** `pool.resetAll()` calls `newGameAll()`, which sends `ucinewgame` to every engine before every position. That is in `stockfish-pool.mjs:647-658`, called from `engine-dispatch-stop-rule.mjs:437,735`, `engine-move-quality.mjs:645` and `engine-grading-depth-ab.mjs:569,745,816`. The app has zero `ucinewgame` / `Clear Hash` hits.
- **Separately:** the calibration harness builds `createStockfishPool({ size })` (`calibration-harness.mjs:394`) with the default `clearHash = true`, so it sends `Clear Hash` on every grade (`calibration-providers.mjs:474`).
- **Consequence:** the §3.6 row "Hash: never cleared vs `--hash warm`: Matches" is false. In the harness a warm hash lasts one search only. The gate cannot see the cross-search part of M4, and it cannot see M5 at all. M5 (partial work left in a cancelled grade's hash, read by the next search) only happens in continuous mode, and consecutive bot searches are two plies apart, so it is material.
- **Repair:**
  - Correct the §3.6 row and the Y-1 row.
  - State that the gate cannot measure M5.
  - Either say the calibration (D-15) refit runs with the hash cleared on every grade, or add a report-only variant that keeps the hash across the searches of a game.

**3. Medium. Breaks (c) as defined ("every provider timing").**
- **Counterexample:** at c = 1, an outer abort lands while a grade is in flight, and the provider rejects on abort (the standard AbortError pattern).
  - In the sketch, `onOuterAbort` aborts the inner signal (queuing the rejection), then `notify` (queuing the wake).
  - The wake continuation runs first: empty drain, then `signal.aborted`, then return.
  - The rejected settlement arrives after the loop has returned and is dropped.
  - Round mode awaits `Promise.all` regardless of abort (`mctsSearch.ts:723-725`) and throws.
  - With a provider that never settles, round mode hangs and continuous mode returns.
- **Call lists also differ:** continuous returns before the in-flight `dispatchExpansion` resumes and calls `grade` (`:586`). So call lists captured at search resolution differ unless the test waits for everything to settle.
- **Test gap:** the §2.4 fixture list has "pre-aborted" and "abort inside `onSnapshot`" but not "external abort while an expansion is in flight". That is the one case where the two loops' control flow differs.
- **Not live in prod:** app providers resolve on abort (`maiaQueue.ts:279-285`; `workerPoolDispatch.ts:285-309`; `:415-420`).
- **Repair:** scope (c) to providers that resolve after abort and compare call lists after quiescence. Add that fixture.

**4. Low to medium. Breaks (c) / X-12 as a guard.**
- **Evidence:** C1 says the round loop is "kept verbatim", but §2.1 pulls `applyAndReport` and `discoverDeadEnd` out of it.
- **Problem:** the "live golden" is therefore the post-refactor round loop. A defect in a shared helper would hit both arms equally, and the c = 1 equality test cannot see it. X-12 asked for equality with the pre-rewrite code.
- **Repair:** make it a Plan 227-10 obligation to re-run the 227-08 `--hash clear` parity check after the extraction, requiring 0 diffs against the committed `reports/data/continuous-dispatch-227/tripwire/parity-clear`. Alternatively, commit pre-rewrite goldens for the §2.4 fixtures. Fix the C1 wording.

**5. Low. §2.6 deadline path is incomplete.**
- **Evidence:** the timer at `deadlineSearch.ts:118-121` aborts directly once the floor is already met, which is the common case. That abort arrives as a timer event while the loop waits, not inside `onSnapshot`.
- **Problem:** "the cut still happens at the snapshot that crosses the floor" is true only when the deadline expires before the floor is reached. The behaviour itself is fine, because (e)'s abort wake handles it.
- **Repair:** fix the text, and add a test with a timer-driven abort while several expansions are in flight.

**6. Low. §2.6 leaves out an in-flight state.**
- **The state:** expansions whose policy is still pending at cancel time call `grade()` after the search has returned.
- **Covered in code:** this is handled by the pre-abort guards listed under (d) above.
- **Related gap:** the app's join on a pending chart request isn't abort-aware (`maiaQueue.ts:311-312`).
- **Repair:** state it, and add a test where the policy settles after a stop and the grade returns empty without enqueuing.

**7. Low. The §5 X-9 citation is wrong.**
- **Evidence:** it cites `workerPoolDispatch.ts:30,69` (an import and a `setTimeout`) as proof that the watchdog and death paths resolve empty.
- **Repair:** the real sites are `workerPoolWatchdog.ts:169,213` and `workerPoolLifecycle.ts:115,194,297,305,318,323`.

**8. Low. The §5 X-4 disposition skips X-4(c).**
- **Problem:** slots that are stopping or not ready create a backlog even when c equals the pool size. Continuous mode makes "stopping" slots routine after every early stop (`workerPoolDispatch.ts:304-308`).
- **Root-split effect:** the app's root split falls back to a plain grade while any slot is stopping or anything is queued (`countIdleReadySlots`, `:345-351`; `:385`). The human's move time hides this in the bot, and `whenIdle` hides it in the harness.
- **Repair:** state it.

**9. Low. The §2.11 reword list has a wrong path and missing items.**
- **Wrong path:** "Content-neutral for round mode" is at `scripts/calibration-harness.mjs:401-406`, not `calibration-providers.mjs:401-408`.
- **Missing:**
  - `mctsSearch.ts:113`, `:126-136`, `:345-360`, `:575-583`, `:602-603`
  - `maiaQueue.ts:259-263`
  - `engine-dispatch-stop-rule.mjs:46` and the `whenIdle` doc, both of which claim quiescence that does not cover Maia
- **Minor drift:** C2 cites `useFlawChessEngine.ts:367`; the concurrency line is `:369`.

## §5 dispositions

The rest are correct against the code and against §9b/§9d:
- X-1, X-2, X-3, X-5, X-6, X-7, X-8, X-10, X-11
- Y-2 through Y-14
- N-1 through N-4

The ones that need correcting are:
- **Y-1:** finding 2.
- **X-12:** finding 4.
- **X-9:** finding 7, citation only.
- **X-4:** finding 8, incomplete.
