import { Chessboard } from 'react-chessboard';

interface MiniBoardProps {
  fen: string;
  flipped?: boolean;
  size?: number;
}

/**
 * Reusable read-only mini chess board thumbnail for position bookmark suggestions.
 */
export function MiniBoard({ fen, flipped = false, size = 80 }: MiniBoardProps) {
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
          darkSquareStyle: { backgroundColor: '#4a5568' },
          lightSquareStyle: { backgroundColor: '#718096' },
          showNotation: false,
          allowDragging: false,
          showAnimations: false,
        }}
      />
    </div>
  );
}
