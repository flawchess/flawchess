import { TYPICAL_BAND_FILL } from '@/lib/theme';

// The grey "typical" band's label, drawn as a watermark: bold text centred in the band and
// cut out of it, so the card surface shows through the letters. The font shrinks to fit
// when the axis makes the band thin.
const TYPICAL_LABEL = 'typical';
const WATERMARK_FONT_SIZE = 24;
const WATERMARK_FONT_WEIGHT = 800;
const WATERMARK_HEIGHT_RATIO = 0.85;
const WATERMARK_LETTER_SPACING = '0.08em';

/** The geometry Recharts passes to a ReferenceArea `shape`. */
export interface BandShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

/**
 * The typical band rect with its label masked out of it (a cutout, not painted text). Get
 * maskId from useTypicalBandMaskId.
 */
export function TypicalBandWatermark({
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  maskId,
}: BandShapeProps & { maskId: string }) {
  if (width <= 0 || height <= 0) return null;
  const fontSize = Math.min(WATERMARK_FONT_SIZE, height * WATERMARK_HEIGHT_RATIO);
  return (
    <g>
      <mask id={maskId} maskUnits="userSpaceOnUse" x={x} y={y} width={width} height={height}>
        <rect x={x} y={y} width={width} height={height} fill="white" />
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={fontSize}
          fontWeight={WATERMARK_FONT_WEIGHT}
          letterSpacing={WATERMARK_LETTER_SPACING}
          fill="black"
        >
          {TYPICAL_LABEL}
        </text>
      </mask>
      {/* Keeps Recharts' own class so band geometry stays queryable like a default ReferenceArea. */}
      <rect
        className="recharts-reference-area-rect"
        x={x}
        y={y}
        width={width}
        height={height}
        fill={TYPICAL_BAND_FILL}
        mask={`url(#${maskId})`}
      />
    </g>
  );
}
