import { Chessboard } from 'react-chessboard';

interface MiniBoardProps {
  fen: string;
  flipped?: boolean;
  size?: number;
}

/**
 * Reusable read-only mini chess board thumbnail for position bookmark suggestions.
 */
export function MiniBoard({ fen, flipped = false, size = 100 }: MiniBoardProps) {
  return (
    <div
      data-testid="mini-board"
      style={{ width: size, height: size, flexShrink: 0 }}
      className="pointer-events-none"
    >
      <Chessboard
        options={{
          position: fen,
          boardOrientation: flipped ? 'black' : 'white',
          boardStyle: { width: size, height: size },
          darkSquareStyle: { backgroundColor: '#8B6914' },
          lightSquareStyle: { backgroundColor: '#D4A843' },
          showNotation: false,
          allowDragging: false,
          showAnimations: false,
        }}
      />
    </div>
  );
}
