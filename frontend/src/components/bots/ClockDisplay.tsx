import type { ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { formatClockLabel, isLowTime } from '@/lib/chessClock';
import { CLOCK_LOW_TIME_URGENT } from '@/lib/theme';

interface ClockDisplayProps {
  /** Side caption — "You" / "FlawChess Bot" per the UI-SPEC Copywriting Contract. */
  sideLabel: string;
  /** Remaining time in milliseconds. */
  remainingMs: number;
  /** The side to move — gets a subtle --secondary highlight (D-06/UI-SPEC). */
  isActive: boolean;
  /** True while the bot's move selection is in flight (D-06). */
  isThinking: boolean;
  testId?: string;
}

/**
 * A single side's clock card for the bot-game board (Phase 169 Plan 05).
 * Digits are formatted by chessClock.ts's formatClockLabel/isLowTime — this
 * component never reimplements clock math or formatting (D-07/UI-SPEC).
 */
export function ClockDisplay({
  sideLabel,
  remainingMs,
  isActive,
  isThinking,
  testId,
}: ClockDisplayProps): ReactElement {
  const lowTime = isLowTime(remainingMs);

  return (
    <div
      data-testid={testId}
      className={cn(
        'flex items-center justify-between gap-2 rounded-[var(--radius)] bg-card p-4',
        isActive && 'bg-secondary',
        lowTime && 'ring-2 ring-destructive/40',
      )}
    >
      <span className="flex items-center gap-2 text-sm font-medium">
        {sideLabel}
        {isThinking && (
          <>
            <span
              aria-hidden="true"
              className="inline-block h-2 w-2 shrink-0 animate-pulse rounded-full bg-brand-brown"
            />
            <span className="sr-only" aria-live="polite">
              Bot is thinking
            </span>
          </>
        )}
      </span>
      <span
        className="text-xl font-bold tabular-nums"
        style={lowTime ? { color: CLOCK_LOW_TIME_URGENT } : undefined}
      >
        {formatClockLabel(remainingMs)}
      </span>
    </div>
  );
}
