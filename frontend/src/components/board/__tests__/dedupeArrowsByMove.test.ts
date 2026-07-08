import { describe, it, expect } from 'vitest';
import { dedupeArrowsByMove } from '../arrowGeometry';
import type { BoardArrow } from '../ChessBoard';

const arrow = (startSquare: string, endSquare: string, extra: Partial<BoardArrow> = {}): BoardArrow => ({
  startSquare,
  endSquare,
  color: '#fff',
  width: 0.5,
  ...extra,
});

describe('dedupeArrowsByMove', () => {
  it('collapses arrows sharing a from→to to a single arrow', () => {
    // The collision that produced "Encountered two children with the same key,
    // `a3-e7`" while dragging the eval-chart slider: a transient live engine
    // 2nd-best arrow matching the best/should-have arrow on the same path.
    const blue = arrow('a3', 'e7', { color: 'blue' });
    const grey = arrow('a3', 'e7', { color: 'grey' });
    const result = dedupeArrowsByMove([blue, grey]);
    expect(result).toHaveLength(1);
  });

  it('keeps the LAST occurrence (the one drawn on top, i.e. what is visible)', () => {
    const blue = arrow('a3', 'e7', { color: 'blue' });
    const grey = arrow('a3', 'e7', { color: 'grey' });
    expect(dedupeArrowsByMove([blue, grey])[0]).toBe(grey);
    expect(dedupeArrowsByMove([grey, blue])[0]).toBe(blue);
  });

  it('preserves order and identity of distinct arrows', () => {
    const a = arrow('e2', 'e4');
    const b = arrow('d2', 'd4');
    const c = arrow('g1', 'f3');
    expect(dedupeArrowsByMove([a, b, c])).toEqual([a, b, c]);
  });

  it('dedupes only by from→to, keeping the deduped arrow in the last position', () => {
    const a = arrow('e2', 'e4');
    const dup1 = arrow('a3', 'e7', { color: 'blue' });
    const b = arrow('d2', 'd4');
    const dup2 = arrow('a3', 'e7', { color: 'grey' });
    // dup1 is dropped in favor of dup2 (last), which keeps dup2's slot.
    expect(dedupeArrowsByMove([a, dup1, b, dup2])).toEqual([a, b, dup2]);
  });

  it('returns an empty array unchanged', () => {
    expect(dedupeArrowsByMove([])).toEqual([]);
  });

  it('keeps two arrows on the same from→to when they have distinct layerKey values', () => {
    // The FlawChess Engine + Stockfish concentric-arrow case (D-06): when both
    // engines agree on the same move, both arrows must survive dedupe instead
    // of collapsing to one, so they render as nested concentric arrows.
    const fc = arrow('e2', 'e4', { color: 'amber', layerKey: 'fc-0' });
    const sf = arrow('e2', 'e4', { color: 'blue', layerKey: 'sf-0' });
    const result = dedupeArrowsByMove([fc, sf]);
    expect(result).toHaveLength(2);
    expect(result).toEqual([fc, sf]);
  });

  it('still collapses same from→to arrows with no layerKey (existing behavior unchanged)', () => {
    const blue = arrow('e2', 'e4', { color: 'blue' });
    const grey = arrow('e2', 'e4', { color: 'grey' });
    expect(dedupeArrowsByMove([blue, grey])).toHaveLength(1);
  });
});
