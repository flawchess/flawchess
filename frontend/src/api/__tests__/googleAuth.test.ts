// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';

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
const PROMOTE_URL = 'https://accounts.google.com/o/oauth2/v2/auth?promote=1';
const PLAIN_URL = 'https://accounts.google.com/o/oauth2/v2/auth?plain=1';

function httpError(status: number): AxiosError {
  const config = { headers: new AxiosHeaders() };
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, {
    status,
    statusText: '',
    headers: {},
    config,
    data: {},
  });
}

function networkError(): AxiosError {
  return new AxiosError('Network Error', AxiosError.ERR_NETWORK, { headers: new AxiosHeaders() });
}

function calledPaths(): string[] {
  return mockedGet.mock.calls.map(([path]) => path);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockedGet.mockReset();
});

describe('getGoogleAuthorizationUrl', () => {
  it('uses the promote endpoint with the guest Bearer header whenever a guest_token is saved', async () => {
    // No intent flag needed (quick 261016-fwd): a guest who logged out first or retried an
    // abandoned Google screen must still be promoted, not duplicated.
    localStorage.setItem(GUEST_TOKEN_KEY, 'guest-jwt-abc');
    mockedGet.mockResolvedValueOnce({ data: { authorization_url: PROMOTE_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PROMOTE_URL);
    expect(mockedGet).toHaveBeenCalledTimes(1);
    const [path, config] = mockedGet.mock.calls[0]!;
    expect(path).toContain('/auth/google/authorize-promote');
    expect(config).toMatchObject({ headers: { Authorization: 'Bearer guest-jwt-abc' } });
    // Guest token preserved on success (cleared later by the OAuth callback page), so a
    // retry after an abandoned Google screen promotes again.
    expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBe('guest-jwt-abc');
  });

  it.each([401, 403])(
    'drops a rejected guest_token (%i) and falls back to plain sign-in',
    async (status) => {
      localStorage.setItem(GUEST_TOKEN_KEY, 'stale-jwt');
      mockedGet
        .mockRejectedValueOnce(httpError(status))
        .mockResolvedValueOnce({ data: { authorization_url: PLAIN_URL } });

      const url = await getGoogleAuthorizationUrl();

      expect(url).toBe(PLAIN_URL);
      const paths = calledPaths();
      expect(paths).toHaveLength(2);
      expect(paths[0]).toContain('authorize-promote');
      expect(paths[1]).toContain('/auth/google/authorize');
      expect(paths[1]).not.toContain('authorize-promote');
      expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBeNull();
    },
  );

  it.each([
    ['a 500', () => httpError(500)],
    ['a network error', networkError],
  ])('rethrows %s without falling back or dropping the guest_token', async (_label, makeError) => {
    // Falling back to plain sign-in on a transient error is what orphaned guest accounts.
    localStorage.setItem(GUEST_TOKEN_KEY, 'guest-jwt-abc');
    mockedGet.mockRejectedValueOnce(makeError());

    await expect(getGoogleAuthorizationUrl()).rejects.toBeInstanceOf(AxiosError);

    expect(calledPaths()).toHaveLength(1);
    expect(calledPaths()[0]).toContain('authorize-promote');
    expect(localStorage.getItem(GUEST_TOKEN_KEY)).toBe('guest-jwt-abc');
  });

  it('uses the plain endpoint when no guest_token exists', async () => {
    mockedGet.mockResolvedValueOnce({ data: { authorization_url: PLAIN_URL } });

    const url = await getGoogleAuthorizationUrl();

    expect(url).toBe(PLAIN_URL);
    const paths = calledPaths();
    expect(paths).toHaveLength(1);
    expect(paths[0]).toContain('/auth/google/authorize');
    expect(paths[0]).not.toContain('authorize-promote');
  });
});
