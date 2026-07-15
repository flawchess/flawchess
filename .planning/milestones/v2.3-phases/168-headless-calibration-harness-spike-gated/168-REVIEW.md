---
phase: 168-headless-calibration-harness-spike-gated
reviewed: 2026-07-12T05:51:24Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - scripts/calibration-harness.mjs
  - scripts/lib/stockfish-pool.mjs
  - scripts/lib/node-engine-providers.mjs
  - scripts/lib/calibration-providers.mjs
  - scripts/lib/calibration-anchors.mjs
  - scripts/lib/calibration-openings.mjs
  - scripts/lib/calibration-elo.mjs
  - scripts/lib/frontend-alias-hook.mjs
  - scripts/gem-elo-calibration.mjs
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
fixed_at: 2026-07-12T06:07:00Z
fix_scope: critical_warning
fixed: 8
skipped: 0
fix_status: all_fixed
---

# Phase 168: Code Review Report

**Reviewed:** 2026-07-12T05:51:24Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the headless calibration harness (bot-vs-anchor game loop, N-process Stockfish pool,
Node `EngineProviders` adapter, Elo-inversion summary, and the `@/`-alias resolve hook), plus
the Phase-165 `gem-elo-calibration.mjs` sibling that now shares bring-up code with it. The core
game logic (terminal classification, adjudication sustain-tracking, UCI-keyed grading via
`pv[0]`, seeded PRNG derivation, per-cell TSV durability) is careful and mostly correct — the
Pitfall-2 "reset every option before every `go`" discipline is followed almost everywhere, and
the incremental per-cell TSV write genuinely survives a mid-sweep crash as documented.

The real defects cluster around **process lifecycle management**: both harnesses spin up
Stockfish child process(es) — and, in the pool case, temp `.cjs`/`.wasm` file copies — in code
that runs *before* the enclosing `try/finally` that's supposed to clean them up, so a failure
in setup (TSV directory not writable, `chess.js` resolution failing, or a partial pool-spawn
failure) leaks live child processes with no reference left to terminate them. There's also one
concrete discipline gap (`stockfishSkillMove` not resetting `MultiPV`) and no error/exit
handlers anywhere on the spawned child processes, meaning any process-level failure (crash,
spawn ENOENT, EPIPE while writing to a dead pipe) surfaces as an unhandled `'error'` event
rather than a catchable failure.

## Critical Issues

### CR-01: Stockfish child processes leak when anything after pool creation fails, before the cleanup `try/finally` is even entered

**FIXED** — commit `2d33651e` (`fix(168): CR-01 guard Stockfish bring-up so a later setup failure can't leak child processes`). Both `calibration-harness.mjs`'s and `gem-elo-calibration.mjs`'s `main()` now wrap the entire spawn-through-TSV-writer-creation sequence in one `try/catch` that tears down the already-created engine(s) before rethrowing.

**File:** `scripts/calibration-harness.mjs:730-744`
**Issue:** `main()` calls `setupHarnessEngines()` (which spawns `args.stockfishProcs` live
Stockfish child processes and returns a `pool` handle) and *then*, still outside any
`try/finally`, calls `buildTimestamp()` / `openMainTsvWriter(mainTsvPath)` (line 735), which does
`fs.mkdirSync` + `fs.createWriteStream`. Only *after* that does the `try { ...sweep... } finally
{ pool.quitAll(); ... }` block begin (lines 744/782-785).

If `openMainTsvWriter` throws — e.g. `args.outDir` isn't writable, the disk is full, or a
sibling process holds a conflicting lock — the already-spawned `pool` (N real OS processes) is
never terminated: `pool` is a local variable in `main()`, `main().catch()` (line 800) only logs
the error and sets `process.exitCode`, and nothing ever calls `pool.quitAll()`. Running the
harness once against a bad `--out-dir` leaks `args.stockfishProcs` (default 4) live Stockfish
processes every time.

The same pattern exists in `scripts/gem-elo-calibration.mjs:626-640`: `spawnStockfish()` (one
process) succeeds, then `openTsvWriter` runs before the `try/finally` at lines 640/668-671 that
calls `stockfish.terminate()`.

**Fix:** Wrap the *entire* bring-up sequence (engine spawn through TSV-writer creation) in one
`try/catch` that tears down whatever was already created before rethrowing, e.g.:
```js
let pool;
try {
  ({ providers, pool, Chess } = await setupHarnessEngines({ stockfishProcs: args.stockfishProcs }));
  tsvWriter = openMainTsvWriter(mainTsvPath); // now inside the same guarded block
} catch (err) {
  pool?.quitAll();
  throw err;
}
```

### CR-02: `createStockfishPool`'s parallel spawn fan-out leaks every already-spawned sibling process (and their temp files) if any one spawn fails

**FIXED** — commit `15e03e8c` (`fix(168): CR-02 terminate every already-spawned sibling engine on partial pool-spawn failure`). `createStockfishPool` now uses `Promise.allSettled` and terminates every fulfilled engine before rethrowing on any rejection; `spawnStockfish()` wraps its own `init()` call so a failed handshake still kills the child and cleans up its temp files (via the WR-04 fix, commit `b8651990`) before rethrowing.

**File:** `scripts/lib/stockfish-pool.mjs:74-78`
**Issue:**
```js
const engines = await Promise.all(Array.from({ length: size }, () => spawnStockfish()));
```
`Promise.all` rejects on the first failing `spawnStockfish()` call, but any of the *other*
`size - 1` engines that already finished spawning (their `child_process` is live, `init()`
completed, UCI handshake done) are simply discarded — nothing iterates the settled results to
terminate them. `createStockfishPool` throws before ever constructing a `pool` object, so there
is no handle left anywhere to call `.terminate()` on those already-running processes.

Compounding this: `scripts/lib/node-engine-providers.mjs:133-154`'s `spawnStockfish()` itself has
the identical gap at a smaller scale — if `await engine.init()` (line 152) times out (30s,
`STOCKFISH_INIT_TIMEOUT_MS`) or otherwise throws, the already-`spawn()`-ed `child` process (and
its two just-copied temp files in `os.tmpdir()`, lines 144-148) is never killed; the local
`engine`/`child` reference is lost when the function throws.

**Fix:** Use `Promise.allSettled` instead, terminate every fulfilled engine if any entry
rejected, then throw:
```js
const results = await Promise.allSettled(Array.from({ length: size }, () => spawnStockfish()));
const failed = results.find((r) => r.status === 'rejected');
if (failed) {
  for (const r of results) if (r.status === 'fulfilled') r.value.terminate();
  throw failed.reason;
}
const engines = results.map((r) => r.value);
```
And in `spawnStockfish()`, wrap the `init()` call so a failed handshake still kills the child and
removes the temp files before rethrowing.

## Warnings

### WR-01: Pool never recovers a timed-out engine with `stopAndSync()` before releasing it back to the free list

**FIXED** — commit `de9468e8` (`fix(168): WR-01 stopAndSync() a failed pool request before releasing its engine`). `withEngine`'s `catch` now calls `engine.stopAndSync().catch(() => {})` before releasing, mirroring `gem-elo-calibration.mjs`'s recovery path.

**File:** `scripts/lib/stockfish-pool.mjs:58-66`
**Issue:** `withEngine`'s `finally` unconditionally calls `releaseEngine(pool, engine)` even when
`fn(engine)` (i.e. `nodeGrade`/`evalPositionCp`/`stockfishSkillMove`) rejected — e.g. because
`waitFor(...)` timed out while the engine was still mid-search. `node-engine-providers.mjs`'s own
`stopAndSync()` (lines 113-125) exists *specifically* to make an engine quiescent again after a
timed-out `go` before it's reused, and `gem-elo-calibration.mjs`'s per-position catch block
(lines 660-665) does call it for exactly this reason. `stockfish-pool.mjs` has no equivalent —
a released-but-still-searching engine can be handed straight to the next FIFO waiter
(`releaseEngine`, lines 49-56) or picked up by the next free-engine scan, corrupting whatever
`go` that next caller issues on top of the still-live search. Under the current harness's call
pattern (bot grading, anchor moves, and adjudication never overlap, and
`SearchBudget.concurrency === pool.size` so there's rarely a queued waiter) this is unlikely to
trigger visibly today, but it's inconsistent pool behavior and a latent trap for any future
caller/feature that does have concurrent pool contention.
**Fix:** In `withEngine`'s `catch`/`finally`, call `await engine.stopAndSync()` before releasing
whenever `fn` rejected, mirroring `gem-elo-calibration.mjs`'s pattern:
```js
async function withEngine(pool, fn) {
  const engine = await acquireEngine(pool);
  try {
    return await fn(engine);
  } catch (err) {
    await engine.stopAndSync().catch(() => {});
    throw err;
  } finally {
    releaseEngine(pool, engine);
  }
}
```

### WR-02: `stockfishSkillMove` doesn't reset `MultiPV` before its `go`, breaking the module's own stated option-reset discipline

**FIXED** — commit `d149f34c` (`fix(168): WR-02 reset MultiPV before stockfishSkillMove's go`). Added `stockfish.send('setoption name MultiPV value 1');` before `position fen ${fen}`, exactly as suggested.

**File:** `scripts/lib/calibration-anchors.mjs:66-76`
**Issue:** The file's own header comment (lines 15-18) states "both anchors set every UCI option
their `go` depends on immediately before that `go`" — and `nodeGrade`/`evalPositionCp` in
`calibration-providers.mjs` (lines 137-139, 167-169) both explicitly reset `MultiPV` before every
search. `stockfishSkillMove` only resets `Skill Level` and `UCI_LimitStrength`:
```js
stockfish.send(`setoption name Skill Level value ${skillLevel}`);
stockfish.send('setoption name UCI_LimitStrength value false');
stockfish.send(`position fen ${fen}`);
stockfish.send(`go movetime ${ANCHOR_MOVETIME_MS}`);
```
If the engine was previously used for a bot-grading `go` (which sets `MultiPV` up to
`candidateUcis.length`, e.g. 20-40), the anchor's `go` runs with that stale MultiPV value —
functionally low-impact for the `bestmove` line specifically, but it's exactly the kind of
cross-role option leakage Pitfall 2 was written to prevent, and it's silently untested.
**Fix:** Add `stockfish.send('setoption name MultiPV value 1');` before `position fen ${fen}`.

### WR-03: No error/exit handlers on the spawned Stockfish child process

**FIXED** — commit `83cbdc06` (`fix(168): WR-03 add error/exit handlers on the spawned Stockfish child process`). Registered `child.on('error', ...)`, `child.on('exit', ...)`, and `child.stdin.on('error', ...)`; every in-flight `waitFor()` is now tracked and rejected with a clear diagnosis on any of these instead of surfacing as an unhandled exception or a generic timeout.

**File:** `scripts/lib/node-engine-providers.mjs:67-131` (`StockfishUciEngine`), `133-154`
(`spawnStockfish`)
**Issue:** The class registers only `this.child.stdout.on('data', ...)` (line 72). There is no
`child.on('error', ...)`, `child.on('exit'/'close', ...)`, or `child.stdin.on('error', ...)`
anywhere. Node's `EventEmitter` throws (crashing the whole process with an unhandled exception)
if an `'error'` event fires with no listener — this can happen from a `spawn` failure (e.g.
`ENOENT` if `node` isn't resolvable, though unlikely here) or from writing to `stdin` after the
child has already exited (`EPIPE`), which `terminate()` (lines 127-130) and every `send()` call
are exposed to if the underlying process died unexpectedly. Separately, if the Stockfish process
crashes mid-search, nothing detects it until the relevant `waitFor` timeout elapses (a generic
"response timeout" error, not a clear "process died" diagnosis).
**Fix:** Register `child.on('error', ...)` and `child.stdin.on('error', ...)` handlers (at
minimum logging + rejecting any in-flight `waitFor`), and consider a `child.on('exit', ...)`
listener that fails fast rather than waiting out the full timeout.

### WR-04: Temp `.cjs`/`.wasm` file copies are never deleted

**FIXED** — commit `b8651990` (`fix(168): WR-04 delete temp .cjs/.wasm Stockfish copies on terminate()`). `StockfishUciEngine` now retains `tempFilePaths` and `fs.rmSync`s both in `terminate()`. Verified live: a full harness run's temp files were absent from `os.tmpdir()` after the run completed (no accumulation).

**File:** `scripts/lib/node-engine-providers.mjs:144-154`
**Issue:** `spawnStockfish()` copies the vendored engine JS + WASM into two uniquely-named files
under `os.tmpdir()` per spawned process (lines 145-148). Neither `StockfishUciEngine.terminate()`
(lines 127-130) nor any other code path ever unlinks them, and the paths aren't even retained on
the `engine`/`StockfishUciEngine` instance, so cleanup isn't even possible later. Every harness
run leaves `2 * size` orphaned files in the OS temp directory (default pool size 4 for
`calibration-harness.mjs`, 1 for `gem-elo-calibration.mjs`) that accumulate indefinitely across
iterative dev-tool invocations.
**Fix:** Store `cjsPath`/`wasmPath` on the returned engine (or a closure) and `fs.unlink` both in
`terminate()`.

### WR-05: `gem-elo-calibration.mjs` still hand-rolls its own `mulberry32`, duplicating the frontend PRNG this same file claims never to reimplement

**FIXED** — commit `30123534` (`fix(168): WR-05 import shared mulberry32 instead of hand-rolling it in gem-elo-calibration.mjs`). Replaced the local definition with `import { mulberry32 } from '@/lib/engine/botSampling';`, the same import `calibration-harness.mjs` already uses. Confirmed algorithmically identical before the swap (the local version's `seed >>> 0` init was redundant since `a |= 0` runs first on every call) and `gem-parity.check.mjs` still passes.

**File:** `scripts/gem-elo-calibration.mjs:191-200`
**Issue:** The file's header explicitly states "Zero reimplementation drift (D-03): every
gem/eval/encoding function below is IMPORTED from the live frontend source ... never
re-derived" (lines 12-13), and `calibration-harness.mjs` does import `mulberry32` from
`@/lib/engine/botSampling` (line 65 of that file). `gem-elo-calibration.mjs`, however, still
defines its own local `mulberry32` for stratified reservoir sampling instead of importing the
same symbol. The two are almost certainly algorithmically identical today, but this is a live
duplication that could silently drift if the frontend implementation ever changes, directly
contradicting this file's own stated invariant.
**Fix:** Replace the local `mulberry32` definition with `import { mulberry32 } from
'@/lib/engine/botSampling';` (same import calibration-harness.mjs already uses).

### WR-06: Silent, uninstrumented fallback when Stockfish reports no "exact" bound during adjudication

**FIXED** — commit `e6f030b6` (`fix(168): WR-06 count and report evalPositionCp's silent neutral-cp fallback`). Added `adjudicationFallbackStats.neutralFallbackCount`, incremented on every fallback and surfaced in `calibration-harness.mjs`'s throughput/spike report (`adjudication neutral fallbacks: N`). Verified live in a real sweep run — the counter reported `0`.

**File:** `scripts/lib/calibration-providers.mjs:158-185` (`evalPositionCp`)
**Issue:** `ADJUDICATION_MOVETIME_MS` is only 500ms (line 63) — short enough that, in a
tactically unstable position, Stockfish's aspiration-window search could plausibly report only
`upperbound`/`lowerbound` info lines the entire time, never an `exact` one. In that case
`lastExact` stays `null` and the function returns `0` (line 177, "should not normally occur") —
silently treating what may be a decisively winning/losing position as neutral for D-10 cutoff 2.
There is no counter or log line tracking how often this fallback fires, so a systematic
occurrence would degrade adjudication accuracy for an entire multi-hour sweep with zero
visibility in the harness's console output or output TSVs.
**Fix:** Increment and report a `neutralFallbackCount` (or similar) alongside the existing
throughput/spike report so a systematic occurrence is visible rather than silent.

## Info

**Not addressed in this fix pass** (`fix_scope: critical_warning`) — IN-01 through IN-05 below remain open. All are noted by the reviewer as low-impact/non-blocking; none were fixed here.

### IN-01: Duplicate literal slack constant

**File:** `scripts/lib/calibration-providers.mjs:57,66`
**Issue:** `SLACK_MS` and `ADJUDICATION_SLACK_MS` are both independently declared as `2500` —
two named constants carrying the identical value with no documented reason they must be allowed
to diverge.
**Fix:** Consider a single shared `WAITFOR_SLACK_MS` constant, or a comment noting they're
allowed to diverge if that's intentional.

### IN-02: `deriveGameSeed`'s uint32 wraparound at very large game indices

**File:** `scripts/calibration-harness.mjs:93-98`
**Issue:** `(seed + gameIndex * SEED_GAME_INDEX_MULTIPLIER) >>> 0` can wrap/collide once
`gameIndex` grows large enough (roughly beyond `2^32 / 1_000_003 ≈ 4293` games), which is far
beyond any realistic single sweep (`--games-per-cell` default 20, largest documented grid ~1440
games) but is unguarded if the harness is ever driven with a much larger `--games-per-cell`.
**Fix:** Non-blocking; note the practical bound in the constant's docstring, or use a
non-multiplicative seed-mixing function if very large sweeps are ever anticipated.

### IN-03: Line buffer doesn't strip a possible trailing `\r`

**File:** `scripts/lib/node-engine-providers.mjs:72-79`
**Issue:** `this.buffer.split('\n')` doesn't account for CRLF output; every exact-string
comparison downstream (`line === 'uciok'`, `line === 'readyok'`) would silently and permanently
fail to match if the vendored engine ever emitted CRLF line endings, hanging every `waitFor`
until its timeout. Currently benign given the vendored build's LF-only stdout on Linux, but
fragile/non-portable.
**Fix:** `.replace(/\r$/, '')` per line, or `.trimEnd()` before comparison.

### IN-04: `invertAnchorElo` produces `NaN`/`-Infinity` if ever called with `games <= 0`

**File:** `scripts/lib/calibration-elo.mjs:36-50`
**Issue:** `clampScore(observedScore, 0)` computes `epsilon = 1/(2*0) = Infinity`, and the
subsequent `Math.min(1 - Infinity, Math.max(Infinity, observedScore))` evaluates to `-Infinity`,
which then makes `Math.log10(1/(-Infinity) - 1)` = `Math.log10(-1)` = `NaN`. The one current call
site (`combineAnchorEstimates`, lines 64-77) guards with `if (games <= 0) continue;` before ever
calling `invertAnchorElo`, so this isn't reachable today, but `invertAnchorElo` is exported and
has no input validation of its own.
**Fix:** Guard `games <= 0` inside `invertAnchorElo` itself (throw or return `null`) rather than
relying on every caller to remember the precondition.

### IN-05: `frontend-alias-hook.mjs`'s extensionless-relative resolution only tries a bare `.ts` sibling

**File:** `scripts/lib/frontend-alias-hook.mjs:62-76`
**Issue:** The fallback only checks `${resolvedNoExt}.ts` — it doesn't try `.tsx` or a
directory's `index.ts`. This is explicitly scoped/documented as intentional for the current
import surface (mctsSearch.ts's sibling set), and the module comment already flags the tripwire
(the gem-parity check), so this is a documented, accepted limitation rather than a hidden defect
— noted here only so a future import of a `.tsx` file or directory-index module under
`frontend/src/lib/engine/` doesn't get mistaken for a hook bug rather than a missing case.
**Fix:** None required now; extend the fallback chain (`.tsx`, `/index.ts`) if/when such an
import is added.

---

_Reviewed: 2026-07-12T05:51:24Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
