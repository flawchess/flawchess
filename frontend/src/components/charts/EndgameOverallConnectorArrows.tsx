/**
 * Phase 85 — Desktop-only connector arrows that tie the three cards of the
 * "Endgame Overall Performance" composite section to the Score Differences
 * tile below Card 2.
 *
 *   Card 1 bottom-center → drops down → turns right → Score Gap left-center
 *   Card 3 bottom-center → drops down → turns left  → Score Gap right-center
 *   Card 2 bottom-center → drops straight down      → Score Gap top-center
 *
 * Positions are measured from the live DOM (card heights vary with content)
 * and recomputed on resize. Hidden on mobile via the stacked-layout check
 * inside `compute()` and `hidden lg:block` on the wrapper.
 */

import { useEffect, useState } from 'react';

// Line thickness matches the MiniWDLBar / MiniBulletChart row height
// (Tailwind h-5 = 20px) so the connectors visually weigh the same as the
// charts they tie together.
const ARROW_BAR_PX = 20;
const ARROW_HEAD_LEN_PX = 26; // protrusion past the trunk end
const ARROW_HEAD_HALF_HEIGHT_PX = 22; // flare past the trunk center on each side

interface ArrowGeom {
  c1x: number;
  c1Bottom: number;
  c2x: number;
  c2Bottom: number;
  c3x: number;
  c3Bottom: number;
  sgLeftEdge: number;
  sgRightEdge: number;
  sgTop: number;
  sgMidY: number;
}

export function ConnectorArrows({
  containerRef,
}: {
  containerRef: React.RefObject<HTMLDivElement | null>;
}) {
  const [geom, setGeom] = useState<ArrowGeom | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function compute() {
      if (!container) return;
      const c1 = container.querySelector<HTMLElement>(
        '[data-testid="tile-games-without-endgame"]',
      );
      const c2 = container.querySelector<HTMLElement>(
        '[data-testid="tile-at-endgame-entry"]',
      );
      const c3 = container.querySelector<HTMLElement>(
        '[data-testid="tile-games-with-endgame"]',
      );
      const sg = container.querySelector<HTMLElement>(
        '[data-testid="endgame-score-differences"]',
      );
      if (!c1 || !c2 || !c3 || !sg) {
        setGeom(null);
        return;
      }
      const wr = container.getBoundingClientRect();
      const c1r = c1.getBoundingClientRect();
      const c2r = c2.getBoundingClientRect();
      const c3r = c3.getBoundingClientRect();
      const sgr = sg.getBoundingClientRect();

      // Mobile (stacked single-column): score gap card's left edge aligns
      // with Card 1's left edge. Bail to avoid drawing arrows that don't
      // visually make sense in the stacked layout.
      if (sgr.left <= c1r.left + 2) {
        setGeom(null);
        return;
      }

      setGeom({
        c1x: c1r.left + c1r.width / 2 - wr.left,
        c1Bottom: c1r.bottom - wr.top,
        c2x: c2r.left + c2r.width / 2 - wr.left,
        c2Bottom: c2r.bottom - wr.top,
        c3x: c3r.left + c3r.width / 2 - wr.left,
        c3Bottom: c3r.bottom - wr.top,
        sgLeftEdge: sgr.left - wr.left,
        sgRightEdge: sgr.right - wr.left,
        sgTop: sgr.top - wr.top,
        sgMidY: sgr.top + sgr.height / 2 - wr.top,
      });
    }

    compute();
    const ro = new ResizeObserver(compute);
    ro.observe(container);
    return () => ro.disconnect();
  }, [containerRef]);

  if (!geom) return null;

  const HALF_BAR = ARROW_BAR_PX / 2;
  const HEAD = ARROW_HEAD_LEN_PX;
  const HALF_HEAD_H = ARROW_HEAD_HALF_HEIGHT_PX;

  // Arrow 1: Card 1 → Score Gap left edge (arrowhead points right)
  // Vertical drops from Card 1 bottom to the horizontal trunk's bottom edge
  // (sgMidY + HALF_BAR), covering the corner block with a single rectangle.
  const a1V = {
    left: geom.c1x - HALF_BAR,
    top: geom.c1Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgMidY + HALF_BAR - geom.c1Bottom,
  };
  // Horizontal trunk starts at the vertical's left edge and ends where the
  // arrowhead begins.
  const a1H = {
    left: geom.c1x - HALF_BAR,
    top: geom.sgMidY - HALF_BAR,
    width: geom.sgLeftEdge - HEAD - (geom.c1x - HALF_BAR),
    height: ARROW_BAR_PX,
  };
  const a1Head = {
    left: geom.sgLeftEdge - HEAD,
    top: geom.sgMidY - HALF_HEAD_H,
    width: HEAD,
    height: HALF_HEAD_H * 2,
    clipPath: 'polygon(0 0, 100% 50%, 0 100%)',
  };

  // Arrow 2: Card 3 → Score Gap right edge (arrowhead points left)
  const a2V = {
    left: geom.c3x - HALF_BAR,
    top: geom.c3Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgMidY + HALF_BAR - geom.c3Bottom,
  };
  const a2H = {
    left: geom.sgRightEdge + HEAD,
    top: geom.sgMidY - HALF_BAR,
    width: geom.c3x + HALF_BAR - (geom.sgRightEdge + HEAD),
    height: ARROW_BAR_PX,
  };
  const a2Head = {
    left: geom.sgRightEdge,
    top: geom.sgMidY - HALF_HEAD_H,
    width: HEAD,
    height: HALF_HEAD_H * 2,
    clipPath: 'polygon(100% 0, 0 50%, 100% 100%)',
  };

  // Arrow 3: Card 2 → Score Gaps top edge (arrowhead points down)
  const a3V = {
    left: geom.c2x - HALF_BAR,
    top: geom.c2Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgTop - HEAD - geom.c2Bottom,
  };
  const a3Head = {
    left: geom.c2x - HALF_HEAD_H,
    top: geom.sgTop - HEAD,
    width: HALF_HEAD_H * 2,
    height: HEAD,
    clipPath: 'polygon(0 0, 100% 0, 50% 100%)',
  };

  // `!absolute` overrides .charcoal-texture's `position: relative`. The class
  // already sets `overflow: hidden`, so clip-path on the arrowhead also clips
  // the noise pseudo-element to the triangle shape.
  const segmentClass = 'charcoal-texture !absolute';

  return (
    <div
      className="absolute inset-0 hidden lg:block pointer-events-none"
      aria-hidden="true"
    >
      <div className={segmentClass} style={a1V} />
      <div className={segmentClass} style={a1H} />
      <div className={segmentClass} style={a1Head} />
      <div className={segmentClass} style={a2V} />
      <div className={segmentClass} style={a2H} />
      <div className={segmentClass} style={a2Head} />
      <div className={segmentClass} style={a3V} />
      <div className={segmentClass} style={a3Head} />
    </div>
  );
}
