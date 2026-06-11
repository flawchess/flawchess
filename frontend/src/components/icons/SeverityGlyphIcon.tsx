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

import { SEV_BLUNDER, SEV_MISTAKE } from '@/lib/theme';

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
  // Tighten the two-char "??" so the larger glyph still clears the dot edge.
  // textAnchor="middle" counts the trailing letter-spacing gap, which shifts the
  // glyphs right by half a step; offset x by letterSpacing/2 to re-center.
  const isMulti = symbol.length > 1;
  const letterSpacing = isMulti ? -2 : 0;
  const x = 12 + letterSpacing / 2;
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
        x={x}
        y="12.5"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        fontFamily="ui-sans-serif, system-ui, sans-serif"
        fontWeight="700"
        fontSize={fontSize}
        letterSpacing={isMulti ? letterSpacing : undefined}
      >
        {symbol}
      </text>
    </svg>
  );
}

/** "??" on a red dot — blunder. */
export function BlunderIcon(props: SeverityGlyphIconProps) {
  return <GlyphBadge symbol="??" color={SEV_BLUNDER} fontSize={17} {...props} />;
}

/** "?" on an orange dot — mistake. */
export function MistakeIcon(props: SeverityGlyphIconProps) {
  return <GlyphBadge symbol="?" color={SEV_MISTAKE} fontSize={19} {...props} />;
}
