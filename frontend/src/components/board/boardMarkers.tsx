/**
 * Shared SVG overlay primitives for the analysis ChessBoard and the games-card
 * MiniBoard (Quick 260627-r9g): a top-left depth-number label and a top-right
 * severity glyph badge. Kept in one place so both boards render identical marks.
 */

import { Gem } from 'lucide-react';

import { SEVERITY_GLYPH } from '../../lib/severityGlyph';
import { GEM_GLYPH } from '../../lib/gemGlyph';
import type { FlawSeverity } from '../../types/library';
import { squareToCoords } from './arrowGeometry';

/**
 * A severity glyph badge (??/?/!?) drawn in a square's top-right corner — replaces
 * the played-move blunder/mistake/inaccuracy arrow. Optional `label` renders the
 * move's depth in the top-left corner, matching the arrow depth-label style.
 *
 * `gem` is an additive, mutually-exclusive alternative to `severity` (Phase 163,
 * SEED-092): when set, the badge renders the violet gem icon instead of the
 * severity NAG glyph. No runtime assertion enforces the exclusivity — callers
 * only ever set one or the other by construction.
 */
export interface SquareMarker {
  square: string;
  severity?: FlawSeverity;
  /** Renders the violet gem badge instead of a severity glyph. */
  gem?: boolean;
  /** Optional depth label (e.g. allowed-tactic depth) rendered top-left. */
  label?: string;
  /** Fill color for the depth label. Defaults to white. */
  labelColor?: string;
}

// Depth-label geometry. Anchored to the square's TOP-LEFT corner, and capped at
// DEPTH_LABEL_MAX_PX so the number reads smaller on the large desktop board while
// keeping its size on the smaller mini/mobile boards (where DEPTH_LABEL_FONT ×
// sqSize stays under the cap).
const DEPTH_LABEL_FONT = 0.55; // fraction of a square; the cap below shrinks big boards
const DEPTH_LABEL_MAX_PX = 22; // absolute font ceiling (≈ small-board square × 0.55)
const DEPTH_LABEL_OUTLINE_RATIO = 0.16; // stroke width as a fraction of the font px
const DEPTH_LABEL_DEFAULT_FILL = 'white';
const DEPTH_LABEL_CORNER_INSET = 0.08; // inset from the corner so the badge clears the piece

// Severity corner-marker geometry. GLYPH_VIEWBOX_DIAMETER is the SeverityGlyphIcon
// circle diameter (r=11 in a 24-unit viewBox) so font sizing reuses SEVERITY_GLYPH ratios.
// Small (mini) boards get a bigger radius so the glyph stays legible, and the badge
// is pulled onto the square's top-right corner so it straddles (overlaps) it rather
// than sitting fully inside (Quick 260627-r9g follow-up).
const SMALL_BOARD_SQ_PX = 40; // squares narrower than this are mini boards
const MARKER_RADIUS = 0.18; // fraction of a square — large boards (analysis)
const MARKER_RADIUS_SMALL = 0.24; // mini boards (games card) — bumped for legibility, but kept compact
const MARKER_CORNER_OVERLAP = 0.5; // center pulled back from the corner by this × r
const GLYPH_VIEWBOX_DIAMETER = 22;
const MARKER_STROKE = 'rgba(0, 0, 0, 0.5)';
// Gem icon size as a fraction of the badge circle's diameter — sized so the
// icon sits inside the stroke rather than touching the circle's edge.
const GEM_ICON_DIAMETER_RATIO = 0.8;

/** A depth-badge number anchored to a square's TOP-LEFT corner. */
export function DepthLabel({
  square,
  label,
  color,
  sqSize,
  flipped,
}: {
  square: string;
  label: string;
  color?: string;
  sqSize: number;
  flipped: boolean;
}) {
  const [tx, ty] = squareToCoords(square, flipped);
  const bx = (tx - 0.5 + DEPTH_LABEL_CORNER_INSET) * sqSize;
  const by = (ty - 0.5 + DEPTH_LABEL_CORNER_INSET) * sqSize;
  const fontPx = Math.min(DEPTH_LABEL_FONT * sqSize, DEPTH_LABEL_MAX_PX);
  return (
    <text
      x={bx}
      y={by}
      fill={color ?? DEPTH_LABEL_DEFAULT_FILL}
      stroke="black"
      strokeWidth={DEPTH_LABEL_OUTLINE_RATIO * fontPx}
      paintOrder="stroke"
      fontSize={fontPx}
      fontWeight="700"
      textAnchor="start"
      dominantBaseline="hanging"
    >
      {label}
    </text>
  );
}

/** A severity glyph badge (??/?/!?) drawn in a square's top-right corner. */
function SquareMarkerBadge({
  marker,
  sqSize,
  flipped,
}: {
  marker: SquareMarker;
  sqSize: number;
  flipped: boolean;
}) {
  const [tx, ty] = squareToCoords(marker.square, flipped);
  const radiusFraction = sqSize < SMALL_BOARD_SQ_PX ? MARKER_RADIUS_SMALL : MARKER_RADIUS;
  const r = radiusFraction * sqSize;
  // Pull the badge center back from the square's top-right corner by half a radius so
  // it straddles (overlaps) the corner instead of sitting fully inside the square.
  const cornerX = (tx + 0.5) * sqSize;
  const cornerY = (ty - 0.5) * sqSize;
  const cx = cornerX - r * MARKER_CORNER_OVERLAP;
  const cy = cornerY + r * MARKER_CORNER_OVERLAP;

  if (marker.gem) {
    // Icon at ~80% of the circle diameter so it sits inside the stroke.
    const iconSize = 2 * r * GEM_ICON_DIAMETER_RATIO;
    return (
      <g>
        <circle cx={cx} cy={cy} r={r} fill={GEM_GLYPH.color} stroke={MARKER_STROKE} strokeWidth={1} />
        <Gem
          x={cx - iconSize / 2}
          y={cy - iconSize / 2}
          width={iconSize}
          height={iconSize}
          stroke="#fff"
        />
      </g>
    );
  }

  // Severity-less markers are only possible when `gem` is set (handled above,
  // and mutually exclusive by construction) — guard defensively rather than
  // indexing SEVERITY_GLYPH with an undefined key.
  if (!marker.severity) return null;
  const glyph = SEVERITY_GLYPH[marker.severity];
  // Reuse SeverityGlyphIcon's font-to-diameter ratio so the on-board glyph matches.
  const fontPx = (glyph.fontSize / GLYPH_VIEWBOX_DIAMETER) * (2 * r);
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={glyph.color} stroke={MARKER_STROKE} strokeWidth={1} />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#fff"
        fontFamily="ui-sans-serif, system-ui, sans-serif"
        fontWeight="700"
        fontSize={fontPx}
      >
        {glyph.symbol}
      </text>
    </g>
  );
}

/** Renders the severity glyph (top-right) plus its optional depth label (top-left). */
export function SquareMarkerGroup({
  marker,
  sqSize,
  flipped,
}: {
  marker: SquareMarker;
  sqSize: number;
  flipped: boolean;
}) {
  return (
    <g>
      <SquareMarkerBadge marker={marker} sqSize={sqSize} flipped={flipped} />
      {marker.label && (
        <DepthLabel
          square={marker.square}
          label={marker.label}
          color={marker.labelColor}
          sqSize={sqSize}
          flipped={flipped}
        />
      )}
    </g>
  );
}
