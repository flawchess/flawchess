/**
 * Feature-discovery route: the ordered registry and the pure arbiter.
 *
 * The route is a list of steps with the red dot on exactly one place at a time
 * (D-02). Completion is stored server-side (users.prompt_state.feature_route);
 * this module has no React and no I/O so the same answer drives every render
 * site (nav header, bottom bar, subtabs, controls).
 */

import { parseTrainRoute } from '@/lib/trainRoute';
import type {
  FeatureRouteActionRequest,
  FeatureRouteState,
  FeatureRouteStepId,
} from '@/types/users';

export type RouteNav = '/library' | '/train' | '/bots' | '/openings' | '/endgames';
export type RouteSubtabSlot = 'library-import' | 'library-stats' | 'openings-stats' | 'train-today';
export type RouteControlSlot = 'openings-played-as' | 'openings-filters' | 'train-start';
export type RouteDotSlot = `nav:${RouteNav}` | `subtab:${RouteSubtabSlot}` | `control:${RouteControlSlot}`;

export interface RouteStepDef {
  id: FeatureRouteStepId;
  /** The nav item the dot sits on while the user is outside the section (D-03). */
  nav: RouteNav;
  /** The subtab the dot sits on once the user is inside the section (D-03). */
  subtab?: { slot: RouteSubtabSlot; isOn: (pathname: string) => boolean };
  /** The control the dot sits on for "used" steps, once the section and subtab are open. */
  control?: RouteControlSlot;
  /** `visit`: done when the page opens (D-13). `used`: done when the control is used (D-13, D-21). */
  completion: 'visit' | 'used';
  visitMatch?: (pathname: string) => boolean;
  /** True when the step's target is locked until games are imported (D-23). */
  requiresGames: boolean;
}

export interface RouteCtx {
  pathname: string;
  navUnlocked: boolean;
  /** Today-inclusive active-day count (profile.active_days), the D-10 clock (D-11). */
  activeDays: number;
}

export interface RouteDotPlacement {
  step: FeatureRouteStepId;
  slot: RouteDotSlot;
}

export interface RouteWriteEnv {
  /** Current UTC day as YYYY-MM-DD. */
  today: string;
  /** Today-inclusive active-day count, the since_days a `current` stamp stores. */
  activeDays: number;
}

/**
 * D-10: a step with the dot on it is shown on its first three active days and skipped on
 * the first profile load of the fourth. Twin of FEATURE_ROUTE_SKIP_ACTIVE_DAYS in
 * app/schemas/feature_route.py; the server re-checks it in SQL, so a client cannot skip
 * early.
 */
export const FEATURE_ROUTE_SKIP_ACTIVE_DAYS = 3;

/**
 * The route. Order is the route (D-06). Adding a step is one entry here plus one
 * backend Literal member, guarded by the paired list tests; a step with a new
 * subtab or control slot also extends the slot union and adds a RouteDot at the
 * new site (D-09). A step added after launch is reached in order (D-12), and a
 * locked step pauses the route, so nothing after it shows until it unlocks and is
 * resolved (D-23).
 */
export const FEATURE_ROUTE: readonly RouteStepDef[] = [
  {
    id: 'import',
    nav: '/library',
    subtab: { slot: 'library-import', isOn: (p) => p.startsWith('/library/import') },
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/library/import'),
    requiresGames: false,
  },
  {
    id: 'train',
    nav: '/train',
    subtab: { slot: 'train-today', isOn: (p) => parseTrainRoute(p)?.tab === 'today' },
    control: 'train-start',
    completion: 'used',
    requiresGames: false,
  },
  {
    id: 'bots',
    nav: '/bots',
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/bots'),
    requiresGames: false,
  },
  {
    id: 'openings',
    nav: '/openings',
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/openings'),
    requiresGames: true,
  },
  {
    id: 'openings-played-as',
    nav: '/openings',
    control: 'openings-played-as',
    completion: 'used',
    requiresGames: true,
  },
  {
    id: 'openings-filters',
    nav: '/openings',
    control: 'openings-filters',
    completion: 'used',
    requiresGames: true,
  },
  {
    id: 'openings-stats',
    nav: '/openings',
    subtab: { slot: 'openings-stats', isOn: (p) => p.startsWith('/openings/stats') },
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/openings/stats'),
    requiresGames: true,
  },
  {
    id: 'endgames',
    nav: '/endgames',
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/endgames'),
    requiresGames: true,
  },
  {
    id: 'library-stats',
    nav: '/library',
    subtab: { slot: 'library-stats', isOn: (p) => p.startsWith('/library/stats') },
    completion: 'visit',
    visitMatch: (p) => p.startsWith('/library/stats'),
    requiresGames: true,
  },
];

/** True when `pathname` is inside the nav item's section. One copy for the nav and the arbiter. */
export function isNavActive(to: string, pathname: string): boolean {
  if (to === '/library') return pathname.startsWith('/library');
  if (to === '/train') return pathname.startsWith('/train');
  if (to === '/bots') return pathname.startsWith('/bots');
  if (to === '/openings') return pathname.startsWith('/openings');
  if (to === '/endgames') return pathname.startsWith('/endgames');
  if (to === '/analysis') return pathname.startsWith('/analysis');
  return pathname === to;
}

/** A step's own target is reachable: it needs no games, or the nav is unlocked (D-23, A-2). */
export function isStepAvailable(step: RouteStepDef, navUnlocked: boolean): boolean {
  return !step.requiresGames || navUnlocked;
}

/**
 * The candidate step: the first unresolved step in route order. When its target is
 * locked there is no candidate and later steps are NOT considered (D-23: a locked
 * step pauses the route; D-12: no queue-jumping). A games-free step placed after a
 * locked one is therefore deliberately not shown until the locked step unlocks and
 * is resolved. The `route` parameter exists so tests can build such a pair; the app
 * always uses the default.
 */
export function findCandidate(
  resolvedIds: ReadonlySet<string>,
  ctx: RouteCtx,
  route: readonly RouteStepDef[] = FEATURE_ROUTE,
): RouteStepDef | null {
  for (const step of route) {
    if (resolvedIds.has(step.id)) continue;
    return isStepAvailable(step, ctx.navUnlocked) ? step : null;
  }
  return null;
}

function placeStep(step: RouteStepDef, pathname: string): RouteDotPlacement | null {
  if (!isNavActive(step.nav, pathname)) return { step: step.id, slot: `nav:${step.nav}` };
  if (step.subtab != null && !step.subtab.isOn(pathname)) {
    return { step: step.id, slot: `subtab:${step.subtab.slot}` };
  }
  if (step.control != null) return { step: step.id, slot: `control:${step.control}` };
  // On a visit step's own page: the recorder completes it, so no dot.
  return null;
}

/** The stored current step has had the dot for the whole skip window (D-10). */
export function isCandidateExpired(state: FeatureRouteState, stepId: string, activeDays: number): boolean {
  const current = state.current;
  if (current == null || current.step !== stepId) return false;
  return activeDays - current.since_days >= FEATURE_ROUTE_SKIP_ACTIVE_DAYS;
}

/**
 * The single dot placement for the stored state, or null (no dot): a null state
 * fails closed, a locked first unresolved step pauses the route, an expired
 * candidate gives way (the recorder posts its skip and the next render moves on),
 * and a visit step whose page is open has nothing left to point at.
 */
export function resolveRouteDot(
  state: FeatureRouteState | null,
  ctx: RouteCtx,
  route: readonly RouteStepDef[] = FEATURE_ROUTE,
): RouteDotPlacement | null {
  if (state == null) return null;
  const candidate = findCandidate(new Set(Object.keys(state.steps)), ctx, route);
  if (candidate == null || isCandidateExpired(state, candidate.id, ctx.activeDays)) return null;
  return placeStep(candidate, ctx.pathname);
}

/**
 * Whether the request would change the stored state. done: until the status is done.
 * current: the step is unresolved and not already current. skip: the step is the
 * unresolved current one.
 */
export function isRouteWriteNeeded(state: FeatureRouteState, request: FeatureRouteActionRequest): boolean {
  const stored = state.steps[request.step];
  switch (request.action) {
    case 'done':
      return stored?.status !== 'done';
    case 'current':
      return stored == null && state.current?.step !== request.step;
    case 'skip':
      return stored == null && state.current?.step === request.step;
  }
}

/** Pure optimistic mirror of the server's transitions; never mutates its input. */
export function applyRouteWrite(
  state: FeatureRouteState,
  request: FeatureRouteActionRequest,
  env: RouteWriteEnv,
): FeatureRouteState {
  switch (request.action) {
    case 'current':
      return { ...state, current: { step: request.step, since_days: env.activeDays } };
    case 'skip':
      return {
        ...state,
        steps: { ...state.steps, [request.step]: { status: 'skipped', date: env.today, with_dot: true } },
      };
    case 'done':
      return {
        ...state,
        steps: {
          ...state.steps,
          [request.step]: { status: 'done', date: env.today, with_dot: state.current?.step === request.step },
        },
      };
  }
}

/** The done requests the current page warrants, in route order (D-13, D-15). */
function planDoneWrites(
  state: FeatureRouteState,
  ctx: RouteCtx,
  route: readonly RouteStepDef[],
): FeatureRouteActionRequest[] {
  const requests: FeatureRouteActionRequest[] = [];
  for (const step of route) {
    if (step.completion !== 'visit' || step.visitMatch == null) continue;
    if (!step.visitMatch(ctx.pathname)) continue;
    if (!isStepAvailable(step, ctx.navUnlocked)) continue;
    const request: FeatureRouteActionRequest = { action: 'done', step: step.id };
    if (isRouteWriteNeeded(state, request)) requests.push(request);
  }
  return requests;
}

/**
 * The skip and current requests of the clock (D-10, D-12, D-23). The candidate is the
 * first unresolved step whose target is available: an expired one is skipped, and the
 * resulting candidate is stamped current when it differs from the stored one.
 */
function planClockWrites(
  state: FeatureRouteState,
  resolved: Set<string>,
  ctx: RouteCtx,
  route: readonly RouteStepDef[],
): FeatureRouteActionRequest[] {
  const requests: FeatureRouteActionRequest[] = [];
  let candidate = findCandidate(resolved, ctx, route);
  if (candidate != null && isCandidateExpired(state, candidate.id, ctx.activeDays)) {
    requests.push({ action: 'skip', step: candidate.id });
    resolved.add(candidate.id);
    candidate = findCandidate(resolved, ctx, route);
  }
  if (candidate != null && state.current?.step !== candidate.id) {
    requests.push({ action: 'current', step: candidate.id });
  }
  return requests;
}

/**
 * The write requests the current page and clock warrant, in order: done requests for
 * visit steps whose page is open (recorded whether or not the dot pointed at them,
 * D-15, also while the route is paused on a locked step; a visit to an unavailable
 * target records nothing, A-2), then the skip of an expired candidate, then the
 * current stamp of the resulting candidate.
 *
 * D-23: the clock of a locked step does not run. A locked first unresolved step is
 * no candidate (findCandidate), so it is never stamped or skipped while locked, and
 * the stamp, with the clock, starts when its target unlocks. Deleting all games
 * removes an existing stamp server-side, so the clock restarts on unlock (A-7).
 */
export function planRouteWrites(
  state: FeatureRouteState | null,
  ctx: RouteCtx,
  route: readonly RouteStepDef[] = FEATURE_ROUTE,
): FeatureRouteActionRequest[] {
  if (state == null) return [];
  const requests = planDoneWrites(state, ctx, route);
  const resolved = new Set(Object.keys(state.steps));
  for (const request of requests) resolved.add(request.step);
  return [...requests, ...planClockWrites(state, resolved, ctx, route)];
}
