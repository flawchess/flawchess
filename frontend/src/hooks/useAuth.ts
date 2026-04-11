import React, { createContext, useCallback, useContext, useState } from 'react';
import * as Sentry from '@sentry/react';
import { queryClient } from '@/lib/queryClient';
import { apiClient } from '@/api/client';
import type { GuestCreateResponse, LoginResponse, UserResponse } from '@/types/api';

const GUEST_TOKEN_KEY = 'guest_token';

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
  logout: () => void;
  /** Clear auth state without redirect — used when a guest navigates to the register page. */
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
    setToken(null);
    setUser(null);
    window.location.href = '/';
  };

  const logoutForPromotion = useCallback((): void => {
    queryClient.clear();
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    // No redirect — caller navigates to register page.
    // guest_token is preserved so RegisterForm can promote the guest account.
  }, []);

  const value: AuthState = { user, token, isLoading, login, loginWithToken, refreshAuthToken, loginAsGuest, register, logout, logoutForPromotion };

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
