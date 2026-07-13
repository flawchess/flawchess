import { useEffect } from 'react';
import type { ReactElement } from 'react';
import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import { Button } from '@/components/ui/button';

interface MoveListPanelProps {
  moveHistory: string[];
  /** Ply of the actual live game position (never moves except via new moves). */
  liveGamePly: number;
  /** Ply currently displayed on the board — may differ from liveGamePly during
   * view-only scroll-back (D-13). */
  viewedPly: number;
  /** Navigate the displayed (view-only) position without affecting the live game. */
  onViewPly: (ply: number) => void;
  /** Snap the displayed position back to the live game position. */
  onReturnToLive: () => void;
}

/**
 * Linear SAN move list for the bot-game board (Phase 169 Plan 05). Reuses
 * MoveList.tsx's item-mapping shape near-verbatim; the active-ply highlight
 * always marks the LIVE game position (brand-brown, per UI-SPEC), while
 * clicking a row or using arrow keys navigates a separate view-only
 * `viewedPly` cursor — the board never disables silently, a "Return to live
 * position" affordance is always shown while scrolled back (D-13).
 */
export function MoveListPanel({
  moveHistory,
  liveGamePly,
  viewedPly,
  onViewPly,
  onReturnToLive,
}: MoveListPanelProps): ReactElement {
  const isScrolledBack = viewedPly !== liveGamePly;

  // Arrow-key view-only scroll-back — guarded against capturing keys while
  // typing in an input/textarea/select, mirroring useChessGame.ts's precedent.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent): void => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        onViewPly(Math.max(0, viewedPly - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        onViewPly(Math.min(liveGamePly, viewedPly + 1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [viewedPly, liveGamePly, onViewPly]);

  const items: HorizontalMoveItem[] = moveHistory.map((san, idx) => {
    const ply = idx + 1;
    const isWhite = idx % 2 === 0;
    const moveNumber = Math.floor(idx / 2) + 1;
    return {
      key: ply,
      ply,
      numberLabel: isWhite ? `${moveNumber}.` : null,
      san,
      // The active highlight always marks the LIVE game position, not the
      // view-only scroll-back cursor (UI-SPEC).
      isCurrent: liveGamePly === ply,
      testId: `move-${ply}`,
      ariaLabel: `Move ${moveNumber}. ${san} (${isWhite ? 'white' : 'black'})`,
    };
  });

  return (
    <div className="flex flex-col gap-2">
      <HorizontalMoveList
        items={items}
        onMoveClick={onViewPly}
        testId="bot-move-list"
        activeItemClassName="bg-brand-brown/10 text-foreground hover:bg-brand-brown/15"
      />
      {isScrolledBack && (
        <Button
          variant="link"
          size="sm"
          className="self-start text-sm"
          onClick={onReturnToLive}
          data-testid="btn-return-live"
        >
          Return to live position
        </Button>
      )}
    </div>
  );
}
