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
}: ScoreGapRowProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
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
      <div className="min-w-0 tabular-nums">
        <MiniBulletChart
          value={value}
          center={0}
          neutralMin={neutralMin}
          neutralMax={neutralMax}
          domain={SCORE_GAP_DOMAIN}
          barColor="neutral"
          ariaLabel={ariaLabel}
          ciLow={ciLow}
          ciHigh={ciHigh}
        />
      </div>
    </div>
  );
}
