---
id: SEED-107
status: superseded
planted: 2026-07-15
planted_during: v2.3 (post Phase 172 / SEED-106)
trigger_when: next analysis-board reliability pass, or when a user reports a gem move that never gets badged without dwelling on it
scope: medium
superseded_by: SEED-108 (backend gem detection — preferred strategy; this client-side fix is the tactical fallback if the backend approach is deferred)
---

> **Strategy note:** [[SEED-108]] proposes moving gem detection to the backend
> full-game analysis pass (Maia on remote workers, gems stored as a peer to
> flaws). That is the preferred direction and would retire the client-side
> sweep entirely. Keep THIS seed only as the short-term fix if SEED-108 is
> deferred.

# SEED-107: Background gem sweep is starved by the always-on live analysis engines

## Why This Matters

The background gem sweep shipped in Phase 172 (SEED-106) was supposed to remove
the dwell requirement — gems should appear across the whole game shortly after
the analysis board opens, without the user parking the cursor on each move. In
practice it never delivers: gems only ever appear via the **live dwell path**
(`gemByNode`), which grades the specific node the cursor rests on. Reported
repro (game_id=1715764, ply 81, move 42.g4, a +16.6 vs +2.4 clear best move):

- Open the board, wait a long time without touching the cursor → g4 is NOT
  badged.
- Reload, park the cursor on g4, wait → g4 IS badged (live path grades it).
- Step over g4 quickly and back → never badged.
- Reproduces on **Android phone AND a powerful dev laptop** — so it is not
  merely the device gate.

## Root-Cause Hypothesis (needs confirmation)

The sweep's yield-to-cursor scheduler bails the instant any live engine is busy:

`nextSweepDispatch` (`frontend/src/lib/gemSweep.ts:148`): `if (liveBusy) return { kind: 'idle' }`.

`liveBusy` is fed by `liveEnginesBusy` (`frontend/src/pages/Analysis.tsx:1650-1655`):

```
const liveEnginesBusy =
    engine.isAnalyzing ||          // live Stockfish eval
    maia.isAnalyzing ||
    grading.isGrading ||
    flawChessEngine.isSearching ||
    needParentGemGrade;
```

That guard assumes the live engines go **quiet** when the user stops
navigating. But an analysis board keeps the live Stockfish eval (and/or the
FlawChess engine) analyzing the **current** position continuously for as long
as the cursor sits there. So `liveEnginesBusy` is effectively **always true**
whenever a position is open, and the sweep never gets an idle window on ANY
device. "Waiting" does not help because waiting is exactly when the live engine
is churning on the current position.

The linchpin to verify in a debug session: log `liveEnginesBusy` (and each of
its terms) while the board is open and idle — confirm at least one term stays
`true` indefinitely.

### Compounding factor (phone only)

`isLowPowerDevice()` (`frontend/src/lib/engine/workerPool.ts:193-198`) disables
the sweep entirely on coarse-pointer / low-core devices
(`effectiveEnabled = enabled && !lowPowerDevice`, `useGemSweep.ts:169`). On the
phone (and any touchscreen laptop) the sweep is off regardless of the
starvation bug — the live dwell path is the ONLY route to a gem there.

## Design Question the Fix Must Answer

The current design fully yields the sweep to any busy live engine. Options:

1. **Yield only to genuine user navigation, not to steady-state background
   analysis.** Give the sweep a real CPU budget that coexists with the live
   eval (it already has its own dedicated Maia + Stockfish worker instances),
   distinguishing "user just moved the cursor" from "live engine is deep-idling
   on a parked position."
2. **Precompute gems server-side / at analysis time** rather than sweeping in
   the browser at all — removes the client CPU contention entirely.
3. **Narrow the busy signal** — drop the always-on `engine.isAnalyzing` /
   `flawChessEngine.isSearching` terms from `liveBusy` and yield only to the
   short-lived live-gem-grade window (`needParentGemGrade`) + active Maia.

## Breadcrumbs

- `frontend/src/lib/gemSweep.ts:144-159` — `nextSweepDispatch`, the yield-to-cursor guard.
- `frontend/src/pages/Analysis.tsx:1650-1655` — `liveEnginesBusy` composition (the suspect).
- `frontend/src/pages/Analysis.tsx:1666-1673` — `useGemSweep` call and `enabled` gate.
- `frontend/src/hooks/useGemSweep.ts:168-177, 344-388` — device gate + scheduler effect.
- `frontend/src/lib/engine/workerPool.ts:193-198` — `isLowPowerDevice` (phone/touchscreen gate).
- `frontend/src/lib/gemSweep.ts:56-83` — `selectSweepCandidates` (walks ALL plies past the book, not "ahead of the cursor"; g4 IS a candidate).
- `.planning/seeds/closed/SEED-106-background-gem-sweep-on-analysis.md` — the sweep this defect is in.

## Notes

Also worth addressing while here: even when the live dwell path DOES badge a
gem, `gemByNode` is FIFO-capped and cleared on navigation reset
(`Analysis.tsx:2126, 2133`), so a live-detected gem can be evicted and must be
re-earned by re-dwelling. And the sweep resets on reload (`useGemSweep.ts:196-203`)
— it re-sweeps every load rather than persisting.
