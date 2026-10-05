// @vitest-environment jsdom
/**
 * libraryApi client-layer tests.
 *
 * Regression coverage for the Games-subtab tag filter: getGames previously
 * omitted `tag` from its request, so tag filters were silently dropped before
 * ever reaching the backend (the Flaws path forwarded it correctly, the Games
 * path did not). These tests assert getGames forwards `tag` to /library/games
 * with the same omit-when-empty behaviour as getFlaws.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as Sentry from '@sentry/react';
import { apiClient, libraryApi, postReviewKeepalive } from '../client';

vi.mock('@sentry/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@sentry/react')>();
  return { ...actual, captureException: vi.fn() };
});

const EMPTY_GAMES_RESPONSE = {
  data: { games: [], matched_count: 0, offset: 0, limit: 20 },
};

function lastGetParams(spy: ReturnType<typeof vi.spyOn>): Record<string, unknown> {
  const calls = spy.mock.calls;
  const lastCall = calls[calls.length - 1];
  // calls[i] = [url, config]; config.params is the serialized query object
  return (lastCall?.[1] as { params: Record<string, unknown> }).params;
}

describe('libraryApi.getGames', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('forwards the tag filter to /library/games (regression: tags were dropped)', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
    await libraryApi.getGames({ tag: ['reversed', 'low-clock'] });

    expect(getSpy).toHaveBeenCalledWith('/library/games', expect.anything());
    expect(lastGetParams(getSpy)).toMatchObject({ tag: ['reversed', 'low-clock'] });
  });

  it('forwards both severity and tag together', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
    await libraryApi.getGames({ severity: ['blunder'], tag: ['miss'] });

    expect(lastGetParams(getSpy)).toMatchObject({ severity: ['blunder'], tag: ['miss'] });
  });

  it('omits tag from the request when the tag array is empty', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
    await libraryApi.getGames({ tag: [] });

    expect(lastGetParams(getSpy)).not.toHaveProperty('tag');
  });

  it('omits tag from the request when tag is undefined', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
    await libraryApi.getGames({ severity: ['mistake'] });

    expect(lastGetParams(getSpy)).not.toHaveProperty('tag');
  });

  // FILT-01 (Phase 175): has_gem/has_great serialize into the query string only
  // when true, same conditional-inclusion pattern as tactic_orientation above.
  describe('has_gem / has_great (FILT-01, Phase 175)', () => {
    it('forwards has_gem: true when has_gem is true', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
      await libraryApi.getGames({ has_gem: true });

      expect(lastGetParams(getSpy)).toMatchObject({ has_gem: true });
    });

    it('forwards has_great: true when has_great is true', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
      await libraryApi.getGames({ has_great: true });

      expect(lastGetParams(getSpy)).toMatchObject({ has_great: true });
    });

    it('forwards both has_gem and has_great together', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
      await libraryApi.getGames({ has_gem: true, has_great: true });

      expect(lastGetParams(getSpy)).toMatchObject({ has_gem: true, has_great: true });
    });

    it('omits has_gem from the request when has_gem is false', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
      await libraryApi.getGames({ has_gem: false });

      expect(lastGetParams(getSpy)).not.toHaveProperty('has_gem');
    });

    it('omits has_gem/has_great from the request when both are undefined', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(EMPTY_GAMES_RESPONSE);
      await libraryApi.getGames({ severity: ['mistake'] });

      expect(lastGetParams(getSpy)).not.toHaveProperty('has_gem');
      expect(lastGetParams(getSpy)).not.toHaveProperty('has_great');
    });
  });
});

describe('postReviewKeepalive', () => {
  const BODY = { v: 1, exit: 'pagehide', review_ms: 3000, review_hidden_ms: 0 } as const;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn(async () => ({ status: 204 }));
    vi.stubGlobal('fetch', fetchMock);
    localStorage.setItem('auth_token', 'tok');
    vi.mocked(Sentry.captureException).mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('posts a keepalive request with the Bearer token to the same-origin review route', () => {
    postReviewKeepalive(7, 2, BODY);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/train/sessions/7/solves/2/review', {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer tok' },
      body: JSON.stringify(BODY),
    });
  });

  it('does not call fetch without a stored token', () => {
    localStorage.clear();
    postReviewKeepalive(7, 2, BODY);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('swallows a rejected fetch without throwing or reporting', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('network'));
    expect(() => postReviewKeepalive(7, 2, BODY)).not.toThrow();
    await Promise.resolve();
    await Promise.resolve();
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it.each([401, 404])('does not report an expected %s response', async (status) => {
    fetchMock.mockResolvedValueOnce({ status });
    postReviewKeepalive(7, 2, BODY);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('reports a 500 once with a constant message and the status in context', async () => {
    fetchMock.mockResolvedValueOnce({ status: 500 });
    postReviewKeepalive(7, 2, BODY);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    const [error, hint] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect((error as Error).message).toBe('Train review keepalive flush failed');
    expect(hint).toMatchObject({
      tags: { source: 'train-review-keepalive' },
      contexts: { train_review: { status: 500 } },
    });
  });
});
