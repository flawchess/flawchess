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

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

// Default bar domain: values beyond +/- DEFAULT_DOMAIN are clamped to the edge.
// 0.40 covers realistic score-diff ranges without making typical values look tiny.
// Callers can narrow the domain via the `domain` prop when the expected diff
// range is smaller (e.g. opponent-calibrated baselines where equally-rated
// players cluster near zero).
const DEFAULT_DOMAIN = 0.40;

// Default neutral zone: -0.10 to 0 (slight underperformance vs overall).
const DEFAULT_NEUTRAL_MIN = -0.10;
const DEFAULT_NEUTRAL_MAX = 0;

// Background zone tint — muted but visible enough to read the zones clearly.
const ZONE_OPACITY = 0.35;

// Tolerance below which two zone boundaries are treated as coincident
// (used to suppress a redundant tick where a neutral boundary meets zero).
const BOUNDARY_EPSILON = 1e-6;

interface MiniBulletChartProps {
  /** Signed difference to visualize (e.g. row_score - opponent_score). */
  value: number;
  /** Lower bound of the neutral zone, expressed as an offset from `center`. Default -0.10. */
  neutralMin?: number;
  /** Upper bound of the neutral zone, expressed as an offset from `center`. Default 0. */
  neutralMax?: number;
  /** Bar domain half-width (values beyond ±domain are clamped). Default 0.40. */
  domain?: number;
  /** Reference center for the chart. The reference line, neutral-zone shading,
   * bar-from-center fill, and zone-color test are all computed relative to this.
   * Default 0 (legacy zero-centered behavior — visually identical to the
   * pre-260504-my2 chart for callers that don't pass `center`). */
  center?: number;
  /** Accessible label. Falls back to the signed numeric value. */
  ariaLabel?: string;
  /** Height class for the zone background, default h-5 (matches MiniWDLBar). */
  heightClass?: string;
  /** Height class for the foreground value bar, default h-2 (thinner than zones). */
  valueHeightClass?: string;
  /** Optional 95% CI lower bound (in domain units, signed). Renders a thin whisker over the value bar when both ciLow and ciHigh are provided. */
  ciLow?: number;
  /** Optional 95% CI upper bound (in domain units, signed). Renders a thin whisker over the value bar when both ciLow and ciHigh are provided. */
  ciHigh?: number;
  /** Optional reference tick at this absolute axis position. Used to mark the
   * per-color MG-entry baseline alongside the 0 cp center reference. Rendered
   * as a thin dashed line distinct from the solid center reference. Suppressed
   * when the value falls outside the visible axis [center - domain, center + domain]. */
  tickPawns?: number;
}

function formatSigned(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

export function MiniBulletChart({
  value,
  neutralMin = DEFAULT_NEUTRAL_MIN,
  neutralMax = DEFAULT_NEUTRAL_MAX,
  domain = DEFAULT_DOMAIN,
  center = 0,
  ariaLabel,
  heightClass = 'h-5',
  valueHeightClass = 'h-2',
  ciLow,
  ciHigh,
  tickPawns,
}: MiniBulletChartProps) {
  // Axis spans [center - domain, center + domain], so the reference line and
  // neutral band sit at the visual middle regardless of `center`. With center=0
  // this reduces to the legacy [-domain, +domain] mapping.
  const axisMin = center - domain;
  const axisMax = center + domain;
  const clamped = Math.max(axisMin, Math.min(axisMax, value));

  // Map an absolute eval to its percent position along the centered axis.
  const toPct = (v: number): number => ((v - axisMin) / (2 * domain)) * 100;
  const centerPct = toPct(center);
  // Neutral-band bounds are offsets from `center`; convert to absolute eval space
  // before clamping to the chart axis.
  const absNeutralMin = center + neutralMin;
  const absNeutralMax = center + neutralMax;
  const neutralMinPct = toPct(Math.max(axisMin, absNeutralMin));
  const neutralMaxPct = toPct(Math.min(axisMax, absNeutralMax));
  const markerPct = toPct(clamped);

  // Fill color follows the zone the raw (unclamped) value falls into,
  // measured against absolute (center-shifted) bounds.
  let fillColor: string;
  if (value >= absNeutralMax) {
    fillColor = ZONE_SUCCESS;
  } else if (value >= absNeutralMin) {
    fillColor = ZONE_NEUTRAL;
  } else {
    fillColor = ZONE_DANGER;
  }

  // Overlay bar spans from the center to the clamped value.
  const barLeft = value >= center ? centerPct : markerPct;
  const barRight = value >= center ? markerPct : centerPct;
  const barWidth = Math.max(0, barRight - barLeft);

  // Suppress ticks that coincide with the center reference line.
  // (With center=0 this reduces to |neutralMin| / |neutralMax|.)
  const showNeutralMinTick = Math.abs(absNeutralMin - center) > BOUNDARY_EPSILON;
  const showNeutralMaxTick = Math.abs(absNeutralMax - center) > BOUNDARY_EPSILON;

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
            backgroundColor: ZONE_DANGER,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${neutralMaxPct - neutralMinPct}%`,
            backgroundColor: ZONE_NEUTRAL,
            opacity: ZONE_OPACITY,
          }}
        />
        <div
          className="h-full"
          style={{
            width: `${100 - neutralMaxPct}%`,
            backgroundColor: ZONE_SUCCESS,
            opacity: ZONE_OPACITY,
          }}
        />
      </div>
      {/* Center reference line */}
      <div
        className="absolute top-0 bottom-0 w-px bg-foreground/50"
        style={{ left: `${centerPct}%` }}
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
      {/* Optional per-color baseline reference tick. Distinct from the solid
        center reference: rendered as a thin dashed marker at the absolute
        axis position. Suppressed when outside the axis. */}
      {tickPawns !== undefined && tickPawns >= axisMin && tickPawns <= axisMax && (
        <div
          className="absolute top-0 bottom-0 w-px bg-foreground/30"
          style={{
            left: `${toPct(tickPawns)}%`,
            borderLeft: '1px dashed currentColor',
            backgroundColor: 'transparent',
          }}
          data-testid="mini-bullet-tick"
          aria-hidden="true"
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
      {/* CI whisker overlay — only rendered when both ciLow and ciHigh are provided */}
      {ciLow !== undefined && ciHigh !== undefined && (() => {
        const ciLowClamped = Math.max(axisMin, ciLow);
        const ciHighClamped = Math.min(axisMax, ciHigh);
        const lowOpen = ciLow < axisMin;
        const highOpen = ciHigh > axisMax;
        const ciLowPct = toPct(ciLowClamped);
        const ciHighPct = toPct(ciHighClamped);
        return (
          <>
            {/* Whisker line */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-px bg-foreground/70 pointer-events-none"
              style={{ left: `${ciLowPct}%`, width: `${ciHighPct - ciLowPct}%` }}
              data-testid="mini-bullet-whisker"
              aria-hidden="true"
            />
            {/* Left end cap (suppressed when CI extends past the left domain edge) */}
            {!lowOpen && (
              <div
                className="absolute top-1/4 bottom-1/4 w-px bg-foreground/70 pointer-events-none"
                style={{ left: `${ciLowPct}%` }}
                data-testid="mini-bullet-whisker-cap-low"
                aria-hidden="true"
              />
            )}
            {/* Right end cap (suppressed when CI extends past the right domain edge) */}
            {!highOpen && (
              <div
                className="absolute top-1/4 bottom-1/4 w-px bg-foreground/70 pointer-events-none"
                style={{ left: `${ciHighPct}%` }}
                data-testid="mini-bullet-whisker-cap-high"
                aria-hidden="true"
              />
            )}
          </>
        );
      })()}
    </div>
  );
}
