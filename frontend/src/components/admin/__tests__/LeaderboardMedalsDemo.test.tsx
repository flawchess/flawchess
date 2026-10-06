// @vitest-environment jsdom
/**
 * LeaderboardMedalsDemo.test.tsx — the admin medals demo renders the production
 * board view and claim dialog from fixtures and never touches the backend.
 * Sounds and confetti are mocked so no audio or canvas runs under jsdom.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';

const unlockAudio = vi.fn();
const playSound = vi.fn();
vi.mock('@/lib/sounds', () => ({
  unlockAudio: (...args: unknown[]) => unlockAudio(...args),
  playSound: (...args: unknown[]) => playSound(...args),
}));
const fireWinConfetti = vi.fn();
vi.mock('@/lib/confetti', () => ({
  fireWinConfetti: (...args: unknown[]) => fireWinConfetti(...args),
}));

import { apiClient } from '@/api/client';
import { LeaderboardMedalsDemo } from '@/components/admin/LeaderboardMedalsDemo';
import { DEMO_BOARD_SCENARIOS, DEMO_CELEBRATE_SCENARIOS } from '@/lib/leaderboardMedalsDemoData';

const getSpy = vi.spyOn(apiClient, 'get');
const postSpy = vi.spyOn(apiClient, 'post');

beforeEach(() => {
  getSpy.mockClear();
  postSpy.mockClear();
});

afterEach(() => {
  cleanup();
  unlockAudio.mockReset();
  playSound.mockReset();
  fireWinConfetti.mockReset();
});

function clickBoard(id: string): void {
  fireEvent.click(screen.getByTestId(`btn-medals-demo-board-${id}`));
}

function clickCelebrate(id: string): void {
  fireEvent.click(screen.getByTestId(`btn-medals-demo-celebrate-${id}`));
}

describe('LeaderboardMedalsDemo tracer', () => {
  it('shows the production podium from a board scenario', () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('podium-tie');
    const podium = screen.getByTestId('train-leaderboard-podium');
    expect(within(podium).getAllByTestId(/^train-leaderboard-podium-entry-/)).toHaveLength(3);
  });

  it("highlights the viewer on last week's podium without a finish line", () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('podium-viewer');
    expect(screen.getByTestId('train-leaderboard-podium-entry-1').getAttribute('data-viewer')).toBe('true');
    expect(screen.queryByTestId('train-leaderboard-last-week-finish')).toBeNull();
  });

  it('opens the production claim dialog from a celebrate button and Claim closes it', () => {
    render(<LeaderboardMedalsDemo />);
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
    clickCelebrate('gold-points');
    const dialog = screen.getByTestId('train-medal-dialog');
    expect(dialog.textContent).toContain('You won a medal!');
    expect(dialog.textContent).toContain('Gold, Points');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });

  it('never calls the backend', () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('podium-tie');
    clickCelebrate('gold-points');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(getSpy).not.toHaveBeenCalled();
    expect(postSpy).not.toHaveBeenCalled();
  });
});

describe('LeaderboardMedalsDemo scenarios', () => {
  it('has one button per board and per celebrate scenario', () => {
    render(<LeaderboardMedalsDemo />);
    expect(screen.getAllByTestId(/^btn-medals-demo-board-/)).toHaveLength(
      Object.keys(DEMO_BOARD_SCENARIOS).length,
    );
    expect(screen.getAllByTestId(/^btn-medals-demo-celebrate-/)).toHaveLength(
      Object.keys(DEMO_CELEBRATE_SCENARIOS).length,
    );
  });

  it('shows the second hint line when the viewer finished #12 last week (D-03)', () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('finished-12');
    expect(screen.getByTestId('train-leaderboard-pass-target')).toBeTruthy();
    expect(screen.getByTestId('train-leaderboard-last-week-finish').textContent).toBe('You finished #12 last week');
  });

  it('renders the full tally with its aria-label for all three medal types', () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('tallies-all-three');
    expect(screen.getByLabelText('12 gold, 10 silver, 11 bronze Points medals')).toBeTruthy();
  });

  it('lists a deleted user on the podium as plain text', () => {
    render(<LeaderboardMedalsDemo />);
    clickBoard('podium-deleted-user');
    expect(screen.getByTestId('train-leaderboard-podium-entry-0').textContent).toContain('Deleted user');
  });

  it('opens a three-week dialog with entries in fixture order', () => {
    render(<LeaderboardMedalsDemo />);
    clickCelebrate('three-weeks');
    expect(screen.getByRole('dialog').textContent).toContain('You won 3 medals!');
    const entries = DEMO_CELEBRATE_SCENARIOS['three-weeks'].medals;
    const labels = entries.map((_, index) => screen.getByTestId(`train-medal-dialog-entry-${index}`).textContent ?? '');
    expect(labels[0]).toContain('Gold, Points');
    expect(labels[1]).toContain('Silver, Accuracy');
    expect(labels[2]).toContain('Bronze, Points');
  });

  it('labels a shared gold in the dialog', () => {
    render(<LeaderboardMedalsDemo />);
    clickCelebrate('shared-gold');
    expect(screen.getByTestId('train-medal-dialog-entry-0').textContent).toContain('Gold, Points (shared)');
  });
});

describe('LeaderboardMedalsDemo simulated toggles', () => {
  it('Claim plays the chime and confetti with both toggles off', () => {
    render(<LeaderboardMedalsDemo />);
    clickCelebrate('gold-points');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(unlockAudio).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledTimes(1);
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
  });

  it('muted: Claim unlocks audio but does not play the chime', () => {
    render(<LeaderboardMedalsDemo />);
    fireEvent.click(screen.getByTestId('btn-medals-demo-toggle-muted'));
    expect(screen.getByTestId('btn-medals-demo-toggle-muted').getAttribute('aria-pressed')).toBe('true');
    clickCelebrate('gold-points');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(unlockAudio).toHaveBeenCalledTimes(1);
    expect(playSound).not.toHaveBeenCalled();
  });

  it('reduced motion: no confetti and no medal pop class', () => {
    render(<LeaderboardMedalsDemo />);
    fireEvent.click(screen.getByTestId('btn-medals-demo-toggle-reduced-motion'));
    clickCelebrate('gold-points');
    expect(screen.getByTestId('train-medal-dialog-entry-0').innerHTML).not.toContain('animate-medal-pop');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(fireWinConfetti).not.toHaveBeenCalled();
  });

  it('the narrow toggle puts max-w-[375px] on the card frame', () => {
    render(<LeaderboardMedalsDemo />);
    const frame = screen.getByTestId('medals-demo-card-frame');
    expect(frame.className).not.toContain('max-w-[375px]');
    fireEvent.click(screen.getByTestId('btn-medals-demo-toggle-narrow'));
    expect(frame.className).toContain('max-w-[375px]');
  });

  it('still makes no backend call across scenarios and toggles', () => {
    render(<LeaderboardMedalsDemo />);
    for (const id of Object.keys(DEMO_BOARD_SCENARIOS)) clickBoard(id);
    fireEvent.click(screen.getByTestId('btn-medals-demo-toggle-narrow'));
    clickCelebrate('gold-points-bronze-accuracy');
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(getSpy).not.toHaveBeenCalled();
    expect(postSpy).not.toHaveBeenCalled();
  });
});
