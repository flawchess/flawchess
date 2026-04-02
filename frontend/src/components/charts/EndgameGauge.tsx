/**
 * Reusable 240-degree SVG gauge component for endgame performance metrics.
 * Replaces the old Recharts PieChart semicircle — now a pure SVG arc with:
 *   - 240° sweep (gap at the bottom), rounded end caps, glass sheen overlay
 *   - Tapered kite-shaped needle colored by zone
 *
 * GaugeZone type and DEFAULT_GAUGE_ZONES are defined in @/lib/theme
 * to avoid exporting non-component values from this file (react-refresh constraint).
 */

import { useId } from 'react';
import { type GaugeZone, DEFAULT_GAUGE_ZONES } from '@/lib/theme';

// Re-export GaugeZone type for callers who need it without importing from theme directly
export type { GaugeZone };

// ─── Layout constants ──────────────────────────────────────────────────────────
const GAUGE_WIDTH = 200;
const CX = GAUGE_WIDTH / 2;
const CY = 82;                   // arc center — placed so top (CY-OUTER_R≈10) and bottom caps (~123) both fit
const INNER_R = 52;
const OUTER_R = 72;
const TRACK_WIDTH = OUTER_R - INNER_R;  // 20px
const MID_R = (INNER_R + OUTER_R) / 2;  // 62 — center of the track
const CAP_R = TRACK_WIDTH / 2;          // 10 — radius of terminal rounded caps

// The arc spans 240 degrees. Gap is 120° split evenly at the bottom (60° each side).
// In standard math (0° = right, CCW positive), the arc goes from 210° to 330°
// (the 120° gap spans 210° → 330° going clockwise through the bottom).
// In SVG (0° = right, CW positive), we go from -210° to 30° — easier expressed as:
//   startAngle = 150° (bottom-left)
//   endAngle   = 390° (= 150° + 240°, bottom-right)
// We convert to radians for path math.
const ARC_START_DEG = 150;     // left terminal of the arc (° from 3-o'clock, clockwise)
const ARC_TOTAL_DEG = 240;     // full sweep in degrees

// Height: bottom-most point is the rounded cap at ≈ CY + (INNER_R+OUTER_R)/2*sin(30°) + TRACK_WIDTH/2 ≈ 123
const GAUGE_HEIGHT = 130;

// Radial gradient stop positions for 3D convex cross-section effect.
// Centered at (CX, CY) with r=OUTER_R; visible track = [INNER_R/OUTER_R .. 100%].
// Highlight near the OUTER edge simulates top-lit rounded surface.
const GLASS_INNER_PCT = `${((INNER_R / OUTER_R) * 100).toFixed(1)}%`;                           // ≈72.2% — inner edge
const GLASS_MID_PCT = `${(((INNER_R + TRACK_WIDTH * 0.4) / OUTER_R) * 100).toFixed(1)}%`;       // ≈83.3% — transition
const GLASS_HIGHLIGHT_PCT = `${(((INNER_R + TRACK_WIDTH * 0.8) / OUTER_R) * 100).toFixed(1)}%`; // ≈94.4% — highlight

// ─── Helpers ───────────────────────────────────────────────────────────────────

/** Convert SVG-angle degrees (0=right, CW) to (x, y) on the given radius. */
function polarToXY(cx: number, cy: number, r: number, angleDeg: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/**
 * Build an SVG donut-arc path for a segment that spans [startDeg, endDeg] (SVG degrees).
 * Returns a closed `<path d="...">` string.
 */
function describeArc(
  cx: number,
  cy: number,
  innerR: number,
  outerR: number,
  startDeg: number,
  endDeg: number,
): string {
  const s1 = polarToXY(cx, cy, outerR, startDeg);
  const e1 = polarToXY(cx, cy, outerR, endDeg);
  const s2 = polarToXY(cx, cy, innerR, endDeg);
  const e2 = polarToXY(cx, cy, innerR, startDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;

  return [
    `M ${s1.x} ${s1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y}`,
    `L ${s2.x} ${s2.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${e2.x} ${e2.y}`,
    'Z',
  ].join(' ');
}

/**
 * Like describeArc but with semicircular caps at both terminals.
 * The caps have radius CAP_R and bulge outward (away from arc center into the gap).
 */
function describeRoundedArc(
  cx: number,
  cy: number,
  innerR: number,
  outerR: number,
  startDeg: number,
  endDeg: number,
): string {
  const capR = (outerR - innerR) / 2;
  const s1 = polarToXY(cx, cy, outerR, startDeg);
  const e1 = polarToXY(cx, cy, outerR, endDeg);
  const s2 = polarToXY(cx, cy, innerR, endDeg);
  const e2 = polarToXY(cx, cy, innerR, startDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;

  return [
    `M ${s1.x} ${s1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y}`,
    `A ${capR} ${capR} 0 0 1 ${s2.x} ${s2.y}`,           // end cap: outer→inner, bulges outward
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${e2.x} ${e2.y}`,
    `A ${capR} ${capR} 0 0 1 ${s1.x} ${s1.y}`,           // start cap: inner→outer, bulges outward
    'Z',
  ].join(' ');
}

/** Like describeRoundedArc but only the START terminal is rounded; the end is flat. */
function describeStartRoundedArc(
  cx: number,
  cy: number,
  innerR: number,
  outerR: number,
  startDeg: number,
  endDeg: number,
): string {
  const capR = (outerR - innerR) / 2;
  const s1 = polarToXY(cx, cy, outerR, startDeg);
  const e1 = polarToXY(cx, cy, outerR, endDeg);
  const s2 = polarToXY(cx, cy, innerR, endDeg);
  const e2 = polarToXY(cx, cy, innerR, startDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;

  return [
    `M ${s1.x} ${s1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y}`,
    `L ${s2.x} ${s2.y}`,                                     // flat end
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${e2.x} ${e2.y}`,
    `A ${capR} ${capR} 0 0 1 ${s1.x} ${s1.y}`,               // start cap: rounded
    'Z',
  ].join(' ');
}

/** Fraction [0,1] → SVG angle in degrees. */
function fractionToAngleDeg(frac: number): number {
  return ARC_START_DEG + frac * ARC_TOTAL_DEG;
}

/** Return the zone color for a given fraction. */
function getZoneColor(pct: number, zones: GaugeZone[]): string {
  for (let i = zones.length - 1; i >= 0; i--) {
    // safe: loop bounds guarantee i is a valid index
    if (pct >= zones[i]!.from) return zones[i]!.color;
  }
  // safe: zones is a non-empty array defined by callers
  return zones[0]!.color;
}

// ─── Sub-components ────────────────────────────────────────────────────────────

/**
 * Gauge arc with rounded terminals and a 3D glass progress fill.
 *
 * Strategy: mute the entire arc first, then redraw the progress portion
 * (zones + glass) on top. This eliminates all overlay alignment issues
 * at the needle boundary and end cap.
 */
function GaugeArcs({ zones, glassId, pct }: { zones: GaugeZone[]; glassId: string; pct: number }) {
  const clipId = `${glassId}-clip`;

  const segments = zones.map((zone) => {
    const startDeg = fractionToAngleDeg(zone.from);
    const endDeg = fractionToAngleDeg(zone.to);
    return { color: zone.color, path: describeArc(CX, CY, INNER_R, OUTER_R, startDeg, endDeg) };
  });

  // Rounded full-arc shape for clipping (rounds the gauge terminals)
  const arcStartDeg = fractionToAngleDeg(0);
  const arcEndDeg = fractionToAngleDeg(1);
  const roundedClip = describeRoundedArc(CX, CY, INNER_R, OUTER_R, arcStartDeg, arcEndDeg);

  // Cap fill positions — circles at terminals fill the rounded cap areas
  const capStart = polarToXY(CX, CY, MID_R, arcStartDeg);
  const capEnd = polarToXY(CX, CY, MID_R, arcEndDeg);

  // Progress zone segments: zones clipped to [0, pct] range
  const progressSegments = pct > 0.01 ? zones.flatMap((zone) => {
    const zoneEnd = Math.min(zone.to, pct);
    if (zoneEnd <= zone.from) return [];
    const startDeg = fractionToAngleDeg(zone.from);
    const endDeg = fractionToAngleDeg(zoneEnd);
    return [{ color: zone.color, path: describeArc(CX, CY, INNER_R, OUTER_R, startDeg, endDeg) }];
  }) : [];

  // Glass progress fill: rounded start covers the start cap area,
  // flat end at needle so the glass doesn't overshoot.
  const needleDeg = fractionToAngleDeg(pct);
  const glassPath = pct > 0.01
    ? describeStartRoundedArc(CX, CY, INNER_R, OUTER_R, arcStartDeg, needleDeg)
    : null;

  return (
    <g>
      <defs>
        <clipPath id={clipId}>
          <path d={roundedClip} />
        </clipPath>
      </defs>

      <g clipPath={`url(#${clipId})`}>
        {/* Layer 1: Full arc at reduced opacity (muted background) */}
        <g opacity="0.3">
          {/* safe: zones is always non-empty (callers provide gauge zone definitions) */}
          <circle cx={capStart.x} cy={capStart.y} r={CAP_R} fill={zones[0]!.color} />
          <circle cx={capEnd.x} cy={capEnd.y} r={CAP_R} fill={zones[zones.length - 1]!.color} />
          {segments.map((seg, i) => (
            <path key={i} d={seg.path} fill={seg.color} />
          ))}
        </g>

        {/* Layer 2: Progress portion at full opacity */}
        {/* safe: zones is always non-empty (callers provide gauge zone definitions) */}
        <circle cx={capStart.x} cy={capStart.y} r={CAP_R} fill={zones[0]!.color} />
        {progressSegments.map((seg, i) => (
          <path key={`p-${i}`} d={seg.path} fill={seg.color} />
        ))}

        {/* Layer 3: Glass overlay — rounded start covers cap, rounded end tapers at needle */}
        {glassPath && <path d={glassPath} fill={`url(#${glassId})`} />}
      </g>
    </g>
  );
}

/** Tapered needle: a narrow kite shape pointing along the value angle. */
function Needle({ pct, color }: { pct: number; color: string }) {
  const angleDeg = fractionToAngleDeg(pct);
  const rad = (angleDeg * Math.PI) / 180;

  // Tip: just inside the inner arc
  const tipR = INNER_R - 4;
  const tipX = CX + tipR * Math.cos(rad);
  const tipY = CY + tipR * Math.sin(rad);

  // Base center: 8px from the pivot center along the needle axis (behind the pivot)
  const baseR = 8;
  const baseCX = CX - baseR * Math.cos(rad);
  const baseCY = CY - baseR * Math.sin(rad);

  // Perpendicular half-width at the base: ±3px
  const HALF_BASE = 3;
  const perpX = -Math.sin(rad);
  const perpY = Math.cos(rad);
  const lx = baseCX + perpX * HALF_BASE;
  const ly = baseCY + perpY * HALF_BASE;
  const rx = baseCX - perpX * HALF_BASE;
  const ry = baseCY - perpY * HALF_BASE;

  const d = `M ${tipX} ${tipY} L ${lx} ${ly} L ${rx} ${ry} Z`;

  return (
    <g filter="drop-shadow(0 1px 2px rgba(0,0,0,0.3))">
      <path d={d} fill={color} />
      <circle cx={CX} cy={CY} r={5} fill={color} />
    </g>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

interface EndgameGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
  zones?: GaugeZone[];
}

export function EndgameGauge({ value, maxValue = 100, label, zones = DEFAULT_GAUGE_ZONES }: EndgameGaugeProps) {
  const uid = useId();
  const glassId = `gauge-glass-${uid.replace(/:/g, '')}`;

  const pct = Math.max(0, Math.min(value / maxValue, 1));
  const needleColor = getZoneColor(pct, zones);
  const testId = `gauge-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="flex flex-col items-center" data-testid={testId}>
      <svg
        width={GAUGE_WIDTH}
        height={GAUGE_HEIGHT}
        viewBox={`0 0 ${GAUGE_WIDTH} ${GAUGE_HEIGHT}`}
        aria-label={`${label}: ${value.toFixed(0)}%`}
        className="pointer-events-none"
      >
        <defs>
          {/*
           * Radial glass gradient: highlight near the OUTER edge of the track,
           * subtle shadow at the inner edge. Simulates top-lit convex surface.
           */}
          <radialGradient id={glassId} cx={CX} cy={CY} r={OUTER_R} gradientUnits="userSpaceOnUse">
            <stop offset={GLASS_INNER_PCT}     stopColor="rgba(0,0,0,0.06)" />
            <stop offset={GLASS_MID_PCT}       stopColor="rgba(255,255,255,0.02)" />
            <stop offset={GLASS_HIGHLIGHT_PCT} stopColor="rgba(255,255,255,0.20)" />
            <stop offset="100%"                stopColor="rgba(0,0,0,0.04)" />
          </radialGradient>
        </defs>

        <GaugeArcs zones={zones} glassId={glassId} pct={pct} />
        <Needle pct={pct} color={needleColor} />

        {/* Percentage inside the gauge, below the needle pivot */}
        <text
          x={CX}
          y={CY + 22}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={needleColor}
          fontSize="18"
          fontWeight="600"
        >
          {value.toFixed(0)}%
        </text>
      </svg>
    </div>
  );
}
