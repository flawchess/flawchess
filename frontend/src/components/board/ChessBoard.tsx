import { useRef, useEffect, useState } from 'react';
import { Chessboard } from 'react-chessboard';

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
}

export function ChessBoard({ position, onPieceDrop }: ChessBoardProps) {
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

  return (
    <div ref={containerRef} className="w-full">
      <Chessboard
        options={{
          position,
          boardStyle: { width: boardWidth, height: boardWidth },
          darkSquareStyle: { backgroundColor: '#4a5568' },
          lightSquareStyle: { backgroundColor: '#718096' },
          onPieceDrop: ({ sourceSquare, targetSquare }) => {
            if (!targetSquare) return false;
            return onPieceDrop(sourceSquare, targetSquare);
          },
        }}
      />
    </div>
  );
}
