/**
 * mctsSearch.ts unit tests (ENGINE-01/02/04/05/07).
 *
 * Covers:
 * - ENGINE-01: a fixed FEN + budget + fabricated providers yields a
 *   non-empty, practicalScore-descending ranked root-move list.
 * - ENGINE-02: only the ~90%-mass-truncated candidate set is ever passed to
 *   grade() — the dropped tail is never graded.
 * - ENGINE-04: every policy() call's elo is keyed on the NODE's own
 *   side-to-move, proven for BOTH a white-root and a black-root run (never
 *   depth/ply parity, Pitfall 3/4).
 * - ENGINE-05: an unexpanded leaf's practicalScore equals
 *   evalToExpectedScore(grade, rootMover) exactly, and descent never
 *   continues past budget.maxPlies.
 * - Terminal positions (Pitfall 6): a one-ply-from-mate fixture yields a
 *   confident practicalScore (~1.0 when the root player delivers mate, ~0.0
 *   when the root player is mated one ply deeper) with zero policy() calls
 *   ever recorded for the terminal node's own fen.
 * - ENGINE-07/D-03: bit-identical output AND full onSnapshot-sequence across
 *   repeated runs at the SAME concurrency level — including concurrency=2
 *   under two deliberately DIFFERENT provider resolution jitters (Pattern 5).
 *   c=1 vs c=2 output equality is intentionally NOT asserted: it is not an
 *   invariant of this algorithm (at c=1 the second selection of a round sees
 *   the first expansion's backed-up value; at c=2 pending-exclusion forces
 *   it onto a different node — the two levels may build different trees).
 * - D-04: `budget.extraRootMoves` survives the truncation cut, is graded,
 *   and appears in rankedLines (WR-08).
 * - Phase 159 D-01: a low-prior/high-value root child that would WIN under
 *   the old practicalScore-only sort LOSES under the new findability sort at
 *   a low root ELO, while practicalScore itself is unchanged (D-04).
 * - Phase 159 D-05/D-06/D-07 (policy temperature): omitting
 *   `policyTemperature` behaves identically to explicitly passing the
 *   default (Pitfall 1 no-op short-circuit); temperature reshapes ONLY the
 *   root-mover's own side, never the opponent's (D-05, proven via the exact
 *   candidateUcis passed to grade() at a non-root node); the
 *   temperature-adjusted prior composes with the D-01 findability sort with
 *   zero extra glue (D-06); an extreme-flatness fixture never exceeds
 *   `ROOT_CANDIDATE_HARD_CAP` root children (D-07/Pitfall 6).
 * - AbortSignal: aborting mid-run stops promptly, resolves with a usable
 *   partial snapshot, and never reports budget exhaustion (WR-08).
 * - WR-04/WR-07 degenerate providers: empty candidate sets and
 *   illegal/malformed UCIs are contained deterministically.
 *
 * Fabricated providers are built from ACTUAL chess.js legal moves (never
 * hand-enumerated) so every candidate uci fed into mctsSearch is guaranteed
 * legal, matching 153-PATTERNS.md's fabricated-provider construction
 * guidance.
 */

import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import { mctsSearch } from '../mctsSearch';
import { ROOT_CANDIDATE_HARD_CAP } from '../policyTemperature';
import type { EngineProviders, EngineSnapshot, SearchBudget, Side, MoveGrade } from '../types';

// ─── Fixtures ────────────────────────────────────────────────────────────────

/** King+pawn ending, White to move — 6 legal moves (e2e3, e2e4, e1d1, e1d2, e1f1, e1f2). */
const SIMPLE_WHITE_FEN = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1';

/** Mirror of SIMPLE_WHITE_FEN, Black to move — 6 legal moves. */
const SIMPLE_BLACK_FEN = '4k3/4p3/8/8/8/8/8/4K3 b - - 0 1';

/** One move (e1e8) delivers immediate checkmate of Black. */
const MATE_IN_1_FEN = '6k1/5ppp/8/8/8/8/8/4R2K w - - 0 1';
const MATE_IN_1_MOVE = 'e1e8';
const MATE_IN_1_TERMINAL_FEN = '4R1k1/5ppp/8/8/8/8/8/7K b - - 1 1';

/** A forced "waiting" move (b2b3), after which Black's ONLY reply (a8a1) checkmates White one ply deeper. */
const FORCED_MATE_ROOT_FEN = 'r6k/8/8/8/8/8/1P3PPP/6K1 w - - 0 1';
const FORCED_MATE_WAITING_MOVE = 'b2b3';
const FORCED_MATE_DEPTH1_FEN = 'r6k/8/8/8/8/1P6/5PPP/6K1 b - - 0 1';
const FORCED_MATE_MOVE = 'a8a1';
const FORCED_MATE_TERMINAL_FEN = '7k/8/8/8/8/1P6/5PPP/r5K1 w - - 1 2';

const SIMPLE_WHITE_POLICY: Record<string, number> = {
  e2e4: 0.5,
  e2e3: 0.3,
  e1d2: 0.15,
  e1f2: 0.03,
  e1d1: 0.01,
  e1f1: 0.01,
};

/** The tail dropped by truncateAndRenormalize's ~90% mass cut on SIMPLE_WHITE_POLICY (0.5+0.3+0.15 = 0.95 >= 0.9). */
const SIMPLE_WHITE_DROPPED_TAIL = ['e1f2', 'e1d1', 'e1f1'];

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

// ─── Fabricated-provider helpers ────────────────────────────────────────────

interface PolicyCall {
  fen: string;
  elo: number;
  side: Side;
}

interface GradeCall {
  fen: string;
  candidateUcis: string[];
}

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

/**
 * A fabricated `policy()`: returns `byFen[fen]` when explicitly configured,
 * else falls back to a uniform distribution over chess.js's real legal moves
 * (so deeper/unconfigured tree nodes always receive a legal distribution).
 * Records every call when `calls` is provided (ENGINE-04 oracle / ENGINE-02
 * dropped-tail assertions).
 */
function makeFixedPolicy(
  byFen: Record<string, Record<string, number>>,
  calls?: PolicyCall[],
): EngineProviders['policy'] {
  return async (fen, elo, side) => {
    calls?.push({ fen, elo, side });
    return byFen[fen] ?? uniformPolicyFromLegalMoves(fen);
  };
}

/**
 * A fabricated `grade()`: returns `byFen[fen][uci]` when explicitly
 * configured, else a neutral `{evalCp: 0}` grade. Records every call
 * (fen + the exact candidateUcis it was given) when `calls` is provided.
 */
function makeFixedGrade(
  byFen: Record<string, Record<string, MoveGrade>>,
  calls?: GradeCall[],
): EngineProviders['grade'] {
  return async (fen, candidateUcis) => {
    calls?.push({ fen, candidateUcis: [...candidateUcis] });
    const fixedForFen = byFen[fen];
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      map.set(uci, fixedForFen?.[uci] ?? { evalCp: 0, evalMate: null, depth: 10 });
    }
    return map;
  };
}

// ─── ENGINE-01: ranked output ───────────────────────────────────────────────

describe('mctsSearch — ENGINE-01 ranked output', () => {
  it('returns a non-empty rankedLines array sorted by practicalScore descending with UCI rootMove values', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.rankedLines.length).toBeGreaterThan(0);
    for (const line of snapshot.rankedLines) {
      expect(line.rootMove.length).toBeGreaterThanOrEqual(4); // UCI, not SAN
    }
    for (let i = 1; i < snapshot.rankedLines.length; i += 1) {
      const prev = snapshot.rankedLines[i - 1];
      const curr = snapshot.rankedLines[i];
      expect(prev).toBeDefined();
      expect(curr).toBeDefined();
      expect(prev!.practicalScore).toBeGreaterThanOrEqual(curr!.practicalScore);
    }
  });
});

// ─── ENGINE-04: ELO oracle, both root colors ────────────────────────────────

describe('mctsSearch — ENGINE-04 ELO oracle', () => {
  it('keys elo on the NODE own side-to-move, proven for both a white-root and a black-root run', async () => {
    const budget: SearchBudget = { maxNodes: 4, elo: { w: 1500, b: 1800 }, maxPlies: 3, concurrency: 1 };
    const grade = makeFixedGrade({});

    const whiteCalls: PolicyCall[] = [];
    await mctsSearch(
      SIMPLE_WHITE_FEN,
      budget,
      { policy: makeFixedPolicy({}, whiteCalls), grade },
      () => {},
      freshSignal(),
    );
    expect(whiteCalls.length).toBeGreaterThan(0);
    expect(whiteCalls.some((c) => c.side === 'w')).toBe(true);
    expect(whiteCalls.some((c) => c.side === 'b')).toBe(true);
    for (const call of whiteCalls) {
      if (call.side === 'w') expect(call.elo).toBe(1500);
      if (call.side === 'b') expect(call.elo).toBe(1800);
    }

    const blackCalls: PolicyCall[] = [];
    await mctsSearch(
      SIMPLE_BLACK_FEN,
      budget,
      { policy: makeFixedPolicy({}, blackCalls), grade },
      () => {},
      freshSignal(),
    );
    expect(blackCalls.length).toBeGreaterThan(0);
    expect(blackCalls.some((c) => c.side === 'w')).toBe(true);
    expect(blackCalls.some((c) => c.side === 'b')).toBe(true);
    for (const call of blackCalls) {
      if (call.side === 'w') expect(call.elo).toBe(1500);
      if (call.side === 'b') expect(call.elo).toBe(1800);
    }
  });
});

// ─── ENGINE-02: truncation — dropped tail never graded ──────────────────────

describe('mctsSearch — ENGINE-02 truncation', () => {
  it('never passes the dropped (sub-90%-mass) tail to grade()', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const gradeCalls: GradeCall[] = [];
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }, gradeCalls),
    };

    await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(gradeCalls.length).toBeGreaterThan(0);
    const allGradedUcis = gradeCalls.flatMap((c) => c.candidateUcis);
    for (const droppedUci of SIMPLE_WHITE_DROPPED_TAIL) {
      expect(allGradedUcis).not.toContain(droppedUci);
    }
    expect(allGradedUcis).toEqual(expect.arrayContaining(['e2e4', 'e2e3', 'e1d2']));
  });
});

// ─── ENGINE-05: leaf sigmoid match + depth cutoff ───────────────────────────

describe('mctsSearch — ENGINE-05 leaf conversion + depth cutoff', () => {
  it("an unexpanded leaf's practicalScore matches evalToExpectedScore(grade, rootMover) exactly", async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    for (const line of snapshot.rankedLines) {
      const grade = SIMPLE_WHITE_GRADES[line.rootMove];
      expect(grade).toBeDefined();
      const expected = evalToExpectedScore(grade!.evalCp, grade!.evalMate, 'white');
      expect(line.practicalScore).toBe(expected);
    }
  });

  it('stops descending at budget.maxPlies — every modal path is exactly one ply', async () => {
    const budget: SearchBudget = { maxNodes: 3, elo: NEUTRAL_BUDGET_ELO, maxPlies: 1, concurrency: 1 };
    const providers: EngineProviders = { policy: makeFixedPolicy({}), grade: makeFixedGrade({}) };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    // Only the root itself is ever expanded — depth-1 children are all
    // closed (depth >= maxPlies) the moment they're first reached.
    expect(snapshot.nodesEvaluated).toBe(1);
    expect(snapshot.budgetExhausted).toBe(true);
    expect(snapshot.rankedLines.length).toBeGreaterThan(0);
    for (const line of snapshot.rankedLines) {
      expect(line.modalPath).toEqual([line.rootMove]);
      // WR-01 regression guard: each depth-capped child is discovered (and
      // visit-bumped) exactly once — the old retry-based exhaustion probe
      // re-walked closed dead ends up to 1000 times, so visits summed to
      // ~1000 here while nodesEvaluated stayed at 1.
      expect(line.visits).toBe(1);
    }
  });
});

// ─── Terminal positions (Pitfall 6) ─────────────────────────────────────────

describe('mctsSearch — terminal positions', () => {
  it('assigns practicalScore ~1.0 when the root player delivers mate, with no policy() call for the terminal node', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const policyCalls: PolicyCall[] = [];
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [MATE_IN_1_FEN]: { [MATE_IN_1_MOVE]: 1.0 } }, policyCalls),
      grade: makeFixedGrade({}),
    };

    const snapshot = await mctsSearch(MATE_IN_1_FEN, budget, providers, () => {}, freshSignal());

    const line = snapshot.rankedLines.find((l) => l.rootMove === MATE_IN_1_MOVE);
    expect(line).toBeDefined();
    expect(line!.practicalScore).toBeCloseTo(1.0, 10);
    expect(policyCalls.some((c) => c.fen === MATE_IN_1_TERMINAL_FEN)).toBe(false);
  });

  it('assigns practicalScore ~0.0 when the root player is mated one ply deeper, with no policy() call for the terminal node', async () => {
    const budget: SearchBudget = { maxNodes: 2, elo: NEUTRAL_BUDGET_ELO, maxPlies: 2, concurrency: 1 };
    const policyCalls: PolicyCall[] = [];
    const providers: EngineProviders = {
      policy: makeFixedPolicy(
        {
          [FORCED_MATE_ROOT_FEN]: { [FORCED_MATE_WAITING_MOVE]: 1.0 },
          [FORCED_MATE_DEPTH1_FEN]: { [FORCED_MATE_MOVE]: 1.0 },
        },
        policyCalls,
      ),
      grade: makeFixedGrade({}),
    };

    const snapshot = await mctsSearch(FORCED_MATE_ROOT_FEN, budget, providers, () => {}, freshSignal());

    const line = snapshot.rankedLines.find((l) => l.rootMove === FORCED_MATE_WAITING_MOVE);
    expect(line).toBeDefined();
    expect(line!.practicalScore).toBeCloseTo(0.0, 10);
    expect(policyCalls.some((c) => c.fen === FORCED_MATE_TERMINAL_FEN)).toBe(false);
  });
});

// ─── D-04: extraRootMoves union (WR-08 coverage) ────────────────────────────

describe('mctsSearch — D-04 extraRootMoves', () => {
  it('an extra root move dropped by the Maia mass cut survives the union, is graded, and appears in rankedLines', async () => {
    const budget: SearchBudget = {
      maxNodes: 1,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 3,
      concurrency: 1,
      extraRootMoves: ['e1f1'], // in SIMPLE_WHITE_DROPPED_TAIL — only the D-04 union can bring it back
    };
    const gradeCalls: GradeCall[] = [];
    const extraMoveGrade: MoveGrade = { evalCp: 120, evalMate: null, depth: 10 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: { ...SIMPLE_WHITE_GRADES, e1f1: extraMoveGrade } }, gradeCalls),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(gradeCalls.flatMap((c) => c.candidateUcis)).toContain('e1f1');
    const extraLine = snapshot.rankedLines.find((l) => l.rootMove === 'e1f1');
    expect(extraLine).toBeDefined();
    // Its practicalScore comes from its OWN grade (not the 0.5 omitted-grade
    // fallback), proving the injected move flowed through grade() for real.
    expect(extraLine!.practicalScore).toBe(evalToExpectedScore(extraMoveGrade.evalCp, extraMoveGrade.evalMate, 'white'));
    // The union revives ONLY the injected move — its dropped-tail siblings stay dropped.
    expect(snapshot.rankedLines.map((l) => l.rootMove)).not.toContain('e1d1');
  });
});

// ─── Phase 159 D-01: findability ranking reorders the root at low ELO ──────

describe('mctsSearch — Phase 159 D-01 findability ranking', () => {
  // e2e4 (low prior 0.06, high V via evalCp=700) would win the OLD
  // practicalScore-only sort against e2e3 (high prior 0.85, lower V via
  // evalCp=100). At a low root ELO (600, pRefForElo(600)=0.12) e2e4's
  // renormalized prior (~0.066) is well below pRef, so its findability
  // factor suppresses it below e2e3's saturated (prior >> pRef) rankScore.
  const FINDABILITY_FEN = SIMPLE_WHITE_FEN;
  const FINDABILITY_POLICY: Record<string, number> = {
    e2e3: 0.85,
    e2e4: 0.06,
    e1d2: 0.04,
    e1f2: 0.03,
    e1d1: 0.01,
    e1f1: 0.01,
  };
  const FINDABILITY_GRADES: Record<string, MoveGrade> = {
    e2e4: { evalCp: 700, evalMate: null, depth: 10 }, // high V, low prior
    e2e3: { evalCp: 100, evalMate: null, depth: 10 }, // lower V, high prior
  };
  const LOW_ELO = 600;

  it('demotes the low-prior/high-V move below the high-prior/lower-V move at low ELO, while practicalScore stays unchanged', async () => {
    const budget: SearchBudget = {
      maxNodes: 1,
      elo: { w: LOW_ELO, b: LOW_ELO },
      maxPlies: 4,
      concurrency: 1,
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [FINDABILITY_FEN]: FINDABILITY_POLICY }),
      grade: makeFixedGrade({ [FINDABILITY_FEN]: FINDABILITY_GRADES }),
    };

    const snapshot = await mctsSearch(FINDABILITY_FEN, budget, providers, () => {}, freshSignal());

    const e2e4Line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e4');
    const e2e3Line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e3');
    expect(e2e4Line).toBeDefined();
    expect(e2e3Line).toBeDefined();

    // practicalScore (D-04) is untouched: still the raw leaf conversion.
    expect(e2e4Line!.practicalScore).toBe(evalToExpectedScore(700, null, 'white'));
    expect(e2e3Line!.practicalScore).toBe(evalToExpectedScore(100, null, 'white'));
    // Sanity: e2e4 really does have the higher practicalScore (would have
    // won the OLD sort) — the assertion below proves the NEW sort reverses it.
    expect(e2e4Line!.practicalScore).toBeGreaterThan(e2e3Line!.practicalScore);

    // The findability-weighted sort puts e2e3 FIRST despite its lower
    // practicalScore, because e2e4's prior is well below pRefForElo(600).
    expect(snapshot.rankedLines[0]?.rootMove).toBe('e2e3');
  });
});

// ─── Phase 159 D-05/D-06/D-07: policy temperature ───────────────────────────

describe('mctsSearch — Phase 159 policy temperature', () => {
  it('omitting policyTemperature behaves identically to the default (no-op short-circuit, Pitfall 1)', async () => {
    const providers = (): EngineProviders => ({
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    });

    const withoutField: SearchBudget = { maxNodes: 3, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const withDefault: SearchBudget = { ...withoutField, policyTemperature: 1 };

    const snapshotA = await mctsSearch(SIMPLE_WHITE_FEN, withoutField, providers(), () => {}, freshSignal());
    const snapshotB = await mctsSearch(SIMPLE_WHITE_FEN, withDefault, providers(), () => {}, freshSignal());

    expect(snapshotB.rankedLines).toEqual(snapshotA.rankedLines);
    expect(snapshotB.nodesEvaluated).toBe(snapshotA.nodesEvaluated);
    expect(snapshotB.budgetExhausted).toBe(snapshotA.budgetExhausted);
  });

  it("reshapes ONLY the root-mover's own side — the opponent's candidateUcis passed to grade() are the untouched raw truncation (D-05)", async () => {
    // ROOT (White to move): a real, legal 4-move policy so root's own
    // children actually get created (needed to reach a depth-1 node).
    const ROOT_POLICY: Record<string, number> = {
      e2e4: 0.85,
      e2e3: 0.05,
      e1d2: 0.05,
      e1f2: 0.05,
    };
    // e2e4 gets by far the best grade so PUCT deterministically selects it
    // as the depth-1 continuation to expand next.
    const ROOT_GRADES: Record<string, MoveGrade> = {
      e2e4: { evalCp: 900, evalMate: null, depth: 10 },
      e2e3: { evalCp: 50, evalMate: null, depth: 10 },
      e1d2: { evalCp: 10, evalMate: null, depth: 10 },
      e1f2: { evalCp: 5, evalMate: null, depth: 10 },
    };
    const chess = new Chess(SIMPLE_WHITE_FEN);
    chess.move({ from: 'e2', to: 'e4' });
    const AFTER_E2E4_FEN = chess.fen(); // Black to move — the opponent node.

    // Same 0.85/0.05/0.05/0.05 shape as ROOT_POLICY, arbitrary fake UCI keys
    // (legality doesn't matter — grade() records candidateUcis BEFORE any
    // legality check). Raw truncation (T=1) keeps exactly 2 of these 4
    // (a1 + the ascending-tie-break first tail move, cumulative 0.85+0.05 =
    // 0.90); T=2 flattening would keep all 4 — the discriminator this test
    // exploits.
    const OPPONENT_POLICY: Record<string, number> = { a1: 0.85, b1: 0.05, c1: 0.05, d1: 0.05 };

    const gradeCalls: GradeCall[] = [];
    const budget: SearchBudget = {
      maxNodes: 2,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 3,
      concurrency: 1,
      policyTemperature: 2,
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: ROOT_POLICY, [AFTER_E2E4_FEN]: OPPONENT_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: ROOT_GRADES }, gradeCalls),
    };

    await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const opponentCall = gradeCalls.find((c) => c.fen === AFTER_E2E4_FEN);
    expect(opponentCall).toBeDefined();
    // Untouched raw truncation kept exactly 2 candidates — proof the
    // opponent's policy was never flattened despite budget.policyTemperature=2.
    expect(opponentCall!.candidateUcis.sort()).toEqual(['a1', 'b1']);

    // Sanity: the root's OWN (rootMover-side) expansion DID see all 4
    // candidates flattened in by T=2 (contrast case, same distribution shape).
    const rootCall = gradeCalls.find((c) => c.fen === SIMPLE_WHITE_FEN);
    expect(rootCall).toBeDefined();
    expect(rootCall!.candidateUcis.length).toBe(4);
  });

  it('composes with D-01 findability: reverses the T=1 winner at T=2 via the SAME low-ELO fixture', async () => {
    // Identical fixture to the "Phase 159 D-01 findability ranking" describe
    // above: e2e4 (low prior, high V) vs e2e3 (high prior, lower V) at a low
    // root ELO. At T=1, e2e4's renormalized prior (~0.066) stays below
    // pRefForElo(600)=0.12 — e2e3 wins (asserted above). At T=2, flattening
    // raises e2e4's renormalized prior to ~0.149, ABOVE pRef — its
    // findability factor saturates to 1, and its higher practicalScore then
    // wins outright. This is D-06's "compose with zero extra glue" claim:
    // the reorder happens purely because child.prior (what T=2 changed) is
    // exactly what rankScore reads.
    const FEN = SIMPLE_WHITE_FEN;
    const POLICY: Record<string, number> = {
      e2e3: 0.85,
      e2e4: 0.06,
      e1d2: 0.04,
      e1f2: 0.03,
      e1d1: 0.01,
      e1f1: 0.01,
    };
    const GRADES: Record<string, MoveGrade> = {
      e2e4: { evalCp: 700, evalMate: null, depth: 10 },
      e2e3: { evalCp: 100, evalMate: null, depth: 10 },
    };
    const LOW_ELO = 600;

    const budgetT2: SearchBudget = {
      maxNodes: 1,
      elo: { w: LOW_ELO, b: LOW_ELO },
      maxPlies: 4,
      concurrency: 1,
      policyTemperature: 2,
    };
    const providers = (): EngineProviders => ({
      policy: makeFixedPolicy({ [FEN]: POLICY }),
      grade: makeFixedGrade({ [FEN]: GRADES }),
    });

    const snapshot = await mctsSearch(FEN, budgetT2, providers(), () => {}, freshSignal());

    expect(snapshot.rankedLines[0]?.rootMove).toBe('e2e4');
  });

  it('an extreme-flatness fixture never produces more than ROOT_CANDIDATE_HARD_CAP root children (D-07/Pitfall 6)', async () => {
    const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'; // 20 legal moves
    const budget: SearchBudget = {
      maxNodes: 1,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 1,
      concurrency: 1,
      policyTemperature: 2,
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [START_FEN]: uniformPolicyFromLegalMoves(START_FEN) }),
      grade: makeFixedGrade({}),
    };

    const snapshot = await mctsSearch(START_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.rankedLines.length).toBeLessThanOrEqual(ROOT_CANDIDATE_HARD_CAP);
  });
});

// ─── AbortSignal (WR-08 coverage) ───────────────────────────────────────────

describe('mctsSearch — abort', () => {
  it('aborting after the Nth snapshot stops promptly, resolves (not rejects), and keeps budgetExhausted=false', async () => {
    const SNAPSHOTS_BEFORE_ABORT = 2;
    const controller = new AbortController();
    const budget: SearchBudget = { maxNodes: 50, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshots: EngineSnapshot[] = [];
    const result = await mctsSearch(
      SIMPLE_WHITE_FEN,
      budget,
      providers,
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

describe('mctsSearch — illegal provider candidates', () => {
  it('drops illegal and malformed UCIs deterministically instead of rejecting the search', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const providers: EngineProviders = {
      // e7e5 is a BLACK move (illegal from SIMPLE_WHITE_FEN — the stale-FEN
      // race shape Phase 154's worker boundary can produce) and 'zz' is
      // malformed; both must be dropped, not crash the runner (WR-07).
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: { e2e4: 0.5, e7e5: 0.3, zz: 0.2 } }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.rankedLines.map((l) => l.rootMove)).toEqual(['e2e4']);
    expect(snapshot.nodesEvaluated).toBe(1);
  });
});

// ─── Degenerate provider: empty candidate set (WR-04) ───────────────────────

describe('mctsSearch — degenerate empty candidate set', () => {
  it('closes the node without calling grade() and without consuming node budget', async () => {
    const budget: SearchBudget = { maxNodes: 3, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const gradeCalls: GradeCall[] = [];
    const providers: EngineProviders = {
      // A provider returning NO candidates for a non-terminal position —
      // the degenerate case fallbackExpectimax already guarded (WR-04).
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: {} }),
      grade: makeFixedGrade({}, gradeCalls),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(gradeCalls).toEqual([]); // grade() never sees candidateUcis: []
    expect(snapshot.nodesEvaluated).toBe(0); // D-09: nothing was expanded
    expect(snapshot.rankedLines).toEqual([]);
  });
});

// ─── ENGINE-07: determinism, concurrency 1 and 2 ────────────────────────────

/** Wraps an async fabricated provider fn with an artificial, deliberately jittered resolution delay. */
function withJitter<Args extends unknown[], Result>(
  fn: (...args: Args) => Promise<Result>,
  jitterMsSequence: number[],
): (...args: Args) => Promise<Result> {
  let callIndex = 0;
  return async (...args: Args) => {
    const idx = callIndex;
    callIndex += 1;
    const delay = jitterMsSequence[idx % jitterMsSequence.length] ?? 0;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return fn(...args);
  };
}

// CR-01 fixture hardening: the original determinism fixtures used uniform
// policies and all-zero grades, pinning every node value at exactly 0.5 —
// structurally unable to detect a selection-order regression (any two search
// trees look identical when every value is 0.5). These constants derive a
// deterministic NON-neutral grade from (fen, uci) so different trees produce
// different outputs.
const GRADE_HASH_MULTIPLIER = 31;
const GRADE_EVAL_CP_SPAN = 300;

/** Deterministic non-neutral cp eval in (-GRADE_EVAL_CP_SPAN, GRADE_EVAL_CP_SPAN) derived from (fen, uci). */
function hashedEvalCp(fen: string, uci: string): number {
  const s = `${fen}|${uci}`;
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (Math.imul(h, GRADE_HASH_MULTIPLIER) + s.charCodeAt(i)) | 0;
  return (Math.abs(h) % (2 * GRADE_EVAL_CP_SPAN)) - GRADE_EVAL_CP_SPAN;
}

/** A fabricated `grade()` returning deterministic, varied (non-0.5-collapsing) grades at every node. */
function makeVariedGrade(): EngineProviders['grade'] {
  return async (fen, candidateUcis) => {
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      map.set(uci, { evalCp: hashedEvalCp(fen, uci), evalMate: null, depth: 10 });
    }
    return map;
  };
}

describe('mctsSearch — ENGINE-07 determinism', () => {
  const determinismBudget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };

  /** Non-neutral providers (CR-01): non-uniform root policy + varied grades everywhere. */
  function makeDeterminismProviders(): EngineProviders {
    return {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeVariedGrade(),
    };
  }

  it('produces toEqual final snapshots AND toEqual full onSnapshot sequences across two repeated runs', async () => {
    const snapshotsRun1: EngineSnapshot[] = [];
    const resultRun1 = await mctsSearch(
      SIMPLE_WHITE_FEN,
      determinismBudget,
      makeDeterminismProviders(),
      (s) => snapshotsRun1.push(structuredClone(s)),
      freshSignal(),
    );

    const snapshotsRun2: EngineSnapshot[] = [];
    const resultRun2 = await mctsSearch(
      SIMPLE_WHITE_FEN,
      determinismBudget,
      makeDeterminismProviders(),
      (s) => snapshotsRun2.push(structuredClone(s)),
      freshSignal(),
    );

    // Guard against a degenerate fixture: at least one value must differ from
    // the 0.5 neutral score, or the equality assertions below prove nothing.
    expect(resultRun1.rankedLines.some((l) => l.practicalScore !== 0.5)).toBe(true);
    expect(resultRun2).toEqual(resultRun1);
    expect(snapshotsRun2).toEqual(snapshotsRun1);
    expect(snapshotsRun1.length).toBeGreaterThan(0);
  });

  it('produces deterministic output + snapshot sequence across repeated concurrency=2 runs under DIFFERENT resolution jitters', async () => {
    // CR-01: this test previously asserted c=2 output equals c=1 output.
    // That is NOT a real invariant (see the mctsSearch.ts module header's
    // "Determinism scope"): pending-exclusion forces same-round breadth at
    // c=2, so c=1 and c=2 may legitimately build different trees. What D-03
    // actually locks is determinism PER concurrency level with canonical-
    // dispatch-order application — proven here by running c=2 twice under
    // deliberately different, non-monotonic resolution jitters (later-
    // dispatched calls can resolve BEFORE earlier-dispatched ones; only
    // Promise.all's order-preserving application keeps this bit-identical).
    const budgetC2: SearchBudget = { ...determinismBudget, concurrency: 2 };

    const providersA: EngineProviders = {
      policy: withJitter(makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }), [30, 5, 20, 0]),
      grade: withJitter(makeVariedGrade(), [10, 25, 0, 15]),
    };
    const snapshotsA: EngineSnapshot[] = [];
    const resultA = await mctsSearch(
      SIMPLE_WHITE_FEN,
      budgetC2,
      providersA,
      (s) => snapshotsA.push(structuredClone(s)),
      freshSignal(),
    );

    const providersB: EngineProviders = {
      policy: withJitter(makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }), [0, 40, 10, 25]),
      grade: withJitter(makeVariedGrade(), [35, 0, 20, 5]),
    };
    const snapshotsB: EngineSnapshot[] = [];
    const resultB = await mctsSearch(
      SIMPLE_WHITE_FEN,
      budgetC2,
      providersB,
      (s) => snapshotsB.push(structuredClone(s)),
      freshSignal(),
    );

    expect(resultA.rankedLines.some((l) => l.practicalScore !== 0.5)).toBe(true);
    expect(resultB).toEqual(resultA);
    expect(snapshotsB).toEqual(snapshotsA);
    expect(snapshotsA.length).toBeGreaterThan(0);
  });
});

