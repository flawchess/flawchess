/**
 * Compact diverging bar chart for showing a signed score difference relative
 * to a baseline. Three muted background zones (red/amber/green) convey the
 * verdict thresholds; a solid overlay bar fills from 0 to the value in the
 * color of the zone it lands in.
 *
 * Used in the Material Breakdown table to visualize each bucket's score
 * relative to the user's overall score. The amber zone is configurable per
 * row so expectations can shift with material context (e.g. when ahead in
 * material, neutral performance is above overall, not at overall).
 */

import { GAUGE_DANGER, GAUGE_WARNING, GAUGE_SUCCESS } from '@/lib/theme';

// Bar domain: values beyond +/- DOMAIN are clamped to the edge.
// 0.30 covers realistic score-diff ranges without making typical values look tiny.
const DOMAIN = 0.30;

// Default amber zone: -0.10 to 0 (slight underperformance vs overall).
const DEFAULT_AMBER_MIN = -0.10;
const DEFAULT_AMBER_MAX = 0;

// Background zone tint — muted but visible enough to read the zones clearly.
const ZONE_OPACITY = 0.35;

// Tolerance below which two zone boundaries are treated as coincident
// (used to suppress a redundant tick where an amber boundary meets zero).
const BOUNDARY_EPSILON = 1e-6;

interface MiniBulletChartProps {
  /** Signed difference to visualize (e.g. row_score - overall_score). */
  value: number;
  /** Lower bound of the amber (neutral) zone. Default -0.10. */
  amberMin?: number;
  /** Upper bound of the amber (neutral) zone. Default 0. */
  amberMax?: number;
  /** Accessible label. Falls back to the signed numeric value. */
  ariaLabel?: string;
  /** Height class for the zone background, default h-5 (matches MiniWDLBar). */
  heightClass?: string;
  /** Height class for the foreground value bar, default h-2 (thinner than zones). */
  valueHeightClass?: string;
}

function formatSigned(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

export function MiniBulletChart({
  value,
  amberMin = DEFAULT_AMBER_MIN,
  amberMax = DEFAULT_AMBER_MAX,
  ariaLabel,
  heightClass = 'h-5',
  valueHeightClass = 'h-2',
}: MiniBulletChartProps) {
  const clamped = Math.max(-DOMAIN, Math.min(DOMAIN, value));

  // Map domain value to percent position (0% = left edge, 100% = right edge).
  const toPct = (v: number): number => ((v + DOMAIN) / (2 * DOMAIN)) * 100;
  const zeroPct = toPct(0);
  const amberMinPct = toPct(Math.max(-DOMAIN, amberMin));
  const amberMaxPct = toPct(Math.min(DOMAIN, amberMax));
  const markerPct = toPct(clamped);

  // Fill color follows the zone the raw (unclamped) value falls into.
  let fillColor: string;
  if (value >= amberMax) {
    fillColor = GAUGE_SUCCESS;
  } else if (value >= amberMin) {
    fillColor = GAUGE_WARNING;
  } else {
    fillColor = GAUGE_DANGER;
  }

  // Overlay bar spans from zero to the clamped value.
  const barLeft = value >= 0 ? zeroPct : markerPct;
  const barRight = value >= 0 ? markerPct : zeroPct;
  const barWidth = Math.max(0, barRight - barLeft);

  // Suppress ticks that coincide with the zero reference line.
  const showAmberMinTick = Math.abs(amberMin) > BOUNDARY_EPSILON;
  const showAmberMaxTick = Math.abs(amberMax) > BOUNDARY_EPSILON;

  return (
    <div
      className={`relative ${heightClass} w-full min-w-[80px] overflow-hidden rounded-sm bg-muted/20`}
      role="img"
      aria-label={ariaLabel ?? `Score difference ${formatSigned(value)}`}
      data-testid="mini-bullet-chart"
    >
      {/* Background zones: red | amber | green */}
      <div className="absolute inset-0 flex">
        <div
          className="h-full"
          style={{
            width: `${amberMinPct}%`,
            backgroundColor: GAUGE_DANGER,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${amberMaxPct - amberMinPct}%`,
            backgroundColor: GAUGE_WARNING,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${100 - amberMaxPct}%`,
            backgroundColor: GAUGE_SUCCESS,
            opacity: ZONE_OPACITY,
          }}
        />
      </div>
      {/* Zero reference line */}
      <div
        className="absolute top-0 bottom-0 w-px bg-foreground/50"
        style={{ left: `${zeroPct}%` }}
      />
      {/* Amber zone boundary ticks — subtle, only shown when distinct from zero */}
      {showAmberMinTick && (
        <div
          className="absolute top-0 bottom-0 w-px bg-gray-700"
          style={{ left: `${amberMinPct}%` }}
        />
      )}
      {showAmberMaxTick && (
        <div
          className="absolute top-0 bottom-0 w-px bg-gray-700"
          style={{ left: `${amberMaxPct}%` }}
        />
      )}
      {/* Value fill bar — thinner than zones, vertically centered */}
      <div
        className={`absolute top-1/2 -translate-y-1/2 ${valueHeightClass}`}
        style={{
          left: `${barLeft}%`,
          width: `${barWidth}%`,
          backgroundColor: fillColor,
        }}
      />
    </div>
  );
}
