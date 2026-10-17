// @vitest-environment jsdom
/**
 * useAuth.test.tsx.
 *
 * logout()'s full-page navigation is also the Umami identity reset: the tracker
 * keeps the identify() id in memory with no reset API, so removing the hard
 * navigation would leave post-logout traffic attributed to the previous user.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/api/client';
import { queryClient } from '@/lib/queryClient';
import { ADMIN_RETURN_TOKEN_STORAGE_KEY } from '@/lib/impersonation';

const originalLocation = window.location;

function wrapper({ children }: { children: React.ReactNode }): React.ReactElement {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  // Observable href assignment without jsdom attempting to leave the page.
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, href: '' },
  });
  localStorage.setItem('auth_token', 'auth-token-value');
  localStorage.setItem('guest_token', 'guest-token-value');
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
  localStorage.clear();
  sessionStorage.clear();
});

describe('useAuth logout', () => {
  it('hard-navigates to / (the analytics identity reset)', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logout();
    });
    expect(window.location.href).toBe('/');
  });

  it('removes auth_token and keeps guest_token', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logout();
    });
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('guest_token')).toBe('guest-token-value');
  });
});

describe('useAuth logoutForPromotion', () => {
  it('clears auth_token, keeps guest_token, and leaves navigation to the caller', () => {
    localStorage.setItem('guest_token', 'guest-token-value');
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logoutForPromotion();
    });
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('guest_token')).toBe('guest-token-value');
    expect(window.location.href).toBe('');
  });
});

describe('useAuth impersonation round-trip', () => {
  it('impersonate stashes the admin token and swaps auth_token', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: { access_token: 'impersonation-token' } });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.impersonate(42);
    });
    expect(localStorage.getItem('auth_token')).toBe('impersonation-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBe('auth-token-value');
  });

  it('impersonate leaves an existing stash unchanged', async () => {
    localStorage.setItem(ADMIN_RETURN_TOKEN_STORAGE_KEY, 'original-admin-token');
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: { access_token: 'impersonation-token' } });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.impersonate(42);
    });
    expect(localStorage.getItem('auth_token')).toBe('impersonation-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBe('original-admin-token');
  });

  it('impersonate with a failed request leaves auth_token and the stash untouched', async () => {
    vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('forbidden'));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.impersonate(42).catch(() => undefined);
    });
    expect(localStorage.getItem('auth_token')).toBe('auth-token-value');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('endImpersonation restores the stashed admin token and lands on /admin', () => {
    localStorage.setItem('auth_token', 'impersonation-token');
    localStorage.setItem(ADMIN_RETURN_TOKEN_STORAGE_KEY, 'admin-token');
    const clearSpy = vi.spyOn(queryClient, 'clear');
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.endImpersonation();
    });
    expect(localStorage.getItem('auth_token')).toBe('admin-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
    expect(clearSpy).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('/admin');
  });

  it('endImpersonation without a stash falls back to a full logout', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.endImpersonation();
    });
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(window.location.href).toBe('/');
  });
});

describe('useAuth admin stash hygiene', () => {
  beforeEach(() => {
    localStorage.setItem(ADMIN_RETURN_TOKEN_STORAGE_KEY, 'admin-token');
  });

  it('logout removes the stash, auth_token, and keeps guest_token', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logout();
    });
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('guest_token')).toBe('guest-token-value');
    expect(window.location.href).toBe('/');
  });

  it('logoutForPromotion removes the stash without navigating', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logoutForPromotion();
    });
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.location.href).toBe('');
  });

  it('loginWithToken removes the stash', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.loginWithToken('new-token');
    });
    expect(localStorage.getItem('auth_token')).toBe('new-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('login removes the stash', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: { access_token: 'login-token' } });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.login('a@example.com', 'pw');
    });
    expect(localStorage.getItem('auth_token')).toBe('login-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('refreshAuthToken leaves the stash in place', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.refreshAuthToken('refreshed-token');
    });
    expect(localStorage.getItem('auth_token')).toBe('refreshed-token');
    expect(localStorage.getItem(ADMIN_RETURN_TOKEN_STORAGE_KEY)).toBe('admin-token');
  });
});
