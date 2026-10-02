/**
 * FreezeMeter — the 0-7 `shield_level` buffer as snowflake "freezes"
 * (SEED-181, sketch 005: plain stroke snowflake, icy blue when held, grey
 * outline when empty). Filled vs empty differs in stroke weight as well as
 * color, so the distinction survives a greyscale render.
 *
 * One-shot animations from the arrival diff, skipped under reduced motion:
 * - `usedCount`: the top `usedCount` empty slots (the freezes spent since the
 *   last visit) shake and split into two falling halves, staggered.
 * - `earnedCount`: the top `earnedCount` held slots pop in with a ring,
 *   after `earnedDelayMs` (so they land after a simultaneous flame ignite).
 */
import { useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { Snowflake } from 'lucide-react';
import { cn } from '@/lib/utils';
import { prefersReducedMotion } from '@/lib/confetti';
import { FREEZE_CAP, FREEZE_CRACK_STAGGER_MS } from '@/lib/streakArrival';
import { TRAIN_FREEZE_COLOR } from '@/lib/theme';

const FREEZE_EARNED_STAGGER_MS = 250;

const HELD_STROKE = 2.4;
const EMPTY_STROKE = 1.6;

export interface FreezeMeterProps {
  freezes: number;
  usedCount?: number;
  earnedCount?: number;
  earnedDelayMs?: number;
  className?: string;
}

function delayStyle(ms: number): CSSProperties {
  return { animationDelay: `${ms}ms` };
}

export function FreezeMeter({
  freezes,
  usedCount = 0,
  earnedCount = 0,
  earnedDelayMs = 0,
  className,
}: FreezeMeterProps): ReactElement {
  const [animate] = useState(() => !prefersReducedMotion());

  return (
    <div
      role="img"
      aria-label={`Freezes: ${freezes} of ${FREEZE_CAP}`}
      data-testid="train-shield-meter"
      data-filled-count={freezes}
      className={cn('flex items-center gap-0.5', className)}
    >
      {Array.from({ length: FREEZE_CAP }, (_, i) => {
        const held = i < freezes;
        // Spent slots crack top-down: the highest spent slot goes first.
        const crackOrder = freezes + usedCount - 1 - i;
        const cracking = animate && !held && crackOrder >= 0 && crackOrder < usedCount;
        const earnedOrder = i - (freezes - earnedCount);
        const earning = animate && held && earnedOrder >= 0;
        return (
          <span
            key={i}
            data-testid="train-freeze-slot"
            data-filled={held}
            className={cn('relative inline-flex size-4', earning && 'train-freeze-popin')}
            style={earning ? delayStyle(earnedDelayMs + earnedOrder * FREEZE_EARNED_STAGGER_MS) : undefined}
          >
            <Snowflake
              aria-hidden="true"
              className={cn('size-4', !held && 'text-muted-foreground/50')}
              strokeWidth={held ? HELD_STROKE : EMPTY_STROKE}
              style={held ? { color: TRAIN_FREEZE_COLOR } : undefined}
            />
            {cracking &&
              (['left', 'right'] as const).map((side) => (
                <Snowflake
                  key={side}
                  aria-hidden="true"
                  className={`train-freeze-half train-freeze-half-${side} absolute inset-0 size-4`}
                  strokeWidth={HELD_STROKE}
                  style={{
                    color: TRAIN_FREEZE_COLOR,
                    ...delayStyle(crackOrder * FREEZE_CRACK_STAGGER_MS),
                  }}
                />
              ))}
          </span>
        );
      })}
    </div>
  );
}
