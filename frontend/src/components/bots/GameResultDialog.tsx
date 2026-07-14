import type { ReactElement } from 'react';
import { Link } from 'react-router-dom';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { resultCopy, type BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';
import { WDL_DRAW, WDL_LOSS, WDL_WIN } from '@/lib/theme';

/** D-20/D-21 copy, exported so `GameResultStrip` renders the EXACT same
 * strings rather than re-typing them — a divergence risk on the "apply
 * changes to mobile too" surface (the strip is the mobile/dismissed
 * surface). Verbatim from 171-UI-SPEC.md's Copywriting Contract. */
export const BOT_GAME_SAVED_COPY = 'Saved to your Library';
export const GUEST_NOT_AUTO_ANALYZED_COPY =
  "Guest games aren't analyzed automatically. Use 'Analyze this game' above, or sign up for automatic analysis of every game.";

interface GameResultDialogProps {
  outcome: BotGameOutcome;
  userColor: MoverColor;
  open: boolean;
  onDismiss: () => void;
  onNewGame: () => void;
  onAnalyze: () => void;
  /** D-21: true only once the finish-time store mutation has CONFIRMED
   * (`useStoreBotGame().isSuccess`) — this row never renders on
   * idle/pending/error (no partial-store hedge copy, per UI-SPEC). */
  storeSucceeded: boolean;
  /** SC4: guests additionally see the not-auto-analyzed caveat below the
   * save confirmation; non-guests never see it. */
  isGuest: boolean;
}

/** Title text color keyed by outcome, from `userColor`'s point of view — draw
 * is neutral grey, a decisive result is green (user won) or red (user lost). */
function titleColorFor(outcome: BotGameOutcome, userColor: MoverColor): string {
  if (outcome.reason === 'draw') return WDL_DRAW;
  return outcome.winner === userColor ? WDL_WIN : WDL_LOSS;
}

/**
 * Dismissible game-end result dialog (Phase 169 D-11). The title is the
 * verbatim `resultCopy` string (never re-derived here) colored by the WDL
 * token matching the outcome — text color only, no full-dialog tint. No body
 * prose beyond the title (popover-copy-minimalism). Dismissing via the
 * existing `Dialog`'s X/outside-click reveals the final board position
 * underneath; `GameResultStrip` (rendered by the page once dismissed) keeps
 * both actions reachable afterward.
 */
export function GameResultDialog({
  outcome,
  userColor,
  open,
  onDismiss,
  onNewGame,
  onAnalyze,
  storeSucceeded,
  isGuest,
}: GameResultDialogProps): ReactElement {
  const title = resultCopy(outcome, userColor);
  const titleColor = titleColorFor(outcome, userColor);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onDismiss();
      }}
    >
      <DialogContent data-testid="result-dialog">
        <DialogHeader>
          <DialogTitle style={{ color: titleColor }}>{title}</DialogTitle>
        </DialogHeader>
        {/* D-20/D-21: only renders once the finish-time store has CONFIRMED
            (never on idle/pending/error) — the "Analyze this game" button
            below is NOT gated on this and keeps working regardless. Must stay
            ABOVE DialogFooter: the footer bleeds to the dialog edges
            (-mx-4 -mb-4, rounded-b-xl, border-t) and only renders correctly as
            the last child — anything after it hangs outside the dialog. */}
        {storeSucceeded && (
          <div className="flex flex-col gap-1">
            <Link
              to="/library/games"
              className="text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
              data-testid="result-saved-to-library"
            >
              {BOT_GAME_SAVED_COPY}
            </Link>
            {isGuest && (
              <p className="text-sm text-muted-foreground" data-testid="result-guest-analysis-caveat">
                {GUEST_NOT_AUTO_ANALYZED_COPY}
              </p>
            )}
          </div>
        )}
        <DialogFooter>
          <Button variant="brand-outline" onClick={onAnalyze} data-testid="btn-analyze-game">
            Analyze this game
          </Button>
          <Button variant="default" onClick={onNewGame} data-testid="btn-new-game">
            New game
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
