import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { resultCopy, type BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';

interface GameResultStripProps {
  outcome: BotGameOutcome;
  userColor: MoverColor;
  onNewGame: () => void;
  onAnalyze: () => void;
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
}: GameResultStripProps): ReactElement {
  const title = resultCopy(outcome, userColor);

  return (
    <div
      data-testid="result-strip"
      className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius)] bg-secondary px-4 py-2"
    >
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
  );
}
