**Verdict: SOUND.** No high or medium finding. Claims (a) to (e) hold against the code at 9f0b6be78. Claim (f) holds within the limits that §3.6 states. Every §5 disposition matches the code and apply-order-design.md §9b/§9d; one row is filed under the wrong category (finding 2).

`frontend/` is identical between the doc's evidence commit 399780bf8 and 9f0b6be78, and HEAD (dc6355730) differs only in a planning file. Every `mctsSearch.ts`, `workerPoolDispatch.ts`, `maiaQueue.ts`, `deadlineSearch.ts`, `workerPoolState.ts`, `workerPool.ts`, `gradingLadder.ts`, watchdog/lifecycle and maiaWorkerHost citation I spot-checked is exact.

**What I tried and could not break:**
- **(a)** Inside a synchronous fill, the only tree mutations are:
  - pending set (`mctsSearch.ts:696`)
  - dead-end close (`:377-380`)
  - visit bump and closure propagation (`:685-686`, `:337-343`)

  Pending is cleared only in `applyExpansion` (`:446`, `:477`), which runs only in the drain. A provider's synchronous prefix (`:533`) cannot mutate the tree. An abort fired from inside a fill only settles promises, which resolve as microtasks.
- **(b)** The fill guard plus "drain lowers F by one, raises A by at most one" gives A + F <= maxNodes. At A = maxNodes, F_before <= 1, so F_after = 0.
- **(c)** At c = 1, with nothing pending, no block can be set: every way a node closes (`:448`, `:482-485`, `:686`) closes its parent too, and an all-illegal expansion closes because the "all children closed" test is vacuously true. The exits and the maxNodes checks are equivalent to round mode's `:650`, `:666` and `:711-718`.
- **(d)** The check sits directly before the only apply call. An abort raised inside `onSnapshot` (`deadlineSearch.ts:97-103`) runs listeners that only settle promises (`workerPoolDispatch.ts:286-312`, `maiaQueue.ts:279-285`).
- **(e)** The `settled.length` part of the pre-await check is structurally always true. The abort re-check covers a synchronous abort during a fill.
- **(f)** The harness Maia FIFO abort and `whenMaiaIdle` behave as the doc says (`calibration-providers.mjs:306-400`). `withEngine` also handles a late rejection after abort (`stockfish-pool.mjs:330-337`). Every judged arm pins `--maia-fifo` (`engine_interleave_227.py:237`, `:260`).

**Findings**

1. **Low, (d)/(e) verification table (§2.12).** The "timer-driven deadline abort" test can pass even with the mutation it lists ("drop `notify()` from `onOuterAbort`").
   - The test must also show that in-flight work is cancelled, which needs abort-aware providers.
   - With abort-aware providers, `dispatchController.abort()` makes them settle empty. That settlement calls `notify()` from the settle callback, waking the loop anyway. It then discards everything and returns, so every assertion still passes under the mutant.
   - Evidence: the loop sketch, `workerPoolDispatch.ts:286-312`.
   - Repair: the fixture's grade should record the abort but settle only after a later macrotask (or never). Assert the search promise resolves before any provider settles, as the c = 1 abort-in-flight fixture already does.

2. **Low, §5 X-9 disposition.** The row is marked "moot", but §5 defines moot as "moot under the relaxed contract", and X-9 has nothing to do with determinism.
   - The design adopts X-9's direction ("continuous is not worse"), so the finding applies.
   - It also corrects X-9's premise "both real providers foreclose it, mock-only". The wedged-ONNX path is real: `maiaWorkerHost.ts` has no analyze watchdog (only init-timeout code at `:84-92` and `:735`), and the queue waits on `lease.analyze` indefinitely (`maiaQueue.ts:174-201`).
   - Repair: change it to "applies", with the correction stated.

3. **Low, §1.3 C5 M5 wording.** "Round mode's pool also stops in-flight grades … at every bot deadline cut (`deadlineSearch.ts:91-121`)" is too broad.
   - In the armed-cut case, the abort fires from `onSnapshot` inside the apply loop (`deadlineSearch.ts:97-103`, `mctsSearch.ts:742`). By then `Promise.all` (`:723-725`) has resolved, so nothing is in flight to cancel.
   - The statement holds for timer cuts (`deadlineSearch.ts:118-120`) and analysis position changes. The conclusion that M5 exists in both arms is unaffected.
   - Repair: say "at every timer-driven deadline cut and every analysis restart".

4. **Low, evidence has drifted at the review commit.** The doc pins line numbers to 399780bf8, but commits 012856e92 and dcba1ba14 (after the SOUND review) moved code:
   - `scripts/engine_dispatch_227_verdict.py`:
     - §1.5's `_check_round_determinism :544-558` no longer exists. It became the report-only `round_repeat_disagreement_positions` at `:565-577`.
     - §3.5 `:530-533` is now the mode check at `:553`, and `:534-537` is now `:557-560`.
     - The `net` line is at `:609`, not `:589`.
     - `LOAD_GATE_MAX` is at `:143`.
   - `engine-dispatch-stop-rule.mjs` cites `:438`, `:439`, `:735`, `:737` and `:738` are each shifted by 2 to 5 lines.
   - `node-engine-providers.mjs:120` is now `:125`.
   - §1.5 and §2.11 still describe as future work items that are already done: the gate relaxation, and the rewording of the tooling comments at `calibration-harness.mjs:405`, the stop-rule header, the `whenIdle` docs and node-engine-providers.
   - Repair: add a note that `scripts/` citations predate those commits, or re-pin them to 9f0b6be78 and mark those items done.

5. **Low, §2.11 reword list is incomplete.** Three comments that continuous mode makes false are missing:
   - `botBudget.ts:63` ("so app == harness determinism holds exactly")
   - `types.ts:66` (stop rule evaluated in the "mctsSearch canonical apply-order loop")
   - `mctsSearch.ts:56-65` (gradeRoot bit-identity "scoped per (concurrency, pool size)")

   Repair: add them to the Plan 227-10 reword list.

**Checked and correct:**
- All other X and Y rows against §9b (lines 1082-1124) and §9d (lines 1177-1213), including:
  - X-7's three null returns: `:368`, `:391`, `:419`
  - Y-12 at `apply-order-design.md:370-373`
  - Y-10's §3 range 272-453
  - Y-14's cache key: `gradingLadder.ts:84-86` and `workerPool.ts:274-276`
  - N-3's FIFO tie-break: `workerPoolState.ts:457-475`
- The committed parity-clear TSVs exist (60 rows, `clear`/`true`/`round`), so the §2.4 re-run obligation is actionable.
