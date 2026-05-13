/**
 * Phase 85 — Score Gap row (label + signed math + bullet chart).
 *
 * Used for both the *Endgame Score Gap* (with − without) and *Endgame Score
 * Loss* (with − achievable) rows in the Score Differences card. Both share
 * the same bullet-chart settings (center=0, neutral band from
 * SCORE_GAP_NEUTRAL_MIN/MAX, domain=SCORE_GAP_DOMAIN) and the same coloring
 * rule: operand zone color only when significant + outside neutral; result
 * colored by zone regardless of confidence so the user always sees where
 * they land (D-04).
 */

import type { ReactNode } from 'react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import {
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';

import { SCORE_GAP_DOMAIN } from './EndgameOverallShared';

interface ScoreGapRowProps {
  label: string;
  value: number;
  formatted: string;
  operand1Pct: string;
  operand1Color: string | undefined;
  operand2Pct: string;
  operand2Color: string | undefined;
  resultColor: string | undefined;
  showMath: boolean;
  mathTestId: string;
  valueTestId: string;
  ariaLabel: string;
  /** Optional info popover trigger rendered at the end of the row (after the
   *  result value). Use InfoPopover from @/components/ui/info-popover. */
  tooltip?: ReactNode;
}

export function ScoreGapRow({
  label,
  value,
  formatted,
  operand1Pct,
  operand1Color,
  operand2Pct,
  operand2Color,
  resultColor,
  showMath,
  mathTestId,
  valueTestId,
  ariaLabel,
  tooltip,
}: ScoreGapRowProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">{label}</span>
        {showMath ? (
          <span className="tabular-nums" data-testid={mathTestId}>
            <span
              className="font-semibold"
              style={operand1Color ? { color: operand1Color } : undefined}
            >
              {operand1Pct}
            </span>
            {' − '}
            <span
              className="font-semibold"
              style={operand2Color ? { color: operand2Color } : undefined}
            >
              {operand2Pct}
            </span>
            {' = '}
            <span
              className="font-semibold"
              style={resultColor ? { color: resultColor } : undefined}
              data-testid={valueTestId}
            >
              {formatted}
            </span>
          </span>
        ) : (
          <span
            className="font-semibold"
            style={resultColor ? { color: resultColor } : undefined}
            data-testid={valueTestId}
          >
            {formatted}
          </span>
        )}
        {tooltip}
      </span>
      <div className="min-w-0 tabular-nums">
        <MiniBulletChart
          value={value}
          center={0}
          neutralMin={SCORE_GAP_NEUTRAL_MIN}
          neutralMax={SCORE_GAP_NEUTRAL_MAX}
          domain={SCORE_GAP_DOMAIN}
          barColor="neutral"
          ariaLabel={ariaLabel}
        />
      </div>
    </div>
  );
}
