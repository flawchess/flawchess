import { useMemo } from 'react';
import { Chessboard } from 'react-chessboard';
import { darkSquareStyle, lightSquareStyle, MOVE_HIGHLIGHT_SQUARE } from '../../lib/theme';
import { squareToCoords, buildArrowPath } from './arrowGeometry';

// Fine-arrow proportions, distinct from ChessBoard.tsx's normalized 0..1 width
// scale. MiniBoard arrows are decorative pointers ("which move scored well/
// poorly?"), so they stay visually thin even on small boards. All values are
// fractions of a single square's pixel size.
const MINI_SHAFT_WIDTH = 0.27;
const MINI_HEAD_WIDTH = 0.75;
const MINI_HEAD_LENGTH_RATIO = 0.7;
const MINI_ARROW_OPACITY = 0.85;
const MINI_TIP_OVERSHOOT = 0.16;

interface MiniBoardArrow {
  from: string;
  to: string;
  color: string;
}

/** A small severity dot pinned to the top-right corner of a square's piece. */
interface MiniBoardCornerDot {
  square: string;
  color: string;
}

// Corner-dot radius and edge inset as fractions of a single square's pixel size,
// so the dot scales with the board. The dot centre is inset from the square's
// top-right corner by (radius + gap) on both axes so it sits ON the piece corner.
const CORNER_DOT_RADIUS = 0.2;
const CORNER_DOT_INSET = 0.24;
const CORNER_DOT_STROKE = 0.05;

interface MiniBoardProps {
  fen: string;
  size?: number;
  flipped?: boolean;
  arrows?: ReadonlyArray<MiniBoardArrow>;
  cornerDot?: MiniBoardCornerDot;
  /** From/to squares of the move that reached this position — highlighted like the Openings board. */
  lastMove?: { from: string; to: string };
}

function MiniCornerDotOverlay({
  dot,
  size,
  flipped,
}: {
  dot: MiniBoardCornerDot;
  size: number;
  flipped: boolean;
}) {
  const sqSize = size / 8;
  // squareToCoords returns the square centre in square units (already orientation-
  // aware). The square's visual top-right corner is at (x+0.5, y-0.5) in screen
  // space regardless of flip; inset toward the centre so the dot stays on-board.
  const [x, y] = squareToCoords(dot.square, flipped);
  const cx = (x + 0.5 - CORNER_DOT_INSET) * sqSize;
  const cy = (y - 0.5 + CORNER_DOT_INSET) * sqSize;
  return (
    <svg
      width={size}
      height={size}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      data-testid="mini-board-corner-dot"
    >
      <circle
        cx={cx}
        cy={cy}
        r={CORNER_DOT_RADIUS * sqSize}
        fill={dot.color}
        stroke="white"
        strokeWidth={CORNER_DOT_STROKE * sqSize}
      />
    </svg>
  );
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

export function MiniBoard({
  fen,
  size = 120,
  flipped = false,
  arrows,
  cornerDot,
  lastMove,
}: MiniBoardProps) {
  // Highlight the move's from/to squares with the same translucent yellow as the
  // Openings ChessBoard last-move highlight (MOVE_HIGHLIGHT_SQUARE).
  const lastFrom = lastMove?.from ?? null;
  const lastTo = lastMove?.to ?? null;
  const squareStyles = useMemo<Record<string, { backgroundColor: string }>>(() => {
    if (!lastFrom || !lastTo) return {};
    return {
      [lastFrom]: { backgroundColor: MOVE_HIGHLIGHT_SQUARE },
      [lastTo]: { backgroundColor: MOVE_HIGHLIGHT_SQUARE },
    };
  }, [lastFrom, lastTo]);

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
      squareStyles,
      showNotation: false,
      allowDragging: false,
      showAnimations: false,
    }),
    [fen, flipped, size, squareStyles],
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
      {cornerDot && <MiniCornerDotOverlay dot={cornerDot} size={size} flipped={flipped} />}
    </div>
  );
}
