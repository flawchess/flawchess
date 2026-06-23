import { apiClient } from '@/api/client';

const GUEST_TOKEN_KEY = 'guest_token';
const PROMOTE_INTENT_KEY = 'promote_intent';

/**
 * Resolve the Google OAuth authorization URL.
 *
 * Two flows:
 *  - Plain `/auth/google/authorize`: normal sign-in / sign-up. The backend is itself
 *    guest-aware: when the request carries an *active* guest's session token (apiClient
 *    attaches the stored `auth_token` automatically), it promotes that guest in place. So a
 *    logged-in guest who clicks "Sign in with Google" is upgraded without any special
 *    frontend handling.
 *  - Explicit `/auth/google/authorize-promote` (guest_token as Bearer): used ONLY when the
 *    user deliberately chose to create an account from a guest session via the "save my
 *    data" CTA. That CTA (`logoutForPromotion`) clears `auth_token` before sending the user
 *    to the register tab, so the active-guest auto-promotion above no longer applies and the
 *    persisted `guest_token` is the only remaining link to their imported data. A one-shot
 *    `promote_intent` flag set by that CTA signals this case.
 *
 * Why gate on the intent flag instead of "a guest_token exists": `guest_token` is
 * deliberately persisted across logout so "Use as Guest" can resume the same account. A
 * returning *registered* user therefore commonly has a stale `guest_token` lingering in
 * localStorage. Keying promotion off its mere presence routed their Google login through the
 * promote flow, which collided with their existing account (UserAlreadyExists →
 * EMAIL_ALREADY_REGISTERED) and locked them out — a regression that surfaced on mobile PWAs
 * where guest mode had been used (2026-06-23). Gating on explicit intent fixes that:
 * returning users always get the plain flow and sign straight into their account.
 */
export async function getGoogleAuthorizationUrl(): Promise<string> {
  // Pass the current origin so the backend builds a redirect_uri matching the host the user
  // is on (localhost vs an HTTPS dev tunnel like Tailscale).
  const origin = encodeURIComponent(window.location.origin);
  const guestToken = localStorage.getItem(GUEST_TOKEN_KEY);
  const promoteIntent = sessionStorage.getItem(PROMOTE_INTENT_KEY) === '1';

  if (promoteIntent && guestToken) {
    // Consume the one-shot intent up front: if the user abandons the OAuth round-trip and
    // retries, falling back to the plain flow (the safe default) is preferable to stranding
    // every later login on the promote path.
    sessionStorage.removeItem(PROMOTE_INTENT_KEY);
    try {
      const res = await apiClient.get<{ authorization_url: string }>(
        `/auth/google/authorize-promote?origin=${origin}`,
        { headers: { Authorization: `Bearer ${guestToken}` } },
      );
      return res.data.authorization_url;
    } catch {
      // Saved guest token expired or invalid — drop it and fall back to plain sign-in.
      localStorage.removeItem(GUEST_TOKEN_KEY);
    }
  }

  const res = await apiClient.get<{ authorization_url: string }>(
    `/auth/google/authorize?origin=${origin}`,
  );
  return res.data.authorization_url;
}
