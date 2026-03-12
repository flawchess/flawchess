import { useRef, useEffect, useState } from 'react';
import { Chessboard } from 'react-chessboard';

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  /** Highlight: { from: "e2", to: "e4" } for the last move */
  lastMove?: { from: string; to: string } | null;
}

const RANKS_WHITE = ['8', '7', '6', '5', '4', '3', '2', '1'];
const RANKS_BLACK = ['1', '2', '3', '4', '5', '6', '7', '8'];
const FILES_WHITE = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const FILES_BLACK = ['h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'];

export function ChessBoard({ position, onPieceDrop, flipped = false, lastMove }: ChessBoardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [boardWidth, setBoardWidth] = useState(400);

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

  // Build squareStyles for last-move highlighting
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (lastMove) {
    const highlightStyle: React.CSSProperties = { backgroundColor: 'rgba(255, 255, 0, 0.35)' };
    squareStyles[lastMove.from] = highlightStyle;
    squareStyles[lastMove.to] = highlightStyle;
  }

  const ranks = flipped ? RANKS_BLACK : RANKS_WHITE;
  const files = flipped ? FILES_BLACK : FILES_WHITE;

  return (
    <div ref={containerRef} className="w-full">
      <div className="flex flex-row">
        {/* Rank labels column (left of board) */}
        <div
          className="flex flex-col w-4 shrink-0"
          style={{ height: boardWidth }}
        >
          {ranks.map((rank) => (
            <span
              key={rank}
              className="flex-1 flex items-center justify-center text-xs text-gray-400 select-none"
            >
              {rank}
            </span>
          ))}
        </div>

        {/* Board + file labels */}
        <div className="flex flex-col">
          <Chessboard
            options={{
              position,
              boardOrientation: flipped ? 'black' : 'white',
              boardStyle: { width: boardWidth, height: boardWidth },
              darkSquareStyle: { backgroundColor: '#4a5568' },
              lightSquareStyle: { backgroundColor: '#718096' },
              showNotation: false,
              squareStyles,
              onPieceDrop: ({ sourceSquare, targetSquare }) => {
                if (!targetSquare) return false;
                return onPieceDrop(sourceSquare, targetSquare);
              },
            }}
          />

          {/* File labels row (below board) */}
          <div
            className="flex flex-row h-4"
            style={{ width: boardWidth }}
          >
            {files.map((file) => (
              <span
                key={file}
                className="flex-1 flex items-center justify-center text-xs text-gray-400 select-none"
              >
                {file}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
