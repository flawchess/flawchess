import { useRef, useEffect, useState, useCallback } from 'react';
import { Chessboard } from 'react-chessboard';
import { GREEN, GREEN_HOVER, RED, RED_HOVER, GREY, GREY_HOVER } from '../../lib/arrowColor';

export interface BoardArrow {
  startSquare: string;
  endSquare: string;
  color: string;
  /** Normalized width 0–1 (0 = thinnest, 1 = thickest) */
  width: number;
}

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  /** Highlight: { from: "e2", to: "e4" } for the last move */
  lastMove?: { from: string; to: string } | null;
  /** Arrows to render on the board */
  arrows?: BoardArrow[];
}

const BRIGHT_NOTATION: React.CSSProperties = { color: 'rgba(255, 255, 255, 0.85)', fontWeight: 600 };

const PIECE_NAMES: Record<string, string> = {
  wP: 'white pawn', wR: 'white rook', wN: 'white knight', wB: 'white bishop', wQ: 'white queen', wK: 'white king',
  bP: 'black pawn', bR: 'black rook', bN: 'black knight', bB: 'black bishop', bQ: 'black queen', bK: 'black king',
};

// Shaft width range as fraction of square size
const MIN_SHAFT_WIDTH = 0.06;
const MAX_SHAFT_WIDTH = 0.26;
// Arrowhead dimensions as fraction of square size
const MIN_HEAD_WIDTH = 0.25;
const MAX_HEAD_WIDTH = 0.65;
const HEAD_LENGTH_RATIO = 0.7; // head length = head width * this
const ARROW_OPACITY = 0.75;
const ARROW_OUTLINE_COLOR = 'rgba(0, 0, 0, 0.5)';
const ARROW_OUTLINE_WIDTH = 1;
// How far past target square center the arrow tip extends (fraction of square size)
const ARROW_TIP_OVERSHOOT = 0.15;

const FILES = 'abcdefgh';

function squareToCoords(square: string, flipped: boolean): [number, number] {
  const file = FILES.indexOf(square[0]);
  const rank = parseInt(square[1], 10) - 1;
  const x = flipped ? 7 - file + 0.5 : file + 0.5;
  const y = flipped ? rank + 0.5 : 7 - rank + 0.5;
  return [x, y];
}

function buildArrowPath(
  x1: number, y1: number, x2: number, y2: number,
  shaftHalf: number, headHalf: number, headLen: number,
): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  // Unit vectors: along arrow and perpendicular
  const ux = dx / len;
  const uy = dy / len;
  const px = -uy; // perpendicular
  const py = ux;

  // Arrowhead base point (where shaft meets head)
  const bx = x2 - ux * headLen;
  const by = y2 - uy * headLen;

  // Key points
  const startLeft = [x1 + px * shaftHalf, y1 + py * shaftHalf];
  const junctionLeft = [bx + px * shaftHalf, by + py * shaftHalf];
  const headLeft = [bx + px * headHalf, by + py * headHalf];
  const tip = [x2, y2];
  const headRight = [bx - px * headHalf, by - py * headHalf];
  const junctionRight = [bx - px * shaftHalf, by - py * shaftHalf];
  const startRight = [x1 - px * shaftHalf, y1 - py * shaftHalf];

  // SVG path: straight edges with a semicircular arc at the shaft start
  return [
    `M ${startLeft[0]},${startLeft[1]}`,
    `L ${junctionLeft[0]},${junctionLeft[1]}`,
    `L ${headLeft[0]},${headLeft[1]}`,
    `L ${tip[0]},${tip[1]}`,
    `L ${headRight[0]},${headRight[1]}`,
    `L ${junctionRight[0]},${junctionRight[1]}`,
    `L ${startRight[0]},${startRight[1]}`,
    `A ${shaftHalf},${shaftHalf} 0 0,0 ${startLeft[0]},${startLeft[1]}`,
    'Z',
  ].join(' ');
}

// Render priority: grey = 0 (bottom), red = 1 (middle), green = 2 (top).
// Within each color, thick arrows are drawn first so thin arrows stay visible.
const ARROW_COLOR_PRIORITY: Record<string, number> = {
  [GREY]: 0,
  [GREY_HOVER]: 0,
  [RED]: 1,
  [RED_HOVER]: 1,
  [GREEN]: 2,
  [GREEN_HOVER]: 2,
};

function ArrowOverlay({ arrows, boardWidth, flipped }: { arrows: BoardArrow[]; boardWidth: number; flipped: boolean }) {
  if (arrows.length === 0) return null;

  const sqSize = boardWidth / 8;

  const sortedArrows = [...arrows].sort(
    (a, b) =>
      (ARROW_COLOR_PRIORITY[a.color] ?? 0) - (ARROW_COLOR_PRIORITY[b.color] ?? 0)
      || b.width - a.width,
  );

  return (
    <svg
      width={boardWidth}
      height={boardWidth}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      data-testid="arrow-overlay"
    >
      {sortedArrows.map((arrow, i) => {
        const [x1, y1] = squareToCoords(arrow.startSquare, flipped);
        const [cx2, cy2] = squareToCoords(arrow.endSquare, flipped);

        // Extend tip past target center
        const adx = cx2 - x1;
        const ady = cy2 - y1;
        const alen = Math.sqrt(adx * adx + ady * ady);
        const x2 = cx2 + (adx / alen) * ARROW_TIP_OVERSHOOT;
        const y2 = cy2 + (ady / alen) * ARROW_TIP_OVERSHOOT;

        const w = arrow.width; // 0–1 normalized frequency
        const shaftHalf = ((MIN_SHAFT_WIDTH + (MAX_SHAFT_WIDTH - MIN_SHAFT_WIDTH) * w) * sqSize) / 2;
        const headWidth = (MIN_HEAD_WIDTH + (MAX_HEAD_WIDTH - MIN_HEAD_WIDTH) * w) * sqSize;
        const headLen = headWidth * HEAD_LENGTH_RATIO;

        const d = buildArrowPath(
          x1 * sqSize, y1 * sqSize, x2 * sqSize, y2 * sqSize,
          shaftHalf, headWidth / 2, headLen,
        );

        return (
          <path
            key={i}
            d={d}
            fill={arrow.color}
            opacity={ARROW_OPACITY}
            stroke={ARROW_OUTLINE_COLOR}
            strokeWidth={ARROW_OUTLINE_WIDTH}
            strokeLinejoin="round"
          />
        );
      })}
    </svg>
  );
}

export function ChessBoard({ position, onPieceDrop, flipped = false, lastMove, arrows = [] }: ChessBoardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [boardWidth, setBoardWidth] = useState(400);
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [prevPosition, setPrevPosition] = useState<string>(position);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        // On mobile (<768px), use full container width; on desktop cap at 400px
        setBoardWidth(Math.min(containerWidth, 400));
      }
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, []);

  // Reset selected square when position changes (e.g. navigating move history).
  // State update during render is the React-recommended pattern for derived state resets.
  if (prevPosition !== position) {
    setPrevPosition(position);
    setSelectedSquare(null);
  }

  type SquareClickHandler = NonNullable<
    NonNullable<Parameters<typeof Chessboard>[0]['options']>['onSquareClick']
  >;
  type SquareHandlerArgs = Parameters<SquareClickHandler>[0];

  const handleSquareClick = useCallback(
    ({ square, piece }: SquareHandlerArgs) => {
      if (selectedSquare === null) {
        // First click: select a square that has a piece
        if (piece) setSelectedSquare(square);
      } else if (square === selectedSquare) {
        // Clicked same square: deselect
        setSelectedSquare(null);
      } else {
        // Second click: attempt move from selectedSquare to target
        const success = onPieceDrop(selectedSquare, square);
        setSelectedSquare(null);
        if (!success && piece !== null) {
          // Failed move but clicked another piece — reselect that piece
          setSelectedSquare(square);
        }
      }
    },
    [selectedSquare, onPieceDrop],
  );

  // Build squareStyles for last-move highlighting
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (lastMove) {
    const highlightStyle: React.CSSProperties = { backgroundColor: 'rgba(255, 255, 0, 0.35)' };
    squareStyles[lastMove.from] = highlightStyle;
    squareStyles[lastMove.to] = highlightStyle;
  }

  // Yellow highlight on selected square (merged with any lastMove highlight)
  if (selectedSquare) {
    squareStyles[selectedSquare] = {
      ...squareStyles[selectedSquare],
      backgroundColor: 'rgba(255, 255, 0, 0.5)',
    };
  }

  return (
    <div ref={containerRef} className="w-full" data-testid="chessboard">
      <div style={{ position: 'relative', width: boardWidth, height: boardWidth, touchAction: 'none' }}>
        <Chessboard
          options={{
            position,
            boardOrientation: flipped ? 'black' : 'white',
            boardStyle: { width: boardWidth, height: boardWidth },
            darkSquareStyle: { backgroundColor: '#4a5568' },
            lightSquareStyle: { backgroundColor: '#718096' },
            darkSquareNotationStyle: BRIGHT_NOTATION,
            lightSquareNotationStyle: BRIGHT_NOTATION,
            id: 'chessboard',
            // react-chessboard v5 animation state machine causes black screen on mobile
            // when position prop updates — disable animations on touch devices only
            showAnimations: !('ontouchstart' in window),
            clearArrowsOnPositionChange: false,
            squareStyles,
            squareRenderer: ({ piece, square, children }) => {
              const pieceName = piece ? PIECE_NAMES[piece.pieceType] : undefined;
              const label = pieceName ? `${square} ${pieceName}` : square;
              return (
                <div
                  style={{ width: '100%', height: '100%', ...squareStyles[square] }}
                  aria-label={label}
                  data-testid={`square-${square}`}
                  // react-chessboard v5 mobile tap detection is broken: dnd-kit's
                  // TouchSensor starts a drag on minimal finger movement, which resets
                  // the library's isClickingOnMobile flag before onTouchEnd fires.
                  // This onPointerUp bypasses that flow to make tap-to-move work.
                  onPointerUp={(e) => {
                    if (e.pointerType === 'touch') {
                      handleSquareClick({ square, piece: piece ?? null });
                    }
                  }}
                >
                  {children}
                </div>
              );
            },
            onSquareClick: handleSquareClick,
            onPieceDrop: ({ sourceSquare, targetSquare }) => {
              if (!targetSquare) return false;
              return onPieceDrop(sourceSquare, targetSquare);
            },
          }}
        />
        <ArrowOverlay arrows={arrows} boardWidth={boardWidth} flipped={flipped} />
      </div>
    </div>
  );
}
