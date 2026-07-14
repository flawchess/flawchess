// @vitest-environment jsdom
/**
 * useLibrary.ts pure-function tests (Quick 260714-rj5, Task 2).
 *
 * Covers `libraryGamePollInterval` — the poll-interval decision that drives
 * useLibraryGame's opt-in `live` mode: poll while a game-mode card is
 * unanalyzed, stop once it's analyzed, stop once the stall backstop trips,
 * stop when there's no data yet.
 */

import { describe, it, expect } from 'vitest';
import {
  libraryGamePollInterval,
  LIBRARY_GAME_POLL_TIMEOUT_MS,
} from '../useLibrary';
import { LIBRARY_GAMES_POLL_INTERVAL_MS } from '@/hooks/useEvalCoverage';
import type { GameFlawCard } from '@/types/library';

function makeCard(overrides: Partial<GameFlawCard> = {}): GameFlawCard {
  return {
    game_id: 1,
    user_result: 'win',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    platform: 'flawchess',
    platform_url: null,
    white_username: null,
    black_username: null,
    white_rating: null,
    black_rating: null,
    opening_name: null,
    opening_eco: null,
    user_color: 'white',
    ply_count: 4,
    termination: null,
    time_control_str: null,
    result_fen: null,
    severity_counts: null,
    chips: [],
    analysis_state: 'no_engine_analysis',
    eval_series: null,
    flaw_markers: null,
    phase_transitions: null,
    moves: ['e4', 'e5'],
    active_eval_status: 'pending',
    ...overrides,
  };
}

describe('libraryGamePollInterval', () => {
  it('returns LIBRARY_GAMES_POLL_INTERVAL_MS while unanalyzed and under the backstop', () => {
    const card = makeCard({ analysis_state: 'no_engine_analysis' });
    expect(libraryGamePollInterval(card, 5_000)).toBe(LIBRARY_GAMES_POLL_INTERVAL_MS);
  });

  it('returns false once the card is analyzed', () => {
    const card = makeCard({ analysis_state: 'analyzed' });
    expect(libraryGamePollInterval(card, 5_000)).toBe(false);
  });

  it('returns false once elapsedMs reaches the stall backstop', () => {
    const card = makeCard({ analysis_state: 'no_engine_analysis' });
    expect(libraryGamePollInterval(card, LIBRARY_GAME_POLL_TIMEOUT_MS)).toBe(false);
    expect(libraryGamePollInterval(card, LIBRARY_GAME_POLL_TIMEOUT_MS + 1)).toBe(false);
  });

  it('returns false when there is no data yet', () => {
    expect(libraryGamePollInterval(undefined, 0)).toBe(false);
  });
});
