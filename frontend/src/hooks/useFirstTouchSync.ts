import { useEffect, useRef } from 'react';
import * as Sentry from '@sentry/react';
import { apiClient } from '@/api/client';
import { markFirstTouchSent, readUnsentFirstTouch } from '@/lib/firstTouch';

/**
 * Submit this browser's stored first touch once a token exists (growth report
 * item 16). Fires on every token change until one submit succeeds; the backend
 * ignores it for an account that already existed or was already attributed, so
 * a returning user signing in simply consumes the stash.
 */
export function useFirstTouchSync(token: string | null): void {
  const inFlightRef = useRef(false);

  useEffect(() => {
    if (token === null || inFlightRef.current) return;
    const touch = readUnsentFirstTouch();
    if (touch === null) return;
    inFlightRef.current = true;
    apiClient
      .post('/users/me/first-touch', touch)
      .then(() => markFirstTouchSent())
      .catch((error: unknown) => {
        Sentry.captureException(error, { tags: { source: 'first-touch' } });
      })
      .finally(() => {
        inFlightRef.current = false;
      });
  }, [token]);
}
