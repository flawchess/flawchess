import type { ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { formatClockLabel, isLowTime } from '@/lib/chessClock';
import { CLOCK_LOW_TIME_URGENT } from '@/lib/theme';

interface ClockDisplayProps {
  /** Side caption — the resolved player display name (lichess_username ->
   * chess_com_username -> "You", see lib/playerName.ts) for the human side,
   * or the persona's name / "FlawChess Bot" for the bot side (Phase 183,
   * D-06), per the UI-SPEC Copywriting Contract. */
  sideLabel: string;
  /** Persona placeholder-avatar glyph (Phase 183, D-06) — rendered beside
   * `sideLabel` for a persona game; omitted (no avatar rendered) for a
   * Custom game or the human side. */
  avatarEmoji?: string;
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
 *
 * Sized to sit close to the analysis board's PlayerBar strip (170 UAT test 7:
 * the original p-4 / text-xl card ate too much vertical space on mobile). The
 * card surface itself stays — the active-side fill and the low-time ring need
 * something to paint on.
 */
export function ClockDisplay({
  sideLabel,
  avatarEmoji,
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
        'flex items-center justify-between gap-2 rounded-[var(--radius)] bg-card px-2 py-1.5',
        isActive && 'bg-secondary',
        lowTime && 'ring-2 ring-destructive/40',
      )}
    >
      <span className="flex items-center gap-2 text-sm font-medium">
        {avatarEmoji && (
          <span aria-hidden="true" className="text-lg leading-none">
            {avatarEmoji}
          </span>
        )}
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
        className="text-lg font-bold tabular-nums"
        style={lowTime ? { color: CLOCK_LOW_TIME_URGENT } : undefined}
      >
        {formatClockLabel(remainingMs)}
      </span>
    </div>
  );
}
