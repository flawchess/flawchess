// @vitest-environment jsdom
/**
 * TrainScoreScreenDemo.test.tsx — the admin session feedback demo renders the
 * production score view from fixtures, never touches the backend, and only
 * celebrates on Replay. Sounds and confetti are mocked so no audio or canvas
 * runs under jsdom.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

const playSound = vi.fn();
vi.mock('@/lib/sounds', () => ({
  playSound: (...args: unknown[]) => playSound(...args),
}));
const fireWinConfetti = vi.fn();
vi.mock('@/lib/confetti', () => ({
  fireWinConfetti: (...args: unknown[]) => fireWinConfetti(...args),
  firePartialConfetti: vi.fn(),
  prefersReducedMotion: () => false,
}));

import { apiClient } from '@/api/client';
import { TrainScoreScreenDemo } from '@/components/admin/TrainScoreScreenDemo';
import {
  DEMO_NEXT_SESSION_SCENARIO_IDS,
  DEMO_RANK_SCENARIO_IDS,
  DEMO_SCORE_SCENARIO_IDS,
  DEMO_SCORE_SCENARIOS,
} from '@/lib/trainScoreDemoData';
import { countMissedPuzzles, displaySessionPercentage, scorePuzzle } from '@/lib/trainScore';

const getSpy = vi.spyOn(apiClient, 'get');
const postSpy = vi.spyOn(apiClient, 'post');

function showFinalState(): void {
  fireEvent.click(screen.getByTestId('btn-score-demo-toggle-reduced-motion'));
}

beforeEach(() => {
  getSpy.mockClear();
  postSpy.mockClear();
  playSound.mockReset();
  fireWinConfetti.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('TrainScoreScreenDemo', () => {
  it('renders every score, next-session and rank scenario without a request or a celebration', () => {
    render(<TrainScoreScreenDemo />);
    showFinalState();
    for (const [prefix, ids] of [
      ['score', DEMO_SCORE_SCENARIO_IDS],
      ['next', DEMO_NEXT_SESSION_SCENARIO_IDS],
      ['rank', DEMO_RANK_SCENARIO_IDS],
    ] as const) {
      for (const id of ids) {
        fireEvent.click(screen.getByTestId(`btn-score-demo-${prefix}-${id}`));
        expect(screen.getByTestId('train-score-screen')).not.toBeNull();
      }
    }
    expect(getSpy).not.toHaveBeenCalled();
    expect(postSpy).not.toHaveBeenCalled();
    expect(playSound).not.toHaveBeenCalled();
    expect(fireWinConfetti).not.toHaveBeenCalled();
  });

  it('shows the percentage of the picked scenario', () => {
    render(<TrainScoreScreenDemo />);
    showFinalState();
    fireEvent.click(screen.getByTestId('btn-score-demo-score-solid'));
    const { score } = DEMO_SCORE_SCENARIOS.solid;
    expect(screen.getByTestId('train-score-percentage').textContent).toBe(
      `${displaySessionPercentage(score)}%`,
    );
  });

  it('the next-session scenario changes the bubble and the line together', () => {
    render(<TrainScoreScreenDemo />);
    expect(screen.getByTestId('train-score-bubble-returns').textContent).toContain('See you tomorrow.');
    expect(screen.getByTestId('train-score-next-session').textContent).toBe('Next session: tomorrow');
    fireEvent.click(screen.getByTestId('btn-score-demo-next-in-a-week'));
    expect(screen.getByTestId('train-score-bubble-returns').textContent).toMatch(/See you on [A-Z][a-z]{2} \d+\./);
    expect(screen.getByTestId('train-score-next-session').textContent).toMatch(/^Next session: [A-Z][a-z]{2} \d+$/);
  });

  it('Replay fires the band sound and confetti', () => {
    render(<TrainScoreScreenDemo />);
    fireEvent.click(screen.getByTestId('btn-score-demo-replay'));
    expect(playSound).toHaveBeenCalledWith('game-win');
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
  });
});

describe('demo score fixtures', () => {
  it('each scenario score is the sum of its puzzles, and only Perfect has no misses', () => {
    for (const id of DEMO_SCORE_SCENARIO_IDS) {
      const { score, outcomes } = DEMO_SCORE_SCENARIOS[id];
      const sum = outcomes.reduce((total, o) => total + scorePuzzle(o.correct_guess, o.move_quality), 0);
      expect(score.total).toBe(sum);
      expect(countMissedPuzzles(outcomes) === 0).toBe(id === 'perfect');
    }
  });
});
