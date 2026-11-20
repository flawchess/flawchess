/**
 * The white NAG text of a severity glyph badge ("??", "?", "?!", or the stacked facepalm
 * "???"), drawn centered at (x, y). Shared by the React badge icons (SeverityGlyphIcon,
 * MoveQualityIcon) and the board corner markers (boardMarkers) so all three render the
 * same glyph.
 *
 * `scale` maps the spec's viewBox units to the target coordinate space: 1 inside a
 * 24-unit icon viewBox, the board's px-per-unit for a corner marker.
 */

import type { GlyphSpec } from '@/lib/severityGlyph';

const GLYPH_FONT_FAMILY = 'ui-sans-serif, system-ui, sans-serif';
const GLYPH_FONT_WEIGHT = '700';
const GLYPH_FILL = '#fff';

interface GlyphTextProps {
  glyph: GlyphSpec;
  x: number;
  y: number;
  scale?: number;
}

export function GlyphText({ glyph, x, y, scale = 1 }: GlyphTextProps) {
  const common = {
    y,
    textAnchor: 'middle',
    dominantBaseline: 'central',
    fill: GLYPH_FILL,
    fontFamily: GLYPH_FONT_FAMILY,
    fontWeight: GLYPH_FONT_WEIGHT,
    fontSize: glyph.fontSize * scale,
  } as const;
  const { stack } = glyph;
  if (!stack) {
    return (
      <text x={x} {...common}>
        {glyph.symbol}
      </text>
    );
  }
  // Stacked: `count` copies of the symbol at a fixed spacing, centered on x, drawn left to
  // right so each one overlaps the previous. The dot-coloured outline (painted under the
  // fill) carves a gap where they overlap, so the marks stay separate at full font size.
  const first = -((stack.count - 1) / 2) * stack.offset;
  return (
    <>
      {Array.from({ length: stack.count }, (_, i) => (
        <text
          key={i}
          x={x + (first + i * stack.offset) * scale}
          {...common}
          stroke={glyph.color}
          strokeWidth={stack.outline * scale}
          strokeLinejoin="round"
          paintOrder="stroke"
        >
          {glyph.symbol}
        </text>
      ))}
    </>
  );
}
