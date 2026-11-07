/**
 * TrainScoreBadge — the score screen's hero: a band-colored progress ring that
 * fills to the session percentage while the number counts up, popping in on
 * arrival. Under reduced motion it renders the final state straight away.
 */
import { useEffect, useState, type ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { TRAIN_RATING_BAND_COLOR } from '@/lib/theme';
import type { TrainRatingBand } from '@/lib/trainScore';

/** Long enough to read as a fill, short enough not to delay the result. */
export const SCORE_COUNT_UP_DURATION_MS = 900;

/** Opacity of the band-colored fill, as a color-mix percentage. Low enough that
 * the large percentage text stays legible on both themes. */
const BADGE_TINT_PERCENT = 14;
/** Opacity of the unfilled part of the ring, as a color-mix percentage. */
const RING_TRACK_PERCENT = 22;

/** SVG units: the viewBox is 100 wide, so the ring is about 7px at the badge's sizes. */
const RING_VIEWBOX_SIZE = 100;
const RING_STROKE_WIDTH = 5;
const RING_CENTER = RING_VIEWBOX_SIZE / 2;
const RING_RADIUS = (RING_VIEWBOX_SIZE - RING_STROKE_WIDTH) / 2;
/** `pathLength` of the arc, so its dash length is simply the percentage. */
const RING_PATH_LENGTH = 100;

function easeOutCubic(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

/** Animates from 0 to `target`. One value drives both the arc and the number, so they stay in step. */
function useCountUp(target: number, animate: boolean): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!animate) return;
    let frame = 0;
    const start = performance.now();
    const tick = (now: number): void => {
      const progress = Math.min((now - start) / SCORE_COUNT_UP_DURATION_MS, 1);
      setValue(target * easeOutCubic(progress));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, animate]);
  return animate ? value : target;
}

export function TrainScoreBadge({
  percentage,
  band,
  reducedMotion,
}: {
  percentage: number;
  band: TrainRatingBand;
  reducedMotion: boolean;
}): ReactElement {
  const color = TRAIN_RATING_BAND_COLOR[band];
  const value = useCountUp(percentage, !reducedMotion);
  return (
    <div
      className={cn(
        'relative flex size-32 shrink-0 items-center justify-center sm:size-36',
        !reducedMotion && 'animate-train-score-badge-pop',
      )}
      data-testid="train-score-badge"
      role="img"
      aria-label={`${percentage}%`}
    >
      {/* Rotated so the arc starts at 12 o'clock. */}
      <svg
        className="absolute inset-0 size-full -rotate-90"
        viewBox={`0 0 ${RING_VIEWBOX_SIZE} ${RING_VIEWBOX_SIZE}`}
        aria-hidden="true"
      >
        <circle
          cx={RING_CENTER}
          cy={RING_CENTER}
          r={RING_RADIUS}
          strokeWidth={RING_STROKE_WIDTH}
          style={{
            fill: `color-mix(in oklch, ${color} ${BADGE_TINT_PERCENT}%, transparent)`,
            stroke: `color-mix(in oklch, ${color} ${RING_TRACK_PERCENT}%, transparent)`,
          }}
        />
        {/* Skipped at 0: a round linecap would still paint a dot. */}
        {value > 0 && (
          <circle
            cx={RING_CENTER}
            cy={RING_CENTER}
            r={RING_RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={RING_STROKE_WIDTH}
            strokeLinecap="round"
            pathLength={RING_PATH_LENGTH}
            strokeDasharray={`${value} ${RING_PATH_LENGTH}`}
            data-testid="train-score-ring-arc"
          />
        )}
      </svg>
      <span
        className="relative text-4xl font-bold leading-none tabular-nums sm:text-5xl"
        data-testid="train-score-percentage"
        style={{ color }}
      >
        {Math.round(value)}%
      </span>
    </div>
  );
}
