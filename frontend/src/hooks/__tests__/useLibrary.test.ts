// @vitest-environment jsdom
/**
 * useLibrary.ts pure-function tests.
 *
 * Covers `libraryGamePollInterval` — the poll-interval decision that drives
 * useLibraryGame's opt-in `live` mode: poll while a game-mode card is
 * unanalyzed, stop once it's analyzed, stop once the stall backstop trips,
 * stop when there's no data yet.
 */

import { afterEach, describe, it, expect, vi } from 'vitest';
import { createElement, type ReactNode } from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { libraryApi } from '@/api/client';
import {
  libraryGamePollInterval,
  LIBRARY_GAME_POLL_TIMEOUT_MS,
  buildLibraryParams,
  useTacticLines,
} from '../useLibrary';
import { LIBRARY_GAMES_POLL_INTERVAL_MS } from '@/hooks/useEvalCoverage';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { GameFlawCard, TacticLinesResponse } from '@/types/library';

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

  // Regression: the backstop must outlast a realistic tier-1 turnaround. A job
  // waits on a worker leasing it, so several minutes is normal — a backstop
  // shorter than that strands the analysis board on "Analyzing…" forever, since
  // this poll is the board's only refresh driver. Pins the DURATION, not just
  // the symbol: the other backstop test passes for any value of the constant.
  it('still polls a game that has been analyzing for several minutes', () => {
    const card = makeCard({ analysis_state: 'no_engine_analysis' });
    const threeMinutes = 3 * 60 * 1000;
    expect(libraryGamePollInterval(card, threeMinutes)).toBe(LIBRARY_GAMES_POLL_INTERVAL_MS);
  });
});

describe('buildLibraryParams — has_gem / has_great', () => {
  it('includes has_gem: true when hasGem is true', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], [], true, false);
    expect(params.has_gem).toBe(true);
  });

  it('omits has_gem when hasGem is false (mirrors rated conditional-inclusion)', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], [], false, false);
    expect(params.has_gem).toBeUndefined();
  });

  it('includes has_great: true when hasGreat is true', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], [], false, true);
    expect(params.has_great).toBe(true);
  });

  it('omits has_great when hasGreat is false', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], [], true, false);
    expect(params.has_great).toBeUndefined();
  });

  it('omits both when hasGem/hasGreat are omitted entirely (default params)', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], []);
    expect(params.has_gem).toBeUndefined();
    expect(params.has_great).toBeUndefined();
  });

  it('includes both when hasGem and hasGreat are both true', () => {
    const params = buildLibraryParams(DEFAULT_FILTERS, [], [], true, true);
    expect(params.has_gem).toBe(true);
    expect(params.has_great).toBe(true);
  });
});

describe('useTacticLines', () => {
  const FIXTURE: TacticLinesResponse = {
    missed_moves: ['Nf3', 'Nc6'],
    missed_depth: 2,
    missed_tactic_ply_index: 1,
    missed_motif: 'fork',
    missed_eval_cp: null,
    missed_eval_mate: null,
    allowed_moves: null,
    allowed_depth: null,
    allowed_tactic_ply_index: null,
    allowed_motif: null,
    allowed_eval_cp: null,
    allowed_eval_mate: null,
    position_fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    flaw_move_san: 'Qh5',
    best_move_uci: null,
    flaw_ply: 2,
    flaw_severity: 'blunder',
  };

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderTacticLines(enabled: boolean) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children);
    return renderHook(() => useTacticLines(1, 2, enabled), { wrapper });
  }

  it('maps an axios 404 to null data, not an error', async () => {
    const notFound = Object.assign(new Error('404'), {
      isAxiosError: true,
      response: { status: 404, data: { detail: 'Flaw not found' } },
    });
    vi.spyOn(libraryApi, 'getTacticLines').mockRejectedValue(notFound);
    const { result } = renderTacticLines(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('still surfaces a 500 as an error', async () => {
    const serverError = Object.assign(new Error('500'), {
      isAxiosError: true,
      response: { status: 500, data: { detail: 'boom' } },
    });
    vi.spyOn(libraryApi, 'getTacticLines').mockRejectedValue(serverError);
    const { result } = renderTacticLines(true);
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('returns the response on success', async () => {
    vi.spyOn(libraryApi, 'getTacticLines').mockResolvedValue(FIXTURE);
    const { result } = renderTacticLines(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(FIXTURE);
  });

  it('does not fetch when disabled', () => {
    const spy = vi.spyOn(libraryApi, 'getTacticLines').mockResolvedValue(FIXTURE);
    renderTacticLines(false);
    expect(spy).not.toHaveBeenCalled();
  });
});
