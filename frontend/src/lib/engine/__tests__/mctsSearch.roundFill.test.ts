/**
 * mctsSearch.ts — D-08 permanent round-fill regression test (SEED-170 item
 * 2, CONTEXT.md D-06/D-08).
 *
 * `selectPath` used to give up on the WHOLE dispatch round the moment a
 * single non-root node had zero selectable children (every child pending or
 * closed), even though other root subtrees still had selectable work. On a
 * peaked non-root policy (one candidate ~92%, or two at ~55%/~37% —
 * `truncateAndRenormalize`'s ~90% mass cut keeps exactly that many
 * candidates), most subtrees collapse to a single child within a few plies,
 * so this fired constantly: effective concurrency dropped from 4 to 1-2 on
 * both the bot (50/c4) and analysis (400/c4) budgets.
 *
 * The observable: `policy()` is the first `await` in `dispatchExpansion`, so
 * every expansion dispatched in one round calls `policy()` before any of
 * that round's `onSnapshot` events fire (the apply loop runs strictly after
 * `Promise.all` resolves). The run length of consecutive `policy()` calls
 * between `onSnapshot` events is therefore exactly one round's dispatch
 * size — deterministic and independent of the event loop, needing zero
 * production instrumentation (225-RESEARCH.md "Round counting in D-08").
 *
 * Fixture: italian-opening FEN, 50 nodes, concurrency 4, 8 plies — the exact
 * shape the throwaway probe measured this phase (225-RESEARCH.md "D-08
 * permanent round-fill test"): pre-fix, the flat root round is followed by
 * mostly 1-2-node rounds instead of full 4-node rounds (37 rounds for the
 * one-candidate shape, 20 for the two-candidate shape, instead of 14).
 *
 * Mutation check (D-08, project mutation-test rule): reverting the fix
 * (restoring `selectPath`'s unconditional `return null` on an empty
 * candidate list at ANY node, and the pre-fix fill-loop `break`) must make
 * these tests fail. Recorded in 225-04-SUMMARY.md, never left as a
 * grep/symbol-presence claim.
 */

import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { mctsSearch } from '../mctsSearch';
import type { EngineProviders, EngineSnapshot, MoveGrade, SearchBudget } from '../types';

// ─── Fixtures ────────────────────────────────────────────────────────────────

/** Italian opening, White to move — the root FEN for every D-08 round-fill case. */
const ROUND_FILL_ROOT_FEN = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4';
const ROUND_FILL_MAX_NODES = 50;
const ROUND_FILL_CONCURRENCY = 4;
const ROUND_FILL_MAX_PLIES = 8;
/** One-candidate peaked shape: truncateAndRenormalize's 0.9 cumulative-mass cut keeps exactly 1 candidate. */
const ONE_CANDIDATE_PEAKS = [0.92];
/** Two-candidate peaked shape: the cut keeps exactly 2 candidates (0.55 + 0.37 = 0.92 >= 0.9). */
const TWO_CANDIDATE_PEAKS = [0.55, 0.37];

const ROUND_FILL_BUDGET: SearchBudget = {
  maxNodes: ROUND_FILL_MAX_NODES,
  elo: { w: 1500, b: 1500 },
  maxPlies: ROUND_FILL_MAX_PLIES,
  concurrency: ROUND_FILL_CONCURRENCY,
};

/** Never-aborted signal — none of these cases exercise cancellation. */
function freshSignal(): AbortSignal {
  return new AbortController().signal;
}

// ─── Fabricated-provider helpers ────────────────────────────────────────────

/** chess.js's OWN legal-move UCI list at `fen`, sorted ascending — never hand-enumerated. */
function legalUcisSorted(fen: string): string[] {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true });
  return moves.map((m) => `${m.from}${m.to}${m.promotion ?? ''}`).sort();
}

/**
 * A `policy()` fabricator that pushes `'P'` on every call (the round-size
 * observable above) and returns: a UNIFORM distribution over legal moves at
 * the root FEN (the root's own policy shape is irrelevant to this bug — only
 * one root expansion ever happens, in round 0 — so keeping it flat isolates
 * the peaked shape to non-root nodes, matching every caller's real root
 * behavior of a broad Maia distribution); at every other reached FEN, the
 * first `peaks.length` sorted legal moves get the given peak masses and the
 * remaining legal moves split the rest evenly, so `truncateAndRenormalize`
 * keeps exactly `peaks.length` candidates there.
 */
function makePeakedPolicy(peaks: number[], events: ('P' | 'S')[]): EngineProviders['policy'] {
  return async (fen) => {
    events.push('P');
    const ucis = legalUcisSorted(fen);
    if (fen === ROUND_FILL_ROOT_FEN) {
      const weight = ucis.length > 0 ? 1 / ucis.length : 0;
      const dist: Record<string, number> = {};
      for (const uci of ucis) dist[uci] = weight;
      return dist;
    }
    const peakMass = peaks.reduce((sum, p) => sum + p, 0);
    const tailUcis = ucis.slice(peaks.length);
    const tailWeight = tailUcis.length > 0 ? Math.max(0, 1 - peakMass) / tailUcis.length : 0;
    const dist: Record<string, number> = {};
    ucis.forEach((uci, i) => {
      const peak = peaks[i];
      dist[uci] = peak !== undefined ? peak : tailWeight;
    });
    return dist;
  };
}

/** Deterministic non-neutral evalCp per uci (char-code sum modulo 201, minus 100) — no randomness, no collapsing to 0.5 everywhere. */
function makeUciDerivedGrade(): EngineProviders['grade'] {
  return async (fen, candidateUcis) => {
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      let charSum = 0;
      for (let i = 0; i < uci.length; i += 1) charSum += uci.charCodeAt(i);
      map.set(uci, { evalCp: (charSum % 201) - 100, evalMate: null, depth: 10 });
    }
    return map;
  };
}

/** Run lengths of consecutive `'P'` entries in `events` — one round's dispatch size each. */
function roundSizesFromEvents(events: ('P' | 'S')[]): number[] {
  const rounds: number[] = [];
  let current = 0;
  for (const event of events) {
    if (event === 'P') {
      current += 1;
    } else if (current > 0) {
      rounds.push(current);
      current = 0;
    }
  }
  if (current > 0) rounds.push(current);
  return rounds;
}

/**
 * Like `makePeakedPolicy` but peaks EVERY fen, including the root — a
 * genuine single-chain tree (no branching anywhere), used only by the
 * T-225-07 fully-blocked-termination case below. `makePeakedPolicy` keeps
 * the root flat deliberately (its own doc comment); this variant is the one
 * place that shape is wrong on purpose.
 */
function makeFullyPeakedPolicy(peaks: number[], events: ('P' | 'S')[]): EngineProviders['policy'] {
  return async (fen) => {
    events.push('P');
    const ucis = legalUcisSorted(fen);
    const peakMass = peaks.reduce((sum, p) => sum + p, 0);
    const tailUcis = ucis.slice(peaks.length);
    const tailWeight = tailUcis.length > 0 ? Math.max(0, 1 - peakMass) / tailUcis.length : 0;
    const dist: Record<string, number> = {};
    ucis.forEach((uci, i) => {
      const peak = peaks[i];
      dist[uci] = peak !== undefined ? peak : tailWeight;
    });
    return dist;
  };
}

/** Wraps an async fabricated provider fn with an artificial, deliberately jittered resolution delay (copied from mctsSearch.test.ts's ENGINE-07 concurrency=2 pattern). */
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

// ─── D-08 round fill ─────────────────────────────────────────────────────────

describe('mctsSearch — D-08 round fill', () => {
  it.each([
    ['one-candidate (92%)', ONE_CANDIDATE_PEAKS],
    ['two-candidate (55%/37%)', TWO_CANDIDATE_PEAKS],
  ])('every non-tail round dispatches exactly %s expansions on a %s peaked non-root policy', async (_label, peaks) => {
    const events: ('P' | 'S')[] = [];
    const providers: EngineProviders = {
      policy: makePeakedPolicy(peaks, events),
      grade: makeUciDerivedGrade(),
    };
    const snapshot = await mctsSearch(
      ROUND_FILL_ROOT_FEN,
      ROUND_FILL_BUDGET,
      providers,
      () => events.push('S'),
      freshSignal(),
    );

    const rounds = roundSizesFromEvents(events);

    expect(snapshot.nodesEvaluated).toBe(ROUND_FILL_MAX_NODES);
    expect(rounds[0]).toBe(1); // round 0 is the root itself, always a single expansion
    expect(rounds.slice(1, -1).every((size) => size === ROUND_FILL_CONCURRENCY)).toBe(true);
    expect(rounds.reduce((sum, size) => sum + size, 0)).toBe(snapshot.nodesEvaluated);
  });

  it('produces toEqual final snapshots and toEqual onSnapshot sequences at concurrency 2 under two different resolution jitters (D-06 determinism scope)', async () => {
    const budgetC2: SearchBudget = { ...ROUND_FILL_BUDGET, concurrency: 2 };

    const providersA: EngineProviders = {
      policy: withJitter(makePeakedPolicy(ONE_CANDIDATE_PEAKS, []), [30, 5, 20, 0]),
      grade: withJitter(makeUciDerivedGrade(), [10, 25, 0, 15]),
    };
    const snapshotsA: EngineSnapshot[] = [];
    const resultA = await mctsSearch(
      ROUND_FILL_ROOT_FEN,
      budgetC2,
      providersA,
      (s) => snapshotsA.push(structuredClone(s)),
      freshSignal(),
    );

    const providersB: EngineProviders = {
      policy: withJitter(makePeakedPolicy(ONE_CANDIDATE_PEAKS, []), [0, 40, 10, 25]),
      grade: withJitter(makeUciDerivedGrade(), [35, 0, 20, 5]),
    };
    const snapshotsB: EngineSnapshot[] = [];
    const resultB = await mctsSearch(
      ROUND_FILL_ROOT_FEN,
      budgetC2,
      providersB,
      (s) => snapshotsB.push(structuredClone(s)),
      freshSignal(),
    );

    // Guard against a degenerate fixture (CR-01): at least one value must
    // differ from the 0.5 neutral score, or the equality assertions below
    // prove nothing.
    expect(resultA.rankedLines.some((l) => l.practicalScore !== 0.5)).toBe(true);
    expect(resultB).toEqual(resultA);
    expect(snapshotsB).toEqual(snapshotsA);
    expect(snapshotsA.length).toBeGreaterThan(0);
  });

  it('resolves with round size 1 every round on a fully single-chain tree (T-225-07 fully-blocked-round termination)', async () => {
    const events: ('P' | 'S')[] = [];
    const providers: EngineProviders = {
      policy: makeFullyPeakedPolicy(ONE_CANDIDATE_PEAKS, events),
      grade: makeUciDerivedGrade(),
    };
    const snapshot = await mctsSearch(
      ROUND_FILL_ROOT_FEN,
      ROUND_FILL_BUDGET,
      providers,
      () => events.push('S'),
      freshSignal(),
    );

    const rounds = roundSizesFromEvents(events);
    // Depths 0..maxPlies-1 are each exactly one expansion event (one
    // policy() call, one nodesEvaluated increment); the depth===maxPlies
    // child is discovered ALREADY CLOSED by selectPath itself (a WR-05 dead
    // end — terminal/depth-capped nodes never call policy(), D-09), so the
    // chain's expandable length is exactly maxPlies, not maxPlies + 1.
    const CHAIN_EXPANDABLE_LENGTH = ROUND_FILL_MAX_PLIES;

    expect(rounds.length).toBe(CHAIN_EXPANDABLE_LENGTH);
    expect(rounds.every((size) => size === 1)).toBe(true);
    expect(snapshot.nodesEvaluated).toBe(CHAIN_EXPANDABLE_LENGTH);
  });
});
