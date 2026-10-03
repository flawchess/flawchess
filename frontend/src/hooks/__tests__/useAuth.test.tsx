// @vitest-environment jsdom
/**
 * useAuth.test.tsx — Phase 229 D-07.
 *
 * logout()'s full-page navigation is also the Umami identity reset: the tracker
 * keeps the identify() id in memory with no reset API, so removing the hard
 * navigation would leave post-logout traffic attributed to the previous user.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/hooks/useAuth';

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
  it('clears auth_token, sets promote_intent, and leaves navigation to the caller', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => {
      result.current.logoutForPromotion();
    });
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(sessionStorage.getItem('promote_intent')).toBe('1');
    expect(window.location.href).toBe('');
  });
});
