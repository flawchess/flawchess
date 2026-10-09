import { describe, it, expect } from 'vitest';
import { resolveArrowOpacity, type BoardArrow } from '../ChessBoard';
import { DARK_BLUE, DARK_GREEN } from '@/lib/arrowColor';
import { TRAIN_FOCUS_ARROW_DIM_OPACITY, TRAIN_FOCUS_ARROW_LIT_OPACITY } from '@/lib/theme';

function arrow(overrides: Partial<BoardArrow> = {}): BoardArrow {
  return { startSquare: 'e2', endSquare: 'e4', color: DARK_GREEN, width: 0.5, ...overrides };
}

describe('resolveArrowOpacity (Phase 237)', () => {
  it('a hovered arrow gets the hover opacity even with an explicit (dim) opacity', () => {
    const hoveredPlain = resolveArrowOpacity(arrow({ isHovered: true }));
    const hoveredDim = resolveArrowOpacity(
      arrow({ isHovered: true, opacity: TRAIN_FOCUS_ARROW_DIM_OPACITY }),
    );
    expect(hoveredDim).toBe(hoveredPlain);
    expect(hoveredDim).not.toBe(TRAIN_FOCUS_ARROW_DIM_OPACITY);
  });

  it('an explicit opacity wins over the color-based default, for a standard and a blue arrow', () => {
    expect(resolveArrowOpacity(arrow({ opacity: TRAIN_FOCUS_ARROW_DIM_OPACITY }))).toBe(
      TRAIN_FOCUS_ARROW_DIM_OPACITY,
    );
    expect(
      resolveArrowOpacity(arrow({ color: DARK_BLUE, opacity: TRAIN_FOCUS_ARROW_LIT_OPACITY })),
    ).toBe(TRAIN_FOCUS_ARROW_LIT_OPACITY);
  });

  it('with no opacity the color default applies: a blue (low-emphasis) arrow is fainter than a standard one, and a hover beats both', () => {
    const standard = resolveArrowOpacity(arrow());
    const blue = resolveArrowOpacity(arrow({ color: DARK_BLUE }));
    const hovered = resolveArrowOpacity(arrow({ isHovered: true }));
    expect(blue).toBeLessThan(standard);
    expect(hovered).toBeGreaterThan(standard);
  });

  it('an explicit opacity of 0 is honoured, not treated as unset', () => {
    expect(resolveArrowOpacity(arrow({ opacity: 0 }))).toBe(0);
  });
});
