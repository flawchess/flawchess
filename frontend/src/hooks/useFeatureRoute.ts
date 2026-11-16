import { useLocation } from 'react-router';
import { hasImportedGames, useUserProfile } from '@/hooks/useUserProfile';
import { useReadiness } from '@/hooks/useReadiness';
import {
  resolveRouteDot,
  type RouteCtx,
  type RouteDotPlacement,
  type RouteDotSlot,
} from '@/lib/featureRoute';

/**
 * The one nav-unlock rule: games exist AND import phase 1 (Tier 1) is complete.
 * tier1 alone is true for a fresh zero-game account (no job in flight) and games
 * alone appear mid-import before phase 1 finishes; both gates avoid unlocking early.
 * Shared by the nav surfaces and the route arbiter.
 */
export function useNavUnlocked(): boolean {
  const { data: profile } = useUserProfile();
  const { tier1 } = useReadiness();
  return hasImportedGames(profile) && tier1;
}

/** Inputs of the pure arbiter. Touches no QueryClient (App.test renders the nav without one). */
export function useRouteCtx(): RouteCtx {
  const { pathname } = useLocation();
  const navUnlocked = useNavUnlocked();
  const { data: profile } = useUserProfile();
  // The profile's today-inclusive count drives the D-10 clock (D-11): no extra request.
  const activeDays = profile?.active_days ?? 0;
  return { pathname, navUnlocked, activeDays };
}

/** The current dot placement, or null. A profile without feature_route gives no dot. */
export function useRouteDotPlacement(): RouteDotPlacement | null {
  const { data: profile } = useUserProfile();
  const ctx = useRouteCtx();
  return resolveRouteDot(profile?.feature_route ?? null, ctx);
}

/** True when the route dot belongs on `slot`. */
export function useRouteDot(slot: RouteDotSlot): boolean {
  return useRouteDotPlacement()?.slot === slot;
}
