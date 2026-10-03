/**
 * mctsSearch.ts — Phase 227 continuous dispatch (D-08..D-11), tests.
 *
 * `reports/continuous-dispatch-227/design.md` (reviewed SOUND, round 2) is the
 * spec. This file holds, in order:
 *
 *   1. PRE-EXTRACTION GOLDENS (design 2.4, R1B-4). Captured from the round loop
 *      BEFORE `applyAndReport` / `discoverDeadEnd` / the search-state record
 *      were extracted from it, so a defect in a helper both loops now share
 *      cannot hide behind a live round-vs-continuous equality (both arms would
 *      carry it). Each golden is the SHA-256 of the JSON of {onSnapshot
 *      sequence, returned snapshot, ordered policy() and grade() call lists
 *      after quiescence}, with a readable summary beside it. They were produced
 *      by running this exact capture against the unrefactored `mctsSearch`;
 *      round mode at c = 1 AND c = 4 must keep matching them after the
 *      extraction, and continuous mode at c = 1 must match the c = 1 ones.
 *      They live inline (not in a .snap or reports/ file) because the accept
 *      rule's content assertion 2 pins the set of files this plan may change.
 *
 * Mutation-check rule (project rule, `mctsSearch.roundFill.test.ts` style):
 * every guard test below is proven by REVERTING the guard it names, watching
 * the test fail, and restoring it. The reverts and the failing tests are
 * recorded in 227-10-SUMMARY.md, never claimed from grep or symbol presence.
 */

import { createHash } from 'node:crypto';
import { describe, it, expect, vi } from 'vitest';
import { mctsSearch } from '../mctsSearch';
import { applyUciMoveFen } from '../treeCommon';
import type { DispatchMode, EngineProviders, EngineSnapshot, MoveGrade, SearchBudget } from '../types';
import {
  flushTurns,
  makeControlledGrade,
  makeFixedPolicy,
  makePeakedPolicy,
  makeUciDerivedGrade,
  makeVariedGrade,
  settlesWithin,
  uniformPolicyFromLegalMoves,
  withJitter,
  deferred,
  type Deferred,
  type PolicyCall,
  type Settlement,
} from './searchTestProviders';

// ─── Fixtures ────────────────────────────────────────────────────────────────

/** King+pawn ending, White to move: 6 legal moves, shallow tree, no transpositions at depth <= 2. */
const SIMPLE_WHITE_FEN = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1';
/** One move (e1e8) delivers immediate checkmate of Black. */
const MATE_IN_1_FEN = '6k1/5ppp/8/8/8/8/8/4R2K w - - 0 1';
/** Italian opening, White to move: broad root, used for the peaked non-root policy shapes. */
const ITALIAN_FEN = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4';

const NEUTRAL_ELO = { w: 1500, b: 1500 };

const SIMPLE_WHITE_POLICY: Record<string, number> = {
  e2e4: 0.5,
  e2e3: 0.3,
  e1d2: 0.15,
  e1f2: 0.03,
  e1d1: 0.01,
  e1f1: 0.01,
};

/** The position after the root's first-choice move: the fixture's "one special child". */
const AFTER_E2E4_FEN = applyUciMoveFen(SIMPLE_WHITE_FEN, 'e2e4') ?? '';

/** One-candidate peaked shape: the 0.9 cumulative-mass cut keeps exactly 1 candidate. */
const ONE_CANDIDATE_PEAKS = [0.92];

/** Three-candidate root shape: 0.4 + 0.3 + 0.25 = 0.95 >= 0.9, so the mass cut keeps exactly 3 root children. */
const THREE_ROOT_CANDIDATE_PEAKS = [0.4, 0.3, 0.25];

/** Stop rule that fires within the plain fixture's budget (checked: golden stopReason is 'early-stop'). */
const FIXTURE_STOP_RULE = {
  marginThreshold: 0.05,
  epsilonThreshold: 0.02,
  stabilityWindow: 2,
  minNodes: 4,
  rootGuardBoostAllowance: 0.1,
};

/** One fabricated search fixture, parameterized by concurrency at run time. */
interface Fixture {
  name: string;
  rootFen: string;
  maxNodes: number;
  maxPlies: number;
  /** Extra `SearchBudget` fields (stopRule, extraRootMoves). */
  budgetExtras?: Partial<SearchBudget>;
  makeProviders: () => EngineProviders;
  /** Abort the outer signal from inside `onSnapshot` once this many nodes are evaluated (deadline-style cut). */
  abortAtNodes?: number;
  /** Hand the search an already-aborted signal. */
  preAborted?: boolean;
}

const simplePolicy = (): EngineProviders['policy'] => makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY });

const withVariedGrade = (policy: EngineProviders['policy']): EngineProviders => ({
  policy,
  grade: makeVariedGrade(),
});

const FIXTURES: Fixture[] = [
  {
    name: 'plain',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 12,
    maxPlies: 4,
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    name: 'stop-rule',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 30,
    maxPlies: 4,
    budgetExtras: { stopRule: FIXTURE_STOP_RULE },
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    // maxPlies 2: every depth-2 node is a WR-05 depth-ceiling dead end (budgetExhausted, visit bumps, closure).
    name: 'dead-ends',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 40,
    maxPlies: 2,
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    // Terminal child (mate) discovered as a dead end, closure propagates root-ward.
    name: 'terminal',
    rootFen: MATE_IN_1_FEN,
    maxNodes: 10,
    maxPlies: 3,
    makeProviders: () => withVariedGrade(makeFixedPolicy({})),
  },
  {
    // WR-04: the child after e2e4 gets an empty candidate set -> degenerate close, no node, no snapshot.
    name: 'degenerate',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 12,
    maxPlies: 4,
    makeProviders: () =>
      withVariedGrade(makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY, [AFTER_E2E4_FEN]: {} })),
  },
  {
    // 8XN-7: a non-abort empty grade Map at a NON-root leaf closes it as a dead end.
    name: 'empty-grade',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 12,
    maxPlies: 4,
    makeProviders: () => {
      const varied = makeVariedGrade();
      return {
        policy: simplePolicy(),
        grade: async (fen, ucis, signal) =>
          fen === AFTER_E2E4_FEN ? new Map<string, MoveGrade>() : varied(fen, ucis, signal),
      };
    },
  },
  {
    name: 'extra-root-moves',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 8,
    maxPlies: 3,
    budgetExtras: { extraRootMoves: ['e1f1'] },
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    // Phase 226 D-18: the root's one grade call routes to gradeRoot.
    name: 'grade-root',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 8,
    maxPlies: 3,
    makeProviders: () => {
      const varied = makeVariedGrade();
      return { policy: simplePolicy(), grade: varied, gradeRoot: (fen, ucis, signal) => varied(fen, ucis, signal) };
    },
  },
  {
    // Deadline-style cut: the abort fires from inside onSnapshot, mid-drain.
    name: 'abort-in-snapshot',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 12,
    maxPlies: 4,
    abortAtNodes: 3,
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    name: 'pre-aborted',
    rootFen: SIMPLE_WHITE_FEN,
    maxNodes: 12,
    maxPlies: 4,
    preAborted: true,
    makeProviders: () => withVariedGrade(simplePolicy()),
  },
  {
    // SEED-170 item 2 shape: a broad root over one-candidate chains, so interior nodes with only a pending child
    // exercise the isBlocked machinery at c > 1.
    name: 'peaked',
    rootFen: ITALIAN_FEN,
    maxNodes: 50,
    maxPlies: 8,
    makeProviders: () => ({ policy: makePeakedPolicy(ITALIAN_FEN, ONE_CANDIDATE_PEAKS), grade: makeUciDerivedGrade() }),
  },
  {
    // Three root candidates, then single-candidate chains below: with c = 4 a walk repeatedly reaches an interior
    // node whose only child is pending, so isBlocked is set and cleared (per round / per fill) on almost every pass.
    name: 'chains',
    rootFen: ITALIAN_FEN,
    maxNodes: 20,
    maxPlies: 8,
    makeProviders: () => ({
      policy: makePeakedPolicy(ITALIAN_FEN, ONE_CANDIDATE_PEAKS, THREE_ROOT_CANDIDATE_PEAKS),
      grade: makeUciDerivedGrade(),
    }),
  },
];

// ─── Capture ─────────────────────────────────────────────────────────────────

/** Artificial per-call resolution delays (ms) for the policy and grade providers. */
interface JitterPlan {
  policy: number[];
  grade: number[];
}

/** Everything design 2.4 defines as "byte-identical": snapshot sequence, final snapshot, ordered call lists. */
interface Capture {
  snapshots: EngineSnapshot[];
  final: EngineSnapshot;
  policyCalls: string[];
  gradeCalls: string[];
}

/** Runs `mctsSearch` on `fixture` and returns its capture AFTER every provider promise has settled (quiescence). */
async function runCapture(
  fixture: Fixture,
  mode: DispatchMode | undefined,
  concurrency: number,
  jitter?: JitterPlan,
): Promise<Capture> {
  const raw = fixture.makeProviders();
  const policy = jitter ? withJitter(raw.policy, jitter.policy) : raw.policy;
  const grade = jitter ? withJitter(raw.grade, jitter.grade) : raw.grade;
  const rawGradeRoot = raw.gradeRoot;
  const gradeRoot = rawGradeRoot && jitter ? withJitter(rawGradeRoot, jitter.grade) : rawGradeRoot;

  const handedOut: Promise<unknown>[] = [];
  const policyCalls: string[] = [];
  const gradeCalls: string[] = [];
  const providers: EngineProviders = {
    policy: (fen, elo, side, signal) => {
      policyCalls.push(`${fen}|${elo}|${side}`);
      const p = policy(fen, elo, side, signal);
      handedOut.push(p);
      return p;
    },
    // The engine passes a 4th (ladder depth) argument through a local cast; record it too.
    grade: ((fen: string, ucis: string[], signal?: AbortSignal, depth?: number) => {
      gradeCalls.push(`grade|${fen}|${ucis.join(',')}|${depth}`);
      const p = (grade as (...a: unknown[]) => Promise<Map<string, MoveGrade>>)(fen, ucis, signal, depth);
      handedOut.push(p);
      return p;
    }) as EngineProviders['grade'],
    ...(gradeRoot
      ? {
          gradeRoot: (fen: string, ucis: string[], signal?: AbortSignal) => {
            gradeCalls.push(`root|${fen}|${ucis.join(',')}`);
            const p = gradeRoot(fen, ucis, signal);
            handedOut.push(p);
            return p;
          },
        }
      : {}),
  };

  const budget: SearchBudget = {
    maxNodes: fixture.maxNodes,
    elo: NEUTRAL_ELO,
    maxPlies: fixture.maxPlies,
    concurrency,
    ...fixture.budgetExtras,
    ...(mode !== undefined ? { dispatchMode: mode } : {}),
  };
  const controller = new AbortController();
  if (fixture.preAborted) controller.abort();
  const snapshots: EngineSnapshot[] = [];
  const final = await mctsSearch(
    fixture.rootFen,
    budget,
    providers,
    (s) => {
      snapshots.push(structuredClone(s));
      if (fixture.abortAtNodes === s.nodesEvaluated) controller.abort();
    },
    controller.signal,
  );
  await quiesce(handedOut);
  return { snapshots, final: structuredClone(final), policyCalls, gradeCalls };
}

/** Waits until every provider promise handed out during a search (including ones created while waiting) has settled. */
async function quiesce(handedOut: Promise<unknown>[]): Promise<void> {
  let seen = -1;
  while (seen !== handedOut.length) {
    seen = handedOut.length;
    await Promise.allSettled(handedOut);
    await flushTurns(2);
  }
}

/** The golden record for one (fixture, concurrency) cell: a digest of the full capture plus a readable summary. */
interface Golden {
  digest: string;
  snapshots: number;
  nodes: number;
  stopReason: EngineSnapshot['stopReason'];
  policyCalls: number;
  gradeCalls: number;
}

const DIGEST_HEX_CHARS = 20;

function toGolden(c: Capture): Golden {
  const digest = createHash('sha256').update(JSON.stringify(c)).digest('hex').slice(0, DIGEST_HEX_CHARS);
  return {
    digest,
    snapshots: c.snapshots.length,
    nodes: c.final.nodesEvaluated,
    stopReason: c.final.stopReason,
    policyCalls: c.policyCalls.length,
    gradeCalls: c.gradeCalls.length,
  };
}

// ─── 1. Pre-extraction goldens (round loop before the helper extraction) ─────

/**
 * Concurrency levels each fixture is captured at. Every fixture runs at c = 1
 * (the level continuous must reproduce byte for byte) and c = 4 (the bot's
 * level: pending exclusion, per-round blocks and canonical apply order all
 * matter there); the chains fixture also runs c = 2.
 */
function goldenConcurrencies(fixture: Fixture): number[] {
  return fixture.name === 'chains' ? [1, 2, 4] : [1, 4];
}

const GOLDENS: Record<string, Golden | undefined> = {
  'abort-in-snapshot@c1': { digest: 'b58026c6614303bcf1ab', snapshots: 3, nodes: 3, stopReason: null, policyCalls: 3, gradeCalls: 3 },
  'abort-in-snapshot@c4': { digest: '85897d45d6646efba6bb', snapshots: 3, nodes: 3, stopReason: null, policyCalls: 4, gradeCalls: 4 },
  'chains@c1': { digest: '6fe7d31df5d3ef8e985a', snapshots: 20, nodes: 20, stopReason: 'budget', policyCalls: 20, gradeCalls: 20 },
  'chains@c2': { digest: '2b15528128a3f6237428', snapshots: 20, nodes: 20, stopReason: 'budget', policyCalls: 20, gradeCalls: 20 },
  'chains@c4': { digest: 'f72e21369b33f3c8e4e9', snapshots: 20, nodes: 20, stopReason: 'budget', policyCalls: 20, gradeCalls: 20 },
  'dead-ends@c1': { digest: '97a0f0ae5101b28933b5', snapshots: 4, nodes: 4, stopReason: 'budget', policyCalls: 4, gradeCalls: 4 },
  'dead-ends@c4': { digest: 'aefe772ad8f0f8dcbc92', snapshots: 4, nodes: 4, stopReason: 'budget', policyCalls: 4, gradeCalls: 4 },
  'degenerate@c1': { digest: '23fe57050edf2a00eb75', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 13, gradeCalls: 12 },
  'degenerate@c4': { digest: '590ed3e79134a27e2d0e', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 13, gradeCalls: 12 },
  'empty-grade@c1': { digest: '2b1c96a2b519ef91242e', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 13, gradeCalls: 13 },
  'empty-grade@c4': { digest: '337736ed9e4fcd8936e3', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 13, gradeCalls: 13 },
  'extra-root-moves@c1': { digest: 'fddab8aec64c0c8665e8', snapshots: 8, nodes: 8, stopReason: 'budget', policyCalls: 8, gradeCalls: 8 },
  'extra-root-moves@c4': { digest: '7278cd73ba778bffa6c6', snapshots: 8, nodes: 8, stopReason: 'budget', policyCalls: 8, gradeCalls: 8 },
  'grade-root@c1': { digest: 'aa27c9f823ff54794de3', snapshots: 8, nodes: 8, stopReason: 'budget', policyCalls: 8, gradeCalls: 8 },
  'grade-root@c4': { digest: 'eaa4a4ac7d56d8c0fa06', snapshots: 8, nodes: 8, stopReason: 'budget', policyCalls: 8, gradeCalls: 8 },
  'peaked@c1': { digest: 'd5e6d231d395d6a2d2d3', snapshots: 50, nodes: 50, stopReason: 'budget', policyCalls: 50, gradeCalls: 50 },
  'peaked@c4': { digest: 'd5e6d231d395d6a2d2d3', snapshots: 50, nodes: 50, stopReason: 'budget', policyCalls: 50, gradeCalls: 50 },
  'plain@c1': { digest: '5452a4ad46455d863836', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 12, gradeCalls: 12 },
  'plain@c4': { digest: 'bbf7f8ba352cc0da7972', snapshots: 12, nodes: 12, stopReason: 'budget', policyCalls: 12, gradeCalls: 12 },
  'pre-aborted@c1': { digest: '7034cfee9baa1c98c3e5', snapshots: 0, nodes: 0, stopReason: null, policyCalls: 0, gradeCalls: 0 },
  'pre-aborted@c4': { digest: '7034cfee9baa1c98c3e5', snapshots: 0, nodes: 0, stopReason: null, policyCalls: 0, gradeCalls: 0 },
  'stop-rule@c1': { digest: '3666b6047c8fa2845b79', snapshots: 6, nodes: 6, stopReason: 'early-stop', policyCalls: 6, gradeCalls: 6 },
  'stop-rule@c4': { digest: 'aa7e79091253c5835b6f', snapshots: 5, nodes: 5, stopReason: 'early-stop', policyCalls: 8, gradeCalls: 8 },
  'terminal@c1': { digest: '860863c55b1d6a074afb', snapshots: 10, nodes: 10, stopReason: 'budget', policyCalls: 10, gradeCalls: 10 },
  'terminal@c4': { digest: '860863c55b1d6a074afb', snapshots: 10, nodes: 10, stopReason: 'budget', policyCalls: 10, gradeCalls: 10 },
};

describe('mctsSearch round loop — pre-extraction goldens (design 2.4, R1B-4)', () => {
  for (const fixture of FIXTURES) {
    for (const c of goldenConcurrencies(fixture)) {
      it(`${fixture.name} at c=${c}: round mode matches the pre-extraction capture`, async () => {
        const cap = await runCapture(fixture, 'round', c);
        const golden = toGolden(cap);
        expect(golden).toEqual(GOLDENS[`${fixture.name}@c${c}`]);
      });
    }
  }
});

// ─── 2. Task 1: continuous dispatch behind the flag ──────────────────────────

/** Different artificial resolution delays for the two arms of an identity comparison. */
const JITTER_ROUND_ARM: JitterPlan = { policy: [3, 0, 2, 1], grade: [1, 2, 0, 3] };
const JITTER_CONTINUOUS_ARM: JitterPlan = { policy: [0, 2, 1, 3], grade: [2, 0, 3, 1] };
/** Heavier, non-monotonic jitter for the c = 4 smoke (later dispatches routinely settle first). */
const JITTER_C4_A: JitterPlan = { policy: [4, 0, 3, 1, 2], grade: [2, 5, 0, 3, 1] };
const JITTER_C4_B: JitterPlan = { policy: [0, 3, 1, 4, 2], grade: [5, 0, 2, 1, 4] };

function fixtureNamed(name: string): Fixture {
  const fixture = FIXTURES.find((f) => f.name === name);
  if (fixture === undefined) throw new Error('unknown fixture');
  return fixture;
}

describe('mctsSearch continuous — c=1 identity with round mode (D-11, design 2.4)', () => {
  for (const fixture of FIXTURES) {
    it(`${fixture.name} at c=1: continuous equals round and the pre-extraction golden under different jitter`, async () => {
      const round = await runCapture(fixture, 'round', 1, JITTER_ROUND_ARM);
      const continuous = await runCapture(fixture, 'continuous', 1, JITTER_CONTINUOUS_ARM);

      expect(continuous.snapshots).toEqual(round.snapshots);
      expect(continuous.final).toEqual(round.final);
      expect(continuous.policyCalls).toEqual(round.policyCalls);
      expect(continuous.gradeCalls).toEqual(round.gradeCalls);
      expect(toGolden(continuous)).toEqual(GOLDENS[`${fixture.name}@c1`]);
    });
  }
});

describe('mctsSearch — dispatchMode omitted is round mode (D-11)', () => {
  for (const name of ['plain', 'stop-rule', 'chains']) {
    it(`omitted, explicit 'round' and the pre-extraction golden agree at c=4 on ${name}`, async () => {
      const fixture = fixtureNamed(name);
      const omitted = await runCapture(fixture, undefined, 4);
      const explicit = await runCapture(fixture, 'round', 4);

      expect(omitted).toEqual(explicit);
      expect(toGolden(omitted)).toEqual(GOLDENS[`${name}@c4`]);
    });
  }
});

describe('mctsSearch continuous — c=4 completes under jitter', () => {
  for (const [label, jitter] of [
    ['jitter A', JITTER_C4_A],
    ['jitter B', JITTER_C4_B],
  ] as const) {
    for (const name of ['plain', 'chains', 'peaked']) {
      it(`${name} at c=4 (${label}): finishes, never exceeds the node budget, ranks root moves`, async () => {
        const fixture = fixtureNamed(name);
        const run = await runCapture(fixture, 'continuous', 4, jitter);

        expect(run.final.nodesEvaluated).toBeLessThanOrEqual(fixture.maxNodes);
        expect(run.final.rankedLines.length).toBeGreaterThan(0);
        expect(run.snapshots.length).toBe(run.final.nodesEvaluated);
      });
    }
  }
});

// ─── 3. Ordering control with hand-settled providers ─────────────────────────

/** A hand-driven search: controlled grades, immediate policy, snapshots recorded, the outer controller exposed. */
function startControlled(
  overrides: Partial<SearchBudget>,
  options: {
    rootFen?: string;
    policy?: EngineProviders['policy'];
    signal?: AbortSignal;
    /** Runs inside `onSnapshot` (i.e. inside the drain), after the snapshot is recorded. */
    afterSnapshot?: (snapshot: EngineSnapshot, controller: AbortController) => void;
  } = {},
): {
  search: Promise<EngineSnapshot>;
  ctl: ReturnType<typeof makeControlledGrade>;
  snapshots: EngineSnapshot[];
  policyCalls: PolicyCall[];
  controller: AbortController;
} {
  const ctl = makeControlledGrade();
  const controller = new AbortController();
  const snapshots: EngineSnapshot[] = [];
  const policyCalls: PolicyCall[] = [];
  const budget: SearchBudget = {
    maxNodes: 8,
    elo: NEUTRAL_ELO,
    maxPlies: 3,
    concurrency: 2,
    dispatchMode: 'continuous',
    ...overrides,
  };
  const providers: EngineProviders = {
    policy: options.policy ?? makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }, policyCalls),
    grade: ctl.grade,
  };
  const search = mctsSearch(
    options.rootFen ?? SIMPLE_WHITE_FEN,
    budget,
    providers,
    (s) => {
      snapshots.push(structuredClone(s));
      options.afterSnapshot?.(s, controller);
    },
    options.signal ?? controller.signal,
  );
  return { search, ctl, snapshots, policyCalls, controller };
}

/** Collects `unhandledRejection` events for the duration of a test; call `stop()` to detach and read them. */
function trackUnhandledRejections(): { stop: () => unknown[] } {
  const seen: unknown[] = [];
  const handler = (reason: unknown): void => {
    seen.push(reason);
  };
  process.on('unhandledRejection', handler);
  return {
    stop: () => {
      process.off('unhandledRejection', handler);
      return seen;
    },
  };
}

/** The root move whose subtree holds the (single) applied non-root expansion in `snapshot`. */
function visitedRootMove(snapshot: EngineSnapshot): string | undefined {
  return snapshot.rankedLines.find((line) => line.visits > 0)?.rootMove;
}

describe('mctsSearch continuous — arrival order (D-08, SEED-171 item 5)', () => {
  it('arrival order: the expansion that settles first is applied first, not the one dispatched first', async () => {
    const { search, ctl, snapshots, controller } = startControlled({ concurrency: 2 });
    await flushTurns();
    ctl.settle(0); // root
    await flushTurns();
    expect(ctl.calls).toHaveLength(3); // root + two expansions in flight
    expect(snapshots).toHaveLength(1);

    ctl.settle(2); // the LATER dispatch settles first
    await flushTurns();

    expect(snapshots).toHaveLength(2); // applied at once, without waiting for call 1
    const applied = visitedRootMove(snapshots[1] as EngineSnapshot);
    expect(applied).toBeDefined();
    expect(applyUciMoveFen(SIMPLE_WHITE_FEN, applied ?? '')).toBe(ctl.calls[2]?.fen);

    controller.abort();
    await search;
  });

  it('fill: a slot freed by one settled expansion is refilled while the other is still in flight', async () => {
    const { search, ctl, controller } = startControlled({ concurrency: 2 });
    await flushTurns();
    ctl.settle(0);
    await flushTurns();
    expect(ctl.calls).toHaveLength(3);

    ctl.settle(1); // one of the two; call 2 stays pending
    await flushTurns();

    expect(ctl.calls).toHaveLength(4); // a new dispatch, no round barrier

    controller.abort();
    await search;
  });
});

// ─── 4. c = 1 divergence fixtures pinned by design 2.4 ───────────────────────

/** Bounded wait that is long enough for any microtask chain but short enough to keep a hang cheap. */
const SHORT_WINDOW_MS = 60;

interface AbortInFlightRun {
  /** The search outcome observed BEFORE the in-flight provider settles. */
  beforeSettle: Settlement<EngineSnapshot>;
  /** The search outcome observed AFTER the provider settled (or rejected) and the loop drained. */
  afterSettle: Settlement<EngineSnapshot>;
  snapshots: EngineSnapshot[];
  policyCalls: PolicyCall[];
  gradeCalls: { fen: string; candidateUcis: string[] }[];
  unhandled: unknown[];
}

/**
 * c = 1: apply the root, leave ONE expansion in flight on a hand-settled
 * grade, abort the outer signal, then settle (or reject) that grade.
 */
async function runAbortInFlight(mode: DispatchMode, outcome: 'settle' | 'reject'): Promise<AbortInFlightRun> {
  const tracker = trackUnhandledRejections();
  const run = startControlled({ concurrency: 1, dispatchMode: mode });
  await flushTurns();
  run.ctl.settle(0); // root
  await flushTurns();
  expect(run.ctl.calls).toHaveLength(2); // one expansion in flight

  run.controller.abort();
  const beforeSettle = await settlesWithin(run.search, SHORT_WINDOW_MS);
  if (outcome === 'settle') run.ctl.settle(1);
  else run.ctl.calls[1]?.result.reject(new Error('late provider failure'));
  const afterSettle = await settlesWithin(run.search, SHORT_WINDOW_MS);
  await flushTurns();
  return {
    beforeSettle,
    afterSettle,
    snapshots: run.snapshots,
    policyCalls: run.policyCalls,
    gradeCalls: run.ctl.calls.map((c) => ({ fen: c.fen, candidateUcis: c.candidateUcis })),
    unhandled: tracker.stop(),
  };
}

describe('mctsSearch continuous — c=1 external abort while an expansion is in flight (design 2.4)', () => {
  it('c=1 abort in flight: same snapshots and call lists as round mode, but continuous resolves before the provider settles', async () => {
    const round = await runAbortInFlight('round', 'settle');
    const continuous = await runAbortInFlight('continuous', 'settle');

    expect(continuous.snapshots).toEqual(round.snapshots);
    expect(continuous.policyCalls).toEqual(round.policyCalls);
    expect(continuous.gradeCalls).toEqual(round.gradeCalls);
    expect(continuous.beforeSettle.state).toBe('resolved'); // an abort frees the loop at once (X-9)
    expect(round.beforeSettle.state).toBe('pending'); // round mode waits for Promise.all
    expect(round.afterSettle.state).toBe('resolved');
    if (continuous.afterSettle.state === 'resolved' && round.afterSettle.state === 'resolved') {
      expect(continuous.afterSettle.value).toEqual(round.afterSettle.value);
    }
  });

  it('c=1 late rejection after abort: continuous returns the snapshot with no unhandled rejection, round mode throws', async () => {
    const round = await runAbortInFlight('round', 'reject');
    const continuous = await runAbortInFlight('continuous', 'reject');

    expect(continuous.beforeSettle.state).toBe('resolved');
    expect(continuous.afterSettle.state).toBe('resolved'); // the late rejection goes to a dead closure, dropped on purpose
    expect(continuous.unhandled).toEqual([]);
    expect(round.afterSettle.state).toBe('rejected'); // accepted divergence: Promise.all rethrows
  });
});

// ─── 5. Task 2: one guard test per continuous-mode invariant ─────────────────

/** Stop rule that fires the moment `nodesEvaluated` reaches 2 over all-neutral grades (every child ties at 0.5). */
const STOP_AT_TWO_RULE = {
  marginThreshold: 0,
  epsilonThreshold: 0,
  stabilityWindow: 1,
  minNodes: 2,
  rootGuardBoostAllowance: 0.1,
};

type ControlledRun = ReturnType<typeof startControlled>;

/** Upper bound on `driveToCompletion` passes: far above what any fixture needs, so a stuck search fails an assertion. */
const MAX_DRIVE_PASSES = 60;

/** Repeatedly settles every not-yet-settled controlled grade (varied values) until the search promise settles. */
async function driveToCompletion(run: ControlledRun): Promise<Settlement<EngineSnapshot>> {
  let done = false;
  const markDone = (): void => {
    done = true;
  };
  void run.search.then(markDone, markDone);
  const settledIndexes = new Set<number>();
  for (let pass = 0; pass < MAX_DRIVE_PASSES && !done; pass += 1) {
    await flushTurns(2);
    for (let i = 0; i < run.ctl.calls.length; i += 1) {
      if (settledIndexes.has(i)) continue;
      settledIndexes.add(i);
      run.ctl.settle(i);
    }
  }
  return settlesWithin(run.search);
}

describe('mctsSearch continuous — no result is applied after abort or early stop (D-09, L-2)', () => {
  it('after abort: grades that settle after the outer abort are never applied', async () => {
    const run = startControlled({ concurrency: 2 });
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    expect(run.snapshots).toHaveLength(1);

    run.controller.abort();
    const outcome = await settlesWithin(run.search);
    run.ctl.settle(1);
    run.ctl.settle(2);
    await flushTurns();

    expect(outcome.state).toBe('resolved');
    expect(run.snapshots).toHaveLength(1); // no snapshot after the abort
    if (outcome.state === 'resolved') expect(outcome.value.nodesEvaluated).toBe(1);
  });

  it('after abort: an abort fired inside onSnapshot discards every result already queued behind it', async () => {
    const run = startControlled(
      { concurrency: 3 },
      {
        afterSnapshot: (snapshot, controller) => {
          if (snapshot.nodesEvaluated === 2) controller.abort(); // the deadline cut aborts from inside onSnapshot
        },
      },
    );
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(4); // root + three expansions in flight
    run.ctl.settle(1);
    run.ctl.settle(2);
    run.ctl.settle(3); // all three settle in one turn, so ONE drain sees all of them

    const outcome = await settlesWithin(run.search);

    expect(outcome.state).toBe('resolved');
    expect(run.snapshots.map((s) => s.nodesEvaluated)).toEqual([1, 2]); // the two queued behind the abort were dropped
  });

  it('early stop: results queued behind the stopping apply are dropped and in-flight grades are cancelled', async () => {
    const run = startControlled({ concurrency: 3, stopRule: STOP_AT_TWO_RULE });
    await flushTurns();
    run.ctl.settleNeutral(0);
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(4);
    run.ctl.settleNeutral(1);
    run.ctl.settleNeutral(2); // call 3 stays in flight

    const outcome = await settlesWithin(run.search);

    expect(outcome.state).toBe('resolved'); // returned without waiting for call 3
    if (outcome.state === 'resolved') {
      expect(outcome.value.stopReason).toBe('early-stop');
      expect(outcome.value.nodesEvaluated).toBe(2);
    }
    expect(run.snapshots.map((s) => s.nodesEvaluated)).toEqual([1, 2]); // call 2's result was queued behind the stop
    expect(run.ctl.calls).toHaveLength(4); // no refill after the stop
    // D-09 / T-227-18: every grade the stopped search handed out was cancelled through the inner controller.
    for (const call of run.ctl.calls) expect(call.signal?.aborted).toBe(true);

    run.ctl.settleNeutral(3); // the stale grade settles later: never applied
    await flushTurns();
    expect(run.snapshots).toHaveLength(2);
  });

  it('early stop: a policy that settles after the stop calls grade with an aborted signal and nothing is applied', async () => {
    const pendingPolicies: { fen: string; result: Deferred<Record<string, number>> }[] = [];
    const rootPolicy = makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY });
    const policy: EngineProviders['policy'] = (fen, elo, side, signal) => {
      if (fen === SIMPLE_WHITE_FEN) return rootPolicy(fen, elo, side, signal);
      const result = deferred<Record<string, number>>();
      pendingPolicies.push({ fen, result });
      return result.promise;
    };
    const run = startControlled({ concurrency: 2, stopRule: STOP_AT_TWO_RULE }, { policy });
    await flushTurns();
    run.ctl.settleNeutral(0);
    await flushTurns();
    expect(pendingPolicies).toHaveLength(2); // both expansions are waiting on their policy

    const [first, second] = pendingPolicies;
    first?.result.resolve(uniformPolicyFromLegalMoves(first.fen));
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(2); // the first expansion reached its grade
    run.ctl.settleNeutral(1); // applies -> nodesEvaluated 2 -> early stop
    const outcome = await settlesWithin(run.search);
    expect(outcome.state).toBe('resolved');
    expect(run.snapshots).toHaveLength(2);

    second?.result.resolve(uniformPolicyFromLegalMoves(second.fen)); // the second policy settles AFTER the stop
    await flushTurns();

    expect(run.ctl.calls).toHaveLength(3); // dispatchExpansion resumed and called grade ...
    expect(run.ctl.calls[2]?.signal?.aborted).toBe(true); // ... with an aborted signal (a pool answers an empty Map at once)
    run.ctl.settleEmpty(2);
    await flushTurns();
    expect(run.snapshots).toHaveLength(2); // nothing applied
  });
});

// ─── budget, root guard, arrival order, fill ─────────────────────────────────

/** Counters a provider wrapper keeps about the expansions in flight (an expansion = one policy call + at most one grade call). */
interface ProviderStats {
  open: number;
  maxOpen: number;
  policyCalls: number;
  gradeCalls: number;
  /** Expansions whose provider chain ended empty: they spend a provider call but no node (WR-04, 8XN-7). */
  degenerate: number;
  /** Max over dispatches of (dispatches so far minus degenerate expansions already settled). Invariant I bounds it by maxNodes. */
  maxDispatchLoad: number;
}

type GradeWithDepth = (
  fen: string,
  candidateUcis: string[],
  signal?: AbortSignal,
  gradingDepth?: number,
) => Promise<Map<string, MoveGrade>>;

function trackProviders(raw: EngineProviders, stats: ProviderStats): EngineProviders {
  return {
    policy: async (fen, elo, side, signal) => {
      stats.policyCalls += 1;
      stats.open += 1;
      stats.maxOpen = Math.max(stats.maxOpen, stats.open);
      stats.maxDispatchLoad = Math.max(stats.maxDispatchLoad, stats.policyCalls - stats.degenerate);
      const distribution = await raw.policy(fen, elo, side, signal);
      if (Object.keys(distribution).length === 0) {
        stats.open -= 1;
        stats.degenerate += 1;
      }
      return distribution;
    },
    grade: (async (fen: string, candidateUcis: string[], signal?: AbortSignal, gradingDepth?: number) => {
      stats.gradeCalls += 1;
      const isRootGrade = stats.gradeCalls === 1; // the first expansion is always the root
      const grades = await (raw.grade as GradeWithDepth)(fen, candidateUcis, signal, gradingDepth);
      stats.open -= 1;
      if (grades.size === 0 && !isRootGrade) stats.degenerate += 1; // 8XN-7: the root is exempt
      return grades;
    }) as EngineProviders['grade'],
  };
}

/** A continuous search over a fixture with jittered, tracked providers; records the open-expansion count at the final node. */
async function runTracked(
  fixture: Fixture,
  concurrency: number,
  jitter: JitterPlan,
): Promise<{ final: EngineSnapshot; stats: ProviderStats; openAtMaxNodes: number[] }> {
  const raw = fixture.makeProviders();
  const jittered: EngineProviders = {
    policy: withJitter(raw.policy, jitter.policy),
    grade: withJitter(raw.grade, jitter.grade),
  };
  const stats: ProviderStats = { open: 0, maxOpen: 0, policyCalls: 0, gradeCalls: 0, degenerate: 0, maxDispatchLoad: 0 };
  const openAtMaxNodes: number[] = [];
  const final = await mctsSearch(
    fixture.rootFen,
    {
      maxNodes: fixture.maxNodes,
      elo: NEUTRAL_ELO,
      maxPlies: fixture.maxPlies,
      concurrency,
      dispatchMode: 'continuous',
      ...fixture.budgetExtras,
    },
    trackProviders(jittered, stats),
    (s) => {
      if (s.nodesEvaluated === fixture.maxNodes) openAtMaxNodes.push(stats.open);
    },
    new AbortController().signal,
  );
  return { final, stats, openAtMaxNodes };
}

describe('mctsSearch continuous — node budget (D-10, claim (b))', () => {
  for (const name of ['plain', 'degenerate', 'empty-grade']) {
    for (const [label, jitter] of [
      ['jitter A', JITTER_C4_A],
      ['jitter B', JITTER_C4_B],
    ] as const) {
      it(`budget: ${name} (${label}) never exceeds maxNodes, never over-dispatches, and has nothing in flight at maxNodes`, async () => {
        const fixture = fixtureNamed(name);
        const { final, stats, openAtMaxNodes } = await runTracked(fixture, 4, jitter);

        expect(final.nodesEvaluated).toBeLessThanOrEqual(fixture.maxNodes);
        expect(final.nodesEvaluated).toBe(fixture.maxNodes); // the budget binds in these fixtures
        // Invariant I: applied + in flight <= maxNodes, so dispatches minus settled degenerate closes never exceed it.
        expect(stats.maxDispatchLoad).toBeLessThanOrEqual(fixture.maxNodes);
        // Provider calls may exceed maxNodes only by the degenerate closes (X-10).
        expect(stats.gradeCalls).toBeLessThanOrEqual(fixture.maxNodes + stats.degenerate);
        // Keyed on the node count (never on budgetExhausted / stopReason, which a maxPlies cut also sets): nothing in flight.
        expect(openAtMaxNodes).toEqual([0]);
      });
    }
  }
});

describe('mctsSearch continuous — root guard (Y-9)', () => {
  it('root guard: exactly one dispatch happens until the root expansion is applied', async () => {
    const run = startControlled({ concurrency: 4 });
    await flushTurns();
    expect(run.policyCalls).toHaveLength(1);
    expect(run.ctl.calls).toHaveLength(1); // only the root, although four slots are free
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(1);

    run.ctl.settle(0);
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(4); // root + the three root children (up to c)

    run.controller.abort();
    await run.search;
  });
});

describe('mctsSearch continuous — pending exclusion (D-08)', () => {
  it('arrival order: no leaf is ever dispatched twice (a pending leaf is excluded from selection)', async () => {
    const run = startControlled({ concurrency: 3, maxNodes: 8, maxPlies: 3 });

    const outcome = await driveToCompletion(run);

    expect(outcome.state).toBe('resolved');
    const fens = run.policyCalls.map((call) => call.fen);
    // maxPlies 3 over this fixture has no transpositions among expandable nodes, so a repeated FEN is a repeated leaf.
    expect(new Set(fens).size).toBe(fens.length);
  });
});

describe('mctsSearch continuous — fill (D-08, SEED-170 item 2)', () => {
  it('fill: a peaked non-root policy keeps concurrency-many expansions in flight after the root commits', async () => {
    const { final, stats } = await runTracked(fixtureNamed('peaked'), 4, JITTER_C4_A);

    expect(final.nodesEvaluated).toBe(50);
    expect(stats.maxOpen).toBe(4);
  });

  it('fill: a block set in one fill is cleared before the next, so it cannot hide a subtree that regained work', async () => {
    // Three chains below the root and c = 4: a walk keeps reaching an interior node whose only child is pending, so
    // blocks are set on nearly every fill. A block that survived to the next fill would hide a chain that has since
    // regained a selectable leaf, and the search would run dry long before maxNodes.
    for (const jitter of [JITTER_C4_A, JITTER_C4_B]) {
      const fixture = fixtureNamed('chains');
      const { final } = await runTracked(fixture, 4, jitter);
      expect(final.nodesEvaluated).toBe(fixture.maxNodes);
    }
  });
});

// ─── rejection ───────────────────────────────────────────────────────────────

describe('mctsSearch continuous — rejection (Y-8)', () => {
  it('rejection: a rejected provider call rejects the search, aborts every sibling and leaves no unhandled rejection', async () => {
    const tracker = trackUnhandledRejections();
    const run = startControlled({ concurrency: 3 });
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(4);
    const failure = new Error('provider failed');

    run.ctl.calls[2]?.result.reject(failure);
    const outcome = await settlesWithin(run.search);

    expect(outcome).toEqual({ state: 'rejected', error: failure });
    expect(run.ctl.calls[1]?.signal?.aborted).toBe(true); // siblings cancelled through the inner controller
    expect(run.ctl.calls[3]?.signal?.aborted).toBe(true);
    run.ctl.settleEmpty(1);
    run.ctl.settleEmpty(3);
    await flushTurns();
    expect(tracker.stop()).toEqual([]);
  });

  it('rejection: a rejection queued behind the apply that fires the stop rule is dropped (R2A-6)', async () => {
    const run = startControlled({ concurrency: 3, stopRule: STOP_AT_TWO_RULE });
    await flushTurns();
    run.ctl.settleNeutral(0);
    await flushTurns();
    run.ctl.settleNeutral(1); // applies -> early stop
    run.ctl.calls[2]?.result.reject(new Error('queued behind the stop')); // same turn: queued behind it

    const outcome = await settlesWithin(run.search);

    expect(outcome.state).toBe('resolved'); // the finished search is not failed by a rejection it no longer wants
    if (outcome.state === 'resolved') expect(outcome.value.stopReason).toBe('early-stop');
  });

  it('rejection: a rejection queued behind an abort raised inside onSnapshot is dropped (R2A-6)', async () => {
    const run = startControlled(
      { concurrency: 3 },
      {
        afterSnapshot: (snapshot, controller) => {
          if (snapshot.nodesEvaluated === 2) controller.abort();
        },
      },
    );
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    run.ctl.settle(1);
    run.ctl.calls[2]?.result.reject(new Error('queued behind the abort'));

    const outcome = await settlesWithin(run.search);

    expect(outcome.state).toBe('resolved');
  });
});

// ─── wakeup ──────────────────────────────────────────────────────────────────

/** Provider shapes whose promises are ALREADY resolved when handed out (cache hits: `Promise.resolve(cached)`). */
function makeResolvedProviders(): EngineProviders {
  const grade = makeVariedGrade();
  return {
    policy: (fen) => Promise.resolve(fen === SIMPLE_WHITE_FEN ? SIMPLE_WHITE_POLICY : uniformPolicyFromLegalMoves(fen)),
    grade: (fen, ucis, signal) => grade(fen, ucis, signal),
  };
}

/** Bound on the already-resolved search: generous for ~12 nodes of microtasks, short enough that a hang fails fast. */
const RESOLVED_SEARCH_WINDOW_MS = 1000;

describe('mctsSearch continuous — no missing wakeup (claim (e), X-8)', () => {
  it('wakeup: a search over already-resolved providers completes with the expected node count', async () => {
    for (const providers of [makeResolvedProviders(), withVariedGrade(simplePolicy())]) {
      const search = mctsSearch(
        SIMPLE_WHITE_FEN,
        { maxNodes: 12, elo: NEUTRAL_ELO, maxPlies: 4, concurrency: 4, dispatchMode: 'continuous' },
        providers,
        () => {},
        new AbortController().signal,
      );
      const outcome = await settlesWithin(search, RESOLVED_SEARCH_WINDOW_MS);

      expect(outcome.state).toBe('resolved');
      if (outcome.state === 'resolved') expect(outcome.value.nodesEvaluated).toBe(12);
    }
  });

  it('wakeup: a settlement that lands during a drain, and one that finds no waiter, are both applied', async () => {
    const holder: { run?: ControlledRun } = {};
    const run = startControlled(
      { concurrency: 2, maxNodes: 8 },
      {
        afterSnapshot: (snapshot) => {
          // Inside the drain of the first applied expansion, settle the other in-flight grade.
          if (snapshot.nodesEvaluated === 2) holder.run?.ctl.settle(2);
        },
      },
    );
    holder.run = run;
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    run.ctl.settle(1);

    const outcome = await driveToCompletion(run);

    expect(outcome.state).toBe('resolved');
    if (outcome.state === 'resolved') expect(outcome.value.nodesEvaluated).toBe(8);
  });

  it('wakeup: a timer-driven abort wakes a loop that is waiting on slow work, before anything settles', async () => {
    const run = startControlled({ concurrency: 3 });
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    expect(run.ctl.calls).toHaveLength(4); // three expansions in flight, none of which will settle by itself
    const TIMER_ABORT_MS = 15;
    setTimeout(() => run.controller.abort(), TIMER_ABORT_MS); // a macrotask abort, like the deadline timer

    const outcome = await settlesWithin(run.search);

    expect(outcome.state).toBe('resolved'); // woken by the abort alone: no provider settled
    for (const call of [run.ctl.calls[1], run.ctl.calls[2], run.ctl.calls[3]]) expect(call?.signal?.aborted).toBe(true);
    run.ctl.settle(1);
    run.ctl.settle(2);
    run.ctl.settle(3);
    await flushTurns();
    expect(run.snapshots).toHaveLength(1); // none applied after the abort
  });

  it('wakeup: an abort raised synchronously inside a provider during a fill still returns and stops the fill (R2B-2)', async () => {
    const controller = new AbortController();
    const policyCalls: PolicyCall[] = [];
    const base = makeFixedPolicy({ [SIMPLE_WHITE_FEN]: SIMPLE_WHITE_POLICY }, policyCalls);
    const ctl = makeControlledGrade();
    const policy: EngineProviders['policy'] = (fen, elo, side, signal) => {
      // First non-root dispatch (the root was call 0): abort from the provider's synchronous prefix, mid-fill.
      if (policyCalls.length === 1) controller.abort();
      return base(fen, elo, side, signal);
    };
    const search = mctsSearch(
      SIMPLE_WHITE_FEN,
      { maxNodes: 8, elo: NEUTRAL_ELO, maxPlies: 3, concurrency: 4, dispatchMode: 'continuous' },
      { policy, grade: ctl.grade },
      () => {},
      controller.signal,
    );
    await flushTurns();
    ctl.settle(0);

    const outcome = await settlesWithin(search); // a grade that never settles must not hang the search

    expect(outcome.state).toBe('resolved');
    expect(policyCalls).toHaveLength(2); // root + the aborting dispatch: the rest of that fill dispatched nothing
  });
});

// ─── listener hygiene ────────────────────────────────────────────────────────

/** Spies on `signal`'s abort-listener registrations; counts only 'abort' listeners. */
function spyOnAbortListeners(signal: AbortSignal): { added: () => number; removed: () => number } {
  const add = vi.spyOn(signal, 'addEventListener');
  const remove = vi.spyOn(signal, 'removeEventListener');
  const abortCalls = (calls: readonly (readonly unknown[])[]): number => calls.filter((call) => call[0] === 'abort').length;
  return { added: () => abortCalls(add.mock.calls), removed: () => abortCalls(remove.mock.calls) };
}

describe('mctsSearch continuous — listener hygiene (Pitfall 7)', () => {
  it('listener: the outer signal ends with exactly the one abort listener it was given removed, after resolving', async () => {
    const outer = new AbortController();
    const spy = spyOnAbortListeners(outer.signal);

    await mctsSearch(
      SIMPLE_WHITE_FEN,
      { maxNodes: 12, elo: NEUTRAL_ELO, maxPlies: 4, concurrency: 3, dispatchMode: 'continuous' },
      withVariedGrade(simplePolicy()),
      () => {},
      outer.signal,
    );

    expect(spy.added()).toBe(1); // one listener for the whole search, never one per dispatch
    expect(spy.removed()).toBe(1);
  });

  it('listener: the same holds when the search rejects', async () => {
    const outer = new AbortController();
    const spy = spyOnAbortListeners(outer.signal);
    const run = startControlled({ concurrency: 2 }, { signal: outer.signal });
    await flushTurns();
    run.ctl.settle(0);
    await flushTurns();
    run.ctl.calls[1]?.result.reject(new Error('provider failed'));

    const outcome = await settlesWithin(run.search);
    run.ctl.settleEmpty(2);
    await flushTurns();

    expect(outcome.state).toBe('rejected');
    expect(spy.added()).toBe(1);
    expect(spy.removed()).toBe(1);
  });
});

