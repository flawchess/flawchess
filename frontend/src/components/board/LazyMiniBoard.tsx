import { useRef, useState, useEffect } from 'react';
import { MiniBoard } from '@/components/board/MiniBoard';

/** Renders MiniBoard only when the card scrolls into view. */
export function LazyMiniBoard({
  fen,
  flipped,
  size,
}: {
  fen: string;
  flipped: boolean;
  size: number;
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
      {visible && <MiniBoard fen={fen} size={size} flipped={flipped} />}
    </div>
  );
}
