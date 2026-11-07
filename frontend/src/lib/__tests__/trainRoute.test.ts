import { describe, expect, it } from 'vitest';
import {
  ARCHIVE_PAGE_MAX,
  buildArchivePath,
  parseArchivePage,
  parseTrainRoute,
  TRAIN_TAB_PATHS,
} from '@/lib/trainRoute';

describe('parseTrainRoute', () => {
  it.each([
    ['/train', { tab: 'today' }],
    ['/train/', { tab: 'today' }],
    ['/train/leaderboard', { tab: 'leaderboard' }],
    ['/train/leaderboard/', { tab: 'leaderboard' }],
    ['/train/archive', { tab: 'archive', list: 'mastered' }],
    ['/train/archive/', { tab: 'archive', list: 'mastered' }],
    ['/train/archive/parked', { tab: 'archive', list: 'parked' }],
    ['/train/archive/parked/', { tab: 'archive', list: 'parked' }],
    ['/train/archive/mastered', null],
    ['/train/archive/parked/extra', null],
    ['/train/archivex', null],
    ['/train/foo', null],
    ['/train/leaderboardx', null],
    ['/', null],
  ])('%s -> %j', (pathname, expected) => {
    expect(parseTrainRoute(pathname)).toEqual(expected);
  });

  it('round-trips every tab path', () => {
    expect(parseTrainRoute(TRAIN_TAB_PATHS.today)).toEqual({ tab: 'today' });
    expect(parseTrainRoute(TRAIN_TAB_PATHS.leaderboard)).toEqual({ tab: 'leaderboard' });
    expect(parseTrainRoute(TRAIN_TAB_PATHS.archive)).toEqual({ tab: 'archive', list: 'mastered' });
  });
});

describe('buildArchivePath', () => {
  it('mastered is the canonical Archive path and parked sits under it', () => {
    expect(buildArchivePath('mastered')).toBe('/train/archive');
    expect(buildArchivePath('parked')).toBe('/train/archive/parked');
  });

  it('round-trips both lists through parseTrainRoute', () => {
    expect(parseTrainRoute(buildArchivePath('mastered'))).toEqual({
      tab: 'archive',
      list: 'mastered',
    });
    expect(parseTrainRoute(buildArchivePath('parked'))).toEqual({
      tab: 'archive',
      list: 'parked',
    });
  });
});

describe('parseArchivePage', () => {
  it.each([[null], ['abc'], ['0'], ['-3'], ['1.5'], [''], ['2e3'], [' 2']])(
    '%j -> 1',
    (raw) => {
      expect(parseArchivePage(raw)).toBe(1);
    },
  );

  it('reads a positive integer', () => {
    expect(parseArchivePage('1')).toBe(1);
    expect(parseArchivePage('7')).toBe(7);
  });

  it('caps at ARCHIVE_PAGE_MAX so the offset stays inside the backend bound', () => {
    expect(parseArchivePage(String(ARCHIVE_PAGE_MAX))).toBe(ARCHIVE_PAGE_MAX);
    expect(parseArchivePage(String(ARCHIVE_PAGE_MAX + 1))).toBe(ARCHIVE_PAGE_MAX);
    expect(parseArchivePage('99999999999999999999')).toBe(ARCHIVE_PAGE_MAX);
  });
});
