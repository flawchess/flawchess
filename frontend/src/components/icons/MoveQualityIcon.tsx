/**
 * MoveQualityIcon — maps a `MoveQuality` bucket to its badge icon, the single
 * source of truth for the gem/great/best/good/inaccuracy/mistake/blunder glyphs
 * shared by the Move Stats table (`MoveStats.tsx`) and the Moves-by-Rating
 * tooltip (`MovesByRatingChart.tsx`). The three severity buckets reuse the same
 * circle + "?!"/"?"/"??" glyph convention as the on-board markers; the positive
 * buckets reuse the standalone badge icons.
 *
 * Kept here (not in `SeverityGlyphIcon.tsx`) because that file intentionally
 * omits an inaccuracy variant for its move-list call sites, whereas both table
 * consumers need all three severities.
 */

import type { CSSProperties } from 'react';

import { GemIcon } from '@/components/icons/GemIcon';
import { GreatMoveIcon } from '@/components/icons/GreatMoveIcon';
import { BestMoveIcon } from '@/components/icons/BestMoveIcon';
import { GoodMoveIcon } from '@/components/icons/GoodMoveIcon';
import { SEVERITY_GLYPH } from '@/lib/severityGlyph';
import type { MoveQuality } from '@/lib/moveQuality';
import type { FlawSeverity } from '@/types/library';

const SEVERITY_QUALITIES: readonly FlawSeverity[] = ['inaccuracy', 'mistake', 'blunder'];

function isSeverityQuality(quality: MoveQuality): quality is FlawSeverity {
  return (SEVERITY_QUALITIES as readonly string[]).includes(quality);
}

/**
 * A single severity glyph badge (circle + "??"/"?"/"?!" text), rendered inline
 * so all 3 severities share one visual convention — mirrors
 * `SeverityGlyphIcon.tsx`'s private `GlyphBadge`, which exports no inaccuracy
 * variant. No letter-spacing tightening — matches the on-board severity glyph
 * (boardMarkers) so the two-char "??"/"?!" read with natural spacing.
 */
function SeverityQualityIcon({
  severity,
  className,
  style,
}: {
  severity: FlawSeverity;
  className?: string;
  style?: CSSProperties;
}) {
  const glyph = SEVERITY_GLYPH[severity];
  return (
    <svg viewBox="0 0 24 24" className={className} style={style} aria-hidden role="img">
      <circle cx="12" cy="12" r="11" fill={glyph.color} />
      <text
        x="12"
        y="12.5"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        fontFamily="ui-sans-serif, system-ui, sans-serif"
        fontWeight="700"
        fontSize={glyph.fontSize}
      >
        {glyph.symbol}
      </text>
    </svg>
  );
}

export interface MoveQualityIconProps {
  quality: MoveQuality;
  className?: string;
  style?: CSSProperties;
}

export function MoveQualityIcon({ quality, className, style }: MoveQualityIconProps) {
  if (isSeverityQuality(quality)) {
    return <SeverityQualityIcon severity={quality} className={className} style={style} />;
  }
  switch (quality) {
    case 'gem':
      return <GemIcon className={className} style={style} aria-hidden />;
    case 'great':
      return <GreatMoveIcon className={className} style={style} aria-hidden />;
    case 'best':
      return <BestMoveIcon className={className} style={style} aria-hidden />;
    case 'good':
      return <GoodMoveIcon className={className} style={style} aria-hidden />;
  }
}
