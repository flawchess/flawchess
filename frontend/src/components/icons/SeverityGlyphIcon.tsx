/**
 * Severity glyph icons — the standard chess annotation marks rendered as small
 * colored-dot badges: "??" on a red dot (blunder) and "?" on an orange dot
 * (mistake). Drawn from scratch (a circle + a `<text>` glyph) rather than reused
 * from Lichess, whose assets are AGPL-3.0; the "??"/"?" NAG marks are a chess
 * convention, not a Lichess creation, so an original SVG sidesteps any license.
 *
 * The dot colors are baked in (SEV_BLUNDER / SEV_MISTAKE from theme.ts) so the
 * badge keeps its semantic red/orange regardless of any `style={{ color }}` a
 * caller passes (callers tint lucide icons that way; these self-color instead).
 *
 * Shape-compatible with `LucideIcon` usage — accepts `className`, `style`, and
 * `aria-hidden` so they drop into the same call sites (FlawComparisonGrid /
 * FlawBulletPopover) as the lucide icons they replace.
 */

import type { CSSProperties } from 'react';

import { SEVERITY_GLYPH } from '@/lib/severityGlyph';

export interface SeverityGlyphIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

interface GlyphBadgeProps extends SeverityGlyphIconProps {
  symbol: string;
  color: string;
  /** Glyph font-size in viewBox units — smaller for the two-char "??". */
  fontSize: number;
}

function GlyphBadge({
  symbol,
  color,
  fontSize,
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: GlyphBadgeProps) {
  // No letter-spacing tightening: the two-char "??"/"?!" clears the dot edge at
  // this font size on its own, and matching the board glyph (boardMarkers, which
  // applies none) keeps the "??" from reading cramped in the move list.
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      <circle cx="12" cy="12" r="11" fill={color} />
      <text
        x="12"
        y="12.5"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        fontFamily="ui-sans-serif, system-ui, sans-serif"
        fontWeight="700"
        fontSize={fontSize}
      >
        {symbol}
      </text>
    </svg>
  );
}

/** "??" on a red dot — blunder. */
export function BlunderIcon(props: SeverityGlyphIconProps) {
  const g = SEVERITY_GLYPH.blunder;
  return <GlyphBadge symbol={g.symbol} color={g.color} fontSize={g.fontSize} {...props} />;
}

/** "?" on an orange dot — mistake. */
export function MistakeIcon(props: SeverityGlyphIconProps) {
  const g = SEVERITY_GLYPH.mistake;
  return <GlyphBadge symbol={g.symbol} color={g.color} fontSize={g.fontSize} {...props} />;
}

// The inaccuracy "!?" yellow glyph is defined in SEVERITY_GLYPH (lib/severityGlyph)
// and rendered as an on-board SVG corner marker (boardMarkers). No standalone React
// component is exported because the move list intentionally omits inaccuracy (D-03).
