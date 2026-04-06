import React, { createContext, useCallback, useContext, useState } from 'react';
import * as Sentry from '@sentry/react';
import { queryClient } from '@/lib/queryClient';
import { apiClient } from '@/api/client';
import type { GuestCreateResponse, LoginResponse, UserResponse } from '@/types/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithToken: (token: string) => void;
  loginAsGuest: () => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
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
      const response = await apiClient.post<GuestCreateResponse>('/auth/guest/create');
      const { access_token } = response.data;
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
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    window.location.href = '/';
  };

  const value: AuthState = { user, token, isLoading, login, loginWithToken, loginAsGuest, register, logout };

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
