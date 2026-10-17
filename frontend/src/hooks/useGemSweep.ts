/**
 * useGemSweep — the background gem-sweep cascade.
 *
 * ─── Fallback-only mechanism ───────────────────────────────────────────────
 *
 * An analyzed game's mainline is not swept: it is rendered directly
 * from the backend's stored `game_best_moves` / `EvalPoint.best_move_tier`
 * data (Analysis.tsx's `storedGemGreatByPly`/`resolveMarkerFor`), which is
 * instant and requires no Maia/Stockfish round-trip. This hook's own
 * candidates (below) are computed from `eval_series`, so its `enabled` gate
 * is ANDed with `!gameHasStoredBestMoveData` at the call site
 * (Analysis.tsx) — the sweep only has real work for a game whose
 * mainline eval data exists but has NOT yet had `best_move_tier` populated.
 * The dedicated-worker machinery below is kept intact, NOT deleted, as the
 * documented fallback for exactly that "no stored tier available" case.
 *
 * Runs the SAME resolution `Analysis.tsx`'s live gem badge already performs
 * (Maia C1 -> Stockfish parent-grade C2), one candidate at a time, AHEAD of
 * the cursor instead of AT it — for every ply that survived the free
 * prefilter (`gemSweep.ts#selectSweepCandidates`).
 *
 * ─── Dedicated hook instances, never merged into one (the load-bearing decision) ─
 *
 * This hook calls `useMaiaEngine` and `useStockfishGradingEngine` itself,
 * driven ONLY by sweep state — dedicated HOOK CALLS, separate from
 * `Analysis.tsx`'s `maia` / `grading` / `gemGrading` calls, each keeping its
 * OWN single-FEN discipline. (Transport is a different axis:
 * the underlying Maia WORKER is one shared
 * instance behind `maiaWorkerHost` — this hook's `useMaiaEngine` call passes
 * `priority: false` and gets its own lease, but on /analysis it is the SAME
 * physical Worker the live chart uses. Stockfish grading remains fully
 * separate; nothing below changes for it.) Two structural reasons the HOOK
 * CALLS cannot be merged into one:
 *
 *  1. `useMaiaEngine` keeps a SINGLE request in flight and re-plans against the
 *     latest inputs on completion, so driving the live curve's instance with a
 *     sweep FEN would occupy that slot and inject the sweep's inference
 *     latency onto the live path.
 *  2. `useStockfishGradingEngine` is a single-FEN state machine with no
 *     queue and no priority (see prepareSearch). Feeding it a
 *     background FEN would make the sweep and the live grade `stop`/re-`go`
 *     each other's in-flight WASM search on every prop change.
 *
 * A dedicated instance makes starvation of the live path STRUCTURALLY
 * impossible instead of merely unlikely.
 *
 * ─── Yield semantics ─────────────────────────────────────────────────────
 *
 * The sweep does NOT abort its in-flight search on every cursor change: a user
 * stepping briskly through the mainline would cancel the
 * sweep continuously and it would never finish. Instead the sweep yields at
 * the DISPATCH gate ONLY — `nextSweepDispatch` (gemSweep.ts) never lets a NEW
 * candidate START while the live path is busy — and the cost of work already
 * started is bounded by `SWEEP_GRADING_MOVETIME_MS` (below). This is safe
 * precisely BECAUSE the workers are dedicated: an in-flight sweep search
 * occupies no resource the live path needs. For the Maia tier specifically,
 * this hook follows the project's own established precedent
 * (`useFlawChessEngine.ts`): "maiaQueue has no stopAll (an in-flight ONNX
 * inference cannot be interrupted) — a stale policy() resolution is unused
 * and harmless." A stale sweep Maia/Stockfish result is simply written to
 * this hook's own map, never forced onto the live display.
 *
 * ─── Cache ───────────────────────────────────────────────────────
 *
 * `gemByPly` is this hook's OWN state, bounded by `candidates.length`
 * (mainline-only) and deliberately NEVER FIFO-capped like
 * `Analysis.tsx`'s `gemByNode`/`maiaCurveByFen` (a 256-entry cap that is a
 * budget SHARED by four maps and free-variation exploration) — a swept
 * move-8 gem must not be evicted before the user reaches move 60.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useMaiaEngine } from './useMaiaEngine';
import { useStockfishGradingEngine } from './useStockfishGradingEngine';
import { FREE_PLAY_DEFAULT_ELO } from './useMaiaEloDefault';
import { isLowPowerDevice } from '@/lib/engine/workerPool';
import { nextSweepDispatch, type SweepCandidate } from '@/lib/gemSweep';
import { classifyGem, summarizeForGem, GEM_MAIA_MAX_PROB, type GemGrade } from '@/lib/gemMove';
import { nearestByElo, selectCandidatesByMass } from '@/lib/moveQuality';
import { sideToMoveFromFen, type MoverColor } from '@/lib/liveFlaw';

// ─── Constants ────────────────────────────────────────────────────────────

/**
 * Sweep-only Stockfish grading movetime cap (ms) — deliberately SMALLER than
 * the live path's `GRADING_MOVETIME_SAFETY_CAP_MS = 4000`
 * (useStockfishGradingEngine.ts). The sweep has no deadline to hit; a shorter
 * cap bounds how long any single background candidate pegs a CPU core,
 * trading grading depth for lower per-candidate wall-clock cost. This is an
 * acceptable trade specifically for the sweep's C2 comparison — a gem
 * requires the played move to beat the runner-up by at least `MISTAKE_DROP`
 * (a large expected-score gap), not a fine one, so a shallower search still
 * resolves it correctly the vast majority of the time. 1000ms is roughly the
 * live free-run's own `MOVETIME_MS` order of magnitude, a deliberately
 * different constant from the live grading
 * path's cap, never a reuse of it.
 */
export const SWEEP_GRADING_MOVETIME_MS = 1000;

/**
 * Per-candidate watchdog cap (ms). A candidate
 * that never resolves — a dead dedicated worker (silent `onerror`), a stuck
 * ONNX inference, a missed terminal `bestmove` — must not pin the single
 * in-flight slot for the rest of the session (the scheduler's first line is
 * `if (inFlight !== null) return;`, so ONE stuck candidate blocks every
 * remaining one). This cap is comfortably larger than a real Maia inference
 * plus `SWEEP_GRADING_MOVETIME_MS`, so it never fires on a merely-slow
 * candidate — only on a genuinely stuck one, which it abandons as an explicit
 * miss so the ascending walk advances.
 */
export const SWEEP_CANDIDATE_TIMEOUT_MS = 30_000;

// ─── Types ────────────────────────────────────────────────────────────────

/** Mirrors Analysis.tsx's private `GemDetail` shape exactly, so the
 *  display merge (sweep-resolved gems + the live per-node resolution) is a
 *  straight union of the two maps' value types. */
export interface SweepGemDetail {
  maiaProbability: number;
  elo: number;
  byOpponent: boolean;
}

export interface UseGemSweepOptions {
  /** Sweep on/off switch (e.g. unanalyzed game, low-power device — folded in below). */
  enabled: boolean;
  /** The game id — resets all sweep state (gemByPly + any in-flight candidate) on change. */
  sweepKey: number | null;
  /** All plies that survived the free prefilter for this game, ascending ply order. */
  candidates: SweepCandidate[];
  /** Each candidate is classified at ITS OWN mover's pinned rung — supplied by the
   *  caller; this hook never reads a slider value. */
  pinnedEloForPly: (plyIndex: number) => number;
  /** True while the live free-run / grading engines are busy on the user's current node. */
  liveBusy: boolean;
  /** The user's color in game mode (null in free-play/no game) — feeds `byOpponent`. */
  userColor: MoverColor | null;
}

export interface UseGemSweepState {
  /** Sweep-resolved gems (confirmed) or explicit misses (null), keyed by ply index.
   *  Bounded by `candidates.length`, never FIFO-capped. */
  gemByPly: Map<number, SweepGemDetail | null>;
  /** True while a candidate is mid-cascade (Maia or Stockfish stage). */
  isSweeping: boolean;
}

/** Which tier of the cascade the in-flight candidate is currently in. */
type SweepStage = 'maia' | 'grade';

/** Captured at the moment C1 passes — the expensive tier's inputs, since
 *  `useMaiaEngine` clears `perElo`/`resultFen` the instant its `fen` prop
 *  goes null (its own debounce effect's fen===null branch), which happens
 *  the moment this hook advances to the 'grade' stage. */
interface GradeContext {
  candidateSans: string[];
  maiaProbability: number;
  pinnedElo: number;
}

// ─── Hook ────────────────────────────────────────────────────────────────

export function useGemSweep({
  enabled,
  sweepKey,
  candidates,
  pinnedEloForPly,
  liveBusy,
  userColor,
}: UseGemSweepOptions): UseGemSweepState {
  const [gemByPly, setGemByPly] = useState<Map<number, SweepGemDetail | null>>(() => new Map());
  const [inFlight, setInFlight] = useState<SweepCandidate | null>(null);
  const [stage, setStage] = useState<SweepStage>('maia');
  const [gradeContext, setGradeContext] = useState<GradeContext | null>(null);
  const [tabHidden, setTabHidden] = useState(() => document.visibilityState === 'hidden');

  // Resolved-ply set (scheduler input + teardown predicate). Declared
  // here — above the engine-enabled computation — because `hasWork` reads it.
  const resolvedPlyIndices = useMemo(() => new Set(gemByPly.keys()), [gemByPly]);

  // Device gate: computed once — a device's core count / pointer
  // type does not change across this hook's lifetime.
  const lowPowerDevice = useMemo(() => isLowPowerDevice(), []);
  const effectiveEnabled = enabled && !lowPowerDevice;
  // "UNRESOLVED candidates remain", NOT
  // `candidates.length > 0`, which would keep both dedicated worker
  // instances (a full Stockfish WASM worker + a multi-MB Maia ONNX model) alive
  // for the entire remaining page lifetime AFTER the sweep had finished. Keying
  // on unresolved-remaining tears both down the moment the last candidate
  // resolves (their cleanup is keyed on `enabled`).
  const hasWork = candidates.some((c) => !resolvedPlyIndices.has(c.plyIndex));
  const engineEnabled = effectiveEnabled && hasWork;

  // Refs-for-latest-value, read inside the idle-callback closure (which must
  // re-check the cursor/live state that may have moved between scheduling
  // and running).
  const liveBusyRef = useRef(liveBusy);
  const effectiveEnabledRef = useRef(effectiveEnabled);
  useEffect(() => {
    liveBusyRef.current = liveBusy;
    effectiveEnabledRef.current = effectiveEnabled;
  });

  // Pending idle-callback handle, cancelled on cleanup/re-schedule.
  const idleHandleRef = useRef<number | null>(null);
  const cancelIdleRef = useRef<((handle: number) => void) | null>(null);

  // ─── Game switch resets all sweep state ──────────────────────────────────

  const prevSweepKeyRef = useRef<number | null>(sweepKey);
  useEffect(() => {
    if (prevSweepKeyRef.current === sweepKey) return;
    prevSweepKeyRef.current = sweepKey;
    setGemByPly(new Map());
    setInFlight(null);
    setStage('maia');
    setGradeContext(null);
  }, [sweepKey]);

  // ─── Tab-hidden pause (mirrors useStockfishGradingEngine.ts / useMaiaEngine.ts) ──

  useEffect(() => {
    function handleVisibility(): void {
      setTabHidden(document.visibilityState === 'hidden');
    }
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // ─── Resolve a candidate: stamp gemByPly and clear in-flight state ───────

  // resolveCandidate touches only
  // stable setState setters (setGemByPly/setInFlight/setStage/setGradeContext),
  // so an empty-dep useCallback identity is correct and stable across
  // renders. A plain function would be re-created every render and called
  // from four effects (C1, C2, watchdog, fast-fail) with NO
  // dependency-array entry and no eslint-disable — a latent stale-closure
  // trap if its body ever grew to read a prop/state closed over from a
  // stale render. So it is a stable reference, listed explicitly in every effect
  // that calls it.
  const resolveCandidate = useCallback((plyIndex: number, detail: SweepGemDetail | null): void => {
    setGemByPly((prev) => {
      if (prev.has(plyIndex)) return prev; // already resolved — first wins
      const next = new Map(prev);
      next.set(plyIndex, detail);
      // Deliberately NOT FIFO-capped — bounded by candidates.length
      // (mainline-only), never Analysis.tsx's shared FIFO-evicted maps.
      return next;
    });
    setInFlight(null);
    setStage('maia');
    setGradeContext(null);
  }, []);

  // ─── Dedicated Maia instance (cheap tier) ────────────────────────────────

  const maiaFen = engineEnabled && inFlight !== null && stage === 'maia' ? inFlight.parentFen : null;
  const maiaSelectedElo = inFlight !== null ? pinnedEloForPly(inFlight.plyIndex) : FREE_PLAY_DEFAULT_ELO;

  const maia = useMaiaEngine({
    fen: maiaFen,
    enabled: engineEnabled,
    // Only perElo (the full per-rung curve) is consumed below — selectedElo
    // only affects the hook's own wdl/expectedScoreAtSelectedElo fields,
    // which this hook never reads (the pinned rung comes from nearestByElo
    // against perElo directly).
    selectedElo: maiaSelectedElo,
    // priority: false — the background sweep shares
    // the /analysis Maia worker host and must yield to the live chart's
    // priority lease; a background sweep candidate queuing behind the live
    // path is the whole point (see the dispatch-gate doc comment above),
    // never the other way around.
    priority: false,
    // ladderOnly: the sweep skips the exact-rung phase and
    // the prefetch — no phase 1/2 round trip. It still goes through the
    // coarse/fill split for phase 3, but the C1 effect below
    // gates on `maia.isLadderComplete`, so gem classification only ever acts
    // once the full 21-rung ladder has landed.
    ladderOnly: true,
  });

  // ─── Dedicated Stockfish grading instance (expensive tier) ───────────────

  const gradeFen = engineEnabled && inFlight !== null && stage === 'grade' ? inFlight.parentFen : null;

  const grading = useStockfishGradingEngine({
    fen: gradeFen,
    candidateSans: gradeContext?.candidateSans ?? [],
    enabled: engineEnabled,
    movetimeMs: SWEEP_GRADING_MOVETIME_MS,
  });

  // ─── C1: Maia completion -> pass to grade stage, or resolve a miss ───────

  useEffect(() => {
    // WAIT-FOR-COMPLETE: gem classification must never act on a coarse
    // (11-rung) ladder. `resultFen` matching alone is not enough, since it
    // matches while the ladder is still partial.
    if (inFlight === null || stage !== 'maia' || !maia.isLadderComplete) return;
    // Guard: only act once the displayed curve actually belongs to the
    // in-flight candidate's parent FEN — never key on this hook's own
    // "current" value.
    if (maia.resultFen !== inFlight.parentFen) return;

    const pinnedElo = pinnedEloForPly(inFlight.plyIndex);
    const rung = nearestByElo(maia.perElo, pinnedElo);
    const maiaProbability = rung?.moveProbabilities[inFlight.playedSan] ?? null;

    if (maiaProbability === null || maiaProbability > GEM_MAIA_MAX_PROB) {
      // C1 fail — the cheap tier's whole purpose: Stockfish is NEVER invoked
      // for this ply.
      resolveCandidate(inFlight.plyIndex, null);
      return;
    }

    // C1 pass — capture what C2 needs NOW (maia.perElo/resultFen reset the
    // instant maiaFen goes null on the next commit) and hand off to the
    // expensive tier.
    setGradeContext({
      candidateSans: selectCandidatesByMass(maia.perElo, pinnedElo, inFlight.playedSan, null),
      maiaProbability,
      pinnedElo,
    });
    setStage('grade');
  }, [inFlight, stage, maia.resultFen, maia.perElo, maia.isLadderComplete, pinnedEloForPly, resolveCandidate]);

  // ─── C2: grade completion -> classifyGem, resolve gem or miss ────────────

  useEffect(() => {
    if (inFlight === null || stage !== 'grade' || gradeContext === null) return;
    // Same guard as the C1 effect above.
    if (grading.gradeMapFen !== inFlight.parentFen) return;
    if (grading.isGrading) return;
    if (grading.gradeMap.size === 0) return;

    const gradeBySan = new Map<string, GemGrade>();
    for (const [san, g] of grading.gradeMap) {
      gradeBySan.set(san, { evalCp: g.evalCp, evalMate: g.evalMate });
    }
    const mover = sideToMoveFromFen(inFlight.parentFen);
    const { bestSan, bestEs, secondBestEs } = summarizeForGem(gradeBySan, mover);
    const isGem = classifyGem({
      maiaProbability: gradeContext.maiaProbability,
      playedIsBest: bestSan === inFlight.playedSan,
      bestEs,
      secondBestEs,
    });
    const byOpponent = userColor != null && mover !== userColor;
    const detail: SweepGemDetail | null = isGem
      ? { maiaProbability: gradeContext.maiaProbability, elo: gradeContext.pinnedElo, byOpponent }
      : null;
    resolveCandidate(inFlight.plyIndex, detail);
  }, [
    inFlight,
    stage,
    gradeContext,
    grading.gradeMap,
    grading.gradeMapFen,
    grading.isGrading,
    userColor,
    resolveCandidate,
  ]);

  // ─── Per-candidate watchdog — never let one candidate pin the queue ─

  useEffect(() => {
    if (inFlight === null) return;
    const plyIndex = inFlight.plyIndex;
    // Abandon a candidate that never resolves (dead worker, stuck inference,
    // missed terminal bestmove) as an explicit miss, so the single-in-flight
    // scheduler advances instead of deadlocking for the rest of the session.
    // Re-armed on every inFlight change; resolveCandidate is a stable
    // useCallback([]) identity, listed below.
    const timer = window.setTimeout(() => {
      resolveCandidate(plyIndex, null);
    }, SWEEP_CANDIDATE_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [inFlight, resolveCandidate]);

  // ─── Fast failure path — abandon a candidate whose dedicated engine
  //     reported a silent worker-load failure, without waiting out the watchdog.

  useEffect(() => {
    if (inFlight === null) return;
    const failed = stage === 'maia' ? maia.hasFailed : grading.hasFailed;
    if (failed) resolveCandidate(inFlight.plyIndex, null);
  }, [inFlight, stage, maia.hasFailed, grading.hasFailed, resolveCandidate]);

  // ─── Scheduler: decide whether to dispatch the next candidate ────────────

  useEffect(() => {
    if (inFlight !== null) return; // one candidate at a time — already busy

    const decision = nextSweepDispatch({
      candidates,
      resolvedPlyIndices,
      inFlight,
      liveBusy,
      tabHidden,
      enabled: effectiveEnabled,
    });
    // 'idle' ("nothing to dispatch
    // right now — yielding, disabled, or hidden") and 'done' ("every
    // candidate has been resolved") are deliberately NOT distinguished here.
    // Both are simple no-ops for this scheduler effect — nothing downstream
    // reads which one occurred (UseGemSweepState exposes gemByPly/isSweeping,
    // neither of which needs a "sweep fully finished" flag), so branching on
    // the distinction would add a dead code path. `resolvedPlyIndices.size`
    // is already the "how much is done" signal a future caller could use.
    if (decision.kind !== 'dispatch') return;

    const candidate = decision.candidate;

    // requestIdleCallback is not implemented in every Safari
    // version — feature-detect, no existing in-repo precedent to copy.
    const scheduleIdle: (cb: () => void) => number =
      typeof window.requestIdleCallback === 'function'
        ? (cb) => window.requestIdleCallback(cb)
        : (cb) => window.setTimeout(cb, 1);
    const cancelIdle: (handle: number) => void =
      typeof window.cancelIdleCallback === 'function'
        ? (handle) => window.cancelIdleCallback(handle)
        : (handle) => window.clearTimeout(handle);
    cancelIdleRef.current = cancelIdle;

    const handle = scheduleIdle(() => {
      idleHandleRef.current = null;
      // Re-check the cursor/live state — it may have moved between
      // scheduling and this callback actually running.
      if (!liveBusyRef.current && effectiveEnabledRef.current) {
        setInFlight(candidate);
        setStage('maia');
      }
    });
    idleHandleRef.current = handle;

    return () => {
      if (idleHandleRef.current !== null) {
        cancelIdleRef.current?.(idleHandleRef.current);
        idleHandleRef.current = null;
      }
    };
  }, [inFlight, candidates, resolvedPlyIndices, liveBusy, tabHidden, effectiveEnabled]);

  return { gemByPly, isSweeping: inFlight !== null };
}
