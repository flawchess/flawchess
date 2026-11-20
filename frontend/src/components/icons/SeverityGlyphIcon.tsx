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
 * `aria-hidden` so they drop into the same call sites (the Flaws filter panel's
 * FlawFilterControl) as the lucide icons they replace. The Library Stats tiles
 * (FlawTiles) and gap popovers (GapPopover) use no glyph, only the severity colour.
 */

import type { CSSProperties } from 'react';

import { GlyphText } from '@/components/icons/GlyphText';
import { FACEPALM_GLYPH, SEVERITY_GLYPH } from '@/lib/severityGlyph';
import type { GlyphSpec } from '@/lib/severityGlyph';

export interface SeverityGlyphIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

function GlyphBadge({
  glyph,
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: SeverityGlyphIconProps & { glyph: GlyphSpec }) {
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
      <circle cx="12" cy="12" r="11" fill={glyph.color} />
      <GlyphText glyph={glyph} x={12} y={12.5} />
    </svg>
  );
}

/** "??" on a red dot — blunder. */
export function BlunderIcon(props: SeverityGlyphIconProps) {
  return <GlyphBadge glyph={SEVERITY_GLYPH.blunder} {...props} />;
}

/** "?" on an orange dot — mistake. */
export function MistakeIcon(props: SeverityGlyphIconProps) {
  return <GlyphBadge glyph={SEVERITY_GLYPH.mistake} {...props} />;
}

/** "???" (three overlapping marks) on a dark red dot — facepalm blunder (score >= 70%). */
export function FacepalmBlunderIcon(props: SeverityGlyphIconProps) {
  return <GlyphBadge glyph={FACEPALM_GLYPH} {...props} />;
}

// The inaccuracy "!?" yellow glyph is defined in SEVERITY_GLYPH (lib/severityGlyph)
// and rendered as an on-board SVG corner marker (boardMarkers). No standalone React
// component is exported because the move list intentionally omits inaccuracy.
