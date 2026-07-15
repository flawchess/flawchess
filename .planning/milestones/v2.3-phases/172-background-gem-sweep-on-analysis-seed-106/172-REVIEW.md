---
phase: 172-background-gem-sweep-on-analysis-seed-106
reviewed: 2026-07-15T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - app/schemas/library.py
  - app/services/library_service.py
  - app/services/opening_lookup.py
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
  - frontend/src/components/board/__tests__/boardMarkers.test.tsx
  - frontend/src/components/board/boardMarkers.tsx
  - frontend/src/components/icons/BookIcon.tsx
  - frontend/src/hooks/__tests__/useGemSweep.test.ts
  - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts
  - frontend/src/hooks/useGemSweep.ts
  - frontend/src/hooks/useMaiaEloDefault.ts
  - frontend/src/hooks/useStockfishGradingEngine.ts
  - frontend/src/lib/__tests__/gemMove.test.ts
  - frontend/src/lib/__tests__/gemSweep.test.ts
  - frontend/src/lib/bookGlyph.ts
  - frontend/src/lib/engine/workerPool.ts
  - frontend/src/lib/gemMove.ts
  - frontend/src/lib/gemSweep.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
  - frontend/src/types/library.ts
  - tests/services/test_library_service.py
  - tests/test_opening_lookup.py
findings:
  critical: 3
  warning: 6
  info: 4
  total: 13
resolved:
  - CR-01
  - CR-02
  - CR-03
  - WR-02
  - WR-04
deferred:
  - WR-01
  - WR-03
  - WR-05
  - WR-06
  - IN-01
  - IN-02
  - IN-03
  - IN-04
status: partially_resolved
---

# Phase 172: Code Review Report

> **Resolution (2026-07-15):** The 3 Critical findings (CR-01, CR-02, CR-03) plus
> the worker-leak warning (WR-02) were fixed on branch
> `gsd/phase-172-background-gem-sweep-on-analysis-seed-106` in commits
> `1a34da33`, `fbd04ff0`, `d79e9a4e`, `6a94d98a` (+ `019b4934` lint follow-up).
> Each was proven with a genuine RED→GREEN revert. **WR-04 was fixed separately in
> quick task 260715-als** (the book fold now defers only to entries that draw a
> move-list glyph, so an inaccuracy-only book ply renders its book badge). WR-01,
> WR-03, WR-05, WR-06 and all Info findings remain deferred (see the deferred-findings
> todo).

**Reviewed:** 2026-07-15
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

The backend half (`find_opening_ply_count`, `opening_ply_count` on `GameFlawCard`) is correct: index alignment between `moves` and `eval_series` holds (`moves_data` drops only the trailing `move_san IS NULL` terminal row), `best_move` on `game_positions[i]` really is the engine best from the position *before* move `i`, and the openings TSV shares python-chess's SAN dialect (`+`, `O-O`) so the trie walk matches. The `sanToUci` prefilter and the book gate (`i < openingPlyCount`) are right, and `gemSweep.ts` is a clean pure module.

The frontend sweep is where the defects are, and they cluster on one theme: **the sweep and the live gem path are wired together as if they were interchangeable, and they are not.** Three concrete issues:

1. A `??` on a `Map<K, T | null>` cannot distinguish "unresolved" from "resolved: not a gem", so the sweep can overrule an explicit live rejection — directly contradicting the comment sitting on top of it.
2. The D-05 yield-to-cursor guard is fed `needParentGemGrade`, not "the live engines are busy". The pure function is proven by a good test; the *wiring* is not — a textbook half-invariant.
3. The in-flight candidate has no failure path at all. One stuck candidate silently kills the sweep for the whole session, and there is no `worker.onerror` on either dedicated engine hook.

## Critical Issues

### CR-01: `??` lets the sweep overrule an explicit live "not a gem" verdict

**File:** `frontend/src/pages/Analysis.tsx:2280-2287`

**Issue:** `gemByNode` and `sweep.gemByPly` are both `Map<K, GemDetail | null>`, where `null` is a *load-bearing* value meaning "graded and rejected — not a gem". The board-marker memo resolves them with `??`:

```ts
const gemHere =
  currentNodeId !== null
    ? gemByNode.get(currentNodeId) ??
      (currentMainlinePly >= 0 ? sweep.gemByPly.get(currentMainlinePly) : undefined)
    : undefined;
```

`null ?? X` evaluates to `X`. So when the live path has already graded this node and **rejected** it (`gemByNode.set(id, null)`), the expression falls straight through to `sweep.gemByPly`. The comment three lines above states the exact opposite:

> "sweep.gemByPly is the FALLBACK only, never consulted while gemByNode already has an answer for this node."

This is reachable: the user navigates to mainline ply P before the sweep's ascending walk reaches it, the live path grades P at `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` and stamps `null`; the sweep later re-grades the same ply at `SWEEP_GRADING_MOVETIME_MS = 1000` (the sweep's `resolvedPlyIndices` is its own map — it never consults `gemByNode`, see WR-05), gets a different `bestSan`/`secondBestEs` at the shallower depth, and stamps a gem. The board then paints a violet gem badge on a move the deeper live search explicitly rejected.

The adjacent claim that the two "agree by construction since both use the same pinned rung (D-01)" is false. D-01 pins the *Maia rung* (C1). C2 is a Stockfish comparison whose result depends on search depth, and this phase deliberately gives the sweep a 4× shorter movetime.

**Fix:** use `has()` to distinguish absent from null, matching the documented precedence:

```ts
const gemHere =
  currentNodeId !== null && gemByNode.has(currentNodeId)
    ? gemByNode.get(currentNodeId)
    : currentMainlinePly >= 0
      ? sweep.gemByPly.get(currentMainlinePly)
      : undefined;
```

Note the move-list fold (`moveListMarkers`, lines 1788-1801) has the same asymmetry by a different route: it skips `null` from `gemByNode` and then unconditionally folds the sweep's gems, so a live-rejected node still gets a gem badge there too. Fix both, or make the precedence explicit in one shared helper.

---

### CR-02: the D-05 yield-to-cursor guard is wired to the wrong signal — the invariant is inert

**File:** `frontend/src/pages/Analysis.tsx:1604-1611`, contract at `frontend/src/hooks/useGemSweep.ts:104-107` and `frontend/src/lib/gemSweep.ts:94-95`

**Issue:** Both `UseGemSweepOptions.liveBusy` and `SweepDispatchInput.liveBusy` document the same contract, verbatim:

> "True while the live free-run / grading engines are busy on the user's current node."

The only call site passes something else:

```ts
const sweep = useGemSweep({
  ...
  liveBusy: needParentGemGrade,   // NOT "the live engines are busy"
});
```

`needParentGemGrade` is true only while the **live gem C2 confirmation** is pending — and Analysis.tsx's own comment on `gemC1` says "gems are rare by construction, so this passes infrequently." Meanwhile `engine` (free-run Stockfish), `grading` (the shared grading worker), `maia`, and `flawChessEngine` (a 2-4 worker Stockfish pool + its own Maia queue) are *all* searching on every cursor move, and `nextSweepDispatch` is blind to every one of them. The sweep therefore dispatches new Maia inference + a Stockfish `go` into that storm on essentially every navigation.

The dedicated-worker argument in `useGemSweep.ts`'s header ("an in-flight sweep search occupies no resource the live path needs") is only true of *worker slots*. It is false of CPU: the sweep adds a WASM Stockfish search and an ONNX inference to a machine already running up to 7-8 engine threads. `isLowPowerDevice()` only excludes ≤4-core / coarse-pointer devices; a 6-core laptop is fully exposed.

This is exactly the half-invariant shape the project's own mutation-test discipline warns about: `gemSweep.test.ts`'s "LOAD-BEARING (D-05 yield-to-cursor invariant)" test proves the *pure function* yields when `liveBusy` is true, and `useGemSweep.test.ts` proves the *hook* honours the prop. Neither test can see that the prop is fed a signal that is almost never true. Deleting the guard would still leave both tests green in practice.

**Fix:** pass a signal that actually means what the type says, e.g.

```ts
const liveEnginesBusy =
  engine.isAnalyzing ||
  grading.isGrading ||
  maia.isAnalyzing ||
  flawChessEngine.isSearching ||   // whatever the FC hook exposes
  needParentGemGrade;

const sweep = useGemSweep({ ..., liveBusy: liveEnginesBusy });
```

If yielding on the full set is judged too aggressive (the free run restarts on every navigation), then *change the documented contract on both interfaces* and rename the prop to what it is (`liveGemGradePending`) — do not leave a type doc asserting an invariant the wiring does not provide.

---

### CR-03: a single failed candidate permanently stalls the sweep — no failure path, no `worker.onerror`

**File:** `frontend/src/hooks/useGemSweep.ts:240-343`; `frontend/src/hooks/useStockfishGradingEngine.ts:335-437`; `frontend/src/hooks/useMaiaEngine.ts` (worker lifecycle)

**Issue:** `inFlight` is cleared in exactly one place — `resolveCandidate` — which is only reachable from the two success paths:

* C1 (line 240): requires `maia.resultFen === inFlight.parentFen`.
* C2 (line 271): requires `grading.gradeMapFen === inFlight.parentFen && !grading.isGrading && grading.gradeMap.size > 0`.

There is no timeout, no watchdog, no error branch. If either condition never becomes true, `inFlight` stays pinned forever, and the scheduler's first line (`if (inFlight !== null) return;`) blocks every remaining candidate for the rest of the session. `isSweeping` stays `true` forever too.

This is not hypothetical. I grepped all three engine hooks:

```
grep -n "onerror" src/hooks/useMaiaEngine.ts src/hooks/useStockfishGradingEngine.ts src/hooks/useStockfishEngine.ts
# (no matches)
```

None of them install a `worker.onerror` handler. `workerPool.ts` added one *specifically* for this class of failure and says so in its own comment (lines 347-350):

> "an async script-load failure (404, CSP block, syntax error) never throws a catchable JS exception on the main thread — it only surfaces here. Without this handler such a failure is completely silent and any in-flight/future request on this slot hangs forever."

For the live hooks a silent worker death degrades to "no engine output" and self-heals on the next navigation. The sweep is the first consumer that can *deadlock* on it: no `uciok` → `isReady` never flips → `prepareSearch` never runs → `gradeMap` stays empty → `inFlight` pinned. Same for a Maia worker that never reports `ready`.

Related second-order stall: `useStockfishGradingEngine`'s `bestmove` handler does **not** call `setIsGrading(false)` on the `stopPending` branch (line 404-417). If the stop was issued by the tab-hide handler and the terminal `bestmove` arrives while still hidden, no re-`go` is issued and `isGrading` is left `true` — which the sweep's C2 guard reads as "still working". It recovers on the next `visibilitychange`, but it is another way for the sweep to sit in a state it has no timeout out of.

**Fix:** (a) add `worker.onerror` to `useStockfishGradingEngine` and `useMaiaEngine` (mirroring `workerPool.createSlot`, incl. `Sentry.captureException`) and surface it as a hook-level `hasFailed` flag; (b) add a per-candidate watchdog in `useGemSweep` so a candidate cannot pin the queue:

```ts
const SWEEP_CANDIDATE_TIMEOUT_MS = 30_000; // >> Maia inference + SWEEP_GRADING_MOVETIME_MS

useEffect(() => {
  if (inFlight === null) return;
  const t = window.setTimeout(() => {
    // Abandon this candidate: stamp it as an explicit miss so the walk advances.
    resolveCandidate(inFlight.plyIndex, null);
  }, SWEEP_CANDIDATE_TIMEOUT_MS);
  return () => window.clearTimeout(t);
}, [inFlight]);
```

Also fix `setIsGrading(false)` on the `stopPending` bestmove branch when no re-`go` is issued.

## Warnings

### WR-01: the sweep's shallower grade permanently suppresses the live path's deeper grade

**File:** `frontend/src/pages/Analysis.tsx:1548-1553`

**Issue:**

```ts
const needParentGemGrade =
  gemC1 !== null &&
  currentNodeId !== null &&
  !gemByNode.has(currentNodeId) &&
  !(currentMainlinePly >= 0 && sweepResolvedPlies.has(currentMainlinePly));
```

Once the sweep has answered a mainline ply — at `SWEEP_GRADING_MOVETIME_MS = 1000` — the live path will **never** grade it, even though the live path uses the 4000 ms cap that Phase 158 measured for depth-parity. So a genuine gem that the deeper live grade would have confirmed is now permanently hidden because the shallower background grade rejected it. Gem detection on mainline plies got strictly *less* accurate than Phase 163, which is the opposite of this phase's intent.

The doc comment defending the 1000 ms cap ("a gem requires the played move to beat the runner-up by at least `MISTAKE_DROP` … so a shallower search still resolves it correctly the vast majority of the time") concedes it is not always right — and the design then makes the shallow answer *final*.

**Fix:** either (a) make the sweep's verdict provisional — allow the live path to re-grade a swept ply the user actually visits, and let the deeper result overwrite `sweep.gemByPly` (or write it into `gemByNode`, which already wins); or (b) raise `SWEEP_GRADING_MOVETIME_MS` to the live cap so the two verdicts are genuinely interchangeable and the whole precedence question dissolves.

---

### WR-02: the dedicated Maia + Stockfish workers are never terminated after the sweep completes

**File:** `frontend/src/hooks/useGemSweep.ts:152-154, 217-236`

**Issue:**

```ts
const hasWork = candidates.length > 0;
const engineEnabled = effectiveEnabled && hasWork;
```

`hasWork` is `candidates.length > 0`, not "unresolved candidates remain". Once every candidate has resolved, `engineEnabled` is *still* `true`, so both dedicated instances stay alive: a full Stockfish WASM worker plus a Maia ONNX worker holding a multi-MB model, idle, for the entire remaining lifetime of the page — on top of the 4 live engine instances and the FlawChess pool's 2-4 workers. The termination path (`useStockfishGradingEngine`'s cleanup at line 431, `useMaiaEngine`'s equivalent) exists and is keyed on `enabled`; it is simply never triggered.

**Fix:** the "unresolved remain" predicate is already computed one line away:

```ts
const hasWork = candidates.some((c) => !resolvedPlyIndices.has(c.plyIndex));
const engineEnabled = effectiveEnabled && hasWork;
```

(Move `resolvedPlyIndices` above the engine calls.) This tears both workers down the moment the sweep finishes.

---

### WR-03: `sweepCandidates` is recomputed on every move-tree mutation, churning the scheduler

**File:** `frontend/src/pages/Analysis.tsx:1567-1576`

**Issue:** `sweepCandidates` depends on `fenAtPly`, which is a `useCallback` over `[mainLine, nodes, rootFen]`. `nodes` is a `Map` whose identity changes on **every** `makeMove`, `insertPvLine`, and `deleteSubtree` — i.e. every free move the user plays and every tactic-chip graft. Each such mutation:

* re-runs `selectSweepCandidates` over the entire mainline (N × `new Chess(fen)` + N × `sanToUci` — a full chess.js replay), and
* produces a **new `candidates` array identity**, which is a dependency of the scheduler effect (line 343), which cancels the pending idle callback and re-schedules it.

Neither `mainLine` nor the mainline nodes' FENs can change without a `loadMainLine`, so all of this work is pure waste. Under rapid sideline play the cancel/reschedule churn can also repeatedly push back dispatch of the next candidate.

**Fix:** derive the parent-FEN list once from `mainLine`, so it does not track `nodes` identity:

```ts
const mainLineParentFens = useMemo<(string | null)[]>(
  () => mainLine.map((_, i) => (i === 0 ? rootFen : (nodes.get(mainLine[i - 1]!)?.fen ?? null))),
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mainline node FENs are immutable after loadMainLine
  [mainLine, rootFen],
);
const fenAtPly = useCallback((i: number) => mainLineParentFens[i] ?? null, [mainLineParentFens]);
```

---

### WR-04: any existing flaw entry suppresses the book badge — including inaccuracies, which render no icon at all

**File:** `frontend/src/pages/Analysis.tsx:1812-1826`

**Issue:** The book fold guards with:

```ts
const existing = merged.get(nodeId);
if (existing?.severity != null || existing?.gem === true) return;
```

But `flawMarkerByNodeId` (line 1289) creates an entry whenever the ply has *a motif OR* a blunder/mistake — and it always sets `severity: sev`, which may be `'inaccuracy'`. Meanwhile `resolveMarkerIcon` (`VariationTree.tsx:73-83`) renders an icon **only** for `blunder`/`mistake`. Net result: a book ply carrying a tactic motif at inaccuracy severity renders **no badge at all** — not the severity glyph (there isn't one), not the book badge (suppressed).

That directly contradicts the precedence comment added in this phase:

> "a book move can still be an inaccuracy (ECO includes plenty of dubious gambits), and in that case the user needs to see the flaw, not the reassurance that it was theory."

The user sees neither. (The board path is fine — `boardMarkers.tsx` renders `SEVERITY_GLYPH['inaccuracy']` as `!?`, so the two surfaces also disagree with each other.)

**Fix:** match the guard to what `resolveMarkerIcon` actually renders:

```ts
const showsSeverityIcon =
  existing?.severity === 'blunder' || existing?.severity === 'mistake';
if (showsSeverityIcon || existing?.gem === true) return;
```

---

### WR-05: the sweep duplicates grading work the live path has already done

**File:** `frontend/src/hooks/useGemSweep.ts:210, 299-343`

**Issue:** `resolvedPlyIndices` is built from the sweep's **own** `gemByPly` only. The sweep has no visibility into `gemByNode`, so it happily re-runs the full Maia + Stockfish cascade on a mainline ply the live path already resolved (which happens whenever the user navigates ahead of the sweep's ascending walk). That is wasted engine time on the exact machine the sweep is supposed to be gentle on, and — per CR-01 — it is the mechanism by which the two verdicts diverge in the first place.

**Fix:** pass the live path's resolved mainline plies into the hook and union them into the skip set:

```ts
// Analysis.tsx
const liveResolvedPlies = useMemo(() => {
  const s = new Set<number>();
  for (const nodeId of gemByNode.keys()) {
    const i = mainLine.indexOf(nodeId);
    if (i >= 0) s.add(i);
  }
  return s;
}, [gemByNode, mainLine]);
// -> useGemSweep({ ..., alreadyResolvedPlies: liveResolvedPlies })
```

---

### WR-06: `useGemSweep`'s effects call `resolveCandidate` without it being in any dependency array

**File:** `frontend/src/hooks/useGemSweep.ts:194-206, 267, 295`

**Issue:** `resolveCandidate` is a plain function re-created on every render and called from both cascade effects, but appears in neither dependency array and carries no `eslint-disable` justifying the omission. It happens to be safe today because its body touches only stable `setState` setters — but that is a load-bearing invariant with nothing pinning it: adding a single prop/state read to `resolveCandidate` (e.g. `userColor` for a byOpponent tweak) would silently make both effects capture a stale copy, and neither the linter nor the tests would notice.

Every other closure in this file is deliberately routed through a ref for exactly this reason (`liveBusyRef`, `effectiveEnabledRef`, `cancelIdleRef`).

**Fix:** wrap it in `useCallback([])` (its body already only uses stable setters) and add it to both effects' dependency arrays, so the "reads nothing unstable" property is enforced rather than assumed.

## Info

### IN-01: `resolveMarkerIcon`'s `isBook` return field is never read

**File:** `frontend/src/components/analysis/VariationTree.tsx:71, 78, 81-83` (produced) vs `:99` (consumed)

The only caller destructures `const { show, Icon, isGem } = resolveMarkerIcon(flaw);`. `isBook` is computed on all four branches and thrown away — `Icon` already carries the distinction. Dead field; drop it or use it.

---

### IN-02: `UseGemSweepState.isSweeping` is never consumed

**File:** `frontend/src/hooks/useGemSweep.ts:117, 345`

`Analysis.tsx` only reads `sweep.gemByPly`. `isSweeping` is dead public API (knip checks module exports, not object fields, so CI will not catch it). Either surface it (a subtle "sweeping…" indicator was arguably the point) or remove it.

---

### IN-03: `SweepDispatch`'s `done` variant is indistinguishable from `idle` at its only call site

**File:** `frontend/src/lib/gemSweep.ts:101-104` vs `frontend/src/hooks/useGemSweep.ts:310`

`if (decision.kind !== 'dispatch') return;` collapses `done` and `idle` into the same no-op. The discriminant is tested (`returns done when every candidate is resolved`) but carries no information anywhere in production. It *would* be useful as the trigger for WR-02's worker teardown — wire it up or drop the variant.

---

### IN-04: book fold synthesizes `ply: -1` when the real ply index is in hand

**File:** `frontend/src/pages/Analysis.tsx:1822-1827`

The fresh `FlawMarkerEntry` created for a book-only node uses `ply: -1`, even though `plyIndex` is the loop variable one line above. `FlawMarkerEntry.ply` is documented as "passed to onPvChipClick for the useTacticLines fetch key". It is latent today (the chip only renders when a motif exists), and `-1` matches the existing `addLive`/`addGem` placeholder convention — but here the correct value is free. Use `ply: plyIndex`.
</content>
</invoke>
