// @vitest-environment jsdom
/**
 * BlunderCheckTimerRing: the drill's countdown ring (Phase 251 UAT). Green, amber and red in
 * equal thirds of the move's time (4 s each at 12 s), the track alone while no clock runs,
 * and one shake from the low-time sound on.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { BlunderCheckTimerRing } from '@/components/train/blunder-check/BlunderCheckTimerRing';
import { BLUNDER_CHECK_TIMER_DANGER, BLUNDER_CHECK_TIMER_SAFE, BLUNDER_CHECK_TIMER_WARN } from '@/lib/theme';

const TOTAL_MS = 12_000;

afterEach(() => {
  cleanup();
});

function renderRing(remainingMs: number, props: { active?: boolean; shake?: boolean } = {}): void {
  render(
    <BlunderCheckTimerRing
      remainingMs={remainingMs}
      totalMs={TOTAL_MS}
      active={props.active ?? true}
      shake={props.shake ?? false}
    />,
  );
}

function numberColor(): string {
  return screen.getByTestId('blunder-check-timer').style.color;
}

describe('BlunderCheckTimerRing', () => {
  it.each([
    [12_000, '12', BLUNDER_CHECK_TIMER_SAFE],
    [8_001, '9', BLUNDER_CHECK_TIMER_SAFE],
    [8_000, '8', BLUNDER_CHECK_TIMER_WARN],
    [4_001, '5', BLUNDER_CHECK_TIMER_WARN],
    [4_000, '4', BLUNDER_CHECK_TIMER_DANGER],
    [100, '1', BLUNDER_CHECK_TIMER_DANGER],
  ])('at %i ms shows %s in the third it falls in', (remainingMs, label, color) => {
    renderRing(remainingMs);
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe(label);
    // Compare through a probe element: jsdom normalizes the inline color string.
    const probe = document.createElement('span');
    probe.style.color = color;
    expect(numberColor()).toBe(probe.style.color);
    expect(numberColor()).not.toBe('');
  });

  it('shows only the track, no number, while no clock runs', () => {
    renderRing(0, { active: false });
    expect(screen.queryByTestId('blunder-check-timer')).toBeNull();
    expect(screen.getByTestId('blunder-check-timer-ring').getAttribute('data-active')).toBe('false');
  });

  it('shakes from the low-time sound on, never before', () => {
    renderRing(5_000);
    expect(screen.getByTestId('blunder-check-timer-ring').className).not.toContain('timer-shake');
    cleanup();
    renderRing(3_000, { shake: true });
    expect(screen.getByTestId('blunder-check-timer-ring').className).toContain('animate-blunder-check-timer-shake');
  });
});
