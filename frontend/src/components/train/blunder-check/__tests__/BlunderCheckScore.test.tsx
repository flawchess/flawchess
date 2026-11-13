// @vitest-environment jsdom
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BlunderCheckScore } from '@/components/train/blunder-check/BlunderCheckScore';
import { POINTS_FLIGHT_LAND_MS } from '@/lib/blunderCheckDrill';
import type { DrillProgress } from '@/lib/blunderCheckDrill';

// With motion: the tab tests cover the reduced-motion path.
vi.mock('@/lib/confetti', async () => {
  const actual = await vi.importActual<typeof import('@/lib/confetti')>('@/lib/confetti');
  return { ...actual, prefersReducedMotion: () => false };
});

const playSound = vi.hoisted(() => vi.fn());
vi.mock('@/lib/sounds', async () => {
  const actual = await vi.importActual<typeof import('@/lib/sounds')>('@/lib/sounds');
  return { ...actual, playSound };
});

type Score = Pick<DrillProgress, 'banked' | 'pot' | 'potEvent' | 'windowOver'>;

/** Longer than the banked total's count-up (its start delay plus one step per point). */
const BANK_COUNT_UP_BUDGET_MS = 2_000;
const COUNT_STEP_MS = 100;

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function potAmount(): string | null {
  return screen.getByTestId('blunder-check-pot-amount').textContent;
}

function total(): string | null {
  return screen.getByTestId('blunder-check-points').textContent;
}

describe('BlunderCheckScore', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    playSound.mockClear();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('adds a gain to the pot only when its badge lands, with the coin sound', async () => {
    const open: Score = { banked: 4, pot: 1, potEvent: null, windowOver: false };
    const { rerender } = render(<BlunderCheckScore progress={open} />);
    expect(potAmount()).toBe('+1');

    rerender(
      <BlunderCheckScore progress={{ banked: 4, pot: 2, potEvent: { kind: 'gain', amount: 1 }, windowOver: false }} />,
    );
    // The server's number is in, but the badge is still flying over from the board.
    expect(potAmount()).toBe('+1');
    await advance(POINTS_FLIGHT_LAND_MS - 1);
    expect(potAmount()).toBe('+1');
    expect(playSound).not.toHaveBeenCalled();

    await advance(1);
    expect(potAmount()).toBe('+2');
    expect(screen.getByTestId('blunder-check-pot-amount').className).toContain(
      'animate-blunder-check-pot-gain',
    );
    expect(playSound).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledWith('pot-gain');
    expect(total()).toBe('4 pts');

    // The same pot size after a bust is a new gain: it flies again.
    rerender(<BlunderCheckScore progress={{ banked: 4, pot: 0, potEvent: null, windowOver: false }} />);
    rerender(
      <BlunderCheckScore progress={{ banked: 4, pot: 2, potEvent: { kind: 'gain', amount: 2 }, windowOver: false }} />,
    );
    expect(potAmount()).toBe('+0');
    await advance(POINTS_FLIGHT_LAND_MS);
    expect(potAmount()).toBe('+2');
  });

  it('a lost pot shows what was lost in red and leaves the total alone', () => {
    render(
      <BlunderCheckScore progress={{ banked: 4, pot: 0, potEvent: { kind: 'bust', amount: 3 }, windowOver: false }} />,
    );
    const pot = screen.getByTestId('blunder-check-pot');
    expect(pot.getAttribute('data-pot-state')).toBe('bust');
    expect(pot.textContent).toBe('-3');
    expect(pot.className).toContain('animate-blunder-check-pot-bust');
    expect(total()).toBe('4 pts');
    expect(playSound).not.toHaveBeenCalled();
  });

  it('a banked pot slides over and the total counts up to the server number', async () => {
    render(
      <BlunderCheckScore
        progress={{ banked: 9, pot: null, potEvent: { kind: 'bank', amount: 5 }, windowOver: false }}
      />,
    );
    const pot = screen.getByTestId('blunder-check-pot');
    expect(pot.getAttribute('data-pot-state')).toBe('bank');
    expect(pot.textContent).toBe('+5');
    expect(total()).toBe('4 pts');

    // One render per counted point: each step's timer is set by the render before it.
    for (let elapsed = 0; elapsed < BANK_COUNT_UP_BUDGET_MS; elapsed += COUNT_STEP_MS) {
      await advance(COUNT_STEP_MS);
    }
    expect(total()).toBe('9 pts');
  });

  it('an empty pot is muted while the window runs and a red +0 once it is over', () => {
    const { rerender } = render(
      <BlunderCheckScore progress={{ banked: 4, pot: 0, potEvent: null, windowOver: false }} />,
    );
    expect(screen.getByTestId('blunder-check-pot').getAttribute('data-pot-state')).toBe('empty');

    rerender(
      <BlunderCheckScore progress={{ banked: 4, pot: 0, potEvent: null, windowOver: true }} />,
    );
    const pot = screen.getByTestId('blunder-check-pot');
    expect(pot.getAttribute('data-pot-state')).toBe('lost');
    expect(pot.textContent).toBe('+0');
  });

  it('keeps the pot place empty when no window is open', () => {
    render(<BlunderCheckScore progress={{ banked: 9, pot: null, potEvent: null, windowOver: false }} />);
    expect(screen.queryByTestId('blunder-check-pot')).toBeNull();
    expect(total()).toBe('9 pts');
  });
});
