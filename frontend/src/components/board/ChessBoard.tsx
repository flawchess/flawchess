import { useRef, useEffect, useState, useCallback } from 'react';
import { Chessboard } from 'react-chessboard';

interface BoardArrow {
  startSquare: string;
  endSquare: string;
  color: string;
}

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  /** Highlight: { from: "e2", to: "e4" } for the last move */
  lastMove?: { from: string; to: string } | null;
  /** Arrows to render on the board (react-chessboard arrow format) */
  arrows?: BoardArrow[];
}

const BRIGHT_NOTATION: React.CSSProperties = { color: 'rgba(255, 255, 255, 0.85)', fontWeight: 600 };

const PIECE_NAMES: Record<string, string> = {
  wP: 'white pawn', wR: 'white rook', wN: 'white knight', wB: 'white bishop', wQ: 'white queen', wK: 'white king',
  bP: 'black pawn', bR: 'black rook', bN: 'black knight', bB: 'black bishop', bQ: 'black queen', bK: 'black king',
};

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
          arrows: arrows,
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
    </div>
  );
}
