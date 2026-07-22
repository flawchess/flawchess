import type { ReactElement } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { resultCopy, type BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';
import {
  BOT_GAME_SAVED_COPY,
  GUEST_NOT_AUTO_ANALYZED_COPY,
} from '@/components/bots/GameResultDialog';

interface GameResultStripProps {
  outcome: BotGameOutcome;
  userColor: MoverColor;
  /** D-08: relabeled "New opponent" — mirrors `GameResultDialog`'s prop. */
  onNewGame: () => void;
  onAnalyze: () => void;
  /** D-21: true only once the finish-time store mutation has CONFIRMED
   * (`useStoreBotGame().isSuccess`) — mirrors `GameResultDialog`'s gate; this
   * IS the mobile/dismissed surface, so the row must land here too. */
  storeSucceeded: boolean;
  /** SC4: guests additionally see the not-auto-analyzed caveat below the
   * save confirmation; non-guests never see it. */
  isGuest: boolean;
  /** Quick 260714-rj5: mirrors `GameResultDialog`'s analyzeBusy gate — see its
   * doc comment. This IS the mobile/dismissed surface, so it must land here too. */
  analyzeBusy: boolean;
  /** Phase 183 (D-06/D-08): mirrors `GameResultDialog`'s persona props —
   * the strip renders the IDENTICAL persona-aware `resultCopy` string and
   * mirrors the same action set (mobile parity). */
  personaName: string | null;
  onRematch: () => void;
}

/**
 * Persistent post-dismiss result strip (Phase 169 D-11). Replaces the normal
 * in-game controls area once `GameResultDialog` is dismissed, keeping the
 * same `resultCopy` text (Body size, not the dialog's Heading size) and the
 * same two actions reachable as compact buttons until "New game" is clicked.
 */
export function GameResultStrip({
  outcome,
  userColor,
  onNewGame,
  onAnalyze,
  storeSucceeded,
  isGuest,
  analyzeBusy,
  personaName,
  onRematch,
}: GameResultStripProps): ReactElement {
  const title = resultCopy(outcome, userColor, personaName);

  return (
    <div
      data-testid="result-strip"
      className="flex flex-col gap-2 rounded-[var(--radius)] bg-secondary px-4 py-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{title}</span>
        <div className="flex items-center gap-2">
          {/* D-21 RETIRED (Quick 260714-rj5) — mirrors GameResultDialog's
              comment: the Analyze CTA is now store-gated because it needs the
              server-assigned game_id to enqueue tier-1 analysis and open the
              game-mode board; a store failure falls back to the free-play
              ?line= URL. */}
          <Button
            variant="brand-outline"
            size="sm"
            onClick={onAnalyze}
            disabled={analyzeBusy}
            data-testid="strip-btn-analyze-game"
          >
            {analyzeBusy && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            Analyze this game
          </Button>
          {/* D-08: mirrors GameResultDialog's primary/secondary swap — Rematch
              is the single high-emphasis CTA when present (persona game). */}
          <Button
            variant={personaName ? 'brand-outline' : 'default'}
            size="sm"
            onClick={onNewGame}
            data-testid="strip-btn-new-game"
          >
            New opponent
          </Button>
          {personaName && (
            <Button
              variant="default"
              size="sm"
              onClick={onRematch}
              data-testid="strip-btn-rematch"
            >
              {`Rematch ${personaName}`}
            </Button>
          )}
        </div>
      </div>
      {/* D-20: only renders once the finish-time store has CONFIRMED (never
          on idle/pending/error). */}
      {storeSucceeded && (
        <div className="flex flex-col gap-1">
          <Link
            to="/library/games"
            className="text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            data-testid="strip-saved-to-library"
          >
            {BOT_GAME_SAVED_COPY}
          </Link>
          {isGuest && (
            <p className="text-sm text-muted-foreground" data-testid="strip-guest-analysis-caveat">
              {GUEST_NOT_AUTO_ANALYZED_COPY}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
