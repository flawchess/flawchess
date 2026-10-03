// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  readStreakLastSeen,
  resolveStreakArrival,
  writeStreakLastSeen,
} from '../streakArrival';

describe('resolveStreakArrival', () => {
  it('plays nothing on a first visit (nothing stored)', () => {
    expect(resolveStreakArrival(null, { streak: 52, freezes: 5 })).toEqual({ kind: 'none' });
  });

  it('plays nothing when nothing changed', () => {
    expect(resolveStreakArrival({ streak: 52, freezes: 5 }, { streak: 52, freezes: 5 })).toEqual({
      kind: 'none',
    });
  });

  it('ignites when the streak went up, and pops the freeze earned with it', () => {
    expect(resolveStreakArrival({ streak: 51, freezes: 4 }, { streak: 52, freezes: 5 })).toEqual({
      kind: 'changed',
      prev: { streak: 51, freezes: 4 },
      ignite: true,
      extinguish: false,
      freezesUsed: 0,
      freezesEarned: 1,
    });
  });

  it('cracks every freeze spent since the last visit while the streak is held', () => {
    expect(resolveStreakArrival({ streak: 52, freezes: 5 }, { streak: 52, freezes: 3 })).toEqual({
      kind: 'changed',
      prev: { streak: 52, freezes: 5 },
      ignite: false,
      extinguish: false,
      freezesUsed: 2,
      freezesEarned: 0,
    });
  });

  it('pops a freeze earned on an off-day session without igniting', () => {
    const arrival = resolveStreakArrival({ streak: 52, freezes: 4 }, { streak: 52, freezes: 5 });
    expect(arrival).toMatchObject({ kind: 'changed', ignite: false, freezesEarned: 1 });
  });

  it('extinguishes on a streak reset, after the last freeze cracks', () => {
    expect(resolveStreakArrival({ streak: 52, freezes: 1 }, { streak: 0, freezes: 0 })).toEqual({
      kind: 'changed',
      prev: { streak: 52, freezes: 1 },
      ignite: false,
      extinguish: true,
      freezesUsed: 1,
      freezesEarned: 0,
    });
  });
});

describe('streak last-seen storage', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it('round-trips per owner', () => {
    writeStreakLastSeen('a@example.com', { streak: 3, freezes: 2 });
    expect(readStreakLastSeen('a@example.com')).toEqual({ streak: 3, freezes: 2 });
    expect(readStreakLastSeen('b@example.com')).toBeNull();
  });

  it('reads corrupt or malformed values as nothing stored', () => {
    localStorage.setItem('flawchess_train_streak_last_seen:anon', '{not json');
    expect(readStreakLastSeen(null)).toBeNull();
    localStorage.setItem('flawchess_train_streak_last_seen:anon', '{"streak":-1,"freezes":2}');
    expect(readStreakLastSeen(null)).toBeNull();
  });

  it('survives storage that throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(readStreakLastSeen(null)).toBeNull();
    expect(() => writeStreakLastSeen(null, { streak: 1, freezes: 1 })).not.toThrow();
  });
});
