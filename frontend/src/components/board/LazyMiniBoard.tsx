import { useRef, useState, useEffect } from 'react';
import { MiniBoard } from '@/components/board/MiniBoard';
import type { SquareMarker } from '@/components/board/boardMarkers';

/** Renders MiniBoard only when the card scrolls into view. */
export function LazyMiniBoard({
  fen,
  flipped,
  size,
  arrows,
  cornerDot,
  squareMarkers,
  lastMove,
  lastMoveColor,
}: {
  fen: string;
  flipped: boolean;
  size: number;
  arrows?: ReadonlyArray<{ from: string; to: string; color: string; label?: string; labelColor?: string }>;
  cornerDot?: { square: string; color: string };
  squareMarkers?: ReadonlyArray<SquareMarker>;
  lastMove?: { from: string; to: string };
  lastMoveColor?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        // safe: IntersectionObserver always provides at least 1 entry when observing 1 element
        if (entries[0]!.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="shrink-0 rounded overflow-hidden bg-muted"
      style={{ width: size, height: size }}
    >
      {visible && (
        <MiniBoard
          fen={fen}
          size={size}
          flipped={flipped}
          arrows={arrows}
          cornerDot={cornerDot}
          squareMarkers={squareMarkers}
          lastMove={lastMove}
          lastMoveColor={lastMoveColor}
        />
      )}
    </div>
  );
}
