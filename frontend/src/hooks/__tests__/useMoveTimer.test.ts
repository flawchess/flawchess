// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { MOVE_TIMER_TICK_MS, useMoveTimer } from '@/hooks/useMoveTimer';

const DURATION_MS = 10_000;

interface Props {
  durationMs: number;
  running: boolean;
  promptKey: string;
}

const START: Props = { durationMs: DURATION_MS, running: true, promptKey: 'a' };

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function setup(initial: Props = START) {
  const onTimeout = vi.fn();
  const hook = renderHook((props: Props) => useMoveTimer({ ...props, onTimeout }), {
    initialProps: initial,
  });
  return { onTimeout, ...hook };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useMoveTimer', () => {
  it('counts down while running and does not time out early', async () => {
    const { result, onTimeout } = setup();
    expect(result.current.remainingMs).toBe(DURATION_MS);

    await advance(5_000);
    expect(result.current.remainingMs).toBeGreaterThan(DURATION_MS - 5_000 - MOVE_TIMER_TICK_MS);
    expect(result.current.remainingMs).toBeLessThanOrEqual(DURATION_MS - 5_000);
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it('calls onTimeout exactly once when the countdown reaches zero', async () => {
    const { result, onTimeout } = setup();

    await advance(DURATION_MS);
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(result.current.remainingMs).toBe(0);

    await advance(DURATION_MS);
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });

  it('a new promptKey restarts the countdown', async () => {
    const { result, rerender, onTimeout } = setup();
    await advance(6_000);

    rerender({ ...START, promptKey: 'b' });
    expect(result.current.remainingMs).toBe(DURATION_MS);

    await advance(6_000);
    expect(onTimeout).not.toHaveBeenCalled();
    await advance(4_000);
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });

  it('running false freezes the countdown', async () => {
    const { result, rerender, onTimeout } = setup();
    await advance(3_000);
    rerender({ ...START, running: false });
    const frozen = result.current.remainingMs;

    await advance(DURATION_MS);
    expect(result.current.remainingMs).toBe(frozen);
    expect(onTimeout).not.toHaveBeenCalled();
  });

  it('shows the full duration until it starts running', async () => {
    const { result, rerender } = setup({ ...START, running: false });
    await advance(5_000);
    expect(result.current.remainingMs).toBe(DURATION_MS);

    rerender({ ...START, running: true });
    await advance(2_000);
    expect(result.current.remainingMs).toBeLessThan(DURATION_MS);
  });

  it('a zero duration times out right away', async () => {
    const { onTimeout } = setup({ ...START, durationMs: 0 });
    await advance(0);
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });

  it('unmounting cancels the countdown', async () => {
    const { unmount, onTimeout } = setup();
    await advance(5_000);
    unmount();

    await advance(DURATION_MS);
    expect(onTimeout).not.toHaveBeenCalled();
  });
});
