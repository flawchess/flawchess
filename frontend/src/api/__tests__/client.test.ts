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
import { apiClient, libraryApi } from '../client';

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
});
