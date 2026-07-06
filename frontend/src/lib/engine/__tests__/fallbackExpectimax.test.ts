/**
 * fallbackExpectimax.ts unit tests (ENGINE-06 / SC5).
 *
 * Covers:
 * - SC5 swap-in: a single `SearchRunner`-typed variable is assigned
 *   `mctsSearch`, then `fallbackExpectimax`, and run with the IDENTICAL
 *   `(rootFen, budget, providers, onSnapshot, signal)` arguments at each
 *   call site — no call-site change, both compile against the same type and
 *   both return a non-empty `rankedLines` array with UCI `rootMove`s and
 *   `practicalScore` in [0, 1].
 * - Determinism: `fallbackExpectimax` produces bit-identical final snapshots
 *   AND full `onSnapshot` sequences across two repeated runs (mirrors
 *   `mctsSearch.test.ts`'s ENGINE-07 repeated-run case; no concurrency
 *   variant needed here since the fallback walk is purely sequential).
 * - WR-05 budgetExhausted contract: BOTH runners over the same terminal-root
 *   and maxPlies-bound fixtures report identical completion states.
 * - D-04 extraRootMoves union, AbortSignal semantics, and WR-07
 *   illegal-candidate containment (mirrors the mctsSearch.test.ts coverage).
 *
 * Fabricated providers are built from ACTUAL chess.js legal moves (never
 * hand-enumerated), matching 153-PATTERNS.md's fabricated-provider
 * construction guidance and the sibling `mctsSearch.test.ts` style.
 */

import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import { mctsSearch } from '../mctsSearch';
import { fallbackExpectimax } from '../fallbackExpectimax';
import type { SearchRunner } from '../guardrail';
import type { EngineProviders, EngineSnapshot, SearchBudget, MoveGrade } from '../types';

// ─── Fixtures ────────────────────────────────────────────────────────────────

/** King+pawn ending, White to move — 6 legal moves (e2e3, e2e4, e1d1, e1d2, e1f1, e1f2). */
const SIMPLE_WHITE_FEN = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1';

const SIMPLE_WHITE_POLICY: Record<string, number> = {
  e2e4: 0.5,
  e2e3: 0.3,
  e1d2: 0.15,
  e1f2: 0.03,
  e1d1: 0.01,
  e1f1: 0.01,
};

const SIMPLE_WHITE_GRADES: Record<string, MoveGrade> = {
  e2e4: { evalCp: 200, evalMate: null, depth: 10 },
  e2e3: { evalCp: 50, evalMate: null, depth: 10 },
  e1d2: { evalCp: -30, evalMate: null, depth: 10 },
};

const NEUTRAL_BUDGET_ELO = { w: 1500, b: 1500 };

/** Never-aborted signal for tests that don't exercise cancellation. */
function freshSignal(): AbortSignal {
  return new AbortController().signal;
}

// ─── Fabricated-provider helpers (mirrors mctsSearch.test.ts) ──────────────

/** Uniform distribution over chess.js's OWN legal-move list at `fen` — never hand-enumerated. */
function uniformPolicyFromLegalMoves(fen: string): Record<string, number> {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true });
  const ucis = moves.map((m) => `${m.from}${m.to}${m.promotion ?? ''}`);
  const weight = ucis.length > 0 ? 1 / ucis.length : 0;
  const dist: Record<string, number> = {};
  for (const uci of ucis) dist[uci] = weight;
  return dist;
}

/** A fabricated `policy()`: returns `byFen[fen]` when configured, else a uniform legal-move distribution. */
function makeFixedPolicy(byFen: Record<string, Record<string, number>>): EngineProviders['policy'] {
  return async (fen: string) => byFen[fen] ?? uniformPolicyFromLegalMoves(fen);
}

/** A fabricated `grade()`: returns `byFen[fen][uci]` when configured, else a neutral `{evalCp: 0}` grade. */
function makeFixedGrade(byFen: Record<string, Record<string, MoveGrade>>): EngineProviders['grade'] {
  return async (fen: string, candidateUcis: string[]) => {
    const fixedForFen = byFen[fen];
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      map.set(uci, fixedForFen?.[uci] ?? { evalCp: 0, evalMate: null, depth: 10 });
    }
    return map;
  };
}

function makeProviders(): EngineProviders {
  return {
    policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
    grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
  };
}

/** Asserts the generic `SearchRunner` output contract shared by both implementations. */
function assertValidSnapshot(snapshot: EngineSnapshot): void {
  expect(snapshot.rankedLines.length).toBeGreaterThan(0);
  for (const line of snapshot.rankedLines) {
    expect(line.rootMove.length).toBeGreaterThanOrEqual(4); // UCI, not SAN
    expect(line.practicalScore).toBeGreaterThanOrEqual(0);
    expect(line.practicalScore).toBeLessThanOrEqual(1);
  }
}

// ─── SC5: swap-in via one SearchRunner-typed variable ───────────────────────

describe('fallbackExpectimax — SC5 guardrail swap-in', () => {
  it('runs mctsSearch and fallbackExpectimax through the SAME SearchRunner-typed variable with identical arguments', async () => {
    const budget: SearchBudget = { maxNodes: 3, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };

    let runner: SearchRunner = mctsSearch;
    const mctsSnapshot = await runner(SIMPLE_WHITE_FEN, budget, makeProviders(), () => {}, freshSignal());
    assertValidSnapshot(mctsSnapshot);

    runner = fallbackExpectimax;
    const fallbackSnapshot = await runner(SIMPLE_WHITE_FEN, budget, makeProviders(), () => {}, freshSignal());
    assertValidSnapshot(fallbackSnapshot);
  });
});

// ─── fallbackExpectimax: reuse + basic correctness ──────────────────────────

describe('fallbackExpectimax — shared-primitive reuse', () => {
  it('returns a non-empty rankedLines array sorted by practicalScore descending with UCI rootMove values', async () => {
    const budget: SearchBudget = { maxNodes: 3, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };

    const snapshot = await fallbackExpectimax(SIMPLE_WHITE_FEN, budget, makeProviders(), () => {}, freshSignal());

    assertValidSnapshot(snapshot);
    for (let i = 1; i < snapshot.rankedLines.length; i += 1) {
      const prev = snapshot.rankedLines[i - 1];
      const curr = snapshot.rankedLines[i];
      expect(prev).toBeDefined();
      expect(curr).toBeDefined();
      expect(prev!.practicalScore).toBeGreaterThanOrEqual(curr!.practicalScore);
    }
  });

  it("an unexpanded leaf's practicalScore matches evalToExpectedScore(grade, rootMover) exactly (leafScore.ts reuse)", async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };

    const snapshot = await fallbackExpectimax(SIMPLE_WHITE_FEN, budget, makeProviders(), () => {}, freshSignal());

    // maxNodes: 1 caps the walk to a single expansion (the root itself), so
    // every root child is still an unbacked leaf estimate straight from
    // leafExpectedScore(grade, rootMover) — proving leafScore.ts's own
    // conversion (not a second copy) drives the fallback's leaf values.
    for (const line of snapshot.rankedLines) {
      const grade = SIMPLE_WHITE_GRADES[line.rootMove];
      expect(grade).toBeDefined();
      const expected = evalToExpectedScore(grade!.evalCp, grade!.evalMate, 'white');
      expect(line.practicalScore).toBe(expected);
    }
  });
});

// ─── D-04: extraRootMoves union (WR-08 coverage) ────────────────────────────

describe('fallbackExpectimax — D-04 extraRootMoves', () => {
  it('an extra root move dropped by the Maia mass cut survives the union, is graded, and appears in rankedLines', async () => {
    const budget: SearchBudget = {
      maxNodes: 1,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 3,
      concurrency: 1,
      extraRootMoves: ['e1f1'], // 0.01 Maia probability — dropped by truncation, revived only by the D-04 union
    };
    const extraMoveGrade: MoveGrade = { evalCp: 120, evalMate: null, depth: 10 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: { ...SIMPLE_WHITE_GRADES, e1f1: extraMoveGrade } }),
    };

    const snapshot = await fallbackExpectimax(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const extraLine = snapshot.rankedLines.find((l) => l.rootMove === 'e1f1');
    expect(extraLine).toBeDefined();
    // Its practicalScore comes from its OWN grade (not the 0.5 omitted-grade
    // fallback), proving the injected move flowed through grade() for real.
    expect(extraLine!.practicalScore).toBe(evalToExpectedScore(extraMoveGrade.evalCp, extraMoveGrade.evalMate, 'white'));
    // The union revives ONLY the injected move — its dropped-tail siblings stay dropped.
    expect(snapshot.rankedLines.map((l) => l.rootMove)).not.toContain('e1d1');
  });
});

// ─── AbortSignal (WR-08 coverage) ───────────────────────────────────────────

describe('fallbackExpectimax — abort', () => {
  it('aborting after the Nth snapshot stops promptly, resolves (not rejects), and keeps budgetExhausted=false', async () => {
    const SNAPSHOTS_BEFORE_ABORT = 2;
    const controller = new AbortController();
    const budget: SearchBudget = { maxNodes: 50, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };

    const snapshots: EngineSnapshot[] = [];
    const result = await fallbackExpectimax(
      SIMPLE_WHITE_FEN,
      budget,
      makeProviders(),
      (s) => {
        snapshots.push(structuredClone(s));
        if (snapshots.length === SNAPSHOTS_BEFORE_ABORT) controller.abort();
      },
      controller.signal,
    );

    expect(snapshots.length).toBe(SNAPSHOTS_BEFORE_ABORT); // no further onSnapshot after abort
    expect(result.nodesEvaluated).toBe(SNAPSHOTS_BEFORE_ABORT); // stopped promptly, far below maxNodes
    expect(result.budgetExhausted).toBe(false); // an abort is not budget exhaustion
    expect(result.rankedLines.length).toBeGreaterThan(0); // partial snapshot is still usable
  });
});

// ─── Illegal/malformed provider candidates (WR-07) ──────────────────────────

describe('fallbackExpectimax — illegal provider candidates', () => {
  it('drops illegal and malformed UCIs deterministically instead of rejecting the search', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const providers: EngineProviders = {
      // e7e5 is a BLACK move (illegal from SIMPLE_WHITE_FEN) and 'zz' is
      // malformed; both must be dropped, not crash the runner (WR-07).
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: { e2e4: 0.5, e7e5: 0.3, zz: 0.2 } }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshot = await fallbackExpectimax(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.rankedLines.map((l) => l.rootMove)).toEqual(['e2e4']);
    expect(snapshot.nodesEvaluated).toBe(1);
  });
});

// ─── Determinism: repeated runs (no concurrency variant — purely sequential) ─

describe('fallbackExpectimax — determinism', () => {
  it('produces toEqual final snapshots AND toEqual full onSnapshot sequences across two repeated runs', async () => {
    const budget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };

    const snapshotsRun1: EngineSnapshot[] = [];
    const resultRun1 = await fallbackExpectimax(
      SIMPLE_WHITE_FEN,
      budget,
      makeProviders(),
      (s) => snapshotsRun1.push(structuredClone(s)),
      freshSignal(),
    );

    const snapshotsRun2: EngineSnapshot[] = [];
    const resultRun2 = await fallbackExpectimax(
      SIMPLE_WHITE_FEN,
      budget,
      makeProviders(),
      (s) => snapshotsRun2.push(structuredClone(s)),
      freshSignal(),
    );

    expect(resultRun2).toEqual(resultRun1);
    expect(snapshotsRun2).toEqual(snapshotsRun1);
    expect(snapshotsRun1.length).toBeGreaterThan(0);
  });
});

// ─── WR-05: budgetExhausted contract — both runners, same fixtures ──────────

describe('budgetExhausted contract (shared across both runners)', () => {
  /** Black is already checkmated (Re8#) — nothing to search at all. */
  const TERMINAL_ROOT_FEN = '4R1k1/5ppp/8/8/8/8/8/7K b - - 1 1';

  const RUNNERS: ReadonlyArray<readonly [string, SearchRunner]> = [
    ['mctsSearch', mctsSearch],
    ['fallbackExpectimax', fallbackExpectimax],
  ];

  for (const [name, runner] of RUNNERS) {
    it(`${name}: a terminal root reports budgetExhausted=false with zero snapshots — no budget dimension stopped anything`, async () => {
      const budget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
      const snapshots: EngineSnapshot[] = [];

      const result = await runner(TERMINAL_ROOT_FEN, budget, makeProviders(), (s) => snapshots.push(s), freshSignal());

      expect(result.budgetExhausted).toBe(false);
      expect(result.nodesEvaluated).toBe(0);
      expect(result.rankedLines).toEqual([]);
      expect(snapshots).toEqual([]);
    });

    it(`${name}: a maxPlies-cut walk reports budgetExhausted=true even when maxNodes is never reached`, async () => {
      const budget: SearchBudget = { maxNodes: 50, elo: NEUTRAL_BUDGET_ELO, maxPlies: 1, concurrency: 1 };

      const result = await runner(SIMPLE_WHITE_FEN, budget, makeProviders(), () => {}, freshSignal());

      expect(result.nodesEvaluated).toBe(1); // only the root fits under maxPlies
      expect(result.budgetExhausted).toBe(true);
    });
  }
});
