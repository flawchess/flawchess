/**
 * Inactivity-gap detection for ordinal-axis timeline charts.
 *
 * Scans consecutive (date, date+1) pairs in a sorted date array and returns
 * a descriptor for every gap that exceeds the threshold. Consumed by
 * EndgameScoreOverTimeChart and EndgameEloTimelineSection to render
 * axis-break annotations on long inactive stretches.
 *
 * Structure mirrors signedBandGradient.ts: exported const + interface +
 * single exported function, zero imports, no React, no side effects.
 */

/** Default threshold: 8 weeks (~2 months). */
export const INACTIVITY_GAP_THRESHOLD_DAYS = 56;

/** Describes a gap between two consecutive data points. */
export interface InactivityGap {
  /** Gap occurs AFTER sortedDates[afterIndex] (the last active point before the gap). */
  afterIndex: number;
  /** Size of the gap in days (rounded to the nearest whole day). */
  gapDays: number;
  /** Human-readable label: "≈Ny inactive" (>=365 days) or "≈Nmo inactive" (< 365 days). */
  label: string;
}

/**
 * Compute inactivity gaps between consecutive dates in a sorted date array.
 *
 * @param sortedDates  ISO YYYY-MM-DD strings in ascending order.
 * @param thresholdDays  Gaps strictly greater than this value are annotated.
 *                       Defaults to INACTIVITY_GAP_THRESHOLD_DAYS (56).
 * @returns Descriptors for every gap exceeding the threshold.
 */
export function computeInactivityGaps(
  sortedDates: string[],
  thresholdDays: number = INACTIVITY_GAP_THRESHOLD_DAYS,
): InactivityGap[] {
  if (sortedDates.length < 2) return [];

  const gaps: InactivityGap[] = [];

  for (let i = 0; i < sortedDates.length - 1; i++) {
    // Both accesses are provably in-bounds: i < sortedDates.length - 1 guarantees
    // i is a valid index and i + 1 is at most sortedDates.length - 1.
    const dateA = sortedDates[i]!;
    const dateB = sortedDates[i + 1]!;
    const days = Math.round(
      (new Date(dateB).getTime() - new Date(dateA).getTime()) / 86400000,
    );

    if (days > thresholdDays) {
      const label =
        days >= 365
          ? `≈${(days / 365).toFixed(1)}y inactive`
          : `≈${Math.round(days / 30)}mo inactive`;
      gaps.push({ afterIndex: i, gapDays: days, label });
    }
  }

  return gaps;
}
