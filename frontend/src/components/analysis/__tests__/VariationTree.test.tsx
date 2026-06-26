// @vitest-environment jsdom
/**
 * Phase 137 Plan 03: VariationTree render tests.
 *
 * Fixture: 3-node main line (1.e4 1...e5 2.Nf3) + one variation (1...d5
 * branching from node 1). Tests cover both dual-DOM paths (mobile + desktop),
 * main-line rendering, variation rendering (BOARD-05), active node
 * aria-current, click → onNodeClick, and the empty state.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { VariationTree } from '../VariationTree';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';

beforeAll(() => {
  // jsdom does not implement scrollIntoView — stub it so the desktop auto-scroll
  // effect does not throw.
  Element.prototype.scrollIntoView = vi.fn();

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── Fixture ──────────────────────────────────────────────────────────────────

/**
 * Main line: ids [1, 2, 3]
 *   1. e4 (id=1, parentId=null)
 *   1... e5 (id=2, parentId=1)
 *   2. Nf3 (id=3, parentId=2)
 *
 * Variation: id=4 (1... d5), branching from id=1 (the fork parent).
 * currentNodeId=4 → buildVariationChain yields chain=[4], forkParentId=1.
 */
function buildFixture(): {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
} {
  const nodes = new Map<NodeId, MoveNode>([
    [
      1,
      {
        id: 1,
        san: 'e4',
        fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
        from: 'e2',
        to: 'e4',
        parentId: null,
      },
    ],
    [
      2,
      {
        id: 2,
        san: 'e5',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
        from: 'e7',
        to: 'e5',
        parentId: 1,
      },
    ],
    [
      3,
      {
        id: 3,
        san: 'Nf3',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2',
        from: 'g1',
        to: 'f3',
        parentId: 2,
      },
    ],
    [
      4,
      {
        id: 4,
        san: 'd5',
        fen: 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2',
        from: 'd7',
        to: 'd5',
        parentId: 1, // branches from id=1 (after 1. e4)
      },
    ],
  ]);
  const mainLine: NodeId[] = [1, 2, 3];
  return { nodes, mainLine };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('VariationTree', () => {
  it('(1) renders both mobile and desktop DOM paths regardless of viewport', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={3}
        onNodeClick={vi.fn()}
      />,
    );
    // Both subtrees are always present in the DOM; CSS hides one at runtime.
    expect(screen.getByTestId('variation-tree-mobile')).toBeTruthy();
    expect(screen.getByTestId('variation-tree-desktop')).toBeTruthy();
  });

  it('(2) main-line move buttons render with correct data-testids and SAN text', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Dual-DOM: each node id appears in both mobile and desktop paths.
    const e4Buttons = screen.getAllByTestId('variation-node-1');
    expect(e4Buttons.length).toBeGreaterThan(0);
    expect(e4Buttons[0]!.textContent).toContain('e4');

    const e5Buttons = screen.getAllByTestId('variation-node-2');
    expect(e5Buttons.length).toBeGreaterThan(0);

    const nf3Buttons = screen.getAllByTestId('variation-node-3');
    expect(nf3Buttons.length).toBeGreaterThan(0);
  });

  it('(3) variation node renders when currentNodeId is on a variation (BOARD-05)', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={4}
        onNodeClick={vi.fn()}
      />,
    );
    // Node 4 (d5) is the variation node — must appear in at least one DOM path.
    const d5Buttons = screen.getAllByTestId('variation-node-4');
    expect(d5Buttons.length).toBeGreaterThan(0);
    expect(d5Buttons[0]!.textContent).toContain('d5');
  });

  it('(4) active node carries aria-current="step"', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={2}
        onNodeClick={vi.fn()}
      />,
    );
    const node2Buttons = screen.getAllByTestId('variation-node-2');
    // At least one DOM-path button must have aria-current="step".
    const hasAriaCurrent = node2Buttons.some(
      (btn) => btn.getAttribute('aria-current') === 'step',
    );
    expect(hasAriaCurrent).toBe(true);
  });

  it('(4b) non-active nodes do not carry aria-current', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={2}
        onNodeClick={vi.fn()}
      />,
    );
    const node1Buttons = screen.getAllByTestId('variation-node-1');
    // None of the node-1 buttons should have aria-current=step.
    const noneHasAriaCurrent = node1Buttons.every(
      (btn) => btn.getAttribute('aria-current') !== 'step',
    );
    expect(noneHasAriaCurrent).toBe(true);
  });

  it('(5) clicking a move button calls onNodeClick with the nodeId', () => {
    const { nodes, mainLine } = buildFixture();
    const onNodeClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        onNodeClick={onNodeClick}
      />,
    );
    // Click the first occurrence of node 3 (Nf3 — mobile DOM path button).
    const nf3Buttons = screen.getAllByTestId('variation-node-3');
    expect(nf3Buttons.length).toBeGreaterThan(0);
    fireEvent.click(nf3Buttons[0]!);
    expect(onNodeClick).toHaveBeenCalledWith(3);
  });

  it('(5b) clicking the variation node calls onNodeClick with variation nodeId', () => {
    const { nodes, mainLine } = buildFixture();
    const onNodeClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={4}
        onNodeClick={onNodeClick}
      />,
    );
    const d5Buttons = screen.getAllByTestId('variation-node-4');
    expect(d5Buttons.length).toBeGreaterThan(0);
    fireEvent.click(d5Buttons[0]!);
    expect(onNodeClick).toHaveBeenCalledWith(4);
  });

  it('(6) empty state shows "No moves yet" in at least one DOM path', () => {
    render(
      <VariationTree
        nodes={new Map()}
        mainLine={[]}
        currentNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Both paths render the empty text (mobile via HorizontalMoveList emptyText,
    // desktop via the explicit <p>).
    const emptyTexts = screen.getAllByText('No moves yet');
    expect(emptyTexts.length).toBeGreaterThan(0);
  });
});
