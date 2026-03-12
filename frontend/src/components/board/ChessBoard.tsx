import { useRef, useEffect, useState } from 'react';
import { Chessboard } from 'react-chessboard';

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  /** Highlight: { from: "e2", to: "e4" } for the last move */
  lastMove?: { from: string; to: string } | null;
}

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

  return (
    <div ref={containerRef} className="w-full">
      <Chessboard
        options={{
          position,
          boardOrientation: flipped ? 'black' : 'white',
          boardStyle: { width: boardWidth, height: boardWidth },
          darkSquareStyle: { backgroundColor: '#4a5568' },
          lightSquareStyle: { backgroundColor: '#718096' },
          squareStyles,
          onPieceDrop: ({ sourceSquare, targetSquare }) => {
            if (!targetSquare) return false;
            return onPieceDrop(sourceSquare, targetSquare);
          },
        }}
      />
    </div>
  );
}
