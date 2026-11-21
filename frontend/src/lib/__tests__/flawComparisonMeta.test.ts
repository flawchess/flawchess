import { describe, expect, it } from 'vitest';
import {
  NO_RECENT_GAMES_HINT,
  isQuietTc,
  libraryBasisText,
  libraryFreshImportBasisText,
  libraryNoRecentGamesText,
  librarySampleBasisText,
} from '@/lib/flawComparisonMeta';

type BasisInput = Parameters<typeof librarySampleBasisText>[0];

const BASE: BasisInput = {
  tc: 'blitz',
  totalN: 412,
  analyzedN: 300,
  capReached: false,
  sampleSince: '2025-03-14',
  recencyFiltered: false,
  otherFiltersActive: false,
  windowMonths: 36,
};

describe('librarySampleBasisText', () => {
  it.each<[string, Partial<BasisInput>, string]>([
    [
      'under the cap, default window',
      {},
      'Based on your 412 blitz games from the last 36 months, 300 analyzed.',
    ],
    [
      'at the cap, default window: "most recent" and the oldest game month',
      { totalN: 1000, analyzedN: 640, capReached: true },
      'Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed.',
    ],
    [
      'under the cap, recency filter',
      { totalN: 212, analyzedN: 180, recencyFiltered: true },
      'Based on your 212 blitz games in the selected period, 180 analyzed.',
    ],
    [
      'at the cap, recency filter',
      { totalN: 1000, analyzedN: 640, capReached: true, recencyFiltered: true, sampleSince: '2026-08-02' },
      'Based on your most recent 1,000 blitz games in the selected period (since Aug 2026), 640 analyzed.',
    ],
    [
      'at the cap, recency filter and another filter',
      {
        totalN: 1000,
        analyzedN: 640,
        capReached: true,
        recencyFiltered: true,
        otherFiltersActive: true,
        sampleSince: '2026-08-14',
      },
      'Based on your most recent 1,000 blitz games in the selected period and the current filters (since Aug 2026), 640 analyzed.',
    ],
    [
      'under the cap, another filter active',
      { otherFiltersActive: true },
      'Based on your 412 blitz games from the last 36 months in the current filters, 300 analyzed.',
    ],
    [
      'at the cap, another filter active',
      { totalN: 1000, analyzedN: 640, capReached: true, otherFiltersActive: true },
      'Based on your most recent 1,000 blitz games in the current filters (since Mar 2025), 640 analyzed.',
    ],
    [
      'recency filter and another filter',
      { totalN: 212, analyzedN: 180, recencyFiltered: true, otherFiltersActive: true },
      'Based on your 212 blitz games in the selected period and the current filters, 180 analyzed.',
    ],
    [
      'a single game is singular',
      { totalN: 1, analyzedN: 1 },
      'Based on your 1 blitz game from the last 36 months, 1 analyzed.',
    ],
  ])('%s', (_label, overrides, expected) => {
    expect(librarySampleBasisText({ ...BASE, ...overrides })).toBe(expected);
  });

  it('ignores sampleSince under the cap', () => {
    expect(librarySampleBasisText({ ...BASE, sampleSince: '2020-01-14' })).toBe(
      'Based on your 412 blitz games from the last 36 months, 300 analyzed.',
    );
  });

  it('omits the since clause at the cap when the window has no start date', () => {
    expect(
      librarySampleBasisText({ ...BASE, totalN: 1000, analyzedN: 1000, capReached: true, sampleSince: null }),
    ).toBe('Based on your most recent 1,000 blitz games, 1,000 analyzed.');
  });
});

describe('libraryBasisText', () => {
  it('names the recent sample in the popover basis line', () => {
    expect(libraryBasisText(1841, 'rapid')).toBe(
      'Based on your 1,841 analyzed rapid games in the recent sample.',
    );
  });
});

describe('libraryFreshImportBasisText', () => {
  it('states the unwindowed total when nothing is analyzed yet', () => {
    expect(libraryFreshImportBasisText(523)).toBe('0 of 523 games analyzed in the current filters.');
  });
});

describe('isQuietTc', () => {
  it('is true only for a TC with no game in the window', () => {
    expect(isQuietTc({ total_n: 0 })).toBe(true);
    expect(isQuietTc({ total_n: 5 })).toBe(false);
  });

  it('is false for an entry without total_n (the tactic payload shape)', () => {
    expect(isQuietTc({})).toBe(false);
  });
});

describe('quiet time control copy', () => {
  it('names the TC and the window length', () => {
    expect(libraryNoRecentGamesText('blitz', 36, false)).toBe(
      'No blitz games in the last 36 months.',
    );
  });

  it('adds the filter qualifier when a sidebar filter other than recency is active', () => {
    expect(libraryNoRecentGamesText('rapid', 36, true)).toBe(
      'No rapid games in the last 36 months in the current filters.',
    );
  });

  it('points at a longer Recency period or a custom range', () => {
    expect(NO_RECENT_GAMES_HINT).toBe(
      'Choose a longer period or a custom range under Recency to include older games.',
    );
  });
});
