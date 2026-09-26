/**
 * Post-auth return path (quick 260926-9bg).
 *
 * A logged-out visitor who opens a protected route (e.g. a newsletter link to
 * /train) is sent to the home page, and an expired session is sent to /login.
 * Every post-auth flow (guest start, email login/register, Google OAuth
 * callback) then lands on `/`, whose authenticated branch used to send
 * zero-game accounts to /library/import, so the original intent was lost.
 *
 * The intended path is stashed in sessionStorage (tab-scoped, survives the
 * Google OAuth round-trip) and read by `HomePage`. It is cleared once an
 * authenticated protected page renders, i.e. once the intent is fulfilled.
 */

export const RETURN_TO_STORAGE_KEY = 'return_to';

/** Destinations that would loop back into the auth flow instead of fulfilling it. */
const NON_RETURN_PATHS: ReadonlySet<string> = new Set(['/', '/login']);
const AUTH_PATH_PREFIX = '/auth/';

/**
 * Returns `raw` if it is a safe same-origin app path, else null. Rejects
 * protocol-relative (`//host`) and backslash (`/\host`) forms, which browsers
 * resolve to another origin, so the stash can never become an open redirect.
 */
export function sanitizeReturnTo(raw: string | null | undefined): string | null {
  if (!raw || !raw.startsWith('/')) return null;
  if (raw.startsWith('//') || raw.startsWith('/\\')) return null;
  const pathname = raw.split(/[?#]/, 1)[0] ?? raw;
  if (NON_RETURN_PATHS.has(pathname) || pathname.startsWith(AUTH_PATH_PREFIX)) return null;
  return raw;
}

export function stashReturnTo(path: string): void {
  const safe = sanitizeReturnTo(path);
  if (safe === null) return;
  try {
    sessionStorage.setItem(RETURN_TO_STORAGE_KEY, safe);
  } catch {
    // Storage blocked (private mode, site-data settings): fall back to the default landing.
  }
}

/** Non-destructive read, so a StrictMode double render sees the same value. */
export function peekReturnTo(): string | null {
  try {
    return sanitizeReturnTo(sessionStorage.getItem(RETURN_TO_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function clearReturnTo(): void {
  try {
    sessionStorage.removeItem(RETURN_TO_STORAGE_KEY);
  } catch {
    // Storage blocked: nothing was stashed either.
  }
}
