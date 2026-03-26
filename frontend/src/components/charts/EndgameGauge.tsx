/**
 * Reusable SVG semicircle gauge component for endgame performance metrics.
 * Renders a half-circle arc with a fill proportional to value/maxValue.
 * Colored zone segments (red/yellow/green) are rendered as background hints.
 * The label is no longer rendered inside this component — the parent must render labels above the gauge.
 */

const GAUGE_R = 72;
const GAUGE_CX = 100;
const GAUGE_CY = 90;
const ARC_LENGTH = Math.PI * GAUGE_R;

// Arc path: left endpoint → right endpoint via semicircle
const ARC_D = `M ${GAUGE_CX - GAUGE_R} ${GAUGE_CY} A ${GAUGE_R} ${GAUGE_R} 0 0 1 ${GAUGE_CX + GAUGE_R} ${GAUGE_CY}`;

function getGaugeColor(pct: number): string {
  if (pct >= 0.8) return 'oklch(0.55 0.17 145)';  // green
  if (pct >= 0.6) return 'oklch(0.65 0.18 80)';   // amber
  return 'oklch(0.55 0.20 25)';                    // red
}

/**
 * Compute a partial arc path using strokeDasharray/strokeDashoffset to fill only
 * the [from, to] fraction of the semicircular arc (both in 0-1 range).
 * Returns { strokeDasharray, strokeDashoffset } style props for a <path d={ARC_D}>.
 */
function zoneSegmentStyle(from: number, to: number): { strokeDasharray: string; strokeDashoffset: number } {
  const segLength = (to - from) * ARC_LENGTH;
  const offset = from * ARC_LENGTH;
  // dasharray: [segment length] [rest of arc] — positions the dash at [from, to]
  return {
    strokeDasharray: `${segLength} ${ARC_LENGTH - segLength}`,
    strokeDashoffset: -offset,
  };
}

export interface GaugeZone {
  from: number; // 0-1 fraction
  to: number;   // 0-1 fraction
  color: string;
}

export const DEFAULT_GAUGE_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.6,  color: 'oklch(0.55 0.20 25)' },   // red
  { from: 0.6,  to: 0.8,  color: 'oklch(0.65 0.18 80)' },   // amber
  { from: 0.8,  to: 1.0,  color: 'oklch(0.55 0.17 145)' },  // green
];

interface EndgameGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
  zones?: GaugeZone[];
}

export function EndgameGauge({ value, maxValue = 100, label, zones = DEFAULT_GAUGE_ZONES }: EndgameGaugeProps) {
  // Clamp arc fill to [0, 1] even if value exceeds maxValue (arc never overflows)
  const pct = Math.max(0, Math.min(value / maxValue, 1));
  const offset = ARC_LENGTH * (1 - pct);
  const color = getGaugeColor(pct);
  const testId = `gauge-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="flex flex-col items-center" data-testid={testId}>
      <svg
        viewBox="0 0 200 110"
        className="w-full max-w-[200px]"
        aria-label={`${label}: ${value.toFixed(0)}%`}
      >
        {/* Zone segment arcs — low opacity background hints */}
        {zones.map((zone) => {
          const style = zoneSegmentStyle(zone.from, zone.to);
          return (
            <path
              key={`${zone.from}-${zone.to}`}
              d={ARC_D}
              fill="none"
              stroke={zone.color}
              strokeOpacity={0.25}
              strokeWidth={16}
              strokeLinecap="butt"
              strokeDasharray={style.strokeDasharray}
              strokeDashoffset={style.strokeDashoffset}
            />
          );
        })}
        {/* Foreground arc — strokeDashoffset controls fill amount */}
        <path
          d={ARC_D}
          fill="none"
          stroke={color}
          strokeWidth={16}
          strokeLinecap="round"
          strokeDasharray={ARC_LENGTH}
          strokeDashoffset={offset}
        />
        {/* Value text — shows true value even when arc is capped */}
        <text
          x={GAUGE_CX}
          y={GAUGE_CY - 8}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={22}
          fontWeight={600}
          fill="currentColor"
        >
          {value.toFixed(0)}%
        </text>
      </svg>
    </div>
  );
}
