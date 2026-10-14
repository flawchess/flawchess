import React, { createContext, useCallback, useContext, useState } from 'react';
import * as Sentry from '@sentry/react';
import { queryClient } from '@/lib/queryClient';
import { apiClient } from '@/api/client';
import type { GuestCreateResponse, LoginResponse, UserResponse } from '@/types/api';
import type { ImpersonateResponse } from '@/types/admin';
import { ADMIN_RETURN_TOKEN_STORAGE_KEY } from '@/lib/impersonation';

const GUEST_TOKEN_KEY = 'guest_token';
// Mirrors the /admin Route in App.tsx, which exports no route constant.
const ADMIN_ROUTE_PATH = '/admin';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithToken: (token: string) => void;
  /** Replace the stored token for the same user without clearing the query cache. */
  refreshAuthToken: (token: string) => void;
  loginAsGuest: () => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  /**
   * Start an impersonation session as a superuser.
   * Calls POST /api/admin/impersonate/{userId}, swaps the stored token, clears
   * TanStack Query cache so no admin-scoped data leaks, and updates context
   * state. Token ordering mirrors `login` — store FIRST, clear AFTER, set state
   * LAST (see login bug-fix comment). The superuser's own token is stashed under
   * ADMIN_RETURN_TOKEN_STORAGE_KEY for endImpersonation, only when no stash exists yet.
   */
  impersonate: (userId: number) => Promise<void>;
  /**
   * End an impersonation session and return to the superuser's own session on /admin.
   * Restores the stashed admin token; falls back to a full logout when none was stashed.
   */
  endImpersonation: () => void;
  logout: () => void;
  /**
   * Clear auth state without redirect — used when a guest navigates to the register page.
   * Callers MUST hard-navigate immediately afterwards (all three current callers assign
   * window.location.href to the register URL), because that reload also wipes the Umami
   * in-memory identity (Phase 229 D-07).
   */
  logoutForPromotion: () => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthState | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    // Guard against SSR/prerender environments where localStorage is unavailable
    () => (typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null),
  );
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      // FastAPI-Users JWT login uses form-encoded body with `username` field
      const params = new URLSearchParams();
      params.set('username', email);
      params.set('password', password);

      const response = await apiClient.post<LoginResponse>(
        '/auth/jwt/login',
        params,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
      );

      const { access_token } = response.data;
      localStorage.setItem('auth_token', access_token);
      localStorage.removeItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
      // Clear AFTER storing new token so any refetches triggered by the clear
      // use the new user's token, not the previous user's token.
      queryClient.clear();
      setToken(access_token);
      setUser(null); // user details fetched lazily if needed
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithToken = useCallback((externalToken: string): void => {
    localStorage.setItem('auth_token', externalToken);
    localStorage.removeItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
    // Clear AFTER storing new token so any refetches triggered by the clear
    // use the new user's token, not the previous user's token.
    queryClient.clear();
    setToken(externalToken);
    setUser(null);
  }, []);

  // Replace the stored token for the same user without clearing the query cache.
  // Bug fix: the guest-JWT refresh on /import used loginWithToken, which cleared
  // userProfile cache mid-keystroke. useUserProfile's isLoading flipped back to
  // true, the Import page swapped the inputs for a "Loading profile..." placeholder,
  // and the focused username input lost focus after the first character.
  const refreshAuthToken = useCallback((externalToken: string): void => {
    localStorage.setItem('auth_token', externalToken);
    setToken(externalToken);
  }, []);

  const impersonate = useCallback(async (userId: number): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<ImpersonateResponse>(
        `/admin/impersonate/${userId}`,
      );
      const { access_token } = response.data;
      // Stash the admin's own token (read from storage, not the stale `token` closure)
      // only after the POST succeeded and only when no stash exists, so a nested or
      // repeat call can never overwrite it with an impersonation token.
      const currentToken = localStorage.getItem('auth_token');
      if (currentToken !== null && localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY) === null) {
        localStorage.setItem(ADMIN_RETURN_TOKEN_STORAGE_KEY, currentToken);
      }
      localStorage.setItem('auth_token', access_token);
      // Clear AFTER storing new token — same ordering as login. A refetch
      // triggered by .clear() must use the new token, not the previous user's.
      queryClient.clear();
      setToken(access_token);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      await apiClient.post<UserResponse>('/auth/register', { email, password });
      // Auto-login after successful registration
      await login(email, password);
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsGuest = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Try to resume a previous guest session before creating a new one.
      // When a guest logs out, the guest token is kept in localStorage so the
      // same account (and its imported data) can be reused on next guest login.
      const savedGuestToken = typeof localStorage !== 'undefined' ? localStorage.getItem(GUEST_TOKEN_KEY) : null;
      if (savedGuestToken) {
        try {
          const refreshRes = await apiClient.post<{ access_token: string }>(
            '/auth/guest/refresh',
            null,
            { headers: { Authorization: `Bearer ${savedGuestToken}` } },
          );
          const freshToken = refreshRes.data.access_token;
          localStorage.setItem(GUEST_TOKEN_KEY, freshToken);
          loginWithToken(freshToken);
          return;
        } catch {
          // Saved token expired or invalid — fall through to create new guest
          localStorage.removeItem(GUEST_TOKEN_KEY);
        }
      }
      const response = await apiClient.post<GuestCreateResponse>('/auth/guest/create');
      const { access_token } = response.data;
      localStorage.setItem(GUEST_TOKEN_KEY, access_token);
      loginWithToken(access_token);
    } catch (error) {
      Sentry.captureException(error, { tags: { source: 'guest-login' } });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    queryClient.clear();
    // Keep guest_token so the same guest account is reused on next "Use as Guest"
    localStorage.removeItem('auth_token');
    // Every session start or end drops the admin stash so a stale admin token can never
    // be restored into another session. register, loginAsGuest, the OAuth callback and
    // RegisterForm inherit the removal through login/loginWithToken.
    localStorage.removeItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
    // Drop any stale promote intent so a later sign-in isn't wrongly routed through guest
    // promotion (see getGoogleAuthorizationUrl).
    sessionStorage.removeItem('promote_intent');
    setToken(null);
    setUser(null);
    // Load-bearing for analytics identity: this hard navigation is also the
    // Umami identity reset. Umami v3 keeps the identify() id in tracker memory
    // with no reset API, so this reload is what stops post-logout traffic from
    // carrying this user's id. Keep it (Phase 229 D-07).
    window.location.href = '/';
  };

  // Bug fix: the impersonation pill's x used to call logout(), so ending an
  // impersonation signed the superuser out and forced a fresh login. impersonate()
  // now stashes the admin's own JWT; this restores it and lands on /admin.
  // The hard navigation is load-bearing (same as logout): it resets the TanStack
  // cache and the Umami in-memory identity (Phase 229 D-07), so keep it a full page
  // load, not a client-side navigate. An expired stashed admin token needs no
  // handling: the 401 interceptor sends the admin to /login. A backend endpoint that
  // mints an admin token from the impersonation claims was deliberately NOT added:
  // a leaked 1h impersonation token could then be exchanged for a 7-day admin token,
  // defeating Phase 62 D-03.
  const endImpersonation = (): void => {
    const stashed = localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
    if (stashed === null) {
      // No stashed admin token (e.g. impersonation started before the stash existed).
      logout();
      return;
    }
    localStorage.setItem('auth_token', stashed);
    localStorage.removeItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
    // Clear AFTER storing the admin token so a refetch triggered by the clear carries it.
    queryClient.clear();
    setToken(stashed);
    setUser(null);
    window.location.href = ADMIN_ROUTE_PATH;
  };

  const logoutForPromotion = useCallback((): void => {
    queryClient.clear();
    localStorage.removeItem('auth_token');
    localStorage.removeItem(ADMIN_RETURN_TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    // Signal that the upcoming sign-up should promote the saved guest account in place.
    // This is the ONLY thing that should drive guest promotion once auth_token is cleared:
    // gating promotion on the mere presence of the persisted guest_token locked out a
    // returning registered user whose stale guest_token collided with their account
    // (2026-06-23). guest_token itself is preserved so the register flow can promote.
    sessionStorage.setItem('promote_intent', '1');
    // No redirect — caller navigates to register page.
  }, []);

  const value: AuthState = { user, token, isLoading, login, loginWithToken, refreshAuthToken, loginAsGuest, register, impersonate, endImpersonation, logout, logoutForPromotion };

  return React.createElement(AuthContext.Provider, { value }, children);
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
