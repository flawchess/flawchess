import { useMemo } from 'react';
import { Chessboard } from 'react-chessboard';
import { darkSquareStyle, lightSquareStyle } from '../../lib/theme';
import { squareToCoords, buildArrowPath } from './arrowGeometry';

// Fine-arrow proportions, distinct from ChessBoard.tsx's normalized 0..1 width
// scale. MiniBoard arrows are decorative pointers ("which move scored well/
// poorly?"), so they stay visually thin even on small boards. All values are
// fractions of a single square's pixel size.
const MINI_SHAFT_WIDTH = 0.10;
const MINI_HEAD_WIDTH = 0.30;
const MINI_HEAD_LENGTH_RATIO = 0.7;
const MINI_ARROW_OPACITY = 0.85;
const MINI_TIP_OVERSHOOT = 0.12;

interface MiniBoardArrow {
  from: string;
  to: string;
  color: string;
}

interface MiniBoardProps {
  fen: string;
  size?: number;
  flipped?: boolean;
  arrows?: ReadonlyArray<MiniBoardArrow>;
}

function MiniArrowOverlay({
  arrows,
  size,
  flipped,
}: {
  arrows: ReadonlyArray<MiniBoardArrow>;
  size: number;
  flipped: boolean;
}) {
  if (arrows.length === 0) return null;
  const sqSize = size / 8;
  return (
    <svg
      width={size}
      height={size}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      data-testid="mini-board-arrow-overlay"
    >
      {arrows.map((a) => {
        // Skip degenerate arrows (same start/end square — would produce NaN path).
        if (a.from === a.to) return null;

        const [x1, y1] = squareToCoords(a.from, flipped);
        const [cx2, cy2] = squareToCoords(a.to, flipped);

        // Extend the tip past the target square center so the arrowhead point
        // sits visibly inside the destination square instead of dead-center.
        const adx = cx2 - x1;
        const ady = cy2 - y1;
        const alen = Math.sqrt(adx * adx + ady * ady);
        const x2 = cx2 + (adx / alen) * MINI_TIP_OVERSHOOT;
        const y2 = cy2 + (ady / alen) * MINI_TIP_OVERSHOOT;

        const shaftHalf = (MINI_SHAFT_WIDTH * sqSize) / 2;
        const headWidth = MINI_HEAD_WIDTH * sqSize;
        const headLen = headWidth * MINI_HEAD_LENGTH_RATIO;

        const d = buildArrowPath(
          x1 * sqSize, y1 * sqSize, x2 * sqSize, y2 * sqSize,
          shaftHalf, headWidth / 2, headLen,
        );

        return (
          <path
            key={`${a.from}-${a.to}`}
            d={d}
            fill={a.color}
            opacity={MINI_ARROW_OPACITY}
          />
        );
      })}
    </svg>
  );
}

export function MiniBoard({ fen, size = 120, flipped = false, arrows }: MiniBoardProps) {
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
    <div
      style={{ width: size, height: size, position: 'relative' }}
      className="pointer-events-none flex-shrink-0"
    >
      <Chessboard options={options} />
      {arrows && arrows.length > 0 && (
        <MiniArrowOverlay arrows={arrows} size={size} flipped={flipped} />
      )}
    </div>
  );
}
