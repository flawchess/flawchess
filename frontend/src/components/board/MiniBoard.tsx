import { Chessboard } from 'react-chessboard';

interface MiniBoardProps {
  fen: string;
  size?: number;
  flipped?: boolean;
}

export function MiniBoard({ fen, size = 120, flipped = false }: MiniBoardProps) {
  return (
    <div style={{ width: size, height: size }} className="pointer-events-none flex-shrink-0">
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
