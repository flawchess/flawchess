/**
 * Great-move badge icon — a white "!" glyph on a blue (`GREAT_GLYPH`) dot,
 * marking a "great move" (Phase 175, SEED-108): a played move that is the
 * only good move in the position (same C2 gate as gem) and one a human at
 * the selected rating rarely finds, but not as rarely as a gem (D-01: gem =
 * maia_prob <= 0.20, great = maia_prob in (0.20, 0.50]).
 *
 * Shape-compatible with `SeverityGlyphIconProps`/`GemIconProps` (`className`,
 * `style`, `aria-hidden`) so it drops into the same move-list call sites
 * (VariationTree's `BlunderIcon`/`MistakeIcon`/`GemIcon`) as the severity
 * glyphs and the gem badge.
 *
 * Unlike `GemIcon` — which draws lucide's MIT-licensed `Gem` icon — the great
 * badge's inner glyph is a CUSTOM inline SVG "!" (D-02): chess.com's "Great
 * Move" mark has no direct lucide equivalent, so it's hand-drawn as a
 * vertical bar + dot, matching `SeverityGlyphIcon`'s from-scratch-glyph
 * approach.
 */

import type { CSSProperties } from 'react';

import { GREAT_GLYPH } from '@/lib/greatGlyph';

export interface GreatMoveIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

/** A white "!" glyph on a blue dot — the "great move" badge. */
export function GreatMoveIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: GreatMoveIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      {/* Accessible name (mirrors GemIcon's 163-REVIEW IN-02 fix): aria-hidden
          defaults to true, but a caller passing false would otherwise expose an
          UNNAMED role="img" to screen readers — the badge conveys meaning only
          via color/shape. */}
      <title>Great move</title>
      <circle cx="12" cy="12" r="11" fill={GREAT_GLYPH.color} />
      {/* Hand-drawn "!" — vertical stroke + dot, matching the badge's white-on-
          color convention (GemIcon/BookIcon's stroke="#fff"). */}
      <line x1="12" y1="6" x2="12" y2="14" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="12" cy="18" r="1.4" fill="#fff" />
    </svg>
  );
}
