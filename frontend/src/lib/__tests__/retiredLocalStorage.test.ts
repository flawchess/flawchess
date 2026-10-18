// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';

import { removeRetiredBookmarkChartKeys } from '../retiredLocalStorage';

beforeEach(() => {
  localStorage.clear();
});

describe('removeRetiredBookmarkChartKeys', () => {
  it('removes the prefixed keys, keeps unrelated ones and returns the count', () => {
    localStorage.setItem('bookmark-chart-enabled-3', 'false');
    localStorage.setItem('bookmark-chart-enabled-17', 'true');
    localStorage.setItem('unrelated-key', 'keep');

    expect(removeRetiredBookmarkChartKeys(localStorage)).toBe(2);

    expect(localStorage.getItem('bookmark-chart-enabled-3')).toBeNull();
    expect(localStorage.getItem('bookmark-chart-enabled-17')).toBeNull();
    expect(localStorage.getItem('unrelated-key')).toBe('keep');
  });

  it('is a no-op on a second call', () => {
    localStorage.setItem('bookmark-chart-enabled-3', 'false');
    removeRetiredBookmarkChartKeys(localStorage);
    expect(removeRetiredBookmarkChartKeys(localStorage)).toBe(0);
  });

  it('returns 0 without throwing when storage access throws', () => {
    const throwing = {
      get length(): number {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredBookmarkChartKeys(throwing)).toBe(0);
  });

  it('returns 0 without throwing when key() throws', () => {
    const throwing = {
      length: 1,
      key: () => {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredBookmarkChartKeys(throwing)).toBe(0);
  });
});
