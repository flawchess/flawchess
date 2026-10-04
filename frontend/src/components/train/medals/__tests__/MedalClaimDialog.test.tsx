// @vitest-environment jsdom
/**
 * MedalClaimDialog.test.tsx — Phase 231 claim-and-celebrate dialog (D-11..D-13).
 * Sounds and confetti are mocked (same shape as TrainScoreScreen.test.tsx) so
 * the Claim-path order and the mute / reduced-motion gates can be asserted.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
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

import { MedalClaimDialog } from '@/components/train/medals/MedalClaimDialog';
import type { MedalClaimDialogProps } from '@/components/train/medals/MedalClaimDialog';
import type { UnclaimedMedal } from '@/types/train';

const THREE_WEEKS: UnclaimedMedal[] = [
  { week_start: '2026-10-05', board: 'points', medal: 'gold', value: 412, shared: false },
  { week_start: '2026-10-05', board: 'accuracy', medal: 'silver', value: 87, shared: true },
  { week_start: '2026-09-28', board: 'points', medal: 'bronze', value: 55, shared: false },
];
const THREE_KEYS = [
  { week_start: '2026-10-05', board: 'points' },
  { week_start: '2026-10-05', board: 'accuracy' },
  { week_start: '2026-09-28', board: 'points' },
];

afterEach(() => {
  cleanup();
  unlockAudio.mockReset();
  playSound.mockReset();
  fireWinConfetti.mockReset();
});

function renderDialog(overrides: Partial<MedalClaimDialogProps> = {}) {
  const onClaim = vi.fn();
  const onDismiss = vi.fn();
  const props: MedalClaimDialogProps = {
    open: true,
    medals: THREE_WEEKS,
    muted: false,
    reducedMotion: false,
    onClaim,
    onDismiss,
    ...overrides,
  };
  const view = render(<MedalClaimDialog {...props} />);
  return { onClaim, onDismiss, props, rerender: view.rerender };
}

describe('MedalClaimDialog content', () => {
  it('lists every medal in the given order with label, week and value', () => {
    renderDialog();
    expect(screen.getByTestId('train-medal-dialog')).not.toBeNull();
    expect(screen.getByText('You won 3 medals!')).not.toBeNull();
    const list = screen.getByTestId('train-medal-dialog-list');
    expect(list.children).toHaveLength(3);

    const first = screen.getByTestId('train-medal-dialog-entry-0');
    expect(within(first).getByText('Gold, Points')).not.toBeNull();
    expect(within(first).getByText('Week of Oct 5 · 412 pts')).not.toBeNull();
    const second = screen.getByTestId('train-medal-dialog-entry-1');
    expect(within(second).getByText('Silver, Accuracy (shared)')).not.toBeNull();
    expect(within(second).getByText('Week of Oct 5 · 87%')).not.toBeNull();
    const third = screen.getByTestId('train-medal-dialog-entry-2');
    expect(within(third).getByText('Bronze, Points')).not.toBeNull();
    expect(within(third).getByText('Week of Sep 28 · 55 pts')).not.toBeNull();
  });

  it('uses the singular title for one medal', () => {
    renderDialog({ medals: [THREE_WEEKS[0]!] });
    expect(screen.getByText('You won a medal!')).not.toBeNull();
  });

  it('renders nothing when closed', () => {
    renderDialog({ open: false });
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });
});

describe('MedalClaimDialog Claim path (D-12, D-13)', () => {
  it('unlocks audio before the chime, plays it once for three medals, fires confetti, reports the keys', () => {
    const { onClaim, onDismiss } = renderDialog();
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));

    expect(unlockAudio).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledWith('game-win');
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
    const unlockOrder = unlockAudio.mock.invocationCallOrder[0]!;
    const soundOrder = playSound.mock.invocationCallOrder[0]!;
    const confettiOrder = fireWinConfetti.mock.invocationCallOrder[0]!;
    const claimOrder = onClaim.mock.invocationCallOrder[0]!;
    expect(unlockOrder).toBeLessThan(soundOrder);
    expect(soundOrder).toBeLessThan(confettiOrder);
    expect(confettiOrder).toBeLessThan(claimOrder);
    expect(onClaim).toHaveBeenCalledTimes(1);
    expect(onClaim).toHaveBeenCalledWith(THREE_KEYS);
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it('a second Claim tap before the dialog closes replays nothing', () => {
    const { onClaim } = renderDialog();
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(playSound).toHaveBeenCalledTimes(1);
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
    expect(onClaim).toHaveBeenCalledTimes(1);
  });

  it('muted: still unlocks audio but plays no sound', () => {
    const { onClaim } = renderDialog({ muted: true });
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(unlockAudio).toHaveBeenCalledTimes(1);
    expect(playSound).not.toHaveBeenCalled();
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
    expect(onClaim).toHaveBeenCalledTimes(1);
  });

  it('reduced motion: no confetti, sound still plays', () => {
    const { onClaim } = renderDialog({ reducedMotion: true });
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    expect(fireWinConfetti).not.toHaveBeenCalled();
    expect(playSound).toHaveBeenCalledWith('game-win');
    expect(onClaim).toHaveBeenCalledTimes(1);
  });

  it('a close reported after Claim fires no second callback', () => {
    const { onClaim, onDismiss, props, rerender } = renderDialog();
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    // The container closes the dialog after Claim; Escape while still open is
    // the worst case for a double callback.
    fireEvent.keyDown(screen.getByTestId('train-medal-dialog'), { key: 'Escape' });
    rerender(<MedalClaimDialog {...props} open={false} />);
    expect(onClaim).toHaveBeenCalledTimes(1);
    expect(onDismiss).not.toHaveBeenCalled();
  });
});

describe('MedalClaimDialog dismiss path (D-13)', () => {
  it('close button: one onDismiss with the keys, no sound, no confetti, no unlock', () => {
    const { onClaim, onDismiss } = renderDialog();
    fireEvent.click(screen.getByTestId('btn-train-medal-dialog-close'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledWith(THREE_KEYS);
    expect(onClaim).not.toHaveBeenCalled();
    expect(unlockAudio).not.toHaveBeenCalled();
    expect(playSound).not.toHaveBeenCalled();
    expect(fireWinConfetti).not.toHaveBeenCalled();
  });

  it('Escape: one onDismiss with the keys, no effects', () => {
    const { onClaim, onDismiss } = renderDialog();
    fireEvent.keyDown(screen.getByTestId('train-medal-dialog'), { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledWith(THREE_KEYS);
    expect(onClaim).not.toHaveBeenCalled();
    expect(unlockAudio).not.toHaveBeenCalled();
    expect(playSound).not.toHaveBeenCalled();
    expect(fireWinConfetti).not.toHaveBeenCalled();
  });

  it('reopening starts a fresh cycle that can settle again', () => {
    const { onDismiss, props, rerender } = renderDialog();
    fireEvent.click(screen.getByTestId('btn-train-medal-dialog-close'));
    rerender(<MedalClaimDialog {...props} open={false} />);
    rerender(<MedalClaimDialog {...props} open={true} />);
    fireEvent.click(screen.getByTestId('btn-train-medal-dialog-close'));
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });
});

describe('MedalClaimDialog medal pop (D-11)', () => {
  it('each icon wrapper carries animate-medal-pop with a staggered delay', () => {
    renderDialog();
    const delays = [0, 1, 2].map((index) => {
      const entry = screen.getByTestId(`train-medal-dialog-entry-${index}`);
      const popped = entry.querySelector<HTMLElement>('.animate-medal-pop');
      expect(popped).not.toBeNull();
      return popped!.style.animationDelay;
    });
    expect(delays).toEqual(['0ms', '120ms', '240ms']);
  });

  it('reduced motion: no entry has the class', () => {
    renderDialog({ reducedMotion: true });
    expect(document.querySelector('.animate-medal-pop')).toBeNull();
  });
});
