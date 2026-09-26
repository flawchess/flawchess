import { useEffect, useRef } from 'react';
import { clearReturnTo, stashReturnTo } from '@/lib/returnTo';

/**
 * ProtectedLayout's side of the post-auth return path (quick 260926-9bg).
 *
 * - Arrived signed out (e.g. a shared /train link): remember `path` so
 *   HomePage can send the user back after guest start, login, or signup.
 * - Authenticated: the intent is fulfilled, drop it.
 *
 * Bug fix: the first version also stashed when the token went away while the
 * layout was mounted. `logout()` clears the token (re-rendering this layout
 * with no token) before its hard redirect to `/`, so logging out from /train
 * re-stashed /train and every later login landed there. Only a mount that
 * never had a token counts as "arrived signed out".
 */
export function useReturnToTracking(token: string | null, path: string): void {
  const hadTokenRef = useRef(token !== null);

  useEffect(() => {
    if (token !== null) {
      hadTokenRef.current = true;
      clearReturnTo();
      return;
    }
    if (!hadTokenRef.current) stashReturnTo(path);
  }, [token, path]);
}
