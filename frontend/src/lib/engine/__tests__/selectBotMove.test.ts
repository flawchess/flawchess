/**
 * selectBotMove.ts unit tests (Phase 166 BOT-01/BOT-02/BOT-03/BOT-04).
 *
 * Covers, all via stubbed `deps.policy`/`deps.search`/`deps.grade` and a
 * seeded `mulberry32` rng (D-08's "unit tests can pass a stub returning
 * canned RankedLine[]"):
 * - blend=0: exactly one deps.policy call, zero deps.search calls (BOT-02).
 * - blend=1: argmax over practicalScore, deterministic regardless of rng.
 * - blend=0.5: one deps.search call with a real no-op onSnapshot function
 *   reference (Pitfall 5), tau=0.05, deterministic under a fixed seed.
 * - budget.elo is always symmetric {w: elo, b: elo} (BOT-03), regardless of
 *   any other input; no policyTemperature set on the budget (D-02).
 * - budget.maxNodes/maxPlies/concurrency pass through unchanged.
 * - degenerate policy/rankedLines -> fallbackMove yields a legal move (BOT-04).
 * - side is derived from the FEN and passed to deps.policy on blend=0.
 * - signal defaults to a never-aborting AbortSignal; a provided signal is
 *   forwarded to deps.search on blend>0 paths.
 */

import { describe, it, expect, vi } from 'vitest';
import { selectBotMove, TAU_MAX, type BotMoveDeps, type BotSettings } from '../selectBotMove';
import { mulberry32, samplePolicy, argmaxLine } from '../botSampling';
import type { BotStyleParams, FeatureMultipliers } from '../botStyle';
import type { EngineSnapshot, MoveGrade, RankedLine, SearchBudget, Side } from '../types';

const WHITE_FEN = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'; // 6 legal moves
const BLACK_FEN = '4k3/4p3/8/8/8/8/8/4K3 b - - 0 1';
const CHECKMATE_FEN = 'rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3'; // fool's mate

function makeLine(
  rootMove: string,
  practicalScore: number,
  childScoreSpread: number | null = null,
): RankedLine {
  return {
    rootMove,
    practicalScore,
    objectiveEvalCp: null,
    objectiveEvalMate: null,
    modalPath: [],
    modalStats: [],
    visits: 0,
    childScoreSpread,
  };
}

// ─── Style fixtures (Phase 182, Plan 06) ────────────────────────────────────

const NEUTRAL_FEATURE_MULTIPLIERS: FeatureMultipliers = {
  isCheck: 1,
  isCapture: 1,
  isPawnAdvance: 1,
  isPawnStorm: 1,
  isExchange: 1,
  isRetreat: 1,
};

function makeStyle(overrides: Partial<BotStyleParams> = {}): BotStyleParams {
  return {
    featureMultipliers: NEUTRAL_FEATURE_MULTIPLIERS,
    scoreBonus: 0,
    varianceBonus: 0,
    contempt: 0,
    threshold: 0,
    hysteresisFloor: 0,
    bookBoost: 1,
    ...overrides,
  };
}

function makeSnapshot(lines: RankedLine[]): EngineSnapshot {
  return { rankedLines: lines, nodesEvaluated: lines.length, budgetExhausted: true, stopReason: 'budget' };
}

interface SearchCall {
  fen: string;
  budget: SearchBudget;
  onSnapshot: (snapshot: EngineSnapshot) => void;
  signal: AbortSignal;
}

/** Builds a stubbed deps.search recording every call, resolving to `lines`. */
function stubSearch(lines: RankedLine[]) {
  const calls: SearchCall[] = [];
  const search = vi.fn(
    async (
      fen: string,
      budget: SearchBudget,
      _providers: unknown,
      onSnapshot: (snapshot: EngineSnapshot) => void,
      signal: AbortSignal,
    ): Promise<EngineSnapshot> => {
      calls.push({ fen, budget, onSnapshot, signal });
      return makeSnapshot(lines);
    },
  );
  return { search, calls };
}

function baseBudget(): Omit<SearchBudget, 'elo' | 'policyTemperature'> {
  return { maxNodes: 200, maxPlies: 6, concurrency: 2 };
}

function baseDeps(overrides: Partial<BotMoveDeps> = {}): BotMoveDeps {
  return {
    policy: vi.fn(async (): Promise<Record<string, number>> => ({})),
    grade: vi.fn(async (): Promise<Map<string, MoveGrade>> => new Map()),
    rng: mulberry32(1),
    ...overrides,
  };
}

// ─── blend=0 — single Maia inference, no search (BOT-02) ───────────────────

describe('selectBotMove — blend=0 (full-human)', () => {
  it('calls deps.policy exactly once and deps.search zero times', async () => {
    const policy = vi.fn(async (): Promise<Record<string, number>> => ({ e2e3: 0.6, e2e4: 0.4 }));
    const { search } = stubSearch([makeLine('e2e3', 0.5)]);
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };
    const deps = baseDeps({ policy, search });

    await selectBotMove(WHITE_FEN, settings, deps);

    expect(policy).toHaveBeenCalledTimes(1);
    expect(search).toHaveBeenCalledTimes(0);
  });

  it('samples the raw Maia policy and returns a move from it', async () => {
    const policy = vi.fn(async (): Promise<Record<string, number>> => ({ e2e3: 1 }));
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };
    const deps = baseDeps({ policy });

    const move = await selectBotMove(WHITE_FEN, settings, deps);
    expect(move).toBe('e2e3');
  });

  it('derives side from the FEN and passes it to deps.policy', async () => {
    const seenSides: Side[] = [];
    const policy = vi.fn(async (_fen: string, _elo: number, side: Side) => {
      seenSides.push(side);
      return { e7e6: 1 };
    });
    const settingsWhite: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };
    const settingsBlack: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };

    await selectBotMove(WHITE_FEN, settingsWhite, baseDeps({ policy }));
    await selectBotMove(BLACK_FEN, settingsBlack, baseDeps({ policy }));

    expect(seenSides).toEqual(['w', 'b']);
  });

  it('falls back to a legal move when the policy is empty/degenerate (BOT-04)', async () => {
    const policy = vi.fn(async (): Promise<Record<string, number>> => ({}));
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };
    const deps = baseDeps({ policy, rng: mulberry32(1) });

    const move = await selectBotMove(WHITE_FEN, settings, deps);
    expect(move).toMatch(/^[a-h][1-8][a-h][1-8][qrbn]?$/);
  });
});

// ─── blend=1 — deterministic argmax over practicalScore (BOT-01) ───────────

describe('selectBotMove — blend=1 (full-stockfish)', () => {
  it('calls deps.search once and returns the argmax-practicalScore move, regardless of rng', async () => {
    // Deliberately NOT sorted by practicalScore — proves argmax scans explicitly.
    const lines = [makeLine('a1a2', 0.2), makeLine('c1c2', 0.95), makeLine('b1b2', 0.6)];
    const settings: BotSettings = { elo: 1800, blend: 1, budget: baseBudget() };

    for (const seed of [1, 2, 3]) {
      const { search, calls } = stubSearch(lines);
      const deps = baseDeps({ search, rng: mulberry32(seed) });
      const move = await selectBotMove(WHITE_FEN, settings, deps);
      expect(move).toBe('c1c2');
      expect(search).toHaveBeenCalledTimes(1);
      expect(calls[0]?.onSnapshot).toBeTypeOf('function');
    }
  });

  it('falls back to a legal move when rankedLines is empty (BOT-04)', async () => {
    const { search } = stubSearch([]);
    const settings: BotSettings = { elo: 1800, blend: 1, budget: baseBudget() };
    const deps = baseDeps({ search, rng: mulberry32(1) });

    const move = await selectBotMove(WHITE_FEN, settings, deps);
    expect(move).toMatch(/^[a-h][1-8][a-h][1-8][qrbn]?$/);
  });
});

// ─── blend in (0,1) — softmax-weighted sampling with slider sharpness ──────

describe('selectBotMove — blend=0.5 (mixed)', () => {
  it('calls deps.search once with a real onSnapshot function reference and a tau=0.05 softmax', async () => {
    // The previous version of this test recomputed the tau formula inside
    // the test (tautological, WR-05) — tau is instead observed through the
    // sampling distribution: with scores {a1a2: 0.3, b1b2: 0.9}, a1a2's
    // softmax mass is exp(-0.6/tau)/(1 + exp(-0.6/tau)): ~6.1e-6 at the
    // correct tau=0.05 but ~2.5e-3 at tau=0.1. The constant draws below
    // bracket those masses, so a wrong tau (or an ignored blend) fails.
    const lines = [makeLine('a1a2', 0.3), makeLine('b1b2', 0.9)];
    const settings: BotSettings = { elo: 1500, blend: 0.5, budget: baseBudget() };

    // The bracketing draws above are calibrated against TAU_MAX = 0.1
    // (tau = TAU_MAX * (1 - 0.5) = 0.05) — anchor it so a curve change
    // forces this fixture to be recalibrated.
    expect(TAU_MAX).toBe(0.1);

    // draw = 0.001 * total: above a1a2's cumulative mass at tau=0.05
    // (~6.1e-6) but below it at tau=0.1 (~2.5e-3) -> must pick b1b2.
    const { search, calls } = stubSearch(lines);
    const deps = baseDeps({ search, rng: () => 0.001 });
    const move = await selectBotMove(WHITE_FEN, settings, deps);

    expect(search).toHaveBeenCalledTimes(1);
    expect(typeof calls[0]?.onSnapshot).toBe('function');
    expect(move).toBe('b1b2');

    // draw = 1e-7 * total: below a1a2's mass at tau=0.05 -> must pick a1a2,
    // proving the softmax puts real (non-zero, tau-sized) mass on the
    // lower-scored move.
    const { search: searchLow } = stubSearch(lines);
    const moveLow = await selectBotMove(
      WHITE_FEN,
      settings,
      baseDeps({ search: searchLow, rng: () => 1e-7 }),
    );
    expect(moveLow).toBe('a1a2');
  });

  it('short-circuits to argmax when tau <= TAU_EPSILON (blend just below 1)', async () => {
    // IN-02: blend = 1 - 1e-9 gives tau = TAU_MAX * 1e-9 = 1e-10, at or
    // below TAU_EPSILON (1e-9) — the orchestrator must take the argmax
    // short-circuit (previously the only untested branch), returning the
    // max-practicalScore move regardless of rng, mirroring the blend=1 test.
    const lines = [makeLine('a1a2', 0.2), makeLine('c1c2', 0.95), makeLine('b1b2', 0.6)];
    const settings: BotSettings = { elo: 1500, blend: 1 - 1e-9, budget: baseBudget() };

    for (const rng of [() => 0, () => 0.5, () => 0.999]) {
      const { search } = stubSearch(lines);
      const move = await selectBotMove(WHITE_FEN, settings, baseDeps({ search, rng }));
      expect(move).toBe('c1c2');
      expect(search).toHaveBeenCalledTimes(1);
    }
  });

  it('is deterministic under a fixed seed', async () => {
    const lines = [makeLine('a1a2', 0.3), makeLine('b1b2', 0.9), makeLine('c1c2', 0.5)];
    const settings: BotSettings = { elo: 1500, blend: 0.5, budget: baseBudget() };

    const { search: searchA } = stubSearch(lines);
    const moveA = await selectBotMove(WHITE_FEN, settings, baseDeps({ search: searchA, rng: mulberry32(99) }));
    const { search: searchB } = stubSearch(lines);
    const moveB = await selectBotMove(WHITE_FEN, settings, baseDeps({ search: searchB, rng: mulberry32(99) }));

    expect(moveA).toBe(moveB);
  });
});

// ─── blend domain clamping (IN-03) ──────────────────────────────────────────

describe('selectBotMove — blend clamping', () => {
  it('clamps a NaN blend to 1 (deterministic argmax) instead of a NaN-tau softmax', async () => {
    // A NaN blend fails all three regime checks (NaN comparisons are always
    // false) and previously reached sampleRankedLines with tau = NaN; the
    // clamp maps it to blend = 1: one search call, zero policy calls, argmax
    // move regardless of rng.
    const lines = [makeLine('a1a2', 0.2), makeLine('c1c2', 0.95), makeLine('b1b2', 0.6)];
    const policy = vi.fn(async (): Promise<Record<string, number>> => ({ a1a2: 1 }));
    const { search } = stubSearch(lines);
    const settings: BotSettings = { elo: 1500, blend: Number.NaN, budget: baseBudget() };
    const deps = baseDeps({ policy, search, rng: () => 0.999 });

    const move = await selectBotMove(WHITE_FEN, settings, deps);

    expect(move).toBe('c1c2');
    expect(search).toHaveBeenCalledTimes(1);
    expect(policy).toHaveBeenCalledTimes(0);
  });
});

// ─── Symmetric ELO (BOT-03) ─────────────────────────────────────────────────

describe('selectBotMove — symmetric ELO (BOT-03)', () => {
  it('builds budget.elo = {w: elo, b: elo} regardless of other input, and omits policyTemperature', async () => {
    const lines = [makeLine('a1a2', 0.5)];
    const settings: BotSettings = { elo: 1732, blend: 0.7, budget: baseBudget() };
    const { search, calls } = stubSearch(lines);
    const deps = baseDeps({ search });

    await selectBotMove(WHITE_FEN, settings, deps);

    const capturedBudget = calls[0]?.budget;
    expect(capturedBudget?.elo).toEqual({ w: 1732, b: 1732 });
    expect(capturedBudget?.maxNodes).toBe(200);
    expect(capturedBudget?.maxPlies).toBe(6);
    expect(capturedBudget?.concurrency).toBe(2);
    expect(capturedBudget?.policyTemperature).toBeUndefined();
  });

  it('rejects policyTemperature on BotSettings.budget at the type level (D-02/WR-04)', () => {
    // The D-02 invariant is structural: Omit<SearchBudget, 'elo' |
    // 'policyTemperature'> makes threading the analysis board's temperature
    // into the bot budget a compile error at any production call site
    // (enforced by tsc -b on src). The @ts-expect-error below documents the
    // exclusion in-editor; note tsconfig.app.json excludes *.test.ts from
    // the build, so the real gate is the BotSettings type itself.
    const settings: BotSettings = {
      elo: 1500,
      blend: 0.5,
      budget: {
        ...baseBudget(),
        // @ts-expect-error — policyTemperature is excluded by type (D-02/WR-04)
        policyTemperature: 1.5,
      },
    };
    expect(settings.elo).toBe(1500);
  });
});

// ─── Terminal position — genuine throw (BOT-04/D-14) ────────────────────────

describe('selectBotMove — terminal position', () => {
  it('throws when the position is checkmate and the fallback path is reached', async () => {
    const policy = vi.fn(async (): Promise<Record<string, number>> => ({}));
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() };
    const deps = baseDeps({ policy });

    await expect(selectBotMove(CHECKMATE_FEN, settings, deps)).rejects.toThrow(/no legal moves/);
  });
});

// ─── AbortSignal — default + forwarding ─────────────────────────────────────

describe('selectBotMove — signal', () => {
  it('defaults to a never-aborting signal when omitted', async () => {
    const lines = [makeLine('a1a2', 0.5)];
    const { search, calls } = stubSearch(lines);
    const settings: BotSettings = { elo: 1500, blend: 1, budget: baseBudget() };
    const deps = baseDeps({ search });

    await selectBotMove(WHITE_FEN, settings, deps);

    expect(calls[0]?.signal.aborted).toBe(false);
  });

  it('forwards a provided signal to deps.search on blend>0 paths', async () => {
    const lines = [makeLine('a1a2', 0.5)];
    const { search, calls } = stubSearch(lines);
    const settings: BotSettings = { elo: 1500, blend: 1, budget: baseBudget() };
    const deps = baseDeps({ search });
    const controller = new AbortController();

    await selectBotMove(WHITE_FEN, settings, deps, controller.signal);

    expect(calls[0]?.signal).toBe(controller.signal);
  });
});

// ─── Style hooks (Phase 182, STYLE-03/04/05) ────────────────────────────────

describe('selectBotMove — style undefined regression (D-03 baseline invariant)', () => {
  it('blend<=0: an omitted style samples the raw policy exactly as before the field existed', async () => {
    // WHITE_FEN has no captures/checks/exchanges/retreats among its 6 legal
    // moves, but e2e3/e2e4 ARE pawn advances — a style boosting
    // isPawnAdvance would visibly shift this distribution (see the styled
    // test below), so this fixture is a real discriminator, not a vacuous
    // one.
    const rawPolicy = { e1d1: 1, e1d2: 1, e1f1: 1, e1f2: 1, e2e3: 1, e2e4: 1 };
    const policy = vi.fn(async (): Promise<Record<string, number>> => rawPolicy);
    const rng = () => 0.5;
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget() }; // no `style` key at all

    const move = await selectBotMove(WHITE_FEN, settings, baseDeps({ policy, rng }));

    // The expectation is derived from calling samplePolicy directly on the
    // UNTRANSFORMED rawPolicy — proving selectBotMove ran zero reweight
    // calls when style is undefined (a mutation that made the reweight
    // unconditional would diverge from this independently-computed value).
    expect(move).toBe(samplePolicy(rawPolicy, rng));
    expect(move).toBe('e1f2');
  });

  it('search branch: an omitted style leaves practicalScore untouched exactly as before the field existed', async () => {
    const lines = [makeLine('a1a2', 0.5, 0.5), makeLine('b1b2', 0.52, 0)];
    const { search } = stubSearch(lines);
    const settings: BotSettings = { elo: 1800, blend: 1, budget: baseBudget() }; // no `style` key at all

    const move = await selectBotMove(WHITE_FEN, settings, baseDeps({ search }));

    // Derived independently from argmaxLine over the UNSHAPED lines — proves
    // selectBotMove ran zero shaping calls when style is undefined.
    expect(move).toBe(argmaxLine(lines));
    expect(move).toBe('b1b2');
  });
});

describe('selectBotMove — styled blend<=0 (STYLE-03 prior reweighting)', () => {
  it('a style favoring isPawnAdvance shifts the sampled move toward a pawn push vs the undefined-style baseline', async () => {
    const rawPolicy = { e1d1: 1, e1d2: 1, e1f1: 1, e1f2: 1, e2e3: 1, e2e4: 1 };
    const policy = vi.fn(async (): Promise<Record<string, number>> => rawPolicy);
    const rng = () => 0.5;
    const style = makeStyle({
      featureMultipliers: { ...NEUTRAL_FEATURE_MULTIPLIERS, isPawnAdvance: 1000 },
    });
    const settings: BotSettings = { elo: 1500, blend: 0, budget: baseBudget(), style };

    const move = await selectBotMove(WHITE_FEN, settings, baseDeps({ policy, rng }));

    // Baseline (no style, same rawPolicy/rng) picks e1f2 (see the regression
    // test above) — the style must pick a DIFFERENT, pawn-advance move.
    expect(move).toBe('e2e3');
    expect(move).not.toBe('e1f2');
  });
});

describe('selectBotMove — styled search branch (STYLE-04 score shaping)', () => {
  it('a style score bonus on one line changes the argmax pick vs the undefined-style baseline', async () => {
    const lines = [makeLine('a1a2', 0.5, 0.5), makeLine('b1b2', 0.52, 0)];
    const { search, calls } = stubSearch(lines);
    // Uniform scoreBonus alone never changes ranking (it's additive across
    // every line) — the differentiator is varianceBonus x childScoreSpread,
    // which favors a1a2's wider spread enough to overtake b1b2's higher raw
    // practicalScore.
    const style = makeStyle({ scoreBonus: 0, varianceBonus: 0.5 });
    const settings: BotSettings = { elo: 1800, blend: 1, budget: baseBudget(), style };

    const move = await selectBotMove(WHITE_FEN, settings, baseDeps({ search }));

    // Baseline (no style, same lines) picks b1b2 (see the regression test
    // above) — the style must pick a DIFFERENT, higher-spread line.
    expect(move).toBe('a1a2');
    expect(move).not.toBe('b1b2');
    // BOT-03: budget.elo stays symmetric regardless of style.
    expect(calls[0]?.budget.elo).toEqual({ w: 1800, b: 1800 });
  });
});
