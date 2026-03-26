/**
 * Reusable SVG semicircle gauge component for endgame performance metrics.
 * Renders a half-circle arc with a fill proportional to value/maxValue.
 */

const GAUGE_R = 72;
const GAUGE_CX = 100;
const GAUGE_CY = 90;
const ARC_LENGTH = Math.PI * GAUGE_R;

// Arc path: left endpoint → right endpoint via semicircle
const ARC_D = `M ${GAUGE_CX - GAUGE_R} ${GAUGE_CY} A ${GAUGE_R} ${GAUGE_R} 0 0 1 ${GAUGE_CX + GAUGE_R} ${GAUGE_CY}`;

function getGaugeColor(pct: number): string {
  if (pct >= 0.9) return 'oklch(0.55 0.17 145)';  // green
  if (pct >= 0.7) return 'oklch(0.65 0.18 80)';   // amber
  return 'oklch(0.55 0.20 25)';                    // red
}

interface EndgameGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
}

export function EndgameGauge({ value, maxValue = 100, label }: EndgameGaugeProps) {
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
        {/* Background arc */}
        <path
          d={ARC_D}
          fill="none"
          stroke="oklch(0.85 0 0 / 0.4)"
          strokeWidth={16}
          strokeLinecap="round"
        />
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
      <p className="text-xs text-muted-foreground text-center mt-1">{label}</p>
    </div>
  );
}
