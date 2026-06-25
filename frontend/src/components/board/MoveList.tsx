import { HorizontalMoveList } from './HorizontalMoveList';
import type { HorizontalMoveItem } from './HorizontalMoveList';

interface MoveListProps {
  moveHistory: string[];
  currentPly: number;
  onMoveClick: (ply: number) => void;
}

export function MoveList({ moveHistory, currentPly, onMoveClick }: MoveListProps) {
  // Flat item list: white moves carry the "N." number label, black moves none
  // (the shared list wraps freely). Preserves the prior `move-${ply}` testids
  // and aria-labels so existing selectors keep working.
  const items: HorizontalMoveItem[] = moveHistory.map((san, idx) => {
    const ply = idx + 1;
    const isWhite = idx % 2 === 0;
    const moveNumber = Math.floor(idx / 2) + 1;
    return {
      key: ply,
      ply,
      numberLabel: isWhite ? `${moveNumber}.` : null,
      san,
      isCurrent: currentPly === ply,
      testId: `move-${ply}`,
      ariaLabel: `Move ${moveNumber}. ${san} (${isWhite ? 'white' : 'black'})`,
    };
  });

  return <HorizontalMoveList items={items} onMoveClick={onMoveClick} />;
}
