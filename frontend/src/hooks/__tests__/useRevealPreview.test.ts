// @vitest-environment jsdom
/**
 * useRevealPreview tests: the keyed ephemeral state (stored live lines and
 * preview-committed ids) must not resurrect across a deactivate/reactivate of the
 * SAME puzzle FEN in one mounted screen. The preview resolution itself is
 * covered through useTrainRevealTree and lib/trainRevealPreview.
 */
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { MoveNode } from '@/hooks/useAnalysisBoard';
import { useRevealPreview } from '@/hooks/useRevealPreview';
import type { UseRevealPreviewOptions } from '@/hooks/useRevealPreview';
import type { PvLine } from '@/hooks/uciParser';
import { TRAIN_LIVE_ALT_MIN_DEPTH } from '@/lib/trainArrows';

const PUZZLE_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const AFTER_E4_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

/** One free node (1.e4) the board is parked on: a leaf, so it can hold a preview. */
const E4_NODE: MoveNode = {
  id: 0,
  san: 'e4',
  fen: AFTER_E4_FEN,
  from: 'e2',
  to: 'e4',
  parentId: null,
};
const NODES = new Map([[E4_NODE.id, E4_NODE]]);

/** A deep, legal engine line for the position after 1.e4. */
const LIVE_PV: PvLine = {
  multipv: 1,
  depth: TRAIN_LIVE_ALT_MIN_DEPTH,
  moves: ['e7e5'],
  evalCp: 20,
  evalMate: null,
};

function options(overrides: Partial<UseRevealPreviewOptions>): UseRevealPreviewOptions {
  return {
    active: true,
    resetKey: PUZZLE_FEN,
    nodes: NODES,
    currentNodeId: E4_NODE.id,
    activeChip: null,
    linePaths: {},
    chips: [],
    pvLines: [],
    ...overrides,
  };
}

function renderPreview(initial: Partial<UseRevealPreviewOptions>) {
  return renderHook((props: UseRevealPreviewOptions) => useRevealPreview(props), {
    initialProps: options(initial),
  });
}

describe('useRevealPreview keyed state', () => {
  it('committed ids do not come back when the same FEN reactivates', () => {
    const { result, rerender } = renderPreview({});
    act(() => result.current.markCommitted([3]));
    expect(result.current.committedIds.has(3)).toBe(true);

    rerender(options({ active: false, resetKey: null }));
    expect(result.current.committedIds.size).toBe(0);
    rerender(options({}));

    // Node ids restart at 0 with the new tree, so id 3 would name an unrelated node.
    expect(result.current.committedIds.size).toBe(0);
  });

  it('a stored live line does not come back when the same FEN reactivates', () => {
    const { result, rerender } = renderPreview({ pvLines: [LIVE_PV] });
    expect(result.current.preview?.steps.map((step) => step.san)).toEqual(['e5']);

    // The engine left the leaf: only the stored line can still show.
    rerender(options({ pvLines: [] }));
    expect(result.current.preview?.steps.map((step) => step.san)).toEqual(['e5']);

    rerender(options({ active: false, resetKey: null, pvLines: [] }));
    rerender(options({ pvLines: [] }));

    expect(result.current.preview).toBeNull();
  });

  it('a change of puzzle FEN also starts from empty state', () => {
    const { result, rerender } = renderPreview({});
    act(() => result.current.markCommitted([3]));

    rerender(options({ resetKey: AFTER_E4_FEN }));

    expect(result.current.committedIds.size).toBe(0);
  });
});
