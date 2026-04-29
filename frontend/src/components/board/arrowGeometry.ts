// Shared SVG-arrow geometry for ChessBoard and MiniBoard.
//
// Both consumers map chess square strings ("e4") to grid coordinates and build
// arrow-shaped <path> d-strings. ChessBoard uses normalized 0–1 widths from
// arrow frequency; MiniBoard uses fixed thin proportions. The math is identical
// — extracted here so we have a single source of truth (see CLAUDE.md
// "Shared Query Filters" precedent: single implementation rule).

const FILES = 'abcdefgh';

/**
 * Convert a chess square string ("e4") to grid coordinates centered on the
 * square. Returns [x, y] in units of squares (0..8). The board orientation
 * flips both axes when `flipped` is true.
 */
export function squareToCoords(square: string, flipped: boolean): [number, number] {
  // safe: square is always a 2-char chess square string like "e4"
  const file = FILES.indexOf(square[0]!);
  const rank = parseInt(square[1]!, 10) - 1;
  const x = flipped ? 7 - file + 0.5 : file + 0.5;
  const y = flipped ? rank + 0.5 : 7 - rank + 0.5;
  return [x, y];
}

/**
 * Build the SVG `d` attribute for an arrow from (x1, y1) to (x2, y2). All
 * coordinates and sizes are in pixel space. The arrow is a 7-point closed
 * polygon: rectangular shaft expanding into a triangular head at the tip.
 */
export function buildArrowPath(
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

  return [
    `M ${startLeft[0]},${startLeft[1]}`,
    `L ${junctionLeft[0]},${junctionLeft[1]}`,
    `L ${headLeft[0]},${headLeft[1]}`,
    `L ${tip[0]},${tip[1]}`,
    `L ${headRight[0]},${headRight[1]}`,
    `L ${junctionRight[0]},${junctionRight[1]}`,
    `L ${startRight[0]},${startRight[1]}`,
    'Z',
  ].join(' ');
}
