// @vitest-environment jsdom
/**
 * BlunderCheckEndScreen.test.tsx: the score screen's link to the Blunder check
 * leaderboard (Phase 251, D-24). The sound and confetti celebration is mocked so
 * nothing plays under jsdom.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router';

vi.mock('@/lib/trainScoreCelebration', () => ({ celebrateScore: vi.fn() }));

// The D-12 continue action reads the shared progress query; this suite has no
// QueryClientProvider, so the hook is mocked and each test sets the puzzles state.
const progressMock = vi.fn<() => { data: TrainProgressResponse | undefined }>(() => ({ data: undefined }));
vi.mock('@/hooks/useTrainProgress', () => ({
  useTrainProgress: () => progressMock(),
}));

// The tracker is observed at the Umami global, so this file imports no analytics module and
// carries no Umami data attribute (BlunderCheckTab.test.tsx scans this directory for both).
const track = vi.fn();
const UMAMI_ATTRIBUTE = ['data-umami', 'event'].join('-');

import { BlunderCheckEndScreen } from '@/components/train/blunder-check/BlunderCheckEndScreen';
import { LEADERBOARD_MODE_STORAGE_KEY } from '@/lib/trainLeaderboard';
import { TrainTodayActionsContext } from '@/components/train/trainTodayActions';
import {
  PHASE_251_PROGRESS_FIELDS,
  PUZZLES_MODE,
} from '@/components/train/__tests__/trainProgressFixtures';
import type { SessionResultResponse } from '@/types/blunderCheck';
import type { TrainModeState, TrainProgressResponse } from '@/types/train';

const RESULT: SessionResultResponse = {
  session_id: 7,
  session_points: 9,
  points_possible: 12,
  score_pct: 75,
  windows: [
    { position: 0, outcome: 'caught', points_scored: 4, points_possible: 4 },
    { position: 1, outcome: 'cleared', points_scored: 5, points_possible: 8 },
  ],
};

function PathProbe() {
  return <div data-testid="path-probe">{useLocation().pathname}</div>;
}

function renderEndScreen(onDone: () => void = () => undefined): void {
  render(
    <MemoryRouter initialEntries={['/train/blunder-check']}>
      <Routes>
        <Route path="*" element={<BlunderCheckEndScreen result={RESULT} onDone={onDone} />} />
      </Routes>
      <PathProbe />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.history.pushState({}, '', '/train/blunder-check');
  window.umami = { track } as unknown as typeof window.umami;
});

afterEach(() => {
  cleanup();
  track.mockReset();
  delete window.umami;
  localStorage.clear();
  progressMock.mockReset();
  progressMock.mockReturnValue({ data: undefined });
});

describe('BlunderCheckEndScreen leaderboard link', () => {
  it('shows a leaderboard link next to the sequence summary', () => {
    renderEndScreen();
    const link = screen.getByTestId('btn-blunder-check-leaderboard');
    expect(link.textContent).toBe('See the leaderboard');
  });

  it('stores the Blunder check mode and opens the leaderboard tab on click', () => {
    renderEndScreen();
    fireEvent.click(screen.getByTestId('btn-blunder-check-leaderboard'));
    expect(localStorage.getItem(LEADERBOARD_MODE_STORAGE_KEY)).toBe('blunder_check');
    expect(screen.getByTestId('path-probe').textContent).toBe('/train/leaderboard');
  });

  it('sends one nav-click with the score-screen source, as an event call not a data attribute', () => {
    renderEndScreen();
    const link = screen.getByTestId('btn-blunder-check-leaderboard');
    expect(link.getAttribute(UMAMI_ATTRIBUTE)).toBeNull();
    fireEvent.click(link);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('nav-click', {
      page: 'train',
      target: 'train',
      value: 'blunder-check-score-screen',
    });
  });

  it('leaves Done alone: it still calls onDone and does not navigate', () => {
    const onDone = vi.fn();
    renderEndScreen(onDone);
    fireEvent.click(screen.getByTestId('btn-train-done'));
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('path-probe').textContent).toBe('/train/blunder-check');
    expect(localStorage.getItem(LEADERBOARD_MODE_STORAGE_KEY)).toBeNull();
  });
});

describe('BlunderCheckEndScreen continue with Puzzles (D-12)', () => {
  const startPuzzles = vi.fn();
  const startBlunderCheck = vi.fn();

  function progressWithPuzzlesState(state: TrainModeState): { data: TrainProgressResponse } {
    return {
      data: {
        ...PHASE_251_PROGRESS_FIELDS,
        modes: { ...PHASE_251_PROGRESS_FIELDS.modes, puzzles: { ...PUZZLES_MODE, state } },
      } as TrainProgressResponse,
    };
  }

  function renderWithActions(onDone: () => void = () => undefined): void {
    render(
      <TrainTodayActionsContext.Provider value={{ startPuzzles, startBlunderCheck }}>
        <MemoryRouter initialEntries={['/train']}>
          <BlunderCheckEndScreen result={RESULT} onDone={onDone} />
        </MemoryRouter>
      </TrainTodayActionsContext.Provider>,
    );
  }

  afterEach(() => {
    startPuzzles.mockReset();
    startBlunderCheck.mockReset();
  });

  it.each<TrainModeState>(['pending', 'in_progress'])(
    'offers the continue button while puzzles are %s, and starts them on click',
    (state) => {
      progressMock.mockReturnValue(progressWithPuzzlesState(state));
      renderWithActions();
      const button = screen.getByTestId('btn-train-continue-puzzles');
      expect(button.textContent).toBe('Continue with Puzzles');
      fireEvent.click(button);
      expect(startPuzzles).toHaveBeenCalledTimes(1);
      expect(startBlunderCheck).not.toHaveBeenCalled();
    },
  );

  it.each<TrainModeState>(['done', 'off'])('shows no continue button while puzzles are %s', (state) => {
    progressMock.mockReturnValue(progressWithPuzzlesState(state));
    const onDone = vi.fn();
    renderWithActions(onDone);
    expect(screen.queryByTestId('btn-train-continue-puzzles')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-done'));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('keeps Done available next to the continue button', () => {
    progressMock.mockReturnValue(progressWithPuzzlesState('pending'));
    const onDone = vi.fn();
    renderWithActions(onDone);
    fireEvent.click(screen.getByTestId('btn-train-done'));
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
