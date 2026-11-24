import type { QueryStatus } from '@tanstack/react-query';

/** Slowest cadence a failing status poll falls back to. */
export const POLL_ERROR_BACKOFF_MS = 30_000;

/**
 * Slow a status poll down while its query is in an error state.
 *
 * FLAWCHESS-24: an offline phone kept polling the eval-coverage and readiness endpoints at 1 s
 * and 3 s, and each failed poll became a Sentry event (about 56 of 69 events in 35 minutes
 * came from these two endpoints).
 *
 * `scheduled` is the interval the hook would use anyway, computed first and unchanged. The
 * result is the larger of it and `POLL_ERROR_BACKOFF_MS` while the status is 'error', which
 * respects the hook's own stop and ladder logic: a `false` (poll finished or stalled) stays
 * `false`, so a failure never restarts a poll that had stopped, and the 60 s and 300 s
 * readiness steps never speed up to 30 s. A success returns the status to 'success', so the
 * normal cadence resumes at once.
 */
export function withErrorBackoff(scheduled: number | false, status: QueryStatus): number | false {
  if (scheduled === false || status !== 'error') return scheduled;
  return Math.max(scheduled, POLL_ERROR_BACKOFF_MS);
}
