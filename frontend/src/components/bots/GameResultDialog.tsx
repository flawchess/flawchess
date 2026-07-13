import type { ReactElement } from 'react';
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

interface GameResultDialogProps {
  outcome: BotGameOutcome;
  userColor: MoverColor;
  open: boolean;
  onDismiss: () => void;
  onNewGame: () => void;
  onAnalyze: () => void;
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
