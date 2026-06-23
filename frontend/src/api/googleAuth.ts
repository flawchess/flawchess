import { apiClient } from '@/api/client';

const GUEST_TOKEN_KEY = 'guest_token';

/**
 * Resolve the Google OAuth authorization URL, preferring in-place guest promotion.
 *
 * Shared by both the Login and Register Google buttons so the two can never drift
 * apart again — divergence between them (the Login button had no promote branch) is
 * exactly what orphaned a guest account in prod (users 198→199, 2026-06-23).
 *
 * If a `guest_token` is saved, route through `/auth/google/authorize-promote` (with the
 * token as a Bearer header) so the guest account and its imported games are upgraded in
 * place rather than replaced by a brand-new account. Falls back to the plain
 * `/auth/google/authorize` flow when no guest session exists or the saved token is
 * rejected. The backend's plain authorize endpoint is itself guest-aware, so this is
 * defense in depth, not the only safety net.
 */
export async function getGoogleAuthorizationUrl(): Promise<string> {
  // Pass the current origin so the backend builds a redirect_uri matching the host
  // the user is on (localhost vs an HTTPS dev tunnel like Tailscale).
  const origin = encodeURIComponent(window.location.origin);
  const guestToken = localStorage.getItem(GUEST_TOKEN_KEY);

  if (guestToken) {
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
