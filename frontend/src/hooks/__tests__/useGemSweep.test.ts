// @vitest-environment jsdom
/**
 * useGemSweep unit tests — hook-level contention, isolation, and cache-bound
 * proof (Phase 172 Plan 04, Task 3).
 *
 * `@/hooks/useMaiaEngine` and `@/hooks/useStockfishGradingEngine` are mocked
 * so every call's options are captured into an array — this is what makes
 * "the sweep did not start work" observable, mirroring
 * `Analysis.test.tsx`'s existing module-wide mocking convention for the same
 * two hooks. `@/lib/engine/workerPool`'s `isLowPowerDevice` is also mocked so
 * the mobile gate is deterministic regardless of the CI runner's reported
 * `hardwareConcurrency`.
 *
 * Per 172-VALIDATION.md's Half-Invariant Risk section and the project's own
 * mutation-test-gap-closure discipline: a test that merely asserts "the
 * sweep resolves gems" proves NOTHING about D-05. The yield case below is
 * the load-bearing one — its revert-and-fail-red proof is recorded in
 * 172-04-SUMMARY.md, not just asserted here.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { SweepCandidate } from '@/lib/gemSweep';

// ─── Mocks ───────────────────────────────────────────────────────────────────

interface MaiaCallOptions {
  fen: string | null;
  enabled: boolean;
  selectedElo: number;
}
interface GradingCallOptions {
  fen: string | null;
  candidateSans: string[];
  enabled: boolean;
  movetimeMs?: number;
}

const maiaCalls: MaiaCallOptions[] = [];
const gradingCalls: GradingCallOptions[] = [];

/** Mutable per-test Maia stub state — a single shared curve, keyed by SAN,
 *  applied regardless of which FEN is requested (the mock doesn't need real
 *  per-position data, only per-SAN probabilities the test controls).
 *  `ready: false` simulates an inference still in flight — `resultFen` stays
 *  null even once `fen` is set, so a test can observe the fen the hook
 *  DISPATCHED before the mock lets the cascade resolve it and move on. */
const maiaState: {
  perElo: { elo: number; moveProbabilities: Record<string, number> }[];
  ready: boolean;
} = { perElo: [], ready: true };

vi.mock('@/hooks/useMaiaEngine', () => ({
  useMaiaEngine: (options: MaiaCallOptions) => {
    maiaCalls.push(options);
    return {
      perElo: maiaState.perElo,
      expectedScoreAtSelectedElo: null,
      wdl: null,
      isReady: true,
      isAnalyzing: false,
      hasFailed: false,
      // WR-03 mock convention (mirrors Analysis.test.tsx): a completed result
      // is "for" whatever fen was requested, once the stub curve is non-empty
      // AND the test has flipped `ready` (simulating inference completion).
      resultFen: options.fen !== null && maiaState.perElo.length > 0 && maiaState.ready ? options.fen : null,
    };
  },
}));

/** Mutable per-test grading stub state — same `ready` gate as `maiaState`. */
const gradingState: {
  gradeMap: Map<string, { evalCp: number | null; evalMate: number | null; depth: number }>;
  isGrading: boolean;
  ready: boolean;
} = { gradeMap: new Map(), isGrading: false, ready: true };

vi.mock('@/hooks/useStockfishGradingEngine', () => ({
  useStockfishGradingEngine: (options: GradingCallOptions) => {
    gradingCalls.push(options);
    return {
      gradeMap: gradingState.gradeMap,
      gradeMapFen:
        options.fen !== null && gradingState.gradeMap.size > 0 && gradingState.ready ? options.fen : null,
      isGrading: gradingState.isGrading,
      isReady: true,
      hasFailed: false,
    };
  },
}));

let lowPowerDevice = false;
vi.mock('@/lib/engine/workerPool', () => ({
  isLowPowerDevice: () => lowPowerDevice,
}));

import {
  useGemSweep,
  SWEEP_GRADING_MOVETIME_MS,
  SWEEP_CANDIDATE_TIMEOUT_MS,
  type UseGemSweepOptions,
} from '../useGemSweep';

// ─── Fixtures ────────────────────────────────────────────────────────────────

function candidate(plyIndex: number, playedSan = 'e4'): SweepCandidate {
  return { plyIndex, parentFen: `fen-${plyIndex}`, playedSan };
}

function lastMaiaCall(): MaiaCallOptions | undefined {
  return maiaCalls[maiaCalls.length - 1];
}
function lastGradingCall(): GradingCallOptions | undefined {
  return gradingCalls[gradingCalls.length - 1];
}

function baseOptions(overrides: Partial<UseGemSweepOptions>): UseGemSweepOptions {
  return {
    enabled: true,
    sweepKey: 1,
    candidates: [],
    pinnedEloForPly: () => 1500,
    liveBusy: false,
    userColor: null,
    ...overrides,
  };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useGemSweep', () => {
  beforeEach(() => {
    maiaCalls.length = 0;
    gradingCalls.length = 0;
    // Default: high probability at every rung -> fails C1 (the cheapest path
    // for tests that don't care about a full C1-pass -> C2 round trip).
    maiaState.perElo = [{ elo: 1500, moveProbabilities: { e4: 0.9 } }];
    maiaState.ready = true;
    gradingState.gradeMap = new Map();
    gradingState.isGrading = false;
    gradingState.ready = true;
    lowPowerDevice = false;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('SWEEP_GRADING_MOVETIME_MS is strictly less than the live grading path\'s 4000ms cap', () => {
    expect(SWEEP_GRADING_MOVETIME_MS).toBeLessThan(4000);
  });

  it('LOAD-BEARING (D-05 yield-to-cursor invariant): with liveBusy true, the sweep\'s Maia instance is driven with fen: null; flipping liveBusy to false dispatches the first candidate', async () => {
    // Keep the Maia mock "in flight" (never resolving) so the dispatched fen
    // is observable rather than resolving-and-clearing within the same tick.
    maiaState.ready = false;
    const c0 = candidate(0);
    const { rerender } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0], liveBusy: true }),
    });

    // liveBusy: true — nextSweepDispatch's FIRST guard short-circuits before
    // any candidate lookup, so no idle callback is even scheduled and the
    // Maia instance stays parked at fen: null. Wait past the idle-callback's
    // setTimeout(cb, 1) fallback window (real timers) so a buggy version that
    // dispatches anyway has a genuine chance to prove it — a synchronous-only
    // check would pass by accident even with the guard deleted, since no
    // timer callback can fire before control returns to this line.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(lastMaiaCall()?.fen).toBeNull();
    expect(lastMaiaCall()?.enabled).toBe(true); // engineEnabled: candidates present, not gated off

    rerender(baseOptions({ candidates: [c0], liveBusy: false }));

    await waitFor(() => {
      expect(lastMaiaCall()?.fen).toBe(c0.parentFen);
    });
  });

  it('cheap-tier short-circuit (SC1/D-04): a candidate whose Maia probability exceeds GEM_MAIA_MAX_PROB resolves to null and the grading mock is never driven with a non-null fen for it', async () => {
    const c0 = candidate(0);
    // Default maiaState (0.9 probability) fails C1 for every candidate.
    const { result } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0] }),
    });

    await waitFor(() => {
      expect(result.current.gemByPly.get(0)).toBeNull();
    });

    expect(gradingCalls.every((c) => c.fen === null)).toBe(true);
  });

  it('a C1-passing candidate reaches the grading tier with a non-null fen', async () => {
    const c0 = candidate(0);
    maiaState.perElo = [{ elo: 1500, moveProbabilities: { e4: 0.05 } }]; // passes C1 (<= 0.2)

    renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0] }),
    });

    await waitFor(() => {
      expect(lastGradingCall()?.fen).toBe(c0.parentFen);
    });
    expect(lastGradingCall()?.movetimeMs).toBe(SWEEP_GRADING_MOVETIME_MS);
  });

  it('pinned rung (SC3/D-01): two candidates with different pinnedEloForPly values read their Maia probability from DIFFERENT rungs of the same curve', async () => {
    // Candidate A ("Nf3") is rare (passes C1) only at the 1200 rung; common
    // (fails C1) at 2000. Candidate B ("e4") is the mirror image. If the hook
    // used a single shared rung for both (ignoring pinnedEloForPly's
    // per-candidate return value), one of the two would never reach grading.
    maiaState.perElo = [
      { elo: 1200, moveProbabilities: { Nf3: 0.05, e4: 0.9 } },
      { elo: 2000, moveProbabilities: { Nf3: 0.9, e4: 0.05 } },
    ];
    const cA = candidate(0, 'Nf3');
    const cB = candidate(1, 'e4');
    // One graded entry per candidate (the played SAN itself) so the C2 effect
    // completes immediately once dispatched, letting the sweep move on to
    // the next candidate — the test only cares that GRADING was reached for
    // both, not the final gem classification.
    gradingState.gradeMap = new Map([['Nf3', { evalCp: 10, evalMate: null, depth: 5 }]]);

    renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({
        candidates: [cA, cB],
        pinnedEloForPly: (plyIndex) => (plyIndex === cA.plyIndex ? 1200 : 2000),
      }),
    });

    await waitFor(() => {
      expect(gradingCalls.some((c) => c.fen === cA.parentFen)).toBe(true);
    });

    // Re-key the grading stub for candidate B's own played SAN once A has
    // been dispatched, so B's C2 pass can also complete and dispatch fire.
    gradingState.gradeMap = new Map([['e4', { evalCp: 10, evalMate: null, depth: 5 }]]);

    await waitFor(() => {
      expect(gradingCalls.some((c) => c.fen === cB.parentFen)).toBe(true);
    });
  });

  it('no slider/selectedElo input exists on the options type — pinnedEloForPly is the only rung source (compile-time guarantee, not just runtime)', () => {
    // TypeScript's excess-property check on the object literal below is the
    // actual proof: adding a `selectedElo`/`selectedElo`-shaped field to
    // UseGemSweepOptions would fail `npx tsc -b --noEmit`, not this
    // assertion. This case exists so the invariant has an explicit, greppable
    // anchor in the suite.
    const options = baseOptions({});
    expect(Object.keys(options).sort()).toEqual(
      ['candidates', 'enabled', 'liveBusy', 'pinnedEloForPly', 'sweepKey', 'userColor'].sort(),
    );
  });

  it('cache bound (Pitfall 4): resolving more than 256 candidates does not evict ply 0 — the sweep map is not FIFO-capped', async () => {
    const CANDIDATE_COUNT = 260;
    const candidates = Array.from({ length: CANDIDATE_COUNT }, (_, i) => candidate(i));
    // Default maiaState (0.9 probability) fails C1 for every candidate —
    // the fastest path through the cascade so the test resolves quickly.
    const { result } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates }),
    });

    await waitFor(
      () => {
        expect(result.current.gemByPly.size).toBe(CANDIDATE_COUNT);
      },
      { timeout: 10000 },
    );

    expect(result.current.gemByPly.has(0)).toBe(true);
  }, 15000);

  it('mobile gate: with isLowPowerDevice() true, both engine mocks are driven with enabled: false / fen: null', () => {
    lowPowerDevice = true;
    const c0 = candidate(0);
    renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0] }),
    });

    expect(lastMaiaCall()?.enabled).toBe(false);
    expect(lastMaiaCall()?.fen).toBeNull();
    expect(lastGradingCall()?.enabled).toBe(false);
    expect(lastGradingCall()?.fen).toBeNull();
  });

  it('candidates: [] drives no worker work (enabled: false, fen: null)', () => {
    renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [] }),
    });

    expect(lastMaiaCall()?.enabled).toBe(false);
    expect(lastMaiaCall()?.fen).toBeNull();
  });

  it('enabled: false drives no worker work (enabled: false, fen: null)', () => {
    const c0 = candidate(0);
    renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0], enabled: false }),
    });

    expect(lastMaiaCall()?.enabled).toBe(false);
    expect(lastMaiaCall()?.fen).toBeNull();
  });

  it('game switch: changing sweepKey clears gemByPly', async () => {
    const c0 = candidate(0);
    const { result, rerender } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0], sweepKey: 1 }),
    });

    await waitFor(() => {
      expect(result.current.gemByPly.size).toBe(1);
    });

    rerender(baseOptions({ candidates: [c0], sweepKey: 2 }));

    await waitFor(() => {
      expect(result.current.gemByPly.size).toBe(0);
    });
  });

  it('LOAD-BEARING (CR-03 watchdog): a candidate whose cascade never resolves is abandoned after SWEEP_CANDIDATE_TIMEOUT_MS, unpinning the single-in-flight queue so the NEXT candidate dispatches — removing the watchdog effect MUST turn this red', () => {
    vi.useFakeTimers();
    try {
      // Maia never resolves (`ready: false` keeps resultFen null), so candidate 0
      // reaches the maia stage and STAYS there. Without the watchdog it pins the
      // single in-flight slot forever and candidate 1 never dispatches.
      maiaState.ready = false;
      maiaState.perElo = [{ elo: 1500, moveProbabilities: { e4: 0.05 } }];
      const c0 = candidate(0);
      const c1 = candidate(1);
      const { result } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
        initialProps: baseOptions({ candidates: [c0, c1] }),
      });

      // The dispatch idle-callback fallback (setTimeout(cb, 1)) fires → c0 goes
      // in flight on the maia stage, never resolving.
      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(lastMaiaCall()?.fen).toBe(c0.parentFen);
      // Still pinned: c0 unresolved, the watchdog has not yet fired.
      expect(result.current.gemByPly.has(0)).toBe(false);

      // Advance past the watchdog → c0 is abandoned as an explicit miss (null).
      act(() => {
        vi.advanceTimersByTime(SWEEP_CANDIDATE_TIMEOUT_MS);
      });
      expect(result.current.gemByPly.get(0)).toBeNull();

      // The queue advanced: the next dispatch idle-callback fires → c1 in flight.
      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(lastMaiaCall()?.fen).toBe(c1.parentFen);
    } finally {
      vi.useRealTimers();
    }
  });

  it('WR-02: once every candidate is resolved the dedicated engines are torn down (enabled: false) — hasWork tracks UNRESOLVED candidates, not candidates.length', async () => {
    // Default maiaState (0.9 probability) fails C1, so the single candidate
    // resolves to null (an explicit miss) almost immediately.
    const c0 = candidate(0);
    const { result } = renderHook((props: UseGemSweepOptions) => useGemSweep(props), {
      initialProps: baseOptions({ candidates: [c0] }),
    });

    await waitFor(() => {
      expect(result.current.gemByPly.get(0)).toBeNull();
    });

    // Every candidate resolved → hasWork is false → BOTH dedicated instances are
    // disabled (their `enabled`-keyed cleanup terminates the workers). With the
    // old `candidates.length > 0` predicate `enabled` would stay true forever.
    await waitFor(() => {
      expect(lastMaiaCall()?.enabled).toBe(false);
      expect(lastGradingCall()?.enabled).toBe(false);
    });
  });
});
