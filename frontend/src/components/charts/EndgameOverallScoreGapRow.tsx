/**
 * Phase 85 — Score Gap row (label + result + bullet chart).
 *
 * Used for both the *Endgame Score Gap* (with − without) and *Achievable Score
 * Gap* (actual − achievable) rows in the Score Differences card. Both share
 * the same bullet-chart shell (center=0, domain=SCORE_GAP_DOMAIN) and the
 * same coloring rule (zone tint regardless of confidence, per D-04), but the
 * neutral band now differs per row (Achievable ±5pp vs Endgame ±10pp — see
 * 260514-kei). The band is supplied by the caller via `neutralMin`/`neutralMax`
 * to keep a single source of truth for which row gets which band.
 */

import type { ReactNode } from 'react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';

import { SCORE_GAP_DOMAIN } from './EndgameOverallShared';

interface ScoreGapRowProps {
  label: ReactNode;
  value: number;
  formatted: string;
  resultColor: string | undefined;
  valueTestId: string;
  ariaLabel: string;
  /** Signed neutral-band lower bound in score-gap units ([−1, +1]).
   *  Caller-supplied so each row picks its own band (no shared constant). */
  neutralMin: number;
  /** Signed neutral-band upper bound in score-gap units ([−1, +1]).
   *  Caller-supplied so each row picks its own band (no shared constant). */
  neutralMax: number;
  /** Optional info popover trigger rendered at the end of the row (after the
   *  result value). Use InfoPopover from @/components/ui/info-popover. */
  tooltip?: ReactNode;
  /** Optional extra classes for the result percent number (font size etc.). */
  valueClassName?: string;
  /** 95% CI lower bound in domain units (signed). Renders whisker when both
   *  ciLow + ciHigh are defined. Mirrors MiniBulletChart's CI contract. */
  ciLow?: number;
  /** 95% CI upper bound in domain units (signed). Renders whisker when both
   *  ciLow + ciHigh are defined. Mirrors MiniBulletChart's CI contract. */
  ciHigh?: number;
  /** Optional bullet half-domain override. Defaults to SCORE_GAP_DOMAIN.
   *  Per-class cards pass ENDGAME_TYPE_SCORE_GAP_DOMAIN so the neutral band
   *  fills the same fraction of the axis as the Endgame Score bullet above. */
  domain?: number;
  /** Optional left slot rendered before the center label group. Used by
   *  EndgameTypeCard to show the Start predicted score. Defaults to undefined
   *  (renders nothing) so the 3 other callers remain pixel-identical. */
  startSlot?: ReactNode;
  /** Optional right slot rendered after the center label group. Used by
   *  EndgameTypeCard to show the End predicted score. Defaults to undefined
   *  (renders nothing) so the 3 other callers remain pixel-identical. */
  endSlot?: ReactNode;
  /** Optional chip rendered alongside the row. Sits inline at the right edge of
   *  the label/value row on all widths (the compact icon + integer form fits
   *  inline at 375px). Used by EndgameOverallPerformanceSection (page-level
   *  rows) and EndgameMetricCard (conv/parity buckets) to surface a
   *  PercentileChip. Defaults to undefined so EndgameTypeCard + Recovery card
   *  render pixel-identical. */
  chipSlot?: ReactNode;
}

export function ScoreGapRow({
  label,
  value,
  formatted,
  resultColor,
  valueTestId,
  ariaLabel,
  neutralMin,
  neutralMax,
  tooltip,
  valueClassName,
  ciLow,
  ciHigh,
  domain = SCORE_GAP_DOMAIN,
  startSlot,
  endSlot,
  chipSlot,
}: ScoreGapRowProps) {
  // quick-260519-ni3: 3-column label line when start/end slots are provided.
  // EndgameTypeCard uses this branch (start/end predicted scores around the
  // center label). chipSlot is never passed here today; if it ever is, it
  // renders inline at the right edge of the center group.
  const hasSlots = startSlot !== undefined || endSlot !== undefined;
  if (hasSlots) {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1 text-sm tabular-nums w-full">
          <div className="flex-1">{startSlot}</div>
          <span className="flex items-center gap-1 shrink-0">
            <span className="text-muted-foreground">{label}</span>
            <span
              className={`font-semibold${valueClassName ? ` ${valueClassName}` : ''}`}
              style={resultColor ? { color: resultColor } : undefined}
              data-testid={valueTestId}
            >
              {formatted}
            </span>
            {tooltip}
            {chipSlot && <span className="ml-auto">{chipSlot}</span>}
          </span>
          <div className="flex-1 flex justify-end">{endSlot}</div>
        </div>
        <div className="min-w-0 tabular-nums">
          <MiniBulletChart
            value={value}
            center={0}
            neutralMin={neutralMin}
            neutralMax={neutralMax}
            domain={domain}
            barColor="neutral"
            ariaLabel={ariaLabel}
            ciLow={ciLow}
            ciHigh={ciHigh}
          />
        </div>
      </div>
    );
  }
  // Non-hasSlots layout uses CSS Grid. Two rows on both mobile and desktop:
  //   row 1 = label/value/tooltip (col 1)  +  chip (col 2, right-aligned)
  //   row 2 = bullet chart        (spans both cols)
  // Callers that don't pass chipSlot collapse cleanly — col 2 of row 1 is
  // simply empty.
  return (
    <div className="grid grid-cols-[1fr_auto] gap-x-1 gap-y-2 w-full">
      <span className="row-start-1 col-start-1 flex items-center gap-1 text-sm tabular-nums min-w-0">
        <span className="text-muted-foreground">{label}</span>
        <span
          className={`font-semibold${valueClassName ? ` ${valueClassName}` : ''}`}
          style={resultColor ? { color: resultColor } : undefined}
          data-testid={valueTestId}
        >
          {formatted}
        </span>
        {tooltip}
      </span>
      {chipSlot && (
        <span className="row-start-1 col-start-2 justify-self-end">{chipSlot}</span>
      )}
      <div className="row-start-2 col-span-2 min-w-0 tabular-nums">
        <MiniBulletChart
          value={value}
          center={0}
          neutralMin={neutralMin}
          neutralMax={neutralMax}
          domain={domain}
          barColor="neutral"
          ariaLabel={ariaLabel}
          ciLow={ciLow}
          ciHigh={ciHigh}
        />
      </div>
    </div>
  );
}
