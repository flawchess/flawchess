import type { ReactElement, ReactNode } from 'react';
import { Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CLOCK_LOW_TIME_URGENT, EVAL_BAR_BLACK, EVAL_BAR_WHITE } from '@/lib/theme';
import { MaterialDisplay } from './MaterialDisplay';

/**
 * Remaining clock as m:ss (floored), e.g. 179.4 → "2:59".
 * Local helper, not a shared import (D-05 — see EvalChart/FlawCard).
 */
function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * The clock readout as a colour-coded badge (Phase 223 UAT). The background is
 * the player's own board colour — the same two values the MoveStats accuracy
 * pills use — so the badge doubles as the row's side-identity indicator and the
 * ■/□ glyph beside the name becomes redundant. Its own component purely to keep
 * `PlayerBar` under the eslint complexity ceiling.
 */
function ClockBadge({
  isWhite,
  clockSeconds,
  clockActive,
  clockUrgent,
  testId,
}: {
  isWhite: boolean;
  clockSeconds: number;
  clockActive: boolean | undefined;
  clockUrgent: boolean;
  testId: string | undefined;
}): ReactElement {
  // Low time outranks side identity: at this point the row's job is to shout,
  // and the name + row position still say whose clock it is.
  const background = clockUrgent ? CLOCK_LOW_TIME_URGENT : isWhite ? EVAL_BAR_WHITE : EVAL_BAR_BLACK;
  return (
    <span
      className={cn(
        'flex shrink-0 items-center gap-1 rounded-md px-2 py-0.5 font-bold tabular-nums',
        clockUrgent || !isWhite ? 'text-white' : 'text-black',
      )}
      style={{ backgroundColor: background }}
      data-testid={testId !== undefined ? `${testId}-clock-badge` : undefined}
    >
      <Clock
        className={cn('h-4 w-4 opacity-70', clockActive === false && 'invisible')}
        aria-hidden="true"
        data-testid={testId !== undefined ? `${testId}-clock-icon` : undefined}
      />
      {formatClock(clockSeconds)}
    </span>
  );
}

interface PlayerBarProps {
  /** True = White (■), false = Black (□) — matches the library game-card glyph convention. */
  isWhite: boolean;
  name: string | null;
  /** ELO/rating; rendered in parentheses when present. */
  rating: number | null;
  /**
   * Phase 223 (BOTVOICE-05, D-11): an honest, tilde-prefixed rating estimate
   * (e.g. a persona's `calibratedLabel`, or the player's own rounded
   * `~${rating}` estimate) — wins over the numeric `rating` prop when both
   * are present, because a calibrated estimate is not an exact rating and a
   * parenthesised integer would misrepresent it as one. Optional and purely
   * additive: every existing call site keeps rendering `rating` exactly as
   * before by simply never passing this prop.
   */
  ratingLabel?: string;
  /** Mover's remaining clock at the current position (seconds); null = no %clk → clock hidden. */
  clockSeconds: number | null;
  /**
   * Phase 223 UAT: `false` hides the clock ICON (digits stay) so only the
   * side to move carries it — a live-game affordance. The icon keeps its
   * layout slot (`invisible`, not unmounted) so the digits never shift when
   * the turn passes. Omitted (`undefined`) keeps the icon on every row, the
   * Analysis board's pre-existing rendering.
   */
  clockActive?: boolean;
  /**
   * Phase 223 UAT: paints the digits in `CLOCK_LOW_TIME_URGENT` — the bot
   * game's low-time treatment (Phase 169 D-07), carried over from the
   * retired mobile clock strip now that both breakpoints render this row.
   * The caller decides via `isLowTime` (`lib/chessClock.ts`); this row owns
   * no clock math.
   */
  clockUrgent?: boolean;
  /**
   * Phase 208 (PASTE-02, UI-SPEC § Interaction Contract 6): optional content
   * for the right-aligned slot, rendered ONLY when clockSeconds is null — a
   * real game's clock always wins. Used by Analysis.tsx to show "{Result} ·
   * {Date}" in an ephemeral pasted game's freed clock slot, on the top
   * player row only.
   */
  rightSlotContent?: ReactNode;
  /**
   * Quick 260809-jzz (D-05): the FEN of the position currently on the board.
   * Omitted means no material display — Analysis free play stays unchanged,
   * since every call site already sits behind the `showPlayerBars` gate.
   */
  fen?: string;
  testId?: string;
}

/**
 * One player's info row for the analysis and bot-game boards: name + ELO on the
 * left, then material imbalance and the clock badge on the right. Rendered above
 * and below the board, ordered by board orientation. clockSeconds is null for
 * imports without a %clk annotation (e.g. some chess.com games), in which case
 * the badge is omitted (or, when passed, rightSlotContent fills that same slot
 * instead) and the ■/□ glyph carries the side identity in its place.
 */
export function PlayerBar({
  isWhite,
  name,
  rating,
  ratingLabel,
  clockSeconds,
  clockActive,
  clockUrgent = false,
  rightSlotContent,
  fen,
  testId,
}: PlayerBarProps): ReactElement {
  // Phase 223 UAT: the badge carries the side identity, so the ■/□ glyph
  // renders ONLY in the fallback case where there is no clock to paint (an
  // import without %clk) and the row would otherwise have no colour cue.
  const hasClock = clockSeconds !== null;

  return (
    <div
      data-testid={testId}
      className="flex items-center justify-between gap-2 px-1 text-sm text-foreground"
    >
      <span className="truncate min-w-0">
        {!hasClock && <>{isWhite ? '■' : '□'} </>}
        {name ?? '?'}
        {ratingLabel !== undefined ? (
          <span className="text-muted-foreground"> {ratingLabel}</span>
        ) : (
          rating !== null && <span className="text-muted-foreground"> ({rating})</span>
        )}
      </span>
      {/* Right group (Phase 223 UAT): material imbalance sits immediately left
          of the clock badge, so both of the row's live readouts share one edge
          instead of the material hanging off the end of the name. */}
      <span className="flex shrink-0 items-center gap-2">
        {fen !== undefined && (
          <MaterialDisplay fen={fen} side={isWhite ? 'white' : 'black'} className="shrink-0" />
        )}
        {hasClock ? (
          <ClockBadge
            isWhite={isWhite}
            clockSeconds={clockSeconds}
            clockActive={clockActive}
            clockUrgent={clockUrgent}
            testId={testId}
          />
        ) : (
          rightSlotContent != null && (
            <span className="shrink-0 truncate text-sm text-muted-foreground">
              {rightSlotContent}
            </span>
          )
        )}
      </span>
    </div>
  );
}
