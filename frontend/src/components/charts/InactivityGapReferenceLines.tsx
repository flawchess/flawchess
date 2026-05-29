/**
 * Shared inactivity-gap render helper for ordinal-axis timeline charts (SC-4).
 *
 * Returns a flat array of <ReferenceLine> elements — NOT a React component.
 * Recharts (ComposedChart/LineChart) discovers ReferenceLine by scanning DIRECT
 * children; a wrapping component or Fragment hides them. The helper is a plain
 * function so the spread `{inactivityGapReferenceLines(...)}` inside any chart
 * yields direct children and Recharts picks them up correctly.
 *
 * Structure mirrors signedBandGradient.ts: exported interface + exported
 * function, zero complex side effects.
 */

import type { ReactElement } from 'react';
import { ReferenceLine } from 'recharts';
import { Palmtree } from 'lucide-react';
import { computeInactivityGaps } from '@/lib/inactivityGaps';
import { BREAK_LABEL_FONT_SIZE, BREAK_LABEL_GLYPH_SIZE } from '@/lib/theme';

export interface InactivityGapReferenceLinesProps {
  /** MUST be ascending-sorted ISO YYYY-MM-DD strings; caller's responsibility. */
  dates: string[];
  /** Forward to ReferenceLine when the chart has named axes; omit for single-default-axis charts. */
  yAxisId?: string;
  /** Gaps strictly greater than this value are annotated. Defaults to INACTIVITY_GAP_THRESHOLD_DAYS (56). */
  thresholdDays?: number;
}

/**
 * Compute inactivity-gap ReferenceLine elements for the given sorted date array.
 *
 * Returns [] for fewer than 2 dates or when no pair exceeds the threshold.
 * Each gap produces one <ReferenceLine> with a Palmtree glyph + enlarged label.
 */
export function inactivityGapReferenceLines({
  dates,
  yAxisId,
  thresholdDays,
}: InactivityGapReferenceLinesProps): ReactElement[] {
  const gaps = computeInactivityGaps(dates, thresholdDays);
  if (gaps.length === 0) return [];

  return gaps.map((gap) => {
    // afterIndex < dates.length - 1 by computeInactivityGaps contract, so
    // dates[gap.afterIndex] is provably in-bounds — non-null assertion is safe.
    const xValue = dates[gap.afterIndex]!;
    const label = gap.label;

    // Recharts custom label: receives viewBox from the chart layout engine.
    const LabelContent = (props: {
      viewBox?: { x?: number; y?: number; width?: number; height?: number };
    }) => {
      const { x = 0, y = 0 } = props.viewBox ?? {};
      const glyphSize = BREAK_LABEL_GLYPH_SIZE;
      const labelX = x + 4;
      const labelY = y + 4;
      // Duration sits below the glyph, horizontally centered on it: textX is the
      // glyph's horizontal midpoint (text-anchor="middle"), textY clears the
      // glyph's bottom edge plus a small gap.
      const textX = labelX + glyphSize / 2;
      const textY = labelY + glyphSize + BREAK_LABEL_FONT_SIZE;
      return (
        <g data-testid="inactivity-gap-label">
          {/* Palmtree glyph: lucide renders as <svg class="lucide ..."> which is
              valid SVG content inside a chart <g>. Sized via BREAK_LABEL_GLYPH_SIZE
              (larger than the text) so the icon is the primary break marker. */}
          <Palmtree
            data-testid="inactivity-gap-glyph"
            width={glyphSize}
            height={glyphSize}
            x={labelX}
            y={labelY}
            stroke="currentColor"
            strokeOpacity={0.6}
          />
          <text
            x={textX}
            y={textY}
            fontSize={BREAK_LABEL_FONT_SIZE}
            fill="currentColor"
            fillOpacity={0.6}
            textAnchor="middle"
            dominantBaseline="central"
          >
            {label}
          </text>
        </g>
      );
    };

    return (
      <ReferenceLine
        key={`inactivity-gap-${gap.afterIndex}`}
        x={xValue}
        {...(yAxisId !== undefined ? { yAxisId } : {})}
        stroke="currentColor"
        strokeOpacity={0.3}
        strokeDasharray="4 2"
        label={<LabelContent />}
      />
    );
  });
}
