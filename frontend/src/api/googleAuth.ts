import axios from 'axios';
import { apiClient } from '@/api/client';

const GUEST_TOKEN_KEY = 'guest_token';

const HTTP_UNAUTHORIZED = 401;
const HTTP_FORBIDDEN = 403;
/** authorize-promote's 403 detail when the token's account was already promoted. */
const NOT_A_GUEST_DETAIL = 'Not a guest user';

/**
 * True when the saved guest token can no longer start a promotion: 401 = expired, invalid
 * or revoked (promotion revokes it), or our own 403 saying the account is no longer a guest.
 * Any other 403 (e.g. a proxy/WAF block) must not count: dropping a valid guest_token there
 * would orphan the guest's games again.
 */
function isGuestTokenRejected(error: unknown): boolean {
  if (!axios.isAxiosError(error) || error.response === undefined) return false;
  const { status, data } = error.response;
  if (status === HTTP_UNAUTHORIZED) return true;
  return status === HTTP_FORBIDDEN && data?.detail === NOT_A_GUEST_DETAIL;
}

/**
 * Resolve the Google OAuth authorization URL.
 *
 * Whenever a guest_token is saved (it outlives logout so "Use as Guest" can resume the
 * same account), the request goes to `/auth/google/authorize-promote` with that token. The
 * backend then decides: a Google identity that already has an account is signed into it
 * (the guest is left alone), and a new identity promotes the guest in place, keeping its
 * imported games. When a guest is still logged in, apiClient's interceptor replaces the
 * header with the stored auth_token, which is that same guest.
 *
 * Bug fix (quick 261016-fwd): promotion used to need a one-shot `promote_intent` flag set
 * by the "save my data" CTAs, consumed before the Google redirect. A guest who logged out
 * first, or backed out of the Google screen and retried, lost the flag, so the plain flow
 * created a duplicate account and orphaned the guest's games (~20 accounts in prod). The
 * flag only existed because the promote callback used to lock a returning registered user
 * with a stale guest_token out with EMAIL_ALREADY_REGISTERED (2026-06-23). The backend
 * now signs that user into their account instead, so the flag is gone.
 *
 * Only a rejected guest token (401, or 403 "Not a guest user") falls back to plain sign-in. A network error or 5xx
 * is re-thrown so the caller asks the user to retry: falling back on a transient error is
 * exactly what orphaned guest accounts.
 */
export async function getGoogleAuthorizationUrl(): Promise<string> {
  // Pass the current origin so the backend builds a redirect_uri matching the host the user
  // is on (localhost vs an HTTPS dev tunnel like Tailscale).
  const origin = encodeURIComponent(window.location.origin);
  const guestToken = localStorage.getItem(GUEST_TOKEN_KEY);

  if (guestToken) {
    try {
      const res = await apiClient.get<{ authorization_url: string }>(
        `/auth/google/authorize-promote?origin=${origin}`,
        { headers: { Authorization: `Bearer ${guestToken}` } },
      );
      return res.data.authorization_url;
    } catch (error) {
      if (!isGuestTokenRejected(error)) throw error;
      // Saved guest token is dead or already promoted: drop it and sign in normally.
      localStorage.removeItem(GUEST_TOKEN_KEY);
    }
  }

  const res = await apiClient.get<{ authorization_url: string }>(
    `/auth/google/authorize?origin=${origin}`,
  );
  return res.data.authorization_url;
}
