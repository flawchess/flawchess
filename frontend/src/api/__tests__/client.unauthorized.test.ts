// @vitest-environment jsdom
/**
 * 401 interceptor (quick 260926-9bg): only a request that carried a token is
 * an expired session. A signed-out visitor's tokenless 401 must not
 * hard-redirect to /login (it would override the home-page landing).
 */
import { AxiosError, AxiosHeaders } from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { peekReturnTo } from '@/lib/returnTo';

const fakeLocation = { pathname: '/train', search: '', href: 'http://localhost/train' };

beforeEach(() => {
  vi.stubGlobal('location', { ...fakeLocation });
  apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    throw new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
      status: 401,
      statusText: 'Unauthorized',
      data: {},
      headers: {},
      config: { ...config, headers: new AxiosHeaders() },
    });
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe('401 interceptor', () => {
  it('redirects to /login and stashes the page when the request carried a token', async () => {
    localStorage.setItem('auth_token', 'expired');
    await expect(apiClient.get('/users/me/profile')).rejects.toBeInstanceOf(AxiosError);
    expect(window.location.href).toBe('/login');
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(peekReturnTo()).toBe('/train');
  });

  it('leaves a tokenless 401 alone', async () => {
    await expect(apiClient.get('/users/me/profile')).rejects.toBeInstanceOf(AxiosError);
    expect(window.location.href).toBe(fakeLocation.href);
    expect(peekReturnTo()).toBeNull();
  });
});
