// @vitest-environment jsdom
/**
 * TrainModeLauncherRow.test.tsx: one launcher row in the four D-09 states for both modes.
 * Start / Resume call the page's actions from `TrainTodayActionsContext`; plan 251-10 extends
 * this file for the level step.
 */
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TrainModeLauncherRow } from '@/components/train/TrainModeLauncherRow';
import type { TrainLauncherMode } from '@/components/train/TrainModeLauncherRow';
import { TrainTodayActionsContext } from '@/components/train/trainTodayActions';
import {
  BLUNDER_CHECK_MODE,
  PUZZLES_MODE,
} from '@/components/train/__tests__/trainProgressFixtures';
import type { TrainModeProgress } from '@/types/train';

const startPuzzles = vi.fn();
const startBlunderCheck = vi.fn();

afterEach(() => {
  cleanup();
  startPuzzles.mockReset();
  startBlunderCheck.mockReset();
});

function Wrapper({ children }: { children: ReactNode }): ReactNode {
  return (
    <TrainTodayActionsContext.Provider value={{ startPuzzles, startBlunderCheck }}>
      {children}
    </TrainTodayActionsContext.Provider>
  );
}

function renderRow(
  mode: TrainLauncherMode,
  progress: Partial<TrainModeProgress>,
  extra: Partial<Parameters<typeof TrainModeLauncherRow>[0]> = {},
): void {
  const base = mode === 'puzzles' ? PUZZLES_MODE : BLUNDER_CHECK_MODE;
  render(
    <TrainModeLauncherRow mode={mode} progress={{ ...base, ...progress }} pointsToday={0} {...extra} />,
    { wrapper: Wrapper },
  );
}

const MODES: ReadonlyArray<{
  mode: TrainLauncherMode;
  slug: string;
  startId: string;
  resumeId: string;
}> = [
  {
    mode: 'puzzles',
    slug: 'puzzles',
    startId: 'btn-train-start',
    resumeId: 'btn-train-resume',
  },
  {
    mode: 'blunder_check',
    slug: 'blunder-check',
    startId: 'btn-train-blunder-check-start',
    resumeId: 'btn-train-blunder-check-start',
  },
];

describe.each(MODES)('TrainModeLauncherRow: $mode', ({ mode, slug, startId, resumeId }) => {
  const rowId = `train-launcher-row-${slug}`;

  it('pending: badge with the count, no "N left" line, and a Start button that starts the mode', () => {
    renderRow(mode, { state: 'pending', remaining: 5, pending: 5 });

    expect(screen.getByTestId(rowId).dataset.state).toBe('pending');
    expect(screen.getByTestId(`train-launcher-badge-${slug}`).textContent).toBe('5');
    // Phase 251 UAT: the red badge carries the count, so there is no second line.
    expect(screen.queryByTestId(`train-launcher-status-${slug}`)).toBeNull();
    const button = screen.getByTestId(startId);
    expect(button.textContent).toBe('Start');
    fireEvent.click(button);
    expect(mode === 'puzzles' ? startPuzzles : startBlunderCheck).toHaveBeenCalledTimes(1);
    expect(mode === 'puzzles' ? startBlunderCheck : startPuzzles).not.toHaveBeenCalled();
  });

  it('pending with nothing counted toward the badge (off a scheduled day): no badge, Start stays', () => {
    renderRow(mode, { state: 'pending', remaining: 5, pending: 0 });

    expect(screen.queryByTestId(`train-launcher-badge-${slug}`)).toBeNull();
    expect(screen.getByTestId(startId)).not.toBeNull();
  });

  it('in progress: badge with the remaining count and a Resume button', () => {
    renderRow(mode, { state: 'in_progress', remaining: 3, pending: 0 });

    expect(screen.getByTestId(`train-launcher-badge-${slug}`).textContent).toBe('3');
    expect(screen.queryByTestId(`train-launcher-status-${slug}`)).toBeNull();
    expect(screen.getByTestId(resumeId).textContent).toBe('Resume');
  });

  it('done: checkmark and "Done today, N points", no badge and no button', () => {
    renderRow(mode, { state: 'done', remaining: 0, pending: 0 }, { pointsToday: 17 });

    expect(screen.getByTestId(rowId).dataset.state).toBe('done');
    expect(screen.getByTestId(`train-launcher-check-${slug}`)).not.toBeNull();
    expect(screen.getByTestId(`train-launcher-done-${slug}`).textContent).toBe('Done today, 17 points');
    expect(screen.queryByTestId(`train-launcher-badge-${slug}`)).toBeNull();
    expect(screen.queryByTestId(startId)).toBeNull();
    expect(screen.queryByTestId(resumeId)).toBeNull();
  });

  it('off: muted row saying Off with no Start, and no Turn on button without a handler', () => {
    renderRow(mode, { state: 'off', size: 0, remaining: 0, pending: 0 });

    expect(screen.getByTestId(rowId).dataset.state).toBe('off');
    expect(screen.getByTestId(`train-launcher-status-${slug}`).textContent).toBe('Off');
    expect(screen.queryByTestId(`train-launcher-badge-${slug}`)).toBeNull();
    expect(screen.queryByTestId(startId)).toBeNull();
    expect(screen.queryByTestId(`btn-train-launcher-turn-on-${slug}`)).toBeNull();
  });

  it('off: the Turn on button calls the handler with the mode', () => {
    const onTurnOn = vi.fn();
    renderRow(mode, { state: 'off', size: 0, remaining: 0, pending: 0 }, { onTurnOn });

    fireEvent.click(screen.getByTestId(`btn-train-launcher-turn-on-${slug}`));
    expect(onTurnOn).toHaveBeenCalledWith(mode);
  });

  it('disabled: Start is disabled', () => {
    renderRow(mode, { state: 'pending', remaining: 2, pending: 2 }, { disabled: true });

    expect(screen.getByTestId(startId).hasAttribute('disabled')).toBe(true);
  });

  it('nothing left in a pending row says so (no badge to carry it)', () => {
    renderRow(mode, { state: 'pending', remaining: 0, pending: 0 });

    expect(screen.getByTestId(`train-launcher-status-${slug}`).textContent).toBe('Nothing waiting');
  });
});

describe('TrainModeLauncherRow: puzzles route dot', () => {
  it('puts the route dot inside the puzzles Start button when asked', () => {
    renderRow('puzzles', { state: 'pending', remaining: 4, pending: 4 }, { showRouteDot: true });

    expect(screen.getByTestId('btn-train-start').querySelector('[data-testid="train-start-notification-dot"]')).not.toBeNull();
  });

  it('renders no dot by default, and never on the Blunder Check row', () => {
    renderRow('puzzles', { state: 'pending', remaining: 4, pending: 4 });
    expect(screen.queryByTestId('train-start-notification-dot')).toBeNull();
    cleanup();

    renderRow('blunder_check', { state: 'pending', remaining: 4, pending: 4 }, { showRouteDot: true });
    expect(screen.queryByTestId('train-start-notification-dot')).toBeNull();
  });
});

describe('Blunder Check pitch (Phase 251 UAT)', () => {
  it('is no longer on the row: it moved into the dismissable launch notice', () => {
    renderRow('blunder_check', { state: 'pending', first_session_done: false });
    expect(screen.queryByTestId('train-launcher-pitch-blunder-check')).toBeNull();
  });
});
