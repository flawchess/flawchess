/**
 * Reusable semicircle gauge component for endgame performance metrics.
 * Uses Recharts PieChart with a 180° arc to render colored zone segments
 * and a needle indicator for the current value.
 * The label is rendered by the parent — this component only renders the gauge.
 *
 * GaugeZone type and DEFAULT_GAUGE_ZONES are defined in @/lib/theme
 * to avoid exporting non-component values from this file (react-refresh constraint).
 */

import { PieChart, Pie, Cell } from 'recharts';
import { type GaugeZone, DEFAULT_GAUGE_ZONES } from '@/lib/theme';

// Re-export GaugeZone type for callers who need it without importing from theme directly
export type { GaugeZone };

/** Derive fill color from zones — returns the color of the zone containing pct. */
function getZoneColor(pct: number, zones: GaugeZone[]): string {
  for (let i = zones.length - 1; i >= 0; i--) {
    if (pct >= zones[i].from) return zones[i].color;
  }
  return zones[0].color;
}

const GAUGE_WIDTH = 200;
const GAUGE_HEIGHT = 110;
const CX = GAUGE_WIDTH / 2;
const CY = GAUGE_HEIGHT - 10;
const INNER_R = 55;
const OUTER_R = 72;

/** SVG needle pointing at the correct angle on the semicircle. */
function Needle({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(value / 100, 1));
  // 180° = left (0%), 0° = right (100%)
  const angle = Math.PI * (1 - pct);
  const needleLen = INNER_R - 6;
  const tipX = CX + needleLen * Math.cos(angle);
  const tipY = CY - needleLen * Math.sin(angle);

  return (
    <g>
      <line x1={CX} y1={CY} x2={tipX} y2={tipY} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      <circle cx={CX} cy={CY} r={4} fill={color} />
    </g>
  );
}

interface EndgameGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
  zones?: GaugeZone[];
}

export function EndgameGauge({ value, maxValue = 100, label, zones = DEFAULT_GAUGE_ZONES }: EndgameGaugeProps) {
  const pct = Math.max(0, Math.min(value / maxValue, 1));
  const needleColor = getZoneColor(pct, zones);
  const testId = `gauge-${label.toLowerCase().replace(/\s+/g, '-')}`;

  // Convert zones to Recharts pie data — each zone is a segment sized by its fraction
  const data = zones.map((z) => ({ value: (z.to - z.from) * 100, color: z.color }));

  return (
    <div className="flex flex-col items-center -mt-5" data-testid={testId}>
      <div className="relative pointer-events-none" style={{ width: GAUGE_WIDTH, height: GAUGE_HEIGHT }}>
        <PieChart width={GAUGE_WIDTH} height={GAUGE_HEIGHT}>
          <Pie
            data={data}
            cx={CX}
            cy={CY}
            startAngle={180}
            endAngle={0}
            innerRadius={INNER_R}
            outerRadius={OUTER_R}
            dataKey="value"
            stroke="none"
            isAnimationActive={false}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
        {/* Needle overlay via absolute-positioned SVG */}
        <svg
          viewBox={`0 0 ${GAUGE_WIDTH} ${GAUGE_HEIGHT}`}
          className="absolute inset-0"
          style={{ width: GAUGE_WIDTH, height: GAUGE_HEIGHT }}
          aria-label={`${label}: ${value.toFixed(0)}%`}
        >
          <Needle value={value} color={needleColor} />
        </svg>
      </div>
      {/* Percentage below the gauge, colored by needle zone */}
      <span className="-mt-1 text-lg font-semibold" style={{ color: needleColor }}>
        {value.toFixed(0)}%
      </span>
    </div>
  );
}
