import { describe, expect, it } from 'vitest';
import {
  FEATURE_ROUTE,
  FEATURE_ROUTE_SKIP_ACTIVE_DAYS,
  applyRouteWrite,
  isRouteWriteNeeded,
  planRouteWrites,
  resolveRouteDot,
  type RouteCtx,
  type RouteStepDef,
} from '@/lib/featureRoute';
import type { FeatureRouteState, FeatureRouteStepId } from '@/types/users';

// Order pinned against the backend FeatureRouteStepId in
// tests/test_feature_route.py (D-06, D-09).
const EXPECTED_STEP_IDS: FeatureRouteStepId[] = [
  'import',
  'train',
  'bots',
  'openings',
  'openings-played-as',
  'openings-filters',
  'openings-stats',
  'endgames',
  'library-stats',
];

const TEST_DATE = '2026-11-15';
const TODAY = '2026-11-16';

function ctx(pathname: string, navUnlocked: boolean, activeDays = 1): RouteCtx {
  return { pathname, navUnlocked, activeDays };
}

function withCurrent(
  state: FeatureRouteState,
  step: FeatureRouteStepId | null,
  sinceDays = 2,
): FeatureRouteState {
  return { ...state, current: step == null ? null : { step, since_days: sinceDays } };
}

function stateWith(done: FeatureRouteStepId[], skipped: FeatureRouteStepId[] = []): FeatureRouteState {
  const steps: FeatureRouteState['steps'] = {};
  for (const id of done) steps[id] = { status: 'done', date: TEST_DATE, with_dot: false };
  for (const id of skipped) steps[id] = { status: 'skipped', date: TEST_DATE, with_dot: true };
  return { steps, current: null };
}

function stepById(id: FeatureRouteStepId): RouteStepDef {
  const step = FEATURE_ROUTE.find((s) => s.id === id);
  if (step == null) throw new Error(`unknown route step ${id}`);
  return step;
}

// A games-free step (bots) after a locked one (openings): no such pair exists among
// the nine launch steps, so the D-23 pause is pinned on this reordered route.
const REORDERED_ROUTE: readonly RouteStepDef[] = [
  stepById('import'),
  stepById('train'),
  stepById('openings'),
  stepById('bots'),
];

function placement(state: FeatureRouteState | null, c: RouteCtx): string | null {
  return resolveRouteDot(state, c)?.slot ?? null;
}

describe('FEATURE_ROUTE registry', () => {
  it('holds the nine step IDs in D-06 order without duplicates', () => {
    const ids = FEATURE_ROUTE.map((s) => s.id);
    expect(ids).toEqual(EXPECTED_STEP_IDS);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('resolveRouteDot order (D-02, D-12)', () => {
  it('with only import resolved the dot is on train', () => {
    expect(resolveRouteDot(stateWith(['import']), ctx('/library/games', true))?.step).toBe('train');
  });

  it('with every step resolved except bots and endgames the dot is on bots (no queue-jumping)', () => {
    const done = EXPECTED_STEP_IDS.filter((id) => id !== 'bots' && id !== 'endgames');
    expect(resolveRouteDot(stateWith(done), ctx('/library/games', true))?.step).toBe('bots');
  });

  it('a skipped step counts as resolved', () => {
    expect(resolveRouteDot(stateWith(['import'], ['train']), ctx('/library/games', true))?.step).toBe('bots');
  });

  it('a fully resolved route has no dot', () => {
    expect(placement(stateWith(EXPECTED_STEP_IDS), ctx('/library/games', true))).toBeNull();
  });

  it('a null state fails closed: no dot and no writes', () => {
    expect(resolveRouteDot(null, ctx('/library/import', true))).toBeNull();
    expect(planRouteWrites(null, ctx('/library/import', true))).toEqual([]);
  });
});

describe('placement (D-03)', () => {
  it('train: nav outside the section, Today subtab on another tab, start button on Today', () => {
    const s = stateWith(['import']);
    expect(placement(s, ctx('/library/games', true))).toBe('nav:/train');
    expect(placement(s, ctx('/train/leaderboard', true))).toBe('subtab:train-today');
    expect(placement(s, ctx('/train', true))).toBe('control:train-start');
  });

  it('import: nav elsewhere, Import subtab inside Library, nothing on the Import page itself', () => {
    const s = stateWith([]);
    expect(placement(s, ctx('/bots', false))).toBe('nav:/library');
    expect(placement(s, ctx('/library/games', false))).toBe('subtab:library-import');
    expect(placement(s, ctx('/library/import', false))).toBeNull();
  });

  it('openings-played-as: nav elsewhere, control inside Openings', () => {
    const s = stateWith(['import', 'train', 'bots', 'openings']);
    expect(placement(s, ctx('/library/games', true))).toBe('nav:/openings');
    expect(placement(s, ctx('/openings/stats', true))).toBe('control:openings-played-as');
  });

  it('openings-stats: subtab while elsewhere in Openings, nothing on the Stats page', () => {
    const s = stateWith(['import', 'train', 'bots', 'openings', 'openings-played-as', 'openings-filters']);
    expect(placement(s, ctx('/openings/explorer', true))).toBe('subtab:openings-stats');
    expect(placement(s, ctx('/openings/stats', true))).toBeNull();
  });

  it('library-stats: subtab inside Library', () => {
    const s = stateWith(EXPECTED_STEP_IDS.filter((id) => id !== 'library-stats'));
    expect(placement(s, ctx('/library/games', true))).toBe('subtab:library-stats');
    expect(placement(s, ctx('/bots', true))).toBe('nav:/library');
  });
});

describe('locked steps pause the route (D-23)', () => {
  it('with import, train and bots resolved and nav locked there is no dot', () => {
    expect(placement(stateWith(['import', 'train', 'bots']), ctx('/library/games', false))).toBeNull();
  });

  it('Train is never locked (D-21)', () => {
    expect(resolveRouteDot(stateWith(['import']), ctx('/library/games', false))?.step).toBe('train');
  });

  it('Bots is never locked', () => {
    expect(resolveRouteDot(stateWith(['import', 'train']), ctx('/library/games', false))?.step).toBe('bots');
  });

  it('a games-free step after a locked one stays hidden until the locked step unlocks and is resolved', () => {
    const c = (navUnlocked: boolean): RouteCtx => ctx('/library/games', navUnlocked);
    const resolved = stateWith(['import', 'train']);
    // bots is games-free and unresolved but sits behind the locked openings step.
    expect(resolveRouteDot(resolved, c(false), REORDERED_ROUTE)).toBeNull();
    expect(resolveRouteDot(resolved, c(true), REORDERED_ROUTE)?.slot).toBe('nav:/openings');
    expect(resolveRouteDot(stateWith(['import', 'train', 'openings']), c(false), REORDERED_ROUTE)?.slot).toBe(
      'nav:/bots',
    );
  });
});

// The done requests only: the clock's skip and current requests have their own describes below.
function doneWrites(state: FeatureRouteState | null, c: RouteCtx, route?: readonly RouteStepDef[]) {
  return planRouteWrites(state, c, route).filter((r) => r.action === 'done');
}

describe('done recording (D-15, A-2, A-4)', () => {
  it('records import when its page opens', () => {
    expect(doneWrites(stateWith([]), ctx('/library/import', false))).toEqual([
      { action: 'done', step: 'import' },
    ]);
  });

  it('records openings then openings-stats on the stats page, in route order', () => {
    expect(doneWrites(stateWith(['import']), ctx('/openings/stats', true))).toEqual([
      { action: 'done', step: 'openings' },
      { action: 'done', step: 'openings-stats' },
    ]);
  });

  it('records nothing for a locked target (a zero-game visit to /openings)', () => {
    expect(doneWrites(stateWith(['import']), ctx('/openings', false))).toEqual([]);
  });

  it('never records train on a visit (it completes on use, D-21)', () => {
    expect(doneWrites(stateWith(['import']), ctx('/train', true))).toEqual([]);
  });

  it('a skipped step visited becomes done (A-4)', () => {
    expect(doneWrites(stateWith(['import'], ['bots']), ctx('/bots', true))).toEqual([
      { action: 'done', step: 'bots' },
    ]);
  });

  it('a done step visited records nothing', () => {
    expect(doneWrites(stateWith(['import', 'bots']), ctx('/bots', true))).toEqual([]);
  });

  it('keeps recording while the dot is paused on a locked step (D-23 stops the dot, not the recording)', () => {
    const resolved = stateWith(['import', 'train']);
    const c = ctx('/bots', false);
    expect(resolveRouteDot(resolved, c, REORDERED_ROUTE)).toBeNull();
    expect(doneWrites(resolved, c, REORDERED_ROUTE)).toEqual([{ action: 'done', step: 'bots' }]);
  });
});

describe('applyRouteWrite', () => {
  it('stores with_dot true when the step was current', () => {
    const state: FeatureRouteState = { steps: {}, current: { step: 'bots', since_days: 2 } };
    const next = applyRouteWrite(state, { action: 'done', step: 'bots' }, { today: TODAY, activeDays: 3 });
    expect(next.steps.bots).toEqual({ status: 'done', date: TODAY, with_dot: true });
  });

  it('stores with_dot false for a step that was not current', () => {
    const state: FeatureRouteState = { steps: {}, current: { step: 'bots', since_days: 2 } };
    const next = applyRouteWrite(state, { action: 'done', step: 'import' }, { today: TODAY, activeDays: 3 });
    expect(next.steps.import).toEqual({ status: 'done', date: TODAY, with_dot: false });
  });

  it('never mutates its input', () => {
    const state = stateWith(['import']);
    const snapshot = JSON.parse(JSON.stringify(state)) as FeatureRouteState;
    const next = applyRouteWrite(state, { action: 'done', step: 'train' }, { today: TODAY, activeDays: 3 });
    expect(state).toEqual(snapshot);
    expect(next).not.toBe(state);
    expect(Object.keys(next.steps)).toEqual(['import', 'train']);
  });
});

describe('the 3-active-day clock (D-10)', () => {
  const base = withCurrent(stateWith(['import']), 'train', 2);

  it('uses a window of three active days', () => {
    expect(FEATURE_ROUTE_SKIP_ACTIVE_DAYS).toBe(3);
  });

  it('keeps the dot on the current step through active day since_days + 2 and drops it at + 3', () => {
    expect(placement(base, ctx('/library/games', true, 4))).toBe('nav:/train');
    expect(placement(base, ctx('/library/games', true, 5))).toBeNull();
  });

  it('posts [skip train, current bots] once expired and nothing before that', () => {
    expect(planRouteWrites(base, ctx('/library/games', true, 5))).toEqual([
      { action: 'skip', step: 'train' },
      { action: 'current', step: 'bots' },
    ]);
    expect(planRouteWrites(base, ctx('/library/games', true, 4))).toEqual([]);
  });

  it('stamps the first unresolved step: [done import, current train] for a fresh signup on Import', () => {
    expect(planRouteWrites(stateWith([]), ctx('/library/import', false, 1))).toEqual([
      { action: 'done', step: 'import' },
      { action: 'current', step: 'train' },
    ]);
  });

  it('visiting a later step stamps the first unresolved one: [done bots, current train]', () => {
    expect(planRouteWrites(stateWith(['import']), ctx('/bots', true, 1))).toEqual([
      { action: 'done', step: 'bots' },
      { action: 'current', step: 'train' },
    ]);
  });

  it('a done on the expired current step wins over a skip', () => {
    const state = withCurrent(stateWith(['import', 'train']), 'bots', 2);
    expect(planRouteWrites(state, ctx('/bots', true, 9))).toEqual([
      { action: 'done', step: 'bots' },
      { action: 'current', step: 'openings' },
    ]);
  });
});

describe('locked steps never run the clock (D-23, A-7)', () => {
  it('skips the games-free current step but stamps nothing when the next step is locked', () => {
    const state = withCurrent(stateWith(['import', 'train']), 'bots', 2);
    expect(planRouteWrites(state, ctx('/library/games', false, 5))).toEqual([{ action: 'skip', step: 'bots' }]);
  });

  it('a fully-resolved-but-locked route writes nothing', () => {
    expect(planRouteWrites(stateWith(['import', 'train', 'bots']), ctx('/library/games', false, 5))).toEqual([]);
  });

  it('emits current only for the first unresolved step and only while its target is available', () => {
    const state = stateWith(['import', 'train']);
    const locked = ctx('/library/games', false, 3);
    const unlocked = ctx('/library/games', true, 3);
    expect(planRouteWrites(state, locked, REORDERED_ROUTE)).toEqual([]);
    expect(planRouteWrites(state, unlocked, REORDERED_ROUTE)).toEqual([{ action: 'current', step: 'openings' }]);
  });

  it('a stale stamp on a locked step is neither dotted nor skipped while locked', () => {
    const state = withCurrent(stateWith(['import', 'train', 'bots']), 'openings', 2);
    const locked = ctx('/library/games', false, 9);
    expect(resolveRouteDot(state, locked)).toBeNull();
    expect(planRouteWrites(state, locked)).toEqual([]);
  });

  it('restarts the clock on unlock: no stamp left, current is stamped with the unlock-day count', () => {
    const cleared = withCurrent(stateWith(['import', 'train', 'bots']), null);
    const unlocked = ctx('/library/games', true, 9);
    const plan = planRouteWrites(cleared, unlocked);
    expect(plan).toEqual([{ action: 'current', step: 'openings' }]);
    const stamped = applyRouteWrite(cleared, { action: 'current', step: 'openings' }, { today: TODAY, activeDays: 9 });
    expect(stamped.current).toEqual({ step: 'openings', since_days: 9 });
    expect(placement(stamped, unlocked)).toBe('nav:/openings');
  });
});

describe('applyRouteWrite current and skip', () => {
  it('current sets {step, since_days: activeDays}', () => {
    const state = stateWith(['import']);
    const next = applyRouteWrite(state, { action: 'current', step: 'train' }, { today: TODAY, activeDays: 4 });
    expect(next.current).toEqual({ step: 'train', since_days: 4 });
    expect(state.current).toBeNull();
  });

  it('skip stores {skipped, today, with_dot true}', () => {
    const state = withCurrent(stateWith(['import']), 'train', 2);
    const next = applyRouteWrite(state, { action: 'skip', step: 'train' }, { today: TODAY, activeDays: 5 });
    expect(next.steps.train).toEqual({ status: 'skipped', date: TODAY, with_dot: true });
    expect(state.steps.train).toBeUndefined();
  });
});

describe('isRouteWriteNeeded', () => {
  const state = withCurrent(stateWith(['import']), 'train', 2);

  it('current is not needed for the step already current or a resolved step', () => {
    expect(isRouteWriteNeeded(state, { action: 'current', step: 'train' })).toBe(false);
    expect(isRouteWriteNeeded(state, { action: 'current', step: 'import' })).toBe(false);
    expect(isRouteWriteNeeded(state, { action: 'current', step: 'bots' })).toBe(true);
  });

  it('skip is needed only for the unresolved current step', () => {
    expect(isRouteWriteNeeded(state, { action: 'skip', step: 'train' })).toBe(true);
    expect(isRouteWriteNeeded(state, { action: 'skip', step: 'bots' })).toBe(false);
    expect(isRouteWriteNeeded(stateWith(['import'], ['train']), { action: 'skip', step: 'train' })).toBe(false);
  });

  it('done is needed until the stored status is done', () => {
    expect(isRouteWriteNeeded(state, { action: 'done', step: 'import' })).toBe(false);
    expect(isRouteWriteNeeded(state, { action: 'done', step: 'train' })).toBe(true);
  });
});
