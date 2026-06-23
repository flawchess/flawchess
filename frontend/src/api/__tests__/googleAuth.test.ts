// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient at module level. Preserve other exports via importActual.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  };
});

import { apiClient } from '@/api/client';
import { getGoogleAuthorizationUrl } from '@/api/googleAuth';

const mockedGet = vi.mocked(apiClient.get);
const GUEST_TOKEN_KEY = 'guest_token';
const PROMOTE_INTENT_KEY = 'promote_intent';
const PROMOTE_URL = 'https://accounts.google.com/o/oauth2/v2/auth?promote=1';
const PLAIN_URL = 'https://accounts.google.com/o/oauth2/v2/auth?plain=1';

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockedGet.mockReset();
});

describe('getGoogleAuthorizationUrl', () => {
  it('uses the promote endpoint with the guest Bearer header when promote intent is set', async () => {
    localStorage.setItem(GUEST_TOKEN_KEY, 'guest-jwt-abc');
    sessionStorage.setItem(PROMOTE_INTENT_KEY, '1');
    mockedGet.mockResolvedValueOnce({ data: { authorization_url: PROMOTE_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PROMOTE_URL);
    expect(mockedGet).toHaveBeenCalledTimes(1);
    const [path, config] = mockedGet.mock.calls[0]!;
    expect(path).toContain('/auth/google/authorize-promote');
    expect(config).toMatchObject({ headers: { Authorization: 'Bearer guest-jwt-abc' } });
    // Guest token preserved on success (cleared later by the OAuth callback page).
    expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBe('guest-jwt-abc');
    // One-shot intent is consumed so a retry can't strand on the promote path.
    expect(sessionStorage.getItem(PROMOTE_INTENT_KEY)).toBeNull();
  });

  it('uses the plain endpoint when a guest_token exists but there is no promote intent', async () => {
    // Regression guard (2026-06-23): a returning registered user with a stale, persisted
    // guest_token must NOT be routed through guest promotion — that collided with their
    // existing account and locked them out. No intent => plain sign-in.
    localStorage.setItem(GUEST_TOKEN_KEY, 'stale-guest-jwt');
    mockedGet.mockResolvedValueOnce({ data: { authorization_url: PLAIN_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PLAIN_URL);
    expect(mockedGet).toHaveBeenCalledTimes(1);
    expect(mockedGet.mock.calls[0]![0]).toContain('/auth/google/authorize');
    expect(mockedGet.mock.calls[0]![0]).not.toContain('authorize-promote');
    // The stale token is left untouched so "Use as Guest" can still resume that session.
    expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBe('stale-guest-jwt');
  });

  it('uses the plain endpoint when no guest_token exists', async () => {
    sessionStorage.setItem(PROMOTE_INTENT_KEY, '1'); // intent without a token still falls back
    mockedGet.mockResolvedValueOnce({ data: { authorization_url: PLAIN_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PLAIN_URL);
    expect(mockedGet).toHaveBeenCalledTimes(1);
    expect(mockedGet.mock.calls[0]![0]).toContain('/auth/google/authorize');
    expect(mockedGet.mock.calls[0]![0]).not.toContain('authorize-promote');
  });

  it('falls back to the plain endpoint and clears a rejected guest_token', async () => {
    localStorage.setItem(GUEST_TOKEN_KEY, 'stale-jwt');
    sessionStorage.setItem(PROMOTE_INTENT_KEY, '1');
    mockedGet
      .mockRejectedValueOnce(new Error('401 expired guest token'))
      .mockResolvedValueOnce({ data: { authorization_url: PLAIN_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PLAIN_URL);
    expect(mockedGet).toHaveBeenCalledTimes(2);
    expect(mockedGet.mock.calls[0]![0]).toContain('authorize-promote');
    expect(mockedGet.mock.calls[1]![0]).toContain('/auth/google/authorize');
    expect(mockedGet.mock.calls[1]![0]).not.toContain('authorize-promote');
    // Stale token removed so it isn't retried on the next attempt.
    expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBeNull();
  });
});
