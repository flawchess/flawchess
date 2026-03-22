import { Chessboard } from 'react-chessboard';
import { darkSquareStyle, lightSquareStyle } from '../../lib/theme';

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
          darkSquareStyle,
          lightSquareStyle,
          showNotation: false,
          allowDragging: false,
          showAnimations: false,
        }}
      />
    </div>
  );
}
