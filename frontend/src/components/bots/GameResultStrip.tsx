import type { ReactElement } from 'react';
import { Link } from 'react-router-dom';
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
  onNewGame: () => void;
  onAnalyze: () => void;
  /** D-21: true only once the finish-time store mutation has CONFIRMED
   * (`useStoreBotGame().isSuccess`) — mirrors `GameResultDialog`'s gate; this
   * IS the mobile/dismissed surface, so the row must land here too. */
  storeSucceeded: boolean;
  /** SC4: guests additionally see the not-auto-analyzed caveat below the
   * save confirmation; non-guests never see it. */
  isGuest: boolean;
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
}: GameResultStripProps): ReactElement {
  const title = resultCopy(outcome, userColor);

  return (
    <div
      data-testid="result-strip"
      className="flex flex-col gap-2 rounded-[var(--radius)] bg-secondary px-4 py-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{title}</span>
        <div className="flex items-center gap-2">
          <Button
            variant="brand-outline"
            size="sm"
            onClick={onAnalyze}
            data-testid="strip-btn-analyze-game"
          >
            Analyze this game
          </Button>
          <Button variant="default" size="sm" onClick={onNewGame} data-testid="strip-btn-new-game">
            New game
          </Button>
        </div>
      </div>
      {/* D-20/D-21: only renders once the finish-time store has CONFIRMED
          (never on idle/pending/error) — the Analyze button above is NOT
          gated on this. */}
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
