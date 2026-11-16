import { useEffect, useRef } from 'react';
import { useRouteCtx } from '@/hooks/useFeatureRoute';
import { useRecordFeatureRoute } from '@/hooks/useRecordFeatureRoute';
import { useUserProfile } from '@/hooks/useUserProfile';
import { planRouteWrites } from '@/lib/featureRoute';

/**
 * Minimum time between two sends of the same request (action + step). Nothing in the
 * normal flow sends a request twice, so this only spaces out retries and re-stamps.
 */
const ROUTE_WRITE_RESEND_COOLDOWN_MS = 10_000;

/**
 * Records visit-completion steps (D-13, D-15) and the Import step once the profile has
 * games (D-14 overruled 2026-11-16), and drives the clock (D-10): posts
 * every request planRouteWrites returns (done, skip, current). Mounted once in
 * ProtectedLayout.
 *
 * Loop protection: each request (action + step) is sent at most once per
 * ROUTE_WRITE_RESEND_COOLDOWN_MS, whatever the server answers and however the cached
 * state changes in between. Nothing resets that. A request still planned after the
 * cooldown is sent again the next time the effect runs (navigation or a profile
 * change), which is what retries a failed write and what re-stamps a step whose
 * stamp the server removed (D-23, delete all games) once its target unlocks again
 * in the same session. There is no timer: without such a trigger nothing is resent.
 *
 * No trackFeature: tracking from an effect on a value is forbidden (frontend/CLAUDE.md).
 */
export function FeatureRouteRecorder(): null {
  const { data: profile } = useUserProfile();
  const ctx = useRouteCtx();
  const record = useRecordFeatureRoute();
  const sentAtRef = useRef<Map<string, number>>(new Map());
  const state = profile?.feature_route ?? null;
  const impersonated = profile?.impersonation != null;
  const { pathname, navUnlocked, activeDays, hasGames } = ctx;

  useEffect(() => {
    if (state == null || impersonated) return;
    // Bug fix (WR-03): the sent keys of current and skip used to be forgotten whenever
    // the stored stamp changed. The recorder's own optimistic patch changes the stamp,
    // so the key was dropped right after its send, and a server answer without the
    // stamp sent the same request again, unbounded and at network speed. No state
    // change clears a key any more; the cooldown alone decides when a resend is allowed.
    const now = Date.now();
    for (const request of planRouteWrites(state, { pathname, navUnlocked, activeDays, hasGames })) {
      const key = `${request.action}:${request.step}`;
      // Bug fix (WR-01): a sent key used to block its request for the whole session, so
      // a done POST that failed (network blip, 5xx) was never sent again and the dot
      // stayed on a page the user had opened (against D-15). The key now expires, so the
      // write is retried on a later visit. It is not retried at once: the failure leaves
      // the optimistic patch in place, and the cooldown covers a refetch that undoes it.
      const sentAt = sentAtRef.current.get(key);
      if (sentAt != null && now - sentAt < ROUTE_WRITE_RESEND_COOLDOWN_MS) continue;
      sentAtRef.current.set(key, now);
      record(request);
    }
  }, [state, pathname, navUnlocked, activeDays, hasGames, impersonated, record]);

  return null;
}
