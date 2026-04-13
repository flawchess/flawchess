/**
 * Compact diverging bar chart for showing a signed score difference relative
 * to a baseline. Three muted background zones (poor/neutral/good) convey the
 * verdict thresholds; a solid overlay bar fills from 0 to the value in the
 * color of the zone it lands in.
 *
 * Used in the Material Breakdown table to visualize each bucket's score
 * relative to the user's overall score. The neutral zone is configurable per
 * row so expectations can shift with material context (e.g. when converting
 * material, the neutral band sits higher than when recovering).
 */

import { GAUGE_DANGER, GAUGE_NEUTRAL, GAUGE_SUCCESS } from '@/lib/theme';

// Bar domain: values beyond +/- DOMAIN are clamped to the edge.
// 0.40 covers realistic score-diff ranges without making typical values look tiny.
const DOMAIN = 0.40;

// Default neutral zone: -0.10 to 0 (slight underperformance vs overall).
const DEFAULT_NEUTRAL_MIN = -0.10;
const DEFAULT_NEUTRAL_MAX = 0;

// Background zone tint — muted but visible enough to read the zones clearly.
const ZONE_OPACITY = 0.35;

// Tolerance below which two zone boundaries are treated as coincident
// (used to suppress a redundant tick where a neutral boundary meets zero).
const BOUNDARY_EPSILON = 1e-6;

interface MiniBulletChartProps {
  /** Signed difference to visualize (e.g. row_score - overall_score). */
  value: number;
  /** Lower bound of the neutral zone. Default -0.10. */
  neutralMin?: number;
  /** Upper bound of the neutral zone. Default 0. */
  neutralMax?: number;
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
  neutralMin = DEFAULT_NEUTRAL_MIN,
  neutralMax = DEFAULT_NEUTRAL_MAX,
  ariaLabel,
  heightClass = 'h-5',
  valueHeightClass = 'h-2',
}: MiniBulletChartProps) {
  const clamped = Math.max(-DOMAIN, Math.min(DOMAIN, value));

  // Map domain value to percent position (0% = left edge, 100% = right edge).
  const toPct = (v: number): number => ((v + DOMAIN) / (2 * DOMAIN)) * 100;
  const zeroPct = toPct(0);
  const neutralMinPct = toPct(Math.max(-DOMAIN, neutralMin));
  const neutralMaxPct = toPct(Math.min(DOMAIN, neutralMax));
  const markerPct = toPct(clamped);

  // Fill color follows the zone the raw (unclamped) value falls into.
  let fillColor: string;
  if (value >= neutralMax) {
    fillColor = GAUGE_SUCCESS;
  } else if (value >= neutralMin) {
    fillColor = GAUGE_NEUTRAL;
  } else {
    fillColor = GAUGE_DANGER;
  }

  // Overlay bar spans from zero to the clamped value.
  const barLeft = value >= 0 ? zeroPct : markerPct;
  const barRight = value >= 0 ? markerPct : zeroPct;
  const barWidth = Math.max(0, barRight - barLeft);

  // Suppress ticks that coincide with the zero reference line.
  const showNeutralMinTick = Math.abs(neutralMin) > BOUNDARY_EPSILON;
  const showNeutralMaxTick = Math.abs(neutralMax) > BOUNDARY_EPSILON;

  return (
    <div
      className={`relative ${heightClass} w-full min-w-[80px] overflow-hidden rounded-sm bg-muted/20`}
      role="img"
      aria-label={ariaLabel ?? `Score difference ${formatSigned(value)}`}
      data-testid="mini-bullet-chart"
    >
      {/* Background zones: poor | neutral | good */}
      <div className="absolute inset-0 flex">
        <div
          className="h-full"
          style={{
            width: `${neutralMinPct}%`,
            backgroundColor: GAUGE_DANGER,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${neutralMaxPct - neutralMinPct}%`,
            backgroundColor: GAUGE_NEUTRAL,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${100 - neutralMaxPct}%`,
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
      {/* Neutral zone boundary ticks — subtle, only shown when distinct from zero */}
      {showNeutralMinTick && (
        <div
          className="absolute top-0 bottom-0 w-px bg-gray-700"
          style={{ left: `${neutralMinPct}%` }}
        />
      )}
      {showNeutralMaxTick && (
        <div
          className="absolute top-0 bottom-0 w-px bg-gray-700"
          style={{ left: `${neutralMaxPct}%` }}
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
