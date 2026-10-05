import { describe, expect, it } from 'vitest';
import { applyVisibility, readStopwatch, startStopwatch } from '@/lib/visibleStopwatch';

describe('visibleStopwatch', () => {
  it('counts a visible span', () => {
    const sw = startStopwatch(1000, false);
    expect(readStopwatch(sw, 3500)).toEqual({ visibleMs: 2500, hiddenMs: 0 });
  });

  it('excludes a hidden span from visibleMs and adds it to hiddenMs', () => {
    let sw = startStopwatch(0, false);
    sw = applyVisibility(sw, true, 2000);
    sw = applyVisibility(sw, false, 7000);
    expect(readStopwatch(sw, 8000)).toEqual({ visibleMs: 3000, hiddenMs: 5000 });
  });

  it('starting hidden keeps visibleMs at 0 until visible', () => {
    let sw = startStopwatch(100, true);
    expect(readStopwatch(sw, 4100)).toEqual({ visibleMs: 0, hiddenMs: 4000 });
    sw = applyVisibility(sw, false, 4100);
    expect(readStopwatch(sw, 5100)).toEqual({ visibleMs: 1000, hiddenMs: 4000 });
  });

  it('a duplicate hidden or visible call is a no-op and never re-baselines', () => {
    let sw = startStopwatch(0, false);
    sw = applyVisibility(sw, true, 1000);
    const afterFirstHidden = sw;
    expect(applyVisibility(sw, true, 4000)).toBe(afterFirstHidden);
    sw = applyVisibility(sw, false, 5000);
    const afterVisible = sw;
    expect(applyVisibility(sw, false, 6000)).toBe(afterVisible);
    expect(readStopwatch(sw, 6000)).toEqual({ visibleMs: 2000, hiddenMs: 4000 });
  });

  it('a seed continues the totals', () => {
    const sw = startStopwatch(10, false, { visibleMs: 500, hiddenMs: 200 });
    expect(readStopwatch(sw, 1010)).toEqual({ visibleMs: 1500, hiddenMs: 200 });
  });

  it('readStopwatch includes the running span and never mutates its input', () => {
    const sw = startStopwatch(0, false);
    const snapshot = { ...sw };
    readStopwatch(sw, 5000);
    expect(sw).toEqual(snapshot);
    expect(readStopwatch(sw, 6000).visibleMs).toBe(6000);
  });
});
