/**
 * Route parsing for the /train layout.
 *
 * `/train/*` is a single route in App.tsx, so `pages/Train.tsx` is the layout
 * and decides what to render from the pathname. Extracted to a pure module so
 * the path table is unit-testable without rendering the page (mirroring the
 * analysisUrl.ts extraction precedent).
 *
 * Paths are matched EXACTLY after stripping trailing slashes. `/train/foo` and
 * `/train/leaderboardx` are unknown and parse to `null`, which the layout
 * turns into a redirect to Today; the pathname is never rendered or sent to
 * the API.
 */

import type { ArchiveList } from '@/types/train';

export type TrainTab = 'today' | 'leaderboard' | 'archive' | 'blunder-check';

export type TrainRoute =
  | { tab: 'today' }
  | { tab: 'leaderboard' }
  | { tab: 'archive'; list: ArchiveList }
  | { tab: 'blunder-check' };

/** Canonical path of each tab. Bookmarks, reminders and Umami pageview history
 * all key on these, so they are settled and must not change. */
export const TRAIN_TAB_PATHS: Record<TrainTab, string> = {
  today: '/train',
  leaderboard: '/train/leaderboard',
  archive: '/train/archive',
  'blunder-check': '/train/blunder-check',
};

/** Path of the Parked list; Mastered is the Archive tab's own path. */
const ARCHIVE_PARKED_PATH = `${TRAIN_TAB_PATHS.archive}/parked`;

/** Returns the route for a pathname, or null for an unknown /train/* path. The parser is
 * beta-agnostic: the page redirects non-beta users away from the blunder-check tab. */
export function parseTrainRoute(pathname: string): TrainRoute | null {
  const path = pathname.replace(/\/+$/, '');
  if (path === TRAIN_TAB_PATHS.today) return { tab: 'today' };
  if (path === TRAIN_TAB_PATHS.leaderboard) return { tab: 'leaderboard' };
  if (path === TRAIN_TAB_PATHS.archive) return { tab: 'archive', list: 'mastered' };
  if (path === ARCHIVE_PARKED_PATH) return { tab: 'archive', list: 'parked' };
  if (path === TRAIN_TAB_PATHS['blunder-check']) return { tab: 'blunder-check' };
  return null;
}

/** Path of one Archive list. Mastered is the canonical `/train/archive`. */
export function buildArchivePath(list: ArchiveList): string {
  return list === 'parked' ? ARCHIVE_PARKED_PATH : TRAIN_TAB_PATHS.archive;
}

/**
 * Highest page a `?page=` value may name. The cap keeps `(page - 1) * 20`
 * inside the backend's offset bound (2^31 - 1), so a hand-typed huge number
 * lands on the over-range path (replace to the last page) instead of a 422.
 */
export const ARCHIVE_PAGE_MAX = 1_000_000;

/** The 1-based page from `?page=`: 1 for null, a non-integer or anything below 1. */
export function parseArchivePage(raw: string | null): number {
  if (raw === null || !/^\d+$/.test(raw)) return 1;
  const page = Number(raw);
  if (page < 1) return 1;
  return Math.min(page, ARCHIVE_PAGE_MAX);
}
