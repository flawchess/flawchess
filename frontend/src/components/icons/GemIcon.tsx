/**
 * Gem badge icon — a white lucide `Gem` icon on a violet (`MAIA_ACCENT`) dot,
 * marking a "gem move" (Phase 163, SEED-092): a played move that is both hard
 * for a human to find and the only good move in the position.
 *
 * Shape-compatible with `SeverityGlyphIconProps` (`className`, `style`,
 * `aria-hidden`) so it drops into the same move-list call sites
 * (VariationTree's `BlunderIcon`/`MistakeIcon`) as the hand-drawn severity
 * glyphs.
 *
 * Unlike `SeverityGlyphIcon` — which draws its glyph from scratch to
 * sidestep Lichess's AGPL-3.0 assets (see that file's docstring) — the gem
 * badge's inner icon is lucide-react's `Gem`, which is MIT-licensed, so no
 * license concern applies here. The shape parity (svg > circle + centered
 * glyph, self-colored, drop-in props) is intentional even though the
 * AGPL-clean rationale doesn't carry over.
 *
 * The violet fill is baked in from `GEM_GLYPH` (not caller-overridable),
 * matching `SeverityGlyphIcon`'s self-color rationale.
 */

import type { CSSProperties } from 'react';
import { Gem } from 'lucide-react';

import { GEM_GLYPH } from '@/lib/gemGlyph';

export interface GemIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

/** A white lucide `Gem` on a violet dot — the "gem move" badge. */
export function GemIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: GemIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      {/* Accessible name (163-REVIEW IN-02): aria-hidden defaults to true, but a
          caller passing false would otherwise expose an UNNAMED role="img" to
          screen readers — the badge conveys meaning only via color/shape. */}
      <title>Gem move</title>
      <circle cx="12" cy="12" r="11" fill={GEM_GLYPH.color} />
      <Gem x={5} y={5} width={14} height={14} stroke="#fff" />
    </svg>
  );
}
