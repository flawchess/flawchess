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

import { describe, it, expect, vi } from 'vitest';
import { Chess } from 'chess.js';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import { mctsSearch } from '../mctsSearch';
import { ROOT_CANDIDATE_HARD_CAP, applyPolicyTemperature } from '../policyTemperature';
import { truncateAndRenormalize } from '../select';
import { gradingDepthForTreeDepth, GRADING_ROOT_DEPTH } from '../gradingLadder';
import type { EngineProviders, EngineSnapshot, SearchBudget, MoveGrade } from '../types';
import {
  makeFixedPolicy,
  makeVariedGrade,
  uniformPolicyFromLegalMoves,
  withJitter,
  type PolicyCall,
} from './searchTestProviders';

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

/**
 * Test-local stop-rule guard allowance (Phase 225 D-01/D-02) — deliberately
 * NOT the production `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance`
 * (0.04, `reports/engine-search-fixes-225/d02-allowance.md`). A wider
 * test-local window keeps the guard-window arithmetic in these fixtures
 * easy to verify by hand (window 0.05 + 0.1 = 0.15).
 */
const GUARD_TEST_ALLOWANCE = 0.1;

/** Never-aborted signal for tests that don't exercise cancellation. */
function freshSignal(): AbortSignal {
  return new AbortController().signal;
}

// ─── Fabricated-provider helpers ────────────────────────────────────────────

interface GradeCall {
  fen: string;
  candidateUcis: string[];
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

/**
 * Phase 225 D-01: builds a `grade()` fixture where every reply at a root
 * child's OWN position is graded with that SAME child's own `evalCp` — so
 * `recomputeValue`'s prior-weighted expectation over equal-valued children
 * leaves the child's own `.value` unchanged after its first expansion.
 * Isolates the guard's visit-based settlement test from any actual value
 * drift the boost would otherwise cause. Replies are read from chess.js's
 * real legal-move list at the child's position — never hand-enumerated.
 */
function buildChildOwnGradeFixture(
  rootFen: string,
  rootGrades: Record<string, MoveGrade>,
): Record<string, Record<string, MoveGrade>> {
  const byFen: Record<string, Record<string, MoveGrade>> = { [rootFen]: rootGrades };
  for (const [uci, grade] of Object.entries(rootGrades)) {
    const chess = new Chess(rootFen);
    chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.length > 4 ? uci[4] : undefined });
    const childFen = chess.fen();
    const replyUcis = chess.moves({ verbose: true }).map((m) => `${m.from}${m.to}${m.promotion ?? ''}`);
    const replyGrades: Record<string, MoveGrade> = {};
    for (const replyUci of replyUcis) replyGrades[replyUci] = grade;
    byFen[childFen] = replyGrades;
  }
  return byFen;
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

  it("modalStats carries each ply's RAW Maia prob (not the renormalized prior) + white-POV eval (Phase 160)", async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const e2e4 = snapshot.rankedLines.find((l) => l.rootMove === 'e2e4');
    expect(e2e4).toBeDefined();
    // Index-aligned with modalPath, one entry per ply.
    expect(e2e4!.modalStats).toHaveLength(e2e4!.modalPath.length);
    // The RAW policy value (0.5) — NOT the renormalized prior (0.5 / 0.95-mass
    // ≈ 0.526). This is exactly what makes the move-chip hover header agree with
    // the raw Maia % shown in the prose move popovers.
    expect(e2e4!.modalStats[0]!.maiaProb).toBeCloseTo(0.5, 10);
    // Per-ply objective eval = the graded white-POV cp of the resulting position.
    expect(e2e4!.modalStats[0]!.objectiveEvalCp).toBe(200);
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

  it('INJECT-02 observable-ranking proof: a post-fix injected move with a real prior ranks ABOVE a known weaker organic candidate whose rankScore it beats', async () => {
    // Policy shaped so e2e4 (injected) carries a genuinely non-trivial raw
    // probability yet is still dropped by truncateAndRenormalize's 90%-mass
    // cut — e2e3 (0.55) + e1d2 (0.35) already reach cumulative 0.90 before
    // e2e4 is even considered. This is a materially different shape than the
    // D-04 test above (whose dropped-tail probability is a near-zero 0.01):
    // INJECT-02 needs the injected candidate's prior to be big enough, once
    // seeded correctly, to outrank a real organic competitor.
    //
    // Phase 225 D-10a: organic grades are SWAPPED from the original Phase
    // 196 fixture (e2e3 now the WORSE organic grade, e1d2 the better one) so
    // this test's derivation depends on the actual rankScore comparison, not
    // merely on which organic candidate happens to have the lower grade —
    // e1d2 is deliberately the higher-graded organic move here.
    const POLICY: Record<string, number> = {
      e2e3: 0.55,
      e1d2: 0.35, // the "known weaker organic": kept, high prior, mediocre grade
      e2e4: 0.07, // the injected candidate: dropped, non-trivial raw prob, strong grade
      e1f2: 0.01,
      e1d1: 0.01,
      e1f1: 0.01,
    };
    const GRADES: Record<string, MoveGrade> = {
      e2e3: { evalCp: 10, evalMate: null, depth: 10 },
      e1d2: { evalCp: 50, evalMate: null, depth: 10 }, // mediocre — the "known weaker organic"
      e2e4: { evalCp: 700, evalMate: null, depth: 10 }, // clearly better value
    };
    // pRefForElo(2200) = 0.015, well below e2e3's (0.55/0.90≈0.611), e1d2's
    // (0.35/0.90≈0.389) AND e2e4's post-fix seeded prior (0.07/0.90≈0.078) —
    // all three saturate rankScore's findability factor to 1, so the ranking
    // below reduces to a direct practicalScore comparison: es(700cp)≈0.929 >
    // es(50cp)≈0.546 > es(10cp)≈0.509 — an unambiguous derivation rather than
    // a coincidence of the findability curve's shape at this ELO.
    const ELO = 2200;
    const budget: SearchBudget = {
      maxNodes: 1,
      elo: { w: ELO, b: ELO },
      maxPlies: 3,
      concurrency: 1,
      extraRootMoves: ['e2e4'],
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const injectedIndex = snapshot.rankedLines.findIndex((l) => l.rootMove === 'e2e4');
    const weakerOrganicIndex = snapshot.rankedLines.findIndex((l) => l.rootMove === 'e1d2');
    expect(injectedIndex).toBeGreaterThanOrEqual(0);
    expect(weakerOrganicIndex).toBeGreaterThanOrEqual(0);
    // Phase 225 D-10a: with the injected seed prior forced to 0, e2e4 scores
    // min(value, V_fallback) instead of saturating to its own value —
    // V_fallback over {e2e3, e1d2, e2e4-at-prior-0} ≈ 0.523, still BELOW
    // e1d2's saturated rankScore ≈0.546 — so the mutation-checked assertion
    // below would fail (e2e4 sorts AFTER e1d2), exactly the INJECT-02
    // regression this test exists to catch (mutation check recorded in the
    // 225-06 SUMMARY, per RESEARCH C-4/D-10a).
    expect(injectedIndex).toBeLessThan(weakerOrganicIndex);
  });
});

// ─── Phase 159 D-01: findability ranking reorders the root at low ELO ──────
// Phase 225 D-10a/D-10e (SEED-170 item 3): rankScore now blends toward
// V_fallback (the prior-weighted mean of the root's own children), never
// toward 0 — so a hard-to-find move far better than the findable
// alternative is no longer suppressed toward the bottom. This is an
// intentional, user-accepted reversal of Phase 159's original showcase
// fixture (D-10e), not a regression.

describe('mctsSearch — Phase 159 D-01 findability ranking (Phase 225 D-10a/D-10e: blend toward V_fallback)', () => {
  // e2e4 (low prior 0.06, high V via evalCp=700) vs e2e3 (high prior 0.85,
  // lower V via evalCp=100), at a low root ELO (600, pRefForElo(600)=0.12).
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

  it('promotes the far-better hard-to-find move above the findable-but-worse move via the V_fallback pull, while practicalScore stays unchanged', async () => {
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
    expect(e2e4Line!.practicalScore).toBeGreaterThan(e2e3Line!.practicalScore);

    // Truncation keeps exactly {e2e3: 0.85, e2e4: 0.06} (cumulative 0.91
    // crosses the 0.9 mass threshold at e2e4) — renormalized priors
    // e2e3≈0.934, e2e4≈0.066. V(e2e3)=es(100cp)≈0.591, V(e2e4)=es(700cp)≈
    // 0.929, so V_fallback = rankFallbackValue over exactly these two
    // children ≈ 0.613. rankScore(e2e3) saturates (prior 0.934 >> pRef600
    // 0.12) to its own value ≈0.591. rankScore(e2e4): f = min(1,
    // 0.066/0.12) ≈ 0.549 => 0.549*0.929 + 0.451*min(0.929, 0.613) ≈ 0.787.
    // 0.787 > 0.591, so e2e4 now ranks FIRST — the Phase 159 showcase
    // ordering is intentionally reversed here (D-10e, user-accepted).
    expect(snapshot.rankedLines[0]?.rootMove).toBe('e2e4');
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

  it('composes with D-01 findability: reverses the T=1 winner at T=2 via a three-candidate fixture (Phase 225 D-10a/D-10e)', async () => {
    // Phase 225 D-10a/D-10e: the OLD two-candidate composition fixture (e2e3
    // vs e2e4 only) no longer reverses at T=1->T=2 — under the V_fallback
    // pull e2e4 already wins at T=1 (see the "Phase 159 D-01 findability
    // ranking" describe above), so the "reverses" claim needs a THIRD
    // candidate (e1d2) whose mediocre grade keeps V_fallback low enough at
    // T=1 that e2e4 does NOT yet clear it, while T=2's flattening still
    // pushes e2e4's renormalized prior over pRefForElo(600)=0.12.
    const FEN = SIMPLE_WHITE_FEN;
    const POLICY: Record<string, number> = {
      e2e3: 0.5,
      e1d2: 0.38,
      e2e4: 0.06,
      e1f2: 0.03,
      e1d1: 0.02,
      e1f1: 0.01,
    };
    const GRADES: Record<string, MoveGrade> = {
      e2e4: { evalCp: 700, evalMate: null, depth: 10 }, // far better, low prior
      e2e3: { evalCp: 350, evalMate: null, depth: 10 }, // findable, good
      e1d2: { evalCp: -300, evalMate: null, depth: 10 }, // findable-ish, bad — keeps V_fallback low at T=1
    };
    const LOW_ELO = 600;

    const budgetT1: SearchBudget = {
      maxNodes: 1,
      elo: { w: LOW_ELO, b: LOW_ELO },
      maxPlies: 4,
      concurrency: 1,
    };
    const budgetT2: SearchBudget = { ...budgetT1, policyTemperature: 2 };
    const providers = (): EngineProviders => ({
      policy: makeFixedPolicy({ [FEN]: POLICY }),
      grade: makeFixedGrade({ [FEN]: GRADES }),
    });

    // T=1: truncation keeps exactly {e2e3: 0.50, e1d2: 0.38, e2e4: 0.06}
    // (cumulative 0.94 crosses the 0.9 mass threshold at e2e4); renormalized
    // priors ~0.532/0.404/0.064. V(e2e3)=es(350cp)~=0.784, V(e1d2)=es(-300cp)
    // ~=0.249, V(e2e4)=es(700cp)~=0.929 => V_fallback ~=0.577 (pulled down by
    // e1d2's bad grade). rankScore(e2e3) saturates (prior >> pRef) = 0.784.
    // rankScore(e2e4): f = min(1, 0.064/0.12) ~=0.549 => 0.549*0.929 +
    // 0.451*min(0.929, 0.577) ~=0.764 < 0.784 — e2e3 wins at T=1.
    const snapshotT1 = await mctsSearch(FEN, budgetT1, providers(), () => {}, freshSignal());
    expect(snapshotT1.rankedLines[0]?.rootMove).toBe('e2e3');

    // T=2: flattening raises e2e4's renormalized prior to ~0.130, ABOVE
    // pRefForElo(600)=0.12 — its findability factor saturates to 1, and its
    // own (unchanged) practicalScore (0.929) then wins outright over e2e3's
    // saturated 0.784. This is D-06's "compose with zero extra glue" claim:
    // the reorder happens purely because child.prior (what T=2 changed) is
    // exactly what rankScore reads.
    const snapshotT2 = await mctsSearch(FEN, budgetT2, providers(), () => {}, freshSignal());
    expect(snapshotT2.rankedLines[0]?.rootMove).toBe('e2e4');
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

  it('extreme-flatness INJECT-01 regression: an out-of-mass-cut injected UCI survives BOTH the mass cut and the hard cap', async () => {
    const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'; // 20 legal moves
    const POLICY_TEMPERATURE = 2;
    const uniformPolicy = uniformPolicyFromLegalMoves(START_FEN);
    // 196-RESEARCH.md Assumption A2: the exact dropped-tail UCI is unverified
    // by name — derive it from the SAME pipeline dispatchExpansion actually
    // runs (temperature reshape THEN truncation), not from the raw policy:
    // floating-point drift from applyPolicyTemperature's renormalization can
    // shift which UCI(s) cross the 90%-mass cutoff by one position vs the raw
    // distribution (measured: raw drops 2 of 20 uniform moves, T=2 drops only
    // 1) — so deriving off the raw policy would pick a UCI the real T=2 run
    // never actually drops, defeating the regression. Assert the fixture's
    // own premise (a dropped UCI must exist) rather than assume it.
    const effectivePolicy = applyPolicyTemperature(uniformPolicy, POLICY_TEMPERATURE);
    const kept = truncateAndRenormalize(effectivePolicy);
    const droppedUci = Object.keys(uniformPolicy).find((uci) => !kept.has(uci));
    expect(droppedUci).toBeDefined();
    const injectedUci = droppedUci as string;

    const budget: SearchBudget = {
      maxNodes: 1,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 1,
      concurrency: 1,
      policyTemperature: POLICY_TEMPERATURE,
      extraRootMoves: [injectedUci],
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [START_FEN]: uniformPolicy }),
      grade: makeFixedGrade({}),
    };

    const snapshot = await mctsSearch(START_FEN, budget, providers, () => {}, freshSignal());

    // Pre-fix: 19 organic + 1 injected = 20 candidates, the injected one
    // seeded at prior 0 sorted dead last by applyRootCandidateHardCap's own
    // comparator, guaranteeing it among the entries the 15-cap dropped.
    expect(snapshot.rankedLines.length).toBeLessThanOrEqual(ROOT_CANDIDATE_HARD_CAP);
    expect(snapshot.rankedLines.some((l) => l.rootMove === injectedUci)).toBe(true);
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

  it('Phase 194 ABORT-01: every providers.grade() call receives the search\'s own AbortSignal, by reference, on every expansion', async () => {
    const controller = new AbortController();
    const budget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const gradeSpy = vi.fn(makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }));
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: gradeSpy,
    };

    await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, controller.signal);

    expect(gradeSpy.mock.calls.length).toBeGreaterThan(0);
    for (const call of gradeSpy.mock.calls) {
      // Reference identity, not merely "defined" — a NEW AbortSignal that
      // happens to report the same .aborted value would pass a weaker check
      // but would NOT actually let WorkerPool.grade's abort listener see this
      // search's real cancel.
      expect(call[2]).toBe(controller.signal);
    }
  });

  it('8XN-2: every providers.policy() call receives the search\'s own AbortSignal, by reference, as its 4th argument', async () => {
    const controller = new AbortController();
    const budget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const policyCalls: (AbortSignal | undefined)[] = [];
    const providers: EngineProviders = {
      policy: async (fen, elo, side, signal) => {
        policyCalls.push(signal);
        return (fen === SIMPLE_WHITE_FEN ? SIMPLE_WHITE_POLICY : uniformPolicyFromLegalMoves(fen)) as Record<
          string,
          number
        >;
      },
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    };

    await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, controller.signal);

    expect(policyCalls.length).toBeGreaterThan(0);
    for (const signal of policyCalls) {
      // Reference identity (not merely "defined") — same rationale as the
      // grade() signal check above: maiaQueue's abort listener must see THIS
      // search's real controller, not a lookalike.
      expect(signal).toBe(controller.signal);
    }
  });

  it('LADDER-02: every providers.grade() call receives a resolved grading-depth 4th argument, never undefined', async () => {
    const controller = new AbortController();
    // Budget sized so the tree actually descends past the ladder table's
    // length: the shipped table is [14, 14] with floor 10, so a search that
    // only reaches tree depth 1 grades everything at 14 and cannot demonstrate
    // variation. 64 nodes / 6 plies is the point at which this fixture's
    // descent first reached the floor rung under the older, longer [14, 14, 14]
    // table (measured, 195-06 Task 2); the 2026-07-31 override moved the floor
    // one ply shallower, so this budget now reaches it strictly sooner and the
    // assertions below only get easier to satisfy — kept as-is rather than
    // re-tightened, since a smaller budget would weaken the other calls' cover.
    const budget: SearchBudget = { maxNodes: 64, elo: NEUTRAL_BUDGET_ELO, maxPlies: 6, concurrency: 1 };
    const gradeSpy = vi.fn(makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }));
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: gradeSpy,
    };

    await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, controller.signal);

    expect(gradeSpy.mock.calls.length).toBeGreaterThan(0);

    // Every 4th arg must be one of the values gradingDepthForTreeDepth(d) can
    // produce for d in [0, maxPlies], and the FIRST call (always the root
    // expansion) must be exactly GRADING_ROOT_DEPTH.
    //
    // Why membership rather than per-call exact leaf-depth equality: the spy
    // observes (fen, ucis, signal, depth) only, and this fixture drives every
    // node from a single FEN, so a call's own tree depth is not recoverable
    // from the spy's arguments. Membership in the ladder's exact image plus
    // the pinned-root check plus the distinct-rung assertion below is what is
    // provable here; a per-call equality assertion would need a fixture that
    // varies FEN by depth.
    const possibleDepths = new Set<number>();
    for (let d = 0; d <= budget.maxPlies; d++) possibleDepths.add(gradingDepthForTreeDepth(d));

    gradeSpy.mock.calls.forEach((call, i) => {
      const gradingDepthArg = call[3];
      expect(gradingDepthArg).not.toBeUndefined(); // the core always resolves a rung
      expect(possibleDepths.has(gradingDepthArg as number)).toBe(true);
      if (i === 0) expect(gradingDepthArg).toBe(GRADING_ROOT_DEPTH); // first call is always the root
    });

    // LADDER-02's observable claim: a real search grades at MORE THAN ONE
    // depth. The membership assertion above is satisfied by a flat table too,
    // so without this the requirement could pass on a ladder that never
    // varies. Flattening GRADING_DEPTH_LADDER/GRADING_DEPTH_FLOOR to a single
    // value must break this line (mutation-verified, 195-06 Task 2).
    const observedDepths = new Set(gradeSpy.mock.calls.map((call) => call[3] as number));
    expect(observedDepths.size).toBeGreaterThan(1);
    expect(observedDepths.has(GRADING_ROOT_DEPTH)).toBe(true);
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

// ─── 8XN-7: non-abort empty grade() Map closes the leaf as a dead end ───────
//
// Before this fix, `applyExpansion` created every candidate child at
// NEUTRAL_EXPECTED_SCORE whenever `grade()` resolved an empty Map for a
// non-empty candidate set (the pool's watchdog/dead-pool/no-live-slot
// fallback) — fabricated 0.5 grades that then backed up into ancestor
// values. The revert proof for this describe block is recorded in
// 260927-8xn-SUMMARY.md: temporarily deleting the guard in
// `dispatchExpansion` makes the non-root case below fail (practicalScore
// becomes NEUTRAL_EXPECTED_SCORE-derived instead of the real grade), while
// the root-exemption case keeps passing either way.

/** The child FEN reached from SIMPLE_WHITE_FEN by e2e4 (black to move), verified with chess.js. */
const SIMPLE_WHITE_AFTER_E2E4_FEN = '4k3/8/8/8/4P3/8/8/4K3 b - - 0 1';

describe('mctsSearch — 8XN-7 empty non-abort grade() closes a dead end', () => {
  it('non-root: a child leaf whose grade() resolves empty stays at its own grade, is never re-expanded, and does not consume node budget', async () => {
    const budget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const gradeCalls: GradeCall[] = [];
    const grade: EngineProviders['grade'] = async (fen, candidateUcis) => {
      gradeCalls.push({ fen, candidateUcis: [...candidateUcis] });
      if (fen === SIMPLE_WHITE_AFTER_E2E4_FEN) return new Map<string, MoveGrade>(); // degenerate pool failure
      const map = new Map<string, MoveGrade>();
      for (const uci of candidateUcis) {
        map.set(uci, SIMPLE_WHITE_GRADES[uci] ?? { evalCp: 0, evalMate: null, depth: 10 });
      }
      return map;
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade,
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const e2e4Line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e4');
    expect(e2e4Line).toBeDefined();
    // The leaf keeps the value ITS OWN parent's grade gave it — never a
    // 0.5-derived value from fabricated children.
    expect(e2e4Line!.practicalScore).toBeCloseTo(
      evalToExpectedScore(SIMPLE_WHITE_GRADES.e2e4!.evalCp, SIMPLE_WHITE_GRADES.e2e4!.evalMate, 'white'),
      10,
    );
    expect(e2e4Line!.modalPath).toEqual(['e2e4']); // no children were ever attached
    // grade() is called exactly once for the failed FEN — selectPath's
    // closure marking (isClosed/propagateClosure, reused from WR-04) means
    // the dead leaf is never selected again.
    const failedCalls = gradeCalls.filter((c) => c.fen === SIMPLE_WHITE_AFTER_E2E4_FEN);
    expect(failedCalls.length).toBe(1);
    // The failed expansion attempt is not counted (D-09): every OTHER
    // dispatched leaf produced children and counted as one evaluated node,
    // but the failed one did not — nodesEvaluated is exactly one less than
    // the total number of dispatched (policy+grade) attempts. Without the
    // 8XN-7 guard, the failed attempt would ALSO increment nodesEvaluated
    // (this is the assertion the revert proof in the SUMMARY breaks).
    expect(snapshot.nodesEvaluated).toBe(gradeCalls.length - failedCalls.length);
  });

  it('root exemption: an empty grade() Map at the root keeps today\'s behavior — candidates still rank at NEUTRAL_EXPECTED_SCORE', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: async () => new Map<string, MoveGrade>(), // always empty, even for the root
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    // The root is NOT closed as a dead end: its Maia candidates still
    // surface, each at the pre-existing NEUTRAL_EXPECTED_SCORE fallback.
    expect(snapshot.rankedLines.length).toBeGreaterThan(0);
    for (const line of snapshot.rankedLines) {
      expect(line.practicalScore).toBe(0.5);
    }
  });

  it('partial map: an omitted candidate keeps the pre-existing NEUTRAL_EXPECTED_SCORE fallback (locked, not part of 8XN-7)', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const TWO_CANDIDATE_POLICY: Record<string, number> = { e2e4: 0.5, e2e3: 0.5 };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: TWO_CANDIDATE_POLICY }),
      // Omits e2e3 — a partial (non-empty) map, distinct from the 8XN-7 empty case.
      grade: async () => new Map<string, MoveGrade>([['e2e4', SIMPLE_WHITE_GRADES.e2e4!]]),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    const e2e4Line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e4');
    const e2e3Line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e3');
    expect(e2e4Line).toBeDefined();
    expect(e2e3Line).toBeDefined();
    expect(e2e4Line!.practicalScore).toBeCloseTo(
      evalToExpectedScore(SIMPLE_WHITE_GRADES.e2e4!.evalCp, SIMPLE_WHITE_GRADES.e2e4!.evalMate, 'white'),
      10,
    );
    expect(e2e3Line!.practicalScore).toBe(0.5); // ungraded candidate keeps the NEUTRAL fallback
  });
});

// ─── Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02): bot-play stop rule ─

describe('mctsSearch — Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02) bot-play stop rule', () => {
  it('clear-winner guard: an in-window unvisited runner-up (e2e3) delays the stop until settled, while an out-of-window unvisited child (e1d2) never blocks it', async () => {
    // Phase 225 D-01 INTENDED BEHAVIOR CHANGE (RESEARCH Pitfall 2 — this is
    // a rewrite, not a loosened assertion). Before the guard, this exact
    // fixture stopped at nodesEvaluated 1 (the pre-225 test asserted
    // `toBe(1)`): e2e4 (200cp, es~0.676) already cleared e2e3 (50cp,
    // es~0.546) by ~0.13 >= marginThreshold(0.05) right after the root's OWN
    // expansion — comparing a value NOBODY had visited yet (every root
    // child, including the top, is unvisited at node 1). With the guard
    // (window = marginThreshold 0.05 + GUARD_TEST_ALLOWANCE 0.1 = 0.15):
    // e2e3's gap (~0.13) is IN-window and unvisited, so it blocks the stop;
    // e1d2's gap (~0.20, -30cp/es~0.472) is OUT-of-window, so it never
    // blocks regardless of its own visit state (D-01's "amended" window
    // semantics, CONTEXT.md).
    //
    // `buildChildOwnGradeFixture` grades every reply at a root child's OWN
    // position with that SAME child's own evalCp, so a root child's first
    // expansion (backupExpectation over equal-valued children) leaves its
    // OWN `.value` unchanged — isolating the guard's VISIT-based settlement
    // logic from any actual value drift the real opponent-error boost would
    // otherwise cause (Task 1's fixture is deliberately boost-free; the
    // production allowance is measured separately, D-02).
    const gradesByFen = buildChildOwnGradeFixture(SIMPLE_WHITE_FEN, SIMPLE_WHITE_GRADES);
    const budget: SearchBudget = {
      maxNodes: 20,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 2, // grandchildren (root children's own children) are depth-capped dead ends
      concurrency: 1,
      stopRule: {
        marginThreshold: 0.05,
        epsilonThreshold: 0.02,
        stabilityWindow: 1,
        minNodes: 1,
        rootGuardBoostAllowance: GUARD_TEST_ALLOWANCE,
      },
    };
    const snapshots: EngineSnapshot[] = [];
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade(gradesByFen),
    };

    const snapshot = await mctsSearch(
      SIMPLE_WHITE_FEN,
      budget,
      providers,
      (s) => snapshots.push(structuredClone(s)),
      freshSignal(),
    );

    // Derivation from select.ts's root PUCT formula (C_PUCT=1.4, floor-
    // boosted priors ~0.526/0.316/0.158 for e2e4/e2e3/e1d2 — all already
    // above ROOT_PRIOR_FLOOR so unaffected by flooring): node 1 is the
    // root's own expansion (every child unvisited, Q gap already >=
    // marginThreshold but the guard blocks). Node 2 re-selects e2e4 (its
    // exploration term still edges out e2e3's at N=1) for its OWN first
    // expansion, settling it — a depth-capped grandchild discovery along the
    // way bumps visits without consuming a node. Node 3 then selects e2e3
    // (its Q term now wins over e2e4's shrunk exploration term at N=2),
    // settling it — at which point e1d2 (out-of-window) is the ONLY
    // unsettled child, so the clear-winner branch finally fires. Pinned
    // from an observed run against this exact fixture; re-derive from
    // select.ts's PUCT formula in this comment if the fixture ever changes.
    expect(snapshot.stopReason).toBe('early-stop');
    expect(snapshot.nodesEvaluated).toBe(3);

    const byMove = new Map(snapshot.rankedLines.map((l) => [l.rootMove, l]));
    expect(byMove.get('e2e4')!.visits).toBeGreaterThanOrEqual(1);
    expect(byMove.get('e2e3')!.visits).toBeGreaterThanOrEqual(1);
    expect(byMove.get('e1d2')!.visits).toBe(0);

    // Stream property: the GUARD, not the margin, is what delayed the stop —
    // every pre-stop snapshot where the top-vs-runner-up margin already met
    // marginThreshold still has an in-window line sitting at visits 0.
    const guardWindow = budget.stopRule!.marginThreshold + budget.stopRule!.rootGuardBoostAllowance;
    expect(snapshots.length).toBeGreaterThan(1);
    for (const s of snapshots.slice(0, -1)) {
      const lines = new Map(s.rankedLines.map((l) => [l.rootMove, l]));
      const top = lines.get('e2e4')!;
      const runnerUp = Math.max(lines.get('e2e3')!.practicalScore, lines.get('e1d2')!.practicalScore);
      if (top.practicalScore - runnerUp >= budget.stopRule!.marginThreshold) {
        const hasUnsettledInWindow = [...lines.values()].some(
          (l) => l.visits === 0 && top.practicalScore - l.practicalScore <= guardWindow,
        );
        expect(hasUnsettledInWindow).toBe(true);
      }
    }
  });

  it('closed-top guard: a terminal (mate-in-1) top root child counts as settled at zero visits, so the search still early-stops at node 1', async () => {
    // RESEARCH Pitfall 1: a "settled = visits >= 1" test alone (no isClosed
    // clause) would stall this clear-winner stop forever — a checkmating
    // root child is never itself visited (createChildNode closes a terminal
    // child immediately at creation; selectPath's candidate filter excludes
    // closed children, so it can never be walked into and re-discovered).
    // e1e8 delivers immediate mate (value ~1, closed at creation, visits 0).
    // The ordinary move e1e2 (0cp, es 0.5) sits at gap ~0.5 — far outside
    // the guard window (0.05 + 0.1 = 0.15) — so it never blocks regardless
    // of its own (unvisited) settlement state.
    const MATE_TOP_POLICY: Record<string, number> = { [MATE_IN_1_MOVE]: 0.6, e1e2: 0.3, h1g2: 0.1 };
    const budget: SearchBudget = {
      maxNodes: 20,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 4,
      concurrency: 1,
      stopRule: {
        marginThreshold: 0.05,
        epsilonThreshold: 0.02,
        stabilityWindow: 1,
        minNodes: 1,
        rootGuardBoostAllowance: GUARD_TEST_ALLOWANCE,
      },
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [MATE_IN_1_FEN]: MATE_TOP_POLICY }),
      grade: makeFixedGrade({ [MATE_IN_1_FEN]: { e1e2: { evalCp: 0, evalMate: null, depth: 10 } } }),
    };

    const snapshot = await mctsSearch(MATE_IN_1_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.nodesEvaluated).toBe(1);
    expect(snapshot.stopReason).toBe('early-stop');
    expect(snapshot.rankedLines[0]?.rootMove).toBe(MATE_IN_1_MOVE);
    const topLine = snapshot.rankedLines.find((l) => l.rootMove === MATE_IN_1_MOVE);
    expect(topLine!.visits).toBe(0); // never visited — settled via isClosed, not a visit bump
  });

  it('near-tie-flatness: closely-bunched root moves stop the search even with no clear winner', async () => {
    // e2e4/e2e3/e1d2 graded 15/10/5cp — spread ~0.0092 (within epsilon 0.01)
    // but top-runnerup margin ~0.0046 (BELOW marginThreshold 0.02, so the
    // clear-winner side alone would NOT fire) — isolates the flatness branch
    // of the OR.
    //
    // D-03 residual (deliberately NOT guarded, CONTEXT.md): the flatness
    // branch never consults hasUnsettledInWindow, so it stops here with
    // every root child still at visits 0 — stopping on a near-tie is
    // low-stakes, and item 1's guard scope is the clear-winner branch only.
    const CLOSE_GRADES: Record<string, MoveGrade> = {
      e2e4: { evalCp: 15, evalMate: null, depth: 10 },
      e2e3: { evalCp: 10, evalMate: null, depth: 10 },
      e1d2: { evalCp: 5, evalMate: null, depth: 10 },
    };
    const budget: SearchBudget = {
      maxNodes: 20,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 4,
      concurrency: 1,
      stopRule: {
        marginThreshold: 0.02,
        epsilonThreshold: 0.01,
        stabilityWindow: 1,
        minNodes: 1,
        rootGuardBoostAllowance: GUARD_TEST_ALLOWANCE,
      },
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: CLOSE_GRADES }),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.nodesEvaluated).toBeLessThan(budget.maxNodes);
    expect(snapshot.nodesEvaluated).toBe(1);
    expect(snapshot.stopReason).toBe('early-stop');
    // D-03 residual, explicit: every root child is STILL unvisited at the
    // stop — the guard never delayed this branch.
    for (const line of snapshot.rankedLines) {
      expect(line.visits).toBe(0);
    }
  });

  it('min-nodes floor: neither side of the rule fires before minNodes expansions have run', async () => {
    // marginThreshold=0/epsilonThreshold=0/stabilityWindow=1 make both sides
    // of the rule trivially satisfied at EVERY check (an all-neutral-grade
    // fixture ties every root child's value at exactly 0.5, forever — a
    // recompute of an all-0.5 subtree backs up to 0.5 again, so the tie never
    // drifts) — isolating minNodes as the ONLY gate on when the stop fires.
    const MIN_NODES_FLOOR = 5;
    const budget: SearchBudget = {
      maxNodes: 20,
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 10,
      concurrency: 1,
      stopRule: {
        marginThreshold: 0,
        epsilonThreshold: 0,
        stabilityWindow: 1,
        minNodes: MIN_NODES_FLOOR,
        rootGuardBoostAllowance: GUARD_TEST_ALLOWANCE,
      },
    };
    const providers: EngineProviders = { policy: makeFixedPolicy({}), grade: makeFixedGrade({}) };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(snapshot.nodesEvaluated).toBe(MIN_NODES_FLOOR);
    expect(snapshot.stopReason).toBe('early-stop');
  });

  it('stopRule omitted vs explicitly undefined: byte-identical snapshots (backward-compat no-op, Pattern 2 pitfall)', async () => {
    const baseBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const providers = (): EngineProviders => ({
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_GRADES }),
    });

    const omitted: SearchBudget = { ...baseBudget };
    const explicitlyUndefined: SearchBudget = { ...baseBudget, stopRule: undefined };

    const snapshotOmitted = await mctsSearch(SIMPLE_WHITE_FEN, omitted, providers(), () => {}, freshSignal());
    const snapshotExplicit = await mctsSearch(
      SIMPLE_WHITE_FEN,
      explicitlyUndefined,
      providers(),
      () => {},
      freshSignal(),
    );

    expect(snapshotExplicit).toEqual(snapshotOmitted);
    // Sanity: this is the pre-existing full-budget path, not an accidental early-stop.
    expect(snapshotOmitted.stopReason).toBe('budget');
  });
});

// ─── ENGINE-07: determinism, concurrency 1 and 2 ────────────────────────────

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

// ─── Phase 226 D-18: gradeRoot routing ──────────────────────────────────────

describe('mctsSearch — gradeRoot routing (Phase 226 D-18)', () => {
  it('calls gradeRoot exactly once, for the root fen with its full candidate set (including an injected extraRootMoves candidate), and never calls grade for the root', async () => {
    const budget: SearchBudget = {
      maxNodes: 2, // root expansion + exactly one non-root expansion
      elo: NEUTRAL_BUDGET_ELO,
      maxPlies: 3,
      concurrency: 1,
      extraRootMoves: ['e1f1'], // dropped-tail move (D-04) — only the root union revives it
    };
    const gradeCalls: GradeCall[] = [];
    const gradeRootCalls: GradeCall[] = [];
    const gradesByFen: Record<string, Record<string, MoveGrade>> = {
      [SIMPLE_WHITE_FEN]: { ...SIMPLE_WHITE_GRADES, e1f1: { evalCp: 120, evalMate: null, depth: 10 } },
    };
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade(gradesByFen, gradeCalls),
      gradeRoot: makeFixedGrade(gradesByFen, gradeRootCalls),
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(gradeRootCalls.length).toBe(1);
    expect(gradeRootCalls[0]!.fen).toBe(SIMPLE_WHITE_FEN);
    // Full root candidate set: the ~90%-mass-kept organic candidates
    // (e2e4, e2e3, e1d2) unioned with the injected e1f1 (D-04) — the exact
    // set that would have gone to `grade` had `gradeRoot` been absent.
    expect(new Set(gradeRootCalls[0]!.candidateUcis)).toEqual(new Set(['e2e4', 'e2e3', 'e1d2', 'e1f1']));
    // grade() is never called for the root fen — only for the one
    // non-root leaf this budget's second node dispatches to.
    expect(gradeCalls.every((c) => c.fen !== SIMPLE_WHITE_FEN)).toBe(true);
    expect(gradeCalls.length).toBeGreaterThan(0); // the non-root expansion did happen and used grade()
    expect(snapshot.rankedLines.some((l) => l.rootMove === 'e1f1')).toBe(true);
  });

  it('routing is transparent: a provider without gradeRoot produces the identical final snapshot as one whose gradeRoot delegates straight to grade', async () => {
    const determinismBudget: SearchBudget = { maxNodes: 5, elo: NEUTRAL_BUDGET_ELO, maxPlies: 3, concurrency: 1 };
    const providersWithout: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeVariedGrade(),
    };
    const resultWithout = await mctsSearch(SIMPLE_WHITE_FEN, determinismBudget, providersWithout, () => {}, freshSignal());

    const delegatingGrade = makeVariedGrade();
    const providersWith: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: delegatingGrade,
      gradeRoot: (fen, candidateUcis, signal) => delegatingGrade(fen, candidateUcis, signal),
    };
    const resultWith = await mctsSearch(SIMPLE_WHITE_FEN, determinismBudget, providersWith, () => {}, freshSignal());

    expect(resultWithout.rankedLines.some((l) => l.practicalScore !== 0.5)).toBe(true);
    expect(resultWith).toEqual(resultWithout);
  });

  it('an empty (non-aborted) gradeRoot Map degrades exactly like an empty root grade() Map today — root children surface at NEUTRAL_EXPECTED_SCORE', async () => {
    const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
    const gradeCalls: GradeCall[] = [];
    const providers: EngineProviders = {
      policy: makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }),
      grade: makeFixedGrade({}, gradeCalls), // must never be reached: maxNodes=1 stops after the root
      gradeRoot: async () => new Map<string, MoveGrade>(), // always empty, even for the root
    };

    const snapshot = await mctsSearch(SIMPLE_WHITE_FEN, budget, providers, () => {}, freshSignal());

    expect(gradeCalls).toEqual([]); // grade() never called — gradeRoot handled the (only) root expansion
    expect(snapshot.rankedLines.length).toBeGreaterThan(0);
    for (const line of snapshot.rankedLines) {
      expect(line.practicalScore).toBe(0.5);
    }
  });
});

