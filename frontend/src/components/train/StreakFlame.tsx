/**
 * StreakFlame — the session-streak count drawn inside a 3-layer flame
 * (SEED-181, sketch 005 variant A "Concentric"): one silhouette repeated at
 * 100/76/56% scale, red outer, orange middle, yellow core, the number in the
 * wide lower bowl. Streak 0 renders an unlit grey outline flame.
 *
 * Two one-shot animations, both chosen by the caller from the arrival diff
 * (`lib/streakArrival.ts`) and both skipped under prefers-reduced-motion:
 * - `ignite`: the layers grow from an ember with a lagging flicker and the
 *   number counts up from `countFrom`.
 * - `frostDelayMs`: after the freeze meter's cracks finish, a frost band
 *   sweeps the flame and it cools briefly but STAYS LIT (the streak was held).
 * - `extinguishFrom`: the streak reset. The old lit flame, still carrying its
 *   old number, shrinks down into its base and fades out, leaving the grey
 *   unlit outline with 0.
 */
import { useEffect, useId, useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { prefersReducedMotion } from '@/lib/confetti';
import {
  TRAIN_FLAME_CORE,
  TRAIN_FLAME_MIDDLE,
  TRAIN_FLAME_NUMBER,
  TRAIN_FLAME_OUTER,
  TRAIN_FLAME_UNLIT,
} from '@/lib/theme';

// Rounded bowl, tip at the top, a small lick on the left (viewBox units).
const FLAME_PATH =
  'M50 4 C58 22 82 36 85 64 C88 94 70 116 50 116 C30 116 12 102 14 76 C15 60 24 50 30 40 C32 52 38 58 42 58 C38 40 42 20 50 4 Z';
/** Scale origin: the flame's bottom center, so the layers nest at the base. */
const FLAME_ORIGIN_X = 50;
const FLAME_ORIGIN_Y = 116;
const LAYERS = [
  { scale: 1, color: TRAIN_FLAME_OUTER },
  { scale: 0.76, color: TRAIN_FLAME_MIDDLE },
  { scale: 0.56, color: TRAIN_FLAME_CORE },
] as const;
const NUMBER_Y = 95;
/** Font size (viewBox units) by digit count; 3+ digits shrink to fit the bowl. */
const NUMBER_FONT_SIZE_BY_DIGITS = [36, 34, 26] as const;

/** The count-up starts once the layers have mostly grown in. */
const COUNT_UP_DELAY_MS = 450;
const COUNT_UP_DURATION_MS = 500;

function layerTransform(scale: number): string | undefined {
  if (scale === 1) return undefined;
  return `translate(${FLAME_ORIGIN_X} ${FLAME_ORIGIN_Y}) scale(${scale}) translate(${-FLAME_ORIGIN_X} ${-FLAME_ORIGIN_Y})`;
}

/** The three filled layers of a lit flame. */
function LitLayers(): ReactElement {
  return (
    <>
      {LAYERS.map(({ scale, color }, i) => (
        <g key={i} transform={layerTransform(scale)}>
          <path d={FLAME_PATH} className={`train-flame-layer train-flame-layer-${i}`} fill={color} />
        </g>
      ))}
    </>
  );
}

function numberFontSize(n: number): number {
  const digits = Math.min(String(n).length, NUMBER_FONT_SIZE_BY_DIGITS.length);
  return NUMBER_FONT_SIZE_BY_DIGITS[digits - 1]!;
}

/** Counts from `from` to `to` once on mount; returns `to` immediately when disabled. */
function useCountUp(from: number, to: number, enabled: boolean): number {
  const [value, setValue] = useState(enabled ? from : to);

  useEffect(() => {
    if (!enabled) return;
    let frame = 0;
    const timer = setTimeout(() => {
      const start = performance.now();
      const step = (now: number): void => {
        const progress = Math.min(1, (now - start) / COUNT_UP_DURATION_MS);
        setValue(Math.round(from + (to - from) * progress));
        if (progress < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    }, COUNT_UP_DELAY_MS);
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [from, to, enabled]);

  return enabled ? value : to;
}

export interface StreakFlameProps {
  count: number;
  /** Play the ignite animation, counting up from `countFrom`. */
  ignite?: boolean;
  countFrom?: number;
  /** Sweep frost over the flame after this delay (freezes were used). */
  frostDelayMs?: number | null;
  /** Streak reset: the lit flame showing this old count goes out first. */
  extinguishFrom?: number | null;
  /** Start the extinguish after this delay (the last freeze cracks first). */
  extinguishDelayMs?: number;
  className?: string;
}

export function StreakFlame({
  count,
  ignite = false,
  countFrom = count,
  frostDelayMs = null,
  extinguishFrom = null,
  extinguishDelayMs = 0,
  className,
}: StreakFlameProps): ReactElement {
  const [animate] = useState(() => !prefersReducedMotion());
  const shown = useCountUp(countFrom, count, ignite && animate);
  // useId returns colon/guillemet-wrapped ids; strip them for url(#…) references.
  const clipId = `streak-flame-clip-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const lit = count > 0;
  const frost = animate && frostDelayMs !== null && lit;
  const extinguish = animate && extinguishFrom !== null && !lit;
  let style: CSSProperties | undefined;
  // The cool-down on the flame body reads the frost delay; the svg itself must
  // not take it, or a simultaneous ignite glow would wait for the frost.
  if (frost) style = { '--train-frost-delay': `${frostDelayMs}ms` } as CSSProperties;
  if (extinguish) style = { '--train-extinguish-delay': `${extinguishDelayMs}ms` } as CSSProperties;

  return (
    <svg
      viewBox="0 -2 100 122"
      role="img"
      aria-label={`Session streak: ${count}`}
      data-testid="train-streak-flame"
      data-lit={lit}
      className={cn(
        'block overflow-visible',
        animate && ignite && lit && 'train-flame-ignite',
        frost && 'train-flame-frosted',
        extinguish && 'train-flame-extinguished',
        className,
      )}
      style={style}
    >
      <defs>
        <clipPath id={clipId}>
          <path d={FLAME_PATH} />
        </clipPath>
        <linearGradient id={`${clipId}-frost`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="white" stopOpacity="0" />
          <stop offset="0.5" stopColor="oklch(0.95 0.05 230)" stopOpacity="0.85" />
          <stop offset="1" stopColor="white" stopOpacity="0" />
        </linearGradient>
      </defs>
      <g className="train-flame-body">
        {lit ? (
          <LitLayers />
        ) : (
          // Unlit: only the outer silhouette, as a grey outline.
          <path
            d={FLAME_PATH}
            className="train-flame-unlit"
            fill="none"
            stroke={TRAIN_FLAME_UNLIT}
            strokeWidth={3.5}
          />
        )}
      </g>
      {extinguish && (
        <g className="train-flame-dying" data-testid="train-streak-extinguish">
          <LitLayers />
          <text
            x="50"
            y={NUMBER_Y}
            textAnchor="middle"
            dominantBaseline="central"
            className="font-brand"
            fontWeight={700}
            fontSize={numberFontSize(extinguishFrom)}
            fill={TRAIN_FLAME_NUMBER}
          >
            {extinguishFrom}
          </text>
        </g>
      )}
      {frost && (
        <g clipPath={`url(#${clipId})`}>
          <rect
            className="train-flame-frost"
            x="-10"
            y="-70"
            width="120"
            height="70"
            fill={`url(#${clipId}-frost)`}
            style={{ animationDelay: `${frostDelayMs}ms` }}
          />
        </g>
      )}
      <text
        x="50"
        y={NUMBER_Y}
        textAnchor="middle"
        dominantBaseline="central"
        className={cn('font-brand', extinguish && 'train-flame-unlit')}
        fontWeight={700}
        fontSize={numberFontSize(shown)}
        fill={lit ? TRAIN_FLAME_NUMBER : TRAIN_FLAME_UNLIT}
        data-testid="train-streak-count"
      >
        {shown}
      </text>
    </svg>
  );
}
