/**
 * BlunderCheckTimerRing: the drill's per-move countdown as a big ring in the host avatar's
 * place (Phase 251 UAT: the inline "10s" read too small). The arc drains as time runs out
 * and turns from green to amber to red in equal thirds of the move's time (4 s each at the
 * 12 s timer); it shakes once as the low-time sound plays, which starts as it turns red.
 *
 * While no clock runs (grading, feedback, the move + reply animation) the ring shows only
 * its track, so the slot keeps its size and the bubble never jumps.
 */

import type { ReactElement } from 'react';
import { timerZone } from '@/lib/blunderCheckDrill';
import type { TimerZone } from '@/lib/blunderCheckDrill';
import { prefersReducedMotion } from '@/lib/confetti';
import {
  BLUNDER_CHECK_TIMER_DANGER,
  BLUNDER_CHECK_TIMER_SAFE,
  BLUNDER_CHECK_TIMER_TRACK,
  BLUNDER_CHECK_TIMER_WARN,
} from '@/lib/theme';
import { cn } from '@/lib/utils';

const MS_PER_SECOND = 1000;
/** SVG geometry in viewBox units; the element itself scales with its size class. */
const VIEWBOX_SIZE = 100;
const STROKE_WIDTH = 9;
const RADIUS = (VIEWBOX_SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
/** One step of `useMoveTimer`, so the arc glides between its readings instead of jumping. */
const ARC_TRANSITION = 'stroke-dashoffset 100ms linear, stroke 200ms ease';

/** The same footprint as the bubble's avatar column it replaces, one step larger on phones. */
const RING_SIZE_CLASS = 'size-16 sm:size-20';

const ZONE_COLOR: Record<TimerZone, string> = {
  safe: BLUNDER_CHECK_TIMER_SAFE,
  warn: BLUNDER_CHECK_TIMER_WARN,
  danger: BLUNDER_CHECK_TIMER_DANGER,
};

export interface BlunderCheckTimerRingProps {
  remainingMs: number;
  /** The move's full time, so the arc shows the share left. */
  totalMs: number;
  /** False while no clock runs: the track only, no number. */
  active: boolean;
  /** True from the low-time sound on (the ring's red third): the ring shakes once. */
  shake: boolean;
}

export function BlunderCheckTimerRing({
  remainingMs,
  totalMs,
  active,
  shake,
}: BlunderCheckTimerRingProps): ReactElement {
  const fraction = active && totalMs > 0 ? Math.min(1, Math.max(0, remainingMs / totalMs)) : 0;
  const color = ZONE_COLOR[timerZone(remainingMs, totalMs)];
  const seconds = Math.ceil(remainingMs / MS_PER_SECOND);
  return (
    <div
      className={cn(
        'relative shrink-0',
        RING_SIZE_CLASS,
        active && shake && !prefersReducedMotion() && 'animate-blunder-check-timer-shake',
      )}
      data-testid="blunder-check-timer-ring"
      data-active={active ? 'true' : 'false'}
      role="timer"
      aria-label={active ? `${seconds} seconds left` : 'Timer paused'}
    >
      <svg viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`} className="size-full -rotate-90" aria-hidden="true">
        <circle
          cx={VIEWBOX_SIZE / 2}
          cy={VIEWBOX_SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={BLUNDER_CHECK_TIMER_TRACK}
          strokeWidth={STROKE_WIDTH}
        />
        {active && (
          <circle
            cx={VIEWBOX_SIZE / 2}
            cy={VIEWBOX_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - fraction)}
            style={{ transition: ARC_TRANSITION }}
          />
        )}
      </svg>
      {active && (
        <span
          className="absolute inset-0 flex items-center justify-center text-2xl font-bold tabular-nums sm:text-3xl"
          style={{ color }}
          data-testid="blunder-check-timer"
        >
          {seconds}
        </span>
      )}
    </div>
  );
}
