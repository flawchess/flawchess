import { useMemo } from 'react';
import { Chessboard } from 'react-chessboard';
import { darkSquareStyle, lightSquareStyle } from '../../lib/theme';

interface MiniBoardProps {
  fen: string;
  size?: number;
  flipped?: boolean;
}

export function MiniBoard({ fen, size = 120, flipped = false }: MiniBoardProps) {
  // Memoize the options object so re-renders of an ancestor (e.g. /openings/games
  // mounts up to 20 MiniBoards) don't hand react-chessboard 5.x a fresh `options`
  // identity and re-fire its internal piece-animation/dnd effects on every parent
  // tick. Identity instability across ~21 boards is what amplifies a single parent
  // re-render past React's 50-nested-update guard (Sentry FLAWCHESS-3Y).
  const options = useMemo(
    () => ({
      position: fen,
      boardOrientation: (flipped ? 'black' : 'white') as 'black' | 'white',
      boardStyle: { width: size, height: size },
      darkSquareStyle,
      lightSquareStyle,
      showNotation: false,
      allowDragging: false,
      showAnimations: false,
    }),
    [fen, flipped, size],
  );

  return (
    <div style={{ width: size, height: size }} className="pointer-events-none flex-shrink-0">
      <Chessboard options={options} />
    </div>
  );
}
